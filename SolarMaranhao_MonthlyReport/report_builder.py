"""
Montagem do PDF do relatório mensal de geração solar.
Usa ReportLab platypus para layout profissional com 8 seções.
"""
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether, HRFlowable,
)
from reportlab.lib.colors import HexColor

from config import PLANTS, PLANT_IDS, TARGET_MONTHLY_KWH, WEATHER_STATION, KWH_TO_BRL

MESES_PT_FULL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

# Cores
GREEN = HexColor("#27AE60")
YELLOW = HexColor("#F39C12")
RED = HexColor("#E74C3C")
BLUE = HexColor("#2980B9")
DARK = HexColor("#2C3E50")
LIGHT_GRAY = HexColor("#ECF0F1")
WHITE = colors.white


def _get_styles():
    """Cria estilos customizados para o relatório."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "CoverTitle", parent=styles["Title"],
        fontSize=24, leading=28, textColor=DARK,
        spaceAfter=10, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "CoverSubtitle", parent=styles["Normal"],
        fontSize=14, leading=18, textColor=BLUE,
        spaceAfter=20, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "SectionTitle", parent=styles["Heading1"],
        fontSize=14, leading=18, textColor=DARK,
        spaceBefore=16, spaceAfter=8,
        borderWidth=0, borderColor=BLUE, borderPadding=4,
    ))
    styles.add(ParagraphStyle(
        "SubTitle", parent=styles["Heading2"],
        fontSize=11, leading=14, textColor=BLUE,
        spaceBefore=10, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "BodyText2", parent=styles["Normal"],
        fontSize=9, leading=12, alignment=TA_JUSTIFY,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "SmallText", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=colors.gray,
    ))
    styles.add(ParagraphStyle(
        "BulletItem", parent=styles["Normal"],
        fontSize=9, leading=12, leftIndent=15,
        bulletIndent=5, spaceAfter=3,
    ))

    return styles


def _status_color(status):
    if status == "verde":
        return GREEN
    elif status == "amarelo":
        return YELLOW
    return RED


def _risk_color(classification):
    c = classification.upper()
    if c == "BAIXO":
        return HexColor("#D5F5E3")
    elif c in ("MÉDIO", "MEDIO"):
        return HexColor("#FEF9E7")
    elif c == "ALTO":
        return HexColor("#FADBD8")
    elif c in ("CRÍTICO", "CRITICO"):
        return HexColor("#F1948A")
    return LIGHT_GRAY


def _priority_color(priority):
    p = priority.upper()
    if p == "ALTA":
        return HexColor("#FADBD8")
    elif p in ("MÉDIA", "MEDIA"):
        return HexColor("#FEF9E7")
    return HexColor("#D5F5E3")


def _make_table(data, col_widths=None, header=True):
    """Cria uma tabela estilizada."""
    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F8F9FA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    table.setStyle(TableStyle(style_cmds))
    return table


def build_report(kpis, analysis, charts, output_path):
    """
    Monta o PDF completo do relatório.
    """
    styles = _get_styles()

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    story = []
    month_name = MESES_PT_FULL.get(kpis["target_month"], "")
    year = kpis["target_year"]

    # ══════════════════════════════════════════
    # SEÇÃO 1 — CAPA E SUMÁRIO EXECUTIVO
    # ══════════════════════════════════════════
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("Relatório Mensal de Geração Solar", styles["CoverTitle"]))
    story.append(Paragraph(f"Maranhão - {month_name}/{year}", styles["CoverSubtitle"]))
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="80%", color=BLUE, thickness=2))
    story.append(Spacer(1, 0.8 * cm))

    # Tabela de usinas
    plant_data = [["Usina", "Município", "Capacidade", "Início Operação"]]
    for pid in PLANT_IDS:
        p = PLANTS[pid]
        plant_data.append([
            p["name"], p["municipality"],
            f"{p['capacity_kwp']:.2f} kWp",
            p["start_date"].strftime("%d/%m/%Y"),
        ])
    story.append(_make_table(plant_data, col_widths=[3.5 * cm, 3.5 * cm, 3 * cm, 3.5 * cm]))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph(
        f"<b>Estação meteorológica:</b> {WEATHER_STATION['name']} "
        f"({WEATHER_STATION['coords'][0]:.5f}; {WEATHER_STATION['coords'][1]:.4f})",
        styles["SmallText"],
    ))
    story.append(Spacer(1, 0.8 * cm))

    # Sumário executivo
    story.append(Paragraph("Sumário Executivo", styles["SubTitle"]))
    exec_summary = analysis.get("sumario_executivo", "")
    if isinstance(exec_summary, str):
        story.append(Paragraph(exec_summary, styles["BodyText2"]))
    story.append(PageBreak())

    # ══════════════════════════════════════════
    # SEÇÃO 2 — KPIs DASHBOARD
    # ══════════════════════════════════════════
    story.append(Paragraph("2. KPIs Principais", styles["SectionTitle"]))

    # Tabela de KPIs
    kpi_data = [["Usina", "Geração\n(kWh)", "Meta\n(kWh)", "Gap\n(%)", "FC\n(%)",
                 "Yield\n(kWh/kWp)", "YTD\n(kWh)", "Status"]]
    for pid in PLANT_IDS:
        gen = kpis["month_generation"][pid]
        gap = kpis["gap_vs_target"][pid]
        fc = kpis["capacity_factor"][pid]
        sy = kpis["specific_yield"][pid]
        ytd = kpis["ytd"][pid]
        status = gap["status"].upper()
        kpi_data.append([
            PLANTS[pid]["name"],
            f"{gen:,.0f}",
            f"{TARGET_MONTHLY_KWH:,.0f}",
            f"{gap['percent']:+.1f}%",
            f"{fc:.1%}",
            f"{sy:.1f}",
            f"{ytd:,.0f}",
            status,
        ])
    # Totals row
    total_gen = kpis["month_generation"]["total"]
    total_ytd = kpis["ytd"]["total"]
    total_target = TARGET_MONTHLY_KWH * len(PLANT_IDS)
    total_gap = (total_gen - total_target) / total_target * 100
    kpi_data.append([
        "TOTAL", f"{total_gen:,.0f}", f"{total_target:,.0f}",
        f"{total_gap:+.1f}%", "-", "-", f"{total_ytd:,.0f}", "",
    ])

    kpi_table = _make_table(kpi_data, col_widths=[2.2*cm, 1.8*cm, 1.8*cm, 1.5*cm, 1.3*cm, 1.8*cm, 2*cm, 1.5*cm])

    # Color status cells
    for i, pid in enumerate(PLANT_IDS):
        status = kpis["gap_vs_target"][pid]["status"]
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (7, i + 1), (7, i + 1), _status_color(status)),
            ("TEXTCOLOR", (7, i + 1), (7, i + 1), WHITE),
            ("FONTNAME", (7, i + 1), (7, i + 1), "Helvetica-Bold"),
        ]))
    # Total row styling
    last_row = len(kpi_data) - 1
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, last_row), (-1, last_row), HexColor("#D6DBDF")),
        ("FONTNAME", (0, last_row), (-1, last_row), "Helvetica-Bold"),
    ]))

    story.append(kpi_table)
    story.append(Spacer(1, 0.5 * cm))

    # Gráficos
    if charts.get("monthly_generation"):
        story.append(Image(charts["monthly_generation"], width=16 * cm, height=8 * cm))
    story.append(Spacer(1, 0.3 * cm))
    if charts.get("ytd_trend"):
        story.append(Image(charts["ytd_trend"], width=16 * cm, height=8 * cm))
    story.append(PageBreak())

    # ══════════════════════════════════════════
    # SEÇÃO 3 — ANÁLISE COMPARATIVA
    # ══════════════════════════════════════════
    story.append(Paragraph("3. Análise Comparativa entre Usinas", styles["SectionTitle"]))

    # Ranking info
    ranking_text = []
    for i, pid in enumerate(kpis["ranking"]):
        gen = kpis["month_generation"][pid]
        gap = kpis["gap_vs_target"][pid]["percent"]
        ranking_text.append(f"{i+1}. {PLANTS[pid]['name']}: {gen:,.0f} kWh ({gap:+.1f}%)")

    story.append(Paragraph(
        f"<b>Ranking de geração:</b> {PLANTS[kpis['best_plant']]['name']} lidera com "
        f"{kpis['month_generation'][kpis['best_plant']]:,.0f} kWh. "
        f"Gap entre melhor e pior: {kpis['gap_best_worst_percent']:.1f}%.",
        styles["BodyText2"],
    ))

    if charts.get("ranking"):
        story.append(Image(charts["ranking"], width=16 * cm, height=6.5 * cm))
    story.append(Spacer(1, 0.3 * cm))
    if charts.get("daily_variation"):
        story.append(Image(charts["daily_variation"], width=16 * cm, height=8 * cm))
    story.append(Spacer(1, 0.3 * cm))

    # YoY comparison
    story.append(Paragraph("Comparativo Ano a Ano", styles["SubTitle"]))
    yoy_data = [["Usina", f"{year-1}", f"{year}", "Variação"]]
    for pid in PLANT_IDS:
        yoy = kpis["yoy_comparison"][pid]
        change = f"{yoy['change_percent']:+.1f}%" if yoy["change_percent"] is not None else "N/A"
        yoy_data.append([
            PLANTS[pid]["name"],
            f"{yoy['previous']:,.0f}" if yoy["previous"] > 0 else "N/A",
            f"{yoy['current']:,.0f}",
            change,
        ])
    story.append(_make_table(yoy_data, col_widths=[3.5*cm, 3*cm, 3*cm, 3*cm]))

    if charts.get("yoy_comparison"):
        story.append(Spacer(1, 0.3 * cm))
        story.append(Image(charts["yoy_comparison"], width=16 * cm, height=8 * cm))
    story.append(PageBreak())

    # ══════════════════════════════════════════
    # SEÇÃO 4 — ANÁLISE DE CAUSAS
    # ══════════════════════════════════════════
    story.append(Paragraph("4. Análise de Causas", styles["SectionTitle"]))

    causas = analysis.get("analise_causas", [])
    if isinstance(causas, list):
        for item in causas:
            causa = item.get("causa", "")
            desc = item.get("descricao", "")
            impacto = item.get("impacto", "")
            story.append(Paragraph(f"<b>{causa}</b> (Impacto: {impacto})", styles["SubTitle"]))
            story.append(Paragraph(desc, styles["BodyText2"]))
    elif isinstance(causas, str):
        for line in causas.split("\n"):
            if line.strip():
                story.append(Paragraph(line, styles["BodyText2"]))
    story.append(PageBreak())

    # ══════════════════════════════════════════
    # SEÇÃO 5 — ANÁLISE DE RISCOS
    # ══════════════════════════════════════════
    story.append(Paragraph("5. Análise de Riscos", styles["SectionTitle"]))

    riscos = analysis.get("analise_riscos", [])
    if isinstance(riscos, list) and riscos:
        risk_data = [["Risco", "Classificação", "Justificativa"]]
        for item in riscos:
            risk_data.append([
                item.get("risco", ""),
                item.get("classificacao", ""),
                item.get("justificativa", ""),
            ])

        risk_table = Table(risk_data, colWidths=[4 * cm, 2.5 * cm, 9 * cm], repeatRows=1)
        risk_style = [
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        for i, item in enumerate(riscos, 1):
            bg = _risk_color(item.get("classificacao", ""))
            risk_style.append(("BACKGROUND", (1, i), (1, i), bg))

        risk_table.setStyle(TableStyle(risk_style))
        story.append(risk_table)
    story.append(PageBreak())

    # ══════════════════════════════════════════
    # SEÇÃO 6 — PLANO DE AÇÃO
    # ══════════════════════════════════════════
    story.append(Paragraph("6. Plano de Ação", styles["SectionTitle"]))

    acoes = analysis.get("plano_acao", [])
    if isinstance(acoes, list) and acoes:
        action_data = [["Ação", "Prioridade", "Responsável", "Prazo", "Impacto", "Status"]]
        for item in acoes:
            action_data.append([
                item.get("acao", ""),
                item.get("prioridade", ""),
                item.get("responsavel", ""),
                item.get("prazo", ""),
                item.get("impacto", ""),
                item.get("status", "Pendente"),
            ])

        action_table = Table(action_data,
                             colWidths=[4.5*cm, 1.8*cm, 2*cm, 1.8*cm, 3.5*cm, 1.8*cm],
                             repeatRows=1)
        action_style = [
            ("BACKGROUND", (0, 0), (-1, 0), DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ALIGN", (5, 0), (5, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]
        for i, item in enumerate(acoes, 1):
            bg = _priority_color(item.get("prioridade", ""))
            action_style.append(("BACKGROUND", (1, i), (1, i), bg))

        action_table.setStyle(TableStyle(action_style))
        story.append(action_table)
    story.append(PageBreak())

    # ══════════════════════════════════════════
    # SEÇÃO 7 — IMPACTO FINANCEIRO
    # ══════════════════════════════════════════
    story.append(Paragraph("7. Impacto Financeiro", styles["SectionTitle"]))

    story.append(Paragraph(
        f"Base de cálculo: 1 kWh = R$ {KWH_TO_BRL:.2f}. "
        f"O impacto é estimado pela diferença entre a meta de {TARGET_MONTHLY_KWH:,.0f} kWh "
        f"e a geração efetiva de cada usina.",
        styles["BodyText2"],
    ))

    fin_data = [["Usina", "Geração\n(kWh)", "Meta\n(kWh)", "Energia Não\nGerada (kWh)",
                 "Receita\nPerdida (R$)", "Impacto\nAnualizado (R$)"]]
    for pid in PLANT_IDS:
        gen = kpis["month_generation"][pid]
        fin = kpis["financial"][pid]
        fin_data.append([
            PLANTS[pid]["name"],
            f"{gen:,.0f}",
            f"{TARGET_MONTHLY_KWH:,.0f}",
            f"{fin['non_generated_kwh']:,.0f}",
            f"R$ {fin['lost_revenue_brl']:,.0f}",
            f"R$ {fin['annualized_impact_brl']:,.0f}",
        ])
    # Total
    ft = kpis["financial"]["total"]
    fin_data.append([
        "TOTAL",
        f"{kpis['month_generation']['total']:,.0f}",
        f"{TARGET_MONTHLY_KWH * len(PLANT_IDS):,.0f}",
        f"{ft['non_generated_kwh']:,.0f}",
        f"R$ {ft['lost_revenue_brl']:,.0f}",
        f"R$ {ft['annualized_impact_brl']:,.0f}",
    ])

    fin_table = _make_table(fin_data, col_widths=[2.5*cm, 2*cm, 2*cm, 2.5*cm, 2.5*cm, 3*cm])
    last_row = len(fin_data) - 1
    fin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, last_row), (-1, last_row), HexColor("#D6DBDF")),
        ("FONTNAME", (0, last_row), (-1, last_row), "Helvetica-Bold"),
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 0.5 * cm))

    # Degradação
    story.append(Paragraph("Degradação Estimada dos Painéis", styles["SubTitle"]))
    deg_data = [["Usina", "Anos em\nOperação", "Degradação\nAcumulada (%)", "Perda Mensal\nEstimada (kWh)"]]
    for pid in PLANT_IDS:
        deg = kpis["degradation"][pid]
        deg_data.append([
            PLANTS[pid]["name"],
            f"{deg['years']:.1f}",
            f"{deg['cumulative_percent']:.2f}%",
            f"{deg['monthly_loss_kwh']:,.0f}",
        ])
    story.append(_make_table(deg_data, col_widths=[3.5*cm, 2.5*cm, 3*cm, 3.5*cm]))
    story.append(PageBreak())

    # ══════════════════════════════════════════
    # SEÇÃO 8 — CONCLUSÃO EXECUTIVA
    # ══════════════════════════════════════════
    story.append(Paragraph("8. Conclusão Executiva", styles["SectionTitle"]))

    conclusao = analysis.get("conclusao_executiva", "")
    if isinstance(conclusao, str):
        for para in conclusao.split("\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), styles["BodyText2"]))
                story.append(Spacer(1, 0.2 * cm))

    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="60%", color=BLUE, thickness=1))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        f"Relatório gerado automaticamente em {date.today().strftime('%d/%m/%Y')}.",
        styles["SmallText"],
    ))

    # Build
    doc.build(story)
    return output_path
