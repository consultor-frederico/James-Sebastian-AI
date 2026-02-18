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
import os

# --- CONFIGURAÇÃO DE SEGURANÇA ---
# Puxa a chave do painel Secrets do Streamlit Cloud
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = "" # Adicione sua chave aqui se testar localmente

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="James Sebastian AI - Auditoria", layout="wide", page_icon="⚖️")

# --- INICIALIZAÇÃO DE ESTADO ---
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = False

# Campos iniciam vazios para preenchimento manual ou via IA
for campo in ['nome_cliente', 'nome_banco', 'numero_contrato']:
    if campo not in st.session_state: st.session_state[campo] = ""
for campo in ['valor_financiado', 'prazo_meses', 'juros_anuais']:
    if campo not in st.session_state: st.session_state[campo] = 0.0

# --- FUNÇÃO PARA BUSCA DINÂMICA DO MODELO (Evita Erro 404) ---
def buscar_melhor_modelo():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        prioridades = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-flash-latest']
        for modelo in prioridades:
            if modelo in modelos: return modelo
        return 'gemini-1.5-flash'
    except:
        return 'gemini-1.5-flash'

# --- FUNÇÕES DE MERCADO ---
@st.cache_data(ttl=3600)
def obter_indices_completos():
    hoje = date.today().strftime("%d/%m/%Y")
    res = {"data": hoje, "Selic": 11.25, "TR": 0.082, "IPCA": 4.51, "Dolar": 5.0, "Euro": 5.4}
    try:
        series = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for nome, cod in series.items():
            r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/1?formato=json", timeout=3)
            if r.status_code == 200: res[nome] = float(r.json()[0]['valor'])
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=3).json()
        res["Dolar"] = float(c["USDBRL"]["bid"]); res["Euro"] = float(c["EURBRL"]["bid"])
    except: pass 
    return res

# --- FUNÇÃO EXTRAÇÃO IA ---
def extrair_dados_ia(arquivos):
    try:
        modelo_nome = buscar_melhor_modelo()
        model = genai.GenerativeModel(modelo_nome)
        prompt = """Analise os documentos e extraia EXATAMENTE este JSON:
        {"banco": str, "contrato": str, "nomes": str, "valor_financiado": float, "prazo_meses": int, "taxa_juros_anual": float}
        Não responda nada além do JSON puro."""
        
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Texto: {texto[:15000]}")
            else:
                conteudo.append(Image.open(arq))
        
        response = model.generate_content(conteudo)
        txt = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(txt)
    except Exception as e:
        st.error(f"Erro na extração: {e}")
        return None

# --- INTERFACE ---
st.title("⚖️ James Sebastian AI - Auditoria Contratual")
indices = obter_indices_completos()
st.write(f"📅 **Indicadores de Hoje ({indices['data']}):**")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Selic", f"{indices['Selic']}%"); c2.metric("TR", f"{indices['TR']}%"); c3.metric("IPCA", f"{indices['IPCA']}%")
c4.metric("Dólar", f"R$ {indices['Dolar']:.2f}"); c5.metric("Euro", f"R$ {indices['Euro']:.2f}")
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
                st.success("Dados carregados!")
                st.rerun()

    st.divider()
    st.header("📝 2. Dados Manuais")
    st.session_state.nome_cliente = st.text_input("Mutuário", st.session_state.nome_cliente)
    st.session_state.valor_financiado = st.number_input("Valor Original", value=float(st.session_state.valor_financiado))
    st.session_state.prazo_meses = st.number_input("Prazo", value=int(st.session_state.prazo_meses))
    st.session_state.juros_anuais = st.number_input("Juros (%)", value=float(st.session_state.juros_anuais))
    if st.button("🔄 Atualizar Cálculos"): st.session_state.dados_carregados = True

# --- EXIBIÇÃO ---
tab1, tab2 = st.tabs(["📊 Gráficos", "📝 Laudo"])
with tab1:
    if not st.session_state.dados_carregados or st.session_state.valor_financiado == 0:
        st.info("💡 Suba os arquivos para ver a perícia.")
    else:
        # Lógica de Amortização Simplificada para o gráfico
        v, p, j = st.session_state.valor_financiado, st.session_state.prazo_meses, st.session_state.juros_anuais
        am = v / p if p > 0 else 0
        sac, ban = [v], [v]
        for i in range(1, p + 1):
            sac.append(max(0, sac[-1] - am))
            ban.append(max(0, ban[-1] - (am * 0.95) if i % 12 != 0 else ban[-1] + (v * 0.01)))
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=sac, name='SAC Justo', line=dict(color='green', dash='dash')))
        fig.add_trace(go.Scatter(y=ban, name='Banco Viciado', line=dict(color='red')))
        st.plotly_chart(fig, use_container_width=True)
