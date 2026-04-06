"""
Cálculo de KPIs de geração solar.
Fator de capacidade, yield específico, degradação, gap vs meta, ranking, impacto financeiro.
"""
from datetime import date
from calendar import monthrange

import pandas as pd

from config import (
    PLANTS, PLANT_IDS, TARGET_MONTHLY_KWH, TARGET_ANNUAL_KWH,
    TARGET_TOLERANCE, KWH_TO_BRL,
)


def calculate_all_kpis(monthly_totals_df, daily_df, target_year, target_month):
    """
    Calcula todos os KPIs para o mês alvo.
    Retorna dict com todas as métricas organizadas por seção.
    """
    _, days_in_month = monthrange(target_year, target_month)
    target_date = date(target_year, target_month, 1)

    # Geração do mês alvo
    month_row = monthly_totals_df[
        (monthly_totals_df["year"] == target_year) &
        (monthly_totals_df["month"] == target_month)
    ]
    month_gen = {}
    for pid in PLANT_IDS:
        if not month_row.empty:
            month_gen[pid] = float(month_row[pid].iloc[0])
        else:
            month_gen[pid] = 0.0
    month_gen["total"] = sum(month_gen[pid] for pid in PLANT_IDS)

    # YTD (acumulado no ano)
    ytd_rows = monthly_totals_df[
        (monthly_totals_df["year"] == target_year) &
        (monthly_totals_df["month"] <= target_month)
    ]
    ytd = {}
    for pid in PLANT_IDS:
        ytd[pid] = float(ytd_rows[pid].sum()) if not ytd_rows.empty else 0.0
    ytd["total"] = sum(ytd[pid] for pid in PLANT_IDS)

    # Geração desde início de operação
    lifetime = {}
    for pid in PLANT_IDS:
        plant = PLANTS[pid]
        start = plant["start_date"]
        mask = (
            (monthly_totals_df["year"] > start.year) |
            ((monthly_totals_df["year"] == start.year) & (monthly_totals_df["month"] >= start.month))
        )
        filtered = monthly_totals_df[mask]
        # Até o mês alvo
        mask2 = (
            (filtered["year"] < target_year) |
            ((filtered["year"] == target_year) & (filtered["month"] <= target_month))
        )
        lifetime[pid] = float(filtered[mask2][pid].sum())
    lifetime["total"] = sum(lifetime[pid] for pid in PLANT_IDS)

    # Média diária
    daily_avg = {pid: month_gen[pid] / days_in_month for pid in PLANT_IDS}
    daily_avg["total"] = month_gen["total"] / days_in_month

    # Fator de capacidade: geração / (capacidade_kWp * horas_no_mês)
    hours_in_month = days_in_month * 24
    capacity_factor = {}
    for pid in PLANT_IDS:
        cap = PLANTS[pid]["capacity_kwp"]
        capacity_factor[pid] = month_gen[pid] / (cap * hours_in_month) if cap > 0 else 0.0

    # Yield específico (kWh/kWp)
    specific_yield = {}
    for pid in PLANT_IDS:
        cap = PLANTS[pid]["capacity_kwp"]
        specific_yield[pid] = month_gen[pid] / cap if cap > 0 else 0.0

    # Gap vs meta
    gap_vs_target = {}
    for pid in PLANT_IDS:
        gap_vs_target[pid] = {
            "absolute": month_gen[pid] - TARGET_MONTHLY_KWH,
            "percent": ((month_gen[pid] - TARGET_MONTHLY_KWH) / TARGET_MONTHLY_KWH * 100) if TARGET_MONTHLY_KWH > 0 else 0.0,
            "status": _classify_gap(month_gen[pid], TARGET_MONTHLY_KWH, TARGET_TOLERANCE),
        }

    # Gap vs meta anual (projetado)
    months_elapsed = target_month
    ytd_target = TARGET_MONTHLY_KWH * months_elapsed
    gap_annual = {}
    for pid in PLANT_IDS:
        projected_annual = (ytd[pid] / months_elapsed * 12) if months_elapsed > 0 else 0.0
        gap_annual[pid] = {
            "ytd_target": ytd_target,
            "ytd_actual": ytd[pid],
            "ytd_gap_percent": ((ytd[pid] - ytd_target) / ytd_target * 100) if ytd_target > 0 else 0.0,
            "projected_annual": projected_annual,
            "annual_gap_percent": ((projected_annual - TARGET_ANNUAL_KWH) / TARGET_ANNUAL_KWH * 100) if TARGET_ANNUAL_KWH > 0 else 0.0,
        }

    # Ranking
    ranking = sorted(PLANT_IDS, key=lambda p: month_gen[p], reverse=True)
    best = ranking[0]
    worst = ranking[-1]
    gap_best_worst = ((month_gen[best] - month_gen[worst]) / month_gen[worst] * 100) if month_gen[worst] > 0 else 0.0

    # Degradação estimada
    degradation = {}
    for pid in PLANT_IDS:
        degradation[pid] = _calculate_degradation(pid, target_date)

    # Perdas estimadas (gap negativo vs meta = perda)
    estimated_losses = {}
    for pid in PLANT_IDS:
        loss = max(0, TARGET_MONTHLY_KWH - month_gen[pid])
        estimated_losses[pid] = loss

    # Projeção de fechamento (se o mês ainda não fechou)
    # Usa a média diária dos dias com dados
    projection = {}
    if not daily_df.empty:
        for pid in PLANT_IDS:
            days_with_data = (daily_df[pid] > 0).sum()
            if days_with_data > 0:
                avg = daily_df[pid].sum() / days_with_data
                projection[pid] = avg * days_in_month
            else:
                projection[pid] = 0.0
    else:
        projection = {pid: month_gen[pid] for pid in PLANT_IDS}

    # Comparativo com mesmo mês do ano anterior (legado)
    yoy = {}
    prev_year = target_year - 1
    prev_row = monthly_totals_df[
        (monthly_totals_df["year"] == prev_year) &
        (monthly_totals_df["month"] == target_month)
    ]
    for pid in PLANT_IDS:
        prev_val = float(prev_row[pid].iloc[0]) if not prev_row.empty else 0.0
        current_val = month_gen[pid]
        if prev_val > 0:
            yoy[pid] = {
                "previous": prev_val,
                "current": current_val,
                "change_percent": ((current_val - prev_val) / prev_val * 100),
            }
        else:
            yoy[pid] = {"previous": 0.0, "current": current_val, "change_percent": None}

    # Comparativo multi-ano: 2 anos anteriores + atual (para tabela expandida)
    yoy_multi = {}
    for pid in PLANT_IDS:
        yoy_multi[pid] = {}
        for yr in [target_year - 2, target_year - 1, target_year]:
            row = monthly_totals_df[
                (monthly_totals_df["year"] == yr) &
                (monthly_totals_df["month"] == target_month)
            ]
            yoy_multi[pid][yr] = float(row[pid].iloc[0]) if not row.empty else None

    # Disponibilidade por usina
    availability = {}
    if not daily_df.empty:
        for pid in PLANT_IDS:
            col = daily_df[pid]
            days_with_gen = int((col > 0).sum())
            zero_days = days_in_month - days_with_gen
            availability[pid] = {
                "days_with_gen": days_with_gen,
                "zero_days": zero_days,
                "availability_pct": days_with_gen / days_in_month * 100 if days_in_month > 0 else 0.0,
                "daily_min": float(col[col > 0].min()) if days_with_gen > 0 else 0.0,
                "daily_avg": float(col[col > 0].mean()) if days_with_gen > 0 else 0.0,
                "daily_max": float(col.max()),
            }

    # Impacto financeiro mensal
    financial = {}
    total_lost_revenue = 0.0
    for pid in PLANT_IDS:
        non_generated = max(0, TARGET_MONTHLY_KWH - month_gen[pid])
        lost_revenue = non_generated * KWH_TO_BRL
        annualized = lost_revenue * 12
        financial[pid] = {
            "non_generated_kwh": non_generated,
            "lost_revenue_brl": lost_revenue,
            "annualized_impact_brl": annualized,
        }
        total_lost_revenue += lost_revenue
    financial["total"] = {
        "non_generated_kwh": sum(financial[pid]["non_generated_kwh"] for pid in PLANT_IDS),
        "lost_revenue_brl": total_lost_revenue,
        "annualized_impact_brl": total_lost_revenue * 12,
    }

    # Impacto financeiro YTD (acumulado no ano até o mês alvo)
    ytd_target_per_plant = TARGET_MONTHLY_KWH * target_month   # meta acumulada
    financial_ytd = {}
    for pid in PLANT_IDS:
        ytd_gen = ytd[pid]
        ytd_gap_kwh = ytd_gen - ytd_target_per_plant        # positivo = superou; negativo = abaixo
        ytd_impact_brl = ytd_gap_kwh * KWH_TO_BRL           # positivo = receita extra; negativo = perda
        financial_ytd[pid] = {
            "ytd_generation":  ytd_gen,
            "ytd_target":      ytd_target_per_plant,
            "ytd_gap_kwh":     ytd_gap_kwh,
            "ytd_impact_brl":  ytd_impact_brl,              # negativo = perda
        }
    total_ytd_impact = sum(financial_ytd[pid]["ytd_impact_brl"] for pid in PLANT_IDS)
    financial_ytd["total"] = {
        "ytd_generation": ytd["total"],
        "ytd_target":     ytd_target_per_plant * len(PLANT_IDS),
        "ytd_gap_kwh":    ytd["total"] - ytd_target_per_plant * len(PLANT_IDS),
        "ytd_impact_brl": total_ytd_impact,
    }

    return {
        "target_year": target_year,
        "target_month": target_month,
        "days_in_month": days_in_month,
        "month_generation": month_gen,
        "ytd": ytd,
        "lifetime_generation": lifetime,
        "daily_average": daily_avg,
        "capacity_factor": capacity_factor,
        "specific_yield": specific_yield,
        "gap_vs_target": gap_vs_target,
        "gap_annual": gap_annual,
        "ranking": ranking,
        "best_plant": best,
        "worst_plant": worst,
        "gap_best_worst_percent": gap_best_worst,
        "degradation": degradation,
        "estimated_losses": estimated_losses,
        "projection": projection,
        "yoy_comparison": yoy,
        "financial":     financial,
        "financial_ytd": financial_ytd,
        "availability":  availability,
        "yoy_multi":     yoy_multi,
    }


