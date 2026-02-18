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

# --- INICIALIZAÇÃO DE ESTADO (SESSION STATE) ---
campos_padrao = {
    'valor_financiado': 305000.00,
    'prazo_meses': 360,
    'juros_anuais': 10.5,
    'nome_cliente': "Não Identificado",
    'numero_contrato': "S/N",
    'nome_banco': "Instituição Financeira"
}

for campo, valor in campos_padrao.items():
    if campo not in st.session_state:
        st.session_state[campo] = valor

# --- FUNÇÕES AUXILIARES ---

@st.cache_data(ttl=3600)
def obter_indices_bacen():
    """Busca indicadores do Bacen"""
    try:
        apis = {
            "Selic": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json",
            "TR": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.226/dados/ultimos/1?formato=json",
            "IPCA": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.13522/dados/ultimos/1?formato=json" 
        }
        resultados = {}
        for nome, url in apis.items():
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                d = r.json()[0]
                resultados[nome] = (float(d['valor']), d['data'])
            else:
                resultados[nome] = (0.0, "-")
        return resultados
    except:
        return None

def extrair_dados_ia(conteudo, tipo_arquivo):
    """Extrai dados via Gemini (Texto ou Imagem)"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt_texto = """
        Atue como um especialista em extração de dados bancários. Analise este documento e retorne um JSON estrito.
        Extraia:
        1. "banco": (Nome do Banco/Instituição)
        2. "contrato": (Número do contrato)
        3. "nomes": (Nome do mutuário/devedor principal)
        4. "valor_financiado": (float, valor da dívida/compra e venda)
        5. "prazo_meses": (int, total de parcelas)
        6. "taxa_juros_anual": (float, taxa nominal anual - procure por 'Nominal' ou 'Efetiva')

        Se não achar algo, coloque null ou 0. Retorne APENAS o JSON.
        """

        if tipo_arquivo == 'imagem':
            response = model.generate_content([prompt_texto, conteudo])
        else:
            response = model.generate_content(prompt_texto + f"\n\nTexto do Documento:\n{conteudo[:20000]}")

        json_str = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)

    except Exception as e:
        st.error(f"Erro na análise IA: {e}")
        return None

def ler_pdf(file):
    texto = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() or ""
    return texto

def gerar_laudo_final(dados):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Escreva um LAUDO TÉCNICO PERICIAL (Revisional Bancária).
        Use formatação Markdown profissional.

        QUALIFICAÇÃO:
        - Mutuário: {dados['nome_cliente']}
        - Banco: {dados['nome_banco']}
        - Contrato nº: {dados['numero_contrato']}
        
        DADOS TÉCNICOS:
        - Valor: R$ {dados['valor_financiado']}
        - Prazo: {dados['prazo_meses']} meses
        - Taxa Contratual: {dados['juros_anuais']}% a.a.
        
        ACHADOS (IRREGULARIDADES):
        - Prática identificada: Anatocismo via "Incorporação de Juros" (Cód. 410).
        - Ocorrências: {dados['ocorrencias']} meses com amortização negativa.
        - Saldo Banco (Viciado): R$ {dados['saldo_banco']}
        - Saldo Recalculado (Justo): R$ {dados['saldo_justo']}
        - DIFERENÇA A RECUPERAR: R$ {dados['diferenca']}
        
        ESCREVA OS TÓPICOS:
        1. Identificação.
        2. Do Objeto (Revisão de contrato habitacional).
        3. Da Metodologia (Recálculo linear expurgando anatocismo - Súmula 121 STF).
        4. Dos Quesitos e Constatações (Explique o dano financeiro).
        5. Conclusão Pericial.
        """
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Erro ao gerar laudo: {e}"

# --- INTERFACE ---

