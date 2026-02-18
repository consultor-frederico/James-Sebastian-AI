import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import google.generativeai as genai
from datetime import date, datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="James Sebastian AI - Perícia Revisional", 
    layout="wide",
    page_icon="⚖️"
)

# --- FUNÇÕES DE INTEGRAÇÃO EXTERNA (BACEN & AI) ---

@st.cache_data(ttl=3600) # Cache de 1 hora para não sobrecarregar a API
def obter_indices_bacen():
    """Busca indicadores econômicos reais da API do Banco Central do Brasil"""
    try:
        # Endpoints da API do Bacen (SGS)
        # 11 = Selic, 226 = TR, 433 = IPCA
        apis = {
            "Selic Meta": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json",
            "TR (Mensal)": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.226/dados/ultimos/1?formato=json",
            "IPCA (12m)": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.13522/dados/ultimos/1?formato=json" 
        }
        
        resultados = {}
        for nome, url in apis.items():
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                dado = response.json()[0]
                valor = float(dado['valor'])
                data = dado['data']
                resultados[nome] = (valor, data)
            else:
                resultados[nome] = (0.0, "Erro")
        return resultados
    except Exception as e:
        return None

def gerar_laudo_ia(api_key, dados_pericia):
    """Gera um laudo jurídico formal usando IA (Google Gemini)"""
    if not api_key:
        return "⚠️ Erro: Chave de API da IA não fornecida."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Você é James Sebastian, um perito judicial especialista em contratos bancários e matemática financeira.
        Escreva um LAUDO TÉCNICO PERICIAL JURÍDICO formal com base nos seguintes dados calculados:

        DADOS DO CONTRATO:
        - Valor Financiado: R$ {dados_pericia['valor_financiado']}
        - Prazo: {dados_pericia['prazo']} meses
        - Taxa Contratual: {dados_pericia['taxa_juros']}% a.a.

        ACHADOS DA PERÍCIA (IRREGULARIDADES):
        - Metodologia Aplicada: Expurgo da Capitalização de Juros (Anatocismo) conforme Súmula 121 STF.
        - Irregularidade Detectada: 'Incorporação de Juros' (Código 410) ao saldo devedor.
        - Quantidade de Ocorrências: {dados_pericia['ocorrencias']} meses com amortização negativa.
        
        RESULTADOS FINANCEIROS:
        - Saldo Devedor cobrado pelo Banco: R$ {dados_pericia['saldo_banco']}
        - Saldo Devedor Recalculado (Justo): R$ {dados_pericia['saldo_justo']}
        - PREJUÍZO AO CONSUMIDOR (Diferença): R$ {dados_pericia['diferenca']}

        ESTRUTURA DO LAUDO:
        1. Identificação do Perito
        2. Objeto da Perícia
        3. Metodologia (Citar SAC e Súmula 121 STF)
        4. Quesitos Técnicos (Análise da Incorporação Cód 410)
        5. Conclusão Pericial (Enfatizar o prejuízo financeiro e a descaracterização do SAC).
        
        Use linguagem jurídica adequada, tom imparcial mas firme tecnicamente. Formate em Markdown.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao gerar laudo com IA: {str(e)}"

# --- TÍTULO E CABEÇALHO ---
st.title("⚖️ Sistema de Perícia Revisional Bancária")
st.markdown("""
**Perito Responsável:** James Sebastian AI | **Status:** Online
Sistema de auditoria forense com **integração Bacen** e **Geração de Laudos via IA**.
""")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Configurações da IA")
    api_key = st.text_input("Google Gemini API Key", type="password", help="Cole sua chave API aqui para gerar o laudo automático.")
    st.caption("[Obter Chave Grátis no Google AI Studio](https://aistudio.google.com/app/apikey)")
    
    st.divider()

    st.header("2. Parâmetros do Contrato")
    valor_financiado = st.number_input("Valor Financiado (R$)", value=305000.00, step=1000.00, format="%.2f")
    prazo_meses = st.number_input("Prazo Total (Meses)", value=358)
    juros_anuais = st.number_input("Taxa de Juros Anual (%)", value=10.5)
    
    st.header("3. Cenário Banco (Simulado)")
    ocorrencias_410 = st.slider("Qtd. de 'Incorporações' (Cód 410)", 0, 20, 5)
    valor_incorporado_medio = st.number_input("Valor Médio Incorporado (R$)", value=2500.00, format="%.2f")

