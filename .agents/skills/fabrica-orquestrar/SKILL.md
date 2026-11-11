---
name: fabrica-orquestrar
description: Coordene a produção, retomada ou correção de um episódio completo da Fábrica de Dark. Use quando o usuário pedir o Short inteiro ou quiser retomar uma produção.
---

1. Identifique tema, série e formato. Use `episodios/<nome>/` como pasta de trabalho.
2. Leia `episodio.json` se existir para localizar a última versão renderizada. Preserve as versões anteriores e use a mesma pasta para reutilizar mídias.
3. Para um episódio novo, pesquise, escreva o roteiro e dirija as cenas. Para um ajuste, localize a versão de origem e altere só o arquivo ou a etapa afetada.
4. Valide o roteiro com `main.py --roteiro <arquivo> --checar-roteiro`. Prepare a voz ou renderize conforme o pedido, usando as instruções das skills da etapa.
5. Revise o resultado. Entregue o MP4, as legendas, o roteiro e as fontes. Informe o que ainda precisa de conferência humana.

A saída desta produção tem estado `aguardando-revisao`. Preserve esse estado até uma aprovação explícita da versão exibida. Leia o README para os comandos de execução no Windows.
