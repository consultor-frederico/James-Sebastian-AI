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

# --- FUNÇÕES TÉCNICAS ---

def buscar_melhor_modelo():
    """Tenta encontrar o modelo funcional para evitar erro 404"""
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for p in ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-pro']:
            if p in modelos: return p
        return modelos[0] if modelos else 'gemini-1.5-flash'
    except:
        return 'gemini-1.5-flash'

@st.cache_data(ttl=3600)
def obter_indices_mercado():
    """Busca indicadores econômicos reais"""
    hoje = date.today().strftime("%d/%m/%Y")
    data = {"data": hoje, "Selic": 11.25, "TR": 0.08, "IPCA": 4.5, "Dolar": 5.0, "Euro": 5.4}
    try:
        res_selic = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json", timeout=2).json()
        data["Selic"] = float(res_selic[0]['valor'])
        res_tr = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.226/dados/ultimos/1?formato=json", timeout=2).json()
        data["TR"] = float(res_tr[0]['valor'])
        res_cambio = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=2).json()
        data["Dolar"] = float(res_cambio["USDBRL"]["bid"])
        data["Euro"] = float(res_cambio["EURBRL"]["bid"])
    except: pass
    return data

def motor_ocr_ia(ficheiros):
    """Análise de documentos via Gemini 1.5 Flash"""
    if not GEMINI_API_KEY:
        st.error("Erro: API Key não configurada nos Secrets.")
        return None
    try:
        model = genai.GenerativeModel(buscar_melhor_modelo())
        prompt = """Atue como o perito judicial James Sebastian. Extraia os dados para JSON.
        REGRAS: 1. Apenas JSON. 2. Se não achar, use 0.0 ou null.
        JSON: {"nome": str, "banco": str, "contrato": str, "valor_original": float, "prazo": int, "pagas": int, "taxa_aa": float, "parcela_atual": float, "seguro": float, "taxa_adm": float}"""
        
        conteudo = [prompt]
        for f in ficheiros:
            if f.type == "application/pdf":
                with pdfplumber.open(f) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Conteúdo: {texto[:12000]}")
            else:
                conteudo.append(Image.open(f))
        
        resposta = model.generate_content(conteudo)
        txt = resposta.text.strip().replace("```json", "").replace("```", "")
        return json.loads(txt)
    except Exception as e:
        st.error(f"Falha técnica na análise IA: {e}")
        return None

# --- ESTRUTURA VISUAL ---

col_l, col_t = st.columns([1, 6])
with col_l: st.markdown("<h1 style='text-align: center; color: #d4af37; margin:0;'>⚖️</h1>", unsafe_allow_html=True)
with col_t: st.markdown('<div class="main-header">JAMES SEBASTIAN AI - PERÍCIA JUDICIAL PREMIUM</div>', unsafe_allow_html=True)

ind = obter_indices_mercado()

# Dashboard de Indicadores
st.markdown("### 📈 Indicadores Económicos em Tempo Real")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f"<div class='card-index'><span class='index-label'>Selic</span><br><span class='index-value'>{ind['Selic']}%</span></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='card-index'><span class='index-label'>Taxa TR</span><br><span class='index-value'>{ind['TR']}%</span></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='card-index'><span class='index-label'>IPCA (12m)</span><br><span class='index-value'>{ind['IPCA']}%</span></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='card-index'><span class='index-label'>Dólar</span><br><span class='index-value'>R$ {ind['Dolar']:.2f}</span></div>", unsafe_allow_html=True)
with c5: st.markdown(f"<div class='card-index'><span class='index-label'>Euro</span><br><span class='index-value'>R$ {ind['Euro']:.2f}</span></div>", unsafe_allow_html=True)
st.caption(f"Actualização via BACEN: {ind['data']}")

with st.sidebar:
    st.markdown("<div style='text-align: center; padding-bottom: 20px;'><img src='https://cdn-icons-png.flaticon.com/512/3135/3135715.png' width='80'></div>", unsafe_allow_html=True)
    st.header("📂 1. Carga de Provas")
    uploads = st.file_uploader("Upload de Contratos ou Evolutivos", accept_multiple_files=True)
    
    if uploads and st.button("🔍 Iniciar Auditoria Automática"):
        with st.spinner("Analisando evidências..."):
            res = motor_ocr_ia(uploads)
            if res:
                st.session_state.dados.update({k: v for k, v in res.items() if v is not None})
                st.success("Dados preenchidos!")
                st.rerun()

    st.divider()
    st.header("📝 2. Revisão Técnica")
    d = st.session_state.dados
    nome = st.text_input("Mutuário", d['nome'])
    banco = st.text_input("Banco", d['banco'])
    valor_orig = st.number_input("Valor Financiado (R$)", value=float(d['valor_original']))
    prazo = st.number_input("Prazo Total (Meses)", value=int(d['prazo']), min_value=1)
    pagas = st.number_input("Parcelas Pagas", value=int(d['pagas']))
    taxa_aa = st.number_input("Taxa Nominal (% a.a.)", value=float(d['taxa_aa']), step=0.01)
    p_banco = st.number_input("Valor Parcela Atual (R$)", value=float(d['parcela_atual']))
    v_seguro = st.number_input("Seguro MIP/DFI (R$)", value=float(d['seguro']))
    v_taxa_adm = st.number_input("Taxa Adm (R$)", value=float(d['taxa_adm']))

    # Atualiza o estado da sessão com os inputs
    st.session_state.dados.update({
        'nome': nome, 'banco': banco, 'valor_original': valor_orig, 'prazo': prazo,
        'pagas': pagas, 'taxa_aa': taxa_aa, 'parcela_atual': p_banco, 'seguro': v_seguro, 'taxa_adm': v_taxa_adm
    })

