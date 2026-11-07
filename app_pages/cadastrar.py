import streamlit as st

from agente.memoria import normalizar_nome
from agente.recursos import capturar_foto, carregar_memoria, carregar_visao
from agente.visao import (
    LADO_MINIMO_ROSTO_CADASTRO,
    ImagemInvalida,
    codificar_jpeg,
    decodificar_imagem,
    desenhar_rostos,
)

VERDE = (80, 175, 76)  # BGR

if "cadastros_feitos" not in st.session_state:
    st.session_state.cadastros_feitos = 0

st.title("Cadastrar pessoa")
st.caption(
    "Cadastre uma foto por vez, com um único rosto. Para melhorar o reconhecimento, "
    "repita o mesmo nome com fotos em ângulos e iluminações diferentes."
)

aviso = st.session_state.pop("aviso_cadastro", None)
if aviso:
    st.success(aviso, icon=":material/check_circle:")

# Trocar o sufixo das chaves limpa os campos depois de cada cadastro.
sufixo = st.session_state.cadastros_feitos
nome = normalizar_nome(st.text_input("Nome da pessoa", max_chars=80, key=f"nome_{sufixo}"))
foto = capturar_foto(f"cadastrar_{sufixo}")
if foto is None:
    st.stop()

try:
    imagem = decodificar_imagem(foto.getvalue())
except ImagemInvalida as erro:
    st.error(str(erro), icon=":material/error:")
    st.stop()

rostos = carregar_visao().perceber(imagem)
if not rostos:
    st.warning(
        "Nenhum rosto encontrado. Tente uma foto mais iluminada e de frente.",
        icon=":material/warning:",
    )
    st.stop()

st.image(
    desenhar_rostos(imagem, rostos, [VERDE] * len(rostos)),
    channels="BGR",
    width=320,
    alt=f"Foto para cadastro com {len(rostos)} rosto(s) marcado(s)",
)

if len(rostos) > 1:
    st.warning(
        f"A foto tem {len(rostos)} rostos. Use uma foto só com a pessoa a cadastrar.",
        icon=":material/group_off:",
    )
    st.stop()

rosto = rostos[0]
if min(rosto.caixa[2:]) < LADO_MINIMO_ROSTO_CADASTRO:
    st.warning("O rosto está muito pequeno. Aproxime-se da câmera.", icon=":material/zoom_in:")
    st.stop()

consentimento = st.checkbox(
    "A pessoa autorizou o uso da foto para reconhecimento facial.",
    key=f"consentimento_{sufixo}",
)

if st.button(
    "Cadastrar foto",
    type="primary",
    icon=":material/save:",
    disabled=not (nome and consentimento),
    key=f"salvar_{sufixo}",
):
    pessoa = carregar_memoria().cadastrar(nome, codificar_jpeg(imagem), rosto.embedding)
    total = len(pessoa.fotos)
    fotos = "1 foto cadastrada" if total == 1 else f"{total} fotos cadastradas"
    st.session_state.aviso_cadastro = f"{pessoa.nome} agora tem {fotos}."
    st.session_state.cadastros_feitos += 1
    st.rerun()
