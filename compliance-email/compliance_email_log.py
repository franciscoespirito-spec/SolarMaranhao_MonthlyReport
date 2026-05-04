#!/usr/bin/env python3
"""
Rotina Mensal - Pesquisa de Logs de Compliance
Usa a Gmail API para listar e-mails recebidos por compliance@beng.eng.br.
Captura TODOS os e-mails recebidos no mês (ISO 37301).

Uso normal (mês corrente):
    python3 compliance_email_log.py

Uso para mês específico:
    python3 compliance_email_log.py 2026 4
"""

import csv
import os
import sys
import logging
from calendar import monthrange
from datetime import datetime, date, timezone, timedelta
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ── Configurações ─────────────────────────────────────────────────────────────
SERVICE_ACCOUNT_FILE = "/root/projetos/compliance-email/credentials/service_account.json"
DELEGATED_USER       = "francisco.santo@beng.eng.br"
COMPLIANCE_EMAIL     = "compliance@beng.eng.br"
DRIVE_FOLDER_ID      = "1Uh6znuDlVWigCnOjoZEeQVVIojjqWjZy"
LOG_FILE             = "/root/logs/compliance_email_log.log"
DOWNLOAD_DIR         = "/root/logs"

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs("/root/logs", exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger()


def get_period(year=None, month=None):
    """Retorna datas de início e fim do mês."""
    if year and month:
        ref = date(year, month, 1)
    else:
        ref = date.today()
    first_day = date(ref.year, ref.month, 1)
    last_day  = date(ref.year, ref.month, monthrange(ref.year, ref.month)[1])
    start_time = datetime(first_day.year, first_day.month, first_day.day,
                          0, 0, 0, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time   = datetime(last_day.year, last_day.month, last_day.day,
                          23, 59, 59, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return first_day, last_day, start_time, end_time


def fetch_email_logs(year: int, month: int, dest_path: str) -> int:
    """
    Lista e-mails recebidos por compliance@beng.eng.br via Gmail API.
    Retorna o número de mensagens encontradas.
    """
    first_day, last_day, _, _ = get_period(year, month)
    after  = first_day.strftime("%Y/%m/%d")
    before = (last_day + timedelta(days=1)).strftime("%Y/%m/%d")
    query  = f"after:{after} before:{before}"
    log.info(f"Gmail API: query={query}")

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=GMAIL_SCOPES
    ).with_subject(COMPLIANCE_EMAIL)
    service = build("gmail", "v1", credentials=creds)

    # Listar IDs de todas as mensagens do período
    msg_ids = []
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId=COMPLIANCE_EMAIL,
            q=query,
            maxResults=500,
            pageToken=page_token,
        ).execute()
        msg_ids.extend(resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    log.info(f"Total de mensagens encontradas: {len(msg_ids)}")

    # Buscar metadados de cada mensagem
    rows = []
    for msg in msg_ids:
        detail = service.users().messages().get(
            userId=COMPLIANCE_EMAIL,
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        headers = {h["name"]: h["value"]
                   for h in detail.get("payload", {}).get("headers", [])}
        rows.append({
            "timestamp":  headers.get("Date", ""),
            "from":       headers.get("From", ""),
            "to":         headers.get("To", ""),
            "subject":    headers.get("Subject", ""),
            "message_id": msg["id"],
        })

    # Salvar CSV
    fieldnames = ["timestamp", "from", "to", "subject", "message_id"]
    with open(dest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"Gmail API: {len(rows)} mensagens salvas em {dest_path}")
    return len(rows)


def upload_to_drive(drive_service, csv_path, filename):
    """Faz upload do CSV para a pasta do Drive."""
    file_metadata = {
        "name": filename,
        "parents": [DRIVE_FOLDER_ID],
    }
    media = MediaFileUpload(csv_path, mimetype="text/csv")
    uploaded = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name",
        supportsAllDrives=True,
    ).execute()
    log.info(f"Upload concluído: {uploaded['name']} (ID: {uploaded['id']})")
    return uploaded


def main():
    log.info("=" * 60)
    log.info("Iniciando rotina de compliance email log (Gmail API)")

    year  = int(sys.argv[1]) if len(sys.argv) > 1 else None
    month = int(sys.argv[2]) if len(sys.argv) > 2 else None

    first_day, last_day, _, _ = get_period(year, month)
    year  = first_day.year
    month = first_day.month
    log.info(f"Período: {first_day} a {last_day}")

    now = datetime.now()
    csv_filename = f"compliance_logs_{now.strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    csv_path = f"{DOWNLOAD_DIR}/{csv_filename}"

    total = fetch_email_logs(year, month, csv_path)

    if total == 0:
        log.info("Nenhuma mensagem encontrada no período.")
        print("AVISO: Nenhum e-mail encontrado no período.")

    drive_creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=DRIVE_SCOPES
    ).with_subject(DELEGATED_USER)
    drive_service = build("drive", "v3", credentials=drive_creds)
    upload_to_drive(drive_service, csv_path, csv_filename)

    log.info("Rotina concluída com sucesso.")
    print(f"OK: {total} registros exportados → Drive: {csv_filename}")


if __name__ == "__main__":
    main()
