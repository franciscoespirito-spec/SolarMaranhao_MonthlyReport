#!/usr/bin/env python3
"""
Salva a sessão autenticada do Google Admin Console (login manual com 2FA).
Execute quando a sessão expirar (o status-vps avisa com ⚠️).

── Pré-requisito no PC Windows (feito uma vez; já foi feito em maio/2026) ──
  1. Instalar VcXsrv: https://sourceforge.net/projects/vcxsrv/
  2. Abrir XLaunch → Multiple windows → Start no client → marcar "Disable access control"

── No PowerShell do PC ──
  ssh -X root@72.61.41.220

── No terminal SSH que abrir (VPS) ──
  /root/venv_email/bin/python3 /root/projetos/compliance-email/save_session.py
"""
import os
import sys
from playwright.sync_api import sync_playwright

SESSION_PATH = "/root/projetos/compliance-email/credentials/admin_session.json"
FLAG_SESSAO = "/root/projetos/compliance-email/logs/oficial/SESSAO_EXPIRADA.flag"


def main():
    print("=" * 60)
    print("Setup de Sessão — Google Admin Console")
    print("=" * 60)

    if not os.environ.get("DISPLAY"):
        print()
        print("ERRO: Sem tela gráfica (DISPLAY vazio).")
        print("Este script precisa abrir um navegador na sua tela.")
        print("Conecte com:  ssh -X root@72.61.41.220  (com o VcXsrv aberto no PC)")
        sys.exit(1)

    print()
    print("1. Um navegador vai abrir na sua tela (via VcXsrv).")
    print("2. Faça login com francisco.santo@beng.eng.br (inclusive 2FA).")
    print("3. Quando chegar ao painel do Admin Console, aguarde.")
    print("4. A sessão será salva e o navegador fechará sozinho.")
    print()

    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--start-maximized"],
        )
        context = browser.new_context(
            viewport=None,
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.goto("https://admin.google.com")

        print("Aguardando você completar o login... (até 10 minutos)")
        try:
            # Espera chegar de fato ao painel (sai de accounts.google.com)
            page.wait_for_url(
                lambda url: "admin.google.com" in url and "accounts.google" not in url,
                timeout=600_000,
            )
        except Exception:
            print("ERRO: Tempo esgotado ou login não completado.")
            browser.close()
            sys.exit(1)

        page.wait_for_timeout(3_000)  # buffer para os cookies consolidarem
        context.storage_state(path=SESSION_PATH)
        os.chmod(SESSION_PATH, 0o600)
        browser.close()

    # Limpa o aviso de sessão expirada, se existir
    if os.path.exists(FLAG_SESSAO):
        os.remove(FLAG_SESSAO)

    print(f"\n✅ Sessão salva com segurança em: {SESSION_PATH}")
    print("\nAgora teste a exportação oficial:")
    print("  /root/venv_email/bin/python3 /root/projetos/compliance-email/exportar_oficial.py")


if __name__ == "__main__":
    main()
