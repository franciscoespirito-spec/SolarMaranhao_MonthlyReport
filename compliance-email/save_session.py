#!/usr/bin/env python3
"""
Salva a sessão autenticada do Google Admin Console.
Execute UMA VEZ via X11 Forwarding para fazer login com 2FA no VPS.

Pré-requisito no PC Windows:
  1. Instalar VcXsrv: https://sourceforge.net/projects/vcxsrv/
  2. Abrir XLaunch → Multiple windows → Start no client → marcar "Disable access control"

No PowerShell do PC:
  ssh -X root@72.61.41.220

No terminal SSH (VPS):
  source /root/venv_email/bin/activate
  python3 /root/scripts/save_session.py
"""
import os
import sys
from playwright.sync_api import sync_playwright

SESSION_PATH = "/root/scripts/credentials/admin_session.json"


def main():
    print("=" * 60)
    print("Setup de Sessão — Google Admin Console")
    print("=" * 60)
    print()
    print("1. Um browser vai abrir na sua tela via X11.")
    print("2. Faça login com francisco.santo@beng.eng.br (inclusive 2FA).")
    print("3. Quando chegar ao painel do Admin Console, aguarde.")
    print("4. A sessão será salva e o browser fechará automaticamente.")
    print()
    print(f"Arquivo de saída: {SESSION_PATH}")
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

        print("Aguardando login... (até 10 minutos)")
        print("Faça login no browser que abriu na janela VNC.")

        try:
            page.wait_for_url(
                "**/admin.google.com/**",
                timeout=600_000,
            )
        except Exception:
            print("ERRO: Tempo esgotado ou login não completado.")
            browser.close()
            sys.exit(1)

        # Buffer para cookies consolidarem
        page.wait_for_timeout(3_000)

        context.storage_state(path=SESSION_PATH)
        print(f"\nSessão salva com sucesso em: {SESSION_PATH}")
        browser.close()

    print()
    print("Pronto! Agora teste o script principal:")
    print("  python3 /root/scripts/compliance_email_log.py 2026 4")


if __name__ == "__main__":
    main()
