"""
Geração de gráficos matplotlib para o relatório de geração solar.
Salva PNGs em diretório temporário para embedar no PDF.
"""
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
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

# Paleta McKinsey/BIG4
NAVY    = "#1B2A4A"
GOLD    = "#C9A84C"
SILVER  = "#CBD5E0"
BG_PLOT = "#F7F9FC"
TEXT_DK = "#2D3748"


def _setup_style():
    plt.rcParams.update({
        "figure.facecolor":    "white",
        "axes.facecolor":      BG_PLOT,
        "axes.grid":           True,
        "grid.alpha":          0.25,
        "grid.color":          SILVER,
        "font.family":         "sans-serif",
        "font.size":           9,
        "axes.titlesize":      11,
        "axes.titleweight":    "bold",
        "axes.titlecolor":     NAVY,
        "axes.labelsize":      9,
        "axes.labelcolor":     TEXT_DK,
        "axes.edgecolor":      SILVER,
        "axes.spines.top":     False,
        "axes.spines.right":   False,
        "xtick.color":         TEXT_DK,
        "ytick.color":         TEXT_DK,
        "legend.framealpha":   0.9,
        "legend.edgecolor":    SILVER,
        "figure.dpi":          150,
    })


def generate_all_charts(kpis, daily_df, monthly_totals_df, output_dir=None):
    """Gera todos os gráficos e retorna dict com caminhos dos PNGs."""
    _setup_style()
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="solar_charts_")

    charts = {}
    charts["cover_image"]        = _generate_cover_image(output_dir)
    charts["monthly_generation"] = _chart_monthly_generation(kpis, output_dir)
    charts["ytd_trend"]          = _chart_ytd_trend(kpis, monthly_totals_df, output_dir)
    charts["ranking"]            = _chart_ranking(kpis, output_dir)
    charts["daily_variation"]    = _chart_daily_variation(daily_df, kpis, output_dir)
    charts["yoy_comparison"]     = _chart_yoy_comparison(kpis, monthly_totals_df, output_dir)

    plt.close("all")
    return charts


