# Máscaras uniformes e isolamento do frame 7 — 03/10/2026

Projeto original: `C:/Users/edugu/Downloads/res`. Continuação dos controles de borda. Produção native.13, gate `pending`, 21 hashes preservados. Não houve promoção de candidato, alteração do oráculo original, mudança de probes ou ampliação da tolerância 8. Revisão humana permanece pendente.

## Contraprova sem temporal

O [recibo de captura](temporal-matte-uniform-controls/receipt.json) conserva **30 PNGs** e seus manifests: sete geometrias × quatro controles, mais dois negativos na identidade. Geometrias: identidade, translação fracionária, pequena transformação afim, rotação, escala não uniforme, rotação com escala e pose de hold com pais transformados. Os PNGs foram definidos como texels RGBA uniformes exatos, sem compressão com perdas. Fontes do worker, script e browser foram congeladas por SHA; o bundle temporário foi removido pelo próprio capturador.

Controles: sem máscara; alpha branco com viewport da imagem igual ao target; alpha branco com imagem ampliada 3× em torno do mesmo pivô; alpha transparente invertido. Source e target compartilham pai e transform. A única textura é constante; não há efeito temporal ou variação de opacidade. Os negativos de alpha transparente normal e alpha branco invertido ficaram inteiramente pretos. A máscara branca ampliada e a transparente invertida tiveram **todos os pixels RGB iguais nas sete geometrias**.

A [análise independente](temporal-matte-uniform-controls/analysis.json) calcula a interseção exata de um polígono convexo com cada pixel. Quatro casos de área fechada calibram o cálculo, incluindo translação fracionária e meio pixel triangular. As referências `C` e `C²` ficaram separadas. Elas são modelos de área ideais; não definem um novo resultado de aprovação para o antialiasing do browser.

| Geometria | MAE na borda: sem máscara vs `C` | MAE: branco ampliado vs `C` | MAE: branco ampliado vs `C²` |
|---|---:|---:|---:|
| Identidade: nenhum pixel parcial | — | — | — |
| Translação fracionária | 4,02 | 32,79 | 28,64 |
| Pequena transformação afim | 1,63 | 34,22 | 6,29 |
| Rotação | 1,51 | 30,97 | 7,01 |
| Escala não uniforme | 4,47 | 4,17 | 32,34 |
| Rotação + escala | 2,24 | 30,00 | 7,35 |
| Hold com pais | 1,62 | 31,11 | 6,96 |

MAE por canal nos pixels parcialmente cobertos, não os probes 2×2 da qualificação API. Os maiores erros individuais também foram retidos: até o controle sem máscara difere da integração de área nos cantos. Por isso os dados não sustentam substituir toda a borda por um modelo universal `C²`.

Uma predição empírica adicional usa o PNG sem máscara e um teste matemático de inclusão do centro do pixel. Ela explica o recorte da translação e da escala sem rotação com diferença máxima de um nível; falha nas geometrias rotacionadas. Está explicitamente identificada como comparação pareada, pois usa pixels observados para uma parte da predição e **não é um oráculo independente de cor**.

## Recorte no código da versão instalada