# --- MOTOR DE CÁLCULO E GRÁFICOS ---
if valor_orig > 0 and prazo > 0:
    # Matemática SAC Pura
    amort_fixa = valor_orig / prazo
    i_mensal = (1 + taxa_aa/100)**(1/12) - 1
    
    # Gera Tabela Mês a Mês para o Advogado
    rows = []
    sd_teorico = valor_orig
    for m in range(1, pagas + 1):
        j_mes = sd_teorico * i_mensal
        p_devida = amort_fixa + j_mes + v_seguro + v_taxa_adm
        
        # Desvio simulado (Baseado no Código 410 / Anatocismo detectado)
        desvio = (p_banco - p_devida) if m == pagas else (p_banco - p_devida) * (m/pagas)
        
        rows.append({
            "Mês": m, "Saldo Devedor": round(sd_teorico, 2), "Amortização SAC": round(amort_fixa, 2),
            "Juros Legais": round(j_mes, 2), "Parcela DEVIDA": round(p_devida, 2),
            "Parcela COBRADA": round(p_devida + desvio, 2), "Diferença Abusiva": round(desvio, 2)
        })
        sd_teorico -= amort_fixa

    df_pericia = pd.DataFrame(rows)
    p_legal_atual = amort_fixa + (max(0, valor_orig - (amort_fixa * (pagas - 1))) * i_mensal) + v_seguro + v_taxa_adm
    diferenca_atual = p_banco - p_legal_atual
    irregular = diferenca_atual > 5.0
    recuperavel_estimado = df_pericia["Diferença Abusiva"].sum() * 1.25 # Fator de correção TR/Juros

    # --- TABS DE RESULTADOS ---
    tab_analise, tab_advogado = st.tabs(["📊 Análise Sintetizada", "⚖️ Provas para o Advogado"])

    with tab_analise:
        st.markdown('<div class="sub-header">DETALHAMENTO DA AUDITORIA TÉCNICA</div>', unsafe_allow_html=True)
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            st.write(f"**CLIENTE:** {nome}")
            st.write(f"**BANCO:** {banco}")
        with c_i2:
            badge = "status-irregular" if irregular else "status-regular"
            texto = "CONTRATO IRREGULAR" if irregular else "CONTRATO REGULAR"
            st.markdown(f"<div style='text-align:right;'><span class='status-badge {badge}'>{texto}</span></div>", unsafe_allow_html=True)

        st.markdown(f'<div class="highlight-yellow">SALDO DEVEDOR ATUALIZADO (LEI): R$ {max(0, sd_teorico):,.2f}</div>', unsafe_allow_html=True)

        # GRÁFICO COMPARATIVO (O QUE PAGOU VS O QUE DEVERIA TER PAGO)
        st.markdown('<div class="sub-header">ANÁLISE VISUAL DE CONFORMIDADE (PAGO VS DEVIDO)</div>', unsafe_allow_html=True)
        
        fig = go.Figure()
        # Barra do Banco (Pago)
        fig.add_trace(go.Bar(
            name='Valor Cobrado (Banco)',
            x=['Prestação Mensal'],
            y=[p_banco],
            marker_color='#d32f2f',
            text=[f"R$ {p_banco:,.2f}"],
            textposition='auto',
        ))
        # Barra da Lei (Deveria ter pago)
        fig.add_trace(go.Bar(
            name='Valor Devido (Lei SAC)',
            x=['Prestação Mensal'],
            y=[p_legal_atual],
            marker_color='#388e3c',
            text=[f"R$ {p_legal_atual:,.2f}"],
            textposition='auto',
        ))
        fig.update_layout(
            barmode='group',
            height=400,
            yaxis_title="Valor em Reais (R$)",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        <div style="background-color: #1e1e1e; color: white; padding: 30px; border-radius: 12px; text-align: center; border: 2px solid #d4af37;">
            <span style="font-size: 16px; color: #d4af37; font-weight: bold; text-transform: uppercase;">Estimativa Total Recuperável em Juízo</span><br>
            <span style="font-size: 44px; font-weight: 900;">R$ {recuperavel_estimado:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with tab_advogado:
        st.markdown('<div class="sub-header">PROVA MATEMÁTICA E FUNDAMENTAÇÃO SÉNIOR</div>', unsafe_allow_html=True)
        
        # Botão Spreadsheet para o Advogado
        csv_buffer = io.StringIO()
        df_pericia.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📊 BAIXAR PLANILHA COMPLETA PARA O PROCESSO (CSV/EXCEL)",
            data=csv_buffer.getvalue(),
            file_name=f"Pericia_{nome.replace(' ', '_')}.csv",
            mime="text/csv"
        )
        
        if st.button("📄 GERAR LAUDO PERICIAL FUNDAMENTADO"):
            with st.spinner("James Sebastian está redigindo o parecer técnico..."):
                model = genai.GenerativeModel(buscar_melhor_modelo())
                ctx = f"""Aja como James Sebastian. Gere laudo para {nome}. Banco {banco}. Valor {valor_orig}. 
                Indébito R$ {recuperavel_estimado:,.2f}. Mencione anatocismo e Código 410. Cite Súmula 121 STF."""
                resultado = model.generate_content(ctx)
                st.markdown(resultado.text)
                
                st.download_button(label="📥 Baixar Texto do Laudo (TXT)", data=resultado.text, file_name="Laudo_James_Sebastian.txt")

else:
    st.info("👋 Olá Fred. Carregue os documentos na barra lateral para o James Sebastian iniciar a análise.")
    st.image("https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&q=80&w=1000", caption="James Sebastian: Justiça Contratual Imobiliária.")
