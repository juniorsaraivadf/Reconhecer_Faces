import numpy as np
import pytest

from agente.fala import montar_frase
from agente.memoria import LIMIAR_PADRAO, Memoria, normalizar_nome
from agente.visao import ImagemInvalida, Visao, decodificar_imagem


def vetor(*valores: float) -> np.ndarray:
    v = np.array(valores, dtype=np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def memoria(tmp_path):
    return Memoria(tmp_path)


def test_normaliza_espacos_do_nome():
    assert normalizar_nome("  Ana   Maria ") == "Ana Maria"


def test_nome_vazio_e_rejeitado(memoria):
    with pytest.raises(ValueError):
        memoria.cadastrar("   ", b"x", vetor(1, 0))


def test_mesmo_nome_acumula_fotos(memoria):
    memoria.cadastrar("Conceição", b"x", vetor(1, 0))
    pessoa = memoria.cadastrar("  conceição ", b"y", vetor(0, 1))
    assert pessoa.nome == "Conceição"
    assert len(pessoa.fotos) == 2
    assert len(memoria.pessoas()) == 1


def test_identifica_pela_foto_mais_parecida(memoria):
    memoria.cadastrar("Ana", b"x", vetor(1, 0, 0))
    memoria.cadastrar("Ana", b"x", vetor(0, 1, 0))
    memoria.cadastrar("Bia", b"x", vetor(0, 0, 1))
    assert memoria.identificar(vetor(0.1, 1, 0)).nome == "Ana"
    assert memoria.identificar(vetor(0, 0.1, 1)).nome == "Bia"


def test_rosto_abaixo_do_limiar_nao_recebe_nome(memoria):
    memoria.cadastrar("Ana", b"x", vetor(1, 0))
    resultado = memoria.identificar(vetor(0, 1))
    assert resultado.nome is None
    assert resultado.similaridade < LIMIAR_PADRAO


def test_memoria_vazia_nao_identifica(memoria):
    assert memoria.identificar(vetor(1, 0)).nome is None


def test_remover_apaga_cadastro_e_arquivos(memoria, tmp_path):
    pessoa = memoria.cadastrar("Ana", b"x", vetor(1, 0))
    caminho = memoria.caminho_foto(pessoa.fotos[0])
    assert caminho.exists()
    memoria.remover(pessoa.id)
    assert memoria.pessoas() == []
    assert not caminho.exists()


def test_cadastro_persiste_entre_instancias(tmp_path):
    Memoria(tmp_path).cadastrar("José", b"x", vetor(1, 0))
    assert Memoria(tmp_path).pessoas()[0].nome == "José"


@pytest.mark.parametrize(
    ("nomes", "esperado"),
    [
        (["Ana"], "Pessoa reconhecida: Ana."),
        (["Ana", "Ana"], "Pessoa reconhecida: Ana."),
        (["Ana", "Bia"], "Pessoas reconhecidas: Ana e Bia."),
        (["Ana", "Bia", "Caio"], "Pessoas reconhecidas: Ana, Bia e Caio."),
    ],
)
def test_frase_falada(nomes, esperado):
    assert montar_frase(nomes) == esperado


def test_bytes_invalidos_sao_rejeitados():
    with pytest.raises(ImagemInvalida):
        decodificar_imagem(b"isto nao e uma imagem")


def test_imagem_sem_rosto_nao_gera_deteccao():
    assert Visao().perceber(np.full((400, 400, 3), 127, np.uint8)) == []
