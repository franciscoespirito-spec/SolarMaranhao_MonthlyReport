"""
Montagem do PDF do relatório mensal de geração solar — Solar Maranhão.
Design profissional estilo BIG4/McKinsey com ReportLab Platypus.
"""
import os
from datetime import date
from xml.sax.saxutils import escape as _xe   # escapa &, <, > em texto dinâmico

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
MESES_PT_ABR = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

# ── Paleta BIG4/McKinsey ────────────────────────────────────────
NAVY       = HexColor("#1B2A4A")
NAVY_MED   = HexColor("#2C5282")
GOLD       = HexColor("#C9A84C")
GOLD_LIGHT = HexColor("#FBF3DC")
CHARCOAL   = HexColor("#2D3748")
STEEL      = HexColor("#718096")
SILVER     = HexColor("#CBD5E0")
BG_ALT     = HexColor("#F7F9FC")
BG_LIGHT   = HexColor("#EEF2F7")
GREEN_DK   = HexColor("#276749")
GREEN_BG   = HexColor("#C6F6D5")
RED_DK     = HexColor("#9B2335")
RED_BG     = HexColor("#FED7D7")
AMBER_DK   = HexColor("#B7791F")
AMBER_BG   = HexColor("#FEFCBF")
WHITE      = colors.white

# Hex strings para uso direto em markup Paragraph
_HEX = {
    "green":  "276749",
    "red":    "9B2335",
    "amber":  "B7791F",
    "navy":   "1B2A4A",
    "steel":  "718096",
    "gold":   "C9A84C",
}


# ── Estilos ─────────────────────────────────────────────────────
def _get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "MainTitle", parent=styles["Title"],
        fontSize=26, leading=30, textColor=NAVY,
        spaceAfter=4, alignment=TA_LEFT, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "SubTitle", parent=styles["Normal"],
        fontSize=13, leading=16, textColor=GOLD,
        spaceAfter=6, alignment=TA_LEFT, fontName="Helvetica",
    ))
    styles.add(ParagraphStyle(
        "SectionTitle", parent=styles["Heading1"],
        fontSize=13, leading=16, textColor=NAVY, fontName="Helvetica-Bold",
        spaceBefore=14, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "SubSectionTitle", parent=styles["Heading2"],
        fontSize=10, leading=13, textColor=NAVY_MED, fontName="Helvetica-Bold",
        spaceBefore=8, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=9, leading=13, alignment=TA_JUSTIFY,
        textColor=CHARCOAL, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        "BodyLeft", parent=styles["Normal"],
        fontSize=9, leading=13, alignment=TA_LEFT,
        textColor=CHARCOAL, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        "Caption", parent=styles["Normal"],
        fontSize=7.5, leading=10, textColor=STEEL,
    ))
    styles.add(ParagraphStyle(
        "CaptionCenter", parent=styles["Normal"],
        fontSize=7.5, leading=10, textColor=STEEL, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "FootnoteStyle", parent=styles["Normal"],
        fontSize=7, leading=9, textColor=STEEL,
    ))
    styles.add(ParagraphStyle(
        "DefBox", parent=styles["Normal"],
        fontSize=8, leading=11, textColor=CHARCOAL,
        leftIndent=6, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "ExecSummary", parent=styles["Normal"],
        fontSize=9.5, leading=14, alignment=TA_JUSTIFY,
        textColor=CHARCOAL, spaceAfter=6,
    ))
    return styles


# ── Helpers ──────────────────────────────────────────────────────
def _status_color(status):
    if status == "verde":   return GREEN_DK
    if status == "amarelo": return AMBER_DK
    return RED_DK


def _status_bg(status):
    if status == "verde":   return GREEN_BG
    if status == "amarelo": return AMBER_BG
    return RED_BG


def _risk_color(cls):
    c = cls.upper()
    if c == "BAIXO":                 return HexColor("#C6F6D5")
    if c in ("MÉDIO", "MEDIO"):      return AMBER_BG
    if c == "ALTO":                  return RED_BG
    if c in ("CRÍTICO", "CRITICO"):  return RED_DK
    return BG_ALT


