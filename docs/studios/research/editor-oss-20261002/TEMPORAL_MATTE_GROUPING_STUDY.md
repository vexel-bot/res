# Acumulação em grupos e conformidade de texels — 03/10/2026

Continuação posterior: [controles da borda e três candidatos de limites](TEMPORAL_MATTE_EDGE_STUDY.md). Os dados e resultados desta rodada abaixo conservam seu significado histórico.

Projeto original: `C:/Users/edugu/Downloads/res`. Continuação dos ensaios sem perdas. Nenhum candidato foi promovido. O worker, o gate e os providers de produção foram restaurados aos bytes congelados de native.13; admissão `pending`. Fixtures, seis frames, 168 probes por caso e limite 8 foram preservados.

## Cinco candidatos pela API real

Cada candidato usou o runner com fontes congeladas e restauração em `finally`. Os três casos foram plano → apply → inspection → job → Remotion → FFmpeg → QC. Os testes conservaram o oráculo original. Resultados completos e SHAs: [temporal-matte-grouping-experiments.json](temporal-matte-grouping-experiments.json).

| Candidato | Filho / alpha invertido | Rig / alpha normal | Rig / luminância invertida |
|---|---|---|---|
| Árvore aritmética SVG com `feImage` de `foreignObject` | QC falhou | QC falhou | QC falhou |
| Árvore de pares, `filter: opacity` | 9,2861; falhou | 6,2433; passou | 7,1095; passou |
| Árvore de pares, opacidade de composição | 8,0361; falhou | 6,2433; passou | 7,0178; passou |
| Opacidade constante da raiz aplicada uma vez, soma plana | 10,0178; falhou | 5,5838; passou | 8,0178; falhou |
| Opacidade constante aplicada uma vez, árvore de pares | 8,7601; falhou | 6,2433; passou | 6,3599; passou |

Os números são erros máximos por canal contra o oráculo original. Houve 15 execuções, sem skips/errors; 12 MP4s medidos com QC técnico passed e 2.016 probes. Os três jobs SVG chegaram ao render, mas os intermediários ficaram inteiramente pretos nos frames 0–8, voltando a pintar no hold 9–15. A [análise desses intermediários](temporal-matte-native14-svg-arithmetic-tree/failed-render-analysis.json) conserva seus SHAs. Esse percurso foi descartado; a especificação permite a média aritmética, mas não comprova a execução de HTML por essa referência SVG neste Chromium.

As árvores conservam os tempos e os pesos finais iguais: ao combinar ramos com `a` e `b` amostras, os pesos são `a/(a+b)` e `b/(a+b)`. A fatoração só foi aplicada quando todas as raízes registradas tinham a mesma opacidade finita e blend normal. Nenhuma variante altera a autoria canônica. A menor divergência 8,0361 continua sendo falha; não foi arredondada para um passe.

Base de pesquisa: [W3C feComposite](https://www.w3.org/TR/filter-effects-1/#feCompositeElement) define a combinação aritmética dos canais; [modelo de processamento](https://www.w3.org/TR/filter-effects-1/#FilterPrimitivesOverview) usa imagens RGBA premultiplicadas. A proposta de reduzir arredondamentos pela árvore é uma hipótese de implementação, não um resultado garantido pela norma.

## Filho invertido: a divergência também está nas amostras isoladas

O manifesto real capturado do rig foi derivado apenas para expor `hero`, manter o rig externo no frame 0 e inverter o matte alpha. O PNG e as tracks canônicas foram preservados. Esse diagnóstico usa diretamente o worker; não é um novo teste de admissão pela API nem qualificação de produto. Dez capturas sem perdas estão em [temporal-matte-png-capture-child-inverted](temporal-matte-png-capture-child-inverted).

No probe residual `(214,96)`, frame 0, o PNG temporal é `{114,25;114,25;114,25}`, a média dos oito PNGs isolados é `{114,875;114,875;114,875}` e o oráculo original prevê 122,7601. A acumulação acrescenta uma diferença de apenas −0,625 nível. As pinturas isoladas desse filho tiveram divergências de borda de até 21,9459. Portanto a conclusão anterior sobre a acumulação explica os dois probes do rig, mas não explica sozinha a borda do filho.

## Contraprova independente do oráculo

O oráculo atual integra a textura bilinear em 64 posições dentro de cada pixel, além de integrar a cobertura geométrica. Isso introduz uma suavização em fronteiras de texels mesmo quando o PNG está apenas transladado por coordenadas inteiras, em escala 1:1. Para conferir esse caso, dez blocos internos foram calculados diretamente pelos quatro texels originais, sem borda geométrica, rotação, escala ou acumulação temporal.

O [recibo de conformidade](temporal-matte-texel-conformance.json) mostra erro máximo de 1,4325 entre a captura Chromium e os texels exatos, enquanto o oráculo original se afasta até 6,5838 desses mesmos texels. Os valores esperados vêm do PNG de autoria e das opacidades 0,6 × 0,85 × 0,9 × 0,9; os pixels observados não definem a expectativa. Exemplo: no bloco `(140,82)` do matte normal, os quatro texels são opacos, então o valor exato é 105,3405, observado 106; o oráculo original calcula 98,7567.

Uma referência **somente de pesquisa** passou a amostrar a textura no centro do pixel e a integrar separadamente a geometria do conteúdo e do viewport. Ela satisfaz os dez casos exatos e reavaliou nove vídeos congelados, sem reescrever seus recibos ou modificar testes. [Dados dessa reavaliação](temporal-matte-center-sampling-study.json). No worker original, o erro máximo do rig/alpha normal passa a 5,1232; o filho mantém o probe de borda de 8,7601. As bordas afins da máscara ainda exigem validação independente antes de adotar a nova referência.

O diagnóstico agora separa três fatores: arredondamento da acumulação, reconstrução incorreta da textura no oráculo antigo e rasterização da borda do target mascarado. Corrigir a referência de textura resolve uma contradição analítica, mas não autoriza promover a combinação. O próximo ensaio deve conferir a cobertura da borda em espaços local e mundial, preservando provas negativas, tempos efetivos, sete variantes completas e regressões antes de remover o gate.

Revisão humana dos três estudos comerciais e os três novos briefs de autonomia permanecem pendentes. A limpeza recursiva anterior foi recusada pela revisão automática (`blocked by policy`); não houve nova tentativa de excluir seus alvos.
