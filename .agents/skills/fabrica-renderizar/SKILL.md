---
name: fabrica-renderizar
description: Renderize ou refaça o MP4 de um episódio da Fábrica de Dark. Use quando houver roteiro JSON e for necessário gerar uma nova versão do vídeo.
---

1. Valide o roteiro com `main.py --roteiro <arquivo> --checar-roteiro`.
2. Rode `main.py --roteiro <arquivo> --episodio <pasta>` com o Python do ambiente do projeto e as dependências do README.
3. Use a mesma pasta em revisões do episódio. O programa reutiliza falas e clipes documentais compatíveis e compõe o MP4 final novamente.
4. Entregue a versão indicada em `episodio.json` com MP4, SRT, roteiro e fontes. Confira o relatório de itens gerados e reutilizados quando o pedido for parcial.
