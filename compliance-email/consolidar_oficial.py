#!/usr/bin/env python3
"""
Consolidação mensal dos exports oficiais do Email Log Search.

Junta todos os CSVs baixados pelo exportar_oficial.py (execuções semanais),
filtra apenas as linhas do mês desejado, remove duplicados (as janelas de
"últimos 30 dias" se sobrepõem de propósito) e gera o CSV consolidado do mês,
que é enviado ao Google Drive.

Uso:
    python3 consolidar_oficial.py            # mês anterior (uso do cron, dia 1)
    python3 consolidar_oficial.py 2026-07    # mês específico
"""
import csv
import glob
import importlib.util
import logging
import os
import sys
from datetime import date, timedelta

BASE        = "/root/projetos/compliance-email"
DIR_OFICIAL = f"{BASE}/logs/oficial"
LOG_FILE    = f"{DIR_OFICIAL}/consolidar_oficial.log"

os.makedirs(DIR_OFICIAL, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger()


def mes_alvo():
    if len(sys.argv) > 1:
        ano, mes = sys.argv[1].split("-")
        return int(ano), int(mes)
    ontem_do_dia1 = date.today().replace(day=1) - timedelta(days=1)
    return ontem_do_dia1.year, ontem_do_dia1.month


def ler_csv(caminho):
    """Lê um CSV oficial tolerando UTF-8 (com/sem BOM) e Latin-1."""
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with open(caminho, encoding=enc, newline="") as f:
                linhas = list(csv.DictReader(f))
            return linhas
        except UnicodeDecodeError:
            continue
    return []


def main():
    ano, mes = mes_alvo()
    prefixo = f"{ano}/{mes:02d}/"          # formato das datas oficiais: 2026/07/17 ...
    log.info("=" * 60)
    log.info(f"Consolidando mês {ano}-{mes:02d}")

    arquivos = sorted(glob.glob(f"{DIR_OFICIAL}/LogSearchResults_*.csv"))
    if not arquivos:
        print("AVISO: nenhum export oficial encontrado ainda (exportar_oficial.py já rodou?).")
        log.warning("Nenhum LogSearchResults_*.csv em logs/oficial")
        sys.exit(0)

    vistos = set()
    linhas_mes = []
    cabecalho = None
    for arq in arquivos:
        linhas = ler_csv(arq)
        log.info(f"{os.path.basename(arq)}: {len(linhas)} linhas")
        for r in linhas:
            if cabecalho is None:
                cabecalho = list(r.keys())
            data_evento = (r.get("Event date") or r.get("Start date") or "")
            if not data_evento.startswith(prefixo):
                continue
            chave = (r.get("Message ID", ""), data_evento,
                     r.get("Event status", ""), r.get("Event target", ""))
            if chave in vistos:
                continue
            vistos.add(chave)
            linhas_mes.append(r)

    if not linhas_mes:
        print(f"AVISO: nenhum dado oficial do mês {ano}-{mes:02d} nos exports acumulados.")
        print("O relatório via API (reserva) continua valendo para este mês.")
        log.warning(f"0 linhas do mês {ano}-{mes:02d}")
        sys.exit(0)

    linhas_mes.sort(key=lambda r: (r.get("Event date") or r.get("Start date") or ""))
    mensagens = {r.get("Message ID", "") for r in linhas_mes}

    destino = f"{DIR_OFICIAL}/compliance_oficial_{ano}-{mes:02d}.csv"
    with open(destino, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cabecalho, extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas_mes)
    log.info(f"Consolidado: {destino} ({len(linhas_mes)} linhas, {len(mensagens)} mensagens)")

    # Upload ao Drive reutilizando a função do relatório via API
    spec = importlib.util.spec_from_file_location("cel", f"{BASE}/compliance_email_log.py")
    cel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cel)
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        cel.SERVICE_ACCOUNT_FILE, scopes=cel.DRIVE_SCOPES
    ).with_subject(cel.DELEGATED_USER)
    drive = build("drive", "v3", credentials=creds)
    cel.upload_to_drive(drive, destino, os.path.basename(destino))

    print(f"OK: {len(mensagens)} mensagens ({len(linhas_mes)} linhas) → Drive: {os.path.basename(destino)}")


if __name__ == "__main__":
    main()
