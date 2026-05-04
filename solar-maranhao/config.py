"""
Configuração estática do sistema de relatórios de geração solar.
Metadados das usinas, constantes, mapeamento Excel.
"""
from datetime import date

# ──────────────────────────────────────────────
# Metadados das Usinas
# ──────────────────────────────────────────────

PLANTS = {
    "spe1": {
        "name": "Usina 1",
        "spe": "SPE 1",
        "sheet_name": "USINA 01 - Barreirinhas",
        "address": "MA 315, 20.5K",
        "municipality": "Barreirinhas",
        "coords": (-2.758471, -42.684936),
        "capacity_kwp": 106.08,
        "panel_count": 208,
        "panel_model": "TRINA SOLAR VERTEX 510Wp",
        "inverter_model": "SUNGROW SG40CX (40kW) + SG33CX (33kW)",
        "start_date": date(2023, 1, 31),
        "degradation_year1": 0.02,
        "degradation_annual": 0.0055,
    },
    "spe2": {
        "name": "Usina 2",
        "spe": "SPE 2",
        "sheet_name": "USINA 02 - Barreirinhas",
        "address": "MA 315, 21.8K",
        "municipality": "Paulino Neves",
        "coords": (-2.759689, -42.673167),
        "capacity_kwp": 106.15,
        "panel_count": 193,
        "panel_model": "Canadian HiKu6 Mono PERC 550Wp",
        "inverter_model": "SUNGROW SG75CX (75kW)",
        "start_date": date(2024, 1, 3),
        "degradation_year1": 0.02,
        "degradation_annual": 0.0055,
    },
    "spe3": {
        "name": "Usina 3",
        "spe": "SPE 3",
        "sheet_name": "USINA 03 - Barreirinhas",
        "address": "Rua Projetada, s/n - Mangaba",
        "municipality": "Barreirinhas",
        "coords": (-2.735578, -42.764591),
        "capacity_kwp": 106.15,
        "panel_count": 193,
        "panel_model": "Canadian HiKu6 Mono PERC 550Wp",
        "inverter_model": "SUNGROW SG75CX (75kW)",
        "start_date": date(2024, 8, 23),
        "degradation_year1": 0.02,
        "degradation_annual": 0.0055,
    },
    "spe5": {
        "name": "Usina 5",
        "spe": "SPE 5",
        "sheet_name": "USINA 05 - Barreirinhas",
        "address": "Rua Projetada, s/n - Pv. Guajiru",
        "municipality": "Barreirinhas",
        "coords": (-2.785010, -42.813006),
        "capacity_kwp": 106.15,
        "panel_count": 193,
        "panel_model": "Canadian HiKu6 Mono PERC 550Wp",
        "inverter_model": "SUNGROW SG75CX (75kW)",
        "start_date": date(2024, 1, 3),
        "degradation_year1": 0.02,
        "degradation_annual": 0.0055,
    },
    "spe6": {
        "name": "Usina 6",
        "spe": "SPE 6",
        "sheet_name": "USINA 06 - Barreirinhas",
        "address": "MA-315 KM 12,180 S/N",
        "municipality": "Barreirinhas",
        "coords": (-2.750074, -42.764540),
        "capacity_kwp": 106.15,
        "panel_count": 193,
        "panel_model": "Canadian HiKu6 Mono PERC 550Wp",
        "inverter_model": "SUNGROW SG75CX (75kW)",
        "start_date": date(2024, 1, 3),
        "degradation_year1": 0.02,
        "degradation_annual": 0.0055,
    },
}

PLANT_IDS = ["spe1", "spe2", "spe3", "spe5", "spe6"]

TOTAL_CAPACITY_KWP = sum(p["capacity_kwp"] for p in PLANTS.values())

# ──────────────────────────────────────────────
# Estação Meteorológica
# ──────────────────────────────────────────────

WEATHER_STATION = {
    "name": "INMET A218 - Preguiças",
    "coords": (-2.59247, -42.7071),
    "state": "MA",
}

# ──────────────────────────────────────────────
# Metas e Constantes
# ──────────────────────────────────────────────

