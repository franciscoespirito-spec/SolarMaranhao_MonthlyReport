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

2. **"analise_causas"**: Decomposição diagnóstica das variações de geração, separando EXATAMENTE os 6 efeitos abaixo — nessa ordem. Para cada efeito, faça um diagnóstico real com base nos dados fornecidos (não genérico). Quantifique o impacto em kWh quando possível. Use os dados de disponibilidade, histórico YoY e degradação para embasar cada causa.

   Lista OBRIGATÓRIA (exatamente esses 6, nessa ordem):
   1. "Efeito Clima" — variações de irradiação, nebulosidade, chuvas acima/abaixo do esperado para o período em Barreirinhas/MA. Citar se estação chuvosa (dez–mai) ou seca (jun–nov) e comparar com o esperado sazonalmente.
   2. "Efeito Sazonalidade" — variação esperada do mês em relação à média anual histórica. Indicar se o mês é tipicamente forte ou fraco para o local.
   3. "Efeito Degradação Natural" — usar os dados de degradação acumulada fornecidos (% e anos de operação por usina). Estimar a perda de geração em kWh atribuída à degradação no mês.
   4. "Efeito Operacional" — avaliação de práticas de O&M: limpeza, sombreamento, estado dos inversores, manutenções preventivas. Basear-se em variações entre usinas e na dispersão de performance.
   5. "Efeito Falha Técnica" — identificar usinas com dias de geração zero ou abaixo de 50% da média, indicar quantos dias afetados e estimar a perda em kWh.
   6. "Efeito Indisponibilidade de Monitoramento/Medição" — avaliar se há usinas com dados ausentes, inconsistências de leitura ou gaps no histórico que possam distorcer o diagnóstico.

   Cada causa deve retornar um objeto com:
   - "causa": nome do efeito (exatamente como listado acima)
   - "descricao": 2-4 frases de diagnóstico baseado nos dados reais, não genérico
   - "impacto": "Alto" | "Médio" | "Baixo" | "Não identificado"
   - "kwh_estimado": estimativa de kWh de desvio atribuído a essa causa (ex: "-1.800 kWh", "+500 kWh", "Não quantificável"); use sinal negativo para perda, positivo para ganho
   - "evidencia": 1-2 frases citando o dado específico que embasa o diagnóstico (ex: "Usina X teve 4 dias com geração zero; Usina Y gerou 23% abaixo da média do portfólio")

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
            max_tokens=8000,
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

    # Disponibilidade e dados diários
    if monthly_totals_df is not None:
        availability = kpis.get("availability", {})
        if availability:
            lines.append("\n### Disponibilidade (dias com geração > 0):")
            for pid in PLANT_IDS:
                av = availability.get(pid, {})
                lines.append(
                    f"- {PLANTS[pid]['name']}: {av.get('days_with_gen', '-')}/{kpis['days_in_month']} dias "
                    f"({av.get('availability_pct', 0):.1f}%) | "
                    f"Dias zero: {av.get('zero_days', '-')} | "
                    f"Geração diária: min={av.get('daily_min', 0):,.0f} / "
                    f"avg={av.get('daily_avg', 0):,.0f} / "
                    f"max={av.get('daily_max', 0):,.0f} kWh"
                )

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
            {
                "causa": "Efeito Clima",
                "descricao": "Análise indisponível — verificar dados meteorológicos da estação INMET A218 (Barreirinhas). Comparar irradiação registrada com a média histórica do período.",
                "impacto": "Não identificado",
                "kwh_estimado": "Não quantificável",
                "evidencia": "Dados de irradiação não disponíveis para o período.",
            },
            {
                "causa": "Efeito Sazonalidade",
                "descricao": f"O mês de {month_name} encontra-se {'na estação chuvosa (dez–mai)' if kpis['target_month'] in range(1,6) or kpis['target_month'] == 12 else 'na estação seca (jun–nov)'} em Barreirinhas/MA. Análise detalhada requer histórico de irradiação mensal.",
                "impacto": "Médio",
                "kwh_estimado": "Não quantificável",
                "evidencia": "Sazonalidade climática do Maranhão — estação chuvosa reduz tipicamente 15–25% na geração.",
            },
            {
                "causa": "Efeito Degradação Natural",
                "descricao": f"A degradação acumulada das usinas varia de {min(kpis['degradation'][p]['cumulative_percent'] for p in PLANT_IDS):.1f}% a {max(kpis['degradation'][p]['cumulative_percent'] for p in PLANT_IDS):.1f}%, com tempo de operação entre {min(kpis['degradation'][p]['years'] for p in PLANT_IDS):.1f} e {max(kpis['degradation'][p]['years'] for p in PLANT_IDS):.1f} anos. Impacto esperado e controlável.",
                "impacto": "Baixo",
                "kwh_estimado": f"-{sum(kpis['degradation'][p]['monthly_loss_kwh'] for p in PLANT_IDS):,.0f} kWh (portfólio)",
                "evidencia": f"Degradação ano 1 de 2,0% e 0,55%/ano subsequente; usinas com {min(kpis['degradation'][p]['years'] for p in PLANT_IDS):.1f}–{max(kpis['degradation'][p]['years'] for p in PLANT_IDS):.1f} anos de operação.",
            },
            {
                "causa": "Efeito Operacional",
                "descricao": f"Gap entre melhor e pior usina do portfólio: {kpis['gap_best_worst_percent']:.1f}%. Diferenças acima de 10% sugerem variações operacionais como sujidade, sombreamento parcial ou ajuste de inclinação. Recomenda-se inspeção nas usinas abaixo da média.",
                "impacto": "Médio" if kpis["gap_best_worst_percent"] > 10 else "Baixo",
                "kwh_estimado": "Não quantificável sem inspeção",
                "evidencia": f"{PLANTS[kpis['best_plant']]['name']} gerou {kpis['month_generation'][kpis['best_plant']]:,.0f} kWh; {PLANTS[kpis['worst_plant']]['name']} gerou {kpis['month_generation'][kpis['worst_plant']]:,.0f} kWh.",
            },
            {
                "causa": "Efeito Falha Técnica",
                "descricao": "Análise indisponível — verificar logs dos inversores e histórico de alarmes. Identificar usinas com dias de geração zero ou abaixo de 50% da média diária do portfólio.",
                "impacto": "Não identificado",
                "kwh_estimado": "Não quantificável",
                "evidencia": "Verificar disponibilidade por usina na seção de KPIs acima.",
            },
            {
                "causa": "Efeito Indisponibilidade de Monitoramento/Medição",
                "descricao": "Análise indisponível — verificar consistência das leituras no sistema de monitoramento. Gaps de dados podem subestimar a geração real ou mascarar falhas.",
                "impacto": "Não identificado",
                "kwh_estimado": "Não quantificável",
                "evidencia": "Confrontar leituras do medidor de energia com os dados do inversor para validação.",
            },
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
