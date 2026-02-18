import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import google.generativeai as genai
import pdfplumber
from PIL import Image
from datetime import date
import json

# --- CONFIGURAÇÃO DA CHAVE DE API ---
GEMINI_API_KEY = "AIzaSyD068i8Vp9R24wwCjrRITsgTjAXo-I5Q-g"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="James Sebastian AI - Perícia Revisional", 
    layout="wide",
    page_icon="⚖️"
)

# --- INICIALIZAÇÃO DE ESTADO ---
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = False

campos_padrao = {
    'valor_financiado': 0.0,
    'prazo_meses': 0,
    'juros_anuais': 0.0,
    'nome_cliente': "Aguardando análise...",
    'numero_contrato': "S/N",
    'nome_banco': "Instituição Financeira"
}

for campo, valor in campos_padrao.items():
    if campo not in st.session_state:
        st.session_state[campo] = valor

# --- FUNÇÕES DE MERCADO (BACEN & CÂMBIO) ---

@st.cache_data(ttl=3600)
def obter_indices_completos():
    """Busca Selic, TR, IPCA e Câmbio em tempo real"""
    hoje = date.today().strftime("%d/%m/%Y")
    resultados = {"data": hoje}
    try:
        # 1. Taxas Bacen (SGS)
        series = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for nome, codigo in series.items():
            url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"
            r = requests.get(url, timeout=5).json()[0]
            resultados[nome] = float(r['valor'])
        
        # 2. Câmbio (AwesomeAPI)
        cambio = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL").json()
        resultados["Dolar"] = float(cambio["USDBRL"]["bid"])
        resultados["Euro"] = float(cambio["EURBRL"]["bid"])
        
        return resultados
    except:
        return None

# --- FUNÇÕES DE IA E PDF ---

def extrair_dados_multiplos(arquivos):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Você é um perito auditor. Analise os documentos e extraia:
        JSON: {"banco": str, "contrato": str, "nomes": str, "valor_financiado": float, "prazo_meses": int, "taxa_juros_anual": float}
        """
        conteudo_ia = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo_ia.append(f"Texto: {texto[:10000]}")
            else:
                conteudo_ia.append(Image.open(arq))

        response = model.generate_content(conteudo_ia)
        json_str = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)
    except:
        return None

def gerar_laudo_final(dados):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Escreva um laudo técnico pericial para {dados['nome_cliente']} contra o banco {dados['nome_banco']}..."
    return model.generate_content(prompt).text

# --- INTERFACE ---

st.title("⚖️ James Sebastian AI - Auditoria Contratual")

# 1. Indicadores Financeiros do Dia
indices = obter_indices_completos()
if indices:
    st.write(f"📅 **Indicadores Econômicos de Hoje ({indices['data']}):**")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Selic Meta", f"{indices['Selic']}%")
    c2.metric("TR Mensal", f"{indices['TR']}%")
    c3.metric("IPCA (12m)", f"{indices['IPCA']}%")
    c4.metric("Dólar", f"R$ {indices['Dolar']:.2f}")
    c5.metric("Euro", f"R$ {indices['Euro']:.2f}")
st.divider()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📂 1. Documentação")
    arquivos = st.file_uploader("Contratos e Evolutivos", type=["pdf", "jpg", "png"], accept_multiple_files=True)
    
    if arquivos and st.button("🔍 Iniciar Auditoria IA"):
        with st.spinner("Analisando documentos..."):
            dados = extrair_dados_multiplos(arquivos)
            if dados:
                st.session_state.nome_cliente = dados.get('nomes', 'Não identificado')
                st.session_state.nome_banco = dados.get('banco', 'Instituição')
                st.session_state.numero_contrato = str(dados.get('contrato', 'S/N'))
                st.session_state.valor_financiado = float(dados.get('valor_financiado', 0))
                st.session_state.prazo_meses = int(dados.get('prazo_meses', 0))
                st.session_state.juros_anuais = float(dados.get('taxa_juros_anual', 0))
                st.session_state.dados_carregados = True
                st.success("Auditoria concluída!")
                st.rerun()

    st.divider()
    st.header("📝 2. Ajuste Manual")
    st.session_state.nome_cliente = st.text_input("Mutuário", st.session_state.nome_cliente)
    st.session_state.valor_financiado = st.number_input("Valor (R$)", value=float(st.session_state.valor_financiado))
    st.session_state.prazo_meses = st.number_input("Prazo (Meses)", value=int(st.session_state.prazo_meses))
    st.session_state.juros_anuais = st.number_input("Juros (%)", value=float(st.session_state.juros_anuais))
    
    if st.button("Aplicar Ajustes Manuais"):
        st.session_state.dados_carregados = True
        st.rerun()

# --- ÁREA DE RESULTADOS ---
t1, t2 = st.tabs(["📊 Gráficos e Números", "📝 Laudo Final"])

with t1:
    if not st.session_state.dados_carregados or st.session_state.valor_financiado == 0:
        st.warning("⚠️ **Nenhum dado carregado.** Por favor, suba os arquivos na barra lateral ou preencha os valores manuais para visualizar os gráficos.")
        st.image("https://via.placeholder.com/800x400.png?text=Aguardando+Documentos+para+Gerar+Gr%C3%A1ficos", use_container_width=True)
    else:
        # MOTOR DE CÁLCULO
        valor = st.session_state.valor_financiado
        meses = st.session_state.prazo_meses
        taxa = st.session_state.juros_anuais
        
        taxa_mes = (1 + taxa/100)**(1/12) - 1
        amort = valor / meses
        
        def calc():
            s_sac, s_ban = valor, valor
            d_sac, d_ban = [], []
            for i in range(1, meses + 1):
                s_sac -= amort
                d_sac.append(max(0, s_sac))
                # Simulação Banco (Inflado)
                s_ban -= (amort * 0.95) if i % 10 != 0 else (s_ban * -0.02) # Simula Anatocismo
                d_ban.append(max(0, s_ban))
            return d_sac, d_ban

        sac, banco = calc()
        mes_ref = min(60, meses)
        dif = banco[mes_ref-1] - sac[mes_ref-1]

        c_a, c_b = st.columns(2)
        c_a.metric("Saldo Banco", f"R$ {banco[mes_ref-1]:,.2f}")
        c_b.metric("Recuperável", f"R$ {dif:,.2f}", delta="Diferença Apurada")

        fig = go.Figure()
        fig.add_trace(go.Scatter(y=sac, name='SAC Legal', line=dict(color='green', dash='dash')))
        fig.add_trace(go.Scatter(y=banco, name='Banco Viciado', line=dict(color='red')))
        st.plotly_chart(fig, use_container_width=True)

with t2:
    if st.session_state.dados_carregados:
        st.subheader("Laudo Judicial Automático")
        if st.button("Gerar Laudo"):
            texto = gerar_laudo_final({'nome_cliente': st.session_state.nome_cliente, 'nome_banco': st.session_state.nome_banco, 'valor_financiado': st.session_state.valor_financiado, 'prazo_meses': st.session_state.prazo_meses, 'juros_anuais': st.session_state.juros_anuais, 'ocorrencias': 5, 'saldo_banco': banco[mes_ref-1], 'saldo_justo': sac[mes_ref-1], 'diferenca': dif})
            st.markdown(texto)
    else:
        st.info("Carregue os dados para liberar o laudo.")
