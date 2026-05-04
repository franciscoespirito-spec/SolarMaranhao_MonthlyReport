#!/usr/bin/env python3
import sys
import requests
from datetime import datetime
from pathlib import Path

log_file = Path("/root/logs/email_test.log")
log_file.parent.mkdir(exist_ok=True)

def log_msg(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(log_file, "a") as f:
        f.write(line + "\n")

now = datetime.now()
label = f"Teste_{now.year}_{now.month:02d}"

log_msg(f"Iniciando - Label: {label}")

try:
    response = requests.post(
        "https://api.proxynova.com/v1/send_email",
        json={
            "to": "compliance@beng.eng.br",
            "from": "Anonymous",
            "subject": label,
            "message": label
        },
        headers={
            "Referer": "https://www.proxynova.com/tools/send-anonymous-email/",
            "Origin": "https://www.proxynova.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    )

    log_msg(f"Status: {response.status_code}")
    log_msg(f"Resposta: {response.text}")

    if response.status_code == 200:
        log_msg("SUCESSO!")
         else:
        log_msg("ERRO no envio")
        sys.exit(1)

except Exception as e:
    log_msg(f"ERRO: {e}")
    sys.exit(1)