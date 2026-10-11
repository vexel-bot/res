# Identidade dos texels e cobertura afim — 03/10/2026

O novo probe do frame 0 confirmou uma falha na referência espacial antiga, não nos texels pintados. Em uma translação inteira, o bloco `(138,82)` lê quatro texels totalmente transparentes. A máscara normal pinta zero; a invertida coincide com o conteúdo sem máscara. O oráculo antigo adiciona uma suavização que não existe nessa translação. Os testes históricos, a tolerância e a gate de produção foram preservados.

O estudo também avança na cobertura geométrica: a referência de rampa de meio pixel reduz o pior erro dos sete controles sem máscara de 44,49 para 6,70. A admissão continua `pending`: conformidade em translação inteira não prova todos os percursos afins de máscara. Projeto original em `C:\Users\edugu\Downloads\res`; os 21 hashes de produção native.13 foram restaurados.

## Contraprova exata no frame 0

Foram renderizados 30 PNGs sem perdas: máscara alpha normal, invertida e conteúdo sem máscara; para cada caso, frame temporal real, centro e oito amostras isoladas. O shutter centrado é recortado ao começo da composição, dando amostras entre 0 e 0,25. A fonte externa fica no frame 0, matriz mundial `(1,0,0,1,100,74)`, alpha local 0,6; o conteúdo acumula alpha 0,6885. Todos os cantos do viewport fonte estão estritamente dentro do conteúdo em todas as amostras, provado pelas matrizes independentes. Portanto, cobertura da borda do conteúdo não define a expectativa nesses blocos.

Cada captura compara os **1.920 blocos 2 × 2** que cobrem o PNG original de 80 × 96. A expectativa vem diretamente dos texels RGBA autorais, antes de observar a captura. São **57.600 comparações**, nenhuma com erro ≥8. [Análise e hashes](temporal-matte-svg-subtract-frame0-controls/analysis.json).

| Percurso | Erro máximo contra texels exatos, todos os PNGs |
|---|---:|
| Alpha normal | 1,1232 |
| Alpha invertido | 2,4325 |
| Sem máscara | 2,4325 |

Em todos os blocos e captures, normal + invertida − sem máscara fica em até 1 nível. Essa soma é controle empírico separado da referência exata. No bloco `(138,82)`, texels `[0,0,0,0]` dão:

| Referência / observação | Normal | Invertida | Sem máscara |
|---|---:|---:|---:|
| Texels autorais, alpha canônico | 0,0000 | 175,5675 | 175,5675 |
| Oráculo antigo, textura supersampled | 6,5838 | 168,9837 | — |
| PNG centro / cada amostra isolada | 0,0000 | 177,00 | 177,00 |
| PNG temporal | 0,0000 | 178,00 | 178,00 |

O erro 9,0163 contra a referência antiga nos reencodes CRF 10/8 é explicado pela textura artificialmente suavizada (6,5838 níveis) mais a quantização/composição observada. Isso não autoriza corrigir os testes para obter passes. A referência nova deve demonstrar conformidade independente no restante de seu domínio.

## Reavaliação de pesquisa dos vídeos já retidos

A referência que amostra a textura no centro do pixel passou em **3.840 blocos exatos** das máscaras normal/invertida, sem diferença acima de 1e-9. Ela conserva a geometria supersampled e a cobertura separada do conteúdo; não foi incorporada ao teste de admissão. [Reavaliação](temporal-matte-qualified-texel-reassessment.json).

| CRF final, sete vídeos derivados | Casos abaixo de 8 na referência de pesquisa | Maior erro |
|---|---:|---:|
| 14, equivalente aos pixels da API | 6 / 7 | 8,0178 |
| 10 | 7 / 7 | 5,5559 |
| 8 | 7 / 7 | 4,9819 |

São os mesmos 21 reencodes do [estudo anterior](TEMPORAL_MATTE_SOURCE_EDGE_STUDY.md), com checksums conferidos; nenhum novo job API nesta reavaliação. O resultado original permanece 5/7 em CRF 14 e 6/7 em CRF 10/8. Os passes pela referência de pesquisa são promissores, mas a cobertura afim continua por qualificar; não foram convertidos em admissão nem aprovação humana.

## Fonte open source e modelo geométrico

A versão exata do navegador é Chrome for Testing 149.0.7790.0, cujo DEPS fixa Skia `0cb35533022b3912904831c2290680bb8eea0363`. Quatro arquivos foram lidos em memória, sem clone ou cópia de implementação. [Hashes, tamanho e linhas selecionadas](skia-quad-coverage-study.json).

