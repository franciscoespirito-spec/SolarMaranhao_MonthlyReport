"""
Integração com Claude API para geração de análises em linguagem natural.
Gera diagnósticos de causas, riscos, plano de ação e conclusão executiva.
"""
import os
import json

import anthropic

from config import PLANTS, PLANT_IDS, TARGET_MONTHLY_KWH

MESES_PT_FULL_LOCAL = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

SYSTEM_PROMPT = """Você é um analista sênior de energia solar fotovoltaica com mais de 15 anos de experiência em operação e manutenção de usinas solares no Brasil.

Você está analisando dados de um portfólio de 5 usinas solares localizadas na região de Barreirinhas, Maranhão, Brasil. A meta de geração é de 14.000 kWh/mês por usina.

Seu papel é:
1. Interpretar os dados de geração e KPIs fornecidos
2. Identificar causas raiz para variações de desempenho
3. Avaliar riscos operacionais e financeiros
4. Propor ações corretivas concretas e priorizadas
5. Fornecer uma conclusão executiva clara

Regras:
- Escreva em português brasileiro formal, mas acessível
- Seja direto e objetivo
- Use dados numéricos para embasar suas análises
- Classifique riscos como: BAIXO, MÉDIO, ALTO ou CRÍTICO
- Para o plano de ação, use formato estruturado com: ação, prioridade, responsável sugerido, prazo, impacto esperado
- Considere fatores climáticos típicos do Maranhão (região equatorial, estação chuvosa dez-mai, seca jun-nov)
- Considere a degradação natural dos painéis ao longo do tempo"""


def generate_analysis(kpis, monthly_totals_df=None):
    """
    Gera análises usando Claude API.
    Retorna dict com textos para as seções 4, 5, 6, 8 e sumário executivo.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback_analysis(kpis)

    client = anthropic.Anthropic(api_key=api_key)

    data_summary = _build_data_summary(kpis, monthly_totals_df)

    prompt = f"""Analise os seguintes dados de geração solar do portfólio para {MESES_PT_FULL_LOCAL.get(kpis['target_month'], '')}/{kpis['target_year']} e gere as análises solicitadas.

## DADOS DO PORTFÓLIO

{data_summary}

## ANÁLISES SOLICITADAS

Gere as seguintes seções em formato JSON com as chaves indicadas:

1. **"sumario_executivo"**: 3-4 frases com as principais conclusões do mês, incluindo destaque para riscos e performance geral.

2. **"analise_causas"**: Análise separada por tipo de causa:
   - Efeito clima (considerar estação chuvosa/seca do MA)
   - Efeito sazonalidade
   - Efeito degradação natural dos painéis
   - Efeito operacional
   - Efeito falha técnica (dias com geração zero)
   - Efeito indisponibilidade de monitoramento
   Cada causa deve ter: descrição da análise e impacto estimado (alto/médio/baixo/não identificado).

3. **"analise_riscos"**: Lista de riscos com classificação:
   - Risco de não atingir meta mensal
   - Risco de não atingir meta anual
   - Risco de indisponibilidade
   - Risco de perda de receita
   - Risco contratual
   - Risco operacional/reputacional
   Cada risco: descrição, classificação (BAIXO/MÉDIO/ALTO/CRÍTICO), justificativa.

4. **"plano_acao"**: Lista de ações concretas, cada uma com:
   - acao: descrição da ação
   - prioridade: ALTA/MÉDIA/BAIXA
   - responsavel: área/função sugerida
   - prazo: prazo sugerido
   - impacto: impacto esperado
   - status: "Pendente"

5. **"conclusao_executiva"**: 4-6 frases avaliando a saúde do portfólio, quais ativos estão bem, quais em alerta, principal prioridade e recomendação da gestão.

Responda SOMENTE com o JSON válido, sem markdown ou texto adicional."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        # Limpar possíveis delimitadores markdown
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]

        analysis = json.loads(text)
        return analysis

    except Exception as e:
        print(f"Aviso: Falha na API Claude ({e}). Usando análise padrão.")
        return _fallback_analysis(kpis)


