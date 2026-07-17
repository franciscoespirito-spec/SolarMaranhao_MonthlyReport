#!/usr/bin/env python3
"""
Exportação OFICIAL do Email Log Search (Google Admin Console) via Playwright.

Baixa o CSV oficial — o único lugar onde o Google fornece o REMETENTE de todos
os e-mails (inclusive os rejeitados na porta, que a Reports API não expõe).

JANELA DE BUSCA (máxima possível): usa "Especificar o intervalo" escolhendo as
datas por CLIQUES NO CALENDÁRIO — nunca digita (o campo digitado tem bug de
máscara conhecido). Tenta hoje-31 dias; se a tela recusar, hoje-30; se o
intervalo falhar por qualquer motivo, cai para o preset "Últimos 7 dias"
(garantia de nunca ficar sem dados). Roda todo dia; o consolidar_oficial.py
deduplica as janelas sobrepostas e fecha o mês.

SESSÃO: os cookies renovados são salvos de volta no admin_session.json a cada
execução (como um navegador real), prolongando a vida da sessão. Se expirar,
cria logs/oficial/SESSAO_EXPIRADA.flag (status-vps avisa; refazer com
save_session.py).

Uso:
    python3 exportar_oficial.py               # exportação normal (headless)
    python3 exportar_oficial.py --debug       # salva screenshot de cada etapa
"""
import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE          = "/root/projetos/compliance-email"
SESSION_PATH  = f"{BASE}/credentials/admin_session.json"
DIR_OFICIAL   = f"{BASE}/logs/oficial"
FLAG_SESSAO   = f"{DIR_OFICIAL}/SESSAO_EXPIRADA.flag"
ULTIMO_OK     = f"{DIR_OFICIAL}/ultimo_sucesso.txt"
LOG_FILE      = f"{DIR_OFICIAL}/exportar_oficial.log"
URL_LOGSEARCH = "https://admin.google.com/ac/emaillogsearch"
DESTINATARIO  = "compliance@beng.eng.br"

MESES_PT = {1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio",
            6: "junho", 7: "julho", 8: "agosto", 9: "setembro", 10: "outubro",
            11: "novembro", 12: "dezembro"}

