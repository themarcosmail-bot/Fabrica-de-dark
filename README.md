# Fábrica de Dark

Esteira local para criar Shorts em português. Ela recebe um tema ou um roteiro JSON e gera um MP4 vertical com narração, cartões tipográficos e legendas por cena.

[Assistir ao Short de demonstração](exemplos/primeiro-short.mp4). Os cartões são desenhados pelo programa e a narração usa a voz brasileira [Faber](https://huggingface.co/rhasspy/piper-voices/blob/main/pt/pt_BR/faber/medium/MODEL_CARD).

## Primeiro Short no Windows

Instale o [Python 3.12](https://www.python.org/downloads/windows/) e uma compilação do [FFmpeg](https://ffmpeg.org/download.html) com `libx264`. Abra o PowerShell na pasta do projeto e confirme que `py` e `ffmpeg` estão disponíveis. Se tiver Python 3.11, troque `-3.12` por `-3.11` nos comandos.

```powershell
py -3.12 --version
ffmpeg -version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.json config.json
New-Item -ItemType Directory -Force models | Out-Null
.\.venv\Scripts\python.exe -m piper.download_voices --data-dir models pt_BR-faber-medium
.\.venv\Scripts\python.exe main.py --roteiro exemplos/primeiro-short.json
```

O download da voz exige internet. Depois de instalar as dependências e baixar a voz, o exemplo acima roda localmente com o roteiro já incluso. Para usar outra voz, ajuste `piper_model` no `config.json`. Confira as condições de uso do modelo antes de publicar a narração.

## Gerar a partir de um tema

Instale e abra o [Ollama](https://ollama.com/download/windows). No PowerShell, baixe o modelo e execute a esteira.

```powershell
ollama pull qwen2.5:3b
.\.venv\Scripts\python.exe main.py "Por que o céu muda de cor ao entardecer?"
```

O Ollama escreve o roteiro a partir do tema. Confira as afirmações antes de publicar. Para usar um roteiro pesquisado no ChatGPT ou no Codex, siga o JSON de exemplo e use `--roteiro`. O campo opcional `fontes` fica preservado no arquivo exportado.

## Piloto de Motores Icônicos

O episódio sobre o motor rotativo da Mazda usa animação própria, ilustrações esquemáticas e legendas embutidas por fala. Usa as mesmas dependências do primeiro Short.

```powershell
.\.venv\Scripts\python.exe main.py --roteiro exemplos/motores-iconicos-01.json
```

O campo opcional `serie` define o texto no topo. As cenas documentais usam um objeto `visual` com `tipo`, `titulo` e `chamada`, além da lista `falas` com os trechos a narrar. O exemplo combina os visuais `impacto`, `origem`, `mecanica`, `cosmo` e `lemans`. Também é possível combinar cenas documentais e cartões tipográficos no mesmo roteiro.

## Arquivos gerados

Cada execução concluída cria uma pasta em `saida/` com:

- `video_final.mp4` em 1080 × 1920, com áudio AAC.
- `legendas.srt` com uma entrada por fala no modo documental ou por cena nos cartões.
- `roteiro.json` com os textos usados e as fontes fornecidas.

O painel de revisão, a fila de produção e a integração com o YouTube ficam para versões futuras.