def _generate_cover_image(output_dir):
    """Gera banner profissional estilo corporativo para a capa."""
    fig = plt.figure(figsize=(7, 2.0))
    ax = fig.add_axes([0, 0, 1, 1])

    ax.set_facecolor(NAVY)
    fig.patch.set_facecolor(NAVY)

    # Grid sutil estilo painel solar
    for x in np.linspace(0, 7, 20):
        ax.plot([x, x], [0, 2.0], color="#2C5282", linewidth=0.4, alpha=0.4)
    for y in np.linspace(0, 2.0, 6):
        ax.plot([0, 7], [y, y], color="#2C5282", linewidth=0.4, alpha=0.4)

    # Barra dourada inferior
    ax.fill_between([0, 7], [0, 0], [0.07, 0.07], color=GOLD, alpha=1.0)

    # Sol
    sun = mpatches.Circle((0.85, 1.05), 0.40, color="#F0A500", alpha=0.95, zorder=5)
    ax.add_patch(sun)
    for angle in np.linspace(0, 2 * np.pi, 8, endpoint=False):
        x1 = 0.85 + 0.43 * np.cos(angle)
        y1 = 1.05 + 0.43 * np.sin(angle)
        x2 = 0.85 + 0.62 * np.cos(angle)
        y2 = 1.05 + 0.62 * np.sin(angle)
        ax.plot([x1, x2], [y1, y2], color="#F0A500", linewidth=1.8, alpha=0.6, zorder=4)

    # Textos
    ax.text(1.65, 1.35, "SOLAR MARANHÃO", color="white",
            fontsize=17, fontweight="bold", va="center")
    ax.text(1.65, 0.85, "Portfólio de Usinas Solares Fotovoltaicas — Barreirinhas / MA",
            color=GOLD, fontsize=9, va="center")
    ax.text(1.65, 0.50, "5 usinas  ·  530,68 kWp instalados  ·  Em operação desde jan/2023",
            color="#90B4D0", fontsize=8, va="center")

    ax.set_xlim(0, 7)
    ax.set_ylim(0, 2.0)
    ax.axis("off")

    path = os.path.join(output_dir, "cover_image.png")
    fig.savefig(path, dpi=150, facecolor=NAVY, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return path


def _chart_monthly_generation(kpis, output_dir):
    """Barras: geração mensal por usina com linha de meta e banda de tolerância."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    names  = [PLANTS[pid]["name"] for pid in PLANT_IDS]
    values = [kpis["month_generation"][pid] for pid in PLANT_IDS]
    clrs   = [PLANT_COLORS[pid] for pid in PLANT_IDS]

    bars = ax.bar(names, values, color=clrs, width=0.55, edgecolor="white", linewidth=0.6)

    lower = TARGET_MONTHLY_KWH * (1 - TARGET_TOLERANCE)
    upper = TARGET_MONTHLY_KWH * (1 + TARGET_TOLERANCE)

    # Banda de tolerância (fundo)
    ax.axhspan(lower, upper, alpha=0.10, color=GOLD, label=f"Tolerância ±{TARGET_TOLERANCE:.0%}")
    # Linhas de limite de tolerância
    ax.axhline(y=upper, color=GOLD, linestyle=":", linewidth=1.2, alpha=0.9, label=f"Limite superior ({upper:,.0f} kWh)")
    ax.axhline(y=lower, color=GOLD, linestyle=":", linewidth=1.2, alpha=0.9, label=f"Limite inferior ({lower:,.0f} kWh)")
    # Linha de meta
    ax.axhline(y=TARGET_MONTHLY_KWH, color="#9B2335", linestyle="--", linewidth=1.8,
               label=f"Meta ({TARGET_MONTHLY_KWH:,.0f} kWh)")

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 120,
                f"{val:,.0f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color=NAVY)

    month_name = MESES_PT_FULL.get(kpis["target_month"], "")
    ax.set_title(f"Geração Mensal por Usina — {month_name}/{kpis['target_year']}")
    ax.set_ylabel("kWh")
    ax.legend(fontsize=7, loc="upper right", ncol=2)
    ax.set_ylim(0, max(values + [upper]) * 1.18)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    fig.tight_layout()
    path = os.path.join(output_dir, "monthly_generation.png")
    fig.savefig(path, bbox_inches="tight")
    return path


def _chart_ytd_trend(kpis, monthly_totals_df, output_dir):
    """Linhas: histórico de geração mês a mês no ano corrente."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    year      = kpis["target_year"]
    year_data = monthly_totals_df[
        (monthly_totals_df["year"] == year) &
        (monthly_totals_df["month"] <= kpis["target_month"])
    ].sort_values("month")

    if year_data.empty:
        return None

    months = [MESES_PT.get(m, str(m)) for m in year_data["month"]]

    for pid in PLANT_IDS:
        ax.plot(months, year_data[pid].values, marker="o", markersize=5,
                color=PLANT_COLORS[pid], linewidth=2.0, label=PLANTS[pid]["name"])

    lower = TARGET_MONTHLY_KWH * (1 - TARGET_TOLERANCE)
    upper = TARGET_MONTHLY_KWH * (1 + TARGET_TOLERANCE)

    ax.axhspan(lower, upper, alpha=0.10, color=GOLD)
    ax.axhline(y=upper, color=GOLD, linestyle=":", linewidth=1.2, alpha=0.9,
               label=f"+{TARGET_TOLERANCE:.0%} ({upper:,.0f} kWh)")
    ax.axhline(y=lower, color=GOLD, linestyle=":", linewidth=1.2, alpha=0.9,
               label=f"−{TARGET_TOLERANCE:.0%} ({lower:,.0f} kWh)")
    ax.axhline(y=TARGET_MONTHLY_KWH, color="#9B2335", linestyle="--",
               linewidth=1.5, alpha=0.9, label=f"Meta ({TARGET_MONTHLY_KWH:,.0f} kWh)")

    ax.set_title(f"Histórico de Geração Mensal — {year}")
    ax.set_ylabel("kWh")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    fig.tight_layout()
    path = os.path.join(output_dir, "ytd_trend.png")
    fig.savefig(path, bbox_inches="tight")
    return path


def _chart_ranking(kpis, output_dir):
    """Barras horizontais: ranking com status e linhas de tolerância."""
    fig, ax = plt.subplots(figsize=(7, 2.8))

    ranking = kpis["ranking"]
    names   = [PLANTS[pid]["name"] for pid in ranking]
    values  = [kpis["month_generation"][pid] for pid in ranking]

    color_map = {"verde": "#276749", "amarelo": "#B7791F", "vermelho": "#9B2335"}
    clrs = [color_map.get(kpis["gap_vs_target"][pid]["status"], "#718096") for pid in ranking]

    ax.barh(names, values, color=clrs, height=0.5, edgecolor="white", linewidth=0.5)

    lower = TARGET_MONTHLY_KWH * (1 - TARGET_TOLERANCE)
    upper = TARGET_MONTHLY_KWH * (1 + TARGET_TOLERANCE)

    ax.axvline(x=TARGET_MONTHLY_KWH, color="#9B2335", linestyle="--",
               linewidth=1.5, alpha=0.85, label=f"Meta ({TARGET_MONTHLY_KWH:,.0f})")
    ax.axvline(x=lower, color=GOLD, linestyle=":", linewidth=1.2,
               alpha=0.9, label=f"Limite −15% ({lower:,.0f})")
    ax.axvline(x=upper, color=GOLD, linestyle=":", linewidth=1.2,
               alpha=0.9, label=f"Limite +15% ({upper:,.0f})")
    ax.axvspan(lower, upper, alpha=0.08, color=GOLD)

    for val, pid in zip(values, ranking):
        gap  = kpis["gap_vs_target"][pid]["percent"]
        sign = "+" if gap >= 0 else ""
        ax.text(val + 150, ranking.index(pid),
                f"{val:,.0f} ({sign}{gap:.1f}%)", va="center", fontsize=8, color=NAVY)

    ax.set_title("Ranking de Geração — Melhor para Pior")
    ax.set_xlabel("kWh")
    ax.invert_yaxis()
    ax.legend(fontsize=7, loc="lower right")
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
        ax.plot(days, daily_df[pid].values, linewidth=1.5,
                color=PLANT_COLORS[pid], label=PLANTS[pid]["name"], alpha=0.9)

    ax.set_title(f"Geração Diária — {MESES_PT_FULL.get(kpis['target_month'], '')}/{kpis['target_year']}")
    ax.set_xlabel("Dia do mês")
    ax.set_ylabel("kWh")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.set_xlim(1, len(daily_df))

    fig.tight_layout()
    path = os.path.join(output_dir, "daily_variation.png")
    fig.savefig(path, bbox_inches="tight")
    return path


def _chart_yoy_comparison(kpis, monthly_totals_df, output_dir):
    """Comparação do mesmo mês em anos diferentes. Exclui 2023 (apenas 1 usina operando)."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    month      = kpis["target_month"]
    month_data = monthly_totals_df[
        (monthly_totals_df["month"] == month) &
        (monthly_totals_df["year"] >= 2024)      # exclui 2023
    ].sort_values("year")

    if month_data.empty:
        return None

    years = month_data["year"].values
    x     = np.arange(len(years))
    width = 0.14

    for i, pid in enumerate(PLANT_IDS):
        vals   = month_data[pid].values
        offset = (i - len(PLANT_IDS) / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, color=PLANT_COLORS[pid],
               label=PLANTS[pid]["name"], edgecolor="white", linewidth=0.5, alpha=0.9)

    ax.axhline(y=TARGET_MONTHLY_KWH, color="#9B2335", linestyle="--",
               linewidth=1.2, alpha=0.8, label="Meta")

    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years])
    ax.set_title(f"Comparativo Ano a Ano — {MESES_PT_FULL.get(month, '')} (2024–{kpis['target_year']})")
    ax.set_ylabel("kWh")
    ax.legend(fontsize=7, loc="best", ncol=2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    fig.tight_layout()
    path = os.path.join(output_dir, "yoy_comparison.png")
    fig.savefig(path, bbox_inches="tight")
    return path
