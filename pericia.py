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
st.set_page_config(page_title="James Sebastian AI - Perícia Premium", layout="wide", page_icon="⚖️")

# Tenta obter a chave da API dos Secrets ou usa uma string vazia para fallback
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- ESTILO CSS PERSONALIZADO (LOOK PREMIUM) ---
st.markdown("""
    <style>
    .main { background-color: #f4f4f9; }
    .stButton>button { 
        width: 100%; border-radius: 8px; height: 3.5em; 
        background-color: #1e1e1e; color: white; font-weight: bold; 
        border: 1px solid #d4af37; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #d4af37; color: #1e1e1e; }
    .main-header { 
        font-size: 32px; font-weight: bold; background-color: #1e1e1e; 
        color: #ffffff; padding: 25px; text-align: center; border-radius: 12px; 
        margin-bottom: 30px; border-bottom: 6px solid #d4af37;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .sub-header { 
        font-size: 20px; font-weight: bold; background-color: #333; 
        color: white; padding: 12px; text-align: center; border-radius: 8px; 
        margin-top: 25px; 
    }
    .status-irregular { 
        color: #ff0000; font-size: 22px; font-weight: bold; text-align: right; 
        border: 2px solid #ff0000; padding: 8px 20px; border-radius: 8px; 
        display: inline-block; background-color: rgba(255,0,0,0.05);
    }
    .status-regular { 
        color: #28a745; font-size: 22px; font-weight: bold; text-align: right; 
        border: 2px solid #28a745; padding: 8px 20px; border-radius: 8px; 
        display: inline-block; background-color: rgba(40,167,69,0.05);
    }
    .highlight-yellow { 
        background-color: #ffff00; padding: 18px; font-weight: bold; 
        font-size: 26px; color: #000; border-radius: 10px; text-align: center; 
        border: 1px solid #ccc; margin: 15px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .card-index { 
        background-color: white; padding: 15px; border-radius: 12px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); text-align: center;
        border-top: 5px solid #d4af37;
    }
    .index-label { font-size: 13px; color: #777; font-weight: bold; text-transform: uppercase; }
    .index-value { font-size: 22px; font-weight: bold; color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE APOIO ---

@st.cache_data(ttl=3600)
def obter_indices_atualizados():
    """Busca índices económicos reais via API do Banco Central e AwesomeAPI"""
    hoje = date.today().strftime("%d/%m/%Y")
    res = {"data": hoje, "Selic": 11.25, "TR": 0.082, "IPCA": 4.51, "Dolar": 5.02, "Euro": 5.41}
    try:
        series = {"Selic": 432, "TR": 226, "IPCA": 13522}
        for nome, cod in series.items():
            r = requests.get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados/ultimos/1?formato=json", timeout=4)
            if r.status_code == 200:
                res[nome] = float(r.json()[0]['valor'])
        c = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL", timeout=4).json()
        res["Dolar"] = float(c["USDBRL"]["bid"])
        res["Euro"] = float(c["EURBRL"]["bid"])
    except:
        pass
    return res

def extrair_dados_ia(arquivos):
    """Extrai dados dos documentos sem inventar valores"""
    if not GEMINI_API_KEY:
        st.error("⚠️ Configura a chave API do Gemini no Streamlit Cloud (Settings -> Secrets).")
        return None
    
    try:
        # Usa o modelo estável mais recente
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """Atue como um perito judicial sênior. Analise os documentos bancários fornecidos e extraia os dados abaixo para um JSON puro.
        IMPORTANTE: 
        1. Responda APENAS o JSON.
        2. Se não encontrar um valor, use null. NÃO INVENTE DADOS.
        Campos: {"nome_mutuario": str, "banco": str, "num_contrato": str, "valor_financiado": float, "prazo_total": int, "parcelas_pagas": int, "taxa_juros_anual": float, "valor_ultima_parcela": float, "valor_seguro": float, "taxa_adm": float}
        Busque por irregularidades como o 'Código 410' (Incorporação Normal)."""
        
        conteudo = [prompt]
        for arq in arquivos:
            if arq.type == "application/pdf":
                with pdfplumber.open(arq) as pdf:
                    texto = "\n".join([p.extract_text() or "" for p in pdf.pages])
                    conteudo.append(f"Conteúdo do PDF: {texto[:18000]}")
            else:
                conteudo.append(Image.open(arq))
        
        response = model.generate_content(conteudo)
        # Limpa markdown da resposta caso a IA inclua
        txt_limpo = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(txt_limpo)
    except Exception as e:
        st.error(f"Erro na análise IA: {e}")
        return None

# --- INTERFACE PRINCIPAL ---

# Cabeçalho de Autoridade
col_l, col_t = st.columns([1, 6])
with col_l:
    st.markdown("<h1 style='text-align: center; color: #d4af37; margin: 0;'>⚖️</h1>", unsafe_allow_html=True)
with col_t:
    st.markdown('<div class="main-header">JAMES SEBASTIAN AI - PERÍCIA JUDICIAL PREMIUM</div>', unsafe_allow_html=True)

idx = obter_indices_atualizados()

# Dashboard de Indicadores em Tempo Real
st.markdown("### 📈 Indicadores do Mercado Financeiro")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f"<div class='card-index'><span class='index-label'>Selic</span><br><span class='index-value'>{idx['Selic']}%</span></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='card-index'><span class='index-label'>TR (Mensal)</span><br><span class='index-value'>{idx['TR']}%</span></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='card-index'><span class='index-label'>IPCA (12m)</span><br><span class='index-value'>{idx['IPCA']}%</span></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='card-index'><span class='index-label'>USD/BRL</span><br><span class='index-value'>R$ {idx['Dolar']:.2f}</span></div>", unsafe_allow_html=True)
with c5: st.markdown(f"<div class='card-index'><span class='index-label'>EUR/BRL</span><br><span class='index-value'>R$ {idx['Euro']:.2f}</span></div>", unsafe_allow_html=True)
st.caption(f"Dados atualizados em tempo real: {idx['data']}")

# Sidebar: Upload e Ajustes
with st.sidebar:
    st.markdown("<div style='text-align: center; padding-bottom: 20px;'><img src='https://cdn-icons-png.flaticon.com/512/3135/3135715.png' width='80'></div>", unsafe_allow_html=True)
    st.header("📂 1. Documentação")
    files = st.file_uploader("Submeter Contratos/Extratos", accept_multiple_files=True, type=['pdf', 'jpg', 'png'])
    
    if files and st.button("🔍 Iniciar Auditoria Automática"):
        with st.spinner("O perito James Sebastian está analisando as provas..."):
            res = extrair_dados_ia(files)
            if res:
                st.session_state.update(res)
                st.success("✅ Dados extraídos com sucesso!")
                st.rerun()

    st.divider()
    st.header("📝 2. Parâmetros Periciais")
    # Campos dinâmicos baseados no estado da sessão
    mutuario = st.text_input("Nome do Mutuário", st.session_state.get('nome_mutuario', ""))
    banco_nome = st.text_input("Instituição Financeira", st.session_state.get('banco', ""))
    valor_f = st.number_input("Valor Financiado (R$)", value=float(st.session_state.get('valor_financiado', 0.0)), step=1000.0)
    prazo_n = st.number_input("Prazo Total (Meses)", value=int(st.session_state.get('prazo_total', 360)), min_value=1)
    pagas_k = st.number_input("Parcelas Já Pagas", value=int(st.session_state.get('parcelas_pagas', 0)))
    taxa_aa = st.number_input("Taxa Contratual (% a.a.)", value=float(st.session_state.get('taxa_juros_anual', 0.0)), step=0.01)
    p_atual_cobrada = st.number_input("Valor da Prestação Cobrada (R$)", value=float(st.session_state.get('valor_ultima_parcela', 0.0)))
    seguro_v = st.number_input("Valor do Seguro (R$)", value=float(st.session_state.get('valor_seguro', 0.0)))
    taxa_adm_v = st.number_input("Taxa Adm. (R$)", value=float(st.session_state.get('taxa_adm', 25.0)))

# --- MOTOR DE CÁLCULO SAC (SISTEMA FINANCEIRO DA HABITAÇÃO) ---
if valor_f > 0 and prazo_n > 0:
    # Matemática SAC: Amortização é constante
    amort_legal = valor_f / prazo_n
    
    # Conversão de taxa anual nominal para mensal efetiva
    # i_mensal = (1 + i_anual)^(1/12) - 1
    taxa_i = (1 + taxa_aa/100)**(1/12) - 1
    
    # Saldo Devedor Teórico no mês atual (antes do pagamento atual)
    # SD(k-1) = Valor_F - (Amort_Legal * (k-1))
    sd_anterior = max(0, valor_f - (amort_legal * (pagas_k - 1)))
    juros_mes_legal = sd_anterior * taxa_i
    
    # Prestação Correta (SAC) = Amortização + Juros + Encargos
    prestacao_correta = amort_legal + juros_mes_legal + seguro_v + taxa_adm_v
    
    # Apuração de Diferenças
    dif_mensal = p_atual_cobrada - prestacao_correta
    recuperavel_estimado = (dif_mensal * pagas_k) * 1.25 # Coeficiente médio com juros/correção
    is_irregular = dif_mensal > 10.0 # Margem técnica de arredondamento

    # --- RESULTADOS ---
    t_res, t_laudo = st.tabs(["📊 Análise Sintetizada", "⚖️ Minuta de Laudo Técnico"])

    with t_res:
        st.markdown('<div class="sub-header">DETALHAMENTO DA ANÁLISE IMOBILIÁRIA</div>', unsafe_allow_html=True)
        
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            st.markdown(f"**NOME:** {mutuario}")
            st.markdown(f"**BANCO:** {banco_nome}")
            st.markdown(f"**VALOR FINANCIADO:** R$ {valor_f:,.2f}")
        with c_i2:
            status_style = "status-irregular" if is_irregular else "status-regular"
            status_txt = "CONTRATO IRREGULAR" if is_irregular else "CONTRATO REGULAR"
            st.markdown(f"<div style='text-align:right;'><span class='{status_style}'>{status_txt}</span></div>", unsafe_allow_html=True)
            st.markdown(f"**CONTRATO Nº:** {st.session_state.get('num_contrato', '---')}")
            st.markdown(f"**PARCELAS PAGAS:** {pagas_k}")

        st.markdown(f'<div class="highlight-yellow">SALDO DEVEDOR ATUALIZADO (TEÓRICO): R$ {max(0, valor_f - (amort_legal * pagas_k)):,.2f}</div>', unsafe_allow_html=True)

        st.markdown('<div class="sub-header">COMPARATIVO DE CONFORMIDADE</div>', unsafe_allow_html=True)
        st.write(f"**VALOR DA PARCELA ATUAL DO IMÓVEL: R$ {p_atual_cobrada:,.2f}**")

        # Gráfico Plotly: Pago vs. Devido (Ajustado para evitar erros de cor)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=['O QUE O BANCO COBRA', 'O QUE A LEI EXIGE (SAC)'],
            x=[p_atual_cobrada, prestacao_correta],
            orientation='h',
            marker_color=['#ff0000', '#28a745'],
            text=[f"R$ {p_atual_cobrada:,.2f}", f"R$ {prestacao_correta:,.2f}"],
            textposition='auto',
        ))
        fig.update_layout(title="Ajuste de Parcela", height=300, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # Quadro de Valores Recuperáveis
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Amortização Mensal", f"R$ {amort_legal:,.2f}")
        m2.metric("Excesso por Parcela", f"R$ {dif_mensal:,.2f}", delta_color="inverse")
        m3.metric("Indébito Estimado", f"R$ {recuperavel_estimado:,.2f}")
        
        st.markdown(f"""
        <div style="background-color: #1e1e1e; color: white; padding: 30px; border-radius: 12px; text-align: center; border: 2px solid #d4af37;">
            <span style="font-size: 18px; color: #d4af37; font-weight: bold;">VALOR TOTAL ESTIMADO PARA RECUPERAÇÃO</span><br>
            <span style="font-size: 42px; font-weight: bold;">R$ {recuperavel_estimado:,.2f}</span>
        </div>
        """, unsafe_allow_html=True)

    with t_laudo:
        st.markdown('<div class="sub-header">PARECER TÉCNICO FUNDAMENTADO</div>', unsafe_allow_html=True)
        
        if st.button("📄 GERAR LAUDO PERICIAL COMPLETO (IA)"):
            with st.spinner("James Sebastian está consolidando a fundamentação jurídica..."):
                model_ia = genai.GenerativeModel('gemini-1.5-flash')
                
                contexto_laudo = f"""
                Atue como o perito judicial James Sebastian, 30 anos de experiência.
                Gere um Laudo Pericial completo em Markdown para o mutuário {mutuario}.
                DADOS: Banco {banco_nome}, Valor Financiado R$ {valor_f:,.2f}, {pagas_k} parcelas pagas.
                IRREGULARIDADE: Diferença de R$ {dif_mensal:,.2f} por parcela.
                
                ESTRUTURA OBRIGATÓRIA:
                1. CABEÇALHO: Identificação e Objeto da Perícia.
                2. METODOLOGIA: Explicação do Sistema SAC (Lei 4.380/64) e amortização fixa.
                3. EXAME TÉCNICO: Tabela comparando Valores Pagos vs Valores Devidos.
                4. ANÁLISE DE ANATOCISMO: Explique o Código 410 e a Súmula 121 do STF.
                5. JURISPRUDÊNCIA: Citar Súmula 121 STF, Súmula 93 STJ e Art. 4º Decreto 22.626/33.
                6. CONCLUSÃO: Valor final do indébito e recomendação técnica de expurgo.
                
                Seja formal, técnico e não invente dados além dos fornecidos.
                """
                
                resultado = model_ia.generate_content(contexto_laudo)
                st.markdown(resultado.text)
                
                st.download_button(
                    label="📥 Descarregar Minuta do Laudo (TXT)",
                    data=resultado.text,
                    file_name=f"Parecer_James_Sebastian_{mutuario.replace(' ', '_')}.txt",
                    mime="text/plain"
                )

else:
    st.info("👋 Olá Fred! O sistema James Sebastian está pronto para a auditoria. Submete os ficheiros na barra lateral ou preenche os dados manualmente para começar.")
    st.image("https://images.unsplash.com/photo-1450101499163-c8848c66ca85?auto=format&fit=crop&q=80&w=1000", caption="James Sebastian: Rigor Matemático e Justiça Contratual.")
