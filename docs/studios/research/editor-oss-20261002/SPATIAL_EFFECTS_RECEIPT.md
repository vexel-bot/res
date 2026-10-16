# Sombra canônica e desfoque espacial — native.12

Projeto: `C:/Users/edugu/Downloads/res`; 03/10/2026. **171 casos pytest únicos passaram, além de 23 verificações do helper TypeScript. Foram conservados 22 MP4s de jobs reais com checksum, revisão e QC.** As três fixtures novas passaram 570 probes de pixels. Revisão humana e autonomia continuam pendentes.

## Comportamento corrigido

O compilador já persistia `editorialShadow={x,y,blur,color,opacity}`, mas o runtime lia aliases diferentes e ignorava a opacidade. Agora executa os cinco campos canônicos; a opacidade atenua a sombra e conserva a fonte. A projeção valida sombra/depth usando os contratos existentes, normalizando defaults somente no manifesto. Dados inválidos recebem diagnóstico com target; autoria/documento não são reescritos. Blur espacial da track ou depth vem antes do drop-shadow. Parâmetros conflitantes estático/animado são rejeitados.

A fixture fortalecida revelou uma segunda falha: oito amostras do blur animado 0→16 entre os frames 0 e 1 desviaram do limite original. O intermediário 444/CRF1 já continha a perda; não modificar novamente o finalizador nem ampliar a tolerância. Um job controlado confirmou bordas nítidas nos sigmas .25/.75 sob o backend padrão. A reconstrução do mesmo snapshot com ANGLE/SwiftShader passou os 190 probes intermediários. Depois disso, fixamos `chromiumOptions.gl=swangle` na seleção e no render, e repetimos os jobs finais e regressões.

Native.12 registra `graphicsBackend=chromium_swangle`. CreativeDocumentV1/MotionGraphV1, compiler v4, library 7, política de exposição v1 e finalizador 1.4.0 permanecem. Não houve engine nova, cópia de implementação de editor ou API paga. [Contrato e decisão anterior à alteração](SPATIAL_EFFECTS_COMPATIBILITY.md).

## Provas atuais

Cada fixture percorre API → plano → apply → inspeção → job → MP4 → QC. O oráculo original combina integral gaussiana, composição alpha/source-over e integração espacial independente; não chama o interpolador do renderer. Os limites permanecem luminância <8 e canal <12 em blocos 2×2.

| Fixture de 1 s, 320×320, 30 fps | Probes finais | Erro máximo de luminância | Tempo observado do job |
| --- | ---: | ---: | ---: |
| Controle sem efeitos | 190 | <0,0001 | 10,562 s |
| Sombras dura/deslocada/transparente/soft, blur estático/animado, blur+sombra | 190 | 2,3947 | 9,407 s |
| Mesma cena, exposição do blur animado | 190 | 3,6614 | 8,093 s |

No frame 0 a exposição usa os oito sigmas .25/.75/1.25/1.75/2.25/2.75/3.25/3.75, e no frame 1 continua com oito amostras. Nos frames 4/8/29 reduz a uma amostra por igualdade dos draw inputs. O probe discriminante passou de 255 no controle central para 188,5 no MP4 exposto: diferença de luminância 66,5. Portanto o teste verifica efeito nos pixels, além do recibo de amostragem. Os intermediários foram conservados e seus hashes conferidos; não substituem a prova do MP4 final.

Regressões: quatro rigs afins com pivô/pai/opacidade/scopes disjuntos; exposição 0/2/8/16 e shutter zero; Unicode/fonte final/layout/hold; seis mattes PNG alpha/luma/inversão/contain/cover; APNG rejeitado sem publicação; máscara/stroke/parenting/blur legado; trims/speed 24/60; comandos/replay/revisão obsoleta/cancelamento; três proporções com áudio e três qualidades de encode. Os quatro rigs passaram 360 probes, máximo 7,3662, e 24 comparações de geometria dentro de .15 px. Controle/shutter zero continuam iguais nos 60 frames RGB. Overflow tipográfico bloqueia a saída com diagnóstico específico.

