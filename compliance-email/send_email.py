import sys, requests
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
message = f"Email de teste de compliance - {label}"
log_msg(f"Iniciando - Label: {label}")

r = requests.post("https://api.proxynova.com/v1/send_email",
    json={"to":"compliance@beng.eng.br","from":"Anonymous","subject":label,"message":message},
    headers={"Referer":"https://www.proxynova.com/tools/send-anonymous-email/","Origin":"https://www.proxynova.com"})

log_msg(f"Status: {r.status_code} - {r.text}")
log_msg("SUCESSO!" if r.status_code == 200 else "ERRO")
