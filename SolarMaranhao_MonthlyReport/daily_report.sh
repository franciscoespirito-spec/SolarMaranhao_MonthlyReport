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

# Detecta o mês mais recente com dados na planilha
TARGET=$(python3 - <<'EOF'
from data_loader import load_workbook, load_all_monthly_totals
wb = load_workbook()
df = load_all_monthly_totals(wb)
nonzero = df[df["total"] > 0]
if nonzero.empty:
    import datetime
    d = datetime.date.today()
    print(f"{d.year}-{d.month:02d}")
else:
    last = nonzero.iloc[-1]
    print(f"{int(last['year'])}-{int(last['month']):02d}")
EOF
)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Mês detectado: $TARGET" >> "$LOG"

# Gerar relatório e enviar email
python3 main.py --month "$TARGET" 2>&1 | tee -a "$LOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Concluído ===" >> "$LOG"