def _build_data_summary(kpis, monthly_totals_df=None):
    """Constrói resumo textual dos dados para o prompt."""
    lines = []
    month_name = MESES_PT_FULL_LOCAL.get(kpis["target_month"], "")

    lines.append(f"### Período: {month_name}/{kpis['target_year']}")
    lines.append(f"Meta mensal por usina: {TARGET_MONTHLY_KWH:,.0f} kWh")
    lines.append(f"Dias no mês: {kpis['days_in_month']}")
    lines.append("")

    lines.append("### Geração mensal por usina:")
    for pid in PLANT_IDS:
        p = PLANTS[pid]
        gen = kpis["month_generation"][pid]
        gap = kpis["gap_vs_target"][pid]
        fc = kpis["capacity_factor"][pid]
        sy = kpis["specific_yield"][pid]
        deg = kpis["degradation"][pid]
        yoy = kpis["yoy_comparison"][pid]

        lines.append(f"- {p['name']} ({p['spe']}): {gen:,.1f} kWh | Gap: {gap['percent']:+.1f}% | "
                     f"FC: {fc:.1%} | Yield: {sy:.1f} kWh/kWp | "
                     f"Degradação acumulada: {deg['cumulative_percent']:.1f}% ({deg['years']} anos) | "
                     f"Capacidade: {p['capacity_kwp']} kWp | Início: {p['start_date']}")
        if yoy["previous"] > 0:
            lines.append(f"  Comparativo ano anterior: {yoy['previous']:,.0f} → {yoy['current']:,.0f} kWh ({yoy['change_percent']:+.1f}%)")

    lines.append(f"\nTotal portfólio: {kpis['month_generation']['total']:,.0f} kWh (meta: {TARGET_MONTHLY_KWH * 5:,.0f} kWh)")
    lines.append(f"\n### Ranking: {' > '.join(PLANTS[p]['name'] for p in kpis['ranking'])}")
    lines.append(f"Gap melhor-pior: {kpis['gap_best_worst_percent']:.1f}%")

    lines.append("\n### Acumulado no ano (YTD):")
    for pid in PLANT_IDS:
        ga = kpis["gap_annual"][pid]
        lines.append(f"- {PLANTS[pid]['name']}: {ga['ytd_actual']:,.0f} kWh | "
                     f"Meta YTD: {ga['ytd_target']:,.0f} kWh | Gap: {ga['ytd_gap_percent']:+.1f}% | "
                     f"Projeção anual: {ga['projected_annual']:,.0f} kWh")

    lines.append("\n### Impacto financeiro (1 kWh = R$ 1,00):")
    for pid in PLANT_IDS:
        fin = kpis["financial"][pid]
        if fin["non_generated_kwh"] > 0:
            lines.append(f"- {PLANTS[pid]['name']}: Energia não gerada: {fin['non_generated_kwh']:,.0f} kWh | "
                         f"Receita perdida: R$ {fin['lost_revenue_brl']:,.0f} | "
                         f"Impacto anualizado: R$ {fin['annualized_impact_brl']:,.0f}")
    fin_total = kpis["financial"]["total"]
    lines.append(f"- TOTAL: Receita perdida: R$ {fin_total['lost_revenue_brl']:,.0f} | "
                 f"Impacto anualizado: R$ {fin_total['annualized_impact_brl']:,.0f}")

    # Histórico mensal se disponível
    if monthly_totals_df is not None and not monthly_totals_df.empty:
        lines.append("\n### Histórico mensal (últimos 6 meses com dados):")
        recent = monthly_totals_df[monthly_totals_df["total"] > 0].tail(6)
        for _, row in recent.iterrows():
            m = MESES_PT_FULL_LOCAL.get(int(row["month"]), "")
            vals = " | ".join(f"{PLANTS[pid]['name']}={row[pid]:,.0f}" for pid in PLANT_IDS)
            lines.append(f"- {m}/{int(row['year'])}: {vals} | Total={row['total']:,.0f}")

    return "\n".join(lines)


