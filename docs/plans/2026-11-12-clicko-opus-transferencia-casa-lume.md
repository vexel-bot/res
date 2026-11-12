# Opus 5.5 · transferência da ÓRBITA para Casa Lume

## Detecção visual

O conector da Clicko enviou à Anthropic os mesmos quatro PNGs de 300 px do ensaio local. Cada imagem foi enviada em uma chamada independente, com a mesma pergunta e sem nome de arquivo, resposta anterior ou gabarito. O Opus acertou os quatro casos. O SmolVLM havia acertado um.

| Quadro | Esperado | Opus |
| --- | --- | --- |
| ÓRBITA original em 2,625 s | Colisão | Sim |
| ÓRBITA original em 3,25 s | Livre | Não |
| ÓRBITA corrigida em 2,625 s | Livre, sem texto | Não |
| ÓRBITA corrigida em 3,375 s | Livre, texto acima da moldura | Não |

Zero falsos positivos em três controles. A amostra mede esse exercício e é pequena para estimar a taxa em outros vídeos.

## Edição autônoma no EffectCraft

O Opus recebeu a mesma semente visual, o mesmo briefing de seis segundos, a ficha consultável da ÓRBITA e dois sons opcionais sintetizados localmente. As alternativas e o gabarito do teste anterior ficaram fora do prompt. O Opus consultou a ficha, inspecionou a semente, editou cinco lotes, revisou a timeline e chamou `finish_project`. A retomada usou a prévia e o rascunho do próprio modelo. O render foi produzido sem edição manual.

- As portas e os frisos mantiveram seus deslocamentos laterais locais, chaves em 0,625 s e 2,125 s e curvas originais, com um rig de recuo adicional.
- O nome entra em 2,208 s na faixa inferior, depois da abertura. Aos 2,5 s está legível a 300 px. A categoria entra em 2,583 s. O convite entra em 3 s e fica estável por volta de 3,3 s.
- A moldura abre junto com a elevação da luz. Os quadros de 0,167 s e 2,083 s mediram brilho médio de 21,6 e 52,5 em 255. O clímax visual está entre 1,3 e 1,7 s. O restante é revelação tipográfica e repouso.
- Os sinais exportados correspondem ao deslizamento de madeira em 0,542 s e ao acento harmônico em 2,167 s. O pico medido foi −14,0 dBFS. O áudio foi verificado pela forma de onda e pela comparação com os sinais de origem. A escuta subjetiva ficou em aberto.

A transferência passou nesse briefing. O nome fica fora da passagem das portas, em posição diferente da demonstração da ÓRBITA. A câmera, a luz e o som reforçam a mesma ação. O vídeo usa um plano contínuo e termina com cerca de 2,7 s de baixa atividade. O teste comprova separação entre ação e texto em uma revelação simples. A qualidade de uma montagem densa, com cortes entre várias cenas e ritmo sonoro sustentado, continua em aberto.

Projeto `9990228e-929f-4ae0-94c7-16f5b0253d52`, revisão 5. Projeto de origem preservado. Job de edição `94f253bb-78eb-47cc-a22a-20117ef81492` e job de exportação `ea96d5be-4998-4be6-86d8-20c79497ade9`. Render de 144 quadros, 540 × 960 a 24 fps.

## Uso e custo

| Etapa | US$ |
| --- | ---: |
| Quatro classificações visuais | 0,016828 |
| Primeira sessão de edição, interrompida antes da timeline | 0,113776 |
| Edição concluída, incluindo retomada do rascunho | 1,093761 |
| **Total medido** | **1,224365** |

A primeira reserva mensal foi rejeitada antes de uma submissão. A reserva seguinte considerou os compromissos já registrados e o teto de US$ 1,50 da edição, apenas no processo do ensaio. A primeira sessão paga parou pela estimativa conservadora de tokens de uma inspeção detalhada. A Clicko passou a consultar a contagem da Anthropic quando essa estimativa ameaça interromper uma sessão com teto. Depois de cinco lotes salvos e duas revisões, o Opus pediu a exportação. Uma única chamada que recebeu a inspeção detalhada custou US$ 0,430383, com cerca de 84,6 mil tokens de escrita de cache. O custo total usa o consumo devolvido pela API e a tarifa publicada. A incerteza registrada foi US$ 0. [Tarifa oficial](https://platform.claude.com/docs/en/about-claude/pricing)

O [executor do ensaio](../../scripts/validation/clicko-orbita-opus-transfer.py) registra os hashes dos quadros, respostas, tokens, custos e recibos. O MP4, o projeto editável, a folha de contato e a verificação do export estão em `output/clicko-casa-lume-opus-2026-11-12` no workspace OneDrive.
