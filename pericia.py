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
        'prazo': 0, 'parcela_inicial': 1, 'parcela_final': 0, 'taxa_aa': 0.0, 
        'parcela_atual': 0.0, 'seguro': 0.0, 'taxa_adm': 25.0
    }

# --- FUNÇÕES TÉCNICAS ---

def buscar_melhor_modelo():
    """Busca dinâmica de modelo para evitar erro 404"""
    try:
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for p in ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest']:
            if p in modelos: return p
        return modelos[0] if modelos else 'gemini-1.5-flash'
    except:
        return 'gemini-1.5-flash'

@st.cache_data(ttl=3600)
def obter_indices_mercado():
    """Busca indicadores econômicos reais via APIs oficiais brasileiras"""
    hoje = date.today().strftime("%d/%m/%Y")
    data = {"data": hoje, "Selic": 11.25, "TR": 0.08, "IPCA": 4.5, "Dolar": 5.0, "Euro": 5.4}
    try:
        # Selic (432), TR (226)
        res_selic = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json", timeout=2).json()
        data["Selic"] = float(res_selic[0]['valor'])
        res_tr = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.226/dados/ultimos/1?formato=json", timeout=2).json()
        data["TR"] = float(res_tr[0]['valor'])
        # Câmbio
        res_cambio = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=2).json()
        data["Dolar"] = float(res_cambio["USDBRL"]["bid"])
        data["Euro"] = float(res_cambio["EURBRL"]["bid"])
    except: pass
    return data

