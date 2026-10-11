# Inversão junto à borda fonte — 03/10/2026

O controle separou a pintura da imagem da inversão da máscara. A imagem direta com alpha uniforme e a máscara normal concordam, mas a inversão SVG original perde complementaridade na borda fonte. Subtrair duas máscaras SVG corrige o desvio localizado, porém **não passa o conjunto original**: cinco dos sete cenários passam, dois falham. Produção `4.0.527-native.13`, combinação `pending`, 21 hashes restaurados; nenhum candidato promovido.

Projeto original: `C:\Users\edugu\Downloads\res`. A investigação continua o [isolamento do frame 7](TEMPORAL_MATTE_UNIFORM_STUDY.md), sem alterar o oráculo, seus probes ou o limite de erro de 8. Os casos externos têm 168 probes; os dois casos com pai comum têm 162, após deduplicação de posições pelo teste original. Os ensaios não substituem os estudos comerciais ou a revisão humana.

## Controles que localizam o problema

O mesmo manifesto derivado do frame 7 conserva os transforms e a opacidade fonte 0,8624997. Os tracks estão constantes, sem exposição temporal. Em cada fase foram renderizados oito PNGs sem perdas: conteúdo sem máscara; alpha normal/invertido da imagem original e de uma imagem branca com alpha 128; pintura direta da imagem original com RGB branco e alpha preservado; pintura direta branca com alpha 128/255. Na pintura direta, o pai fonte tem opacidade 1; na máscara, a opacidade dos ancestrais externos não entra na cobertura fonte. A geometria mundial da fonte permanece igual.

Há **32 capturas em quatro fases**: native.13, combinação vetor/margem/árvore, subtração com gradiente e subtração com fundo SVG. São controles do worker, não novos vídeos pela API. Provider e gate não foram alterados nesses controles; os dois workers foram carregados temporariamente e restaurados em `finally`. Fontes, imagens, manifestos e PNGs têm bytes/hashes retidos. [Análise verificável](temporal-matte-source-edge-controls/analysis.json).

Valores médios do bloco 2 × 2 `(150,184)`, inteiramente dentro do conteúdo, junto à borda inferior da imagem fonte:

| Controle | native.13 / vetor-margem | Subtração com gradiente | Subtração com fundo SVG |
|---|---:|---:|---:|
| Conteúdo sem máscara | 177,00 | 177,00 | 177,00 |
| Máscara normal, alpha 128 | 72,00 | 72,00 | 72,00 |
| Máscara invertida, alpha 128 | 112,00 | 104,50 | 104,50 |
| Normal + invertida − sem máscara | +7,00 | −0,50 | −0,50 |
| Imagem direta, alpha 128 | 103,50 | 103,50 | 103,50 |

A opacidade acumulada do conteúdo é 0,6885. Multiplicar a pintura direta observada por esse fator prevê 71,2598, próximo dos 72 observados na máscara normal. Essa comparação usa pixels capturados e está identificada como **referência empírica**, não oráculo independente. No interior uniforme `(160,170)`, normal + invertida = conteúdo sem máscara; na borda interna da textura original `(162,92)`, o desvio original da soma chega a +8,75. A inversão, e não apenas o viewport externo, altera a cobertura.

Separadamente, uma referência geométrica calcula a interseção exata do polígono fonte com cada pixel. Para `(150,184)`, a cobertura média é 0,944877. Com texels uniformes e borda clamped, ela prevê pintura direta 104,3144; o PNG dá 103,50. Acrescentar outro kernel com texels transparentes fora do bitmap prevê 97,4323, contradito pelo controle. Esse resultado descarta essa hipótese de dupla suavização para este bloco; não prova que interseção de área descreva universalmente o antialiasing do Chromium. Os dois modelos continuam registrados na análise, sem substituir a expectativa do teste original.

## Alternativas pela cadeia API → job → MP4

Todos os candidatos mantêm os tempos efetivos por nó e a árvore balanceada de composição. A gate foi removida somente durante os experimentos, com versão temporária native.14; as quatro fontes alteradas e as 23 fontes congeladas de cada execução foram arquivadas. [Recibo consolidado](temporal-matte-source-edge-experiments.json).

| Candidato, três cenários externos | Filho / alpha invertido | Rig / alpha normal | Rig / luminância invertida |
|---|---:|---:|---:|
| Subtração com gradiente opaco | 12,2601; falhou | 6,2433; passou | 8,8175; falhou |
| Inversão por filtro no espaço target | 10,7730; falhou | 6,2433; passou | 8,7730; falhou |
| Subtração com fundo SVG | 8,0178; falhou | 6,2433; passou | 6,7678; passou |

A primeira alternativa usa `mask-composite: subtract` entre um gradiente branco e a máscara fonte não invertida. Ela reduz o erro do antigo bloco do frame 7 para 4,0361, mas introduz perdas em outras bordas. A segunda aplica `A' = 1 − A` depois do transform fonte→target, com região do filtro explícita e expandida; surgem halos em novos probes. A terceira substitui o gradiente por outra máscara SVG branca com clip vetorial do conteúdo e deixa a fonte invertida sem esse clip antes da subtração; corrige a falha anterior, mas conserva erro 8,0178 no frame 4, `(110,100)`.

O último candidato também percorreu os **sete cenários originais**, sem seleção posterior de probes:

| Cenário | Erro máximo | Resultado |
|---|---:|---|
| Controle / externo / alpha normal | 6,2433 | passou |
| Filho / externo / alpha normal | 6,2433 | passou |
| Filho / externo / alpha invertido | 8,0178 | falhou |
| Rig / externo / alpha normal | 6,2433 | passou |
| Rig / externo / luminância invertida | 6,7678 | passou |
| Filho / pai comum / alpha normal | 6,2912 | passou |
| Rig / pai comum / luminância normal | 8,1116 | falhou |

