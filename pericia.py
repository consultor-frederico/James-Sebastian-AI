import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import google.generativeai as genai
import pdfplumber
from datetime import date
import json

# --- CONFIGURAÇÃO DA CHAVE DE API (HARDCODED) ---
# ⚠️ ATENÇÃO: Se este código for para um GitHub PÚBLICO, esta chave ficará exposta.
# O ideal é usar st.secrets, mas para seu uso imediato, está configurada aqui.
GEMINI_API_KEY = "AIzaSyD068i8Vp9R24wwCjrRITsgTjAXo-I5Q-g"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="James Sebastian AI - Perícia Revisional", 
    layout="wide",
    page_icon="⚖️"
)

# --- INICIALIZAÇÃO DE ESTADO (SESSION STATE) ---
# Isso permite que os dados preenchidos pela IA permaneçam na tela
if 'valor_financiado' not in st.session_state: st.session_state.valor_financiado = 305000.00
if 'prazo_meses' not in st.session_state: st.session_state.prazo_meses = 360
if 'juros_anuais' not in st.session_state: st.session_state.juros_anuais = 10.5

# --- FUNÇÕES DE INTEGRAÇÃO ---

@st.cache_data(ttl=3600)
def obter_indices_bacen():
    """Busca indicadores econômicos reais da API do Banco Central"""
    try:
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
                resultados[nome] = (float(dado['valor']), dado['data'])
            else:
                resultados[nome] = (0.0, "Erro")
        return resultados
    except:
        return None

def extrair_texto_pdf(file):
    """Lê o conteúdo de texto de um arquivo PDF carregado"""
    texto_completo = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                texto_completo += page.extract_text() + "\n"
        return texto_completo
    except Exception as e:
        return None

def analisar_documento_ia(texto):
    """Usa o Gemini para ler o contrato e extrair números"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Analise o texto deste contrato bancário/imobiliário e extraia APENAS os seguintes dados em formato JSON:
        1. "valor_financiado": (float, valor total da dívida/mútuo)
        2. "prazo_meses": (int, número total de parcelas)
        3. "taxa_juros_anual": (float, taxa de juros nominal anual)
        
        Se não encontrar algum dado, tente estimar ou coloque 0.
        Retorne APENAS o JSON puro, sem markdown.
        
        Texto do Contrato:
        {texto[:15000]} 
        """
        # Limitamos a 15k caracteres para caber no prompt rápido
        
        response = model.generate_content(prompt)
        # Limpeza básica para garantir que é JSON
        json_str = response.text.replace("```json", "").replace("```", "")
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Erro na extração IA: {e}")
        return None

