"""Memória do agente: pessoas cadastradas, suas fotos e seus embeddings."""

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PASTA_DADOS = Path(__file__).resolve().parent.parent / "dados"

# Similaridade de cosseno recomendada pelos autores do SFace no OpenCV.
LIMIAR_PADRAO = 0.363


@dataclass(frozen=True)
class Foto:
    arquivo: str
    embedding: list[float]


@dataclass(frozen=True)
class Pessoa:
    id: str
    nome: str
    fotos: tuple[Foto, ...]


@dataclass(frozen=True)
class Resultado:
    nome: str | None  # None quando ninguém atinge o limiar
    similaridade: float  # maior similaridade encontrada, mesmo abaixo do limiar


def normalizar_nome(nome: str) -> str:
    return " ".join(nome.split())


def _chave(nome: str) -> str:
    return normalizar_nome(nome).casefold()


class Memoria:
    def __init__(self, pasta: Path = PASTA_DADOS) -> None:
        self._arquivo = pasta / "pessoas.json"
        self._pasta_fotos = pasta / "fotos"
        self._pasta_fotos.mkdir(parents=True, exist_ok=True)
        self._trava = threading.Lock()

    def _ler(self) -> list[Pessoa]:
        if not self._arquivo.exists():
            return []
        registros = json.loads(self._arquivo.read_text(encoding="utf-8"))
        return [
            Pessoa(r["id"], r["nome"], tuple(Foto(**f) for f in r["fotos"]))
            for r in registros
        ]

    def _gravar(self, pessoas: list[Pessoa]) -> None:
        registros = [
            {"id": p.id, "nome": p.nome, "fotos": [vars(f) for f in p.fotos]}
            for p in pessoas
        ]
        temporario = self._arquivo.with_suffix(".tmp")
        temporario.write_text(json.dumps(registros, ensure_ascii=False), encoding="utf-8")
        # O OneDrive pode bloquear o arquivo por instantes durante a sincronização.
        for tentativa in range(5):
            try:
                os.replace(temporario, self._arquivo)
                return
            except PermissionError:
                if tentativa == 4:
                    raise
                time.sleep(0.2)

    def pessoas(self) -> list[Pessoa]:
        with self._trava:
            return sorted(self._ler(), key=lambda p: _chave(p.nome))

    def caminho_foto(self, foto: Foto) -> Path:
        return self._pasta_fotos / foto.arquivo

    def cadastrar(self, nome: str, jpeg: bytes, embedding: np.ndarray) -> Pessoa:
        """Adiciona a foto à pessoa com esse nome, criando-a se ainda não existir."""
        nome = normalizar_nome(nome)
        if not nome:
            raise ValueError("O nome não pode ficar vazio.")
        foto = Foto(f"{uuid.uuid4().hex}.jpg", [float(v) for v in embedding])
        with self._trava:
            pessoas = self._ler()
            (self._pasta_fotos / foto.arquivo).write_bytes(jpeg)
            for indice, pessoa in enumerate(pessoas):
                if _chave(pessoa.nome) == _chave(nome):
                    atualizada = Pessoa(pessoa.id, pessoa.nome, (*pessoa.fotos, foto))
                    pessoas[indice] = atualizada
                    break
            else:
                atualizada = Pessoa(uuid.uuid4().hex, nome, (foto,))
                pessoas.append(atualizada)
            self._gravar(pessoas)
        return atualizada

    def remover(self, pessoa_id: str) -> None:
        with self._trava:
            pessoas = self._ler()
            for pessoa in pessoas:
                if pessoa.id == pessoa_id:
                    for foto in pessoa.fotos:
                        (self._pasta_fotos / foto.arquivo).unlink(missing_ok=True)
            self._gravar([p for p in pessoas if p.id != pessoa_id])

    def identificar(self, embedding: np.ndarray, limiar: float = LIMIAR_PADRAO) -> Resultado:
        """Compara o embedding com todas as fotos e devolve a melhor correspondência."""
        melhor_nome, melhor_similaridade = None, -1.0
        for pessoa in self.pessoas():
            matriz = np.array([foto.embedding for foto in pessoa.fotos], dtype=np.float32)
            similaridade = float((matriz @ embedding).max())
            if similaridade > melhor_similaridade:
                melhor_nome, melhor_similaridade = pessoa.nome, similaridade
        if melhor_similaridade < limiar:
            return Resultado(None, melhor_similaridade)
        return Resultado(melhor_nome, melhor_similaridade)
