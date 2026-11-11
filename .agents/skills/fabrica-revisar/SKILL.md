---
name: fabrica-revisar
description: Revise um Short renderizado pela Fábrica de Dark. Use para inspecionar o vídeo final, suas fontes, legendas, acessibilidade e direitos de uso.
---

1. Abra a versão indicada em `episodio.json` e confira que MP4, SRT e roteiro pertencem à mesma versão. Para revisão interativa, rode `python revisar.py --episodio <pasta>` e abra o endereço local exibido.
2. Use FFprobe para conferir imagem vertical de 1080 × 1920 e trilha de áudio. Verifique se o vídeo decodifica e se os tempos das legendas estão em ordem, dentro da duração do MP4.
3. Confira a abertura, as cenas no ritmo das falas, a leitura em tamanho de celular e os termos difíceis. Valide as afirmações contra as fontes e a proveniência dos materiais.
4. Relate cada ajuste com cena, trecho e etapa responsável. Entregue a prévia e registre a versão exata que foi revisada. O painel salva decisões em `versoes/<versao>/revisao.json`. Registre aprovação quando o usuário aprovar a versão. Quando uma nova versão for renderizada, revise-a novamente.