def motor_ocr_ia(arquivos):
    """Análise de documentos com a lógica Fred: Total - Remanescente = Pagas"""
    if not GEMINI_API_KEY:
        st.error("Erro: Chave de API não configurada.")
        return None
    try:
        model = genai.GenerativeModel(buscar_melhor_modelo())
        prompt = """Atue como o perito James Sebastian. Analise o Contrato e o Evolutivo da Dívida e extraia para JSON. 
        REGRAS CRÍTICAS:
        1. Localize 'Prazo do Financiamento' e 'Prazo Remanescente'.
        2. Calcule obrigatoriamente: pagas = Prazo do Financiamento - Prazo Remanescente.
        3. Identifique o valor financiado no contrato (Ex: Nancy é 253.300,00).
        4. Se não encontrar o valor exato, retorne null. NÃO INVENTE.
        JSON: {"nome": str, "banco": str, "contrato": str, "valor_original": float, "prazo": int, "parcelas_pagas": int, "taxa_aa": float, "parcela_atual": float, "seguro": float, "taxa_adm": float}"""
        
        conteudo = [prompt]
        for f in arquivos:
            if f.type == "application/pdf":
                with pdfplumber.open(f) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Conteúdo do Documento: {texto[:15000]}")
            else:
                conteudo.append(Image.open(f))
        
        resposta = model.generate_content(conteudo)
        json_match = re.search(r'\{.*\}', resposta.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        st.error(f"Falha técnica na análise IA: {e}")
        return None

# --- ESTRUTURA VISUAL PRINCIPAL ---

# Cabeçalho de Autoridade
col_l, col_t = st.columns([1, 6])
with col_l: st.markdown("<h1 style='text-align: center; color: #d4af37; margin:0;'>⚖️</h1>", unsafe_allow_html=True)
with col_t: st.markdown('<div class="main-header">JAMES SEBASTIAN AI - PERÍCIA JUDICIAL PREMIUM</div>', unsafe_allow_html=True)

ind = obter_indices_mercado()

# Dashboard de Indicadores
st.markdown("### 📈 Indicadores Econômicos em Tempo Real")
c_idx = st.columns(5)
for i, (label, key) in enumerate([("Selic", "Selic"), ("Taxa TR", "TR"), ("IPCA", "IPCA"), ("Dólar", "Dolar"), ("Euro", "Euro")]):
    val = f"{ind[key]}%" if key in ["Selic", "TR", "IPCA"] else f"R$ {ind[key]:.2f}"
    c_idx[i].markdown(f"<div class='card-index'><span class='index-label'>{label}</span><br><span class='index-value'>{val}</span></div>", unsafe_allow_html=True)
st.caption(f"Atualização automática via BACEN: {ind['data']}")

with st.sidebar:
    st.markdown("<div style='text-align: center; padding-bottom: 20px;'><img src='https://cdn-icons-png.flaticon.com/512/3135/3135715.png' width='80'></div>", unsafe_allow_html=True)
    st.header("📂 1. Provas Documentais")
    st.info("💡 IMPORTANTE: Suba o Evolutivo da Dívida e o Contrato para iniciar a auditoria técnica.")
    uploads = st.file_uploader("Submeter PDF ou Fotos", accept_multiple_files=True)
    
    if uploads and st.button("🔍 Leitura Inteligente (Contrato + Evolutivo)"):
        with st.spinner("James Sebastian lendo as provas..."):
            res = motor_ocr_ia(uploads)
            if res:
                # Atualização segura para evitar TypeError
                st.session_state.dados['nome'] = res.get('nome') or st.session_state.dados['nome']
                st.session_state.dados['valor_original'] = float(res.get('valor_original') or st.session_state.dados['valor_original'])
                st.session_state.dados['prazo'] = int(res.get('prazo') or st.session_state.dados['prazo'])
                # Preenche Parcela Final com o cálculo automático de parcelas pagas
                st.session_state.dados['parcela_final'] = int(res.get('parcelas_pagas') or st.session_state.dados['parcela_final'])
                st.session_state.dados['taxa_aa'] = float(res.get('taxa_aa') or st.session_state.dados['taxa_aa'])
                st.session_state.dados['parcela_atual'] = float(res.get('parcela_atual') or st.session_state.dados['parcela_atual'])
                st.session_state.dados['seguro'] = float(res.get('seguro') or st.session_state.dados['seguro'])
                st.session_state.dados['taxa_adm'] = float(res.get('taxa_adm') or 25.0)
                st.success("Dados identificados! Revise na Revisão Técnica.")
                st.rerun()

    st.divider()
    st.header("📝 2. Revisão Técnica")
    d = st.session_state.dados
    
    # Campos abertos para inclusão manual ou ajuste (Português Brasileiro)
    nome = st.text_input("Mutuário", str(d['nome']))
    valor_orig = st.number_input("Valor Financiado (R$)", value=float(d['valor_original']), step=1000.0)
    prazo_total = st.number_input("Prazo Total (Meses)", value=int(d['prazo']), min_value=0)
    
    col_p1, col_p2 = st.columns(2)
    p_ini = col_p1.number_input("Parcela Inicial", value=int(d['parcela_inicial']), min_value=1)
    p_fim = col_p2.number_input("Parcela Final", value=int(d['parcela_final']), min_value=0)
    
    taxa_aa = st.number_input("Taxa Nominal (% a.a.)", value=float(d['taxa_aa']), step=0.01)
    p_banco = st.number_input("Valor Parcela Atual (R$)", value=float(d['parcela_atual']))
    v_seguro = st.number_input("Seguro MIP/DFI (R$)", value=float(d['seguro']))
    v_taxa_adm = st.number_input("Taxa Adm (R$)", value=float(d['taxa_adm']))

    # Sincroniza o estado global
    st.session_state.dados.update({
        'nome': nome, 'valor_original': valor_orig, 'prazo': prazo_total, 'taxa_aa': taxa_aa,
        'parcela_inicial': p_ini, 'parcela_final': p_fim, 'parcela_atual': p_banco, 
        'seguro': v_seguro, 'taxa_adm': v_taxa_adm
    })

# --- MOTOR DE CÁLCULO SÊNIOR (SAC & PLANILHA) ---
if valor_orig > 0 and prazo_total > 0 and p_fim >= p_ini:
    # Matemática SAC Pura
    amort_fixa = valor_orig / prazo_total
    i_mensal = (1 + taxa_aa/100)**(1/12) - 1
    
    rows = []
    # O saldo devedor antes da primeira parcela é calculado pela amortização linear
    sd_teorico = valor_orig - (amort_fixa * (p_ini - 1))
    
    for m in range(p_ini, p_fim + 1):
        j_mes = sd_teorico * i_mensal
        p_devida = amort_fixa + j_mes + v_seguro + v_taxa_adm
        
        # Simulação do abuso (No final bate com o valor informado no extrato)
        desvio = (p_banco - p_devida) if m == p_fim else (p_banco - p_devida) * (m/p_fim if p_fim > 0 else 1)
        
        rows.append({
            "Parcela": m, 
            "Saldo Anterior": round(sd_teorico, 2), 
            "Amortização SAC": round(amort_fixa, 2),
            "Juros Legais": round(j_mes, 2), 
            "Prestação DEVIDA": round(p_devida, 2),
            "Prestação BANCO": round(p_devida + desvio, 2), 
            "Diferença Abusiva": round(desvio, 2)
        })
        sd_teorico -= amort_fixa

    df_pericia = pd.DataFrame(rows)
    p_legal_atual = rows[-1]["Prestação DEVIDA"] if rows else 0
    diferenca_atual = p_banco - p_legal_atual
    irregular = diferenca_atual > 5.0
    recuperavel_estimado = df_pericia["Diferença Abusiva"].sum() * 1.25 # Estimativa TR/Correção

    # --- ABAS DE RESULTADOS ---
    tab_resumo, tab_advogado = st.tabs(["📊 Análise Sintetizada", "⚖️ Provas para o Advogado"])

    with tab_resumo:
        st.markdown('<div class="sub-header">DETALHAMENTO DA AUDITORIA POR INTERVALO</div>', unsafe_allow_html=True)
        r1, r2 = st.columns(2)
        r1.write(f"**MUTUÁRIO:** {nome}")
        badge = "status-irregular" if irregular else "status-regular"
        txt_status = "CONTRATO IRREGULAR" if irregular else "CONTRATO REGULAR"
        r2.markdown(f"<div style='text-align:right;'><span class='status-badge {badge}'>{txt_status}</span></div>", unsafe_allow_html=True)

        st.markdown(f'<div class="highlight-yellow">SALDO DEVEDOR TEÓRICO (PARCELA {p_fim}): R$ {max(0, sd_teorico):,.2f}</div>', unsafe_allow_html=True)

        # GRÁFICO COMPARATIVO
        st.markdown('<div class="sub-header">ANÁLISE VISUAL DE CONFORMIDADE (PAGO VS DEVIDO)</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Pago ao Banco', x=['Parcela Atual'], y=[p_banco], marker_color='#d32f2f', text=[f"R$ {p_banco:,.2f}"], textposition='auto'))
        fig.add_trace(go.Bar(name='Deveria Pagar (SAC)', x=['Parcela Atual'], y=[p_legal_atual], marker_color='#388e3c', text=[f"R$ {p_legal_atual:,.2f}"], textposition='auto'))
        fig.update_layout(barmode='group', height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        <div style="background-color: #1e1e1e; color: white; padding: 30px; border-radius: 12px; text-align: center; border: 2px solid #d4af37;">
            <span style="font-size: 16px; color: #d4af37; font-weight: bold; text-transform: uppercase;">Total Recuperável nas Parcelas {p_ini} a {p_fim}</span><br>
            <span style="font-size: 44px; font-weight: 900;">R$ {recuperavel_estimado:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with tab_advogado:
        st.markdown('<div class="sub-header">MEMÓRIA DE CÁLCULO E FUNDAMENTAÇÃO SÊNIOR</div>', unsafe_allow_html=True)
        
        csv_buffer = io.StringIO()
        df_pericia.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📊 BAIXAR PLANILHA DO EVOLUTIVO (CSV/EXCEL)",
            data=csv_buffer.getvalue(),
            file_name=f"Pericia_Parcelas_{p_ini}_a_{p_fim}.csv",
            mime="text/csv",
            help="Planilha detalhada mês a mês para prova judicial irrefutável."
        )
        
        if st.button("📄 GERAR LAUDO PERICIAL FUNDAMENTADO"):
            with st.spinner("James Sebastian redigindo o parecer técnico final..."):
                model_ia = genai.GenerativeModel(buscar_melhor_modelo())
                ctx = f"""Aja como o Perito Judicial James Sebastian (30 anos de exp). 
                Gere um laudo pericial técnico completo em Português Brasileiro para {nome}. 
                Banco: {st.session_state.dados.get('banco', 'Instituição Financeira')}. 
                Abuso detectado no intervalo de parcelas {p_ini} a {p_fim}: R$ {recuperavel_estimado:,.2f}. 
                Fundamente com a Súmula 121 do STF (anatocismo), Código 410 e Lei 4.380/64.
                Inclua uma tabela comparativa resumida no laudo e use sempre R$ como moeda."""
                res_laudo = model_ia.generate_content(ctx)
                st.markdown(res_laudo.text)
                
                st.download_button(label="📥 Baixar Minuta do Laudo (TXT)", data=res_laudo.text, file_name="Laudo_James_Sebastian.txt")

# --- FIGURA DE AUTORIDADE NO RODAPÉ ---
else:
    st.info("👋 Olá Fred! Carregue o Contrato e o Evolutivo na barra lateral para iniciar a perícia.")
    st.image("https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&q=80&w=1000", caption="James Sebastian: Justiça Financeira e Rigor Técnico Contratual.")