def gerar_laudo_ia(dados_pericia):
    """Gera o laudo jurídico final"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Você é James Sebastian, perito judicial. Escreva um LAUDO TÉCNICO PERICIAL JURÍDICO (Markdown).
        
        DADOS:
        - Valor: R$ {dados_pericia['valor_financiado']} | Prazo: {dados_pericia['prazo']} meses | Taxa: {dados_pericia['taxa_juros']}% a.a.
        - Irregularidade: Incorporação de Juros (Cód 410) - Anatocismo.
        - Ocorrências: {dados_pericia['ocorrencias']} meses.
        
        FINANCEIRO:
        - Saldo Banco: R$ {dados_pericia['saldo_banco']}
        - Saldo Justo (SAC Puro): R$ {dados_pericia['saldo_justo']}
        - DIFERENÇA (PREJUÍZO): R$ {dados_pericia['diferenca']}
        
        ESTRUTURA:
        1. Objeto da Perícia.
        2. Metodologia (Expurgo Súmula 121 STF).
        3. Quesitos Técnicos (Análise da Incorporação e Amortização Negativa).
        4. Conclusão (Forte e técnica).
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao gerar laudo: {e}"

# --- INTERFACE VISUAL ---

st.title("⚖️ James Sebastian AI - Auditoria Contratual")
st.markdown("**Sistema de Perícia Forense Automatizada** | Integração Bacen & Google Gemini")

# --- BARRA LATERAL (INPUTS E UPLOAD) ---
with st.sidebar:
    st.header("📂 Documentação")
    uploaded_file = st.file_uploader("Subir Contrato/Extrato (PDF)", type="pdf")
    
    if uploaded_file is not None:
        if st.button("✨ Extrair Dados Automaticamente (IA)"):
            with st.spinner("Lendo documento e extraindo parâmetros..."):
                texto = extrair_texto_pdf(uploaded_file)
                if texto:
                    dados_extraidos = analisar_documento_ia(texto)
                    if dados_extraidos:
                        st.session_state.valor_financiado = float(dados_extraidos.get('valor_financiado', 0))
                        st.session_state.prazo_meses = int(dados_extraidos.get('prazo_meses', 0))
                        st.session_state.juros_anuais = float(dados_extraidos.get('taxa_juros_anual', 0))
                        st.success("Dados extraídos com sucesso!")
                        st.rerun() # Recarrega a página com os novos dados
                    else:
                        st.error("IA não conseguiu identificar os padrões.")
                else:
                    st.error("Não foi possível ler o PDF.")

    st.divider()
    st.header("1. Parâmetros do Contrato")
    
    # Inputs conectados ao Session State (permite auto-preenchimento)
    valor_financiado = st.number_input("Valor Financiado (R$)", value=st.session_state.valor_financiado, step=1000.00, format="%.2f")
    prazo_meses = st.number_input("Prazo Total (Meses)", value=st.session_state.prazo_meses)
    juros_anuais = st.number_input("Taxa de Juros Anual (%)", value=st.session_state.juros_anuais)
    
    st.header("2. Cenário de Irregularidades")
    ocorrencias_410 = st.slider("Qtd. Incorporações (Cód 410)", 0, 30, 5)
    valor_incorporado_medio = st.number_input("Valor Médio Incorporado (R$)", value=2500.00)

# --- DASHBOARD BACEN ---
indices = obter_indices_bacen()
if indices:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Selic", f"{indices['Selic Meta'][0]}%")
    c2.metric("TR Mensal", f"{indices['TR (Mensal)'][0]}%")
    c3.metric("IPCA 12m", f"{indices['IPCA (12m)'][0]}%")
    c4.metric("Status API", "Online 🟢")

st.divider()

# --- MOTOR DE CÁLCULO ---
def calcular_sac_puro(valor, meses, taxa_anual):
    taxa_mensal = (1 + taxa_anual/100)**(1/12) - 1
    amortizacao = valor / meses
    saldo = valor
    dados = []
    for i in range(1, meses + 1):
        juros = saldo * taxa_mensal
        saldo -= amortizacao
        if saldo < 0: saldo = 0
        dados.append({"Mês": i, "Saldo Devedor": saldo, "Cenário": "SAC Legal"})
    return pd.DataFrame(dados)

def simular_banco(df_sac, ocorrencias, valor_inc):
    df = df_sac.copy()
    df["Cenário"] = "Banco (Viciado)"
    saldos = []
    saldo_atual = valor_financiado
    indices_inc = np.linspace(10, 50, ocorrencias, dtype=int)
    
    for i in range(len(df)):
        amort = valor_financiado / prazo_meses
        if (i+1) in indices_inc:
            saldo_atual += valor_inc # Anatocismo
        else:
            saldo_atual -= amort
        if saldo_atual < 0: saldo_atual = 0
        saldos.append(saldo_atual)
    df["Saldo Devedor"] = saldos
    return df

# Execução
df_sac = calcular_sac_puro(valor_financiado, prazo_meses, juros_anuais)
df_banco = simular_banco(df_sac, ocorrencias_410, valor_incorporado_medio)

# Resultados Hoje (Mês 52 simulado)
mes_ref = 52 if prazo_meses > 52 else prazo_meses - 1
saldo_sac = df_sac.iloc[mes_ref]['Saldo Devedor']
saldo_banco = df_banco.iloc[mes_ref]['Saldo Devedor']
diferenca = saldo_banco - saldo_sac

# --- ABAS DE RESULTADOS ---
t1, t2, t3 = st.tabs(["📊 Análise Gráfica", "📝 Laudo Jurídico IA", "📂 Dados Brutos"])

with t1:
    col1, col2 = st.columns(2)
    col1.metric("Saldo Banco (Cobrado)", f"R$ {saldo_banco:,.2f}", delta_color="inverse")
    col2.metric("Prejuízo Detectado", f"R$ {diferenca:,.2f}", delta="- Valor a Recuperar", delta_color="normal")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_sac['Mês'], y=df_sac['Saldo Devedor'], name='SAC Justo', line=dict(color='green', dash='dash')))
    fig.add_trace(go.Scatter(x=df_banco['Mês'], y=df_banco['Saldo Devedor'], name='Banco (Anatocismo)', line=dict(color='red')))
    fig.update_layout(title="Evolução do Saldo Devedor: Legal vs Ilegal")
    st.plotly_chart(fig, use_container_width=True)

with t2:
    st.subheader("Gerador de Peças Jurídicas")
    if st.button("📄 Redigir Laudo Pericial Completo"):
        with st.spinner("Analisando jurisprudência e calculando..."):
            dados = {
                "valor_financiado": f"{valor_financiado:,.2f}",
                "prazo": prazo_meses,
                "taxa_juros": juros_anuais,
                "ocorrencias": ocorrencias_410,
                "saldo_banco": f"{saldo_banco:,.2f}",
                "saldo_justo": f"{saldo_sac:,.2f}",
                "diferenca": f"{diferenca:,.2f}"
            }
            texto_laudo = gerar_laudo_ia(dados)
            st.markdown(texto_laudo)
            st.download_button("Baixar .txt", texto_laudo, "laudo_final.txt")

with t3:
    st.dataframe(df_banco)