O [índice do código primário](chromium-mask-clip-study.json) fixa o executável Chrome for Testing 149.0.7790.0 e três arquivos pelos seus SHAs. [SVGMaskPainter](https://chromium.googlesource.com/chromium/src/+/149.0.7790.0/third_party/blink/renderer/core/paint/svg_mask_painter.cc) chama o recorte retangular dos limites do recurso. [GraphicsContext](https://chromium.googlesource.com/chromium/src/+/149.0.7790.0/third_party/blink/renderer/platform/graphics/graphics_context.h) encaminha esse recorte a `ClipRect`, cujo default é sem antialiasing; [a implementação](https://chromium.googlesource.com/chromium/src/+/149.0.7790.0/third_party/blink/renderer/platform/graphics/graphics_context.cc) passa a opção ao canvas. A pesquisa lê fontes em memória, sem clone ou cópia de implementação.

O caminho confirma a existência de um recorte sem AA. Não prova que a rasterização final ocorra em espaço mundial, nem prescreve uma única fórmula para os pixels após a composição. Essa limitação coincide com a falha da predição por centro do pixel nas poses rotacionadas.

## Combinação dos ajustes, com API real

Três novos candidatos conservaram o clip vetorial do target, ampliaram a região SVG para afastar seu recorte da borda e usaram `no-clip` com outline transparente de 2 px para a caixa HTML. A exposição usa árvore de pares. O segundo aplica a opacidade constante da raiz uma vez quando os requisitos de fatoração são satisfeitos; o terceiro amplia apenas a região do filtro de inversão. Fontes originais/candidatas, testes e renders foram retidos; restauração em `finally`, sem conflito concorrente.

| Candidato | Filho / alpha invertido | Rig / alpha normal | Rig / luminância invertida |
|---|---:|---:|---:|
| Vetor + margem + árvore | 9,0361; falhou | 6,2433; passou | 5,9246; passou |
| Mesmo ajuste + fatoração de opacidade | 9,0361; falhou | 6,2433; passou | 5,8060; passou |
| Mesmo ajuste + filtro de inversão ampliado | 9,0361; falhou | 6,2433; passou | 5,9246; passou |

Erros máximos contra o oráculo original, sem arredondar para passes. [Recibo verificado](temporal-matte-vector-guard-experiments.json): **nove testes reais, seis passes e três falhas, sem skips/errors; nove MP4s com QC técnico passed e 1.512 probes**. Todos os três candidatos conservaram exatamente uma falha: filho invertido, frame 7, bloco `(150,184)`.

No controle do filtro, os bytes do renderer diferem somente no retângulo do filtro de inversão. Nenhum dos 504 probes RGB mudou. A hipótese de esse retângulo causar o residual foi descartada. A textura amostrada no centro do pixel da pesquisa anterior também não muda a expectativa deste bloco.

## A falha restante antecede a acumulação

Foi derivado o mesmo caso canônico para expor apenas `hero` no frame 7, mantendo todos os externos no frame 7. Dez PNGs sem perdas conservaram exposição real, centro e oito amostras isoladas com tracks constantes avaliadas pelo mesmo interpolador de 18 passos do worker. Este é um diagnóstico direto, não outra qualificação pela API. Os bytes dos dois workers candidatos foram carregados temporariamente; provider/gate não foram alterados; os 21 hashes de produção foram restaurados. [Recibo e análise](temporal-matte-frame7-vector-guard/analysis.json).

No bloco `(150,184)`, a referência original prevê **103,7139**. Todas as oito amostras isoladas pintam **112,00**: erro 8,2861 já sem acumulação. O temporal pinta **112,75**, igual ao MP4 da API no mesmo bloco. A acumulação acrescenta apenas **0,75**. O centro local da imagem do matte fica em `(19,4342;95,1876)` num viewport de altura 96; o centro local do conteúdo fica bem dentro de seu retângulo. A falha está, portanto, junto à borda da imagem fonte, e não na borda geométrica do target que motivou o ensaio anterior. Isso não identifica ainda se a causa é o viewport, a interpolação ou outra etapa de pintura da imagem.

O próximo controle deve comparar alpha normal, inversão e pintura direta de uma imagem com alpha uniforme, na mesma borda fonte e com as mesmas transformações. Ele pode separar recorte e reconstrução de texels sem ajustar a expectativa a pixels observados. Nenhum candidato desta rodada justifica a promoção; os sete casos completos e as regressões continuam necessários depois de resolver o residual.

Revisão humana dos estudos comerciais, três novos briefs de autonomia e limpeza dos repositórios de estudo permanecem pendentes. A revisão automática recusou a limpeza recursiva anterior com `blocked by policy`; não houve tentativa de contornar a decisão.
