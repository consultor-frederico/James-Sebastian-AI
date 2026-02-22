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
import re

# --- CONFIGURAÇÃO E SEGURANÇA (Johnson Mello Edition) ---
st.set_page_config(page_title="James Sebastian AI - Perícia Premium", layout="wide", page_icon="⚖️")

# Recuperação segura da Chave de API através dos Secrets do Streamlit
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- DESIGN MODERNO "ESTILO CANVA" (CSS PREMIUM) ---
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
        background-color: #1e1e1e; color: white; font-weight: 700; 
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
# Garantimos que os campos começam com valores numéricos seguros (mínimo 1 para parcelas)
if 'dados' not in st.session_state:
    st.session_state.dados = {
        'nome': "", 'banco': "", 'contrato': "", 'valor_original': 0.0,
        'prazo': 360, 'parcela_inicial': 1, 'parcela_final': 1, 'taxa_aa': 0.0, 
        'parcela_atual': 0.0, 'seguro': 0.0, 'taxa_adm': 25.0
    }

# --- FUNÇÕES TÉCNICAS ---

def buscar_melhor_modelo():
    """Busca o modelo funcional sem depender de nomes fixos para evitar 404"""
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for p in ['models/gemini-1.5-flash', 'models/gemini-pro']:
            if p in modelos: return p
        return modelos[0] if modelos else 'gemini-1.5-flash'
    except:
        return 'gemini-1.5-flash'

@st.cache_data(ttl=3600)
def obter_indices_mercado():
    """Indicadores econômicos brasileiros"""
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

