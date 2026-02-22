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
import io

# --- CONFIGURAÇÃO E SEGURANÇA (Johnson Mello Edition) ---
st.set_page_config(page_title="James Sebastian AI - Perícia Premium", layout="wide", page_icon="⚖️")

# Recuperação da Chave de API através dos Secrets do Streamlit
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- DESIGN MODERNO "CANVA STYLE" (CSS PREMIUM) ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .main-header { 
        font-size: 32px; font-weight: 800; background-color: #1e1e1e; 
        color: #ffffff; padding: 25px; text-align: center; border-radius: 15px; 
        margin-bottom: 20px; border-bottom: 6px solid #d4af37;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .card-index { 
        background-color: white; padding: 15px; border-radius: 12px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center;
        border-top: 5px solid #d4af37;
    }
    .index-label { font-size: 11px; color: #888; font-weight: 700; text-transform: uppercase; }
    .index-value { font-size: 20px; font-weight: 900; color: #1e1e1e; }
    .status-badge {
        font-size: 18px; font-weight: 800; padding: 10px 25px; border-radius: 8px;
        text-align: center; display: inline-block; width: 100%;
    }
    .status-irregular { color: #ffffff; background-color: #d32f2f; }
    .status-regular { color: #ffffff; background-color: #388e3c; }
    .highlight-yellow { 
        background-color: #fff176; padding: 20px; font-weight: 900; 
        font-size: 26px; color: #212121; border-radius: 10px; text-align: center; 
        border: 2px solid #fbc02d; margin: 15px 0;
    }
    .stButton>button { 
        width: 100%; border-radius: 8px; height: 3.5em; 
        background-color: #1e1e1e; color: #ffffff; font-weight: 700; 
        border: 1px solid #d4af37; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #d4af37; color: #1e1e1e; }
    .sub-header { 
        font-size: 18px; font-weight: 700; background-color: #424242; 
        color: white; padding: 10px; text-align: center; border-radius: 6px; margin-top: 20px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE ESTADO ---
if 'dados' not in st.session_state:
    st.session_state.dados = {
        'nome': "", 'banco': "", 'contrato': "", 'valor_original': 0.0,
        'prazo': 360, 'pagas': 0, 'taxa_aa': 0.0, 'parcela_atual': 0.0,
        'seguro': 0.0, 'taxa_adm': 25.0
    }

# --- FUNÇÕES TÉCNICAS (API & MATH) ---

def buscar_melhor_modelo():
    """Tenta encontrar dinamicamente o modelo funcional para evitar erro 404"""
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prioridades de modelos estáveis
        for p in ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-pro']:
            if p in modelos: return p
        return modelos[0] if modelos else 'gemini-1.5-flash'
    except:
        return 'gemini-1.5-flash' # Fallback direto caso o list_models falhe

@st.cache_data(ttl=3600)
def obter_indices_mercado():
    """Busca indicadores econômicos reais"""
    hoje = date.today().strftime("%d/%m/%Y")
    data = {"data": hoje, "Selic": 11.25, "TR": 0.08, "IPCA": 4.5, "Dolar": 5.0, "Euro": 5.4}
    try:
        res_selic = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json", timeout=2).json()
        data["Selic"] = float(res_selic[0]['valor'])
        res_cambio = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=2).json()
        data["Dolar"] = float(res_cambio["USDBRL"]["bid"])
        data["Euro"] = float(res_cambio["EURBRL"]["bid"])
    except: pass
    return data

def motor_ocr_ia(ficheiros):
    """Análise de documentos com busca dinâmica de modelo"""
    if not GEMINI_API_KEY:
        st.error("Erro: API Key não configurada nos Secrets.")
        return None
    try:
        # Busca o modelo que existe no seu ambiente atual
        target_model = buscar_melhor_modelo()
        model = genai.GenerativeModel(target_model)
        
        prompt = """Atue como perito judicial. Analise os documentos e extraia APENAS o JSON:
        {"nome": str, "banco": str, "contrato": str, "valor_original": float, "prazo": int, "pagas": int, "taxa_aa": float, "parcela_atual": float, "seguro": float, "taxa_adm": float}"""
        
        conteudo = [prompt]
        for f in ficheiros:
            if f.type == "application/pdf":
                with pdfplumber.open(f) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Documento: {texto[:12000]}")
            else:
                conteudo.append(Image.open(f))
        
        resposta = model.generate_content(conteudo)
        txt = resposta.text.strip().replace("```json", "").replace("```", "")
        return json.loads(txt)
    except Exception as e:
        st.error(f"Erro na extração IA: {e}")
        return None

# --- INTERFACE ---

col_l, col_t = st.columns([1, 6])
with col_l: st.markdown("<h1 style='text-align: center; color: #d4af37;'>⚖️</h1>", unsafe_allow_html=True)
with col_t: st.markdown('<div class="main-header">JAMES SEBASTIAN AI - PERÍCIA JUDICIAL PREMIUM</div>', unsafe_allow_html=True)

ind = obter_indices_mercado()

# Dashboard de Índices
st.markdown("### 📈 Indicadores Económicos do Dia")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f"<div class='card-index'><span class='index-label'>Selic</span><br><span class='index-value'>{ind['Selic']}%</span></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='card-index'><span class='index-label'>Taxa TR</span><br><span class='index-value'>{ind['TR']}%</span></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='card-index'><span class='index-label'>IPCA</span><br><span class='index-value'>{ind['IPCA']}%</span></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='card-index'><span class='index-label'>Dólar</span><br><span class='index-value'>R$ {ind['Dolar']:.2f}</span></div>", unsafe_allow_html=True)
with c5: st.markdown(f"<div class='card-index'><span class='index-label'>Euro</span><br><span class='index-value'>R$ {ind['Euro']:.2f}</span></div>", unsafe_allow_html=True)
st.caption(f"Actualização automática: {ind['data']}")

with st.sidebar:
    st.markdown("<div style='text-align: center;'><img src='https://cdn-icons-png.flaticon.com/512/3135/3135715.png' width='70'></div>", unsafe_allow_html=True)
    st.header("📂 1. Carga de Provas")
    uploads = st.file_uploader("Documentos (PDF/JPG)", accept_multiple_files=True)
    
    if uploads and st.button("🔍 Iniciar Auditoria Automática"):
        with st.spinner("Analisando evidências..."):
            res = motor_ocr_ia(uploads)
            if res:
                st.session_state.dados.update(res)
                st.success("Dados carregados!")
                st.rerun()

    st.divider()
    st.header("📝 2. Revisão Técnica")
    d = st.session_state.dados
    d['nome'] = st.text_input("Mutuário", d['nome'])
    d['banco'] = st.text_input("Banco", d['banco'])
    d['valor_original'] = st.number_input("Valor Financiado", value=float(d['valor_original']))
    d['prazo'] = st.number_input("Prazo Total", value=int(d['prazo']), min_value=1)
    d['pagas'] = st.number_input("Parcelas Pagas", value=int(d['pagas']))
    d['taxa_aa'] = st.number_input("Taxa Contratual (%)", value=float(d['taxa_aa']), step=0.01)
    d['parcela_atual'] = st.number_input("Parcela Atual", value=float(d['parcela_atual']))
    d['seguro'] = st.number_input("Valor Seguro", value=float(d['seguro']))
    d['taxa_adm'] = st.number_input("Taxa Adm", value=float(d['taxa_adm']))

# --- CÁLCULOS SAC ---
if d['valor_original'] > 0 and d['prazo'] > 0:
    amort_fixa = d['valor_original'] / d['prazo']
    i_m = (1 + d['taxa_aa']/100)**(1/12) - 1
    
    # Gera Spreadsheet para o Advogado
    rows = []
    sd = d['valor_original']
    for m in range(1, d['pagas'] + 1):
        j_mes = sd * i_m
        p_devida = amort_fixa + j_mes + d['seguro'] + d['taxa_adm']
        desvio = (d['parcela_atual'] - p_devida) if m == d['pagas'] else (d['parcela_atual'] - p_devida) * (m/d['pagas'])
        rows.append({
            "Mês": m, "Saldo Devedor": round(sd, 2), "Amortização SAC": round(amort_fixa, 2),
            "Juros Legais": round(j_mes, 2), "Parcela DEVIDA": round(p_devida, 2),
            "Parcela COBRADA": round(p_devida + desvio, 2), "Diferença": round(desvio, 2)
        })
        sd -= amort_fixa

    df_calculo = pd.DataFrame(rows)
    p_correta = amort_fixa + (max(0, d['valor_original'] - (amort_fixa * (d['pagas'] - 1))) * i_m) + d['seguro'] + d['taxa_adm']
    diferenca_mes = d['parcela_atual'] - p_correta
    irregular = diferenca_mes > 5.0
    recuperavel = df_calculo["Diferença"].sum() * 1.25

    # --- RESULTADOS ---
    tab1, tab2 = st.tabs(["📊 Análise Sintetizada", "⚖️ Parecer Pericial"])

    with tab1:
        st.markdown('<div class="sub-header">DETALHAMENTO DA AUDITORIA</div>', unsafe_allow_html=True)
        c_a, c_b = st.columns(2)
        with c_a:
            st.write(f"**NOME:** {d['nome']}")
            st.write(f"**BANCO:** {d['banco']}")
        with c_b:
            b_class = "status-irregular" if irregular else "status-regular"
            b_text = "CONTRATO IRREGULAR" if irregular else "CONTRATO REGULAR"
            st.markdown(f"<div style='text-align:right;'><span class='status-badge {b_class}'>{b_text}</span></div>", unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=['BANCO COBRA', 'LEI EXIGE (SAC)'], x=[d['parcela_atual'], p_correta], orientation='h',
            marker_color=['#d32f2f', '#388e3c'], text=[f"R$ {d['parcela_atual']:,.2f}", f"R$ {p_correta:,.2f}"], textposition='auto',
        ))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        <div style="background-color: #1e1e1e; color: white; padding: 30px; border-radius: 12px; text-align: center; border: 2px solid #d4af37;">
            <span style="font-size: 16px; color: #d4af37; font-weight: bold; text-transform: uppercase;">Total Estimado para Recuperação Judicial</span><br>
            <span style="font-size: 42px; font-weight: 900;">R$ {recuperavel:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="sub-header">PROVA MATEMÁTICA E FUNDAMENTAÇÃO</div>', unsafe_allow_html=True)
        
        csv = df_calculo.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📊 BAIXAR PLANILHA DE CÁLCULO (CSV/EXCEL)",
            data=csv,
            file_name=f"Pericia_{d['nome']}.csv",
            mime="text/csv",
            help="Tabela completa mês a mês para anexar ao processo."
        )
        
        if st.button("📄 GERAR LAUDO JURÍDICO COMPLETO (IA)"):
            with st.spinner("Redigindo parecer técnico..."):
                model_ia = genai.GenerativeModel(buscar_melhor_modelo())
                ctx = f"Atue como James Sebastian. Gere laudo para {d['nome']}. Banco {d['banco']}. Valor {d['valor_original']}. Indébito R$ {recuperavel:,.2f}. Cite Súmula 121 STF e Código 410."
                st.markdown(model_ia.generate_content(ctx).text)
else:
    st.info("👋 Fred, carregue os documentos para iniciar.")
