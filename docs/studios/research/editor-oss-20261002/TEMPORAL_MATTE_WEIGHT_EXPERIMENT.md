# Experimento de ponderação — native.14 temporário

03/10/2026. Projeto original em Downloads/res. Investigação das três divergências retidas no checkpoint native.13. Nenhuma tolerância, fixture, frame ou probe será alterado. Não é qualificação de produção.

Arquivos experimentais: `workers/remotion-benchmark/src/temporal-exposure.tsx` troca somente `filter: opacity(1/N)` por `opacity: 1/N`; `backend/app/domain/studios/temporal_exposure.py` remove temporariamente o diagnóstico de admissão da combinação para executar a prova pela API; `backend/app/providers/studios/remotion_render.py` identifica os dois providers como `4.0.527-native.14` durante o ensaio. CreativeDocumentV1, MotionGraphV1, TemporalExposureV1, compilador v4 e biblioteca v7 conservam seu significado e leitores. Não há migração canônica nem mudança de contrato UI. A versão native.14 identifica o experimento, não uma capacidade aprovada.

O runner conserva os bytes originais e candidatos, congela SHAs antes dos testes e restaura os originais em `finally`. Detecta edição concorrente antes de restaurar. O estado de produção após o experimento volta a native.13 com a admissão pending. Resultados anteriores permanecem históricos. A variante com filtro serve de contraprova se for necessária, com outro diretório e snapshot próprios.

Primeiro conjunto: alpha invertido no filho, alpha normal no rig, luminance invertido no rig; seis frames e 168 probes originais por caso. API → plano → apply → inspection → job → MP4 → QC → pixels. Aprovação depende de todos os casos originais e regressões, além da revisão humana separada.

## Resultado do primeiro ensaio

O candidato `composition-opacity` não resolveu as divergências. O job real terminou com QC técnico, mas os três casos continuaram fora do limite: filho/alpha invertido teve erro máximo 8,0178 no frame 4 em `(110,100)`; rig/alpha normal manteve 8,4280 e 9,2433 no frame 0; rig/luminance invertido passou a ter uma divergência de 8,1095 no frame 4. Portanto, não há base para trocar o filtro pela propriedade `opacity` nem para remover a admissão pending. O `run.json` registra `exitCode: 1` e restauração byte a byte dos arquivos de produção.

Esse resultado também afasta a hipótese simples de que a ponderação CSS seja a causa única. As diferenças mudaram de posição em dois casos, então a alteração afeta a rasterização, mas não torna a saída fiel ao oracle. O próximo ensaio deve isolar a pintura de uma única amostra e comparar o PNG intermediário antes de testar outra composição; qualquer novo candidato precisa de um snapshot próprio e do mesmo conjunto de probes.

A contraprova `filter-opacity`, com o mesmo runner e snapshot, reproduziu o estado native.13: filho/alpha invertido falhou apenas em `(214,96)` no frame 0 com 8,7601; rig/alpha normal falhou em `(138,134)` e `(140,82)` com 8,4280 e 9,2433; rig/luminance invertido passou. O XML contém três execuções reais, todas com o restante do pipeline e restauração confirmada. Isso separa a variação do ensaio de composição da causa persistente nos probes do rig e do filho.

## Amostras isoladas

O manifesto capturado da variante `rig-external-alpha-normal` foi congelado e usado para nove diagnósticos de um único sample: centro e os oito tempos `0,015625 … 0,234375` do shutter de 180 graus. Em cada manifesto, o valor de cada track foi fixado no tempo do sample dentro do rig e no frame central fora dele; a receita temporal foi removida somente do diagnóstico. O PNG original, o asset matte, as fontes do worker e os checksums dos nove MP4s estão em [temporal-matte-isolated-samples](./temporal-matte-isolated-samples).

As nove pinturas isoladas em MP4 ficaram abaixo do limite, todas com erro máximo 6,2433. Nos dois probes persistentes do vídeo temporal, a média dos oito MP4s isolados foi `{53,53,53}` e `{105,105,105}`, enquanto o vídeo temporal observado foi `{58,58,58}` e `{108,108,108}`; os valores esperados do oracle eram 49,5720 e 98,7567. Assim, o matte e a transformação isolados não explicam a falha. A diferença aparece na acumulação de camadas, com excesso de 5 e 3 níveis no vídeo temporal antes do encode final.

