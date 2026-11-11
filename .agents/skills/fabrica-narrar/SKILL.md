---
name: fabrica-narrar
description: Prepare a voz Piper e ajuste a pronúncia de falas da Fábrica de Dark. Use para gerar áudio, corrigir termos técnicos ou revisar a sincronização das legendas.
---

1. Leia `falas` como o texto exibido. Use `falas_voz` com entradas alinhadas para pronúncias especiais. Use `null` nas falas cuja pronúncia segue o texto exibido.
2. Valide o roteiro e rode `main.py --roteiro <arquivo> --episodio <pasta> --somente-voz` com o Python do ambiente do projeto.
3. Leia `narracao.json` na pasta do episódio para localizar os WAVs por cena. Confira nomes, siglas, números e termos técnicos nos trechos afetados.
4. Entregue ao render a mesma pasta de episódio para reaproveitar os WAVs. O render recalcula os tempos das legendas pela duração efetiva das falas.
