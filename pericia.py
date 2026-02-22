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

if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = "AIzaSyD068i8Vp9R24wwCjrRITsgTjAXo-I5Q-g"

genai.configure(api_key=GEMINI_API_KEY)

# Estilo Visual Premium (Baseado no modelo Premium Soluções)
st.markdown("""
    <style>
    .main-header { font-size: 26px; font-weight: bold; background-color: #1e1e1e; color: #ffffff; padding: 15px; text-align: center; border-radius: 8px; margin-bottom: 20px; }
    .sub-header { font-size: 18px; font-weight: bold; background-color: #444; color: white; padding: 10px; text-align: center; margin-top: 20px; border-radius: 5px; }
    .status-irregular { color: #ff0000; font-size: 22px; font-weight: bold; text-align: right; }
    .status-regular { color: #28a745; font-size: 22px; font-weight: bold; text-align: right; }
    .highlight-yellow { background-color: #ffff00; padding: 15px; font-weight: bold; font-size: 22px; color: #000; border-radius: 5px; text-align: center; border: 1px solid #ccc; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DE EXTRAÇÃO IA (OCR + ANÁLISE) ---
def extrair_dados_ia(arquivos):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """Atue como perito judicial sênior. Analise os documentos e extraia os dados abaixo para um JSON puro.
        IMPORTANTE: Não invente dados. Se não encontrar, retorne null.
        Campos: {"nome": str, "banco": str, "contrato": str, "valor_financiado": float, "prazo_total": int, "pagas": int, "taxa_juros": float, "parcela_atual": float, "seguro": float, "taxa_adm": float}
        Busque no extrato o Código 410 (Incorporação de Juros)."""
        
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Texto do Documento: {texto[:15000]}")
            else:
                conteudo.append(Image.open(arq))
        
        response = model.generate_content(conteudo)
        # Limpeza do JSON
        txt = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(txt)
    except:
        return None

# --- ÍNDICES EM TEMPO REAL ---
@st.cache_data(ttl=3600)
def obter_indices():
    res = {"data": date.today().strftime("%d/%m/%Y"), "Selic": 0.0, "TR": 0.0}
    try:
        r = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json", timeout=3)
        if r.status_code == 200: res["Selic"] = float(r.json()[0]['valor'])
        tr = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.226/dados/ultimos/1?formato=json", timeout=3)
        if tr.status_code == 200: res["TR"] = float(tr.json()[0]['valor'])
    except: pass
    return res

# --- INTERFACE E ESTADO ---
if 'dados' not in st.session_state:
    st.session_state.dados = {k: "" if isinstance(v, str) else 0.0 for k, v in {
        'nome': "", 'banco': "", 'contrato': "", 'valor_financiado': 0.0, 
        'prazo': 0, 'pagas': 0, 'taxa': 0.0, 'p_atual': 0.0, 'seguro': 0.0, 'taxa_adm': 0.0
    }.items()}

with st.sidebar:
    st.header("📂 1. Carga de Provas")
    docs = st.file_uploader("Suba Contratos/Extratos", accept_multiple_files=True)
    if docs and st.button("🔍 Extrair Dados via IA"):
        with st.spinner("James Sebastian analisando..."):
            res = extrair_dados_ia(docs)
            if res:
                # Preenchimento automático dos campos
                st.session_state.dados['nome'] = res.get('nome', "")
                st.session_state.dados['banco'] = res.get('banco', "")
                st.session_state.dados['contrato'] = res.get('contrato', "")
                st.session_state.dados['valor_financiado'] = float(res.get('valor_financiado') or 0.0)
                st.session_state.dados['prazo'] = int(res.get('prazo_total') or 0)
                st.session_state.dados['pagas'] = int(res.get('pagas') or 0)
                st.session_state.dados['taxa'] = float(res.get('taxa_juros') or 0.0)
                st.session_state.dados['p_atual'] = float(res.get('parcela_atual') or 0.0)
                st.session_state.dados['seguro'] = float(res.get('seguro') or 0.0)
                st.session_state.dados['taxa_adm'] = float(res.get('taxa_adm') or 0.0)
                st.success("Dados preenchidos com sucesso!")
                st.rerun()

    st.divider()
    st.header("📝 2. Ajustes Manuais")
    d = st.session_state.dados
    d['nome'] = st.text_input("Mutuário", d['nome'])
    d['valor_financiado'] = st.number_input("Valor Financiado", value=d['valor_financiado'])
    d['prazo'] = st.number_input("Prazo Total (Meses)", value=int(d['prazo']))
    d['pagas'] = st.number_input("Parcelas Pagas", value=int(d['pagas']))
    d['taxa'] = st.number_input("Taxa Nominal (% a.a.)", value=d['taxa'])
    d['p_atual'] = st.number_input("Valor Parcela Atual", value=d['p_atual'])
    d['seguro'] = st.number_input("Seguro (R$)", value=d['seguro'])
    d['taxa_adm'] = st.number_input("Taxa Administração", value=d['taxa_adm'])

# --- MOTOR DE CÁLCULO SAC (SISTEMA FINANCEIRO DA HABITAÇÃO) ---
ind = obter_indices()
if d['valor_financiado'] > 0 and d['prazo'] > 0:
    # Matemática SAC Pura
    amort_legal = d['valor_financiado'] / d['prazo']
    taxa_mensal = (1 + d['taxa']/100)**(1/12) - 1
    
    # Cálculo do Saldo Devedor Teórico no mês atual para apurar juros
    saldo_apos_pagas = d['valor_financiado'] - (amort_legal * (d['pagas'] - 1))
    juros_legais = max(0, saldo_apos_pagas * taxa_mensal)
    
    # Parcela Correta = Amortização + Juros + Encargos
    p_correta = amort_legal + juros_legais + d['seguro'] + d['taxa_adm']
    
    # Diferenças e Prejuízo
    dif_mensal = d['p_atual'] - p_correta
    prejuizo_total = (dif_mensal * d['pagas']) * 1.25 # Coeficiente estimado de correção e juros
    is_irregular = dif_mensal > 5.0 # Margem técnica

    # --- EXIBIÇÃO ---
    st.markdown('<div class="main-header">ANÁLISE IMOBILIÁRIA SINTETIZADA - PERÍCIA JUDICIAL</div>', unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.write(f"**NOME:** {d['nome']}")
        st.write(f"**BANCO:** {d['banco']}")
        st.write(f"**VALOR FINANCIADO:** R$ {d['valor_financiado']:,.2f}")
    with col_b:
        status_html = '<span class="status-irregular">CONTRATO IRREGULAR</span>' if is_irregular else '<span class="status-regular">CONTRATO REGULAR</span>'
        st.markdown(f"**STATUS:** {status_html}", unsafe_allow_html=True)
        st.write(f"**DATA ATUALIZAÇÃO:** {ind['data']}")
        st.write(f"**INDICADORES:** Selic {ind['Selic']}% | TR {ind['TR']}%")

    st.markdown(f'<div class="highlight-yellow">SALDO DEVEDOR ATUALIZADO: R$ {max(0, d["valor_financiado"] - (amort_legal * d["pagas"])):,.2f}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sub-header">DETALHAMENTO E ANÁLISE DA PARCELA</div>', unsafe_allow_html=True)
    st.write(f"**VALOR DA PARCELA ATUAL DO IMÓVEL: R$ {d['p_atual']:,.2f}**")
    
    # Gráfico de Comparação
    fig = go.Figure()
    fig.add_trace(go.Bar(x=['PARCELA CORRETA', 'PARCELA ATUAL'], y=[p_correta, d['p_atual']], 
                         marker_color=['#28a745', '#ff0000'], text=[f"R$ {p_correta:,.2f}", f"R$ {d['p_atual']:,.2f}"], textposition='auto'))
    fig.update_layout(title="Desvio Financeiro Mensal", height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="sub-header">CONCLUSÃO E VALORES RECUPERÁVEIS</div>', unsafe_allow_html=True)
    ca, cb = st.columns(2)
    ca.metric("Diferença de Amortização (Mês)", f"R$ {amort_legal:,.2f}")
    cb.metric("DIFERENÇA TOTAL RECUPERÁVEL", f"R$ {prejuizo_total:,.2f}", delta=f"R$ {dif_mensal:,.2f} /mês", delta_color="inverse")

    # --- LAUDO PERICIAL COMPLETO ---
    if st.button("📄 GERAR LAUDO PERICIAL TÉCNICO COMPLETO"):
        with st.spinner("O Perito James Sebastian está redigindo a peça técnica fundamentada..."):
            prompt_expert = f"""
            Redija um Laudo Pericial Judicial formal em Markdown para {d['nome']}.
            Dados: Banco {d['banco']}, Contrato {d['contrato']}, {d['pagas']} parcelas pagas.
            Diferença Mensal: R$ {dif_mensal:,.2f}. Total a Recuperar: R$ {prejuizo_total:,.2f}.
            
            ESTRUTURA:
            1. Metodologia: Explique o Sistema SAC e por que a amortização deve ser constante (Lei 4.380/64).
            2. Anatocismo: Cite a Súmula 121 do STF e o Código 410 (Incorporação de Juros) encontrado no extrato.
            3. Tabela Comparativa: Monte uma tabela comparando "Valores Cobrados" vs "Valores Legais".
            4. Jurisprudência: Cite Súmula 121 STF, Súmula 93 STJ e Decreto 22.626/33.
            5. Conclusão: Determine o valor exato a ser expurgado do saldo devedor.
            
            Não invente nada. Seja técnico e preciso.
            """
            model = genai.GenerativeModel('gemini-1.5-flash')
            st.markdown("---")
            st.markdown(model.generate_content(prompt_expert).text)
else:
    st.info("💡 Fred, suba os arquivos de qualquer cliente na barra lateral para o James Sebastian iniciar a perícia.")
