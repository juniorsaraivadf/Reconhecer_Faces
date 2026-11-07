import streamlit as st

st.set_page_config(page_title="Agente de reconhecimento facial", page_icon=":material/face:")

pagina = st.navigation(
    [
        st.Page(
            "app_pages/identificar.py",
            title="Identificar",
            icon=":material/person_search:",
            help="Envie ou tire uma foto para o agente reconhecer e falar o nome da pessoa.",
        ),
        st.Page(
            "app_pages/cadastrar.py",
            title="Cadastrar",
            icon=":material/person_add:",
            help="Cadastre uma foto de cada vez. Mais fotos da mesma pessoa melhoram o reconhecimento.",
        ),
        st.Page(
            "app_pages/pessoas.py",
            title="Pessoas cadastradas",
            icon=":material/group:",
            help="Veja quem está cadastrado e exclua pessoas com suas fotos.",
        ),
    ]
)
pagina.run()
