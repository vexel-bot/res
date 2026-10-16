# Controles da borda mascarada — 03/10/2026

Continuação: [contraprova uniforme e isolamento do frame 7](TEMPORAL_MATTE_UNIFORM_STUDY.md). O estudo abaixo conserva seus resultados históricos.

Projeto original: `C:/Users/edugu/Downloads/res`. Produção native.13 preservada: os 21 hashes do baseline foram conferidos após os três experimentos. A combinação permanece `pending`; nenhum candidato foi promovido. Oráculo original, probes e tolerância 8 não foram alterados.

## Controles sem máscara

Foram capturados dez PNGs sem perdas: centro, oito amostras isoladas e exposição temporal do mesmo filho. O rig externo permanece no frame 0. A única mudança de desenho frente às capturas invertidas anteriores foi remover `recipeAssetMatte` do filho. A reconstrução dessa propriedade reproduz **os dez hashes de manifests anteriores**; os três arquivos do worker também têm os mesmos hashes. Os manifests e os bytes das fontes desta captura ficaram retidos em [temporal-matte-png-capture-child-unmasked](temporal-matte-png-capture-child-unmasked).

Os três blocos de borda estão fora do bitmap em todas as amostras. Logo não envolvem filtragem da textura nem luminância do PNG. A cobertura geométrica foi integrada independentemente em grade 64×64 por pixel, sem usar a imagem observada para definir a expectativa. O controle sem máscara ficou a até **2,8042** níveis por canal dessa cobertura. Já a diferença entre as pinturas com e sem máscara chegou a **44,25** níveis no mesmo bloco. Dados completos: [temporal-matte-edge-controls.json](temporal-matte-edge-controls.json).

| Bloco, frame 0 | PNG temporal invertido | PNG temporal sem máscara | Diferença |
|---|---:|---:|---:|
| `(214,96)` | 114,25 | 132,00 | −17,75 |
| `(44,96)` | 34,00 | 56,50 | −22,50 |
| `(94,46)` | 171,50 | 173,25 | −1,75 |

Valores iguais nos três canais; cada medida é a média do bloco 2×2. A máscara pode acrescentar cobertura de borda ao conteúdo, portanto a igualdade com o controle sem máscara não é uma nova condição de aprovação. O relatório conserva separadamente as previsões `C` e `C²`. Em particular, algumas amostras ficam próximas de `C²`, enquanto outras perdem cobertura além dessa previsão. A divergência fica localizada no percurso mascarado; a etapa precisa de rasterização ainda não foi provada.

## Código primário da versão instalada

Foi conferido o SHA do executável Chrome for Testing **149.0.7790.0** usado pelo worker. Três arquivos dessa versão foram lidos em memória, sem clone ou cópia de implementação; o [índice de pesquisa](chromium-mask-bounds-study.json) conserva URLs, SHAs e linhas dos símbolos.

O [CSSMaskPainter](https://chromium.googlesource.com/chromium/src/+/149.0.7790.0/third_party/blink/renderer/core/paint/css_mask_painter.cc) limita caixas HTML pelo border box no caminho normal; `no-clip` usa o overflow visual local e descendentes que pintam. O [PaintLayer](https://chromium.googlesource.com/chromium/src/+/149.0.7790.0/third_party/blink/renderer/core/paint/paint_layer.cc) deriva esse limite do overflow visual. Separadamente, [SVGMaskPainter](https://chromium.googlesource.com/chromium/src/+/149.0.7790.0/third_party/blink/renderer/core/paint/svg_mask_painter.cc) recorta o registro de desenho pelos limites do recurso SVG. Isso explica por que ampliar apenas os atributos da máscara não elimina necessariamente o limite da caixa HTML; é uma inferência sobre o percurso, não a identificação de cada erro de pixel. A [norma CSS Masking](https://www.w3.org/TR/css-masking-1/#MaskElement) também descreve o recorte pelos atributos da região da máscara, mas não fixa o resultado deste algoritmo de antialiasing.

## Três candidatos pela API real

Todos seguiram plano → apply → inspection → job → Remotion → FFmpeg → MP4 → QC. Os quatro arquivos temporariamente alterados foram arquivados e restaurados em `finally`, sem conflitos concorrentes. Recibo: [temporal-matte-edge-experiments.json](temporal-matte-edge-experiments.json).

| Candidato | Filho / alpha invertido | Rig / alpha normal | Rig / luminância invertida |
|---|---:|---:|---:|
| Viewport SVG ampliado e um clip vetorial do target | 14,8663; falhou | 9,2433; falhou | 9,7520; falhou |
| Viewport ampliado só na inversão, fundo branco no target, árvore de pares | 11,9491; falhou | 6,2433; passou | 11,4258; falhou |
| `no-clip`, outline transparente de 2 px, árvore de pares | 23,9189; falhou | 6,7284; passou | 24,5808; falhou |

Erros máximos por canal contra o oráculo original. **Nove execuções, dois passes e sete falhas, sem skips/errors; nove MP4s com QC técnico passed e 1.512 probes.** QC técnico não significa aprovação de pixels ou revisão humana.

A margem transparente deixou o filho abaixo do limite no frame 0 (máximo 7,0163), mas introduziu divergências posteriores e no hold (máximo 21,6337). As outras alternativas também pioraram frames parados. Portanto nenhuma é adequada para promoção. Esse resultado invalida a ideia de corrigir apenas o primeiro frame com uma alteração de limites; não autoriza ampliar tolerância ou retirar probes.

## Próxima decisão técnica

Antes de novas combinações de composição, a referência de cobertura precisa de uma contraprova própria: máscara inteiramente branca e PNG inteiramente transparente invertido, sem temporal, com translação fracionária, rotação e escala. Deve separar rasterização local antes do transform de rasterização mundial e preservar os controles sem máscara. A conformidade exata de texels da rodada anterior resolve uma contradição de textura, mas não escolhe entre os modelos `C` e `C²` na borda afim. A adoção de uma referência revisada depende dessa evidência independente; os recibos históricos permanecem como foram executados.

Depois de um candidato consistente, ainda são necessários os sete casos completos, as regressões das capacidades admitidas e inspeção real antes de remover o gate. A revisão humana dos estudos comerciais e os três novos briefs de autonomia permanecem pendentes. A limpeza recursiva anterior foi recusada pela revisão automática (`blocked by policy`); seus alvos não foram excluídos nem houve tentativa de contorno.