A segunda falha completa ocorre no frame 7, `(208,100)`. O conjunto soma **16 execuções, nove passes e sete falhas, sem skips/errors; 16 MP4s com QC técnico passed; 2.676 probes de pixels e 96 verificações de matriz**. As três execuções externas repetidas na matriz completa não são cenários únicos adicionais. QC técnico passed confirma integridade técnica do vídeo; não aprova uma combinação que falhou pixels.

## Fontes e consequência

### Separação das duas falhas restantes

Foram derivadas 20 capturas PNG adicionais: temporal real, centro e oito amostras isoladas para cada cenário que falhou. Os tracks isolados usam a mesma avaliação cúbica de 18 passos do worker; tempo externo fica no centro. Nove manifestos constantes por cenário tiveram os pontos mundiais de target/fonte conferidos contra as matrizes independentes do teste, com erro inferior a 0,002. A soma das expectativas isoladas reproduz a expectativa original do probe até 1e-9. [Diagnóstico sem perdas](temporal-matte-svg-subtract-residual-controls-v2/analysis.json).

| Probe original que falhou | Expectativa original | Média dos oito PNGs isolados | PNG temporal | MP4 intermediário | MP4 final |
|---|---:|---:|---:|---:|---:|
| Filho, frame 4, `(110,100)` | 127,7322 | 129,75 | 130,25 | 129,75 | 135,75 |
| Rig / pai comum, frame 7, `(208,100)` | 142,8884 | 148,25 | 149,00 | 149,00 | 151,00 |

A acumulação acrescenta somente 0,5 e 0,75 à média isolada. O PNG temporal fica abaixo do limite original em ambos os probes, mas o MP4 final cruza esse limite. A referência de pesquisa que amostra textura no centro prevê 147,4880 para o rig, em vez de 142,8884; sua limitação de antialiasing afim continua explícita, sem mudar o veredito original. A diferença final/intermediário inclui composição e encode FFmpeg, não foi atribuída integralmente ao CRF sem contraprova.

A primeira derivação do caso de pai comum estava incorreta: colocou a fonte dentro de `rig` e a amostrou junto. Foi excluída antes da análise. A derivação corrigida põe `mask-rig` em `(80,60)` como filho de `outer`, irmão de `rig`, e conserva o tempo fonte central, como o teste original. Os 20 PNGs anteriores e seus bytes permanecem com [classificação de invalidade](temporal-matte-svg-subtract-residual-controls/classification.json); não integram as 52 capturas válidas da rodada. Isso não invalida os sete testes reais da API, que usaram a fixture original.

### Contraprova do encode final

Os sete intermediários retidos foram recompostos com o mesmo grafo RGBA → scale/pad → overlay → yuv420p do finalizador e o mesmo preset `veryfast`, threads e FPS. O controle **CRF 14 reproduziu exatamente todos os 1.164 probes RGB dos sete MP4s reais**. Só depois dessa equivalência foram comparados CRF 10 e 8; áudio foi copiado do resultado final, sem outra qualificação do mixer. São 21 vídeos derivados, não novos jobs API. [Estudo de encode](temporal-matte-svg-subtract-final-encode-study-v2/analysis.json).

| CRF final | Cenários abaixo do limite original | Filho invertido, erro máximo | Rig / pai comum, erro máximo |
|---|---:|---:|---:|
| 14, controle equivalente à API | 5 / 7 | 8,0178 | 8,1116 |
| 10 | 6 / 7 | 9,0163 | 5,3616 |
| 8 | 6 / 7 | 9,0163 | 5,6116 |

Os dois CRFs menores resolvem os probes anteriores, mas expõem erro 9,0163 no filho invertido, frame 0, `(138,82)`: observado 178 contra expectativa 168,9837. Assim, não basta aumentar a qualidade para promover a combinação, e não foi alterado o preset de produção. O ensaio inicial de encode direto, sem o grafo contextual, falhou sua própria equivalência e foi [excluído](temporal-matte-svg-subtract-final-encode-study/classification.json), com bytes preservados.

A semântica de subtração vem de [CSS Masking, mask-composite](https://www.w3.org/TR/css-masking-1/#the-mask-composite): a máscara atual é source, as inferiores formam destination; `subtract` aplica source-out. Isso define a composição, não o rasterizador ou sua precisão. A alternativa de filtro usa a matriz de [Filter Effects, feColorMatrix](https://www.w3.org/TR/filter-effects-1/#feColorMatrixElement). Os limites de recorte continuam documentados nas fontes pinadas de Chromium 149 do [estudo anterior](TEMPORAL_MATTE_UNIFORM_STUDY.md). Não houve clone adicional nem implementação externa copiada.

O próximo diagnóstico deve separar cobertura e textura no novo probe do frame 0, conservando referências independentes. Uma tolerância aumentada ou um arredondamento de 8,0178 para 8 não constituiriam correção. A produção permanece restaurada; a combinação de matte e exposição sob ancestral externo móvel segue rejeitada explicitamente pela gate enquanto não qualificada. As regressões de produção já registradas não foram recontadas como testes novos nesta rodada.

Revisão humana dos estudos comerciais e três novos briefs de autonomia continuam pendentes. A revisão automática de aprovação recusou a limpeza recursiva anterior com `blocked by policy`; os repositórios de estudo e os bundles abrangidos continuam presentes, sem tentativa de contornar a decisão.
