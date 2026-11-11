"""Prova de vida por desafio: a pessoa vira o rosto para um lado sorteado e volta.

Uma foto (impressa ou na tela de um celular) não consegue virar o rosto, então não
passa no desafio. Um vídeo gravado da pessoa ainda pode passar se, por acaso, ela
virar para o lado sorteado no tempo certo.
"""

import random
from dataclasses import dataclass
from enum import Enum

import numpy as np

# Giro = deslocamento horizontal do nariz em relação ao meio dos olhos, dividido pela
# distância entre os olhos. De frente fica perto de 0; virado ~26° chega a 0,25.
# Inclinar uma foto plana encolhe olhos e nariz na mesma proporção, sem mudar o giro:
# só uma cabeça de verdade (em 3D) faz esse valor variar.
GIRO_MINIMO_VIRADO = 0.25
GIRO_MAXIMO_DE_FRENTE = 0.15
TEMPO_LIMITE_S = 8.0

DIRECOES = ("esquerda", "direita")


def estimar_giro(olho_1: np.ndarray, olho_2: np.ndarray, nariz: np.ndarray) -> float:
    """Estima o giro horizontal do rosto a partir de três pontos da imagem (x, y).

    Valores positivos: o nariz aponta para a direita da imagem, o que, numa câmera
    voltada para a pessoa, é a esquerda dela.
    """
    distancia = abs(float(olho_1[0] - olho_2[0]))
    if distancia < 1:
        return 0.0
    meio = (float(olho_1[0]) + float(olho_2[0])) / 2
    return (float(nariz[0]) - meio) / distancia


class Situacao(Enum):
    AGUARDANDO = "aguardando"
    APROVADO = "aprovado"
    REPROVADO = "reprovado"


@dataclass
class Desafio:
    nome: str
    direcao: str  # "esquerda" ou "direita", do ponto de vista da pessoa
    prazo: float  # instante limite, em segundos (time.time())
    girou: bool = False

    @classmethod
    def sortear(cls, nome: str, agora: float) -> "Desafio":
        return cls(nome, random.choice(DIRECOES), agora + TEMPO_LIMITE_S)

    @property
    def instrucao(self) -> str:
        return f"Vire o rosto para a {self.direcao} e depois volte a olhar para a câmera."

    def avaliar(self, rostos: list[tuple[str | None, float]], agora: float) -> Situacao:
        """Avança o desafio com os rostos de um quadro, cada um como (nome, giro)."""
        if agora > self.prazo:
            return Situacao.REPROVADO
        sinal = 1 if self.direcao == "esquerda" else -1
        if not self.girou:
            self.girou = any(giro * sinal >= GIRO_MINIMO_VIRADO for _, giro in rostos)
            return Situacao.AGUARDANDO
        # Depois de virar, a mesma pessoa precisa voltar de frente e ser reconhecida.
        if any(nome == self.nome and abs(giro) <= GIRO_MAXIMO_DE_FRENTE for nome, giro in rostos):
            return Situacao.APROVADO
        return Situacao.AGUARDANDO
