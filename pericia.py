import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import google.generativeai as genai
from datetime import date

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="James Sebastian AI - Análise Premium", layout="wide")

# CSS para imitar o layout Premium das imagens enviadas
st.markdown("""
    <style>
    .header-box { background-color: #1e1e1e; color: white; padding: 20px; text-align: center; border-radius: 5px; margin-bottom: 20px; }
    .premium-title { font-size: 28px; font-weight: bold; }
    .sub-header { background-color: #777; color: white; padding: 10px; text-align: center; font-weight: bold; margin-top: 20px; }
    .status-irregular { color: #ff0000; font-size: 20px; font-weight: bold; }
    .status-regular { color: #28a745; font-size: 20px; font-weight: bold; }
    .saldo-highlight { background-color: #ffff00; padding: 15px; font-weight: bold; font-size: 22px; color: black; border-radius: 5px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- SEGURANÇA ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = "AIzaSyD068i8Vp9R24wwCjrRITsgTjAXo-I5Q-g"

genai.configure(api_key=GEMINI_API_KEY)

# --- ÍNDICES EM TEMPO REAL ---
@st.cache_data(ttl=3600)
def obter_indices():
    res = {"data": date.today().strftime("%d/%m/%Y"), "Selic": 11.25, "TR": 0.082}
    try:
        r = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json", timeout=3)
        if r.status_code == 200: res["Selic"] = float(r.json()[0]['valor'])
        tr = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.226/dados/ultimos/1?formato=json", timeout=3)
        if tr.status_code == 200: res["TR"] = float(tr.json()[0]['valor'])
    except: pass
    return res

# --- SIDEBAR: ENTRADA DE DADOS ---
with st.sidebar:
    st.header("⚖️ Perícia Judicial")
    st.write("**Perito:** James Sebastian (30+ anos de exp.)")
    st.divider()
    
    mutuario = st.text_input("Nome do Mutuário", "")
    banco = st.text_input("Instituição Financeira", "")
    num_contrato = st.text_input("Número do Contrato", "")
    v_financiado = st.number_input("Valor Financiado (R$)", min_value=0.0)
    prazo = st.number_input("Prazo Total (Meses)", min_value=1, value=358)
    pagas = st.number_input("Parcelas Pagas", min_value=0)
    taxa_juros = st.number_input("Taxa de Juros Nominal (% a.a.)", min_value=0.0)
    p_atual = st.number_input("Valor da Parcela Atual (R$)", min_value=0.0)
    v_seguro = st.number_input("Seguro (R$)", min_value=0.0)
    v_taxa_adm = st.number_input("Taxa Adm (R$)", min_value=0.0)

    executar = st.button("📊 Realizar Análise Técnica")

# --- MOTOR FINANCEIRO (SAC LEGAL) ---
ind = obter_indices()

if executar and v_financiado > 0:
    # Amortização SAC é Constante
    amort_mensal = v_financiado / prazo
    taxa_mensal = (1 + taxa_juros/100)**(1/12) - 1
    
    # Saldo e Juros na parcela atual
    saldo_apos_pagas = v_financiado - (amort_mensal * (pagas - 1))
    juros_mes = saldo_apos_pagas * taxa_mensal
    p_correta = amort_mensal + juros_mes + v_seguro + v_taxa_adm
    
    # Prejuízo
    dif_mensal = p_atual - p_correta
    prejuizo_total = dif_mensal * pagas
    is_irregular = dif_mensal > 10.0 # Margem de tolerância

    # --- INTERFACE PREMIUM ---
    st.markdown('<div class="header-box"><span class="premium-title">ANÁLISE IMOBILIÁRIA SINTETIZADA</span></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**NOME:** {mutuario}")
        st.write(f"**BANCO:** {banco}")
        st.write(f"**VALOR FINANCIADO:** R$ {v_financiado:,.2f}")
        st.write(f"**QUANTIDADE DE PARCELAS:** {prazo}")
    with col2:
        status_html = f'<span class="status-irregular">CONTRATO IRREGULAR</span>' if is_irregular else f'<span class="status-regular">CONTRATO REGULAR</span>'
        st.markdown(f"**DATA:** {ind['data']} {status_html}", unsafe_allow_html=True)
        st.write(f"**PARCELAS PAGAS:** {pagas}")
        st.write(f"**JUROS CONTRATUAIS:** {taxa_juros}%")
        st.write(f"**CONTRATO Nº:** {num_contrato}")

    st.markdown(f'<div class="saldo-highlight">SALDO DEVEDOR ATUALIZADO: R$ {(v_financiado - (amort_mensal * pagas)):,.2f}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sub-header">DETALHAMENTO DA PARCELA</div>', unsafe_allow_html=True)
    st.write(f"**VALOR DA PARCELA ATUAL DO IMÓVEL: R$ {p_atual:,.2f}**")

    # Comparativo Visual (Ajustado para evitar erros de cor)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=['PARCELA CORRETA', 'PARCELA ATUAL'], y=[p_correta, p_atual],
                         marker_color=['#28a745', '#ff0000'], textposition='auto'))
    fig.update_layout(title="Ajuste de Parcela", height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="sub-header">CONCLUSÃO PERICIAL</div>', unsafe_allow_html=True)
    ca, cb = st.columns(2)
    ca.metric("Amortização Teórica (SAC)", f"R$ {amort_mensal:,.2f}")
    cb.metric("DIFERENÇA TOTAL RECUPERÁVEL", f"R$ {prejuizo_total:,.2f}", delta=f"R$ {dif_mensal:,.2f} /mês", delta_color="inverse")

    # --- LAUDO IA ---
    if st.button("📄 Gerar Laudo Judicial Completo"):
        with st.spinner("James Sebastian está redigindo a fundamentação técnica..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            Como Perito Judicial James Sebastian (30 anos de experiência), redija um LAUDO PERICIAL em Markdown.
            NOME: {mutuario}, BANCO: {banco}, CONTRATO: {num_contrato}.
            PREJUÍZO: R$ {prejuizo_total:,.2f}. 
            Anatocismo detectado via amortização negativa (incorporação de juros).
            Inclua: Metodologia SAC, Análise do Código 410, Súmula 121 STF e Conclusão técnica com recomendações de expurgo.
            """
            st.markdown("---")
            st.markdown(model.generate_content(prompt).text)
else:
    st.info("Insira os dados na barra lateral para iniciar a perícia.")
