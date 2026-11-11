from pathlib import Path

import streamlit as st

TITULO = "Reconhecimento de Faces com IA"
LOGO = Path(__file__).parent / "assets" / "logo_seti.jpg"

st.set_page_config(page_title=TITULO, page_icon=":material/face:")
st.image(
    str(LOGO),
    width=360,
    alt="Logo da SETI, Semana de Tecnologia Industrial do IFCE Campus Limoeiro do Norte",
)
st.title(TITULO)

pagina = st.navigation(
    [
        st.Page(
            "app_pages/identificar.py",
            title="Identificar",
            icon=":material/person_search:",
            help="Mostre o rosto na câmera ao vivo, ou use uma foto, para o agente reconhecer e falar o nome da pessoa.",
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
