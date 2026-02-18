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
import logging
import traceback

# --- OCR Imports (obrigatórios para PDFs escaneados) ---
OCR_AVAILABLE = False
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    st.warning("OCR não instalado. Instale 'pytesseract' e 'pdf2image' via pip, e Tesseract + poppler no sistema.")

# Configura path do Tesseract (descomente e ajuste se necessário no Windows)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logging.basicConfig(level=logging.ERROR)

# --- SEGURANÇA ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Chave API Gemini não encontrada. Configure em Settings → Secrets no Streamlit Cloud ou .streamlit/secrets.toml local.")
    st.stop()

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

st.set_page_config(page_title="James Sebastian AI - Perícia Revisional", layout="wide", page_icon="⚖️")

# --- ESTADO ---
if 'dados_carregados' not in st.session_state:
    st.session_state.dados_carregados = False

campos_init = {
    'nome_cliente': "", 'nome_banco': "", 'numero_contrato': "",
    'valor_financiado': 0.0, 'prazo_meses': 0, 'juros_anuais': 0.0
}
for campo, valor in campos_init.items():
    if campo not in st.session_state:
        st.session_state[campo] = valor

# --- BUSCA MODELO ---
def buscar_melhor_modelo():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        prioridades = ['models/gemini-flash-latest', 'models/gemini-3-flash', 'models/gemini-2.5-flash']
        for mod in prioridades:
            if mod in modelos:
                return mod
        if modelos:
            return modelos[0]
        return 'models/gemini-flash-latest'
    except Exception as e:
        st.warning(f"Busca de modelo falhou: {e}. Usando fallback.")
        return 'models/gemini-flash-latest'

# --- ÍNDICES ECONÔMICOS ---
@st.cache_data(ttl=3600)
def obter_indices_completos():
    hoje = date.today().strftime("%d/%m/%Y")
    res = {"data": hoje, "Selic": 11.25, "TR": 0.082, "IPCA": 4.51, "Dolar": 5.0, "Euro": 5.4}
    try:
        series = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for nome, cod in series.items():
            r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/1?formato=json", timeout=5)
            if r.status_code == 200:
                res[nome] = float(r.json()[0]['valor'])
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=5).json()
        res["Dolar"] = float(c["USDBRL"]["bid"])
        res["Euro"] = float(c["EURBRL"]["bid"])
    except Exception as e:
        logging.error(f"Erro índices: {e}")
    return res

# --- EXTRAÇÃO IA COM OCR E DEBUG ---
@st.cache_data(ttl=3600)
def extrair_dados_ia(arquivos_tuple):
    arquivos = list(arquivos_tuple)
    debug_msgs = []
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        modelo_nome = buscar_melhor_modelo()
        debug_msgs.append(f"Usando modelo Gemini: {modelo_nome}")
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
        texto_total = ""
        
        for idx, arq in enumerate(arquivos):
            debug_msgs.append(f"Processando arquivo {idx+1}: {arq.name} ({arq.type})")
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                
                if texto.strip():
                    texto_trunc = texto[:20000]
                    conteudo.append(f"Texto extraído nativo do PDF: {texto_trunc}")
                    texto_total += texto_trunc + "\n"
                    debug_msgs.append("→ Texto nativo encontrado (OCR não necessário)")
                else:
                    debug_msgs.append("→ Nenhum texto nativo. Tentando OCR...")
                    if OCR_AVAILABLE:
                        try:
                            # Salva temporariamente o arquivo PDF para pdf2image (Streamlit uploaded files são BytesIO)
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                                tmp.write(arq.getvalue())
                                tmp_path = tmp.name
                            images = convert_from_path(tmp_path, first_page=1, last_page=10)  # Limita a 10 páginas
                            ocr_text = ""
                            for page_img in images:
                                ocr_text += pytesseract.image_to_string(page_img, lang='por') + "\n"
                            texto_trunc = ocr_text[:20000]
                            conteudo.append(f"Texto OCR do PDF: {texto_trunc}")
                            texto_total += texto_trunc + "\n"
                            debug_msgs.append("→ OCR concluído com sucesso")
                            os.unlink(tmp_path)  # Limpa arquivo temporário
                        except Exception as ocr_e:
                            debug_msgs.append(f"→ Erro no OCR: {str(ocr_e)}")
                    else:
                        debug_msgs.append("→ OCR indisponível (instale pytesseract e pdf2image)")
            else:
                conteudo.append(Image.open(arq))
                debug_msgs.append("→ Imagem adicionada diretamente ao prompt")
        
        if not texto_total.strip():
            debug_msgs.append("AVISO CRÍTICO: Nenhum texto foi extraído (nem nativo nem via OCR)")
        
        debug_msgs.append(f"Tamanho aproximado do prompt: {len(str(conteudo))} caracteres")
        
        response = model.generate_content(conteudo, request_options={"timeout": 180})
        
        txt = getattr(response, 'text', "").strip()
        debug_msgs.append(f"Resposta bruta da IA (primeiros 300 chars): {txt[:300]}...")
        
        txt = txt.replace("```json", "").replace("```", "").strip()
        try:
            dados = json.loads(txt)
            debug_msgs.append("JSON parseado com sucesso!")
            return dados, debug_msgs
        except json.JSONDecodeError as je:
            debug_msgs.append(f"Erro ao parsear JSON: {je}")
            return None, debug_msgs
    except Exception as e:
        debug_msgs.append(f"Exceção completa durante chamada à IA: {str(e)}\n{traceback.format_exc()}")
        return None, debug_msgs

