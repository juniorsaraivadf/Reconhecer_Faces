import streamlit as st
from gtts.tts import gTTSError

from agente.fala import montar_frase
from agente.memoria import LIMIAR_PADRAO
from agente.recursos import (
    capturar_foto,
    carregar_memoria,
    carregar_visao,
    falar,
    gerar_audio,
)
from agente.visao import ImagemInvalida, decodificar_imagem, desenhar_rostos

VERDE, VERMELHO = (80, 175, 76), (54, 67, 244)  # BGR

st.header("Identificar pessoa")
st.caption("Mostre um rosto ao agente: ele compara com os cadastros e fala o nome.")

memoria = carregar_memoria()
if not memoria.pessoas():
    st.info("Cadastre pelo menos uma pessoa para começar.", icon=":material/info:")
    st.page_link("app_pages/cadastrar.py", label="Ir para o cadastro", icon=":material/person_add:")
    st.stop()

limiar = st.sidebar.slider(
    "Limiar de similaridade",
    min_value=0.20,
    max_value=0.80,
    value=LIMIAR_PADRAO,
    step=0.01,
    key="limiar",
    help="Valores maiores evitam confundir pessoas, mas podem rejeitar quem está cadastrado.",
)

foto = capturar_foto("identificar")
if foto is None:
    st.stop()

conteudo = foto.getvalue()
try:
    imagem = decodificar_imagem(conteudo)
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

resultados = [memoria.identificar(rosto.embedding, limiar) for rosto in rostos]
cores = [VERDE if resultado.nome else VERMELHO for resultado in resultados]

for numero, resultado in enumerate(resultados, start=1):
    prefixo = f"Rosto {numero}: " if len(resultados) > 1 else ""
    similaridade = f"Similaridade: {resultado.similaridade:.2f} (limiar: {limiar:.2f})"
    if resultado.nome:
        st.success(similaridade, title=f"{prefixo}{resultado.nome}", icon=":material/check_circle:")
    else:
        st.error(similaridade, title=f"{prefixo}pessoa não cadastrada", icon=":material/person_off:")

st.image(
    desenhar_rostos(imagem, rostos, cores),
    channels="BGR",
    width=420,
    alt=f"Foto analisada com {len(rostos)} rosto(s) marcado(s)",
)

nomes = [resultado.nome for resultado in resultados if resultado.nome]
if nomes:
    frase = montar_frase(nomes)
    try:
        with st.spinner("Preparando a voz..."):
            audio = gerar_audio(frase)
    except gTTSError:
        st.warning(
            "Não foi possível gerar a voz. Verifique a conexão com a internet.",
            icon=":material/volume_off:",
        )
    else:
        st.audio(audio, format="audio/mpeg", alt=frase)
        falar(audio, f"{foto.file_id}:{frase}")
