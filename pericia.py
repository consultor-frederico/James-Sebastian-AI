if arquivos and st.button("🔍 Iniciar Auditoria IA"):
        with st.spinner("Analisando documentos..."):
            res, debug_info = extrair_dados_ia(tuple(arquivos))
            
            if res:
                # Preenchimento garantido dos dados
                st.session_state.nome_cliente = str(res.get('nomes', ''))
                st.session_state.nome_banco = str(res.get('banco', ''))
                st.session_state.numero_contrato = str(res.get('contrato', ''))
                st.session_state.valor_financiado = float(res.get('valor_financiado') or 0.0)
                st.session_state.prazo_meses = int(res.get('prazo_meses') or 0)
                st.session_state.juros_anuais = float(res.get('taxa_juros_anual') or 0.0)
                st.session_state.dados_carregados = True
                
                st.success("✅ Auditoria concluída! Dados carregados nos campos abaixo.")
                st.rerun()
            else:
                st.error("❌ A IA leu o arquivo, mas não conseguiu extrair os dados estruturados.")
                with st.expander("Clique aqui para ver o motivo detalhado"):
                    for msg in debug_info:
                        st.write(msg)
                st.warning("Dica: Verifique se o contrato está legível ou tente subir apenas a primeira página.")
