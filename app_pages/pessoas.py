import streamlit as st

from agente.memoria import Pessoa
from agente.recursos import carregar_memoria

memoria = carregar_memoria()


@st.dialog("Excluir pessoa")
def confirmar_exclusao(pessoa: Pessoa) -> None:
    st.write(f"Excluir {pessoa.nome} e suas fotos? Esta ação não pode ser desfeita.")
    if st.button("Excluir", type="primary", icon=":material/delete:", key="confirmar_exclusao"):
        memoria.remover(pessoa.id)
        st.rerun()


st.title("Pessoas cadastradas")

pessoas = memoria.pessoas()
if not pessoas:
    st.info("Ninguém foi cadastrado ainda.", icon=":material/info:")
    st.page_link("app_pages/cadastrar.py", label="Ir para o cadastro", icon=":material/person_add:")
    st.stop()

st.caption(f"Total de pessoas: {len(pessoas)}")

for pessoa in pessoas:
    with st.container(border=True):
        total = len(pessoa.fotos)
        with st.container(horizontal=True, vertical_alignment="center"):
            st.subheader(pessoa.nome)
            st.badge(f"{total} {'foto' if total == 1 else 'fotos'}")
            if st.button("Excluir", icon=":material/delete:", key=f"excluir_{pessoa.id}"):
                confirmar_exclusao(pessoa)
        st.image(
            [str(memoria.caminho_foto(foto)) for foto in pessoa.fotos],
            width=96,
            alt=[f"Foto {i} de {pessoa.nome}" for i in range(1, total + 1)],
        )