# --- DASHBOARD DE MERCADO (LIVE) ---
st.subheader("📈 Indicadores de Mercado (Fonte: Banco Central)")
indices = obter_indices_bacen()

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
if indices:
    col_m1.metric("Selic Meta (Atual)", f"{indices['Selic Meta'][0]}% a.a.")
    col_m2.metric("TR (Último Mês)", f"{indices['TR (Mensal)'][0]}%")
    col_m3.metric("IPCA (Acum. 12m)", f"{indices['IPCA (12m)'][0]}%")
    col_m4.metric("Status API Bacen", "Conectado 🟢")
else:
    st.warning("Não foi possível conectar à API do Banco Central no momento.")

st.divider()

# --- FUNÇÕES DE CÁLCULO (CORE) ---

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
            "Mês": i, "Saldo Devedor": saldo_anterior, "Amortização": amortizacao,
            "Juros": juros, "Prestação": prestacao, "Cenário": "SAC Legal"
        })
    return pd.DataFrame(dados)

def simular_cenario_banco(df_sac, ocorrencias, valor_inc):
    df_banco = df_sac.copy()
    df_banco["Cenário"] = "Banco (Viciado)"
    saldo_atual = valor_financiado
    saldos = []
    indices_inc = np.linspace(10, 52, ocorrencias, dtype=int)
    
    for i, row in df_banco.iterrows():
        amort = row["Amortização"]
        if (i + 1) in indices_inc:
            saldo_atual += valor_inc 
            amort = 0 
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

mes_atual = 52
saldo_sac_hoje = df_sac.iloc[mes_atual]['Saldo Devedor']
saldo_banco_hoje = df_banco.iloc[mes_atual]['Saldo Devedor']
diferenca = saldo_banco_hoje - saldo_sac_hoje

# --- INTERFACE (ABAS) ---
tab1, tab2, tab3 = st.tabs(["📊 Análise Visual", "🤖 Laudo Pericial (IA)", "📑 Dados Detalhados"])

with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Devedor (Banco)", f"R$ {saldo_banco_hoje:,.2f}", delta_color="inverse")
    col2.metric("Saldo Devedor (Justo)", f"R$ {saldo_sac_hoje:,.2f}", delta=f"- R$ {diferenca:,.2f}")
    col3.metric("Indício de Anatocismo", "ALTO RISCO" if ocorrencias_410 > 0 else "BAIXO", delta_color="inverse")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_sac['Mês'], y=df_sac['Saldo Devedor'], mode='lines', name='SAC Puro', line=dict(color='green', dash='dash')))
    fig.add_trace(go.Scatter(x=df_banco['Mês'], y=df_banco['Saldo Devedor'], mode='lines', name='Banco (Com Incorporações)', line=dict(color='red')))
    fig.update_layout(height=400, title="Divergência de Saldo Devedor")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("🤖 Gerador de Laudo Pericial com IA")
    st.info("A Inteligência Artificial analisará os dados calculados e redigirá um laudo jurídico formal.")
    
    if st.button("📝 Escrever Laudo Pericial Agora"):
        if not api_key:
            st.error("Por favor, insira sua API Key do Google Gemini na barra lateral para usar a IA.")
        else:
            with st.spinner("O Perito Virtual (IA) está redigindo o laudo..."):
                # Prepara os dados para a IA
                dados_contexto = {
                    "valor_financiado": f"{valor_financiado:,.2f}",
                    "prazo": prazo_meses,
                    "taxa_juros": juros_anuais,
                    "ocorrencias": ocorrencias_410,
                    "saldo_banco": f"{saldo_banco_hoje:,.2f}",
                    "saldo_justo": f"{saldo_sac_hoje:,.2f}",
                    "diferenca": f"{diferenca:,.2f}"
                }
                laudo_texto = gerar_laudo_ia(api_key, dados_contexto)
                
                st.markdown("### 📄 Laudo Técnico Gerado")
                st.markdown(laudo_texto)
                
                st.download_button(
                    label="📥 Baixar Laudo (TXT)",
                    data=laudo_texto,
                    file_name="laudo_pericial_ia.txt",
                    mime="text/plain"
                )

with tab3:
    st.subheader("Tabela de Evolução Comparativa")
    df_display = pd.DataFrame({
        "Mês": df_sac["Mês"],
        "Saldo Banco": df_banco["Saldo Devedor"],
        "Saldo Justo": df_sac["Saldo Devedor"],
        "Diferença": df_banco["Saldo Devedor"] - df_sac["Saldo Devedor"],
        "Nota": df_banco.get("Obs", "")
    })
    
    def highlight_bad(s):
        return ['background-color: #ffcccc' if v == '⚠️ CÓD 410' else '' for v in s]

    st.dataframe(df_display.style.format({"Saldo Banco": "R$ {:,.2f}", "Saldo Justo": "R$ {:,.2f}", "Diferença": "R$ {:,.2f}"}).apply(highlight_bad, subset=['Nota']), use_container_width=True)
