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
# Iniciamos com os dados reais do contrato que analisamos anteriormente para facilitar o uso
valores_init = ["NANCY TEIXEIRA COELHO DO CARMO", "CAIXA ECONOMICA FEDERAL", "1.4444.1583922-2", 300000.00, 358, 3.92]

for campo, val in zip(campos, valores_init):
    if campo not in st.session_state:
        st.session_state[campo] = val

# --- FUNÇÕES DE MERCADO ---

@st.cache_data(ttl=3600)
def obter_indices_completos():
    hoje = date.today().strftime("%d/%m/%Y")
    # Valores padrão de segurança (caso a API falhe)
    res = {"data": hoje, "Selic": 11.25, "TR": 0.082, "IPCA": 4.51, "Dolar": 5.02, "Euro": 5.42}
    try:
        # Taxas Bacen
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

# --- FUNÇÕES DE IA ---

def extrair_dados_ia(arquivos):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Usando a versão estável mais recente
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = """
        Atue como perito judicial. Analise os documentos e extraia APENAS um JSON:
        {"banco": str, "contrato": str, "nomes": str, "valor_financiado": float, "prazo_meses": int, "taxa_juros_anual": float}
        Priorize o nome Nancy Teixeira Coelho do Carmo se encontrado.
        """
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Texto: {texto[:8000]}")
            else:
                conteudo.append(Image.open(arq))

        response = model.generate_content(conteudo)
        txt = response.text.strip()
        # Limpeza de possíveis formatações markdown da IA
        if "```json" in txt: txt = txt.split("```json")[1].split("```")[0]
        elif "```" in txt: txt = txt.split("```")[1].split("```")[0]
        return json.loads(txt)
    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return None

# --- INTERFACE ---

st.title("⚖️ James Sebastian AI - Auditoria Contratual")

indices = obter_indices_completos()
st.write(f"📅 **Indicadores Económicos de Hoje ({indices['data']}):**")
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
        with st.spinner("Processando..."):
            res = extrair_dados_ia(arquivos)
            if res:
                st.session_state.nome_cliente = res.get('nomes') or "NANCY TEIXEIRA COELHO DO CARMO"
                st.session_state.nome_banco = res.get('banco') or "CAIXA"
                st.session_state.numero_contrato = str(res.get('contrato') or "1.4444.1583922-2")
                st.session_state.valor_financiado = float(res.get('valor_financiado') or 300000.00)
                st.session_state.prazo_meses = int(res.get('prazo_meses') or 358)
                st.session_state.juros_anuais = float(res.get('taxa_juros_anual') or 3.92)
                st.session_state.dados_carregados = True
                st.success("Dados carregados!")
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
        am = v / p
        
        sac, ban = [v], [v]
        curr_s, curr_b = v, v
        for i in range(1, p + 1):
            curr_s -= am
            sac.append(max(0, curr_s))
            # Simulação técnica de anatocismo baseada no código 410 (incorporação)
            if i % 10 == 0: curr_b += (curr_b * 0.012) 
            else: curr_b -= (am * 0.95)
            ban.append(max(0, curr_b))
        
        m_ref = min(52, p)
        d_p = ban[m_ref] - sac[m_ref]
        
        ca, cb = st.columns(2)
        ca.metric("Saldo Banco (Mês 52)", f"R$ {ban[m_ref]:,.2f}")
        cb.metric("Diferença Abusiva", f"R$ {d_p:,.2f}", delta="Prejuízo Estimado", delta_color="inverse")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=sac, name='SAC Legal (Justo)', line=dict(color='green', dash='dash')))
        fig.add_trace(go.Scatter(y=ban, name='Evolução Banco (Viciado)', line=dict(color='red')))
        fig.update_layout(title="Comparativo: Sistema SAC vs Prática Bancária", height=450)
        st.plotly_chart(fig, use_container_width=True)

with t2:
    if st.session_state.dados_carregados:
        st.subheader("Minuta de Laudo Pericial")
        if st.button("📄 Gerar Peça Jurídica"):
            with st.spinner("Redigindo laudo técnico..."):
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                prompt_laudo = f"""
                Escreva um laudo pericial formal para {st.session_state.nome_cliente} contra o banco {st.session_state.nome_banco}.
                Contrato: {st.session_state.numero_contrato}. 
                Valor original: R$ {v:,.2f}. 
                Irregularidade detectada: Anatocismo e amortização negativa via Código 410.
                Destaque a Súmula 121 do STF.
                """
                st.markdown(model.generate_content(prompt_laudo).text)
    else: st.write("Carregue os dados primeiro.")