Os 22 vídeos retidos são 3 efeitos espaciais +4 rigs +5 exposições +2 tipografias +6 mattes +2 comandos. Casos tipográficos false/true passam quatro testes; cada pasta conserva o último caso true. Outros renders suplementares aprovados nos testes não aumentam a contagem de artefatos retidos.

Os XMLs atuais contêm 25, 134 e 37 execuções; deduplicação resulta em 171 casos. Apesar do nome `pure-regression`, o XML de 134 também inclui três casos com renderer real; eles reaparecem na suíte nativa e não são somados duas vezes. Não houve failure/error/skip nestas três rodadas. [Recibo consolidado e hashes](spatial-effects-receipt.json); [fonte congelada no início da qualificação](spatial-effects-native12-sources.json). O consolidator rejeita drift dos bytes, provider/backend/qualidade divergentes, checksum incorreto e qualquer falha atual.

## Pesquisa e contraprovas

Chromium observado: Google Chrome for Testing 149.0.7790.0. O [DEPS da tag](https://chromium.googlesource.com/chromium/src/+/refs/tags/149.0.7790.0/DEPS) fixa Skia `0cb35533022b3912904831c2290680bb8eea0363`. O [código primário de blur](https://skia.googlesource.com/skia/+/0cb35533022b3912904831c2290680bb8eea0363/src/core/SkBlurEngine.cpp) contém caminhos discretos/caixas e escolhas por backend/build. Isso orientou o experimento; não prova qual ramo o binário executou. Semântica de sombra e sigma segue a [referência W3C Filter Effects](https://www.w3.org/TR/filter-effects-1/#funcdef-filter-drop-shadow). [Inventário de URLs, hashes e binário](spatial-effects-browser-sources.json): cinco fontes lidas em memória, sem novo clone ou árvore de código retida.

Preservados como históricos: native.10/sombra com 55 probes reprovados; native.11/fixture forte com uma falha final e duas no intermediário; job controlado de sigma pequeno com seis probes reprovados; fixture suave anterior aprovada, que não substitui a prova forte. O diagnóstico GL reconstruído também não é contado como novo job API aprovado. Os recibos anteriores permanecem com seus próprios providers/fontes; não promovê-los executando consolidators antigos contra produção atual.

## Limites e próximos passos

São fixtures técnicas, sem nota estética, preferência cega ou aprovação comercial. Não qualificam todos os sigmas/conteúdos/transformações/hardwares; standalone subpixel e blur extremo conservam aproximação raster/custo não abrangidos aqui. Não há promessa de p95 ou velocidade de prévia a partir de três renders pequenos. H.264 intermediário/final e conversão de cor continuam com perdas finitas, mesmo com captura PNG. Pais externos à exposição ficam no frame central; nested com overlap permanece diagnosticado. Exposição+matte sob pai externo animado e outros stacks avançados continuam pendentes. A UI de parâmetros espaciais não foi ampliada nesta rodada.

Próximo incremento: expor parâmetros canônicos de sombra/depth no inspetor, com prova de UI/revisão, e tratar combinações restantes antes de promover estudos comerciais. Os três estudos dirigidos A/B/controle precisam de avaliação humana real nos quatro eixos; três briefs novos/autonomia vêm depois. Não atribuir notas automaticamente nem revalidar os vídeos comerciais históricos apenas pela versão nova do renderer.

A revisão automática de aprovação rejeitou anteriormente a exclusão recursiva dos clones e bundles de pesquisa com `blocked by policy`. A limpeza continua pendente, sem contorno ou nova tentativa sobre esses alvos. Nesta investigação não houve novos clones/bundles permanentes; os jobs usam o ciclo temporário normal do runner.

Reproduzir o consolidado na raiz: `python scripts/validation/editor-spatial-effects-receipt.py`. Para os testes usar o diretório `backend` e as três seleções registradas nos XMLs; conservar artefatos via variáveis `*_EVIDENCE_DIR`. Os scripts de diagnóstico pequeno/GL são pesquisa separada e não entram na suíte de qualificação.