O percurso Ganesh em [QuadPerEdgeAA.cpp](https://skia.googlesource.com/skia/+/0cb35533022b3912904831c2290680bb8eea0363/src/gpu/ganesh/ops/QuadPerEdgeAA.cpp) desloca bordas em meio pixel e interpola coverage dos vértices. [GrQuadUtils.cpp](https://skia.googlesource.com/skia/+/0cb35533022b3912904831c2290680bb8eea0363/src/gpu/ganesh/geometry/GrQuadUtils.cpp) contém os cálculos de inset/outset. A leitura não estabelece que todo draw do navegador use esse caminho.

A hipótese de pesquisa usa a menor distância euclidiana orientada do centro do pixel às quatro bordas do quad: `clamp(0,5 + distância, 0, 1)`. Não há parâmetro ajustado aos pixels. Cinco casos fechados verificam centro, borda, exterior e canto fracionário antes da comparação. No canto fracionário, o mínimo das rampas difere matematicamente do produto das áreas.

Nos sete PNGs uniformes **sem máscara** já retidos, foram comparados 12.200 pixels próximos às bordas:

| Transform | Máximo: área exata | Máximo: rampa | RMS: rampa |
|---|---:|---:|---:|
| Identidade | 1,4325 | 1,4325 | 1,0113 |
| Translação fracionária | 44,4930 | 4,5514 | 2,4014 |
| Afim pequena | 38,1447 | 3,9512 | 1,3114 |
| Rotação | 28,7746 | 5,0117 | 1,2009 |
| Escala não uniforme | 41,0627 | 5,6595 | 2,7250 |
| Rotação + escala | 27,1497 | 6,6958 | 1,5696 |
| Hierarquia em hold | 26,4367 | 4,8466 | 1,2957 |

[Análise das rampas](temporal-matte-edge-ramp-study.json). Área exata permanece no relatório como hipótese distinta, não foi apagada. A rampa se aproxima dos quads compostos observados; isso não demonstra por si só a cobertura do clip SVG, o espaço de rasterização da máscara ou a reconstrução de textura sob affine.

## Estado do percurso mascarado

Foram capturados mais 30 PNGs com os dois workers temporários da subtração SVG: sete transforms × quatro modos, mais dois negativos. Provider e gate ficaram intactos. As fontes, manifests, recursos e imagens têm bytes/hashes retidos; o wrapper restaurou os dois workers e verificou os 21 hashes de produção. Os controles com imagem branca cobrindo o target e inversão de imagem vazia têm a mesma finalidade matemática. Área/rampa e uma/duas/três coberturas são mantidas separadamente na análise para evitar escolher a hipótese apenas pelo melhor número. [Capturas](temporal-matte-svg-subtract-uniform-controls/receipt.json).

A qualificação completa ainda depende desse percurso, da cadeia real API com a referência validada, das regressões e da inspeção/revisão humana. Este recibo não soma os 21 reencodes históricos como vídeos novos nem muda a versão de produção.

Os 30 PNGs candidatos completaram o controle: ambos os negativos ficaram totalmente pretos, e branca cobrindo o target = inversão de imagem vazia em **todos os pixels dos sete pares**. [Análise de todas as hipóteses](temporal-matte-svg-subtract-uniform-controls/analysis.json). Uma única cobertura `rampa²` não explica os cantos rotacionados: chega a 26,6188 níveis na pequena transformação afim; `área²` chega a 37,6601 no canto da translação fracionária. Nenhuma dessas hipóteses foi adotada como solução universal.

Uma referência seguinte separa o quad sólido do clip. O quad usa rampa; o clip alinhado aos eixos usa rampa, enquanto o clip rotacionado usa interseção de área. Essa distinção é compatível com a otimização de caminhos retangulares em [SkCanvas.cpp](https://skia.googlesource.com/skia/+/0cb35533022b3912904831c2290680bb8eea0363/src/core/SkCanvas.cpp), quando `rectStaysRect`; [ClipStack.cpp](https://skia.googlesource.com/skia/+/0cb35533022b3912904831c2290680bb8eea0363/src/gpu/ganesh/ClipStack.cpp) mantém percursos analíticos e de coverage. A fórmula continua uma hipótese; a inspeção de fonte não prova todos os detalhes de rasterização local.

| Transform, branca cobrindo target / inversão vazia | Máximo, quad × clip | RMS |
|---|---:|---:|
| Identidade | 1,4325 | 1,0113 |
| Translação fracionária | 5,1773 | 2,6802 |
| Afim pequena | 3,0551 | 1,0423 |
| Rotação | 4,9445 | 1,1534 |
| Escala não uniforme | **8,1525** | 3,7308 |
| Rotação + escala | 7,8158 | 1,5406 |
| Hierarquia em hold | 5,4492 | 1,1294 |

[Referência mista](temporal-matte-mixed-coverage-study.json), erros por **pixel individual** nos controles uniformes. O residual 8,1525 da escala não uniforme permanece; não foi arredondado nem absorvido por um ajuste empírico. A imagem branca de tamanho local também acrescenta sua própria cobertura em transforms rotacionados, ainda não plenamente modelada. Por isso os resultados de pesquisa dos vídeos, medidos em blocos 2 × 2, não substituem uma qualificação completa das coberturas individuais.

A reavaliação mista dos 21 reencodes mantém 6/7 abaixo de 8 em CRF 14 e 7/7 em CRF 10/8; máximos 8,0603, 5,7107 e 4,7979 respectivamente. [Comparações](temporal-matte-ramp-reassessment.json). O conteúdo, a imagem fonte e o clip são calculados independentemente da observação, sem constantes ajustadas. O domínio ainda incompleto é explicitado no próprio relatório.

## CRF 10 pela API real

Depois dos controles, o mesmo candidato percorreu os sete cenários novamente pela cadeia edição canônica → plano aplicado/revisão 2 → inspeção → job → MP4 → QC. O finalizador temporário mudou **somente** versão 1.4.0→1.4.1 e CRF high 14→10, incluindo o recibo `videoCrf`; os bytes desses três ajustes foram conferidos. Os dois workers gráficos são idênticos aos do ensaio anterior. As cinco fontes temporariamente alteradas foram restauradas em `finally`, sem conflitos; os 21 hashes originais conferem. Não foi alterado o teste original, o manifesto dos cenários ou a tolerância.

[Recibo consolidado](temporal-matte-texel-coverage-receipt.json): **sete MP4s novos com QC técnico passed, 1.164 probes de pixels e 42 verificações de matriz; seis passes e uma falha no teste original, sem skips/errors**. O encode observado em todos os jobs registra `high / videoCrf:10`. Todos os 1.164 blocos RGB dos jobs coincidem exatamente com os reencodes CRF 10 retidos. Assim a comparação das duas referências de pesquisa se aplica aos pixels da API, não apenas a um processo avulso de FFmpeg.

| Cenário API / CRF 10 | Máximo: oráculo histórico | Máximo: textura no centro | Máximo: quad/clip/textura |
|---|---:|---:|---:|
| Controle / externo / alpha normal | 6,5838 | 2,6721 | 2,5448 |
| Filho / externo / alpha normal | 6,5838 | 2,8279 | 2,9552 |
| Filho / externo / alpha invertido | **9,0163** | 4,8933 | 4,8933 |
| Rig / externo / alpha normal | 6,5838 | 4,2888 | 4,1024 |
| Rig / externo / luminância invertida | 5,5559 | 5,5559 | 5,7107 |
| Filho / pai comum / alpha normal | 6,7433 | 5,0412 | 4,8737 |
| Rig / pai comum / luminância normal | 5,3616 | 3,0412 | 2,8737 |

A única falha histórica está no frame 0, `(138,82)`, confirmado pela contraprova de texels. Mesmo assim, nenhum desses passes de pesquisa foi convertido em admissão. O residual individual de clip e a cobertura de imagem coincidente ainda precisam de qualificação própria antes de substituir o oráculo; a produção mantém provider native.13, finalizador 1.4.0/high=14 e gate `pending`.

A rodada acrescentou 60 PNGs válidos (30 de texels, 30 de cobertura) e sete vídeos API. Os sete PNGs sem máscara usados na análise de rampas são controles históricos; os 21 reencodes usados nas reavaliações também são históricos. Não foram somados como novas execuções. A coleta mantém manifesto/recursos/source bytes/checksums e mede estados de aprovação separadamente. A revisão humana dos estudos comerciais, os três novos briefs de autonomia e a inspeção da combinação permanecem pendentes.

A revisão automática recusou a limpeza recursiva anterior com `blocked by policy`. Os materiais abrangidos permanecem presentes; não houve tentativa de contornar a recusa. Não houve novo clone nesta rodada.