st.title("⚖️ James Sebastian AI - Auditoria Contratual")
st.markdown("**Sistema Integrado:** PDF/Imagem -> OCR IA -> Laudo Jurídico")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Upload de Documentos")
    st.info("Suba fotos (JPG) ou arquivos (PDF) do contrato/extrato.")
    
    arquivo = st.file_uploader("Selecione o arquivo", type=["pdf", "jpg", "jpeg", "png"])
    
    if arquivo and st.button("🔍 Extrair Dados com IA"):
        with st.spinner("A IA está lendo o documento..."):
            dados_extraidos = None
            
            if arquivo.type == "application/pdf":
                texto_pdf = ler_pdf(arquivo)
                if texto_pdf:
                    dados_extraidos = extrair_dados_ia(texto_pdf, 'texto')
            else:
                imagem = Image.open(arquivo)
                dados_extraidos = extrair_dados_ia(imagem, 'imagem')
            
            if dados_extraidos:
                st.session_state.nome_cliente = dados_extraidos.get('nomes', 'Não Identificado')
                st.session_state.nome_banco = dados_extraidos.get('banco', 'Instituição Financeira')
                st.session_state.numero_contrato = str(dados_extraidos.get('contrato', 'S/N'))
                
                val = float(dados_extraidos.get('valor_financiado', 0))
                prz = int(dados_extraidos.get('prazo_meses', 0))
                jur = float(dados_extraidos.get('taxa_juros_anual', 0))
                
                if val > 0: st.session_state.valor_financiado = val
                if prz > 0: st.session_state.prazo_meses = prz
                if jur > 0: st.session_state.juros_anuais = jur
                
                st.success("Leitura concluída com sucesso!")
                st.rerun()
            else:
                st.error("Não foi possível extrair dados legíveis.")

    st.divider()
    st.header("2. Dados Identificados")
    st.session_state.nome_cliente = st.text_input("Nome do Mutuário", st.session_state.nome_cliente)
    st.session_state.nome_banco = st.text_input("Banco", st.session_state.nome_banco)
    st.session_state.numero_contrato = st.text_input("Nº Contrato", st.session_state.numero_contrato)
    
    st.subheader("Financeiro")
    st.session_state.valor_financiado = st.number_input("Valor Financiado (R$)", value=float(st.session_state.valor_financiado), format="%.2f")
    st.session_state.prazo_meses = st.number_input("Prazo (Meses)", value=int(st.session_state.prazo_meses))
    st.session_state.juros_anuais = st.number_input("Juros Anuais (%)", value=float(st.session_state.juros_anuais))
    
    st.divider()
    st.header("3. Simulação de Fraude")
    ocorrencias = st.slider("Meses com Incorporação (410)", 0, 60, 5)
    valor_inc = st.number_input("Valor Médio Incorporado", value=2500.00)

# --- CORPO PRINCIPAL ---

indices = obter_indices_bacen()
if indices:
    c1, c2, c3 = st.columns(3)
    c1.metric("Selic Hoje", f"{indices['Selic'][0]}%")
    c2.metric("TR Mensal", f"{indices['TR'][0]}%")
    c3.metric("IPCA 12m", f"{indices['IPCA'][0]}%")

st.divider()

def calcular_cenarios(valor, meses, taxa, ocr, v_inc):
    taxa_mes = (1 + taxa/100)**(1/12) - 1
    amort = valor / meses
    saldo = valor
    dados_sac = []
    
    saldo_banco = valor
    dados_banco = []
    indices_fraude = np.linspace(10, meses-10, ocr, dtype=int) if ocr > 0 else []

    for i in range(1, meses + 1):
        juros_sac = saldo * taxa_mes
        saldo -= amort
        if saldo < 0: saldo = 0
        dados_sac.append(saldo)
        
        amort_banco = valor / meses
        if i in indices_fraude:
            saldo_banco += v_inc
        else:
            saldo_banco -= amort_banco
        if saldo_banco < 0: saldo_banco = 0
        dados_banco.append(saldo_banco)
        
    return pd.DataFrame({"Mês": range(1, meses+1), "SAC": dados_sac, "Banco": dados_banco})

df = calcular_cenarios(st.session_state.valor_financiado, 
                       st.session_state.prazo_meses, 
                       st.session_state.juros_anuais, 
                       ocorrencias, valor_inc)

mes_atual = min(60, st.session_state.prazo_meses)
s_banco = df.iloc[mes_atual-1]['Banco']
s_sac = df.iloc[mes_atual-1]['SAC']
dif = s_banco - s_sac

# --- ABAS DE RESULTADOS ---
tab1, tab2 = st.tabs(["📊 Gráficos e Números", "⚖️ Laudo Pericial Pronto"])

with tab1:
    col_a, col_b = st.columns(2)
    col_a.metric("Saldo Devedor (Banco)", f"R$ {s_banco:,.2f}", delta_color="inverse")
    col_b.metric("Excesso Cobrado", f"R$ {dif:,.2f}", delta="- Valor a Restituir")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Mês'], y=df['SAC'], name='Evolução Legal', line=dict(color='green', dash='dash')))
    fig.add_trace(go.Scatter(x=df['Mês'], y=df['Banco'], name='Evolução Banco', line=dict(color='red')))
    fig.update_layout(title="Comparativo de Evolução da Dívida", height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Gerador de Laudo Automático")
    st.write("A IA usará os dados extraídos do documento para redigir o laudo.")
    
    if st.button("📝 Gerar Laudo Jurídico"):
        with st.spinner("Redigindo documento forense..."):
            dados_laudo = {
                'nome_cliente': st.session_state.nome_cliente,
                'nome_banco': st.session_state.nome_banco,
                'numero_contrato': st.session_state.numero_contrato,
                'valor_financiado': f"{st.session_state.valor_financiado:,.2f}",
                'prazo_meses': st.session_state.prazo_meses,
                'juros_anuais': st.session_state.juros_anuais,
                'ocorrencias': ocorrencias,
                'saldo_banco': f"{s_banco:,.2f}",
                'saldo_justo': f"{s_sac:,.2f}",
                'diferenca': f"{dif:,.2f}"
            }
            texto = gerar_laudo_final(dados_laudo)
            st.markdown(texto)
            st.download_button("Baixar Laudo (.txt)", texto, f"Laudo_{st.session_state.nome_cliente}.txt")
