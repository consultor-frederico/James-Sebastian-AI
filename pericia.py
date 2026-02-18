import streamlit as st

import pandas as pd

import numpy as np

import plotly.graph_objects as go

import requests

import google.generativeai as genai

from datetime import date

import json



# --- SEGURANÇA ---

if "GEMINI_API_KEY" in st.secrets:

    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

else:

    GEMINI_API_KEY = "AIzaSyD068i8Vp9R24wwCjrRITsgTjAXo-I5Q-g"



genai.configure(api_key=GEMINI_API_KEY)



# --- CONFIGURAÇÃO DA PÁGINA ---

st.set_page_config(page_title="James Sebastian AI - Perícia Judicial", layout="wide")



# Estilo Visual Premium e Sinalização de Status

st.markdown("""

    <style>

    .main-header { font-size: 26px; font-weight: bold; background-color: #1e1e1e; color: #ffffff; padding: 15px; text-align: center; border-radius: 8px; margin-bottom: 20px; }

    .sub-header { font-size: 18px; font-weight: bold; background-color: #444; color: white; padding: 10px; text-align: center; margin-top: 20px; border-radius: 5px; }

    .status-irregular { color: #ff0000; font-size: 22px; font-weight: bold; text-align: right; }

    .status-regular { color: #28a745; font-size: 22px; font-weight: bold; text-align: right; }

    .highlight-yellow { background-color: #ffff00; padding: 15px; font-weight: bold; font-size: 22px; color: #000; border-radius: 5px; text-align: center; }

    </style>

    """, unsafe_allow_html=True)



# --- BUSCA DE ÍNDICES EM TEMPO REAL ---

@st.cache_data(ttl=3600)

def obter_indices_atualizados():

    hoje = date.today().strftime("%d/%m/%Y")

    res = {"data": hoje, "Selic": 0.0, "TR": 0.0, "IPCA": 0.0, "Dolar": 0.0, "Euro": 0.0}

    try:

        # BACEN

        indices_bacen = {"Selic": 432, "TR": 226, "IPCA": 13522}

        for nome, cod in indices_bacen.items():

            r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/1?formato=json", timeout=5)

            if r.status_code == 200: res[nome] = float(r.json()[0]['valor'])

        # Câmbio

        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=5).json()

        res["Dolar"] = float(c["USDBRL"]["bid"])

        res["Euro"] = float(c["EURBRL"]["bid"])

    except: pass

    return res



# --- INTERFACE DE ENTRADA (DADOS EM BRANCO) ---

with st.sidebar:

    st.header("⚖️ Perícia Judicial")

    st.write("**Perito Responsável:** James Sebastian")

    st.write("**Registro Profissional:** Ativo (30+ anos)")

    st.divider()

    

    st.header("📝 Dados do Mutuário")

    mutuario = st.text_input("Nome do Mutuário", "")

    banco = st.text_input("Instituição Financeira", "")

    num_contrato = st.text_input("Número do Contrato", "")

    v_financiado = st.number_input("Valor Financiado (R$)", min_value=0.0, step=1000.0)

    prazo_total = st.number_input("Prazo Contratual (Meses)", min_value=0, step=1)

    parcelas_pagas = st.number_input("Quantidade de Parcelas Pagas", min_value=0, step=1)

    taxa_juros_anual = st.number_input("Taxa de Juros Nominal (% a.a.)", min_value=0.0, step=0.01)

    p_atual = st.number_input("Valor da Parcela Atual (R$)", min_value=0.0, step=10.0)

    v_seguro = st.number_input("Valor do Seguro (MIP/DFI) (R$)", min_value=0.0)

    v_taxa_adm = st.number_input("Taxa de Administração (R$)", min_value=0.0)



    executar = st.button("📊 Realizar Perícia Judicial")



# --- PROCESSAMENTO E CÁLCULO SAC ---

ind = obter_indices_atualizados()



