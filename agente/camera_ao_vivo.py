"""Câmera ao vivo: mostra o vídeo no navegador e envia quadros para o agente.

O navegador envia um quadro, espera o Python analisá-lo e só então envia o próximo.
Quando o Python pede uma pausa (depois de reconhecer alguém), o envio para até ela acabar.
"""

from collections.abc import Callable

import streamlit as st

_CAMERA_AO_VIVO = st.components.v2.component(
    "camera_ao_vivo",
    html="""
<div class="camera">
  <video autoplay muted playsinline aria-label="Vídeo ao vivo da câmera"></video>
  <p class="status" role="status">Abrindo a câmera...</p>
</div>
""",
    css="""
.camera {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-family: var(--st-font);
  color: var(--st-text-color);
}
video {
  width: 100%;
  max-width: 480px;
  border-radius: var(--st-base-radius);
  background: var(--st-secondary-background-color);
  transform: scaleX(-1); /* espelho, como num selfie; os quadros enviados não são espelhados */
}
.status {
  margin: 0;
  font-size: 0.875rem;
}
""",
    js="""
const instancias = new WeakMap()
const MAIOR_LADO = 640
const TEMPO_MAXIMO_RESPOSTA_MS = 5000

function passo(inst) {
  const agora = Date.now()
  if (agora < inst.pausaAte) {
    const segundos = Math.ceil((inst.pausaAte - agora) / 1000)
    inst.status.textContent = `Pessoa reconhecida. Novo reconhecimento em ${segundos} s.`
    return
  }
  if (!inst.stream || inst.video.readyState < 2) return
  inst.status.textContent = "Procurando rostos..."

  const respondido = (inst.data?.ultimo_quadro ?? 0) >= inst.enviado
  const demorou = agora - inst.enviadoEm > TEMPO_MAXIMO_RESPOSTA_MS
  const intervalo = inst.data?.intervalo_ms ?? 700
  if ((!respondido && !demorou) || agora - inst.enviadoEm < intervalo) return

  const { videoWidth: largura, videoHeight: altura } = inst.video
  const escala = Math.min(1, MAIOR_LADO / Math.max(largura, altura))
  inst.canvas.width = Math.round(largura * escala)
  inst.canvas.height = Math.round(altura * escala)
  inst.canvas.getContext("2d").drawImage(inst.video, 0, 0, inst.canvas.width, inst.canvas.height)
  const imagem = inst.canvas.toDataURL("image/jpeg", 0.85).split(",")[1]

  inst.enviado += 1
  inst.enviadoEm = agora
  inst.setTriggerValue("quadro", { id: inst.enviado, imagem })
}

export default function ({ data, parentElement, setTriggerValue }) {
  let inst = instancias.get(parentElement)
  if (!inst) {
    inst = {
      video: parentElement.querySelector("video"),
      status: parentElement.querySelector(".status"),
      canvas: document.createElement("canvas"),
      enviado: data?.ultimo_quadro ?? 0,
      enviadoEm: 0,
      pausaId: null,
      pausaAte: 0,
      stream: null,
      ativo: true,
    }
    instancias.set(parentElement, inst)

    if (!navigator.mediaDevices?.getUserMedia) {
      inst.status.textContent = "Este navegador não permite acessar a câmera (use localhost ou HTTPS)."
    } else {
      navigator.mediaDevices
        .getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 } }, audio: false })
        .then((stream) => {
          if (!inst.ativo) return stream.getTracks().forEach((t) => t.stop())
          inst.stream = stream
          inst.video.srcObject = stream
        })
        .catch((erro) => {
          inst.status.textContent = `Não foi possível acessar a câmera: ${erro.message}`
        })
    }
    inst.timer = setInterval(() => passo(inst), 200)
  }

  inst.data = data
  inst.setTriggerValue = setTriggerValue
  // Só reinicia a contagem quando o Python inicia uma pausa nova.
  if (data && data.pausa_id !== inst.pausaId) {
    inst.pausaId = data.pausa_id
    inst.pausaAte = Date.now() + (data.espera_ms ?? 0)
  }

  return () => {
    inst.ativo = false
    clearInterval(inst.timer)
    inst.stream?.getTracks().forEach((t) => t.stop())
    instancias.delete(parentElement)
  }
}
""",
)


def camera_ao_vivo(
    *,
    key: str,
    ultimo_quadro: int,
    pausa_id: int,
    espera_ms: int,
    on_quadro: Callable[[], None],
    intervalo_ms: int = 700,
) -> None:
    """Mostra a câmera ao vivo. A cada quadro recebido, chama ``on_quadro``.

    O quadro fica em ``st.session_state[key].quadro`` como ``{"id", "imagem"}``,
    com a imagem JPEG em base64.
    """
    _CAMERA_AO_VIVO(
        key=key,
        data={
            "ultimo_quadro": ultimo_quadro,
            "pausa_id": pausa_id,
            "espera_ms": espera_ms,
            "intervalo_ms": intervalo_ms,
        },
        on_quadro_change=on_quadro,
    )
