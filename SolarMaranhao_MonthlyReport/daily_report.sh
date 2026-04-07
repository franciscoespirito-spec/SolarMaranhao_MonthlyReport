#!/bin/bash
# Gera e envia diariamente o relatório PDF de geração solar.
# Executado às 11h UTC (08h BRT) pelo timer solar-daily-report.timer.
# Detecta automaticamente o mês com dados mais recentes na planilha.

set -euo pipefail

PROJ="/root/projetos/SolarMaranhao_MonthlyReport"
LOG="$PROJ/daily_report.log"

# Carregar variáveis de ambiente (API keys, senha Gmail)
if [ -f /root/.env_solar ]; then
    set -a
    source /root/.env_solar
    set +a
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Iniciando geração do relatório diário ===" >> "$LOG"

cd "$PROJ"

# Sempre usa o mês anterior consolidado (mês corrente ainda não está encerrado)
TARGET=$(python3 - <<'EOF'
import datetime
today = datetime.date.today()
first_of_month = today.replace(day=1)
prev = first_of_month - datetime.timedelta(days=1)
print(f"{prev.year}-{prev.month:02d}")
EOF
)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Mês detectado: $TARGET" >> "$LOG"

# Gerar relatório e enviar email
python3 main.py --month "$TARGET" 2>&1 | tee -a "$LOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Concluído ===" >> "$LOG"
