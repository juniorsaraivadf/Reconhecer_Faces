# Agente de reconhecimento facial

Aplicativo Streamlit que cadastra pessoas por foto, identifica quem aparece em uma nova foto e fala o nome reconhecido.

## Como executar

Com o [uv](https://docs.astral.sh/uv/) instalado:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\streamlit.exe run streamlit_app.py
```

## Como usar

1. Em **Cadastrar**, informe o nome, tire ou envie uma foto com um único rosto e clique em **Cadastrar foto**.
2. Repita com o mesmo nome para adicionar fotos da pessoa em ângulos e iluminações diferentes.
3. Em **Identificar**, no modo **Vídeo ao vivo**, basta ficar de frente para a câmera: o agente reconhece direto do vídeo, fala o nome e espera 10 segundos antes de um novo reconhecimento. No modo **Foto**, tire ou envie uma foto. O agente mostra o resultado e fala o nome.
4. Em **Pessoas cadastradas**, veja os cadastros ou exclua uma pessoa com todas as fotos.

## Como funciona

| Etapa do agente | Arquivo | O que faz |
|---|---|---|
| Percepção | `agente/visao.py` | O YuNet localiza os rostos e o SFace converte cada um em um vetor de 128 números (embedding). |
| Memória | `agente/memoria.py` | Guarda os embeddings e compara o rosto novo por similaridade de cosseno. |
| Decisão | `agente/memoria.py` | Aceita a pessoa mais parecida se a similaridade atingir o limiar (padrão: 0,363). Abaixo disso, o rosto é tratado como não cadastrado. |
| Ação | `agente/fala.py` | Gera a fala em português com gTTS. |

O limiar pode ser ajustado na barra lateral da página **Identificar**. Valores maiores reduzem confusões entre pessoas, mas podem rejeitar quem está cadastrado.

## Publicar no Streamlit Community Cloud

1. Envie o projeto para um repositório no GitHub, incluindo a pasta `modelos/`. A pasta `dados/` fica fora por causa do `.gitignore`.
2. Em [share.streamlit.io](https://share.streamlit.io), crie o app apontando para `streamlit_app.py`.
3. Em **Advanced settings**, escolha Python 3.12.

Antes de publicar, considere:

- **Os cadastros não são permanentes.** O disco do Community Cloud é temporário, e `dados/` é apagada quando o app reinicia ou é reimplantado. Para manter os cadastros, seria preciso usar um armazenamento externo.
- **Controle quem acessa.** O app não tem login: quem abrir o link pode ver, cadastrar e excluir pessoas. Configure o app como privado e convide apenas os participantes.

## Privacidade

Fotos e embeddings faciais são dados biométricos, considerados dados pessoais sensíveis pela LGPD. Cadastre apenas quem autorizou.

- Os dados ficam em `dados/`. Se o projeto estiver em uma pasta do OneDrive, eles também são sincronizados com a nuvem.
- O gTTS envia o texto falado, que inclui o nome da pessoa, ao serviço de voz do Google. As fotos não são enviadas.

## Testes

```powershell
uv pip install --python .venv\Scripts\python.exe pytest
.venv\Scripts\python.exe -m pytest tests
```

## Créditos dos modelos

[YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) e [SFace](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface), do OpenCV Zoo. Consulte as licenças nesses links.
