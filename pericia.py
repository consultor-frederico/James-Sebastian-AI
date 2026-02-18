import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import google.generativeai as genai
from datetime import date
import json
from scipy.optimize import newton

# --- SEGURANÇA ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = "AIzaSyD068i8Vp9R24wwCjrRITsgTjAXo-I5Q-g"

genai.configure(api_key=GEMINI_API_KEY)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="James Sebastian AI - Perícia Judicial", layout="wide")

# Estilo Visual Premium
st.markdown("""
    <style>
    .main-header { font-size: 26px; font-weight: bold; background-color: #1e1e1e; color: #ffffff; padding: 15px; text-align: center; border-radius: 8px; margin-bottom: 20px; }
    .sub-header { font-size: 18px; font-weight: bold; background-color: #444; color: white; padding: 10px; text-align: center; margin-top: 20px; border-radius: 5px; }
    .status-irregular { color: #ff0000; font-size: 22px; font-weight: bold; text-align: right; }
    .status-regular { color: #28a745; font-size: 22px; font-weight: bold; text-align: right; }
    .highlight-yellow { background-color: #ffff00; padding: 15px; font-weight: bold; font-size: 22px; color: #000; border-radius: 5px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DE CÁLCULO DE TAXA IMPLÍCITA (Engenharia Reversa) ---
def calcular_taxa_implicita(valor_f, prazo, parcela_alvo):
    try:
        # No SAC: Parcela = (V/N) + V * i. Logo: i = (Parcela - (V/N)) / V
        amort = valor_f / prazo
        taxa_estimada = (parcela_alvo - amort) / valor_f
        return max(0.0, taxa_estimada * 12 * 100) # Retorna taxa anual %
    except:
        return 0.0

@st.cache_data(ttl=3600)
def obter_indices_atualizados():
    hoje = date.today().strftime("%d/%m/%Y")
    res = {"data": hoje, "Selic": 0.0, "TR": 0.0, "IPCA": 0.0, "Dolar": 0.0, "Euro": 0.0}
    try:
        indices_bacen = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for nome, cod in indices_bacen.items():
            r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/1?formato=json", timeout=5)
            if r.status_code == 200: res[nome] = float(r.json()[0]['valor'])
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=5).json()
        res["Dolar"] = float(c["USDBRL"]["bid"])
        res["Euro"] = float(c["EURBRL"]["bid"])
    except: pass
    return res

# --- INTERFACE DE ENTRADA ---
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
    prazo_total = st.number_input("Prazo Contratual (Meses)", min_value=1, step=1)
    parcelas_pagas = st.number_input("Parcelas Pagas até hoje", min_value=0, step=1)
    
    taxa_juros_anual = st.number_input("Taxa de Juros Nominal (% a.a.) - Deixe 0 para calcular", min_value=0.0, step=0.01)
    p_atual = st.number_input("Valor da Parcela Atual (R$)", min_value=0.0, step=10.0)
    v_seguro = st.number_input("Seguro MIP/DFI (R$)", min_value=0.0)
    v_taxa_adm = st.number_input("Taxa Adm (R$)", min_value=0.0)

    executar = st.button("📊 Realizar Auditoria Técnica")

ind = obter_indices_atualizados()

if executar and v_financiado > 0:
    # Lógica de Preenchimento Automático de Detalhes Faltantes
    if taxa_juros_anual == 0:
        taxa_juros_anual = calcular_taxa_implicita(v_financiado, prazo_total, p_atual - v_seguro - v_taxa_adm)
        st.warning(f"⚠️ Taxa de juros não informada. Engenharia reversa apurou: {taxa_juros_anual:.2f}% a.a.")

    # Matemática SAC Pura
    amortizacao_mensal = v_financiado / prazo_total
    taxa_mensal = (1 + taxa_juros_anual/100)**(1/12) - 1
    
    # Saldo devedor teórico
    saldo_anterior = v_financiado - (amortizacao_mensal * (parcelas_pagas - 1))
    juros_legais = max(0, saldo_anterior * taxa_mensal)
    
    p_correta = amortizacao_mensal + juros_legais + v_seguro + v_taxa_adm
    dif_parcela = p_atual - p_correta
    is_irregular = dif_parcela > 5.0
    dif_total_recuperavel = (dif_parcela * parcelas_pagas) * 1.2 # Incluindo estimativa de correção

    # --- RESULTADOS ---
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

    st.markdown(f'<div class="highlight-yellow">SALDO DEVEDOR ATUALIZADO: R$ {max(0, v_financiado - (amortizacao_mensal * parcelas_pagas)):,.2f}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sub-header">ANÁLISE VISUAL DA CONFORMIDADE</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=['VALOR LEGAL (SAC)', 'VALOR COBRADO'], y=[p_correta, p_atual], 
                         marker_color=['#28a745', '#ff0000'], text=[f"R$ {p_correta:,.2f}", f"R$ {p_atual:,.2f}"], textposition='auto'))
    st.plotly_chart(fig, use_container_width=True)

    ca, cb = st.columns(2)
    ca.metric("Amortização Mensal (SAC)", f"R$ {amortizacao_mensal:,.2f}")
    cb.metric("POTENCIAL DE RECUPERAÇÃO", f"R$ {dif_total_recuperavel:,.2f}", delta=f"R$ {dif_parcela:,.2f} /mês", delta_color="inverse")

    # --- LAUDO COMPLETO ---
    if st.button("📄 GERAR LAUDO PERICIAL COMPLETO (PDF READY)"):
        with st.spinner("James Sebastian está redigindo a peça técnica final..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            Redija um LAUDO PERICIAL JUDICIAL COMPLETO em Markdown, com rigor técnico de 30 anos de experiência.
            DADOS: Mutuário {mutuario}, Banco {banco}, Contrato {num_contrato}, Valor {v_financiado}, Prazo {prazo_total}.
            RESULTADO: Diferença mensal de R$ {dif_parcela:,.2f} e Recuperável de R$ {dif_total_recuperavel:,.2f}.
            
            ESTRUTURA OBRIGATÓRIA:
            1. CABEÇALHO: Nome do Perito, Objeto e Identificação das Partes.
            2. METODOLOGIA: Explicação detalhada do Sistema SAC (Lei 4.380/64) e por que a amortização deve ser constante.
            3. EXAME TÉCNICO: Demonstração matemática da irregularidade (Engenharia Reversa Financeira).
            4. ANATOCISMO: Análise da Súmula 121 do STF e do 'Código 410' (incorporação de juros ao saldo).
            5. QUESITOS DO PERITO: Responda se houve cobrança acima do pactuado e se há amortização negativa.
            6. JURISPRUDÊNCIA: Citações do STF e STJ sobre SFH e anatocismo.
            7. CONCLUSÃO: Valor exato do indébito e recomendação de recálculo imediato.
            
            Use tabelas em Markdown para comparar os valores. Seja formal e incisivo.
            """
            st.markdown("---")
            st.markdown(model.generate_content(prompt).text)
else:
    st.info("💡 Insira os dados disponíveis. O James Sebastian calculará os detalhes faltantes automaticamente.")
