# James-Sebastian-AI
Sistema de Perícia Judicial e Auditoria Financeira para contratos SFH/SAC. Realiza recálculo de dívidas, expurgo de anatocismo (Súmula 121 STF) e detecção de irregularidades (Cód. 410) com Python e Streamlit.
# ⚖️ James Sebastian AI - Sistema de Perícia Revisional Bancária

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow)

## 📋 Sobre o Projeto

Este repositório contém uma ferramenta de **Auditoria Forense Financeira** desenvolvida para analisar contratos de financiamento imobiliário, especificamente no âmbito do **SFH (Sistema Financeiro da Habitação)**.

O objetivo principal do sistema é identificar e quantificar abusividades contratuais, com foco na prática de **Anatocismo (Juros sobre Juros)** disfarçada de "Incorporação de Juros" (Código 410), comum em contratos de grandes instituições financeiras.

## 🚀 Funcionalidades Principais

* **Simulação de Cenários:** Compara a evolução da dívida cobrada pelo banco ("Cenário Viciado") contra a evolução legal da dívida ("Cenário Justo/SAC Puro").
* **Detecção de Anatocismo:** Identifica meses onde houve amortização negativa ou incorporação de juros ao saldo devedor.
* **Recálculo Automático:** Aplica metodologia de juros simples para expurgar a capitalização composta.
* **Dashboard Interativo:** Visualização gráfica (Plotly) da divergência entre o saldo cobrado e o saldo devido.
* **Geração de Laudo Preliminar:** Emite um resumo técnico com o prejuízo estimado e fundamentação para ações revisionais.

## 🛠️ Tecnologias Utilizadas

* **Python:** Linguagem base para cálculos financeiros de alta precisão.
* **Streamlit:** Framework para criação da interface web interativa.
* **Pandas:** Manipulação e estruturação dos dados do extrato (DataFrames).
* **Plotly:** Geração de gráficos dinâmicos e interativos para visualização da perícia.
* **NumPy:** Cálculos matemáticos vetoriais.

## ⚖️ Fundamentação Jurídica

A lógica do algoritmo baseia-se nos seguintes princípios:
* **Súmula 121 do STF:** *"É vedada a capitalização de juros, ainda que expressamente convencionada."*
* **Sistema de Amortização Constante (SAC):** Verificação do cumprimento da cláusula de amortização linear.
* **Código de Defesa do Consumidor:** Dever de transparência e proibição de onerosidade excessiva.

## 📦 Como Executar Localmente

1.  Clone o repositório:
    ```bash
    git clone [https://github.com/SEU_USUARIO/NOME_DO_REPO.git](https://github.com/SEU_USUARIO/NOME_DO_REPO.git)
    ```
2.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
3.  Execute a aplicação:
    ```bash
    streamlit run pericia.py
    ```

## 📊 Exemplo de Uso

A ferramenta permite ajustar parâmetros como:
* Valor Financiado
* Taxa de Juros Anual
* Prazo do Contrato
* Quantidade de Incorporações (Irregularidades) detectadas no extrato.

---
**Desenvolvido por Frederico Novotny** | *Ferramenta de apoio à análise pericial.*
