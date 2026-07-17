#!/usr/bin/env python3
"""
Exportação OFICIAL do Email Log Search (Google Admin Console) via Playwright.

Baixa o CSV oficial — o único lugar onde o Google fornece o REMETENTE de todos
os e-mails (inclusive os rejeitados na porta, que a Reports API não expõe).

Estratégia anti-bug: NUNCA digita datas (o campo "Especificar o intervalo" tem
um bug de máscara/validação conhecido). Usa o período PRÉ-DEFINIDO "Últimos 7
dias" (o maior que existe no menu) e roda TODO DIA: cada dia fica coberto por
até 7 execuções sobrepostas — redundância que tolera falhas e sessão expirada
por alguns dias. A consolidação mensal (dedupe) é do consolidar_oficial.py.

Uso:
    python3 exportar_oficial.py               # exportação normal (headless)
    python3 exportar_oficial.py --debug       # salva screenshot de cada etapa

Falhas de sessão criam logs/oficial/SESSAO_EXPIRADA.flag (o status-vps avisa).
Refazer login: save_session.py (ver instruções no cabeçalho daquele arquivo).
"""
import os
import sys
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE          = "/root/projetos/compliance-email"
SESSION_PATH  = f"{BASE}/credentials/admin_session.json"
DIR_OFICIAL   = f"{BASE}/logs/oficial"
FLAG_SESSAO   = f"{DIR_OFICIAL}/SESSAO_EXPIRADA.flag"
ULTIMO_OK     = f"{DIR_OFICIAL}/ultimo_sucesso.txt"
LOG_FILE      = f"{DIR_OFICIAL}/exportar_oficial.log"
URL_LOGSEARCH = "https://admin.google.com/ac/emaillogsearch"
DESTINATARIO  = "compliance@beng.eng.br"

# O maior período pré-definido do menu é "Últimos 7 dias" (verificado em 17/07/2026;
# opções reais: Hoje / Desde ontem / Últimos 7 dias / Especificar o intervalo / Mais de 30 dias).
# NUNCA escolher "Especificar o intervalo" — é o campo com bug de máscara.
SELETOR_OPCAO_7DIAS = (
    "li[role='option'][data-value='last7Days'], "
    "[role='option'][aria-label*='7 dias' i], "
    "[role='option']:has-text('Últimos 7 dias')"
)