def _classify_gap(actual, target, tolerance):
    """Classifica o status da geração vs meta."""
    ratio = actual / target if target > 0 else 0
    if ratio >= 1.0:
        return "verde"       # Atingiu ou superou a meta
    elif ratio >= (1 - tolerance):
        return "amarelo"     # Dentro da tolerância
    else:
        return "vermelho"    # Abaixo da tolerância


def _calculate_degradation(plant_id, reference_date):
    """
    Calcula a degradação estimada dos painéis com base na idade.
    Retorna dict com percentual de degradação acumulada e perda estimada.
    """
    plant = PLANTS[plant_id]
    start = plant["start_date"]
    years_operating = (reference_date - start).days / 365.25

    if years_operating <= 0:
        return {"years": 0, "cumulative_percent": 0.0, "monthly_loss_kwh": 0.0}

    # Ano 1: até 2%, depois 0.55%/ano
    if years_operating <= 1:
        cumulative = plant["degradation_year1"] * years_operating
    else:
        cumulative = plant["degradation_year1"] + plant["degradation_annual"] * (years_operating - 1)

    # Perda mensal estimada em relação à meta
    monthly_loss = TARGET_MONTHLY_KWH * cumulative

    return {
        "years": round(years_operating, 1),
        "cumulative_percent": round(cumulative * 100, 2),
        "monthly_loss_kwh": round(monthly_loss, 1),
    }
