# Exposição + matte sob pai externo — qualificação em curso

03/10/2026, Downloads/res. O incremento não está concluído. Contexto de tempo por nó e correção do fundo da inversão estão implementados no candidato native.13; três probes no primeiro frame ainda ultrapassam o limite de 8. A API conserva `motion_recipe_temporal_matte_moving_external_ancestor_pending` para a combinação. [Compatibilidade](TEMPORAL_MATTE_COMPATIBILITY.md), [dados consolidados](temporal-matte-checkpoint.json), [fontes atuais](temporal-matte-native13-current-sources.json).

## Evidência nova

O baseline native.12 rejeitou o plano real com HTTP422 antes de aplicar ou publicar render. Durante o experimento de admissão, doze MP4s foram produzidos pela API/job/pipeline, todos com QC técnico passed e revisão humana pending. Os resultados de pixels permanecem separados do QC e da admissão atual.

O PNG original 80×96 contém triângulo branco, buraco, região preta opaca, cinza semitransparente e área transparente. Sete variantes cobrem control/child/rig, referência externa independente ou ramo irmão sob pai comum, alpha/luminance e inversão. Há seis frames de conferência: 0/4/7/8/10/15, movimento affine, pivôs, opacidades e hold. Matrizes fonte→target concordam com o cálculo independente em todas as fases, com erro máximo abaixo de 0,002. O contexto usa subframe só dentro da subárvore exposta; pais e referências externas conservam o frame central. Metadados de tempo não impedem a redução no hold.

O primeiro oracle multiplicava geometria e matte antes de rasterizar e deixava a textura vazar fora do viewport. O controle sem exposição também contradisse esse modelo. A pesquisa de [CSS Masking, processamento](https://www.w3.org/TR/css-masking-1/#mask-processing) sustenta a multiplicação dos alphas rasterizados e o [clipping da região SVG](https://www.w3.org/TR/css-masking-1/#MaskElement). O oracle atual calcula os dois alphas separadamente e respeita o viewport/texels de borda, usando somente autoria e o PNG. É uma aproximação de raster, com 17 verificações analíticas próprias; não copia matrizes DOM ou valores do MP4 para produzir o esperado. Os resultados do modelo anterior continuam preservados.

A primeira tentativa com as sete variantes teve quatro passes e três falhas. Expandir o fundo branco da máscara invertida, mantendo a região de clipping, removeu a borda coincidente adicional. A etapa seguinte conferiu os três casos que falharam: luminance invertido no rig passou; alpha invertido no filho e alpha normal no rig ainda falharam. Não aumentar tolerância nem excluir probes; a promoção depende de resolver o conjunto inteiro.

| Variante / frame 0 | Pixel | Esperado | Intermediário | MP4 final |
|---|---|---|---|---|
| Filho, alpha invertido | (214,96) | 122,7601 | 114 | 114 |
| Rig, alpha normal | (138,134) | 49,5720 | 58 | 58 |
| Rig, alpha normal | (140,82) | 98,7567 | 108 | 108 |

O intermediário é PNG capture → H.264 yuv444p CRF1; o final é yuv420p CRF14. Esses três blocos RGB coincidem nos dois vídeos: o encode final não explica a divergência. Todos usam Chromium swangle. O valor observado sozinho não decide se a causa é o desenho, AA do mask local ou quantização da acumulação. Próxima investigação: comparar a ponderação atual `filter: opacity(1/N)` com opacidade de composição e conferir amostras isoladas, com fixtures idênticas, sem trocar motor ou afrouxar o oracle.

## Estado de produção e regressão

A admissão original para pai externo animado foi restaurada após o experimento. Ciclos, paint stack/ancestral exposto da fonte, máscaras legadas, nested overlap e APNG continuam com diagnóstico. O experimento está em `backend/tests/temporal_matte_kernel_diagnostic.py`, fora da coleta padrão; seus testes positivos não representam uma capacidade admitida no estado atual. A prova negativa atual pela API é preservada separadamente.

O runner `scripts/validation/editor-temporal-matte-regression.py` seleciona exatamente os 171 casos únicos da qualificação anterior e acrescenta os 17 do oracle original: **188 passaram, sem failures/errors/skips**. Foram conferidos **22 MP4s das capacidades admitidas e um negativo de APNG**, com provider native.13 e checksums preservados. Inclui sombra/blur, rigs, exposição/hold/shutter zero, fonte/layout/Unicode, mattes, comandos/revisão/undo/replay, trim24/60 e cancelamento. O XML e o recibo do runner são a fonte do resultado, sem contar repetições ou promover os MP4s experimentais. Um teste API adicional confirma HTTP422/pending no estado atual. Worker TypeScript e Ruff passaram. Os recibos native.12 e a inspeção UI anterior ficam históricos; não rodar seus consolidadores sobre fontes native.13.

As fases experimentais não tiveram snapshots de fonte separados antes de cada render; a versão native.13 sozinha não distingue o fundo branco anterior do corrigido. O snapshot atual identifica os bytes da regressão, não transforma os ensaios anteriores em qualificação da versão final. Preservar esta limitação no próximo incremento.

Nenhum repositório ou bundle adicional de estudo foi baixado. Revisão humana dos estudos comerciais, três briefs novos de autonomia e limpeza anterior recusada continuam pendentes. Esta rodada é progresso técnico e evidência de falha; não conclusão do objetivo.
