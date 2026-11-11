"""Percepção do agente: encontra rostos e os transforma em embeddings.

Usa dois modelos ONNX do OpenCV Zoo: YuNet (detecção) e SFace (reconhecimento).
"""

import threading
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from agente.prova_de_vida import estimar_giro

PASTA_MODELOS = Path(__file__).resolve().parent.parent / "modelos"
MODELO_DETECTOR = PASTA_MODELOS / "face_detection_yunet_2023mar.onnx"
MODELO_RECONHECEDOR = PASTA_MODELOS / "face_recognition_sface_2021dec.onnx"

CONFIANCA_MINIMA_DETECCAO = 0.8
MAIOR_LADO_IMAGEM = 1280
LADO_MINIMO_ROSTO_CADASTRO = 60


class ImagemInvalida(ValueError):
    """Os bytes recebidos não formam uma imagem legível."""


@dataclass(frozen=True)
class Rosto:
    caixa: tuple[int, int, int, int]  # x, y, largura, altura
    embedding: np.ndarray  # vetor de norma 1
    confianca: float
    giro: float = 0.0  # giro horizontal estimado; veja agente.prova_de_vida.estimar_giro


def decodificar_imagem(conteudo: bytes) -> np.ndarray:
    """Converte bytes em imagem BGR, respeitando a orientação EXIF."""
    imagem = cv2.imdecode(np.frombuffer(conteudo, np.uint8), cv2.IMREAD_COLOR)
    if imagem is None:
        raise ImagemInvalida("Não foi possível ler a imagem.")
    maior_lado = max(imagem.shape[:2])
    if maior_lado > MAIOR_LADO_IMAGEM:
        escala = MAIOR_LADO_IMAGEM / maior_lado
        imagem = cv2.resize(imagem, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    return imagem


def codificar_jpeg(imagem: np.ndarray) -> bytes:
    sucesso, buffer = cv2.imencode(".jpg", imagem, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not sucesso:
        raise ImagemInvalida("Não foi possível salvar a imagem.")
    return buffer.tobytes()


def desenhar_rostos(
    imagem: np.ndarray, rostos: list[Rosto], cores: list[tuple[int, int, int]]
) -> np.ndarray:
    """Devolve uma cópia da imagem com cada rosto numerado a partir de 1."""
    copia = imagem.copy()
    espessura = max(2, max(imagem.shape[:2]) // 300)
    for numero, (rosto, cor) in enumerate(zip(rostos, cores), start=1):
        x, y, largura, altura = rosto.caixa
        cv2.rectangle(copia, (x, y), (x + largura, y + altura), cor, espessura)
        cv2.putText(
            copia,
            str(numero),
            (x, max(y - 8, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            espessura * 0.4,
            cor,
            espessura,
        )
    return copia


class Visao:
    def __init__(self) -> None:
        # Carrega por buffer: no Windows, o OpenCV não abre caminhos com acentos.
        sem_config = np.empty(0, np.uint8)
        self._detector = cv2.FaceDetectorYN.create(
            "onnx",
            np.fromfile(MODELO_DETECTOR, np.uint8),
            sem_config,
            (320, 320),
            CONFIANCA_MINIMA_DETECCAO,
        )
        self._reconhecedor = cv2.FaceRecognizerSF.create(
            "onnx", np.fromfile(MODELO_RECONHECEDOR, np.uint8), sem_config
        )
        # Os modelos são compartilhados entre sessões e guardam estado interno.
        self._trava = threading.Lock()

    def perceber(self, imagem: np.ndarray) -> list[Rosto]:
        """Devolve os rostos da imagem, ordenados da esquerda para a direita."""
        altura, largura = imagem.shape[:2]
        rostos = []
        with self._trava:
            self._detector.setInputSize((largura, altura))
            _, deteccoes = self._detector.detect(imagem)
            for deteccao in deteccoes if deteccoes is not None else []:
                alinhado = self._reconhecedor.alignCrop(imagem, deteccao)
                vetor = self._reconhecedor.feature(alinhado).flatten().astype(np.float32)
                x, y, w, h = (int(v) for v in deteccao[:4])
                # Pontos do YuNet: dois olhos, ponta do nariz e cantos da boca.
                giro = estimar_giro(deteccao[4:6], deteccao[6:8], deteccao[8:10])
                rostos.append(
                    Rosto(
                        (x, y, w, h),
                        vetor / np.linalg.norm(vetor),
                        float(deteccao[-1]),
                        giro,
                    )
                )
        return sorted(rostos, key=lambda rosto: rosto.caixa[0])
