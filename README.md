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

O campo opcional `serie` define o texto no topo. As cenas documentais usam um objeto `visual` com `tipo`, `titulo` e `chamada`, além da lista `falas` com os trechos a narrar. `linha-tempo` recebe `itens` com `marco`, `titulo` e `detalhe`. `contagem-rotores` recebe `quantidade` e `rotulo`, e pode usar a ilustração `cosmo-sport` para dois rotores. Use `impacto` e `mecanica` para mostrar o rotor do Wankel. É possível combinar cenas documentais e cartões tipográficos no mesmo roteiro.

## Produzir e revisar um episódio

As [skills do projeto](.agents/skills) orientam pesquisa, roteiro, direção visual, narração, renderização e revisão. Abra o repositório no Codex e peça, por exemplo, **“Use a Fábrica de Dark para produzir um Short de Motores Icônicos sobre o rotativo da Mazda.”** Também dá para executar o roteiro de exemplo no PowerShell:

```powershell
.\.venv\Scripts\python.exe main.py --roteiro exemplos/motores-iconicos-01.json --checar-roteiro
.\.venv\Scripts\python.exe main.py --roteiro exemplos/motores-iconicos-01.json --episodio episodios/mazda --somente-voz
.\.venv\Scripts\python.exe main.py --roteiro exemplos/motores-iconicos-01.json --episodio episodios/mazda
```

`episodios/mazda/narracao.json` lista os arquivos de áudio. `episodios/mazda/episodio.json` aponta para o MP4, as legendas e o roteiro da versão mais recente e mostra quantas falas e cenas foram reutilizadas. Cada render deixa uma versão em `versoes/` com estado `aguardando-revisao`.

Para corrigir uma cena, edite uma cópia do roteiro e renderize com a mesma pasta de episódio. Para corrigir apenas a pronúncia, use `falas_voz` na cena. Por exemplo, `[null, "A ideia do rotativo era de Félix Vânkel."]` usa a grafia alternativa na segunda fala e mantém a legenda original. Um ajuste visual reaproveita os áudios e as demais cenas documentais. O MP4 completo é recomposto a cada revisão.

## Arquivos gerados

Sem `--episodio`, cada execução concluída cria uma pasta em `saida/` com:

- `video_final.mp4` em 1080 × 1920, com áudio AAC.
- `legendas.srt` com uma entrada por fala no modo documental ou por cena nos cartões.
- `roteiro.json` com os textos usados e as fontes fornecidas.

## Revisar no painel local

Após gerar um episódio com `--episodio`, inicie o painel apontando para a mesma pasta:

```powershell
.\.venv\Scripts\python.exe revisar.py --episodio episodios/mazda
```

Abra `http://127.0.0.1:8765/` no navegador deste computador. Escolha a versão, assista ao vídeo, confira as fontes e baixe o roteiro ou as legendas. Use **Pedir ajustes** para salvar as notas ou **Aprovar versão** para registrar a aprovação local.

A decisão fica em `versoes/<versao>/revisao.json`. Cada versão tem seu próprio registro. Uma nova renderização começa aguardando revisão. A fila de produção e a integração com o YouTube ficam para versões futuras.
