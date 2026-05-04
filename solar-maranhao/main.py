#!/usr/bin/env python3
"""
Sistema de Relatório Mensal de Geração Solar - Maranhão
Gera relatório PDF profissional a partir de dados diários do Excel.

Uso:
    python3 main.py [--month YYYY-MM] [--no-email] [--dry-run]
"""
import argparse
import os
import sys
from datetime import date, timedelta

from config import PLANTS, PLANT_IDS, OUTPUT_DIR, EXCEL_PATH
from data_loader import load_workbook, load_all_monthly_totals, load_daily_data
from kpi_calculator import calculate_all_kpis
from chart_generator import generate_all_charts
from ai_analyst import generate_analysis
from report_builder import build_report
from email_sender import send_report_email

MESES_PT_FULL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def get_previous_month():
    """Retorna (ano, mês) do mês anterior."""
    today = date.today()
    first_of_month = today.replace(day=1)
    last_month = first_of_month - timedelta(days=1)
    return last_month.year, last_month.month


def main():
    parser = argparse.ArgumentParser(description="Gerador de Relatório Mensal de Geração Solar")
    parser.add_argument("--month", type=str, help="Mês alvo no formato YYYY-MM (default: mês anterior)")
    parser.add_argument("--no-email", action="store_true", help="Gera PDF sem enviar email")
    parser.add_argument("--dry-run", action="store_true", help="Calcula KPIs sem gerar PDF")
    parser.add_argument("--excel", type=str, default=EXCEL_PATH, help="Caminho do Excel")
    args = parser.parse_args()

    # Determinar mês alvo
    if args.month:
        try:
            parts = args.month.split("-")
            target_year, target_month = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            print(f"Erro: formato de mês inválido '{args.month}'. Use YYYY-MM.")
            sys.exit(1)
    else:
        target_year, target_month = get_previous_month()

    month_name = MESES_PT_FULL.get(target_month, str(target_month))
    print(f"=== Relatório Mensal de Geração Solar ===")
    print(f"Período: {month_name}/{target_year}")
    print()

    # 1. Carregar dados
    print("[1/6] Carregando dados do Excel...")
    wb = load_workbook(args.excel)
    monthly_totals = load_all_monthly_totals(wb, target_year)
    daily_data = load_daily_data(wb, target_year, target_month)
    print(f"  - {len(monthly_totals)} meses de dados históricos carregados")
    print(f"  - {len(daily_data)} dias de dados diários para {month_name}/{target_year}")

    # 2. Calcular KPIs
    print("[2/6] Calculando KPIs...")
    kpis = calculate_all_kpis(monthly_totals, daily_data, target_year, target_month)

    # Resumo rápido
    total = kpis["month_generation"]["total"]
    meta_total = 14000 * len(PLANT_IDS)
    print(f"  - Geração total: {total:,.0f} kWh ({total/meta_total*100:.1f}% da meta)")
    print(f"  - Ranking: {' > '.join(PLANTS[p]['name'] for p in kpis['ranking'])}")
    print(f"  - Impacto financeiro: R$ {kpis['financial']['total']['lost_revenue_brl']:,.0f}")

    if args.dry_run:
        print("\n[dry-run] Encerrando sem gerar PDF.")
        return

    # 3. Gerar gráficos
    print("[3/6] Gerando gráficos...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    charts = generate_all_charts(kpis, daily_data, monthly_totals, OUTPUT_DIR)
    print(f"  - {len(charts)} gráficos gerados")

    # 4. Gerar análises (IA)
    print("[4/6] Gerando análises (Claude AI)...")
    analysis = generate_analysis(kpis, monthly_totals)
    ai_source = "Claude API" if os.environ.get("ANTHROPIC_API_KEY") else "fallback (sem API key)"
    print(f"  - Análises geradas via {ai_source}")

    # 5. Montar PDF
    print("[5/6] Montando relatório PDF...")
    filename = f"Relatorio_Solar_Maranhao_{target_year}_{target_month:02d}.pdf"
    output_path = os.path.join(OUTPUT_DIR, filename)
    build_report(kpis, analysis, charts, output_path)
    print(f"  - PDF salvo: {output_path}")

    # 6. Email
    if not args.no_email:
        print(f"[6/6] Enviando email...")
        try:
            send_report_email(output_path, target_year, target_month)
        except Exception as e:
            print(f"  - Erro ao enviar email: {e}")
    else:
        print("[6/6] Email desabilitado (--no-email).")

    print(f"\nRelatório concluído: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
