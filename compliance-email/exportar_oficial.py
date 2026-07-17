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
        log.info("Etapa 3: selecionando período pré-definido")
        seletor_periodo = None
        for tentativa in [
            lambda: page.get_by_label("Período da mensagem", exact=False),
            lambda: page.get_by_label("Message period", exact=False),
            lambda: page.locator("[aria-label*='período' i]"),
            lambda: page.locator("[aria-label*='period' i]"),
            lambda: page.get_by_role("combobox").first,
        ]:
            try:
                loc = tentativa()
                if loc.count() > 0 and loc.first.is_visible():
                    seletor_periodo = loc.first
                    break
            except Exception:
                continue
        if seletor_periodo is None:
            falha(page, "periodo", "não achei o seletor de período — a tela pode ter mudado")
        seletor_periodo.click()
        page.wait_for_timeout(1_500)
        if DEBUG: shot(page, "03_menu_periodo_aberto")

        # Registra as opções vistas (para depuração caso o Google mude a tela)
        try:
            todas = page.get_by_role("option")
            textos = [todas.nth(i).inner_text().strip() for i in range(todas.count())]
            log.info(f"Opções de período encontradas: {textos}")
        except Exception:
            textos = []

        # Clica APENAS na opção VISÍVEL "Últimos 7 dias" (o Google duplica itens ocultos)
        def achar_visivel():
            candidatos = page.locator(SELETOR_OPCAO_7DIAS)
            for i in range(candidatos.count()):
                if candidatos.nth(i).is_visible():
                    return candidatos.nth(i)
            return None

        alvo = achar_visivel()
        if alvo is None:
            # o menu pode ter fechado — reabre e tenta de novo
            seletor_periodo.click()
            page.wait_for_timeout(1_500)
            alvo = achar_visivel()
        if alvo is None:
            falha(page, "preset", f"não achei opção VISÍVEL 'Últimos 7 dias'. Opções vistas: {textos}")
        log.info("Período escolhido: 'Últimos 7 dias'")
        alvo.click()
        page.wait_for_timeout(1_000)
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
        page.wait_for_timeout(2_000)
        if DEBUG: shot(page, "06_menu_download")

        # se abrir um menu/diálogo pedindo o formato, escolhe CSV
        destino = f"{DIR_OFICIAL}/LogSearchResults_{datetime.now().strftime('%Y-%m-%d_%H%M')}.csv"
        try:
            with page.expect_download(timeout=120_000) as dl_info:
                opcao_csv = page.locator(
                    "[role='menuitem']:has-text('CSV'), [role='option']:has-text('CSV'), "
                    "button:has-text('CSV'), label:has-text('CSV')"
                )
                if opcao_csv.count() > 0 and opcao_csv.first.is_visible():
                    opcao_csv.first.click()
                    # pode haver um botão de confirmação depois da escolha
                    conf = page.get_by_role("button", name="Fazer o download")
                    if conf.count() > 0 and conf.first.is_visible():
                        conf.first.click()
            dl_info.value.save_as(destino)
        except PWTimeout:
            falha(page, "download", "o download não começou em 2 minutos")

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
