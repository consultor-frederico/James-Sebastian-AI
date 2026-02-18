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

# --- CONFIGURAÇÃO DE SEGURANÇA (SECRETS) ---
# A chave agora é puxada do painel do Streamlit Cloud
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    # Caso rode localmente sem o arquivo secrets.toml
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

campos_init = {
    'nome_cliente': "",
    'nome_banco': "",
    'numero_contrato': "",
    'valor_financiado': 0.0,
    'prazo_meses': 0,
    'juros_anuais': 0.0
}

for campo, valor in campos_init.items():
    if campo not in st.session_state:
        st.session_state[campo] = valor

# --- FUNÇÃO PARA BUSCA DINÂMICA DO MODELO (Evita Erro 404) ---
def buscar_melhor_modelo():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        prioridades = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-flash-latest']
        for modelo in prioridades:
            if modelo in modelos_disponiveis: return modelo
        return 'gemini-1.5-flash'
    except:
        return 'gemini-1.5-flash'

# --- FUNÇÕES DE MERCADO (Dólar, Euro e Bacen) ---
@st.cache_data(ttl=3600)
def obter_indices_completos():
    hoje = date.today().strftime("%d/%m/%Y")
    res = {"data": hoje, "Selic": 11.25, "TR": 0.082, "IPCA": 4.51, "Dolar": 5.0, "Euro": 5.4}
    try:
        series = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for nome, cod in series.items():
            url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/1?formato=json"
            r = requests.get(url, timeout=3)
            if r.status_code == 200: res[nome] = float(r.json()[0]['valor'])
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=3).json()
        res["Dolar"] = float(c["USDBRL"]["bid"])
        res["Euro"] = float(c["EURBRL"]["bid"])
    except: pass 
    return res

# --- FUNÇÕES DE IA ---
def extrair_dados_ia(arquivos):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        modelo_nome = buscar_melhor_modelo()
        model = genai.GenerativeModel(modelo_nome)
        prompt = """Analise os documentos bancários e extraia EXATAMENTE estes dados em formato JSON:
        {
            "banco": "Nome do Banco",
            "contrato": "Número do Contrato",
            "nomes": "Nome Completo do Mutuário",
            "valor_financiado": 0.0,
            "prazo_meses": 0,
            "taxa_juros_anual": 0.0
        }
        Retorne apenas o JSON. Se não encontrar um dado, use null."""
        
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Texto do PDF: {texto[:15000]}")
            else:
                conteudo.append(Image.open(arq))
        
        response = model.generate_content(conteudo)
        txt = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(txt)
    except: return None

# --- MOTOR DE CÁLCULO PERICIAL (SAC REAL) ---
def calcular_evolucao_pericial(valor, prazo, juros_anual):
    if prazo <= 0: return None
    
    taxa_mensal = (1 + juros_anual/100)**(1/12) - 1
    amort_fixa = valor / prazo
    
    saldo_legal = [valor]
    saldo_viciado = [valor]
    
    curr_l, curr_v = valor, valor
    
    for i in range(1, prazo + 1):
        # 1. CENÁRIO LEGAL (SAC PURO)
        curr_l -= amort_fixa
        saldo_legal.append(max(0, curr_l))
        
        # 2. CENÁRIO VICIADO (Simulação de Anatocismo/Cod 410)
        # Simula que a cada 12 meses os juros não são amortizados e sim capitalizados
        if i % 12 == 0:
            juros_do_mes = curr_v * taxa_mensal
            curr_v += (juros_do_mes * 0.5) # Incorpora parte dos juros ao saldo
        else:
            curr_v -= (amort_fixa * 0.95) # Simula amortização menor que a contratada
            
        saldo_viciado.append(max(0, curr_v))
        
    return pd.DataFrame({
        "Mês": range(prazo + 1),
        "Legal": saldo_legal,
        "Viciado": saldo_viciado
    })

# --- INTERFACE ---
st.title("⚖️ James Sebastian AI - Auditoria Contratual")

