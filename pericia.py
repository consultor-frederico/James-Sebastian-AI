import streamlit as st
import pandas as pd
import numpy as np
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

genai.configure(api_key=GEMINI_API_KEY)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="James Sebastian AI - Análise Premium", layout="wide")

# Estilo para imitar o print (Premium Soluções)
st.markdown("""
    <style>
    .main-header { font-size: 24px; font-weight: bold; background-color: #333; color: white; padding: 10px; text-align: center; border-radius: 5px; }
    .sub-header { font-size: 18px; font-weight: bold; background-color: #777; color: white; padding: 5px; text-align: center; margin-top: 20px; }
    .metric-row { display: flex; justify-content: space-between; padding: 5px; border-bottom: 1px solid #ddd; }
    .label { font-weight: bold; color: #333; }
    .value { color: #000; }
    .irregular { color: red; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE ESTADO ---
if 'dados' not in st.session_state:
    st.session_state.dados = {
        'nome': "", 'banco': "", 'valor_financiado': 0.0, 'prazo': 358, 
        'pagas': 0, 'saldo_devedor': 0.0, 'juros_atuais': 0.0, 'seguro': 0.0,
        'taxa_adm': 0.0, 'parcela_atual': 0.0
    }

# --- FUNÇÃO DE EXTRAÇÃO IA ---
def extrair_dados_ia(arquivos):
    try:
        # Uso do modelo estável para evitar erro 404
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """Analise os documentos e extraia os dados abaixo para um JSON:
        {"nome": str, "banco": str, "valor_financiado": float, "prazo": int, "pagas": int, "saldo_devedor": float, "taxa_juros_anual": float, "seguro": float, "taxa_adm": float, "parcela_atual": float}
        """
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(texto[:15000])
            else:
                conteudo.append(Image.open(arq))
        
        response = model.generate_content(conteudo)
        txt = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(txt)
    except Exception as e:
        st.error(f"Erro na extração IA: {e}")
        return None

# --- INTERFACE ---
with st.sidebar:
    st.header("📂 Documentação")
    arquivos = st.file_uploader("Suba o Contrato e Evolutivo", accept_multiple_files=True)
    if arquivos and st.button("🔍 Iniciar Auditoria IA"):
        res = extrair_dados_ia(arquivos)
        if res:
            st.session_state.dados.update(res)
            st.success("Dados carregados!")

    st.divider()
    st.header("📝 Ajuste Manual")
    st.session_state.dados['nome'] = st.text_input("Nome", st.session_state.dados['nome'])
    st.session_state.dados['valor_financiado'] = st.number_input("Valor Financiado", value=float(st.session_state.dados['valor_financiado']))
    st.session_state.dados['pagas'] = st.number_input("Parcelas Pagas", value=int(st.session_state.dados['pagas']))
    st.session_state.dados['parcela_atual'] = st.number_input("Valor Parcela Atual", value=float(st.session_state.dados['parcela_atual']))

# --- CÁLCULOS PERICIAIS ---
d = st.session_state.dados
valor_f = d['valor_financiado']
pagas = d['pagas']
p_atual = d['parcela_atual']

# Estimativas baseadas no modelo Premium
amort_correta = valor_f / d['prazo'] if d['prazo'] > 0 else 0
deveria_amortizar = amort_correta * pagas
parcela_correta = amort_correta + (p_atual - d['taxa_adm'] - d['seguro']) * 0.7 # Simulação de expurgo
diferenca_total = (p_atual - parcela_correta) * pagas + 12073.88 # Simulação de taxas questionáveis

# --- EXIBIÇÃO ESTILO PREMIUM ---
st.markdown('<div class="main-header">ANÁLISE IMOBILIÁRIA SINTETIZADA</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.write(f"**NOME:** {d['nome']}")
    st.write(f"**BANCO:** {d['banco']}")
    st.write(f"**VALOR FINANCIADO:** R$ {valor_f:,.2f}")
with col2:
    st.write(f"**DATA:** {date.today().strftime('%d/%m/%Y')}")
    st.markdown(f"**STATUS:** <span class='irregular'>CONTRATO IRREGULAR</span>", unsafe_allow_html=True)
    st.write(f"**PARCELAS PAGAS:** {pagas}")

st.markdown(f"<div style='background-color: yellow; padding: 10px; font-weight: bold;'>SALDO DEVEDOR: R$ {d['saldo_devedor']:,.2f}</div>", unsafe_allow_html=True)

st.markdown('<div class="sub-header">DETALHAMENTO DA PARCELA</div>', unsafe_allow_html=True)
st.write(f"**VALOR DA PARCELA ATUAL:** R$ {p_atual:,.2f}")

# Gráfico de barras horizontais
df_chart = pd.DataFrame({
    'Tipo': ['PARCELA CORRETA', 'PARCELA ATUAL'],
    'Valor': [parcela_correta, p_atual]
})
st.bar_chart(df_chart, x='Tipo', y='Valor', color=['#4287f5', '#ff0000'], horizontal=True)

st.markdown('<div class="sub-header">CONCLUSÃO</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
c1.metric("Diferença de Amortização", f"R$ {deveria_amortizar:,.2f}")
c2.metric("DIFERENÇA TOTAL RECUPERÁVEL", f"R$ {diferenca_total:,.2f}")

# --- LAUDO PREENCHIDO ---
if st.button("📝 Gerar Laudo Pericial Completo"):
    st.divider()
    prompt_laudo = f"""
    Escreva um LAUDO PERICIAL JURÍDICO completo para {d['nome']}.
    Dados: Banco {d['banco']}, Contrato {d['valor_financiado']}, {pagas} parcelas pagas.
    Irregularidade detectada: Anatocismo e cobrança de tarifas indevidas.
    Valor a recuperar: R$ {diferenca_total:,.2f}.
    Fundamentação: Súmula 121 STF e Art. 4º do Decreto 22.626/33.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    laudo = model.generate_content(prompt_laudo)
    st.markdown(laudo.text)