TARGET_MONTHLY_KWH = 14_000       # Meta mensal por usina (kWh)
TARGET_TOLERANCE = 0.15            # ±15%
TARGET_ANNUAL_KWH = 168_000        # Meta anual por usina (kWh)
KWH_TO_BRL = 1.0                   # 1 kWh = R$ 1,00

# ──────────────────────────────────────────────
# Email
# ──────────────────────────────────────────────

RECIPIENT_EMAIL = "francisco.espirito@gmail.com"

# ──────────────────────────────────────────────
# Mapeamento de colunas Excel por ano
# Cada entrada: (col_date, col_generation) para dados diários
# e (col_summary_start, row_summary) para resumo mensal
# ──────────────────────────────────────────────

# Colunas base para dados diários em cada seção anual (todas as usinas exceto offset da Usina 05 nos anos antigos)
EXCEL_YEAR_COLUMNS = {
    2023: {"date_col": "A", "gen_col": "B", "summary_start_col": "H", "summary_desc_col": "H", "month_cols_start": "I"},
    2024: {"date_col": "Y", "gen_col": "Z", "summary_start_col": "AG", "summary_desc_col": "AG", "month_cols_start": "AH"},
    2025: {"date_col": "AX", "gen_col": "AY", "summary_start_col": "BF", "summary_desc_col": "BF", "month_cols_start": "BG"},
    2026: {"date_col": "BZ", "gen_col": "CA", "summary_start_col": "CH", "summary_desc_col": "CH", "month_cols_start": "CI"},
}

# Mapeamento de colunas mensais no resumo (2026): CI=Jan, CJ=Feb, CK=Mar, CL=Apr, ...
MONTH_OFFSET_2026 = {1: "CI", 2: "CJ", 3: "CK", 4: "CL", 5: "CM", 6: "CN",
                     7: "CO", 8: "CP", 9: "CQ", 10: "CR", 11: "CS", 12: "CT"}
TOTAL_COL_2026 = "CU"

# Sumario: colunas com histórico mensal por SPE
SUMARIO_MONTHLY_COLS = {
    "date_col": "AS",
    "spe1": "AT",
    "spe2": "AU",
    "spe3": "AV",
    "spe5": "AW",
    "spe6": "AX",
}
SUMARIO_MONTHLY_START_ROW = 5
SUMARIO_MONTHLY_END_ROW = 52

# Sumario: KPIs live (linhas 5-11, colunas E-K)
SUMARIO_KPI_COL_MAP = {
    "desc": "E",
    "spe1": "F",
    "spe2": "G",
    "spe3": "H",
    "spe5": "I",
    "spe6": "J",
    "total": "K",
}

# Paleta profissional — estilo BIG4/McKinsey
COLORS = {
    "navy":        "#1B2A4A",   # Azul marinho — headers, títulos
    "navy_med":    "#2C5282",   # Azul marinho médio
    "gold":        "#C9A84C",   # Dourado — destaques, separadores
    "gold_light":  "#FBF3DC",   # Dourado claro — fundo destaques
    "charcoal":    "#2D3748",   # Cinza escuro — texto corpo
    "steel":       "#718096",   # Cinza aço — legendas
    "silver":      "#CBD5E0",   # Prata — bordas
    "bg_alt":      "#F7F9FC",   # Fundo claro — linhas alternadas
    "green":       "#276749",   # Verde escuro — status positivo
    "green_bg":    "#C6F6D5",   # Verde claro — fundo positivo
    "red":         "#9B2335",   # Vermelho escuro — status negativo
    "red_bg":      "#FED7D7",   # Vermelho claro — fundo negativo
    "amber":       "#B7791F",   # Âmbar — status atenção
    "amber_bg":    "#FEFCBF",   # Âmbar claro — fundo atenção
    "white":       "#FFFFFF",
}

# Paleta de cores por usina — profissional, sem cores saturadas
PLANT_COLORS = {
    "spe1": "#2C5282",   # azul profundo
    "spe2": "#276749",   # verde escuro
    "spe3": "#C05621",   # laranja escuro
    "spe5": "#9B2335",   # vermelho escuro
    "spe6": "#553C9A",   # roxo escuro
}

# Caminho do Excel
EXCEL_PATH = "Historico Geracao Solar Maranhao 2026.xlsx"
OUTPUT_DIR = "output"