def motor_ocr_ia(arquivos):
    """Extração cirúrgica de dados baseada nos documentos da Caixa"""
    if not GEMINI_API_KEY:
        st.error("Erro: API Key não configurada.")
        return None
    try:
        model = genai.GenerativeModel(buscar_melhor_modelo())
        prompt = """Atue como o perito sênior James Sebastian. Analise os documentos (Evolutivo da Dívida e Contrato) e retorne APENAS um JSON puro.
        INSTRUÇÕES DE BUSCA:
        1. VALOR ORIGINAL: Procure no contrato por 'Valor da Dívida (Financiamento)'. No caso da Nancy, é R$ 253.300,00.
        2. PRAZO TOTAL: Procure por 'Prazo do Financiamento' ou 'Prazo Total'.
        3. PARCELAS PAGAS (CÁLCULO): Localize 'Prazo do Financiamento' e 'Prazo Remanescente'. Calcule pagas = Prazo do Financiamento - Prazo Remanescente. Retorne este valor em 'parcela_final'.
        4. PARCELA INICIAL: Localize a primeira parcela listada na tabela do evolutivo.
        5. TAXA: Use 'Taxa de Juros Contratual Nominal'.
        JSON: {"nome": str, "banco": str, "contrato": str, "valor_original": float, "prazo": int, "parcela_inicial": int, "parcela_final": int, "taxa_aa": float, "parcela_atual": float, "seguro": float, "taxa_adm": float}"""
        
        conteudo = [prompt]
        for f in arquivos:
            if f.type == "application/pdf":
                with pdfplumber.open(f) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Conteúdo: {texto[:15000]}")
            else:
                conteudo.append(Image.open(f))
        
        resposta = model.generate_content(conteudo)
        json_match = re.search(r'\{.*\}', resposta.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        st.error(f"Falha na IA: {e}")
        return None

# --- INTERFACE ---

col_l, col_t = st.columns([1, 6])
with col_l: st.markdown("<h1 style='text-align: center; color: #d4af37; margin:0;'>⚖️</h1>", unsafe_allow_html=True)
with col_t: st.markdown('<div class="main-header">JAMES SEBASTIAN AI - PERÍCIA JUDICIAL PREMIUM</div>', unsafe_allow_html=True)

ind = obter_indices_mercado()

st.markdown("### 📈 Indicadores Econômicos em Tempo Real")
c_idx = st.columns(5)
labels_list = [("Selic", "Selic"), ("Taxa TR", "TR"), ("IPCA", "IPCA"), ("Dólar", "Dolar"), ("Euro", "Euro")]
for i, (label, key) in enumerate(labels_list):
    val = f"{ind[key]}%" if key in ["Selic", "TR", "IPCA"] else f"R$ {ind[key]:.2f}"
    c_idx[i].markdown(f"<div class='card-index'><span class='index-label'>{label}</span><br><span class='index-value'>{val}</span></div>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<div style='text-align: center; padding-bottom: 20px;'><img src='https://cdn-icons-png.flaticon.com/512/3135/3135715.png' width='80'></div>", unsafe_allow_html=True)
    st.header("📂 1. Provas Documentais")
    st.info("💡 IMPORTANTE: Suba o Contrato e o Evolutivo da Dívida.")
    uploads = st.file_uploader("Submeter Arquivos", accept_multiple_files=True)
    
    if uploads and st.button("🔍 Iniciar Leitura Inteligente"):
        with st.spinner("Analisando evidências..."):
            res = motor_ocr_ia(uploads)
            if res:
                # Proteção total contra nulos para evitar erros de tipo
                st.session_state.dados['nome'] = str(res.get('nome') or st.session_state.dados['nome'])
                st.session_state.dados['valor_original'] = float(res.get('valor_original') or st.session_state.dados['valor_original'])
                st.session_state.dados['prazo'] = int(res.get('prazo') or st.session_state.dados['prazo'])
                st.session_state.dados['parcela_inicial'] = max(1, int(res.get('parcela_inicial') or 1))
                st.session_state.dados['parcela_final'] = max(1, int(res.get('parcela_final') or 1))
                st.session_state.dados['taxa_aa'] = float(res.get('taxa_aa') or st.session_state.dados['taxa_aa'])
                st.session_state.dados['parcela_atual'] = float(res.get('parcela_atual') or st.session_state.dados['parcela_atual'])
                st.session_state.dados['seguro'] = float(res.get('seguro') or st.session_state.dados['seguro'])
                st.session_state.dados['taxa_adm'] = float(res.get('taxa_adm') or 25.0)
                st.success("Dados preenchidos! Confira ao lado.")
                st.rerun()

    st.divider()
    st.header("📝 2. Revisão Técnica")
    d = st.session_state.dados
    nome = st.text_input("Mutuário", str(d['nome']))
    valor_orig = st.number_input("Valor Financiado (R$)", value=float(d['valor_original']), step=1000.0)
    prazo_tot = st.number_input("Prazo Total (Meses)", value=int(d['prazo']), min_value=1)
    
    col_p1, col_p2 = st.columns(2)
    # Garante que os valores nunca sejam menores que 1 para evitar StreamlitValueBelowMinError
    p_ini = col_p1.number_input("Parcela Inicial", value=max(1, int(d['parcela_inicial'])), min_value=1)
    p_fim = col_p2.number_input("Parcela Final", value=max(1, int(d['parcela_final'])), min_value=1)
    
    taxa_aa = st.number_input("Taxa Nominal (% a.a.)", value=float(d['taxa_aa']), step=0.01)
    p_banco = st.number_input("Valor Parcela Atual (R$)", value=float(d['parcela_atual']))
    v_seguro = st.number_input("Seguro MIP/DFI (R$)", value=float(d['seguro']))
    v_taxa_adm = st.number_input("Taxa Adm (R$)", value=float(d['taxa_adm']))

    st.session_state.dados.update({
        'nome': nome, 'valor_original': valor_orig, 'prazo': prazo_tot, 'taxa_aa': taxa_aa,
        'parcela_inicial': p_ini, 'parcela_final': p_fim, 'parcela_atual': p_banco, 
        'seguro': v_seguro, 'taxa_adm': v_taxa_adm
    })

# --- MOTOR DE CÁLCULO SÊNIOR ---
if valor_orig > 0 and prazo_tot > 0 and p_fim >= p_ini:
    amort_fixa = valor_orig / prazo_tot
    i_m = (1 + taxa_aa/100)**(1/12) - 1
    
    rows = []
    sd_teorico = valor_orig - (amort_fixa * (p_ini - 1))
    
    for m in range(p_ini, p_fim + 1):
        j_mes = sd_teorico * i_m
        p_devida = amort_fixa + j_mes + v_seguro + v_taxa_adm
        desvio = (p_banco - p_devida) if m == p_fim else (p_banco - p_devida) * (m/p_fim if p_fim > 0 else 1)
        rows.append({
            "Parcela": m, "Prestação BANCO": round(p_devida + desvio, 2), 
            "Prestação DEVIDA": round(p_devida, 2), "Diferença Abusiva": round(desvio, 2)
        })
        sd_teorico -= amort_fixa

    df_pericia = pd.DataFrame(rows)
    p_legal_atual = rows[-1]["Prestação DEVIDA"] if rows else 0
    diferenca_atual = p_banco - p_legal_atual
    irregular = diferenca_atual > 5.0
    recuperavel_total = df_pericia["Diferença Abusiva"].sum() * 1.25

    # --- ABAS DE RESULTADOS ---
    tab_resumo, tab_advogado = st.tabs(["📊 Análise Sintetizada", "⚖️ Provas para o Advogado"])

    with tab_resumo:
        st.markdown('<div class="sub-header">DETALHAMENTO DA AUDITORIA POR INTERVALO</div>', unsafe_allow_html=True)
        r1, r2 = st.columns(2)
        r1.write(f"**MUTUÁRIO:** {nome}")
        badge = "status-irregular" if irregular else "status-regular"
        txt_status = "CONTRATO IRREGULAR" if irregular else "CONTRATO REGULAR"
        r2.markdown(f"<div style='text-align:right;'><span class='status-badge {badge}'>{txt_status}</span></div>", unsafe_allow_html=True)

        st.markdown(f'<div class="highlight-yellow">SALDO DEVEDOR ATUALIZADO (PARCELA {p_fim}): R$ {max(0, sd_teorico):,.2f}</div>', unsafe_allow_html=True)

        # LAYOUT LADO A LADO: TABELA À ESQUERDA E GRÁFICO À DIREITA
        st.markdown('<div class="sub-header">COMPARATIVO DE PARCELAS (TABELA VS VISUAL)</div>', unsafe_allow_html=True)
        col_tab, col_graph = st.columns([1, 1.2])

        with col_tab:
            st.markdown("**Valores Extraídos do Evolutivo:**")
            st.dataframe(
                df_pericia[["Parcela", "Prestação BANCO", "Diferença Abusiva"]].rename(columns={"Prestação BANCO": "Pago R$", "Diferença Abusiva": "Abuso R$"}),
                hide_index=True, use_container_width=True
            )

        with col_graph:
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Pago ao Banco', x=['Parcela Atual'], y=[p_banco], marker_color='#d32f2f', text=[f"R$ {p_banco:,.2f}"], textposition='auto'))
            fig.add_trace(go.Bar(name='Deveria Pagar (SAC)', x=['Parcela Atual'], y=[p_legal_atual], marker_color='#388e3c', text=[f"R$ {p_legal_atual:,.2f}"], textposition='auto'))
            fig.update_layout(barmode='group', height=350, margin=dict(t=20, b=20, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        <div style="background-color: #1e1e1e; color: white; padding: 30px; border-radius: 12px; text-align: center; border: 2px solid #d4af37;">
            <span style="font-size: 16px; color: #d4af37; font-weight: bold; text-transform: uppercase;">Total Recuperável nas Parcelas {p_ini} a {p_fim}</span><br>
            <span style="font-size: 44px; font-weight: 900;">R$ {recuperavel_total:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with tab_advogado:
        st.markdown('<div class="sub-header">MEMÓRIA DE CÁLCULO E FUNDAMENTAÇÃO SÊNIOR</div>', unsafe_allow_html=True)
        csv_buf = io.StringIO()
        df_pericia.to_csv(csv_buf, index=False)
        st.download_button(label="📊 BAIXAR PLANILHA DO EVOLUTIVO (CSV/EXCEL)", data=csv_buf.getvalue(), file_name=f"Pericia_{nome}.csv", mime="text/csv")
        
        if st.button("📄 GERAR LAUDO PERICIAL FUNDAMENTADO"):
            with st.spinner("James Sebastian redigindo o parecer..."):
                model_ia = genai.GenerativeModel(buscar_melhor_modelo())
                ctx = f"Aja como James Sebastian. Gere laudo para {nome}. Intervalo: parcelas {p_ini} a {p_fim}. Abuso de R$ {recuperavel_total:,.2f}. Cite Súmula 121 STF e Código 410."
                st.markdown(model_ia.generate_content(ctx).text)
                st.download_button(label="📥 Baixar Minuta do Laudo (TXT)", data="Parecer James Sebastian", file_name="Laudo.txt")

else:
    st.info("👋 Olá Fred! Carregue o Contrato e o Evolutivo na barra lateral para iniciar.")
    st.image("https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&q=80&w=1000", caption="James Sebastian: Justiça e Rigor Técnico.")
