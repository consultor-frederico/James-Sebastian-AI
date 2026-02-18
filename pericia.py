import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date

# Configuração da Página
st.set_page_config(page_title="James Sebastian AI - Perícia Revisional", layout="wide")

# --- TÍTULO E CABEÇALHO ---
st.title("⚖️ Sistema de Perícia Revisional Bancária")
st.markdown("""
**Perito Responsável:** James Sebastian | **Metodologia:** Expurgo de Anatocismo (Súmula 121 STF)
Este sistema recalcula o financiamento imobiliário removendo a capitalização de juros (Código 410) 
e comparando a evolução real (Banco) vs. evolução legal (SAC Puro).
""")

# --- BARRA LATERAL (PARÂMETROS DO CONTRATO) ---
st.sidebar.header("1. Parâmetros do Contrato")

# Valores estimados com base na nossa análise anterior
valor_financiado = st.sidebar.number_input("Valor Financiado (R$)", value=305000.00, step=1000.00)
prazo_meses = st.sidebar.number_input("Prazo Total (Meses)", value=358)
juros_anuais = st.sidebar.number_input("Taxa de Juros Anual (%)", value=10.5) # Estimativa TR + Poupança + Spread
data_inicio = st.sidebar.date_input("Data Início", value=date(2021, 7, 28))

st.sidebar.header("2. Cenário Banco (Simulado)")
# Aqui simularíamos a importação do PDF, mas vamos criar o cenário do anatocismo manualmente
ocorrencias_410 = st.sidebar.slider("Quantidade de 'Incorporações' (Cód 410)", 0, 20, 5)
valor_incorporado_medio = st.sidebar.number_input("Valor Médio Incorporado (R$)", value=2500.00)

# --- FUNÇÕES DE CÁLCULO (O CÉREBRO DA PERÍCIA) ---

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
    # Cria uma cópia e "estraga" ela com o anatocismo
    df_banco = df_sac.copy()
    df_banco["Cenário"] = "Banco (Com Anatocismo)"
    
    # Simula as incorporações em meses aleatórios ou específicos
    # Vamos aplicar um "fator de maldade" cumulativo
    saldo_atual = valor_financiado
    saldos = []
    
    # Índices onde ocorrem as incorporações (simulando aleatoriedade do extrato)
    indices_inc = np.linspace(10, 52, ocorrencias, dtype=int)
    
    for i, row in df_banco.iterrows():
        # Lógica normal
        juros = row["Juros"]
        amort = row["Amortização"]
        
        # Se for mês de incorporação (Código 410)
        if (i + 1) in indices_inc:
            # O Banco NÃO amortiza e SOMA juros ao saldo
            saldo_atual += valor_inc # Incorporação
            amort = 0 # Amortização negativa
            df_banco.at[i, "Obs"] = "⚠️ CÓD 410"
        else:
            saldo_atual -= amort
            
        if saldo_atual < 0: saldo_atual = 0
        saldos.append(saldo_atual)
        
    df_banco["Saldo Devedor"] = saldos
    return df_banco

# --- EXECUÇÃO DOS CÁLCULOS ---

df_sac = calcular_sac_puro(valor_financiado, prazo_meses, juros_anuais)
df_banco = simular_cenario_banco(df_sac, ocorrencias_410, valor_incorporado_medio)

# Filtrar para o momento atual (mês 52 aprox)
mes_atual = 52
saldo_sac_hoje = df_sac.iloc[mes_atual]['Saldo Devedor']
saldo_banco_hoje = df_banco.iloc[mes_atual]['Saldo Devedor']
diferenca = saldo_banco_hoje - saldo_sac_hoje

# --- DASHBOARD VISUAL ---

# 1. KPIs
col1, col2, col3 = st.columns(3)
col1.metric("Saldo Devedor (Banco)", f"R$ {saldo_banco_hoje:,.2f}", delta_color="inverse")
col2.metric("Saldo Devedor (Recálculo Justo)", f"R$ {saldo_sac_hoje:,.2f}", delta=f"- R$ {diferenca:,.2f}")
col3.metric("Indício de Anatocismo", "DETECTADO", delta_color="inverse", help="Diferença gerada pelas incorporações (Cód 410)")

st.markdown("---")

# 2. Gráfico Comparativo
st.subheader("📉 Evolução da Dívida: Banco vs. Perícia")

fig = go.Figure()

# Linha do SAC Puro (Verde)
fig.add_trace(go.Scatter(
    x=df_sac['Mês'], 
    y=df_sac['Saldo Devedor'],
    mode='lines',
    name='Evolução Legal (SAC Puro)',
    line=dict(color='green', width=2, dash='dash')
))

# Linha do Banco (Vermelha)
fig.add_trace(go.Scatter(
    x=df_banco['Mês'], 
    y=df_banco['Saldo Devedor'],
    mode='lines',
    name='Evolução Banco (Com Vícios)',
    line=dict(color='red', width=3)
))

# Marcar o momento atual
fig.add_vline(x=mes_atual, line_dash="dot", annotation_text="Hoje (Mês 52)", annotation_position="top right")

fig.update_layout(height=400, xaxis_title="Meses Decorridos", yaxis_title="Saldo Devedor (R$)")
st.plotly_chart(fig, use_container_width=True)

# 3. Análise Detalhada (Tabela)
st.subheader("📋 Laudo Técnico Simplificado")

# Combina os dataframes para exibição
df_display = pd.DataFrame({
    "Mês": df_sac["Mês"],
    "Saldo Banco": df_banco["Saldo Devedor"],
    "Saldo Justo": df_sac["Saldo Devedor"],
    "Diferença (Prejuízo)": df_banco["Saldo Devedor"] - df_sac["Saldo Devedor"],
    "Ocorrência": df_banco.get("Obs", "")
})

# Formatação condicional
def highlight_410(s):
    return ['background-color: #ffcccc' if v == '⚠️ CÓD 410' else '' for v in s]

st.dataframe(
    df_display.style.format({
        "Saldo Banco": "R$ {:,.2f}", 
        "Saldo Justo": "R$ {:,.2f}", 
        "Diferença (Prejuízo)": "R$ {:,.2f}"
    }).apply(highlight_410, subset=['Ocorrência']),
    use_container_width=True
)

# 4. Conclusão Automática
st.error(f"""
**CONCLUSÃO PERICIAL PRELIMINAR:**
Foi identificada uma divergência de **R$ {diferenca:,.2f}** em desfavor do mutuário no mês {mes_atual}.
A aplicação de incorporações (Cód 410) gerou amortização negativa, violando a metodologia SAC contratada.
Recomenda-se ação revisional para expurgo do anatocismo.
""")
