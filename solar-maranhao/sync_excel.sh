#!/bin/bash
# Sincroniza a planilha do Google Drive compartilhado para o servidor.
# Executado diariamente às 6h UTC pelo timer solar-sync-excel.timer.

REMOTE="gdrive1:15. Operação e Manutenção"
LOCAL="/root/projetos/SolarMaranhao_MonthlyReport"
FILE="Historico Geracao Solar Maranhao 2026.xlsx"
LOG="$LOCAL/sync_excel.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando sincronização do Excel..." >> "$LOG"

rclone copy "$REMOTE/$FILE" "$LOCAL/" \
    --update \
    --log-file="$LOG" \
    --log-level INFO

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sincronização concluída com sucesso." >> "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERRO na sincronização (exit code $EXIT_CODE)." >> "$LOG"
fi

exit $EXIT_CODE