if executar and v_financiado > 0 and prazo_total > 0:

    # Matemática SAC Pura (SFH)

    amortizacao_mensal = v_financiado / prazo_total # Amortização constante

    taxa_mensal = (1 + taxa_juros_anual/100)**(1/12) - 1

    

    # Saldo devedor teórico na parcela atual

    saldo_anterior = v_financiado - (amortizacao_mensal * (parcelas_pagas - 1))

    juros_legais = saldo_anterior * taxa_mensal

    

    # Parcela que deveria ser paga (SAC)

    p_correta = amortizacao_mensal + juros_legais + v_seguro + v_taxa_adm

    

    # Diferenças

    dif_parcela = p_atual - p_correta

    is_irregular = dif_parcela > 5.0 # Margem de erro mínima

    dif_amortizacao = amortizacao_mensal * parcelas_pagas

    dif_total_recuperavel = (dif_parcela * parcelas_pagas) + (dif_parcela * 0.2) # Juros e Correção estimada

    

    # --- RESULTADOS VISUAIS ---

    st.markdown('<div class="main-header">ANÁLISE IMOBILIÁRIA SINTETIZADA - LAUDO PERICIAL</div>', unsafe_allow_html=True)

    

    c1, c2 = st.columns([2, 1])

    with c1:

        st.write(f"**MUTUÁRIO:** {mutuario}")

        st.write(f"**BANCO:** {banco}")

        st.write(f"**CONTRATO Nº:** {num_contrato}")

        st.write(f"**VALOR FINANCIADO:** R$ {v_financiado:,.2f}")

    with c2:

        status_html = f'<div class="status-irregular">CONTRATO IRREGULAR</div>' if is_irregular else f'<div class="status-regular">CONTRATO REGULAR</div>'

        st.markdown(status_html, unsafe_allow_html=True)

        st.write(f"**DATA ATUALIZAÇÃO:** {ind['data']}")

        st.write(f"**INDICADORES:** Selic {ind['Selic']}% | TR {ind['TR']}%")



    st.markdown(f'<div class="highlight-yellow">SALDO DEVEDOR ATUALIZADO: R$ {(v_financiado - dif_amortizacao):,.2f}</div>', unsafe_allow_html=True)



    st.markdown('<div class="sub-header">DETALHAMENTO DA PARCELA</div>', unsafe_allow_html=True)

    st.write(f"**VALOR DA PARCELA ATUAL DO IMÓVEL: R$ {p_atual:,.2f}**")

    

    # Análise Visual: Pago vs Deveria Pagar

    fig = go.Figure()

    fig.add_trace(go.Bar(x=['PARCELA CORRETA', 'PARCELA ATUAL'], y=[p_correta, p_atual], 

                         marker_color=['#28a745', '#ff0000'], text=[f"R$ {p_correta:,.2f}", f"R$ {p_atual:,.2f}"], textposition='auto'))

    fig.update_layout(title="Comparativo: Custo Efetivo da Prestação", height=400)

    st.plotly_chart(fig, use_container_width=True)



    # Métricas Finais

    st.markdown('<div class="sub-header">CONCLUSÃO PERICIAL</div>', unsafe_allow_html=True)

    ca, cb = st.columns(2)

    ca.metric("Diferença de Amortização", f"R$ {amortizacao_mensal:,.2f}")

    cb.metric("DIFERENÇA TOTAL RECUPERÁVEL", f"R$ {dif_total_recuperavel:,.2f}")



    # --- LAUDO IA ---

    if st.button("📄 Gerar Laudo Pericial Completo"):

        with st.spinner("O Perito James Sebastian está consolidando as provas..."):

            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""

            Como Perito Judicial James Sebastian (30 anos de experiência), redija um LAUDO PERICIAL JURÍDICO em Markdown.

            NOME: {mutuario}, BANCO: {banco}, CONTRATO: {num_contrato}, VALOR: {v_financiado}.

            PREJUÍZO ACUMULADO: R$ {dif_total_recuperavel:,.2f}.

            Fundamente com: Súmula 121 STF, Art. 4º Decreto 22.626/33 e a Lei 4.380/64 (SFH).

            Analise o impacto do anatocismo (incorporação de juros) no saldo devedor.

            Ao final, liste os 'Pontos de Irregularidade' e 'Jurisprudência Aplicada'.

            """

            st.markdown(model.generate_content(prompt).text)

else:

    st.info("💡 James Sebastian aguarda a inserção dos dados para iniciar a análise técnica.")