def _priority_bg(p):
    p = p.upper()
    if p == "ALTA":                  return RED_BG
    if p in ("MÉDIA", "MEDIA"):      return AMBER_BG
    return GREEN_BG


def _make_table(data, col_widths=None, header=True, row_heights=None):
    table = Table(data, colWidths=col_widths, rowHeights=row_heights,
                  repeatRows=1 if header else 0)
    style = [
        ("BACKGROUND",   (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",         (0, 0), (-1, -1), 0.4, SILVER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, BG_ALT]),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    table.setStyle(TableStyle(style))
    return table


def _add_page_footer(canvas, doc):
    """Rodapé profissional com número de página."""
    canvas.saveState()
    w = A4[0]
    y = 1.3 * cm
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.8)
    canvas.line(2 * cm, y + 0.45 * cm, w - 2 * cm, y + 0.45 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(STEEL)
    canvas.drawString(2 * cm, y, "Solar Maranhão — Relatório Mensal de Geração Solar")
    canvas.drawRightString(w - 2 * cm, y, f"Página {doc.page}")
    canvas.restoreState()


# ── Builder principal ─────────────────────────────────────────────
def build_report(kpis, analysis, charts, output_path):
    """Monta o PDF completo do relatório."""
    styles     = _get_styles()
    month_name = MESES_PT_FULL.get(kpis["target_month"], "")
    year       = kpis["target_year"]
    month_abr  = MESES_PT_ABR.get(kpis["target_month"], "")
    prev2_year = year - 2   # 2024 quando o alvo é 2026
    prev_year  = year - 1   # 2025

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2.0 * cm, bottomMargin=2.2 * cm,
    )

    story = []

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 1 — CAPA
    # ═══════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.5 * cm))

    # Título principal
    story.append(Paragraph("Solar Maranhão", styles["MainTitle"]))
    story.append(Paragraph(f"Relatório de {month_name}/{year}", styles["SubTitle"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.5))
    story.append(Spacer(1, 0.4 * cm))

    # Imagem de capa (banner corporativo)
    if charts.get("cover_image") and os.path.exists(charts["cover_image"]):
        story.append(Image(charts["cover_image"], width=16.6 * cm, height=4.7 * cm))
        story.append(Spacer(1, 0.5 * cm))

    # Tabela de usinas (capa)
    plant_hdr = [["Usina", "Endereço", "Município", "Cap. (kWp)", "Painéis / Inversor", "Início Operação"]]
    for pid in PLANT_IDS:
        p = PLANTS[pid]
        plant_hdr.append([
            p["name"],
            p["address"],
            p["municipality"],
            f"{p['capacity_kwp']:.2f}",
            f"{p['panel_count']} × {p['panel_model'].split()[0]}\n{p['inverter_model'].split('(')[0].strip()}",
            p["start_date"].strftime("%d/%m/%Y"),
        ])
    plant_table = _make_table(
        plant_hdr,
        col_widths=[2.2*cm, 3.8*cm, 2.8*cm, 1.8*cm, 3.2*cm, 2.0*cm],
    )
    story.append(plant_table)
    story.append(Spacer(1, 0.35 * cm))

    # Estação meteorológica
    story.append(Paragraph(
        f"<b>Estação meteorológica mais próxima das usinas: INMET A218 — Preguiças</b>  "
        f"({WEATHER_STATION['coords'][0]:.5f}; {WEATHER_STATION['coords'][1]:.4f}; "
        f"MA; FarolPreguicas; A218)",
        styles["Caption"],
    ))
    story.append(Paragraph(
        "INMET: Instituto Nacional de Meteorologia — https://portal.inmet.gov.br/",
        styles["FootnoteStyle"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    # Sumário executivo
    story.append(HRFlowable(width="100%", color=SILVER, thickness=0.5))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Sumário Executivo", styles["SectionTitle"]))
    exec_sum = analysis.get("sumario_executivo", "")
    if isinstance(exec_sum, str):
        story.append(Paragraph(exec_sum, styles["ExecSummary"]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 2 — KPIs PRINCIPAIS
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph(f"2. KPIs Principais — Dados de {month_name}/{year}", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.0))
    story.append(Spacer(1, 0.4 * cm))

    # Tabela KPI
    kpi_hdr = [
        [
            "Usina",
            Paragraph("Geração\nmensal\n(kWh)", styles["CaptionCenter"]),
            Paragraph("Meta\nmédia\n(kWh)", styles["CaptionCenter"]),
            Paragraph("Gap\n(%)", styles["CaptionCenter"]),
            Paragraph("FC\n(%)", styles["CaptionCenter"]),
            Paragraph("Yield\n(kWh/\nkWp)", styles["CaptionCenter"]),
            Paragraph("Disp.\n(%)", styles["CaptionCenter"]),
            Paragraph("Geração\nanual\n2026 (kWh)", styles["CaptionCenter"]),
            "Status",
        ]
    ]
    for pid in PLANT_IDS:
        gen    = kpis["month_generation"][pid]
        gap    = kpis["gap_vs_target"][pid]
        fc     = kpis["capacity_factor"][pid]
        sy     = kpis["specific_yield"][pid]
        ytd_v  = kpis["ytd"][pid]
        av     = kpis.get("availability", {}).get(pid, {})
        disp   = f"{av.get('availability_pct', 0):.0f}%" if av else "—"
        status = gap["status"]
        kpi_hdr.append([
            PLANTS[pid]["name"],
            f"{gen:,.0f}",
            f"{TARGET_MONTHLY_KWH:,.0f}",
            f"{gap['percent']:+.1f}%",
            f"{fc:.1%}",
            f"{sy:.1f}",
            disp,
            f"{ytd_v:,.0f}",
            Paragraph(f"<b>{status.upper()}</b>", styles["CaptionCenter"]),
        ])

    total_gen    = kpis["month_generation"]["total"]
    total_ytd    = kpis["ytd"]["total"]
    total_target = TARGET_MONTHLY_KWH * len(PLANT_IDS)
    total_gap    = (total_gen - total_target) / total_target * 100
    kpi_hdr.append([
        Paragraph("<b>TOTAL</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{total_gen:,.0f}</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{total_target:,.0f}</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{total_gap:+.1f}%</b>", styles["CaptionCenter"]),
        "—", "—", "—",
        Paragraph(f"<b>{total_ytd:,.0f}</b>", styles["CaptionCenter"]),
        "",
    ])

    kpi_tbl = _make_table(
        kpi_hdr,
        col_widths=[2.0*cm, 1.9*cm, 1.8*cm, 1.4*cm, 1.3*cm, 1.7*cm, 1.3*cm, 2.0*cm, 1.6*cm],
        row_heights=[1.1*cm] + [None] * (len(kpi_hdr) - 1),
    )

    # Colorir coluna Status + linha total
    for i, pid in enumerate(PLANT_IDS):
        st = kpis["gap_vs_target"][pid]["status"]
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (8, i + 1), (8, i + 1), _status_bg(st)),
            ("TEXTCOLOR",  (8, i + 1), (8, i + 1), _status_color(st)),
            ("FONTNAME",   (8, i + 1), (8, i + 1), "Helvetica-Bold"),
        ]))
    last = len(kpi_hdr) - 1
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, last), (-1, last), BG_LIGHT),
        ("FONTNAME",   (0, last), (-1, last), "Helvetica-Bold"),
        ("LINEABOVE",  (0, last), (-1, last), 1.0, NAVY),
    ]))

    story.append(kpi_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # Caixa de definições
    defs_data = [[
        Paragraph(
            "<b>GAP</b> — Diferença percentual entre a geração realizada e a meta mensal (14.000 kWh/usina). "
            "Positivo = acima da meta; Negativo = abaixo da meta.",
            styles["DefBox"]
        ),
        Paragraph(
            "<b>FC (Fator de Capacidade)</b> — Relação entre a energia gerada e a energia máxima possível "
            "considerando a capacidade instalada em kWp durante todas as horas do mês.",
            styles["DefBox"]
        ),
    ], [
        Paragraph(
            "<b>Yield (Produtividade Específica)</b> — Geração mensal em kWh dividida pela capacidade instalada "
            "em kWp. Indica a eficiência de aproveitamento da radiação solar por unidade instalada.",
            styles["DefBox"]
        ),
        Paragraph(
            "<b>Geração Anual 2026</b> — Total acumulado de geração desde janeiro de 2026 até o mês de referência "
            f"({month_name}/{year}). Permite acompanhar o desempenho no ano.",
            styles["DefBox"]
        ),
    ]]
    defs_tbl = Table(defs_data, colWidths=[8.1*cm, 8.1*cm])
    defs_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GOLD_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 0.8, GOLD),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, GOLD),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    story.append(defs_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # Gráficos seção 2
    if charts.get("monthly_generation"):
        story.append(Image(charts["monthly_generation"], width=16.6 * cm, height=7.8 * cm))
    story.append(Spacer(1, 0.3 * cm))
    if charts.get("ytd_trend"):
        story.append(Image(charts["ytd_trend"], width=16.6 * cm, height=7.8 * cm))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 3 — ANÁLISE COMPARATIVA
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("3. Análise Comparativa entre Usinas", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.0))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(
        f"<b>Ranking de geração — {month_name}/{year}:</b>  "
        f"{PLANTS[kpis['best_plant']]['name']} lidera com "
        f"{kpis['month_generation'][kpis['best_plant']]:,.0f} kWh. "
        f"Gap entre melhor e pior: {kpis['gap_best_worst_percent']:.1f}%.",
        styles["Body"],
    ))

    if charts.get("ranking"):
        story.append(Image(charts["ranking"], width=16.6 * cm, height=6.5 * cm))
    story.append(Spacer(1, 0.3 * cm))
    if charts.get("daily_variation"):
        story.append(Image(charts["daily_variation"], width=16.6 * cm, height=7.5 * cm))
    story.append(Spacer(1, 0.4 * cm))

    # Tabela multi-ano
    story.append(Paragraph(
        f"Comparativo {month_abr}/{prev2_year}, {month_abr}/{prev_year} e {month_abr}/{year}",
        styles["SubSectionTitle"],
    ))

    yoy_m   = kpis.get("yoy_multi", {})
    yoy_hdr = [
        ["Usina",
         f"{month_abr}/{prev2_year}",
         f"{month_abr}/{prev_year}",
         f"{month_abr}/{year}",
         f"Var.\n{year}–{prev_year}",
         f"Var.\n{year}–{prev2_year}"],
    ]
    for pid in PLANT_IDS:
        row_d  = yoy_m.get(pid, {})
        v2024  = row_d.get(prev2_year)
        v2025  = row_d.get(prev_year)
        v2026  = row_d.get(year) or kpis["month_generation"][pid]

        def _fmt(v): return f"{v:,.0f}" if v and v > 0 else "N/A"
        def _var(cur, ref):
            if ref and ref > 0:
                pct = (cur - ref) / ref * 100
                return f"{pct:+.1f}%"
            return "N/A"

        yoy_hdr.append([
            PLANTS[pid]["name"],
            _fmt(v2024),
            _fmt(v2025),
            _fmt(v2026),
            _var(v2026, v2025),
            _var(v2026, v2024),
        ])

    # Totais
    def _sum_year(yr):
        return sum(yoy_m.get(pid, {}).get(yr) or 0 for pid in PLANT_IDS)

    t24 = _sum_year(prev2_year)
    t25 = _sum_year(prev_year)
    t26 = kpis["month_generation"]["total"]
    yoy_hdr.append([
        Paragraph("<b>TOTAL</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{t24:,.0f}</b>", styles["CaptionCenter"]) if t24 > 0 else "N/A",
        Paragraph(f"<b>{t25:,.0f}</b>", styles["CaptionCenter"]) if t25 > 0 else "N/A",
        Paragraph(f"<b>{t26:,.0f}</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{(t26-t25)/t25*100:+.1f}%</b>", styles["CaptionCenter"]) if t25 > 0 else "N/A",
        Paragraph(f"<b>{(t26-t24)/t24*100:+.1f}%</b>", styles["CaptionCenter"]) if t24 > 0 else "N/A",
    ])

    yoy_tbl = _make_table(yoy_hdr, col_widths=[3.0*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.8*cm, 2.8*cm])

    # Cor linhas de variação: verde se positivo, vermelho se negativo
    for i in range(1, len(yoy_hdr)):
        pid = PLANT_IDS[i - 1] if i <= len(PLANT_IDS) else None
        if pid:
            row_d = yoy_m.get(pid, {})
            v2025 = row_d.get(prev_year)
            v2026 = row_d.get(year) or kpis["month_generation"][pid]
            v2024 = row_d.get(prev2_year)
            for col_idx, (cur, ref) in [(4, (v2026, v2025)), (5, (v2026, v2024))]:
                if ref and ref > 0:
                    bg = GREEN_BG if cur >= ref else RED_BG
                    fc = GREEN_DK if cur >= ref else RED_DK
                    yoy_tbl.setStyle(TableStyle([
                        ("BACKGROUND", (col_idx, i), (col_idx, i), bg),
                        ("TEXTCOLOR",  (col_idx, i), (col_idx, i), fc),
                        ("FONTNAME",   (col_idx, i), (col_idx, i), "Helvetica-Bold"),
                    ]))

    # Total row
    last_row = len(yoy_hdr) - 1
    yoy_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, last_row), (-1, last_row), BG_LIGHT),
        ("FONTNAME",   (0, last_row), (-1, last_row), "Helvetica-Bold"),
        ("LINEABOVE",  (0, last_row), (-1, last_row), 1.0, NAVY),
    ]))

    story.append(yoy_tbl)
    story.append(Spacer(1, 0.4 * cm))

    if charts.get("yoy_comparison"):
        story.append(Image(charts["yoy_comparison"], width=16.6 * cm, height=7.8 * cm))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 4 — ANÁLISE DE CAUSAS
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("4. Análise de Causas", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.0))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "Decomposição diagnóstica das variações de geração por tipo de efeito — "
        "separando causas externas (clima, sazonalidade) de causas internas (operacional, técnica, monitoramento).",
        styles["Caption"],
    ))
    story.append(Spacer(1, 0.3 * cm))

    def _impact_colors(imp_raw):
        """Retorna (bg_color, text_color, label) para cada nível de impacto."""
        imp = imp_raw.strip().lower()
        if "alto" in imp or "crítico" in imp or "critico" in imp:
            return RED_BG, RED_DK, imp_raw.upper()
        elif "médio" in imp or "medio" in imp:
            return AMBER_BG, AMBER_DK, imp_raw.upper()
        elif "baixo" in imp:
            return GREEN_BG, GREEN_DK, imp_raw.upper()
        else:
            return BG_ALT, STEEL, "NÃO IDENT."

    causas = analysis.get("analise_causas", [])
    if isinstance(causas, list):
        for item in causas:
            causa      = _xe(item.get("causa", ""))
            desc       = _xe(item.get("descricao", ""))
            evidencia  = _xe(item.get("evidencia", ""))
            kwh_est    = _xe(item.get("kwh_estimado", "—"))
            imp_raw    = item.get("impacto", "Não identificado")
            bg, fg, badge = _impact_colors(imp_raw)

            # Coluna esquerda: badge de impacto + nome da causa
            left_cell = [
                Paragraph(
                    f"<b><font color='white'> {badge} </font></b>",
                    ParagraphStyle(
                        "BadgeStyle", parent=styles["Normal"],
                        fontSize=7, leading=10, alignment=TA_CENTER,
                        textColor=colors.white, backColor=fg,
                        borderPadding=(2, 4, 2, 4),
                    ),
                ),
                Spacer(1, 0.1 * cm),
                Paragraph(f"<b>{causa}</b>", ParagraphStyle(
                    "CausaName", parent=styles["Normal"],
                    fontSize=9, leading=12, alignment=TA_CENTER,
                    textColor=NAVY,
                )),
            ]

            # Coluna direita: diagnóstico + evidência + kWh estimado
            right_lines = []
            if desc:
                right_lines.append(Paragraph(desc, styles["BodyLeft"]))
            if evidencia:
                steel_c = _HEX["steel"]
                right_lines.append(Paragraph(
                    f"<i><font color='#{steel_c}'>Evidência: {evidencia}</font></i>",
                    styles["Caption"],
                ))
            if kwh_est and kwh_est != "—":
                kw_color = _HEX["red"] if kwh_est.lstrip().startswith("-") else _HEX["green"]
                right_lines.append(Paragraph(
                    f"<font color='#{kw_color}'><b>Impacto estimado: {kwh_est}</b></font>",
                    ParagraphStyle(
                        "KwhImpact", parent=styles["Normal"],
                        fontSize=8, leading=11, alignment=TA_LEFT,
                        spaceAfter=2,
                    ),
                ))

            tbl = Table(
                [[left_cell, right_lines]],
                colWidths=[4.2 * cm, 12.0 * cm],
            )
            tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (0, 0), bg),
                ("BACKGROUND",    (1, 0), (1, 0), WHITE),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN",         (0, 0), (0, 0), "CENTER"),
                ("ALIGN",         (1, 0), (1, 0), "LEFT"),
                ("BOX",           (0, 0), (-1, -1), 0.5, SILVER),
                ("LINEAFTER",     (0, 0), (0, -1), 0.5, SILVER),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (0, 0),  6),
                ("RIGHTPADDING",  (0, 0), (0, 0),  6),
                ("LEFTPADDING",   (1, 0), (1, 0),  8),
                ("RIGHTPADDING",  (1, 0), (1, 0),  6),
            ]))
            story.append(KeepTogether([tbl, Spacer(1, 0.2 * cm)]))

    elif isinstance(causas, str):
        for line in causas.split("\n"):
            if line.strip():
                story.append(Paragraph(_xe(line), styles["Body"]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 5 — ANÁLISE DE RISCOS
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("5. Análise de Riscos", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.0))
    story.append(Spacer(1, 0.3 * cm))

    riscos = analysis.get("analise_riscos", [])
    if isinstance(riscos, list) and riscos:
        risk_hdr = [["Risco", "Classificação", "Justificativa"]]
        for item in riscos:
            risk_hdr.append([
                _xe(item.get("risco", "")),
                _xe(item.get("classificacao", "")),
                Paragraph(_xe(item.get("justificativa", "")), styles["Body"]),
            ])

        risk_tbl = Table(risk_hdr, colWidths=[4.2*cm, 2.6*cm, 9.4*cm], repeatRows=1)
        risk_style = [
            ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ("ALIGN",         (1, 0), (1, -1),  "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("GRID",          (0, 0), (-1, -1), 0.4, SILVER),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BG_ALT]),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ]
        for i, item in enumerate(riscos, 1):
            bg = _risk_color(item.get("classificacao", ""))
            risk_style += [
                ("BACKGROUND", (1, i), (1, i), bg),
                ("FONTNAME",   (1, i), (1, i), "Helvetica-Bold"),
                ("ALIGN",      (1, i), (1, i), "CENTER"),
            ]
        risk_tbl.setStyle(TableStyle(risk_style))
        story.append(risk_tbl)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 6 — PLANO DE AÇÃO
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("6. Plano de Ação", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.0))
    story.append(Spacer(1, 0.3 * cm))

    acoes = analysis.get("plano_acao", [])
    if isinstance(acoes, list) and acoes:
        action_hdr = [["Ação", "Prior.", "Responsável", "Prazo", "Impacto Esperado", "Status"]]
        for item in acoes:
            action_hdr.append([
                Paragraph(item.get("acao", ""), styles["Body"]),
                Paragraph(f"<b>{item.get('prioridade', '')}</b>", styles["CaptionCenter"]),
                Paragraph(item.get("responsavel", ""), styles["Body"]),
                Paragraph(item.get("prazo", ""), styles["Body"]),
                Paragraph(item.get("impacto", ""), styles["Body"]),
                Paragraph(item.get("status", "Pendente"), styles["CaptionCenter"]),
            ])

        action_tbl = Table(
            action_hdr,
            colWidths=[4.8*cm, 1.5*cm, 2.2*cm, 1.8*cm, 3.8*cm, 1.9*cm],
            repeatRows=1,
        )
        action_style = [
            ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("GRID",          (0, 0), (-1, -1), 0.4, SILVER),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BG_ALT]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ]
        for i, item in enumerate(acoes, 1):
            bg = _priority_bg(item.get("prioridade", ""))
            action_style += [
                ("BACKGROUND", (1, i), (1, i), bg),
            ]
        action_tbl.setStyle(TableStyle(action_style))
        story.append(action_tbl)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 7 — IMPACTO FINANCEIRO
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph(f"7. Impacto Financeiro — Ano {year}", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.0))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph(
        f"Base de cálculo: 1 kWh = R$ {KWH_TO_BRL:.2f}. "
        f"A coluna <b>Impacto Mensal</b> refere-se ao desvio de {month_name}/{year} em relação à meta de "
        f"{TARGET_MONTHLY_KWH:,.0f} kWh/usina. "
        f"A coluna <b>Impacto Acumulado {year}</b> consolida o desvio desde jan/{year} até {month_name}/{year}. "
        f"Valores em <font color='#276749'><b>verde</b></font> indicam geração acima da meta; "
        f"em <font color='#9B2335'><b>vermelho</b></font>, abaixo.",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.3 * cm))

    fytd = kpis.get("financial_ytd", {})
    fin_hdr = [[
        "Usina",
        Paragraph("Geração\nmensal\n(kWh)", styles["CaptionCenter"]),
        Paragraph("Meta\nmensal\n(kWh)", styles["CaptionCenter"]),
        Paragraph("Energia\nnão gerada\n(kWh)", styles["CaptionCenter"]),
        Paragraph("Impacto\nmensal\n(R$)", styles["CaptionCenter"]),
        Paragraph(f"Geração\nanual {year}\n(kWh)", styles["CaptionCenter"]),
        Paragraph(f"Meta\nanual {year}\n(kWh)", styles["CaptionCenter"]),
        Paragraph(f"Impacto\nacumulado\n{year} (R$)", styles["CaptionCenter"]),
    ]]

    for pid in PLANT_IDS:
        gen     = kpis["month_generation"][pid]
        fin_m   = kpis["financial"][pid]
        fd      = fytd.get(pid, {})
        ytd_imp = fd.get("ytd_impact_brl", 0)
        ytd_gen = fd.get("ytd_generation", 0)
        ytd_tgt = fd.get("ytd_target", 0)

        imp_str = f"R$ {abs(ytd_imp):,.0f}"
        if ytd_imp >= 0:
            imp_cell = Paragraph(f"<font color='#276749'><b>+{imp_str}</b></font>", styles["CaptionCenter"])
        else:
            imp_cell = Paragraph(f"<font color='#9B2335'><b>−{imp_str}</b></font>", styles["CaptionCenter"])

        fin_hdr.append([
            PLANTS[pid]["name"],
            f"{gen:,.0f}",
            f"{TARGET_MONTHLY_KWH:,.0f}",
            f"{fin_m['non_generated_kwh']:,.0f}",
            f"R$ {fin_m['lost_revenue_brl']:,.0f}",
            f"{ytd_gen:,.0f}",
            f"{ytd_tgt:,.0f}",
            imp_cell,
        ])

    # Total
    ft      = kpis["financial"]["total"]
    fdt     = fytd.get("total", {})
    tot_imp = fdt.get("ytd_impact_brl", 0)
    tot_str = f"R$ {abs(tot_imp):,.0f}"
    if tot_imp >= 0:
        tot_cell = Paragraph(f"<font color='#276749'><b>+{tot_str}</b></font>", styles["CaptionCenter"])
    else:
        tot_cell = Paragraph(f"<font color='#9B2335'><b>−{tot_str}</b></font>", styles["CaptionCenter"])

    fin_hdr.append([
        Paragraph("<b>TOTAL</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{kpis['month_generation']['total']:,.0f}</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{TARGET_MONTHLY_KWH*len(PLANT_IDS):,.0f}</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{ft['non_generated_kwh']:,.0f}</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>R$ {ft['lost_revenue_brl']:,.0f}</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{fdt.get('ytd_generation', 0):,.0f}</b>", styles["CaptionCenter"]),
        Paragraph(f"<b>{fdt.get('ytd_target', 0):,.0f}</b>", styles["CaptionCenter"]),
        tot_cell,
    ])

    fin_tbl = _make_table(
        fin_hdr,
        col_widths=[2.2*cm, 1.8*cm, 1.8*cm, 1.9*cm, 1.9*cm, 2.0*cm, 2.0*cm, 2.1*cm],
        row_heights=[1.1*cm] + [None] * (len(fin_hdr) - 1),
    )
    last_fin = len(fin_hdr) - 1
    fin_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, last_fin), (-1, last_fin), BG_LIGHT),
        ("FONTNAME",   (0, last_fin), (-1, last_fin), "Helvetica-Bold"),
        ("LINEABOVE",  (0, last_fin), (-1, last_fin), 1.0, NAVY),
    ]))
    story.append(fin_tbl)
    story.append(Spacer(1, 0.6 * cm))

    # Degradação
    story.append(Paragraph("Degradação Estimada dos Painéis", styles["SubSectionTitle"]))
    story.append(Paragraph(
        "Taxa de degradação: 2,0% no 1º ano; 0,55%/ano nos anos seguintes. "
        "Perda estimada em relação à meta mensal de 14.000 kWh/usina.",
        styles["Body"],
    ))
    deg_hdr = [["Usina", "Modelo dos Painéis", "Anos em\nOperação",
                "Degradação\nAcumulada (%)", "Perda Mensal\nEstimada (kWh)"]]
    for pid in PLANT_IDS:
        deg = kpis["degradation"][pid]
        deg_hdr.append([
            PLANTS[pid]["name"],
            PLANTS[pid]["panel_model"],
            f"{deg['years']:.1f}",
            f"{deg['cumulative_percent']:.2f}%",
            f"{deg['monthly_loss_kwh']:,.0f}",
        ])
    deg_tbl = _make_table(deg_hdr, col_widths=[2.2*cm, 5.5*cm, 2.0*cm, 2.5*cm, 2.8*cm])
    story.append(deg_tbl)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════
    # SEÇÃO 8 — CONCLUSÃO EXECUTIVA
    # ═══════════════════════════════════════════════════════════
    story.append(Paragraph("8. Conclusão Executiva", styles["SectionTitle"]))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.0))
    story.append(Spacer(1, 0.4 * cm))

    conclusao = analysis.get("conclusao_executiva", "")
    if isinstance(conclusao, str):
        for para in conclusao.split("\n"):
            if para.strip():
                story.append(Paragraph(_xe(para.strip()), styles["ExecSummary"]))
                story.append(Spacer(1, 0.2 * cm))

    story.append(Spacer(1, 1.5 * cm))
    story.append(HRFlowable(width="50%", color=GOLD, thickness=1.5))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        f"Relatório gerado automaticamente em {date.today().strftime('%d/%m/%Y')}. "
        "Dados de geração fornecidos pelo sistema SUNGROW. "
        "Análises assistidas por Inteligência Artificial (Claude AI — Anthropic).",
        styles["FootnoteStyle"],
    ))

    # Build
    doc.build(story, onFirstPage=_add_page_footer, onLaterPages=_add_page_footer)
    return output_path