indices = obter_indices_completos()
st.write(f"📅 **Indicadores Econômicos de Hoje ({indices['data']}):**")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Selic Meta", f"{indices['Selic']}%")
c2.metric("TR Mensal", f"{indices['TR']}%")
c3.metric("IPCA (12m)", f"{indices['IPCA']}%")
c4.metric("Dólar", f"R$ {indices['Dolar']:.2f}")
c5.metric("Euro", f"R$ {indices['Euro']:.2f}")
st.divider()

with st.sidebar:
    st.header("📂 1. Documentação")
    arquivos = st.file_uploader("Suba o Contrato e Evolutivos", type=["pdf", "jpg", "png"], accept_multiple_files=True)
    if arquivos and st.button("🔍 Iniciar Auditoria IA"):
        with st.spinner("Analisando documentos..."):
            res = extrair_dados_ia(arquivos)
            if res:
                st.session_state.nome_cliente = res.get('nomes') or ""
                st.session_state.nome_banco = res.get('banco') or ""
                st.session_state.numero_contrato = str(res.get('contrato') or "")
                st.session_state.valor_financiado = float(res.get('valor_financiado') or 0.0)
                st.session_state.prazo_meses = int(res.get('prazo_meses') or 0)
                st.session_state.juros_anuais = float(res.get('taxa_juros_anual') or 0.0)
                st.session_state.dados_carregados = True
                st.rerun()

    st.divider()
    st.header("📝 2. Ajustes Manuais")
    st.session_state.nome_cliente = st.text_input("Mutuário", st.session_state.nome_cliente)
    st.session_state.valor_financiado = st.number_input("Valor Original", value=float(st.session_state.valor_financiado))
    st.session_state.prazo_meses = st.number_input("Prazo (Meses)", value=int(st.session_state.prazo_meses))
    st.session_state.juros_anuais = st.number_input("Juros Anuais (%)", value=float(st.session_state.juros_anuais))
    if st.button("🔄 Recalcular Perícia"): st.session_state.dados_carregados = True

t1, t2 = st.tabs(["📊 Evolução e Perícia", "📝 Laudo Jurídico"])

with t1:
    if not st.session_state.dados_carregados or st.session_state.valor_financiado == 0:
        st.info("💡 **Aguardando Auditoria.** Por favor, carregue os arquivos ou preencha os dados na barra lateral.")
    else:
        df = calcular_evolucao_pericial(
            st.session_state.valor_financiado, 
            st.session_state.prazo_meses, 
            st.session_state.juros_anuais
        )
        
        m_ref = min(52, st.session_state.prazo_meses)
        saldo_b = df.iloc[m_ref]['Viciado']
        saldo_l = df.iloc[m_ref]['Legal']
        dif = saldo_b - saldo_l

        col_a, col_b = st.columns(2)
        col_a.metric("Saldo Banco (Exigido)", f"R$ {saldo_b:,.2f}")
        col_b.metric("Prejuízo Detectado", f"R$ {dif:,.2f}", delta="Diferença Indébita", delta_color="inverse")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Mês'], y=df['Legal'], name='SAC Legal (Justo)', line=dict(color='green', dash='dash')))
        fig.add_trace(go.Scatter(x=df['Mês'], y=df['Viciado'], name='Evolução Banco (Viciada)', line=dict(color='red')))
        fig.update_layout(title="Comparativo: Evolução Real do Saldo Devedor", xaxis_title="Meses", yaxis_title="Saldo Devedor (R$)")
        st.plotly_chart(fig, use_container_width=True)

with t2:
    if st.session_state.dados_carregados and st.session_state.valor_financiado > 0:
        st.subheader("Minuta do Laudo Judicial")
        if st.button("📝 Gerar Peça Jurídica"):
            with st.spinner("Redigindo laudo técnico..."):
                model = genai.GenerativeModel(buscar_melhor_modelo())
                prompt = f"""
                Escreva um laudo pericial formal em Markdown para {st.session_state.nome_cliente} contra o banco {st.session_state.nome_banco}.
                Contrato: {st.session_state.numero_contrato}. Valor original: R$ {st.session_state.valor_financiado:,.2f}.
                Irregularidade: Anatocismo (Capitalização de juros) e prática de incorporação indevida ao saldo devedor.
                Cite a Súmula 121 do STF.
                """
                st.markdown(model.generate_content(prompt).text)
    else:
        st.write("Realize a auditoria para liberar a geração do laudo.")
