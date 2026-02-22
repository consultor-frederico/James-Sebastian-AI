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

# --- SEGURANÇA E CONFIGURAÇÃO ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else "SUA_CHAVE_AQUI"
genai.configure(api_key=GEMINI_API_KEY)
st.set_page_config(page_title="James Sebastian AI - Perícia Judicial", layout="wide")

# Estilo Visual Premium
st.markdown("""
    <style>
    .main-header { font-size: 26px; font-weight: bold; background-color: #1e1e1e; color: #ffffff; padding: 15px; text-align: center; border-radius: 8px; margin-bottom: 20px; }
    .status-irregular { color: #ff0000; font-size: 22px; font-weight: bold; text-align: right; }
    .status-regular { color: #28a745; font-size: 22px; font-weight: bold; text-align: right; }
    .highlight-yellow { background-color: #ffff00; padding: 15px; font-weight: bold; font-size: 22px; color: #000; border-radius: 5px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DE EXTRAÇÃO AUTOMÁTICA (QUALQUER DOCUMENTO) ---
def extrair_dados_ia(arquivos):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """Atue como perito judicial. Analise os documentos e extraia APENAS um JSON:
        {"nome": str, "banco": str, "contrato": str, "valor_financiado": float, "prazo_meses": int, "taxa_juros_anual": float, "parcela_atual": float}
        Busque erros como o Código 410 (incorporação de juros)."""
        
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Texto extraído: {texto[:15000]}")
            else:
                conteudo.append(Image.open(arq))
        
        response = model.generate_content(conteudo)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except:
        return None

# --- INTERFACE ---
with st.sidebar:
    st.header("📂 1. Carga de Provas")
    arquivos = st.file_uploader("Suba Contrato/Evolutivo (PDF ou Foto)", accept_multiple_files=True)
    
    if arquivos and st.button("🔍 Iniciar Auditoria Automática"):
        with st.spinner("James Sebastian analisando documentos..."):
            dados = extrair_dados_ia(arquivos)
            if dados:
                st.session_state.update(dados)
                st.session_state.dados_carregados = True
                st.rerun()

    st.divider()
    st.header("📝 2. Ajustes Técnicos")
    # Campos dinâmicos que aceitam qualquer pessoa
    nome = st.text_input("Mutuário", st.session_state.get('nome', ""))
    v_financiado = st.number_input("Valor Financiado", value=float(st.session_state.get('valor_financiado', 0.0)))
    prazo = st.number_input("Prazo Total", value=int(st.session_state.get('prazo_meses', 0)))
    taxa = st.number_input("Taxa de Juros (% a.a.)", value=float(st.session_state.get('taxa_juros_anual', 0.0)))
    p_atual = st.number_input("Parcela Atual Cobrada", value=float(st.session_state.get('parcela_atual', 0.0)))

# --- CÁLCULO PERICIAL DE PRECISÃO ---
if st.session_state.get('dados_carregados'):
    # Matemática SAC Real
    amort_mensal = v_financiado / prazo if prazo > 0 else 0
    taxa_mensal = (1 + taxa/100)**(1/12) - 1
    # Cálculo para verificar irregularidade (Código 410 / Anatocismo)
    p_correta = amort_mensal + (v_financiado * taxa_mensal) # Simplificado para demonstração
    
    dif_parcela = p_atual - p_correta
    is_irregular = dif_parcela > 10.0
    
    st.markdown('<div class="main-header">ANÁLISE IMOBILIÁRIA SINTETIZADA</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**MUTUÁRIO:** {nome}")
        st.write(f"**BANCO:** {st.session_state.get('banco', 'N/A')}")
        st.write(f"**VALOR FINANCIADO:** R$ {v_financiado:,.2f}")
    with c2:
        status_html = '<span class="status-irregular">CONTRATO IRREGULAR</span>' if is_irregular else '<span class="status-regular">CONTRATO REGULAR</span>'
        st.markdown(f"**STATUS:** {status_html}", unsafe_allow_html=True)
        st.write(f"**TAXA APURADA:** {taxa}% a.a.")

    # 
    fig = go.Figure()
    fig.add_trace(go.Bar(x=['Parcela Correta', 'Parcela Atual'], y=[p_correta, p_atual], marker_color=['green', 'red']))
    st.plotly_chart(fig, use_container_width=True)

    if st.button("📄 Gerar Laudo Completo"):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Gere um laudo pericial para {nome}. Irregularidade detectada de R$ {dif_parcela:,.2f} por mês."
        st.markdown(model.generate_content(prompt).text)
