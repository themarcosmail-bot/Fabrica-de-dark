# Fábrica de Dark

## Escolha da skill

Antes de editar um episódio ou executar a produção, identifique a etapa pedida e abra o `SKILL.md` correspondente. Faça isso também quando o pedido vier em linguagem natural e não citar uma skill.

| Pedido | Arquivo a ler |
| --- | --- |
| Produzir ou retomar um episódio inteiro | `.agents/skills/fabrica-orquestrar/SKILL.md` |
| Pesquisar ou checar uma afirmação | `.agents/skills/fabrica-pesquisar/SKILL.md` |
| Escrever ou ajustar o roteiro | `.agents/skills/fabrica-roteirizar/SKILL.md` |
| Planejar ou refazer o visual de uma cena | `.agents/skills/fabrica-dirigir-cenas/SKILL.md` |
| Corrigir pronúncia, refazer uma fala ou sincronizar legendas | `.agents/skills/fabrica-narrar/SKILL.md` |
| Gerar ou renderizar uma nova versão do MP4 | `.agents/skills/fabrica-renderizar/SKILL.md` |
| Conferir o episódio renderizado | `.agents/skills/fabrica-revisar/SKILL.md` |

## Correção de pronúncia

Abra primeiro `.agents/skills/fabrica-narrar/SKILL.md`. Altere somente a entrada correspondente de `falas_voz` e preserve `falas` e todos os textos visuais. Use a pasta de episódio indicada pelo usuário para reaproveitar os arquivos em cache.

Se o pedido também incluir um vídeo novo, abra `.agents/skills/fabrica-renderizar/SKILL.md` e execute a renderização após preparar a fala. Antes de responder, confirme a nova versão em `episodio.json`, o MP4 e o número de falas geradas e reutilizadas em `narracao.json`.
