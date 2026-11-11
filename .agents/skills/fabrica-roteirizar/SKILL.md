---
name: fabrica-roteirizar
description: Escreva ou ajuste o roteiro em português de um Short da Fábrica de Dark. Use após a pesquisa ou quando o usuário fornecer um roteiro próprio.
---

1. Leia a pesquisa ou o roteiro enviado. Defina uma pergunta de abertura, o problema concreto e o desfecho que responde à abertura.
2. Escreva falas curtas e naturais em português brasileiro. Use o esquema do exemplo `exemplos/motores-iconicos-01.json` e preserve o campo `fontes`.
3. Envie ao estágio visual um texto por cena ou, se o visual já estiver escolhido, uma lista `falas` por cena. Mantenha cada fala documental com até 74 caracteres.
4. Entregue o roteiro JSON. Antes de renderizar, valide-o com `main.py --roteiro <arquivo> --checar-roteiro`.
