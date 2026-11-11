import base64
import time

import numpy as np
import streamlit as st
from gtts.tts import gTTSError

from agente.camera_ao_vivo import camera_ao_vivo
from agente.fala import montar_frase
from agente.memoria import LIMIAR_PADRAO, Resultado
from agente.prova_de_vida import Desafio, Situacao
from agente.recursos import (
    capturar_foto,
    carregar_memoria,
    carregar_visao,
    falar,
    gerar_audio,
)
from agente.visao import ImagemInvalida, Rosto, codificar_jpeg, decodificar_imagem, desenhar_rostos

VERDE, VERMELHO = (80, 175, 76), (54, 67, 244)  # BGR
PAUSA_APOS_RECONHECER_S = 10
PAUSA_APOS_FALHA_S = 3
INTERVALO_NORMAL_MS = 700
INTERVALO_DESAFIO_MS = 300  # mais quadros durante o desafio, para captar o giro
CHAVE_VIDEO = "video_identificar"


def analisar(imagem: np.ndarray, limiar: float) -> tuple[list[Rosto], list[Resultado]]:
    rostos = carregar_visao().perceber(imagem)
    return rostos, [carregar_memoria().identificar(rosto.embedding, limiar) for rosto in rostos]


def marcar(imagem: np.ndarray, rostos: list[Rosto], resultados: list[Resultado]) -> np.ndarray:
    cores = [VERDE if resultado.nome else VERMELHO for resultado in resultados]
    return desenhar_rostos(imagem, rostos, cores)


def exibir_resultados(resultados: list[Resultado], limiar: float) -> None:
    for numero, resultado in enumerate(resultados, start=1):
        prefixo = f"Rosto {numero}: " if len(resultados) > 1 else ""
        similaridade = f"Similaridade: {resultado.similaridade:.2f} (limiar: {limiar:.2f})"
        if resultado.nome:
            st.success(similaridade, title=f"{prefixo}{resultado.nome}", icon=":material/check_circle:")
        else:
            st.error(similaridade, title=f"{prefixo}pessoa não cadastrada", icon=":material/person_off:")


def aviso_sem_voz() -> None:
    st.warning(
        "Não foi possível gerar a voz. Verifique a conexão com a internet.",
        icon=":material/volume_off:",
    )


def preparar_fala(frase: str, identificador: str) -> tuple[str, str, bytes] | None:
    try:
        return identificador, frase, gerar_audio(frase)
    except gTTSError:
        return None


def novo_estado_video() -> dict:
    return {
        "ultimo_quadro": 0,
        "pausa_id": 0,
        "pausado_ate": 0.0,
        "limiar": LIMIAR_PADRAO,
        "resultados": [],
        "imagem": None,  # JPEG do último quadro com rostos marcados
        "desafio": None,  # Desafio em andamento
        "fala_desafio": None,  # (identificador, frase, áudio) da instrução do desafio
        "falhou_ate": 0.0,  # depois de uma falha, espera um pouco antes de novo desafio
        "fala": None,  # (identificador, frase, áudio) do último reconhecimento
        "sem_voz": False,
    }


def ao_receber_quadro() -> None:
    """Analisa o quadro da câmera: reconhece, aplica a prova de vida, fala e pausa."""
    estado = st.session_state.video_estado
    quadro = st.session_state[CHAVE_VIDEO].quadro
    if not quadro:
        return
    estado["ultimo_quadro"] = quadro["id"]
    agora = time.time()
    if agora < estado["pausado_ate"]:
        return

    try:
        imagem = decodificar_imagem(base64.b64decode(quadro["imagem"]))
    except ValueError:  # base64 corrompido ou ImagemInvalida
        return

    limiar = st.session_state.get("limiar", LIMIAR_PADRAO)
    rostos, resultados = analisar(imagem, limiar)
    estado["limiar"] = limiar
    estado["resultados"] = resultados
    estado["imagem"] = codificar_jpeg(marcar(imagem, rostos, resultados)) if rostos else None

    desafio: Desafio | None = estado["desafio"]
    if desafio is None:
        if agora < estado["falhou_ate"]:
            return
        reconhecidos = [(r, res) for r, res in zip(rostos, resultados) if res.nome]
        if not reconhecidos:
            return
        # Um desafio por vez, para a pessoa mais próxima da câmera (maior rosto).
        _, resultado = max(reconhecidos, key=lambda par: par[0].caixa[2] * par[0].caixa[3])
        assert resultado.nome is not None
        desafio = Desafio.sortear(resultado.nome, agora)
        estado["desafio"] = desafio
        estado["fala_desafio"] = preparar_fala(desafio.instrucao, f"desafio:{desafio.prazo}")
        return

    situacao = desafio.avaliar(
        [(res.nome, rosto.giro) for rosto, res in zip(rostos, resultados)], agora
    )
    if situacao is Situacao.AGUARDANDO:
        return
    estado["desafio"] = estado["fala_desafio"] = None
    if situacao is Situacao.REPROVADO:
        estado["falhou_ate"] = agora + PAUSA_APOS_FALHA_S
        return

    frase = montar_frase([desafio.nome])
    estado["pausa_id"] += 1
    estado["fala"] = preparar_fala(frase, f"video:{estado['pausa_id']}:{frase}")
    estado["sem_voz"] = estado["fala"] is None
    # A espera começa depois de a voz ficar pronta, para durar os 10 s inteiros.
    estado["pausado_ate"] = time.time() + PAUSA_APOS_RECONHECER_S


