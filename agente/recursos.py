"""Recursos compartilhados pelas páginas do Streamlit."""

import base64

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from agente.fala import sintetizar
from agente.memoria import Memoria
from agente.visao import Visao

TAMANHO_MAXIMO_FOTO_MB = 15

# O autoplay do st.audio não toca de novo quando a mesma pessoa é reconhecida em
# seguida e pode reiniciar a fala. Aqui, cada identificador de fala toca uma só vez.
_REPRODUTOR_DE_FALA = st.components.v2.component(
    "reprodutor_de_fala",
    js="""
export default function ({ data }) {
  if (!data || window.__ultimaFala === data.id) return
  window.__ultimaFala = data.id
  window.__audioFala?.pause()
  window.__audioFala = new Audio("data:audio/mpeg;base64," + data.audio)
  // Se o navegador bloquear, o usuário ainda tem o player visível na página.
  window.__audioFala.play().catch(() => {})
}
""",
)


def falar(audio: bytes, identificador: str) -> None:
    """Toca o áudio automaticamente, uma vez para cada identificador."""
    _REPRODUTOR_DE_FALA(
        data={"id": identificador, "audio": base64.b64encode(audio).decode("ascii")},
        key="reprodutor_de_fala",
    )


@st.cache_resource(show_spinner="Carregando os modelos de reconhecimento...")
def carregar_visao() -> Visao:
    return Visao()


@st.cache_resource
def carregar_memoria() -> Memoria:
    return Memoria()


@st.cache_data(show_spinner=False, max_entries=200)
def gerar_audio(frase: str) -> bytes:
    return sintetizar(frase)


def capturar_foto(chave: str) -> UploadedFile | None:
    """Mostra a escolha entre câmera e arquivo e devolve a foto obtida."""
    origem = st.segmented_control(
        "Origem da foto",
        ["Câmera", "Arquivo"],
        default="Câmera",
        required=True,
        key=f"origem_{chave}",
    )
    if origem == "Câmera":
        return st.camera_input("Tire uma foto", key=f"camera_{chave}")
    return st.file_uploader(
        "Escolha uma foto",
        type=["jpg", "jpeg", "png"],
        max_upload_size=TAMANHO_MAXIMO_FOTO_MB,
        key=f"arquivo_{chave}",
    )