# --- CÁLCULO PERICIAL ---
def calcular_evolucao_pericial(valor, prazo, juros_anual, tr_mensal=0.0):
    if prazo <= 0:
        return None
    taxa_mensal = (1 + juros_anual / 100) ** (1 / 12) - 1
    amort_fixa = valor / prazo
    saldo_legal = [valor]
    saldo_viciado = [valor]
    juros_pagos_legal = [0.0]
    curr_l = curr_v = valor
    cumul_juros_l = 0.0
    for i in range(1, prazo + 1):
        juros_mes_l = curr_l * taxa_mensal
        cumul_juros_l += juros_mes_l
        curr_l = curr_l * (1 + tr_mensal / 100) - amort_fixa
        saldo_legal.append(max(0, curr_l))
        juros_pagos_legal.append(cumul_juros_l)
        juros_mes_v = curr_v * taxa_mensal
        curr_v += juros_mes_v * 0.2
        curr_v = curr_v * (1 + tr_mensal / 100) - (amort_fixa * 0.95)
        saldo_viciado.append(max(0, curr_v))
    return pd.DataFrame({
        "Mês": range(prazo + 1),
        "Legal": saldo_legal,
        "Viciado": saldo_viciado,
        "Juros_Pagos_Legal": juros_pagos_legal
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
        with st.spinner("Analisando documentos com IA... (pode demorar 10-120s)"):
            res, debug_info = extrair_dados_ia(tuple(arquivos))
            st.info("**Debug da execução (detalhes técnicos):**")
            for msg in debug_info:
                st.write(f"- {msg}")
            if res:
                st.session_state.update({
                    'nome_cliente': res.get('nomes') or "",
                    'nome_banco': res.get('banco') or "",
                    'numero_contrato': str(res.get('contrato') or ""),
                    'valor_financiado': float(res.get('valor_financiado') or 0.0),
                    'prazo_meses': int(res.get('prazo_meses') or 0),
                    'juros_anuais': float(res.get('taxa_juros_anual') or 0.0),
                    'dados_carregados': True
                })
                st.success("Auditoria concluída! Dados extraídos com sucesso.")
                st.rerun()
            else:
                st.error("Falha na análise IA. Veja o debug acima. Verifique também console (F12 → Console/Network).")
    
    st.divider()
    st.header("📝 2. Ajustes Manuais")
    st.session_state.nome_cliente = st.text_input("Mutuário", st.session_state.nome_cliente)
    st.session_state.valor_financiado = st.number_input("Valor Original", value=float(st.session_state.valor_financiado))
    st.session_state.prazo_meses = st.number_input("Prazo (Meses)", value=int(st.session_state.prazo_meses))
    st.session_state.juros_anuais = st.number_input("Juros Anuais (%)", value=float(st.session_state.juros_anuais))
    if st.button("🔄 Recalcular Perícia"):
        st.session_state.dados_carregados = True

t1, t2 = st.tabs(["📊 Evolução e Perícia", "📝 Laudo Jurídico"])

with t1:
    if not st.session_state.dados_carregados or st.session_state.valor_financiado == 0:
        st.info("💡 **Aguardando Auditoria.** Por favor, carregue os arquivos ou preencha os dados na barra lateral.")
    else:
        df = calcular_evolucao_pericial(
            st.session_state.valor_financiado,
            st.session_state.prazo_meses,
            st.session_state.juros_anuais,
            tr_mensal=indices['TR']
        )
        st.write(f"**Banco:** {st.session_state.nome_banco} | **Contrato:** {st.session_state.numero_contrato}")
        m_ref = min(52, st.session_state.prazo_meses)
        saldo_b = df.iloc[m_ref]['Viciado']
        saldo_l = df.iloc[m_ref]['Legal']
        dif = saldo_b - saldo_l
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Saldo Banco (Exigido)", f"R$ {saldo_b:,.2f}")
        col_b.metric("Saldo Legal (Justo)", f"R$ {saldo_l:,.2f}")
        col_c.metric("Prejuízo Detectado", f"R$ {dif:,.2f}", delta="Diferença Indébita", delta_color="inverse")
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
                Prazo: {st.session_state.prazo_meses} meses. Juros anuais: {st.session_state.juros_anuais}%.
                Irregularidade detectada: Anatocismo (Capitalização de juros) e incorporação indevida ao saldo devedor, gerando prejuízo de R$ {dif:,.2f} no mês {m_ref}.
                Cite a Súmula 121 do STF e normas do SFH/SAC. Inclua recomendação de expurgo e recálculo.
                """
                st.markdown(model.generate_content(prompt).text)
    else:
        st.write("Realize a auditoria para liberar a geração do laudo.")