os.makedirs(DIR_OFICIAL, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger()
DEBUG = "--debug" in sys.argv


def shot(page, nome):
    """Screenshot de depuração (sempre em falhas; a cada etapa se --debug)."""
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
    print(f"Screenshot de depuração em: {DIR_OFICIAL}/step_ERRO_{etapa}.png")
    sys.exit(1)


def sessao_expirada(page):
    with open(FLAG_SESSAO, "w") as f:
        f.write(datetime.now().isoformat())
    shot(page, "ERRO_sessao_expirada")
    log.error("Sessão do Google expirada — refazer login com save_session.py")
    print("❌ SESSÃO EXPIRADA — o Google pediu login.")
    print("   Refaça o login: veja instruções em save_session.py")
    print("   (VcXsrv no PC → ssh -X → rodar save_session.py)")
    sys.exit(2)


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
            accept_downloads=True,
        )
        page = ctx.new_page()

        # ── Etapa 1: abrir a Pesquisa de registros de e-mail ────────────────
        log.info("Etapa 1: abrindo emaillogsearch")
        page.goto(URL_LOGSEARCH, timeout=90_000, wait_until="domcontentloaded")
        page.wait_for_timeout(8_000)  # app Angular demora a montar
        if "accounts.google" in page.url or "signin" in page.url.lower():
            sessao_expirada(page)
        if DEBUG: shot(page, "01_pagina_aberta")

        # ── Etapa 2: preencher o destinatário ───────────────────────────────
        log.info("Etapa 2: preenchendo destinatário")
        campo = None
        # tenta por label (PT e EN), depois por atributos comuns
        for tentativa in [
            lambda: page.get_by_label("E-mail do destinatário", exact=False),
            lambda: page.get_by_label("Recipient email", exact=False),
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
            falha(page, "destinatario", "não achei o campo 'E-mail do destinatário' — a tela pode ter mudado")
        campo.click()
        campo.fill(DESTINATARIO)
        if DEBUG: shot(page, "02_destinatario")

        # ── Etapa 3: escolher o período PRÉ-DEFINIDO (nunca digitar datas) ──
        log.info("Etapa 3: selecionando período 'Últimos 7 dias'")

        def achar_opcao_visivel():
            candidatos = page.locator(SELETOR_OPCAO_7DIAS)
            for i in range(candidatos.count()):
                if candidatos.nth(i).is_visible():
                    return candidatos.nth(i)
            return None

        def esperar_opcao(timeout_ms):
            decorrido = 0
            while decorrido < timeout_ms:
                alvo = achar_opcao_visivel()
                if alvo:
                    return alvo
                page.wait_for_timeout(500)
                decorrido += 500
            return None

        # Plano A: achar o GATILHO visual do menu e clicar (vários candidatos)
        gatilhos = [
            ("texto 'Período das mensagens'", lambda: page.get_by_text("Período das mensagens", exact=False)),
            ("texto 'Período da mensagem'",   lambda: page.get_by_text("Período da mensagem", exact=False)),
            ("aria-haspopup=listbox",         lambda: page.locator("[aria-haspopup='listbox']")),
            ("combobox",                      lambda: page.get_by_role("combobox")),
            ("aria-label período",            lambda: page.locator("[aria-label*='período' i][aria-label*='mensag' i]")),
        ]
        alvo = None
        for nome, fabrica in gatilhos:
            try:
                loc = fabrica()
                n = loc.count()
            except Exception:
                continue
            for i in range(min(n, 4)):
                cand = loc.nth(i)
                try:
                    if not cand.is_visible():
                        continue
                    log.info(f"Tentando abrir menu via: {nome} (elemento {i})")
                    cand.scroll_into_view_if_needed()
                    cand.click()
                    alvo = esperar_opcao(5_000)
                    if alvo:
                        break
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(800)
                except Exception as e:
                    log.info(f"  gatilho '{nome}' falhou: {str(e)[:80]}")
            if alvo:
                log.info(f"Menu aberto via: {nome}")
                break
        if DEBUG: shot(page, "03_menu_periodo_aberto")

        if alvo is not None:
            alvo.click()
            page.wait_for_timeout(1_000)
        else:
            # Plano C: acionar a opção OCULTA via JavaScript e conferir se pegou
            log.warning("Menu não abriu visualmente — acionando a opção por JavaScript")
            cand = page.locator("li[role='option'][data-value='last7Days']")
            if cand.count() == 0:
                falha(page, "preset", "opção 'Últimos 7 dias' não existe no HTML — tela mudou")
            cand.first.evaluate("el => el.click()")
            page.wait_for_timeout(1_500)
            # confere se o seletor agora exibe o período escolhido
            confer = page.get_by_text("Últimos 7 dias", exact=False)
            visivel = any(confer.nth(i).is_visible() for i in range(min(confer.count(), 6)))
            if not visivel:
                falha(page, "preset", "cliquei por JavaScript mas a seleção não confirmou na tela")
            log.info("Seleção por JavaScript confirmada na tela")
        log.info("Período escolhido: 'Últimos 7 dias'")
        if DEBUG: shot(page, "04_periodo_escolhido")

        # ── Etapa 4: pesquisar ───────────────────────────────────────────────
        log.info("Etapa 4: clicando em Pesquisar")
        botao = None
        for tentativa in [
            lambda: page.get_by_role("button", name="Pesquisar"),
            lambda: page.get_by_role("button", name="Search"),
            lambda: page.locator("button:has-text('Pesquisar')"),
        ]:
            try:
                loc = tentativa()
                if loc.count() > 0 and loc.first.is_visible():
                    botao = loc.first
                    break
            except Exception:
                continue
        if botao is None:
            falha(page, "pesquisar", "não achei o botão Pesquisar")
        botao.click()
        page.wait_for_timeout(10_000)  # aguarda a busca retornar
        if DEBUG: shot(page, "05_resultados")

        # ── Etapa 5: baixar como CSV ─────────────────────────────────────────
        log.info("Etapa 5: baixando CSV")
        baixar = None
        for tentativa in [
            lambda: page.get_by_role("button", name="Fazer o download"),
            lambda: page.get_by_role("button", name="Baixar"),
            lambda: page.get_by_role("button", name="Download"),
            lambda: page.locator("[aria-label*='download' i], [aria-label*='baixar' i]"),
        ]:
            try:
                loc = tentativa()
                if loc.count() > 0 and loc.first.is_visible():
                    baixar = loc.first
                    break
            except Exception:
                continue
        if baixar is None:
            falha(page, "baixar", "não achei o botão de download — a pesquisa retornou resultados?")
        baixar.click()
        page.wait_for_timeout(2_500)  # diálogo "Baixar resultados" abre
        if DEBUG: shot(page, "06_dialogo_download")

        # O diálogo tem 2 opções (rádio): "Exportar para o Google Planilhas" (padrão)
        # e "Baixar como arquivo CSV". Precisamos MARCAR o CSV antes de confirmar.
        marcou = False
        for tentativa in [
            lambda: page.get_by_role("radio", name="Baixar como arquivo CSV"),
            lambda: page.get_by_text("Baixar como arquivo CSV", exact=False),
            lambda: page.locator("[role='radio']:near(:text('CSV'))"),
        ]:
            try:
                loc = tentativa()
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    marcou = True
                    log.info("Opção 'Baixar como arquivo CSV' marcada")
                    break
            except Exception:
                continue
        if not marcou:
            falha(page, "opcao_csv", "não consegui marcar 'Baixar como arquivo CSV' no diálogo")
        page.wait_for_timeout(800)
        if DEBUG: shot(page, "07_csv_marcado")

        # Clica em BAIXAR do diálogo — isso ENFILEIRA uma tarefa (não baixa direto).
        # O Google gera o CSV de forma assíncrona e disponibiliza um link "Baixar CSV"
        # no painel de Tarefas (ícone de relógio no topo).
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

        # Localiza o link "Baixar CSV" (texto exato do painel de Tarefas)
        def achar_link_csv():
            loc = page.get_by_text("Baixar CSV", exact=False)
            for i in range(loc.count()):
                try:
                    if loc.nth(i).is_visible():
                        return loc.nth(i)
                except Exception:
                    continue
            return None

        # O painel está aberto? (marcadores de texto do painel de Tarefas)
        def painel_visivel():
            for marcador in ("SUAS TAREFAS", "Concluído", "pronto para download", "TAREFAS DOS OUTROS"):
                try:
                    if page.get_by_text(marcador, exact=False).count() > 0:
                        return True
                except Exception:
                    pass
            return False

        def abrir_painel_tarefas():
            for fabrica in [
                lambda: page.get_by_role("button", name="Tarefas"),
                lambda: page.get_by_role("button", name="Tasks"),
                lambda: page.locator("[aria-label*='tarefa' i]"),
                lambda: page.locator("[aria-label*='task' i]"),
                lambda: page.locator("header [role='button'], [role='banner'] [role='button']"),
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

        # Aguarda a tarefa concluir (até ~2,5 min). Só abre o painel se ele NÃO estiver visível.
        link = None
        for ciclo in range(50):
            link = achar_link_csv()
            if link is not None:
                break
            if not painel_visivel():
                abrir_painel_tarefas()
            page.wait_for_timeout(3_000)
        if DEBUG: shot(page, "09_painel_tarefas")

        if link is None:
            # Diagnóstico: registra todos os links/botões visíveis com CSV/Baixar/download
            try:
                cands = page.locator("a, button, [role='link'], [role='button']")
                achados = []
                for i in range(min(cands.count(), 200)):
                    el = cands.nth(i)
                    try:
                        if not el.is_visible():
                            continue
                        txt = (el.inner_text() or "").strip()
                        al = el.get_attribute("aria-label") or ""
                        if any(p in (txt + al).lower() for p in ("csv", "baixar", "download", "tarefa")):
                            achados.append(f"[{el.evaluate('e=>e.tagName')}] txt='{txt[:40]}' aria='{al[:40]}'")
                    except Exception:
                        continue
                log.error("Candidatos visíveis (CSV/baixar/download/tarefa): " + " | ".join(achados[:25]))
            except Exception:
                pass
            falha(page, "download", "o link 'Baixar CSV' não apareceu no painel de Tarefas em ~2,5 min")

        # Clica no link → captura o download real
        destino = f"{DIR_OFICIAL}/LogSearchResults_{datetime.now().strftime('%Y-%m-%d_%H%M')}.csv"
        try:
            with page.expect_download(timeout=120_000) as dl_info:
                link.click()
            dl_info.value.save_as(destino)
        except PWTimeout:
            falha(page, "download", "cliquei em 'Baixar CSV' mas o download não começou")

        tamanho = os.path.getsize(destino)
        log.info(f"CSV salvo: {destino} ({tamanho} bytes)")

        # sucesso: atualiza marcador e limpa flag de sessão
        with open(ULTIMO_OK, "w") as f:
            f.write(datetime.now().isoformat())
        if os.path.exists(FLAG_SESSAO):
            os.remove(FLAG_SESSAO)

        print(f"OK: exportação oficial salva em {destino} ({tamanho} bytes)")
        browser.close()


if __name__ == "__main__":
    main()
