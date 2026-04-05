"""
Geração de gráficos matplotlib para o relatório de geração solar.
Salva PNGs em diretório temporário para embedar no PDF.
"""
import os
import tempfile
from calendar import month_abbr

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from config import PLANTS, PLANT_IDS, PLANT_COLORS, TARGET_MONTHLY_KWH, TARGET_TOLERANCE

# Meses em português
MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

MESES_PT_FULL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def _setup_style():
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "#FAFAFA",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.labelsize": 9,
        "figure.dpi": 150,
    })


def generate_all_charts(kpis, daily_df, monthly_totals_df, output_dir=None):
    """
    Gera todos os gráficos e retorna dict com caminhos dos PNGs.
    """
    _setup_style()
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="solar_charts_")

    charts = {}
    charts["monthly_generation"] = _chart_monthly_generation(kpis, output_dir)
    charts["ytd_trend"] = _chart_ytd_trend(kpis, monthly_totals_df, output_dir)
    charts["ranking"] = _chart_ranking(kpis, output_dir)
    charts["daily_variation"] = _chart_daily_variation(daily_df, kpis, output_dir)
    charts["yoy_comparison"] = _chart_yoy_comparison(kpis, monthly_totals_df, output_dir)

    plt.close("all")
    return charts


def _chart_monthly_generation(kpis, output_dir):
    """Barras agrupadas: geração mensal por usina com linha de meta."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    names = [PLANTS[pid]["name"] for pid in PLANT_IDS]
    values = [kpis["month_generation"][pid] for pid in PLANT_IDS]
    colors = [PLANT_COLORS[pid] for pid in PLANT_IDS]

    bars = ax.bar(names, values, color=colors, width=0.6, edgecolor="white", linewidth=0.5)

    # Linha de meta
    ax.axhline(y=TARGET_MONTHLY_KWH, color="#E74C3C", linestyle="--", linewidth=1.5, label=f"Meta ({TARGET_MONTHLY_KWH:,.0f} kWh)")

    # Faixa de tolerância
    lower = TARGET_MONTHLY_KWH * (1 - TARGET_TOLERANCE)
    upper = TARGET_MONTHLY_KWH * (1 + TARGET_TOLERANCE)
    ax.axhspan(lower, upper, alpha=0.08, color="#F39C12", label=f"Tolerância ±{TARGET_TOLERANCE:.0%}")

    # Valores nas barras
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 100,
                f"{val:,.0f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

    month_name = MESES_PT_FULL.get(kpis["target_month"], "")
    ax.set_title(f"Geração Mensal por Usina - {month_name}/{kpis['target_year']}")
    ax.set_ylabel("kWh")
    ax.legend(fontsize=7, loc="upper right")
    ax.set_ylim(0, max(values + [upper]) * 1.15)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    fig.tight_layout()
    path = os.path.join(output_dir, "monthly_generation.png")
    fig.savefig(path, bbox_inches="tight")
    return path


def _chart_ytd_trend(kpis, monthly_totals_df, output_dir):
    """Linhas: geração mês a mês no ano corrente."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    year = kpis["target_year"]
    year_data = monthly_totals_df[
        (monthly_totals_df["year"] == year) &
        (monthly_totals_df["month"] <= kpis["target_month"])
    ].sort_values("month")

    if year_data.empty:
        return None

    months = [MESES_PT.get(m, str(m)) for m in year_data["month"]]

    for pid in PLANT_IDS:
        ax.plot(months, year_data[pid].values, marker="o", markersize=4,
                color=PLANT_COLORS[pid], linewidth=1.8, label=PLANTS[pid]["name"])

    ax.axhline(y=TARGET_MONTHLY_KWH, color="#E74C3C", linestyle="--", linewidth=1, alpha=0.7, label="Meta")

    ax.set_title(f"Tendência de Geração Mensal - {year}")
    ax.set_ylabel("kWh")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    fig.tight_layout()
    path = os.path.join(output_dir, "ytd_trend.png")
    fig.savefig(path, bbox_inches="tight")
    return path


def _chart_ranking(kpis, output_dir):
    """Barras horizontais: ranking de usinas com cores por status."""
    fig, ax = plt.subplots(figsize=(7, 2.8))

    ranking = kpis["ranking"]
    names = [PLANTS[pid]["name"] for pid in ranking]
    values = [kpis["month_generation"][pid] for pid in ranking]

    color_map = {"verde": "#27AE60", "amarelo": "#F39C12", "vermelho": "#E74C3C"}
    colors = [color_map.get(kpis["gap_vs_target"][pid]["status"], "#95A5A6") for pid in ranking]

    bars = ax.barh(names, values, color=colors, height=0.5, edgecolor="white")

    ax.axvline(x=TARGET_MONTHLY_KWH, color="#E74C3C", linestyle="--", linewidth=1.5, alpha=0.7)

    for bar, val, pid in zip(bars, values, ranking):
        gap = kpis["gap_vs_target"][pid]["percent"]
        sign = "+" if gap >= 0 else ""
        ax.text(bar.get_width() + 100, bar.get_y() + bar.get_height() / 2,
                f"{val:,.0f} ({sign}{gap:.1f}%)", va="center", fontsize=8)

    ax.set_title("Ranking de Geração - Melhor para Pior")
    ax.set_xlabel("kWh")
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    fig.tight_layout()
    path = os.path.join(output_dir, "ranking.png")
    fig.savefig(path, bbox_inches="tight")
    return path


def _chart_daily_variation(daily_df, kpis, output_dir):
    """Linhas diárias: variação durante o mês."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    if daily_df.empty:
        return None

    days = range(1, len(daily_df) + 1)

    for pid in PLANT_IDS:
        ax.plot(days, daily_df[pid].values, linewidth=1.2,
                color=PLANT_COLORS[pid], label=PLANTS[pid]["name"], alpha=0.85)

    ax.set_title(f"Geração Diária - {MESES_PT_FULL.get(kpis['target_month'], '')}/{kpis['target_year']}")
    ax.set_xlabel("Dia do mês")
    ax.set_ylabel("kWh")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.set_xlim(1, len(daily_df))

    fig.tight_layout()
    path = os.path.join(output_dir, "daily_variation.png")
    fig.savefig(path, bbox_inches="tight")
    return path


def _chart_yoy_comparison(kpis, monthly_totals_df, output_dir):
    """Comparação do mesmo mês em anos diferentes."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    month = kpis["target_month"]
    month_data = monthly_totals_df[monthly_totals_df["month"] == month].sort_values("year")

    if month_data.empty:
        return None

    years = month_data["year"].values
    x = np.arange(len(years))
    width = 0.15

    for i, pid in enumerate(PLANT_IDS):
        vals = month_data[pid].values
        offset = (i - len(PLANT_IDS) / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width, color=PLANT_COLORS[pid],
                      label=PLANTS[pid]["name"], edgecolor="white", linewidth=0.5)

    ax.axhline(y=TARGET_MONTHLY_KWH, color="#E74C3C", linestyle="--", linewidth=1, alpha=0.7)

    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years])
    ax.set_title(f"Comparativo Ano a Ano - {MESES_PT_FULL.get(month, '')}")
    ax.set_ylabel("kWh")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    fig.tight_layout()
    path = os.path.join(output_dir, "yoy_comparison.png")
    fig.savefig(path, bbox_inches="tight")
    return path
