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

# --- CONFIGURAÇÃO E SEGURANÇA ---
st.set_page_config(page_title="James Sebastian AI - Perícia Premium", layout="wide")

# Tenta obter a chave da API dos Secrets ou usa uma string vazia para fallback
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- ESTILO CSS PERSONALIZADO (LOOK PREMIUM) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #1e1e1e; color: white; font-weight: bold; border: 1px solid #d4af37; }
    .stButton>button:hover { background-color: #d4af37; color: #1e1e1e; }
    .main-header { font-size: 32px; font-weight: bold; background-color: #1e1e1e; color: #ffffff; padding: 20px; text-align: center; border-radius: 8px; margin-bottom: 25px; border-bottom: 5px solid #d4af37; }
    .sub-header { font-size: 20px; font-weight: bold; background-color: #333; color: white; padding: 10px; text-align: center; margin-top: 20px; border-radius: 5px; }
    .status-irregular { color: #ff0000; font-size: 24px; font-weight: bold; text-align: right; border: 2px solid #ff0000; padding: 5px 15px; border-radius: 5px; display: inline-block; }
    .status-regular { color: #28a745; font-size: 24px; font-weight: bold; text-align: right; border: 2px solid #28a745; padding: 5px 15px; border-radius: 5px; display: inline-block; }
    .highlight-yellow { background-color: #ffff00; padding: 15px; font-weight: bold; font-size: 24px; color: #000; border-radius: 5px; text-align: center; border: 1px solid #ccc; margin: 10px 0; }
    .card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; border-top: 4px solid #d4af37; }
    .index-label { font-size: 14px; color: #666; font-weight: bold; text-transform: uppercase; }
    .index-value { font-size: 20px; font-weight: bold; color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE APOIO ---

@st.cache_data(ttl=3600)
def obter_indices_atualizados():
    """Busca índices económicos reais via API do Banco Central e AwesomeAPI"""
    hoje = date.today().strftime("%d/%m/%Y")
    res = {"data": hoje, "Selic": 11.25, "TR": 0.082, "IPCA": 4.44, "Dolar": 5.00, "Euro": 5.40}
    try:
        # Selic (432), TR (226), IPCA (13522)
        series = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for nome, cod in series.items():
            r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/1?formato=json", timeout=3)
            if r.status_code == 200:
                res[nome] = float(r.json()[0]['valor'])
        # Câmbio
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=3).json()
        res["Dolar"] = float(c["USDBRL"]["bid"])
        res["Euro"] = float(c["EURBRL"]["bid"])
    except:
        pass
    return res

def extrair_dados_ia(arquivos):
    """Lê PDFs/Imagens e extraia dados estruturados via Gemini"""
    if not GEMINI_API_KEY:
        st.error("Chave API Gemini não configurada nos Secrets.")
        return None
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """Atue como um perito judicial sénior. Analise estes documentos bancários e extraia os dados para um JSON.
        REGRAS: 
        1. Se o dado não estiver presente, use null. NÃO INVENTE VALORES.
        2. Extraia: nome_mutuario, banco, num_contrato, valor_financiado, prazo_total, parcelas_pagas, taxa_juros_anual, valor_ultima_parcela, valor_seguro, taxa_adm.
        3. Procure especificamente por indícios de incorporação de juros ao saldo (Anatocismo).
        Retorne apenas o JSON puro, sem formatação markdown."""
        
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Texto do documento: {texto[:18000]}")
            else:
                conteudo.append(Image.open(arq))
        
        response = model.generate_content(conteudo)
        txt_limpo = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(txt_limpo)
    except Exception as e:
        st.error(f"Erro na extração IA: {e}")
        return None

# --- INTERFACE PRINCIPAL ---

# Logotipo e Título
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.markdown("<div style='font-size: 70px; text-align: center; color: #d4af37;'>⚖️</div>", unsafe_allow_html=True)
with col_title:
    st.markdown('<div class="main-header">JAMES SEBASTIAN AI - PERÍCIA JUDICIAL PREMIUM</div>', unsafe_allow_html=True)

indices = obter_indices_atualizados()

# Quadro de Índices Atualizados
st.markdown("### 📈 Indicadores Económicos em Tempo Real")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f"<div class='card'><span class='index-label'>Selic</span><br><span class='index-value'>{indices['Selic']}%</span></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='card'><span class='index-label'>TR (Mensal)</span><br><span class='index-value'>{indices['TR']}%</span></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='card'><span class='index-label'>IPCA (12m)</span><br><span class='index-value'>{indices['IPCA']}%</span></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='card'><span class='index-label'>Dólar</span><br><span class='index-value'>R$ {indices['Dolar']:.2f}</span></div>", unsafe_allow_html=True)
with c5: st.markdown(f"<div class='card'><span class='index-label'>Euro</span><br><span class='index-value'>R$ {indices['Euro']:.2f}</span></div>", unsafe_allow_html=True)
st.caption(f"Última atualização: {indices['data']}")

# Sidebar para Documentos e Inputs
with st.sidebar:
    st.markdown("<div style='text-align: center;'><img src='https://cdn-icons-png.flaticon.com/512/3135/3135715.png' width='80'></div>", unsafe_allow_html=True)
    st.header("📂 Auditoria de Documentos")
    uploaded_files = st.file_uploader("Submeter Contratos/Evolutivos", accept_multiple_files=True, type=['pdf', 'jpg', 'png'])
    
    if uploaded_files and st.button("🔍 Iniciar Leitura Inteligente"):
        with st.spinner("O perito está a analisar as provas..."):
            res_ia = extrair_dados_ia(uploaded_files)
            if res_ia:
                st.session_state.update(res_ia)
                st.success("Dados carregados com sucesso!")
                st.rerun()

    st.divider()
    st.header("📝 Parâmetros do Contrato")
    nome = st.text_input("Mutuário", st.session_state.get('nome_mutuario', ""))
    banco = st.text_input("Instituição Bancária", st.session_state.get('banco', ""))
    v_financiado = st.number_input("Valor Financiado (R$)", value=float(st.session_state.get('valor_financiado') or 0.0), step=1000.0)
    prazo = st.number_input("Prazo Contratado (Meses)", value=int(st.session_state.get('prazo_total') or 360), min_value=1)
    pagas = st.number_input("Parcelas Pagas", value=int(st.session_state.get('parcelas_pagas') or 0))
    taxa_anual = st.number_input("Taxa Nominal (% a.a.)", value=float(st.session_state.get('taxa_juros_anual') or 0.0), step=0.01)
    p_atual = st.number_input("Valor da Prestação Atual (R$)", value=float(st.session_state.get('valor_ultima_parcela') or 0.0))
    seguro = st.number_input("Seguro MIP/DFI (R$)", value=float(st.session_state.get('valor_seguro') or 0.0))
    taxa_adm = st.number_input("Taxa de Administração (R$)", value=float(st.session_state.get('taxa_adm') or 25.0))

# --- CÁLCULOS PERICIAIS (SISTEMA SAC) ---
if v_financiado > 0 and prazo > 0:
    # Matemática SAC: Amortização constante
    amort_mensal = v_financiado / prazo
    taxa_mensal = (1 + taxa_anual/100)**(1/12) - 1
    
    # Cálculo do Saldo Devedor Teórico (Saldo anterior à parcela atual)
    saldo_anterior = v_financiado - (amort_mensal * (pagas - 1))
    juros_legais = max(0, saldo_anterior * taxa_mensal)
    
    # Valor da Prestação Correta (SAC)
    p_deveria = amort_mensal + juros_legais + seguro + taxa_adm
    
    # Diferenças Apuradas
    dif_mensal = p_atual - p_deveria
    prejuizo_total = dif_mensal * pagas
    is_irregular = dif_mensal > 5.0 # Margem de tolerância técnica

    # --- TABS DE RESULTADOS ---
    tab1, tab2 = st.tabs(["📊 Quadro Resumo", "⚖️ Minuta do Laudo Pericial"])

    with tab1:
        st.markdown('<div class="sub-header">ANÁLISE IMOBILIÁRIA SINTETIZADA</div>', unsafe_allow_html=True)
        
        c_res1, c_res2 = st.columns(2)
        with c_res1:
            st.markdown(f"**MUTUÁRIO:** {nome}")
            st.markdown(f"**BANCO:** {banco}")
            st.markdown(f"**MONTANTE FINANCIADO:** R$ {v_financiado:,.2f}")
        with c_res2:
            status_class = "status-irregular" if is_irregular else "status-regular"
            status_text = "CONTRATO IRREGULAR" if is_irregular else "CONTRATO REGULAR"
            st.markdown(f"<div style='text-align:right;'><span class='{status_class}'>{status_text}</span></div>", unsafe_allow_html=True)
            st.markdown(f"**DATA DA PERÍCIA:** {date.today().strftime('%d/%m/%Y')}")

        st.markdown(f'<div class="highlight-yellow">SALDO DEVEDOR TEÓRICO: R$ {max(0, v_financiado - (amort_mensal * pagas)):,.2f}</div>', unsafe_allow_html=True)

        st.markdown('<div class="sub-header">COMPARATIVO DE PRESTAÇÃO</div>', unsafe_allow_html=True)
        
        # Gráfico Plotly Comparativo Horizontal
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=['Prestação Atual (Banco)', 'Prestação Correta (SAC)'],
            x=[p_atual, p_deveria],
            orientation='h',
            marker_color=['#ff0000', '#28a745'],
            text=[f"R$ {p_atual:,.2f}", f"R$ {p_deveria:,.2f}"],
            textposition='auto',
        ))
        fig.update_layout(title="Ajuste de Parcela (Pago vs. Devido)", height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        col_met1, col_met2, col_met3 = st.columns(3)
        col_met1.metric("Amortização Teórica", f"R$ {amort_mensal:,.2f}")
        col_met2.metric("Diferença Mensal", f"R$ {dif_mensal:,.2f}", delta_color="inverse")
        col_met3.metric("Recuperável Estimado", f"R$ {prejuizo_total:,.2f}")
        
        st.markdown(f"""
        <div style="background-color: #1e1e1e; color: white; padding: 25px; border-radius: 8px; text-align: center; border: 2px solid #d4af37;">
            <span style="font-size: 18px; color: #d4af37;">TOTAL RECUPERÁVEL (SEM CORREÇÃO MONETÁRIA)</span><br>
            <span style="font-size: 38px; font-weight: bold;">R$ {prejuizo_total:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="sub-header">CONSOLIDAÇÃO DO PARECER TÉCNICO</div>', unsafe_allow_html=True)
        
        if st.button("📄 Gerar Laudo Pericial Fundamentado"):
            with st.spinner("James Sebastian está a redigir a peça técnica..."):
                model_pericia = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt_laudo = f"""
                Aja como o perito judicial James Sebastian, com 30 anos de experiência.
                Escreva um Laudo Pericial completo em Markdown para o cliente {nome}.
                CONTEXTO: Banco {banco}, Financiamento de R$ {v_financiado:,.2f}, {pagas} parcelas pagas.
                RESULTADO: Diferença de R$ {dif_mensal:,.2f} por parcela.
                
                O LAUDO DEVE CONTER:
                1. Introdução: Objeto da perícia.
                2. Metodologia: Explicação do Sistema SAC e amortização constante (Lei 4.380/64).
                3. Quadro de Confronto: Tabela comparando valores cobrados vs valores devidos.
                4. Análise de Anatocismo: Explicação técnica sobre a incorporação de juros ao saldo (Código 410).
                5. Jurisprudência: Citar Súmula 121 STF e Súmula 93 STJ.
                6. Conclusão Final com o valor total do indébito.
                """
                
                laudo_result = model_pericia.generate_content(prompt_laudo)
                st.markdown(laudo_result.text)
                
                st.download_button(
                    label="📥 Baixar Minuta do Laudo (TXT)",
                    data=laudo_result.text,
                    file_name=f"Laudo_Pericial_{nome.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

else:
    st.info("👋 Olá Fred! O sistema James Sebastian está pronto. Submeta os documentos na barra lateral para iniciar a auditoria.")
    st.image("https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&q=80&w=1000", caption="James Sebastian: Rigor Técnico e Justiça Financeira.")