@st.fragment
def reconhecer_pelo_video() -> None:
    # Cada quadro reexecuta só este fragmento, não a página inteira.
    estado = st.session_state.video_estado
    desafio: Desafio | None = estado["desafio"]
    agora = time.time()
    camera_ao_vivo(
        key=CHAVE_VIDEO,
        ultimo_quadro=estado["ultimo_quadro"],
        pausa_id=estado["pausa_id"],
        espera_ms=max(0, round((estado["pausado_ate"] - agora) * 1000)),
        on_quadro=ao_receber_quadro,
        intervalo_ms=INTERVALO_DESAFIO_MS if desafio else INTERVALO_NORMAL_MS,
        mensagem=desafio.instrucao if desafio else "",
    )

    # Durante o desafio, o nome não aparece: só é revelado depois da prova de vida.
    if desafio:
        st.info(desafio.instrucao, title="Prova de vida", icon=":material/frame_person:")
        if estado["fala_desafio"]:
            identificador, _, audio = estado["fala_desafio"]
            falar(audio, identificador)
        return
    if agora < estado["falhou_ate"]:
        st.warning(
            "O rosto não foi virado a tempo. Olhe para a câmera para tentar de novo.",
            title="Prova de vida não concluída",
            icon=":material/gpp_bad:",
        )
        return

    if estado["resultados"]:
        exibir_resultados(estado["resultados"], estado["limiar"])
    if estado["imagem"]:
        st.image(
            estado["imagem"],
            width=420,
            alt=f"Quadro analisado com {len(estado['resultados'])} rosto(s) marcado(s)",
        )

    pausado = agora < estado["pausado_ate"]
    if pausado and estado["sem_voz"]:
        aviso_sem_voz()
    if pausado and estado["fala"]:
        identificador, frase, audio = estado["fala"]
        st.audio(audio, format="audio/mpeg", alt=frase)
        falar(audio, identificador)


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

modo = st.segmented_control(
    "Modo de identificação",
    ["Vídeo ao vivo", "Foto"],
    default="Vídeo ao vivo",
    required=True,
    key="modo_identificar",
    help=(
        "No vídeo ao vivo, o agente pede para virar o rosto (prova de vida), fala o nome "
        f"e espera {PAUSA_APOS_RECONHECER_S} segundos antes de reconhecer de novo."
    ),
)

if modo == "Vídeo ao vivo":
    if "video_estado" not in st.session_state:
        st.session_state.video_estado = novo_estado_video()
    reconhecer_pelo_video()
    st.stop()

# Ao voltar para o vídeo, começa do zero, sem pausa, desafio ou resultado antigo.
st.session_state.pop("video_estado", None)

st.caption(
    ":material/warning: O modo Foto não tem prova de vida: uma foto de outra foto "
    "também é reconhecida."
)
foto = capturar_foto("identificar")
if foto is None:
    st.stop()

try:
    imagem = decodificar_imagem(foto.getvalue())
except ImagemInvalida as erro:
    st.error(str(erro), icon=":material/error:")
    st.stop()

rostos, resultados = analisar(imagem, limiar)
if not rostos:
    st.warning(
        "Nenhum rosto encontrado. Tente uma foto mais iluminada e de frente.",
        icon=":material/warning:",
    )
    st.stop()

exibir_resultados(resultados, limiar)
st.image(
    marcar(imagem, rostos, resultados),
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
        aviso_sem_voz()
    else:
        st.audio(audio, format="audio/mpeg", alt=frase)
        falar(audio, f"{foto.file_id}:{frase}")