os.makedirs(DIR_OFICIAL, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger()
DEBUG = "--debug" in sys.argv


# ── utilidades ────────────────────────────────────────────────────────────────

def shot(page, nome):
    caminho = f"{DIR_OFICIAL}/step_{nome}.png"
    try:
        page.screenshot(path=caminho, full_page=False)
        log.info(f"screenshot: {caminho}")
    except Exception:
        pass


def falha(page, etapa, msg):
    shot(page, f"ERRO_{etapa}")
    log.error(f"[{etapa}] {msg}")
    print(f"ERRO [{etapa}]: {msg}")
    print(f"Screenshot: {DIR_OFICIAL}/step_ERRO_{etapa}.png")
    sys.exit(1)


def sessao_expirada(page):
    with open(FLAG_SESSAO, "w") as f:
        f.write(datetime.now().isoformat())
    shot(page, "ERRO_sessao_expirada")
    log.error("Sessão do Google expirada — refazer login com save_session.py")
    print("❌ SESSÃO EXPIRADA — refazer login (ver save_session.py / MAPA_VPS.md)")
    sys.exit(2)


def clicar_visivel(loc, maxn=12):
    """Clica no primeiro elemento VISÍVEL do locator (o Google duplica ocultos)."""
    for i in range(min(loc.count(), maxn)):
        el = loc.nth(i)
        try:
            if el.is_visible():
                el.click()
                return True
        except Exception:
            pass
    return False


# ── período: menu e calendário ────────────────────────────────────────────────

def abrir_menu_periodo(page):
    for seletor in ("[aria-haspopup='listbox']", "[role='combobox']"):
        loc = page.locator(seletor)
        for i in range(min(loc.count(), 8)):
            el = loc.nth(i)
            try:
                if not el.is_visible():
                    continue
                el.click()
                page.wait_for_timeout(1_200)
                return True
            except Exception:
                continue
    return False


def escolher_opcao_periodo(page, texto):
    """Escolhe uma opção do menu de período pelo texto (só itens visíveis)."""
    for _ in range(12):
        cand = page.locator("li[role='option']")
        for i in range(cand.count()):
            el = cand.nth(i)
            try:
                if el.is_visible() and texto.lower() in (el.inner_text() or "").lower():
                    el.click()
                    return True
            except Exception:
                pass
        page.wait_for_timeout(500)
    return False


def mes_do_calendario(page, timeout_ms=6000):
    """(ano, mês) do cabeçalho do calendário (ex: 'julho de 2026' → (2026,7)).

    Relê em loop até o timeout (o cabeçalho às vezes demora a renderizar).
    """
    import re
    pat = re.compile(r"^([a-zçãáéíóúâêô]+) de (\d{4})$", re.I)
    decorrido = 0
    while decorrido < timeout_ms:
        els = page.get_by_text(pat)
        for i in range(min(els.count(), 8)):
            el = els.nth(i)
            try:
                if not el.is_visible():
                    continue
                m = pat.match(el.inner_text().strip().lower())
                if not m:
                    continue
                nome, ano = m.group(1), m.group(2)
                for num, n in MESES_PT.items():
                    if n == nome:
                        return (int(ano), num)
            except Exception:
                pass
        page.wait_for_timeout(500)
        decorrido += 500
    return None


def abrir_calendario(page, rotulo):
    """Clica no campo de data e espera o calendário (gridcell) renderizar."""
    campo = page.locator(f"input[aria-label='{rotulo}']")
    for _ in range(3):
        if not clicar_visivel(campo):
            return False
        try:
            page.wait_for_selector("[role='gridcell']", state="visible", timeout=5000)
            page.wait_for_timeout(400)
            return True
        except Exception:
            page.wait_for_timeout(600)
    return False


def navegar_mes(page, direcao):
    """direcao -1 = mês anterior, +1 = próximo mês (botões <div> com aria-label)."""
    rotulo = "mês anterior" if direcao < 0 else "próximo mês"
    return clicar_visivel(page.locator(f"[aria-label='{rotulo}']"))


def clicar_dia(page, dia):
    """Clica na CÉLULA (gridcell) do dia. Retorna True, 'disabled' ou False."""
    gc = page.locator("[role='gridcell']")
    for i in range(gc.count()):
        e = gc.nth(i)
        try:
            if not e.is_visible():
                continue
            if (e.inner_text() or "").strip() != str(dia):
                continue
            if e.get_attribute("aria-disabled") == "true":
                return "disabled"
            e.click()
            return True
        except Exception:
            continue
    return False


def menor_dia_habilitado(page):
    """Menor número de dia HABILITADO no calendário visível (int) ou None."""
    gc = page.locator("[role='gridcell']")
    melhor = None
    for i in range(gc.count()):
        e = gc.nth(i)
        try:
            if not e.is_visible():
                continue
            t = (e.inner_text() or "").strip()
            if not t.isdigit():
                continue
            if e.get_attribute("aria-disabled") == "true":
                continue
            d = int(t)
            if melhor is None or d < melhor:
                melhor = d
        except Exception:
            continue
    return melhor


def definir_de_mais_antiga(page):
    """Abre 'De', vai ao mês anterior e clica no dia HABILITADO mais antigo.

    Esse é exatamente o limite do Google (~30 dias): dias além ficam desabilitados.
    Retorna a data (date) escolhida ou None.
    """
    from datetime import date
    if not abrir_calendario(page, "De"):
        return None
    if mes_do_calendario(page) is None:
        return None
    # tenta o mês anterior; se não houver dia habilitado lá, usa o mês atual
    navegar_mes(page, -1)
    page.wait_for_timeout(700)
    mes = mes_do_calendario(page)
    dia = menor_dia_habilitado(page)
    if dia is None:
        navegar_mes(page, +1)
        page.wait_for_timeout(700)
        mes = mes_do_calendario(page)
        dia = menor_dia_habilitado(page)
    if dia is None or mes is None:
        return None
    if clicar_dia(page, dia) is not True:
        return None
    page.wait_for_timeout(800)
    return date(mes[0], mes[1], dia)


def valor_campo(page, rotulo):
    loc = page.locator(f"input[aria-label='{rotulo}']")
    for i in range(loc.count()):
        el = loc.nth(i)
        try:
            if el.is_visible():
                return el.input_value()
        except Exception:
            pass
    return ""


def definir_data(page, rotulo, data):
    """Define um campo de data ('De'/'Até') SÓ COM CLIQUES no calendário.

    Navega nos dois sentidos (mês anterior/próximo) até o mês-alvo e clica no dia.
    """
    if not abrir_calendario(page, rotulo):
        log.warning(f"calendário de '{rotulo}' não abriu")
        return False
    alvo = (data.year, data.month)
    for _ in range(15):
        atual = mes_do_calendario(page)
        if atual is None:
            log.warning(f"  não li o mês do calendário para '{rotulo}'")
            return False
        if atual == alvo:
            break
        direcao = -1 if alvo < atual else 1
        log.info(f"  '{rotulo}': calendário em {atual}, indo p/ {alvo} (dir={direcao})")
        if not navegar_mes(page, direcao):
            log.warning("  botão de navegação de mês não encontrado")
            return False
        page.wait_for_timeout(700)
    else:
        return False
    r = clicar_dia(page, data.day)
    if r == "disabled":
        log.warning(f"  dia {data.day} está DESABILITADO (futuro?) no calendário de '{rotulo}'")
        return False
    if not r:
        log.warning(f"  dia {data.day} não clicável em '{rotulo}'")
        return False
    page.wait_for_timeout(800)
    return True


def erro_de_intervalo(page):
    """Mensagens de validação conhecidas da tela."""
    for t in ("Digite uma data e hora válidas", "não pode ser", "inválid"):
        loc = page.get_by_text(t, exact=False)
        for i in range(min(loc.count(), 4)):
            try:
                if loc.nth(i).is_visible():
                    return t
            except Exception:
                pass
    return None


def clicar_pesquisar(page):
    for fabrica in [
        lambda: page.get_by_role("button", name="Pesquisar"),
        lambda: page.get_by_role("button", name="Search"),
        lambda: page.locator("button:has-text('Pesquisar')"),
    ]:
        try:
            if clicar_visivel(fabrica()):
                return True
        except Exception:
            continue
    return False


def selecionar_intervalo_maximo(page):
    """Janela máxima via 'Especificar o intervalo' (31 dias; senão 30).

    Retorna o nº de dias da janela que funcionou. Levanta exceção se nada
    funcionar (o chamador cai para o preset de 7 dias).
    """
    if not abrir_menu_periodo(page):
        raise RuntimeError("menu de período não abriu")
    if not escolher_opcao_periodo(page, "Especificar o intervalo"):
        raise RuntimeError("opção 'Especificar o intervalo' não apareceu")
    page.wait_for_timeout(2_000)
    if DEBUG: shot(page, "03a_intervalo_selecionado")

    hoje = datetime.now(timezone.utc).date()
    # 1) "Até" = hoje (mês atual, clica o dia de hoje)
    if not definir_data(page, "Até", hoje):
        raise RuntimeError("não consegui definir 'Até' = hoje")
    # 2) "De" = data habilitada mais antiga (o próprio limite do Google, ~30 dias)
    de = definir_de_mais_antiga(page)
    if de is None:
        raise RuntimeError("não consegui definir 'De' (data mais antiga)")
    dias = (hoje - de).days
    de_v, ate_v = valor_campo(page, "De"), valor_campo(page, "Até")
    log.info(f"Janela escolhida: {de} → {hoje} ({dias} dias) | campos De='{de_v}' Até='{ate_v}'")
    if DEBUG: shot(page, "03b_datas_definidas")
    if not (de_v and ate_v):
        raise RuntimeError("campos De/Até ficaram vazios")
    erro = erro_de_intervalo(page)
    if erro:
        raise RuntimeError(f"validação recusou o intervalo ({erro})")
    if not clicar_pesquisar(page):
        raise RuntimeError("botão Pesquisar não encontrado")
    page.wait_for_timeout(10_000)
    erro = erro_de_intervalo(page)
    if erro:
        raise RuntimeError(f"pesquisa recusou o intervalo ({erro})")
    log.info(f"✅ Janela de {dias} dias aceita")
    return dias


def selecionar_preset_7dias(page):
    """Fallback garantido: preset 'Últimos 7 dias' + Pesquisar."""
    if not abrir_menu_periodo(page):
        raise RuntimeError("menu de período não abriu (fallback)")
    if not escolher_opcao_periodo(page, "Últimos 7 dias"):
        raise RuntimeError("preset 'Últimos 7 dias' não apareceu (fallback)")
    page.wait_for_timeout(1_000)
    if not clicar_pesquisar(page):
        raise RuntimeError("botão Pesquisar não encontrado (fallback)")
    page.wait_for_timeout(10_000)


# ── fluxo principal ───────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("Iniciando exportação oficial do Email Log Search")

    if not os.path.exists(SESSION_PATH):
        print(f"ERRO: sessão não encontrada em {SESSION_PATH}. Rode save_session.py.")
        sys.exit(2)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = browser.new_context(
            storage_state=SESSION_PATH,
            user_agent=("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
            locale="pt-BR",
            viewport={"width": 1400, "height": 1000},
            accept_downloads=True,
        )
        page = ctx.new_page()

        # ── Etapa 1: abrir a Pesquisa de registros de e-mail ────────────────
        log.info("Etapa 1: abrindo emaillogsearch")
        page.goto(URL_LOGSEARCH, timeout=90_000, wait_until="domcontentloaded")
        page.wait_for_timeout(8_000)
        if "accounts.google" in page.url:
            sessao_expirada(page)
        ctx.storage_state(path=SESSION_PATH)   # renova cookies logo ao entrar
        if DEBUG: shot(page, "01_pagina_aberta")

        # ── Etapa 2: preencher o destinatário ───────────────────────────────
        log.info("Etapa 2: preenchendo destinatário")
        campo = None
        for tentativa in [
            lambda: page.get_by_label("E-mail do destinatário", exact=False),
            lambda: page.locator("input[aria-label*='destinatário' i]"),
            lambda: page.locator("input[aria-label*='recipient' i]"),
        ]:
            try:
                loc = tentativa()
                if loc.count() > 0 and loc.first.is_visible():
                    campo = loc.first
                    break
            except Exception:
                continue
        if campo is None:
            falha(page, "destinatario", "campo 'E-mail do destinatário' não encontrado")
        campo.click()
        campo.fill(DESTINATARIO)
        if DEBUG: shot(page, "02_destinatario")

        # ── Etapa 3: período MÁXIMO (31→30 dias por calendário; fallback 7) ─
        try:
            janela = selecionar_intervalo_maximo(page)
        except Exception as e:
            log.warning(f"Intervalo máximo falhou ({e}); caindo para 'Últimos 7 dias'")
            try:
                selecionar_preset_7dias(page)
                janela = 7
            except Exception as e2:
                falha(page, "periodo", f"nem intervalo nem preset funcionaram: {e2}")
        log.info(f"Etapa 3 concluída — janela de {janela} dias pesquisada")
        if DEBUG: shot(page, "05_resultados")

        # ── Etapa 4: baixar como CSV (diálogo → tarefa assíncrona → link) ───
        log.info("Etapa 4: baixando CSV")
        baixar = None
        for tentativa in [
            lambda: page.get_by_role("button", name="Fazer o download"),
            lambda: page.get_by_role("button", name="Baixar"),
            lambda: page.get_by_role("button", name="Download"),
            lambda: page.locator("[aria-label*='download' i], [aria-label*='baixar' i]"),
        ]:
            try:
                loc = tentativa()
                for i in range(loc.count()):
                    if loc.nth(i).is_visible():
                        baixar = loc.nth(i)
                        break
                if baixar:
                    break
            except Exception:
                continue
        if baixar is None:
            falha(page, "baixar", "botão de download não encontrado — a pesquisa retornou resultados?")
        baixar.click()
        page.wait_for_timeout(2_500)
        if DEBUG: shot(page, "06_dialogo_download")

        # marca o rádio "Baixar como arquivo CSV" (padrão é Google Planilhas)
        marcou = False
        for tentativa in [
            lambda: page.get_by_role("radio", name="Baixar como arquivo CSV"),
            lambda: page.get_by_text("Baixar como arquivo CSV", exact=False),
        ]:
            try:
                if clicar_visivel(tentativa()):
                    marcou = True
                    break
            except Exception:
                continue
        if not marcou:
            falha(page, "opcao_csv", "não consegui marcar 'Baixar como arquivo CSV'")
        page.wait_for_timeout(800)
        if DEBUG: shot(page, "07_csv_marcado")

        # BAIXAR do diálogo enfileira uma TAREFA assíncrona
        confirmar = None
        for tentativa in [
            lambda: page.get_by_role("button", name="Baixar", exact=True),
            lambda: page.get_by_role("button", name="BAIXAR"),
            lambda: page.locator("button:has-text('BAIXAR'), button:has-text('Baixar')"),
        ]:
            try:
                loc = tentativa()
                if loc.count() > 0 and loc.last.is_visible():
                    confirmar = loc.last
                    break
            except Exception:
                continue
        if confirmar is None:
            falha(page, "baixar_dialogo", "botão BAIXAR do diálogo não encontrado")
        confirmar.click()
        log.info("Tarefa de geração do CSV enfileirada; aguardando ficar pronta")
        page.wait_for_timeout(4_000)
        if DEBUG: shot(page, "08_pos_baixar")

        # o CSV pronto aparece no painel de Tarefas com o link "Baixar CSV"
        def achar_link_csv():
            loc = page.get_by_text("Baixar CSV", exact=False)
            for i in range(loc.count()):
                try:
                    if loc.nth(i).is_visible():
                        return loc.nth(i)
                except Exception:
                    continue
            return None

        def painel_visivel():
            for marcador in ("SUAS TAREFAS", "Concluído", "pronto para download"):
                try:
                    if page.get_by_text(marcador, exact=False).count() > 0:
                        return True
                except Exception:
                    pass
            return False

        def abrir_painel_tarefas():
            for fabrica in [
                lambda: page.get_by_role("button", name="Tarefas"),
                lambda: page.locator("[aria-label*='tarefa' i]"),
                lambda: page.locator("[aria-label*='task' i]"),
            ]:
                try:
                    loc = fabrica()
                    for i in range(min(loc.count(), 8)):
                        if loc.nth(i).is_visible():
                            loc.nth(i).click()
                            page.wait_for_timeout(1_500)
                            if painel_visivel() or achar_link_csv():
                                return True
                except Exception:
                    continue
            return False

        link = None
        for _ in range(50):  # até ~2,5 min
            link = achar_link_csv()
            if link is not None:
                break
            if not painel_visivel():
                abrir_painel_tarefas()
            page.wait_for_timeout(3_000)
        if DEBUG: shot(page, "09_painel_tarefas")
        if link is None:
            falha(page, "download", "o link 'Baixar CSV' não apareceu no painel de Tarefas")

        destino = f"{DIR_OFICIAL}/LogSearchResults_{datetime.now().strftime('%Y-%m-%d_%H%M')}.csv"
        try:
            with page.expect_download(timeout=120_000) as dl_info:
                link.click()
            dl_info.value.save_as(destino)
        except PWTimeout:
            falha(page, "download", "cliquei em 'Baixar CSV' mas o download não começou")

        tamanho = os.path.getsize(destino)
        log.info(f"CSV salvo: {destino} ({tamanho} bytes; janela {janela} dias)")

        # sucesso: renova cookies, atualiza marcador, limpa flag
        ctx.storage_state(path=SESSION_PATH)
        with open(ULTIMO_OK, "w") as f:
            f.write(f"{datetime.now().isoformat()} janela={janela}d\n")
        if os.path.exists(FLAG_SESSAO):
            os.remove(FLAG_SESSAO)

        print(f"OK: exportação oficial salva em {destino} ({tamanho} bytes, janela de {janela} dias)")
        browser.close()


if __name__ == "__main__":
    main()
