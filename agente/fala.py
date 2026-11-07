"""Ação do agente: transforma os nomes reconhecidos em voz."""

import io

from gtts import gTTS


def montar_frase(nomes: list[str]) -> str:
    """Monta a frase falada, sem repetir nomes."""
    unicos = list(dict.fromkeys(nomes))
    if len(unicos) == 1:
        return f"Pessoa reconhecida: {unicos[0]}."
    return f"Pessoas reconhecidas: {', '.join(unicos[:-1])} e {unicos[-1]}."


def sintetizar(frase: str) -> bytes:
    """Gera um MP3 da frase em português do Brasil (requer internet)."""
    audio = io.BytesIO()
    gTTS(frase, lang="pt", tld="com.br").write_to_fp(audio)
    return audio.getvalue()
