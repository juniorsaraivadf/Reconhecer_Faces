import numpy as np
import pytest

from agente.fala import montar_frase
from agente.memoria import LIMIAR_PADRAO, Memoria, normalizar_nome
from agente.prova_de_vida import TEMPO_LIMITE_S, Desafio, Situacao, estimar_giro
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


def ponto(x: float, y: float) -> np.ndarray:
    return np.array([x, y], dtype=np.float32)


def test_giro_de_frente_e_virado():
    olho_1, olho_2 = ponto(40, 50), ponto(60, 50)
    assert estimar_giro(olho_1, olho_2, ponto(50, 60)) == pytest.approx(0)
    assert estimar_giro(olho_1, olho_2, ponto(58, 60)) == pytest.approx(0.4)
    assert estimar_giro(olho_2, olho_1, ponto(42, 60)) == pytest.approx(-0.4)


def test_giro_com_olhos_sobrepostos_nao_quebra():
    assert estimar_giro(ponto(50, 50), ponto(50, 50), ponto(70, 60)) == 0


def test_desafio_aprovado_ao_virar_e_voltar():
    desafio = Desafio("Ana", "esquerda", prazo=10)
    assert desafio.avaliar([("Ana", 0.0)], agora=1) is Situacao.AGUARDANDO
    assert desafio.avaliar([(None, 0.5)], agora=2) is Situacao.AGUARDANDO
    assert desafio.avaliar([("Ana", 0.05)], agora=3) is Situacao.APROVADO


def test_desafio_ignora_lado_errado():
    desafio = Desafio("Ana", "direita", prazo=10)
    desafio.avaliar([("Ana", 0.5)], agora=1)  # virou para a esquerda
    assert desafio.avaliar([("Ana", 0.0)], agora=2) is Situacao.AGUARDANDO


def test_desafio_exige_a_mesma_pessoa_na_volta():
    desafio = Desafio("Ana", "direita", prazo=10)
    desafio.avaliar([("Ana", -0.5)], agora=1)
    assert desafio.avaliar([("Bia", 0.0)], agora=2) is Situacao.AGUARDANDO


def test_foto_parada_e_reprovada_no_prazo():
    desafio = Desafio.sortear("Ana", agora=0)
    for segundo in range(int(TEMPO_LIMITE_S) + 1):
        assert desafio.avaliar([("Ana", 0.02)], agora=segundo) is Situacao.AGUARDANDO
    assert desafio.avaliar([("Ana", 0.02)], agora=TEMPO_LIMITE_S + 0.1) is Situacao.REPROVADO
