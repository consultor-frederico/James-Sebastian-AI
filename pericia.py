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

# Campos iniciam vazios para preenchimento manual ou via IA
campos_init = {
    'nome_cliente': "",
    'nome_banco': "",
    'numero_contrato': "",
    'valor_financiado': 0.0,
    'prazo_meses': 0,
    'juros_anuais': 0.0
}

for campo, valor in campos_init.items():
    if campo not in st.session_state:
        st.session_state[campo] = valor

# --- FUNÇÃO PARA BUSCA DINÂMICA DO MODELO (Resolve Erro 404) ---
def buscar_melhor_modelo():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Tenta as versões mais estáveis primeiro
        prioridades = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-flash-latest']
        for modelo in prioridades:
            if modelo in modelos_disponiveis: return modelo
        return 'gemini-1.5-flash'
    except:
        return 'gemini-1.5-flash'

# --- FUNÇÕES DE MERCADO (Dólar, Euro e Bacen) ---
@st.cache_data(ttl=3600)
def obter_indices_completos():
    hoje = date.today().strftime("%d/%m/%Y")
    res = {"data": hoje, "Selic": 11.25, "TR": 0.082, "IPCA": 4.51, "Dolar": 5.0, "Euro": 5.4}
    try:
        # Bacen
        series = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for nome, cod in series.items():
            r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/1?formato=json", timeout=3)
            if r.status_code == 200: res[nome] = float(r.json()[0]['valor'])
        # Câmbio
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=3).json()
        res["Dolar"] = float(c["USDBRL"]["bid"])
        res["Euro"] = float(c["EURBRL"]["bid"])
    except: pass 
    return res

# --- FUNÇÕES DE IA ---
def extrair_dados_ia(arquivos):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        modelo_nome = buscar_melhor_modelo()
        model = genai.GenerativeModel(modelo_nome)
        prompt = "Analise os documentos e extraia um JSON: {'banco': str, 'contrato': str, 'nomes': str, 'valor_financiado': float, 'prazo_meses': int, 'taxa_juros_anual': float}"
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Texto: {texto[:8000]}")
            else: conteudo.append(Image.open(arq))
        response = model.generate_content(conteudo)
        txt = response.text.strip()
        if "```json" in txt: txt = txt.split("```json")[1].split("```")[0]
        elif "```" in txt: txt = txt.split("```")[1].split("```")[0]
        return json.loads(txt)
    except: return None

# --- INTERFACE ---
st.title("⚖️ James Sebastian AI - Auditoria Contratual")
indices = obter_indices_completos()
st.write(f"📅 **Indicadores Econômicos de Hoje ({indices['data']}):**")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Selic", f"{indices['Selic']}%")
c2.metric("TR", f"{indices['TR']}%")
c3.metric("IPCA", f"{indices['IPCA']}%")
c4.metric("Dólar", f"R$ {indices['Dolar']:.2f}")
c5.metric("Euro", f"R$ {indices['Euro']:.2f}")
st.divider()

with st.sidebar:
    st.header("📂 1. Documentação")
    arquivos = st.file_uploader("Contratos e Evolutivos", type=["pdf", "jpg", "png"], accept_multiple_files=True)
    if arquivos and st.button("🔍 Iniciar Auditoria IA"):
        with st.spinner("Analisando documentos..."):
            res = extrair_dados_ia(arquivos)
            if res:
                st.session_state.nome_cliente = res.get('nomes') or ""
                st.session_state.nome_banco = res.get('banco') or ""
                st.session_state.numero_contrato = str(res.get('contrato') or "")
                st.session_state.valor_financiado = float(res.get('valor_financiado') or 0.0)
                st.session_state.prazo_meses = int(res.get('prazo_meses') or 0)
                st.session_state.juros_anuais = float(res.get('taxa_juros_anual') or 0.0)
                st.session_state.dados_carregados = True
                st.rerun()

    st.divider()
    st.header("📝 2. Dados do Contrato")
    st.session_state.nome_cliente = st.text_input("Mutuário", st.session_state.nome_cliente)
    st.session_state.valor_financiado = st.number_input("Valor Original", value=float(st.session_state.valor_financiado))
    st.session_state.prazo_meses = st.number_input("Prazo", value=int(st.session_state.prazo_meses))
    st.session_state.juros_anuais = st.number_input("Juros (%)", value=float(st.session_state.juros_anuais))
    if st.button("🔄 Atualizar Cálculos"): st.session_state.dados_carregados = True

t1, t2 = st.tabs(["📊 Evolução e Perícia", "📝 Laudo Jurídico"])
with t1:
    if not st.session_state.dados_carregados or st.session_state.valor_financiado == 0:
        st.info("💡 Suba o contrato para análise automática ou preencha os dados na lateral.")
    else:
        v, p, j = st.session_state.valor_financiado, st.session_state.prazo_meses, st.session_state.juros_anuais
        am = v / p
        sac, ban = [v], [v]
        curr_s, curr_b = v, v
        for i in range(1, p + 1):
            curr_s -= am; sac.append(max(0, curr_s))
            if i % 12 == 0: curr_b += (curr_b * 0.015) 
            else: curr_b -= (am * 0.98)
            ban.append(max(0, curr_b))
        m_ref = min(52, p)
        d_p = ban[m_ref] - sac[m_ref]
        col_a, col_b = st.columns(2)
        col_a.metric("Saldo Banco (Mês 52)", f"R$ {ban[m_ref]:,.2f}")
        col_b.metric("Prejuízo Detectado", f"R$ {d_p:,.2f}", delta_color="inverse")
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=sac, name='SAC Justo', line=dict(color='green', dash='dash')))
        fig.add_trace(go.Scatter(y=ban, name='Banco Viciado', line=dict(color='red')))
        st.plotly_chart(fig, use_container_width=True)

with t2:
    if st.session_state.dados_carregados:
        st.subheader("Laudo Jurídico")
        if st.button("Gerar Laudo"):
            model = genai.GenerativeModel(buscar_melhor_modelo())
            prompt = f"Gere um laudo para {st.session_state.nome_cliente} contra {st.session_state.nome_banco}. Valor {v}."
            st.markdown(model.generate_content(prompt).text)
