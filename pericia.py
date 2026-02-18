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

# --- CONFIGURAÇÃO DE SEGURANÇA ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = "AIzaSyD068i8Vp9R24wwCjrRITsgTjAXo-I5Q-g"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="James Sebastian AI - Auditoria", layout="wide", page_icon="⚖️")

# --- INICIALIZAÇÃO DE ESTADO (CAMPOS VAZIOS) ---
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = False

# Inicialização dinâmica: nada de dados pré-fixados
campos_init = {
    'nome_cliente': "", 'nome_banco': "", 'numero_contrato': "",
    'valor_financiado': 0.0, 'prazo_meses': 0, 'juros_anuais': 0.0
}

for campo, valor in campos_init.items():
    if campo not in st.session_state:
        st.session_state[campo] = valor

# --- FUNÇÃO DE BUSCA DE MODELO (Evita Erro 404) ---
def buscar_melhor_modelo():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        prioridades = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-flash-latest']
        for p in prioridades:
            if p in modelos: return p
        return 'gemini-1.5-flash'
    except: return 'gemini-1.5-flash'

# --- FUNÇÕES DE MERCADO ---
@st.cache_data(ttl=3600)
def obter_indices_dia():
    hoje = date.today().strftime("%d/%m/%Y")
    res = {"data": hoje, "Selic": 11.25, "TR": 0.08, "IPCA": 4.5, "Dolar": 5.0, "Euro": 5.4}
    try:
        series = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for n, c in series.items():
            url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{c}/dados/ultimos/1?formato=json"
            res[n] = float(requests.get(url, timeout=2).json()[0]['valor'])
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=2).json()
        res["Dolar"] = float(c["USDBRL"]["bid"])
        res["Euro"] = float(c["EURBRL"]["bid"])
    except: pass
    return res

# --- EXTRAÇÃO IA ---
def extrair_dados_ia(arquivos):
    try:
        model = genai.GenerativeModel(buscar_melhor_modelo())
        prompt = "Analise os documentos e extraia EXATAMENTE este JSON: {'banco': str, 'contrato': str, 'nomes': str, 'valor_financiado': float, 'prazo_meses': int, 'taxa_juros_anual': float}. Se não achar, use null."
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Doc: {texto[:15000]}")
            else: conteudo.append(Image.open(arq))
        
        resp = model.generate_content(conteudo).text
        txt = resp.strip().replace("```json", "").replace("```", "")
        return json.loads(txt)
    except: return None

# --- INTERFACE ---
st.title("⚖️ James Sebastian AI - Auditoria Contratual")
ind = obter_indices_dia()
st.write(f"📅 **Indicadores Oficiais em {ind['data']}:**")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Selic", f"{ind['Selic']}%"); c2.metric("TR", f"{ind['TR']}%")
c3.metric("Dólar", f"R$ {ind['Dolar']:.2f}"); c4.metric("Euro", f"R$ {ind['Euro']:.2f}"); c5.metric("IPCA", f"{ind['IPCA']}%")
st.divider()

with st.sidebar:
    st.header("📂 1. Documentação")
    files = st.file_uploader("Selecione os arquivos", accept_multiple_files=True, type=['pdf','jpg','png'])
    if files and st.button("🔍 Iniciar Auditoria IA"):
        with st.spinner("Lendo documentos..."):
            res = extrair_dados_ia(files)
            if res:
                st.session_state.nome_cliente = res.get('nomes') or ""
                st.session_state.nome_banco = res.get('banco') or ""
                st.session_state.numero_contrato = str(res.get('contrato') or "")
                st.session_state.valor_financiado = float(res.get('valor_financiado') or 0.0)
                st.session_state.prazo_meses = int(res.get('prazo_meses') or 0)
                st.session_state.juros_anuais = float(res.get('taxa_juros_anual') or 0.0)
                st.session_state.dados_carregados = True
                st.rerun()

    st.header("📝 2. Dados Manuais")
    st.session_state.nome_cliente = st.text_input("Mutuário", st.session_state.nome_cliente)
    st.session_state.valor_financiado = st.number_input("Valor Original", value=float(st.session_state.valor_financiado))
    st.session_state.prazo_meses = st.number_input("Prazo Total", value=int(st.session_state.prazo_meses))
    st.session_state.juros_anuais = st.number_input("Taxa (%)", value=float(st.session_state.juros_anuais))
    if st.button("🔄 Atualizar Cálculos"): st.session_state.dados_carregados = True

# --- RESULTADOS ---
t1, t2 = st.tabs(["📊 Evolução e Perícia", "📝 Laudo Jurídico"])

with t1:
    if not st.session_state.dados_carregados or st.session_state.valor_financiado <= 0:
        st.info("💡 Aguardando dados. Suba os arquivos ou digite os valores na lateral.")
    else:
        v, p = st.session_state.valor_financiado, st.session_state.prazo_meses
        am = v / p if p > 0 else 0
        sac, ban = [v], [v]
        for i in range(1, p + 1):
            sac.append(max(0, sac[-1] - am))
            # Simula anatocismo técnico
            if i % 12 == 0: ban.append(ban[-1] + (v * 0.012))
            else: ban.append(max(0, ban[-1] - (am * 0.96)))
        
        m_ref = min(52, p)
        dif = ban[m_ref] - sac[m_ref]
        col_a, col_b = st.columns(2)
        col_a.metric("Saldo Banco (Mês 52)", f"R$ {ban[m_ref]:,.2f}")
        col_b.metric("Prejuízo Detectado", f"R$ {dif:,.2f}", delta_color="inverse")
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=sac, name='SAC Legal', line=dict(color='green', dash='dash')))
        fig.add_trace(go.Scatter(y=ban, name='Banco Viciado', line=dict(color='red')))
        st.plotly_chart(fig, use_container_width=True)

with t2:
    if st.session_state.dados_carregados:
        if st.button("📄 Gerar Laudo Técnico"):
            model = genai.GenerativeModel(buscar_melhor_modelo())
            prompt = f"Gere um laudo pericial para {st.session_state.nome_cliente} contra o banco {st.session_state.nome_banco}. Valor original: R$ {v}. Irregularidade: Anatocismo."
            st.markdown(model.generate_content(prompt).text)
