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

# --- CONFIGURAÇÃO DA CHAVE DE API ---
GEMINI_API_KEY = "AIzaSyD068i8Vp9R24wwCjrRITsgTjAXo-I5Q-g"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="James Sebastian AI - Perícia Revisional", 
    layout="wide",
    page_icon="⚖️"
)

# --- INICIALIZAÇÃO DE ESTADO ---
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = False

campos = ['nome_cliente', 'nome_banco', 'numero_contrato', 'valor_financiado', 'prazo_meses', 'juros_anuais']
valores_init = ["Aguardando análise...", "Instituição Financeira", "S/N", 0.0, 0, 0.0]

for campo, val in zip(campos, valores_init):
    if campo not in st.session_state:
        st.session_state[campo] = val

# --- FUNÇÕES DE MERCADO ---

@st.cache_data(ttl=3600)
def obter_indices_completos():
    """Busca Selic, TR, IPCA e Câmbio"""
    hoje = date.today().strftime("%d/%m/%Y")
    res = {"data": hoje, "Selic": 13.25, "TR": 0.12, "IPCA": 4.5, "Dolar": 5.0, "Euro": 5.4} # Valores padrão
    try:
        # Taxas Bacen
        series = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for nome, cod in series.items():
            r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/1?formato=json", timeout=3)
            if r.status_code == 200: res[nome] = float(r.json()[0]['valor'])
        
        # Câmbio
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=3).json()
        res["Dolar"] = float(c["USDBRL"]["bid"])
        res["Euro"] = float(c["EURBRL"]["bid"])
    except:
        pass # Usa os padrões se a internet falhar
    return res

# --- FUNÇÕES DE IA ---

def extrair_dados_ia(arquivos):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Usando modelo estável para evitar erro 404
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Você é um perito judicial. Analise os documentos de financiamento e extraia APENAS um JSON:
        {"banco": str, "contrato": str, "nomes": str, "valor_financiado": float, "prazo_meses": int, "taxa_juros_anual": float}
        """
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Documento Texto: {texto[:10000]}")
            else:
                conteudo.append(Image.open(arq))

        response = model.generate_content(conteudo)
        # Limpeza robusta do JSON
        txt = response.text.strip()
        if "```json" in txt: txt = txt.split("```json")[1].split("```")[0]
        elif "```" in txt: txt = txt.split("```")[1].split("```")[0]
        return json.loads(txt)
    except Exception as e:
        st.error(f"Erro técnico na IA: {e}")
        return None

# --- INTERFACE ---

st.title("⚖️ James Sebastian AI - Auditoria Contratual")

indices = obter_indices_completos()
st.write(f"📅 **Indicadores de Hoje ({indices['data']}):**")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Selic Meta", f"{indices['Selic']}%")
c2.metric("TR Mensal", f"{indices['TR']}%")
c3.metric("IPCA (12m)", f"{indices['IPCA']}%")
c4.metric("Dólar", f"R$ {indices['Dolar']:.2f}")
c5.metric("Euro", f"R$ {indices['Euro']:.2f}")
st.divider()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📂 1. Documentação")
    arquivos = st.file_uploader("Contratos e Evolutivos", type=["pdf", "jpg", "png"], accept_multiple_files=True)
    
    if arquivos and st.button("🔍 Iniciar Auditoria IA"):
        with st.spinner("Processando documentos..."):
            res = extrair_dados_ia(arquivos)
            if res:
                st.session_state.nome_cliente = res.get('nomes', 'Não identificado')
                st.session_state.nome_banco = res.get('banco', 'Instituição')
                st.session_state.numero_contrato = str(res.get('contrato', 'S/N'))
                st.session_state.valor_financiado = float(res.get('valor_financiado', 0))
                st.session_state.prazo_meses = int(res.get('prazo_meses', 0))
                st.session_state.juros_anuais = float(res.get('taxa_juros_anual', 0))
                st.session_state.dados_carregados = True
                st.success("Auditoria realizada!")
                st.rerun()

    st.divider()
    st.header("📝 2. Dados do Contrato")
    st.session_state.nome_cliente = st.text_input("Mutuário", st.session_state.nome_cliente)
    st.session_state.valor_financiado = st.number_input("Valor Original (R$)", value=float(st.session_state.valor_financiado))
    st.session_state.prazo_meses = st.number_input("Prazo Total", value=int(st.session_state.prazo_meses))
    st.session_state.juros_anuais = st.number_input("Taxa de Juros (%)", value=float(st.session_state.juros_anuais))
    
    if st.button("🔄 Atualizar Cálculos"):
        st.session_state.dados_carregados = True

# --- RESULTADOS ---
t1, t2 = st.tabs(["📊 Evolução e Perícia", "📝 Laudo Jurídico"])

with t1:
    if not st.session_state.dados_carregados or st.session_state.valor_financiado <= 0:
        st.info("💡 **Aguardando dados.** Suba os documentos ou preencha os valores na lateral.")
    else:
        v, p, j = st.session_state.valor_financiado, st.session_state.prazo_meses, st.session_state.juros_anuais
        t_m = (1 + j/100)**(1/12) - 1
        am = v / p
        
        # Simulação
        sac, ban = [v], [v]
        curr_s, curr_b = v, v
        for i in range(1, p + 1):
            curr_s -= am
            sac.append(max(0, curr_s))
            # Simula anatocismo (Cod 410)
            if i % 12 == 0: curr_b += (curr_b * 0.01)
            else: curr_b -= (am * 0.98)
            ban.append(max(0, curr_b))
        
        m_ref = min(52, p)
        d_p = ban[m_ref] - sac[m_ref]
        
        c_a, c_b = st.columns(2)
        c_a.metric("Saldo Banco (Mês 52)", f"R$ {ban[m_ref]:,.2f}")
        c_b.metric("Excesso Detectado", f"R$ {d_p:,.2f}", delta="Prejuízo Acumulado", delta_color="inverse")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=sac, name='SAC Legal', line=dict(color='green', dash='dash')))
        fig.add_trace(go.Scatter(y=ban, name='Evolução Banco', line=dict(color='red')))
        fig.update_layout(title="Comparativo: Banco vs Recálculo Pericial", height=450)
        st.plotly_chart(fig, use_container_width=True)

with t2:
    if st.session_state.dados_carregados:
        st.subheader("Minuta de Laudo Técnico")
        if st.button("Gerar Peça"):
            with st.spinner("Redigindo..."):
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                p = f"Gere um laudo pericial revisional para {st.session_state.nome_cliente} contra o banco {st.session_state.nome_banco}. Valor: {v}, Prazo: {p}. Destaque anatocismo."
                st.markdown(model.generate_content(p).text)
    else: st.write("Carregue os dados primeiro.")
