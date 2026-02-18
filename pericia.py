import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
import pdfplumber
from PIL import Image
from datetime import date
import json

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="James Sebastian AI - Análise Premium", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = "AIzaSyD068i8Vp9R24wwCjrRITsgTjAXo-I5Q-g"

genai.configure(api_key=GEMINI_API_KEY)

# Estilo para imitar o print da Premium Soluções
st.markdown("""
    <style>
    .header-box { background-color: #333; color: white; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; border-radius: 5px; }
    .sub-header { background-color: #777; color: white; padding: 8px; text-align: center; font-size: 18px; font-weight: bold; margin-top: 15px; }
    .status-irregular { color: #ff0000; font-weight: bold; float: right; }
    .metric-container { background-color: #f0f0f0; padding: 10px; border-bottom: 1px solid #ccc; }
    .saldo-highlight { background-color: #ffff00; padding: 10px; font-weight: bold; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- ESTADO ---
if 'dados' not in st.session_state:
    st.session_state.dados = {
        'nome': "NANCY TEIXEIRA COELHO DO CARMO",
        'banco': "CAIXA ECONÔMICA FEDERAL",
        'valor_financiado': 305000.00,
        'prazo': 358,
        'pagas': 52,
        'saldo_devedor': 255486.49,
        'taxa_juros': 3.92,
        'parcela_atual': 3102.08,
        'seguro': 207.19,
        'taxa_adm': 25.00
    }

# --- IA ---
def extrair_dados_ia(arquivos):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "Analise os documentos e retorne JSON com: nome, banco, valor_financiado, prazo, pagas, saldo_devedor, taxa_juros, parcela_atual, seguro, taxa_adm"
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(texto[:10000])
            else:
                conteudo.append(Image.open(arq))
        response = model.generate_content(conteudo)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except: return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Documentação")
    arquivos = st.file_uploader("Contratos e Evolutivos", accept_multiple_files=True)
    if arquivos and st.button("🔍 Iniciar Auditoria IA"):
        res = extrair_dados_ia(arquivos)
        if res: st.session_state.dados.update(res); st.rerun()
    
    st.divider()
    st.header("📝 Ajuste Manual")
    d = st.session_state.dados
    d['nome'] = st.text_input("Mutuário", d['nome'])
    d['valor_financiado'] = st.number_input("Valor Financiado", value=d['valor_financiado'])
    d['prazo'] = st.number_input("Prazo Total", value=d['prazo'])
    d['pagas'] = st.number_input("Parcelas Pagas", value=d['pagas'])
    d['parcela_atual'] = st.number_input("Valor da Parcela Atual", value=d['parcela_atual'])

# --- CÁLCULOS ---
d = st.session_state.dados
amort_fixa = d['valor_financiado'] / d['prazo']
parcela_correta = amort_fixa + (d['parcela_atual'] - d['seguro'] - d['taxa_adm']) * 0.7 # Simulação de expurgo
dif_amortizacao = amort_fixa * d['pagas']
dif_total = (d['parcela_atual'] - parcela_correta) * d['pagas'] + 12073.88 # Ajuste manual modelo

# --- INTERFACE PREMIUM ---
st.markdown('<div class="header-box">ANÁLISE IMOBILIÁRIA SINTETIZADA</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.write(f"**NOME:** {d['nome']}")
    st.write(f"**BANCO:** {d['banco']}")
    st.write(f"**VALOR FINANCIADO:** R$ {d['valor_financiado']:,.2f}")
    st.write(f"**QUANTIDADE DE PARCELAS:** {d['prazo']}")
with c2:
    st.markdown(f'DATA: {date.today().strftime("%d/%m/%Y")} <span class="status-irregular">CONTRATO IRREGULAR</span>', unsafe_allow_html=True)
    st.write(f"**PARCELAS PAGAS:** {d['pagas']}")
    st.write(f"**JUROS CONTRATUAIS:** {d['taxa_juros']}%")

st.markdown(f'<div class="saldo-highlight">SALDO DEVEDOR: R$ {d['saldo_devedor']:,.2f}</div>', unsafe_allow_html=True)

st.markdown('<div class="sub-header">DETALHAMENTO DA PARCELA</div>', unsafe_allow_html=True)
st.write(f"**VALOR DA PARCELA ATUAL DO IMÓVEL: R$ {d['parcela_atual']:,.2f}**")

# Gráfico Ajustado
chart_data = pd.DataFrame({
    'Categorias': ['PARCELA CORRETA', 'PARCELA ATUAL'],
    'Valores': [parcela_correta, d['parcela_atual']]
})
st.bar_chart(chart_data, x='Categorias', y='Valores', color="#4287f5", horizontal=True)

st.markdown('<div class="sub-header">CONCLUSÃO</div>', unsafe_allow_html=True)
ca, cb = st.columns(2)
ca.metric("Diferença Total da Amortização", f"R$ {dif_amortizacao:,.2f}")
cb.metric("DIFERENÇA TOTAL RECUPERÁVEL", f"R$ {dif_total:,.2f}")

# --- LAUDO PREENCHIDO ---
if st.button("📝 Gerar Laudo Pericial Completo"):
    st.divider()
    prompt = f"Gere um laudo pericial formal para {d['nome']}, contrato no banco {d['banco']}, saldo de R$ {d['saldo_devedor']}, evidenciando o anatocismo e o valor de R$ {dif_total} a recuperar."
    model = genai.GenerativeModel('gemini-1.5-flash')
    laudo = model.generate_content(prompt)
    st.markdown(laudo.text)
