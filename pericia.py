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

# --- CONFIGURAÇÃO E SEGURANÇA (Johnson Mello Edition) ---
st.set_page_config(page_title="James Sebastian AI - Perícia Premium", layout="wide", page_icon="⚖️")

# Recuperação segura da Chave de API
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- DESIGN MODERNO E INTUITIVO (CSS PREMIUM) ---
st.markdown("""
    <style>
    /* Estilo Global */
    .main { background-color: #f8f9fa; }
    
    /* Cabeçalho de Autoridade */
    .main-header { 
        font-size: 34px; font-weight: 800; background-color: #1e1e1e; 
        color: #ffffff; padding: 25px; text-align: center; border-radius: 12px; 
        margin-bottom: 30px; border-bottom: 6px solid #d4af37;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    
    /* Cartões de Indicadores */
    .card-index { 
        background-color: white; padding: 20px; border-radius: 15px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;
        border-top: 5px solid #d4af37; transition: transform 0.3s;
    }
    .card-index:hover { transform: translateY(-5px); }
    .index-label { font-size: 14px; color: #888; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .index-value { font-size: 24px; font-weight: 900; color: #1e1e1e; margin-top: 5px; }
    
    /* Status Dinâmico */
    .status-badge {
        font-size: 20px; font-weight: bold; padding: 10px 25px; border-radius: 50px;
        text-align: center; display: inline-block;
    }
    .status-irregular { color: white; background-color: #e74c3c; border: 2px solid #c0392b; }
    .status-regular { color: white; background-color: #2ecc71; border: 2px solid #27ae60; }
    
    /* Destaques */
    .highlight-yellow { 
        background-color: #ffff00; padding: 20px; font-weight: 800; 
        font-size: 28px; color: #000; border-radius: 12px; text-align: center; 
        border: 2px solid #e6e600; margin: 20px 0;
    }
    
    /* Botões */
    .stButton>button { 
        width: 100%; border-radius: 10px; height: 3.5em; 
        background-color: #1e1e1e; color: white; font-weight: bold; 
        border: 1px solid #d4af37; font-size: 16px;
    }
    .stButton>button:hover { background-color: #d4af37; color: #1e1e1e; border: 1px solid #1e1e1e; }
    
    .sub-header { 
        font-size: 22px; font-weight: bold; background-color: #333; 
        color: white; padding: 12px; text-align: center; border-radius: 8px; margin-top: 25px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE INTELIGÊNCIA E DADOS ---

@st.cache_data(ttl=3600)
def fetch_live_indices():
    """Obtém indicadores econômicos reais de fontes oficiais"""
    hoje = date.today().strftime("%d/%m/%Y")
    data = {"data": hoje, "Selic": 11.25, "TR": 0.081, "IPCA": 4.48, "Dolar": 5.01, "Euro": 5.42}
    try:
        # APIs Banco Central
        endpoints = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for k, v in endpoints.items():
            r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{v}/dados/ultimos/1?formato=json", timeout=3)
            if r.status_code == 200: data[k] = float(r.json()[0]['valor'])
        # Câmbio Comercial
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=3).json()
        data["Dolar"] = float(c["USDBRL"]["bid"])
        data["Euro"] = float(c["EURBRL"]["bid"])
    except: pass
    return data

def process_audit_ia(files):
    """Extração de dados via OCR e Visão Computacional do Gemini 1.5 Flash"""
    if not GEMINI_API_KEY:
        st.error("Erro: API Key não detectada. Configure os Secrets no Streamlit.")
        return None
    try:
        # Correção do erro 404: Chamada padrão do modelo estável
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """Atue como perito judicial bancário James Sebastian. Analise estes documentos e extraia os dados para JSON.
        REGRAS: 1. Apenas JSON puro. 2. Se não houver o dado, use null. 3. NÃO INVENTE.
        JSON: {"nome": str, "banco": str, "num_contrato": str, "valor_financiado": float, "prazo_meses": int, "parcelas_pagas": int, "taxa_juros_aa": float, "valor_prestacao": float, "seguro_valor": float, "taxa_adm_valor": float}"""
        
        content = [prompt]
        for f in files:
            if f.type == "application/pdf":
                with pdfplumber.open(f) as pdf:
                    txt = "\n".join([page.extract_text() or "" for page in pdf.pages])
                    content.append(f"Conteúdo Documento: {txt[:18000]}")
            else:
                content.append(Image.open(f))
        
        response = model.generate_content(content)
        clean_json = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"Falha técnica na análise IA: {e}")
        return None

# --- CONSTRUÇÃO DA INTERFACE ---

# Cabeçalho com Logotipo Estilizado
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.markdown("<h1 style='text-align: center; color: #d4af37; margin-bottom: 0;'>⚖️</h1>", unsafe_allow_html=True)
with col_title:
    st.markdown('<div class="main-header">JAMES SEBASTIAN AI - PERÍCIA JUDICIAL PREMIUM</div>', unsafe_allow_html=True)

idx = fetch_live_indices()

# Painel de Indicadores Econômicos
st.markdown("### 📈 Painel de Indicadores de Mercado")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f"<div class='card-index'><span class='index-label'>Selic Meta</span><br><span class='index-value'>{idx['Selic']}%</span></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='card-index'><span class='index-label'>Taxa TR (M)</span><br><span class='index-value'>{idx['TR']}%</span></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='card-index'><span class='index-label'>IPCA (12m)</span><br><span class='index-value'>{idx['IPCA']}%</span></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='card-index'><span class='index-label'>USD/BRL</span><br><span class='index-value'>R$ {idx['Dolar']:.2f}</span></div>", unsafe_allow_html=True)
with c5: st.markdown(f"<div class='card-index'><span class='index-label'>EUR/BRL</span><br><span class='index-value'>R$ {idx['Euro']:.2f}</span></div>", unsafe_allow_html=True)
st.caption(f"Dados atualizados automaticamente em: {idx['data']}")

# Sidebar: Inteligência de Carga
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
    st.header("📂 1. Auditoria de Arquivos")
    uploaded_files = st.file_uploader("Subir PDFs ou Fotos de Contratos", accept_multiple_files=True, type=['pdf', 'jpg', 'png'])
    
    if uploaded_files and st.button("🔍 Iniciar Auditoria Automática"):
        with st.spinner("O perito está lendo as evidências..."):
            audit_data = process_audit_ia(uploaded_files)
            if audit_data:
                st.session_state.update(audit_data)
                st.success("✅ Auditoria de documentos concluída!")
                st.rerun()

    st.divider()
    st.header("📝 2. Detalhes do Contrato")
    # Campos que se auto-preenchem após o upload
    nome = st.text_input("Nome do Mutuário", st.session_state.get('nome', ""))
    inst_banco = st.text_input("Instituição Financeira", st.session_state.get('banco', ""))
    valor_orig = st.number_input("Valor Financiado (R$)", value=float(st.session_state.get('valor_financiado', 0.0)), step=1000.0)
    prazo_m = st.number_input("Prazo Total (Meses)", value=int(st.session_state.get('prazo_meses', 360)), min_value=1)
    pagas_m = st.number_input("Parcelas Pagas", value=int(st.session_state.get('parcelas_pagas', 0)))
    taxa_aa_contrato = st.number_input("Juros Anual (% a.a.)", value=float(st.session_state.get('taxa_juros_aa', 0.0)), step=0.01)
    p_cobrada = st.number_input("Valor Parcela Atual (R$)", value=float(st.session_state.get('valor_prestacao', 0.0)))
    v_seguro = st.number_input("Custo Seguro (MIP/DFI)", value=float(st.session_state.get('seguro_valor', 0.0)))
    v_taxa_adm = st.number_input("Taxa Administrativa", value=float(st.session_state.get('taxa_adm_valor', 25.0)))

# --- MOTOR FINANCEIRO JAMES SEBASTIAN (ESTABILIDADE SEM SCIPY) ---
if valor_orig > 0 and prazo_m > 0:
    # Lógica SAC: Amortização é fixa e sagrada
    amort_mensal_correta = valor_orig / prazo_m
    
    # Conversão de juros anual para mensal efetiva
    # i_m = (1 + i_a)^(1/12) - 1
    taxa_i_mensal = (1 + taxa_aa_contrato/100)**(1/12) - 1
    
    # Saldo Devedor Teórico no mês da auditoria
    # SD = Valor_F - (Amort_F * (Parcelas_Pagas - 1))
    sd_teorico_mes = max(0, valor_orig - (amort_mensal_correta * (pagas_m - 1)))
    juros_legais_mes = sd_teorico_mes * taxa_i_mensal
    
    # Prestação que deveria ser paga segundo a Lei 4.380/64
    parcela_sac_pura = amort_mensal_correta + juros_legais_mes + v_seguro + v_taxa_adm
    
    # Apuração de Indébitos
    desvio_mensal = p_cobrada - parcela_sac_pura
    prejuizo_acumulado = (desvio_mensal * pagas_m) * 1.22 # Estimativa média de juros e correção sobre indébito
    is_irregular = desvio_mensal > 5.0 # Margem técnica

    # --- RESULTADOS VISUAIS (TABS) ---
    tab_resumo, tab_pericia = st.tabs(["📊 Análise Sintetizada", "⚖️ Parecer Pericial Judicial"])

    with tab_resumo:
        st.markdown('<div class="sub-header">DETALHAMENTO DA ANÁLISE IMOBILIÁRIA</div>', unsafe_allow_html=True)
        
        col_inf1, col_inf2 = st.columns(2)
        with col_inf1:
            st.markdown(f"**MUTUÁRIO:** {nome}")
            st.markdown(f"**BANCO:** {inst_banco}")
            st.markdown(f"**CONTRATO Nº:** {st.session_state.get('num_contrato', 'N/A')}")
        with col_inf2:
            s_class = "status-irregular" if is_irregular else "status-regular"
            s_text = "CONTRATO IRREGULAR" if is_irregular else "CONTRATO REGULAR"
            st.markdown(f"<div style='text-align:right;'><span class='status-badge {s_class}'>{s_text}</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:right;'><b>VALOR FINANCIADO:</b> R$ {valor_orig:,.2f}</div>", unsafe_allow_html=True)

        st.markdown(f'<div class="highlight-yellow">SALDO DEVEDOR ATUALIZADO (TEÓRICO): R$ {max(0, valor_orig - (amort_mensal_correta * pagas_m)):,.2f}</div>', unsafe_allow_html=True)

        st.markdown('<div class="sub-header">ANÁLISE DE CONFORMIDADE DA PARCELA</div>', unsafe_allow_html=True)
        st.write(f"**VALOR DA PARCELA ATUAL DO IMÓVEL: R$ {p_cobrada:,.2f}**")

        # Gráfico Comparativo de Barras Horizontais (Plotly)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=['O QUE O BANCO COBRA', 'O QUE A LEI EXIGE (SAC)'],
            x=[p_cobrada, parcela_sac_pura],
            orientation='h',
            marker_color=['#e74c3c', '#2ecc71'],
            text=[f"R$ {p_cobrada:,.2f}", f"R$ {parcela_sac_pura:,.2f}"],
            textposition='auto',
        ))
        fig.update_layout(title="Ajuste de Parcela", height=320, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # Quadro de Valores Recuperáveis
        st.markdown("---")
        m_a, m_b, m_c = st.columns(3)
        m_a.metric("Amortização Média", f"R$ {amort_mensal_correta:,.2f}")
        m_b.metric("Excesso Mensal", f"R$ {desvio_mensal:,.2f}", delta_color="inverse")
        m_c.metric("Indébito Apurado", f"R$ {prejuizo_acumulado:,.2f}")
        
        st.markdown(f"""
        <div style="background-color: #1e1e1e; color: white; padding: 30px; border-radius: 12px; text-align: center; border: 2px solid #d4af37;">
            <span style="font-size: 18px; color: #d4af37; font-weight: bold;">ESTIMATIVA TOTAL DE RECUPERAÇÃO JUDICIAL</span><br>
            <span style="font-size: 42px; font-weight: 900;">R$ {prejuizo_acumulado:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with tab_pericia:
        st.markdown('<div class="sub-header">CONSOLIDAÇÃO DA FUNDAMENTAÇÃO TÉCNICA</div>', unsafe_allow_html=True)
        
        if st.button("📄 GERAR LAUDO PERICIAL COMPLETO (SÉNIOR)"):
            with st.spinner("James Sebastian está consolidando a jurisprudência..."):
                model_perito = genai.GenerativeModel('gemini-1.5-flash')
                
                contexto = f"""
                Atue como o perito judicial James Sebastian, com 30 anos de experiência.
                Gere um Laudo Pericial completo em Markdown para {nome}.
                BANCO: {inst_banco}, VALOR: R$ {valor_orig:,.2f}, PAGAS: {pagas_m}.
                IRREGULARIDADE: Diferença abusiva de R$ {desvio_mensal:,.2f} por mês.
                
                ESTRUTURA OBRIGATÓRIA:
                1. IDENTIFICAÇÃO: Objeto e partes.
                2. METODOLOGIA: O sistema SAC e a Lei 4.380/64.
                3. DEMONSTRATIVO: Tabela comparando Pago vs Devido.
                4. ANÁLISE DE ANATOCISMO: Explique o Código 410 e a amortização negativa.
                5. JURISPRUDÊNCIA: Cite Súmula 121 STF, Súmula 93 STJ e Art. 4º Decreto 22.626/33.
                6. CONCLUSÃO: Valor final do indébito e recomendação técnica de expurgo e recálculo.
                """
                
                resultado_laudo = model_perito.generate_content(contexto)
                st.markdown(resultado_laudo.text)
                
                st.download_button(
                    label="📥 Baixar Minuta do Laudo (TXT)",
                    data=resultado_laudo.text,
                    file_name=f"Laudo_James_Sebastian_{nome.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

else:
    # Mensagem Inicial Elegante
    st.info("👋 Bem-vindo Fred. O sistema de auditoria premium James Sebastian está pronto para operar.")
    st.markdown("""
    ### Instruções de Operação:
    1.  **Submeter Provas:** Utilize o campo lateral para carregar contratos ou extratos.
    2.  **Processamento IA:** Clique em "Iniciar Auditoria Automática" para preencher os dados.
    3.  **Análise Humana:** Revise os campos e clique em "Gerar Laudo" para fundamentação jurídica.
    """)
    st.image("https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&q=80&w=1000", caption="James Sebastian: Rigor Técnico, Ética Contratual e Justiça Financeira.")
