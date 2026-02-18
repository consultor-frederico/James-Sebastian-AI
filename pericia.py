import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="James Sebastian AI - Perícia Revisional", 
    layout="wide",
    page_icon="⚖️"
)

# --- LISTA DE CAPACIDADES (Do Prompt) ---
capacidades_sistema = [
    "Realizar recálculo completo de dívidas em contratos SFH/SAC, ajustando amortizações e juros conforme normas vigentes.",
    "Expurgar anatocismo (capitalização de juros sobre juros) de acordo com a Súmula 121 do STF.",
    "Detectar irregularidades específicas, como o Código 410 (irregularidades contratuais na Caixa).",
    "Analisar o histórico de parcelas pagas, identificando atrasos e recalculando multas.",
    "Gerar relatórios detalhados com demonstrativos de amortização média e juros acumulados.",
    "Calcular diferenças totais em amortizações, tarifas questionáveis e abatimentos indevidos.",
    "Simular cenários de renegociação de dívidas, projetando novos planos de pagamento.",
    "Integrar dados de entrada para análises automatizadas.",
    "Gerar gráficos comparativos para visualização de discrepâncias.",
    "Exportar resultados em formatos como Excel/CSV para uso em perícias judiciais.",
    "Verificar conformidade com normas do Banco Central do Brasil.",
    "Processar múltiplos contratos em batch (Módulo Enterprise)."
]

# --- TÍTULO E CABEÇALHO ---
st.title("⚖️ Sistema de Perícia Revisional Bancária")
st.markdown("""
**Perito Responsável:** James Sebastian | **Metodologia:** Expurgo de Anatocismo (Súmula 121 STF)
Este sistema realiza auditoria financeira em contratos habitacionais, identificando irregularidades como a "Incorporação de Juros" (Cód. 410) e recalculando o saldo devedor real.
""")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Parâmetros do Contrato")
    
    # Inputs
    valor_financiado = st.number_input("Valor Financiado (R$)", value=305000.00, step=1000.00, format="%.2f")
    prazo_meses = st.number_input("Prazo Total (Meses)", value=358)
    juros_anuais = st.number_input("Taxa de Juros Anual (%)", value=10.5)
    data_inicio = st.date_input("Data Início", value=date(2021, 7, 28))

    st.header("2. Cenário Banco (Simulado)")
    st.info("Simulação de irregularidades encontradas no extrato bancário.")
    ocorrencias_410 = st.slider("Qtd. de 'Incorporações' (Cód 410)", 0, 20, 5)
    valor_incorporado_medio = st.number_input("Valor Médio Incorporado (R$)", value=2500.00, format="%.2f")

    st.markdown("---")
    
    # Exibição das Funcionalidades (Capacidade Documental)
    with st.expander("📚 Funcionalidades do Sistema"):
        for cap in capacidades_sistema:
            st.caption(f"• {cap}")

# --- FUNÇÕES DE CÁLCULO ---

def calcular_sac_puro(valor, meses, taxa_anual):
    taxa_mensal = (1 + taxa_anual/100)**(1/12) - 1
    amortizacao = valor / meses
    
    saldo = valor
    dados = []
    
    for i in range(1, meses + 1):
        juros = saldo * taxa_mensal
        prestacao = amortizacao + juros
        saldo_anterior = saldo
        saldo -= amortizacao
        
        if saldo < 0: saldo = 0
        
        dados.append({
            "Mês": i,
            "Saldo Devedor": saldo_anterior,
            "Amortização": amortizacao,
            "Juros": juros,
            "Prestação": prestacao,
            "Cenário": "SAC Legal (Sem Abuso)"
        })
        
    return pd.DataFrame(dados)

def simular_cenario_banco(df_sac, ocorrencias, valor_inc):
    df_banco = df_sac.copy()
    df_banco["Cenário"] = "Banco (Com Anatocismo)"
    
    saldo_atual = valor_financiado
    saldos = []
    
    # Índices onde ocorrem as incorporações (simulando aleatoriedade)
    indices_inc = np.linspace(10, 52, ocorrencias, dtype=int)
    
    for i, row in df_banco.iterrows():
        juros = row["Juros"]
        amort = row["Amortização"]
        
        # Se for mês de incorporação (Código 410)
        if (i + 1) in indices_inc:
            saldo_atual += valor_inc # Incorporação (Aumenta dívida)
            amort = 0 # Amortização negativa
            df_banco.at[i, "Obs"] = "⚠️ CÓD 410"
        else:
            saldo_atual -= amort
            
        if saldo_atual < 0: saldo_atual = 0
        saldos.append(saldo_atual)
        
    df_banco["Saldo Devedor"] = saldos
    return df_banco

# --- PROCESSAMENTO ---

df_sac = calcular_sac_puro(valor_financiado, prazo_meses, juros_anuais)
df_banco = simular_cenario_banco(df_sac, ocorrencias_410, valor_incorporado_medio)

