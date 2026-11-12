# ÓRBITA com Opus 5.5 e revisão no EffectCraft

## O que limitava a edição

| Evidência | Efeito para o editor | Alteração |
| --- | --- | --- |
| A geração anterior consumiu 224.431 tokens de entrada em 16 chamadas. A integração reenviava contexto sem ativar o cache da Anthropic. | Cada inspeção repetia parte do custo do briefing, das ferramentas, dos scripts e dos resultados anteriores. | Cache de cinco minutos no Opus 5.5 via API direta. O recibo distingue entrada normal, leitura, gravação e saída. O limite reserva pelo pior caso de gravação. |
| As folhas de quadros exigiam números de frames. Era possível conferir imagens espaçadas e deixar passar o instante em que a transição falhava. | Um roteiro temporal em segundos precisava ser convertido manualmente. O recibo não dizia qual versão tinha sido revisada. | A prévia aceita segundos ou frames e rotula ambos. O recibo registra os pontos amostrados e o lote salvo que foi renderizado. |
| O protótipo local mostrou contraste e legibilidade no fechamento, mas deixou Saturno quase parado no miolo. | Uma composição legível pode continuar sem progressão. Uma folha de quadros isolada do processo não induz uma correção. | O briefing dá liberdade de direção e pede corte completo, verificação antes e depois da transição principal, ajuste localizado e nova prévia antes de exportar. |
| Claude recebe imagens amostradas. A trilha anterior tinha pico de −31,8 dBFS. | Ele pode examinar estados do quadro. Fluidez, som e sincronismo dependem de evidência temporal e medições fora da folha de quadros. | O projeto dispõe de uma trilha local com acentos conhecidos. A exportação será analisada com quadros, intervalos e medição do áudio final. |

