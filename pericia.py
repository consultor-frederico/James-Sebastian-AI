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
# Substitua pela sua chave real se necessário, mas a que você forneceu está aqui.
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

def ler_pdf(file):
    """Extrai texto de um PDF"""
    texto = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                texto += page.extract_text() or ""
        return texto
    except Exception as e:
        return f"Erro ao ler PDF: {e}"

def extrair_dados_multiplos(arquivos):
    """
    Processa uma LISTA de arquivos (PDFs e Imagens),
    junta tudo e manda para o Gemini extrair os dados.
    """
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 1. Preparar o Prompt
        prompt_sistema = """
        Você é um perito assistente especialista em auditoria bancária.
        Analise o conjunto de documentos fornecidos (Contratos, Extratos, Fotos) e extraia os dados consolidados.
        
        RETORNE APENAS UM JSON (sem markdown) com estas chaves:
        1. "banco": (Nome da Instituição Financeira)
        2. "contrato": (Número do contrato)
        3. "nomes": (Nome do mutuário/devedor principal)
        4. "valor_financiado": (float, valor original da dívida/compra e venda - use ponto para decimais)
        5. "prazo_meses": (int, prazo total em meses)
        6. "taxa_juros_anual": (float, taxa de juros nominal anual. Se houver Nominal e Efetiva, prefira a Nominal)

        Se houver divergência entre documentos, priorize o "Contrato de Financiamento" para taxas e prazos.
        Se não encontrar algum dado, coloque null ou 0.
        """
        
        conteudo_ia = [prompt_sistema]
        texto_acumulado = ""
        
        # 2. Iterar sobre os arquivos e preparar o payload
        for arq in arquivos:
            # Se for PDF -> Extrai texto
            if arq.type == "application/pdf":
                texto = ler_pdf(arq)
                texto_acumulado += f"\n--- Conteúdo do arquivo {arq.name} ---\n{texto}\n"
            
            # Se for Imagem -> Adiciona a imagem direta para a IA ver
            elif arq.type in ["image/png", "image/jpeg", "image/jpg"]:
                img = Image.open(arq)
                conteudo_ia.append(f"\nImagem do arquivo {arq.name}:")
                conteudo_ia.append(img)
        
        # Adiciona todo o texto acumulado dos PDFs ao payload
        if texto_acumulado:
            conteudo_ia.append("\nTEXTOS EXTRAÍDOS DOS PDFs:\n" + texto_acumulado[:30000]) # Limite de caracteres

        # 3. Chamar a IA
        response = model.generate_content(conteudo_ia)
        
        # 4. Limpar JSON
        json_str = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(json_str)

    except Exception as e:
        st.error(f"Erro na análise IA: {e}")
        return None

def gerar_laudo_final(dados):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Escreva um LAUDO TÉCNICO PERICIAL JURÍDICO (Revisional Bancária - SFH).
        Use formatação Markdown profissional. Seja técnico, imparcial e contundente.

        1. QUALIFICAÇÃO:
        - Mutuário: {dados['nome_cliente']}
        - Réu (Banco): {dados['nome_banco']}
        - Contrato nº: {dados['numero_contrato']}
        
        2. DADOS DO CONTRATO:
        - Valor Financiado: R$ {dados['valor_financiado']}
        - Prazo: {dados['prazo_meses']} meses
        - Taxa Contratual: {dados['juros_anuais']}% a.a.
        
        3. ACHADOS DA PERÍCIA (IRREGULARIDADES):
        - Metodologia: Recálculo utilizando o Sistema de Amortização Constante (SAC) puro, sem capitalização.
        - Irregularidade Principal: Identificada a prática de "Incorporação de Juros" (Código 410 no extrato), caracterizando Anatocismo (Súmula 121 STF).
        - Impacto: {dados['ocorrencias']} meses onde os juros não pagos foram somados ao saldo devedor, gerando juros sobre juros.
        
        4. RESULTADO FINANCEIRO (DATA BASE ATUAL):
        - Saldo Devedor Exigido pelo Banco (Viciado): R$ {dados['saldo_banco']}
        - Saldo Devedor Apurado na Perícia (Legal): R$ {dados['saldo_justo']}
        - INDÉBITO/PREJUÍZO A RECUPERAR: R$ {dados['diferenca']}
        
        ESTRUTURA DO TEXTO:
        I. Do Objeto da Perícia
        II. Da Metodologia Aplicada
        III. Dos Quesitos Técnicos (Análise da Evolução da Dívida e do Anatocismo)
        IV. Da Conclusão Pericial (Destaque o valor da diferença encontrada).
        """
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Erro ao gerar laudo: {e}"

# --- INTERFACE ---

st.title("⚖️ James Sebastian AI - Auditoria Contratual Multidocumento")
st.markdown("**Sistema Integrado:** Suporte a Múltiplos Arquivos (PDF + Imagens) -> Análise Cruzada -> Laudo Jurídico")

# --- BARRA LATERAL (UPLOAD E DADOS) ---
with st.sidebar:
    st.header("1. Upload de Documentos")
    st.info("Selecione TODOS os arquivos de uma vez (Contrato, Extrato, Fotos). Segure Ctrl ou Shift para selecionar vários.")
    
    arquivos = st.file_uploader("Selecione os arquivos", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)
    
    if arquivos and st.button("🔍 Analisar Documentos com IA"):
        with st.spinner(f"A IA está lendo {len(arquivos)} documento(s)..."):
            
            dados_extraidos = extrair_dados_multiplos(arquivos)
            
            if dados_extraidos:
                # Atualiza Session State com verificação de nulos
                st.session_state.nome_cliente = dados_extraidos.get('nomes') or "Não Identificado"
                st.session_state.nome_banco = dados_extraidos.get('banco') or "Instituição Financeira"
                st.session_state.numero_contrato = str(dados_extraidos.get('contrato') or "S/N")
                
                val = dados_extraidos.get('valor_financiado')
                prz = dados_extraidos.get('prazo_meses')
                jur = dados_extraidos.get('taxa_juros_anual')
                
                if val: st.session_state.valor_financiado = float(val)
                if prz: st.session_state.prazo_meses = int(prz)
                if jur: st.session_state.juros_anuais = float(jur)
                
                st.success("Análise cruzada concluída!")
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
    st.write(f"Gerando laudo para: **{st.session_state.nome_cliente}**")
    
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
