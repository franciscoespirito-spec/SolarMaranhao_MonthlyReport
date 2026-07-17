#!/usr/bin/env python3
"""
Rotina Mensal - Log de E-mails de Compliance
Usa Admin SDK Reports API para listar e-mails recebidos por compliance@beng.eng.br.
Mesma fonte de dados do Google Admin Console > Relatórios > Pesquisa de logs de e-mail.

Uso normal (mês anterior, já fechado — é o que o cron do dia 1 usa):
    python3 compliance_email_log.py

Uso para mês específico:
    python3 compliance_email_log.py 2026 4
"""

import csv
import os
import re
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
LOG_FILE             = "/root/projetos/compliance-email/logs/compliance_email_log.log"
DOWNLOAD_DIR         = "/root/projetos/compliance-email/logs"

ADMIN_SCOPES = ["https://www.googleapis.com/auth/admin.reports.audit.readonly"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs("/root/projetos/compliance-email/logs", exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger()


def get_period(year=None, month=None):
    if year and month:
        ref = date(year, month, 1)
    else:
        # Sem argumentos: usa o MÊS ANTERIOR (fechado). O cron roda no dia 1 às 6h UTC,
        # antes do e-mail marcador do mês novo (9h UTC) — o mês corrente estaria vazio.
        hoje = date.today()
        ref = date(hoje.year, hoje.month, 1) - timedelta(days=1)
    first_day = date(ref.year, ref.month, 1)
    last_day  = date(ref.year, ref.month, monthrange(ref.year, ref.month)[1])
    start_time = datetime(first_day.year, first_day.month, first_day.day,
                          0, 0, 0, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time   = datetime(last_day.year, last_day.month, last_day.day,
                          23, 59, 59, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return first_day, last_day, start_time, end_time


def get_nested(parameters, chave):
    """Extrai os parâmetros aninhados (messageValue) de um parâmetro do evento.

    Nos eventos de Gmail do Reports API, a informação real fica aninhada dentro de
    'message_info' / 'event_info' (messageValue.parameter), e não no nível de cima.
    """
    for p in parameters:
        if p.get("name") == chave and "messageValue" in p:
            result = {}
            for q in p["messageValue"].get("parameter", []):
                name = q.get("name")
                if "value" in q:
                    result[name] = q["value"]
                elif "boolValue" in q:
                    result[name] = q["boolValue"]
                elif "intValue" in q:
                    result[name] = q["intValue"]
                elif "multiValue" in q:
                    result[name] = q["multiValue"]
            return result
    return {}


def map_status(event_info, message_info):
    """Determina o status da entrega a partir dos campos aninhados."""
    if message_info.get("is_spam") is True:
        return "Spam"
    success = event_info.get("success")
    if success is True:
        return "Entregue"
    if success is False:
        return "Falhou"
    return "Desconhecido"


STATUS_PRIORITY = {"Entregue": 3, "Spam": 2, "Falhou": 1, "Desconhecido": 0}


def fetch_email_logs(year: int, month: int, dest_path: str) -> int:
    """
    Consulta Admin SDK Reports API para obter e-mails recebidos por compliance@.
    Retorna o número de mensagens únicas encontradas.
    """
    first_day, last_day, start_time, end_time = get_period(year, month)
    log.info(f"Admin SDK Reports API: período {first_day} a {last_day}")

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=ADMIN_SCOPES
    ).with_subject(DELEGATED_USER)
    service = build("admin", "reports_v1", credentials=creds)

    # A API limita cada consulta a no máximo 30 dias — meses de 31 dias falhavam.
    # Solução: dividir o mês em 2 blocos (dia 1–15 e dia 16–fim) e somar os resultados.
    meio_fim = date(first_day.year, first_day.month, 15)
    meio_ini = date(first_day.year, first_day.month, 16)
    blocos = [(first_day, meio_fim), (meio_ini, last_day)]

    agora = datetime.now(timezone.utc)
    activities = []
    for bloco_ini, bloco_fim in blocos:
        start_dt = datetime(bloco_ini.year, bloco_ini.month, bloco_ini.day,
                            0, 0, 0, tzinfo=timezone.utc)
        end_dt   = datetime(bloco_fim.year, bloco_fim.month, bloco_fim.day,
                            23, 59, 59, tzinfo=timezone.utc)
        if start_dt > agora:
            continue  # bloco totalmente no futuro — nada a consultar
        if end_dt > agora:
            end_dt = agora  # não pedir dados do futuro
        start_time = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time   = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        log.info(f"  Bloco {bloco_ini} a {bloco_fim}: startTime={start_time}  endTime={end_time}")

        # Buscar todas as atividades de Gmail do domínio no bloco
        page_token = None
        page = 0
        while True:
            page += 1
            resp = service.activities().list(
                userKey="all",
                applicationName="gmail",
                startTime=start_time,
                endTime=end_time,
                maxResults=1000,
                pageToken=page_token,
            ).execute()

            batch = resp.get("items", [])
            activities.extend(batch)
            log.info(f"  Página {page}: {len(batch)} atividades (total acumulado: {len(activities)})")

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    log.info(f"Total de atividades brutas do domínio: {len(activities)}")

    # Filtrar e processar apenas e-mails recebidos por compliance@
    messages = {}  # message_id → melhor evento

    for activity in activities:
        id_time = activity.get("id", {}).get("time", "")
        for event in activity.get("events", []):
            # Só interessam eventos de entrega de mensagem
            if event.get("name") != "delivery":
                continue

            message_info = get_nested(event.get("parameters", []), "message_info")
            event_info   = get_nested(event.get("parameters", []), "event_info")

            # Filtrar destinatário: compliance@ aparece dentro de flattened_destinations
            # (ex: "gmail-ui::compliance@beng.eng.br")
            destinos = str(message_info.get("flattened_destinations", "") or "")
            if COMPLIANCE_EMAIL.lower() not in destinos.lower():
                continue

            msg_id  = message_info.get("rfc2822_message_id", "") or id_time
            sender  = str(message_info.get("flattened_sources", "")
                          or message_info.get("source", "") or "")
            subject = message_info.get("subject", "")
            status  = map_status(event_info, message_info)

            # Manter o evento de maior prioridade de status por message_id
            existing = messages.get(msg_id)
            if existing is None or STATUS_PRIORITY.get(status, 0) > STATUS_PRIORITY.get(existing["status"], 0):
                messages[msg_id] = {
                    "data":     id_time,
                    "remetente": sender,
                    "assunto":  subject,
                    "status":   status,
                }

    log.info(f"E-mails únicos recebidos por {COMPLIANCE_EMAIL}: {len(messages)}")

    # Ordenar por data
    rows = sorted(messages.values(), key=lambda r: r["data"])

    # Formatar data para leitura humana
    for row in rows:
        try:
            dt = datetime.fromisoformat(row["data"].replace("Z", "+00:00"))
            row["data"] = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    # Salvar CSV
    fieldnames = ["data", "remetente", "assunto", "status"]
    with open(dest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"CSV salvo: {dest_path} ({len(rows)} linhas)")
    return len(rows)


def upload_to_drive(drive_service, csv_path, filename):
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
    log.info("Iniciando rotina de compliance email log (Admin SDK Reports API)")

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
        print("AVISO: Nenhum e-mail encontrado para compliance@ no período.")

    drive_creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=DRIVE_SCOPES
    ).with_subject(DELEGATED_USER)
    drive_service = build("drive", "v3", credentials=drive_creds)
    upload_to_drive(drive_service, csv_path, csv_filename)

    log.info("Rotina concluída com sucesso.")
    print(f"OK: {total} e-mails exportados → Drive: {csv_filename}")


if __name__ == "__main__":
    main()