def _fallback_analysis(kpis):
    """Análise padrão quando a API não está disponível."""
    month_name = MESES_PT_FULL_LOCAL.get(kpis["target_month"], "")
    total = kpis["month_generation"]["total"]
    meta_total = TARGET_MONTHLY_KWH * len(PLANT_IDS)

    best = PLANTS[kpis["best_plant"]]["name"]
    worst = PLANTS[kpis["worst_plant"]]["name"]

    return {
        "sumario_executivo": (
            f"No mês de {month_name}/{kpis['target_year']}, o portfólio gerou {total:,.0f} kWh, "
            f"representando {total/meta_total*100:.1f}% da meta total de {meta_total:,.0f} kWh. "
            f"A melhor performance foi da {best} e a pior da {worst}, "
            f"com gap de {kpis['gap_best_worst_percent']:.1f}% entre elas."
        ),
        "analise_causas": [
            {"causa": "Efeito clima", "descricao": "Análise indisponível - verificar dados meteorológicos da estação INMET A218.", "impacto": "A avaliar"},
            {"causa": "Efeito sazonalidade", "descricao": "Análise indisponível.", "impacto": "A avaliar"},
            {"causa": "Efeito degradação", "descricao": f"Degradação acumulada entre {min(kpis['degradation'][p]['cumulative_percent'] for p in PLANT_IDS):.1f}% e {max(kpis['degradation'][p]['cumulative_percent'] for p in PLANT_IDS):.1f}%.", "impacto": "Baixo"},
            {"causa": "Efeito operacional", "descricao": "Análise indisponível.", "impacto": "A avaliar"},
            {"causa": "Efeito falha técnica", "descricao": "Análise indisponível.", "impacto": "A avaliar"},
            {"causa": "Efeito monitoramento", "descricao": "Análise indisponível.", "impacto": "A avaliar"},
        ],
        "analise_riscos": [
            {"risco": "Não atingir meta mensal", "classificacao": "ALTO" if total < meta_total * 0.85 else "MÉDIO", "justificativa": f"Geração em {total/meta_total*100:.0f}% da meta."},
            {"risco": "Não atingir meta anual", "classificacao": "MÉDIO", "justificativa": "Avaliar tendência dos próximos meses."},
            {"risco": "Indisponibilidade", "classificacao": "MÉDIO", "justificativa": "Verificar dias com geração zero."},
            {"risco": "Perda de receita", "classificacao": "ALTO" if kpis['financial']['total']['lost_revenue_brl'] > 5000 else "MÉDIO", "justificativa": f"Perda estimada de R$ {kpis['financial']['total']['lost_revenue_brl']:,.0f} no mês."},
            {"risco": "Contratual", "classificacao": "BAIXO", "justificativa": "A avaliar."},
            {"risco": "Operacional/reputacional", "classificacao": "BAIXO", "justificativa": "A avaliar."},
        ],
        "plano_acao": [
            {"acao": "Verificar logs dos inversores de todas as usinas", "prioridade": "ALTA", "responsavel": "O&M", "prazo": "48h", "impacto": "Identificar falhas técnicas", "status": "Pendente"},
            {"acao": "Inspeção termográfica dos painéis", "prioridade": "MÉDIA", "responsavel": "O&M", "prazo": "7 dias", "impacto": "Identificar hotspots e defeitos", "status": "Pendente"},
            {"acao": "Revisar cronograma de limpeza preventiva", "prioridade": "MÉDIA", "responsavel": "O&M", "prazo": "15 dias", "impacto": "Recuperar perdas por sujidade", "status": "Pendente"},
        ],
        "conclusao_executiva": (
            f"O portfólio apresentou geração de {total:,.0f} kWh em {month_name}/{kpis['target_year']}, "
            f"ficando {abs(total/meta_total*100 - 100):.1f}% {'abaixo' if total < meta_total else 'acima'} da meta. "
            f"A {best} liderou a geração enquanto a {worst} apresentou o pior desempenho. "
            f"Recomenda-se atenção prioritária às usinas com gap acima de 15% em relação à meta."
        ),
    }