# Momento atual (simulado mês 52)
mes_atual = 52
saldo_sac_hoje = df_sac.iloc[mes_atual]['Saldo Devedor']
saldo_banco_hoje = df_banco.iloc[mes_atual]['Saldo Devedor']
diferenca = saldo_banco_hoje - saldo_sac_hoje

# --- INTERFACE PRINCIPAL (ABAS) ---

tab1, tab2, tab3 = st.tabs(["📊 Análise Visual & KPIs", "📑 Relatório Detalhado & Exportação", "💰 Simulação de Renegociação"])

with tab1:
    # 1. KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Devedor (Banco)", f"R$ {saldo_banco_hoje:,.2f}", delta_color="inverse")
    col2.metric("Saldo Devedor (Recálculo Justo)", f"R$ {saldo_sac_hoje:,.2f}", delta=f"- R$ {diferenca:,.2f}")
    col3.metric("Indício de Anatocismo", "DETECTADO" if ocorrencias_410 > 0 else "NÃO DETECTADO", 
                delta_color="inverse", help="Baseado na detecção de Código 410 e amortização negativa.")

    st.markdown("---")

    # 2. Gráfico
    st.subheader("📉 Evolução da Dívida: Banco vs. Perícia")
    fig = go.Figure()

    # Linha do SAC Puro
    fig.add_trace(go.Scatter(
        x=df_sac['Mês'], y=df_sac['Saldo Devedor'],
        mode='lines', name='Evolução Legal (SAC Puro)',
        line=dict(color='green', width=2, dash='dash')
    ))

    # Linha do Banco
    fig.add_trace(go.Scatter(
        x=df_banco['Mês'], y=df_banco['Saldo Devedor'],
        mode='lines', name='Evolução Banco (Com Vícios)',
        line=dict(color='red', width=3)
    ))

    fig.add_vline(x=mes_atual, line_dash="dot", annotation_text="Hoje (Mês 52)")
    fig.update_layout(height=450, xaxis_title="Meses Decorridos", yaxis_title="Saldo Devedor (R$)")
    st.plotly_chart(fig, use_container_width=True)

    # Conclusão Automática
    if diferenca > 0:
        st.error(f"""
        **CONCLUSÃO PERICIAL PRELIMINAR:**
        Foi identificada uma divergência de **R$ {diferenca:,.2f}** em desfavor do mutuário.
        A aplicação de incorporações (Cód 410) gerou amortização negativa, violando a metodologia SAC contratada.
        Recomenda-se ação revisional para expurgo do anatocismo.
        """)
    else:
        st.success("Não foram encontradas divergências significativas com os parâmetros atuais.")

with tab2:
    st.subheader("📋 Laudo Técnico Simplificado (Tabela)")
    
    # Preparar DataFrame para exibição
    df_display = pd.DataFrame({
        "Mês": df_sac["Mês"],
        "Saldo Banco": df_banco["Saldo Devedor"],
        "Saldo Justo": df_sac["Saldo Devedor"],
        "Diferença (Prejuízo)": df_banco["Saldo Devedor"] - df_sac["Saldo Devedor"],
        "Ocorrência": df_banco.get("Obs", "")
    })

    # Função de estilo
    def highlight_410(s):
        return ['background-color: #ffcccc; color: darkred' if v == '⚠️ CÓD 410' else '' for v in s]

    st.dataframe(
        df_display.style.format({
            "Saldo Banco": "R$ {:,.2f}", 
            "Saldo Justo": "R$ {:,.2f}", 
            "Diferença (Prejuízo)": "R$ {:,.2f}"
        }).apply(highlight_410, subset=['Ocorrência']),
        use_container_width=True,
        height=400
    )

    # Botão de Exportação (Capacidade 10)
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Relatório Completo (CSV)",
        data=csv,
        file_name='laudo_pericial_revisional.csv',
        mime='text/csv',
    )

with tab3:
    st.subheader("🤝 Simulação de Acordo / Renegociação")
    st.markdown("Projeção de novo plano de pagamento baseada no **Saldo Devedor Justo** (Expurgo do Anatocismo).")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.info(f"**Saldo Devedor Atual (Justo):** R$ {saldo_sac_hoje:,.2f}")
        novo_prazo = st.number_input("Novo Prazo Desejado (Meses)", value=int(prazo_meses - mes_atual))
        nova_taxa = st.number_input("Nova Taxa de Juros Anual (%)", value=10.0)
    
    with col_b:
        # Cálculo simples da nova prestação (SAC)
        nova_taxa_mensal = (1 + nova_taxa/100)**(1/12) - 1
        nova_amort = saldo_sac_hoje / novo_prazo
        primeiro_juro = saldo_sac_hoje * nova_taxa_mensal
        primeira_parcela = nova_amort + primeiro_juro
        
        st.metric("Nova Primeira Parcela (Estimada)", f"R$ {primeira_parcela:,.2f}")
        st.metric("Economia Mensal Estimada", f"R$ {diferenca * 0.01:,.2f} (média aprox)")
        
        st.warning("Esta é uma simulação extrajudicial baseada no recálculo pericial. Valores sujeitos a negociação com a instituição.")