O custo anterior calculado foi US$ 1,104424. A proporção aproximada foi 81% de entrada e 19% de saída, usando os preços padrão de US$ 4 e US$ 20 por milhão. Na Anthropic, gravação no cache de cinco minutos custa US$ 5 por milhão, e leitura US$ 0,20. O teto da sessão permanece US$ 1,50, com exposição de chamadas inconclusivas contabilizada. [Preços e cache da Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

## Demonstrações de edição com Claude

| Material | Evidência consultada | Aplicação |
| --- | --- | --- |
| [Aidan Stanik, How I Edit Videos with Claude Code](https://www.youtube.com/watch?v=BNPlUj-CxB0) | Descrição e capítulos do autor. Materiais em 7:39, primeiro render e revisão em 15:55, correção de transições em 18:05 e iteração em motion em 19:02. O player abriu e ficou em 0:00. | Tornar barata e localizada a iteração a partir de pixels do próprio render. |
| [Jason Cooperson, How I Fully Automated My Video Editing](https://www.youtube.com/watch?v=XeTAlZiIWHE) | Descrição e capítulos do autor. Corte inicial em 6:57, grafismos em 10:19, segunda passagem em 11:42 e exportação em 18:40. O autor relata reaproveitar material e renderizar somente a parte alterada na segunda passagem. | Conferir os instantes alterados na prévia do EffectCraft antes do render final. |
| [Sandy Lee, How I Fully Automated Video Editing](https://www.youtube.com/watch?v=vI4RdXMSq8c) | Descrição e capítulos da autora. Transcrição e FFmpeg em 2:45, direção em 5:36 e B-roll em 16:57. A autora usa ferramentas distintas para cada etapa. | Medir a limitação de mídia separadamente da capacidade de composição. |
| [Lavin, I Fully Automated My Video Editing Using Claude](https://www.youtube.com/watch?v=3F6tP8tMosc) | Capítulos do autor. Roteiro e checagem de quadros em 7:53, ajuste de repetições no Premiere em 8:56 e storyboard em 12:18. | Planejar o que deve mudar no quadro e comparar com a montagem exportada. |

Os capítulos descrevem o processo declarado pelos autores. Não são verificação independente do custo, do grau de autonomia ou da qualidade desses vídeos. A documentação de [Remotion](https://www.remotion.dev/docs/ai/skills) e a documentação de [PrimCut](https://docs.primcut.app/features/primcut-mcp) confirmam exemplos de integração com prévia, leitura da timeline ou transcrição. Na Clicko a execução permanece no EffectCraft.

## Protocolo da geração

Uma sessão de Opus 5.5 via Anthropic direta, com teto de US$ 1,50, modo de planejamento deliberado e liberdade de direção. Composição de 12 s em 540 × 960 e 24 fps. Brief, público, marca, categoria e CTA preservados. Serão registrados custo medido, exposição incerta, tempo, lotes editados, prévias por lote, exportação, legibilidade a 300 px, progressão visual e nível de áudio. Mudaram as instruções e as opções de material junto com a implementação. A comparação entre os vídeos não identifica o efeito isolado dessas mudanças.

## Resultado

O EffectCraft exportou o MP4 que o próprio Opus montou e pediu para finalizar. O corte tem 12 s, 288 quadros, H.264 em 540 × 960 e AAC. A sessão levou 6 min 54 s até a revisão salva, e o render levou 39,8 s. Tempo decorrido do início da sessão até o MP4 de 7 min 38 s. A edição anterior levou 2 min 47 s até salvar a revisão.

| Indicador | Corte anterior do Opus | Nova sessão |
| --- | --- | --- |
| Chamadas e lotes salvos | 16 chamadas e 6 lotes | 20 chamadas e 10 lotes |
| Prévia auditada por lote | Sem registro dos tempos e do lote da folha | 6 folhas, incluindo a revisão final do lote 10 |
| Entrada normal, gravação e leitura de cache | 224.431 tokens de entrada | 42 normais, 103.839 de gravação e 332.358 de leitura |
| Saída | 10.335 tokens | 15.364 tokens |
| Custo medido pela resposta da Anthropic | US$ 1,104424 | US$ 0,8931146, sem cobrança incerta registrada |
| Áudio final | Média −44,4 dBFS e pico −31,8 dBFS | Média −29,9 dBFS e pico −10,1 dBFS |
| Leitura a 300 px | A categoria ficava em segundo plano | A 10,5 s, marca, categoria e CTA permanecem legíveis |

Os números de cache contabilizam repetições por chamada. Para o mesmo volume de tokens da nova sessão, a tarifa normal de entrada e saída somaria US$ 2,052236. É uma comparação de preço sobre o uso medido. A sessão sem cache teria de encerrar ou reduzir o contexto antes de ultrapassar o teto.

- **0–2,2 s.** O recorte apresenta Saturno em escala próxima. A categoria começa discreta no alto. A introdução ainda concentra pouco contraste na primeira fração de segundo.
- **2,2–5,4 s.** A abertura de escala revela o planeta e os anéis. O texto intermediário entra abaixo da imagem. O meio tem mais progressão que a foto quase estática do protótipo local.
- **5,4–8,3 s.** Os quadros confirmam o arco branco crescendo sobre o limbo, o planeta recuando e a letra permanecendo no lugar quando o restante do título entra. O Opus relatou ter encurtado a espera entre a saída do planeta e o encaixe da letra. O recibo comprova as prévias com tempos entre 7,4 e 8,5 s e edições posteriores.
- **8,3–12 s.** Uma linha sai da letra e enquadra a categoria e o convite. Marca, categoria e CTA foram conferidos a 300 px. A fonte fotográfica aparece em tela. Compreensão, ritmo percebido e preferência do público continuam sem validação.

O Reel aberto pelo usuário não apareceu nas abas acessíveis e a ferramenta de captura da janela falhou. A comparação específica fica pendente do link. A pesquisa do YouTube usou descrições e capítulos. O player conferido apresentou erro de reprodução.

Sessão 78138382-b4dc-4b66-8400-de262b5eb714. Documento 1ad668e2-c400-4b06-b02d-f3db2d47b4f6. Exportação 772bffe6-993a-4d45-81bf-315d7e550b36. SHA-256 f067c08a0125cf04f107eb801b54f9096f36df4e8e57e17598accab5ff28f5ce.