### Captura PNG sem perdas

Para eliminar a hipótese de quantização do H.264, o mesmo manifesto real e os nove manifests isolados foram renderizados diretamente pelo `@remotion/renderer` pinado em PNG, com SwiftShader. A captura está em [temporal-matte-png-capture](./temporal-matte-png-capture), com recibo, hashes dos fontes e análise de pixels. Os nove PNGs isolados repetiram o limite máximo 7,2433; nos probes persistentes, a média isolada foi `{54,54,54}` e `{106,106,106}`, contra `{58,58,58}` e `{108,108,108}` no PNG temporal. Portanto os excessos de 4 e 2 níveis já existem na composição Chromium e não são introduzidos pelo encode H.264. A admissão permanece pending.

Essa leitura é compatível com a semântica documentada para `plus-lighter`: o operador soma as contribuições pré-multiplicadas e é voltado a cross-fades. A especificação também exige grupos isolados e a ordem de filtro, máscara, blending e composição; o comportamento observado aqui é uma limitação/nuance da acumulação HTML/CSS com oito grupos mascarados, não uma prova de que o oracle esteja errado. [Compositing and Blending](https://www.w3.org/TR/compositing-1/#compositingandblendingorder), [MDN mix-blend-mode](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/mix-blend-mode).

Conclusão operacional: manter a admissão `motion_recipe_temporal_matte_moving_external_ancestor_pending`. O próximo candidato precisa trocar a acumulação de grupos por uma composição de amostras que preserve a soma ponderada em um grupo controlado, e deve repetir as sete variantes, os 168 probes e a regressão de 188 casos antes de qualquer promoção. Não elevar a tolerância e não converter os MP4s experimentais em aprovação.

Também foi testada a variante `direct-root`, que move `plus-lighter` para a raiz DOM quando a amostra não é um fragmento. Ela piorou o rig: além dos dois probes originais, produziu dezenas de divergências de até 21,9893; o filho com fragmento permaneceu igual. O candidato foi descartado e os arquivos foram restaurados. A tentativa reforça que o limite está na fronteira de composição do grupo, não em uma simples propriedade do elemento raiz.

A variante `nested-opacity`, com uma superfície externa para `plus-lighter` e uma superfície interna para `filter: opacity(1/N)`, reproduziu exatamente os resultados do filtro original: filho com um probe residual, rig com dois e luminance invertido passando. A separação das superfícies, sozinha, também não corrige a acumulação.

Com a mesma estrutura, mas `opacity: 1/N` na superfície interna (`nested-composition-opacity`), o resultado foi o mesmo da variante de opacidade direta: os três casos permaneceram fora do limite, com a divergência do filho deslocada para o frame 4 e a luminance invertida também falhando. A família de testes elimina a troca simples de propriedade e de ordem de superfícies como correção suficiente.

Referências primárias: [ordem de composição e isolamento](https://www.w3.org/TR/compositing-1/#compositingandblendingorder), [filtro opacity](https://www.w3.org/TR/filter-effects-1/#funcdef-filter-opacity). A hipótese de quantização é uma investigação; essas especificações não comprovam a causa dos pixels locais.

## Continuação: limite da conclusão sobre acumulação

O [estudo de agrupamento e texels](TEMPORAL_MATTE_GROUPING_STUDY.md) acrescenta cinco candidatos congelados e um diagnóstico PNG isolado do filho invertido. Três alternativas resolveram os dois casos de rig, mas nenhuma passou todos os probes originais. No filho, a diferença temporal versus média isolada é apenas −0,625 no ponto residual; a borda já diverge nos samples. A conformidade 1:1 também encontrou suavização de textura indevida no oráculo. As conclusões acima sobre acumulação são específicas dos probes do rig, não uma explicação geral da falha. Nenhum recibo histórico ou limite foi reescrito para produzir aprovação.
