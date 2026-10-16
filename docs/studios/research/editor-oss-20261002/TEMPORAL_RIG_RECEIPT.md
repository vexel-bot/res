# Exposição temporal em grupos transformados — native.10

Projeto: `C:/Users/edugu/Downloads/res`. Rodada de 03/10/2026. **146 casos pytest únicos passaram; 19 MP4s de jobs reais foram conservados com checksum, revisão e QC.** Os quatro casos afins passaram 360 probes de pixels e 24 comparações de geometria. Revisão humana e autonomia continuam pendentes. CreativeDocumentV1/MotionGraphV1, Remotion/FFmpeg, compiler v4, library 7 e exposição v1 permanecem.

## Comportamento e prova

A fixture original tem dois grupos, filho, pivôs centrais, bordas, rotações, escalas anisotrópicas e opacidades multiplicadas. Tracks canônicas animam até frame 8 e mantêm a pose. Exposição do rig amostra rig e filho; exposição do filho mantém os pais externos no frame central. Intervalos disjuntos são aceitos; overlap em ancestral/filho com política nova retorna `motion_recipe_temporal_nested_target_pending:<target>`, inclusive na projeção persistida. O lowering já rejeitava nested legado e conserva esse diagnóstico.

O oráculo original calcula matrizes e recorta polígonos sem chamar o interpolador/matriz do runtime. Compõe pivôs e offsets das bordas, verifica bounds DOM da primeira amostra e calcula cobertura/opacidade média em blocos alinhados 2×2. Frames: 0, 4, 6, 7, 10 e 29. Critérios: luminância <8 em escala 0–255 e geometria <0,15 px. A ordem das matrizes e transformação de origem seguem o [modelo de transformação W3C, publicado como Candidate Recommendation](https://www.w3.org/TR/css-transforms-1/#transform-rendering); aplicação à fixture é cálculo e evidência local.

| Caso / vídeo real | Probes | Maior erro de luminância | Maior erro de geometria |
|---|---:|---:|---:|
| [Controle](temporal-rig-render/control/rig.mp4) | 90 | 5,0422 | 0,000245 px |
| [Grupo exposto](temporal-rig-render/rig/rig.mp4) | 90 | 5,6332 | 0,000088 px |
| [Filho exposto](temporal-rig-render/child/rig.mp4) | 90 | 5,1722 | 0,000136 px |
| [Intervalos separados](temporal-rig-render/disjoint/rig.mp4) | 90 | 4,6542 | 0,000063 px |

Cada linha percorre API → plano → apply → inspeção/revisão → job → Remotion → finalização FFmpeg → MP4/QC → pixels decodificados. Dispatch Celery é substituído pela execução local do job; renderer, encoder, fontes e mídia são reais. A retenção do intermediário copia o resultado efetivo. Bounds DOM não alegam cobertura de pixels; essa prova está em pixelChecks.

## Correções e diagnóstico

Removido `filter: blur(0px)` quando não há efeito espacial: em PNG reconstruído, erro máximo caiu de 5,42 para 2,92 e no canto problemático de 5,42 para 1,24. Valores não zero e presença de shadow conservam o ramo de efeitos. Isso melhora rasterização; não qualifica as sombras existentes.

Intermediário high passou a H.264/yuv444p/CRF1 com captura PNG. A tentativa CRF0 foi rejeitada pelo Remotion instalado; não houve bypass. PNG é lossless, mas RGB/YUV e o vídeo intermediário têm precisão finita/perdas. [Documentação Remotion](https://www.remotion.dev/docs/renderer/render-media#crf); intervalo instalado verificado em crf.js de 4.0.527.

O final CRF18 ainda perdeu bordas: rig 9,01 e filho 8,52. A [comparação de estágios](temporal-rig-raster/latest-stage-pixels.json) localizou a perda no encoder final. A [grade controlada](temporal-rig-raster/final-encode-study/receipt.json) separou conversão 4:2:0 conservada em FFV1, preset medium e CRFs 16/14/12. Medium/18 e veryfast/16 não passaram todos; veryfast/14 passou todos. A [documentação FFmpeg/libx264](https://ffmpeg.org/ffmpeg-codecs.html#libx264_002c-libx264rgb) descreve CRF e preset como opções distintas. Esses resultados são locais, não garantia universal de qualidade.

Finalizador contextual **1.4.0** usa high=14; draft=28 e standard=23 permanecem. Native.10 identifica runtime/validação novos. Recibos distinguem qualidade, CRF e pixelFormat do intermediário e final. MP4s afins finais medem 11,0–11,4 KB por 1 segundo nesta fixture; não projetar isso para mídia comercial. [Compatibilidade e decisões antes das alterações](TEMPORAL_RIG_COMPATIBILITY.md). Rodadas anteriores permanecem históricas; a pasta final18 tem controle já substituído por CRF14 e isso está declarado na compatibilidade.

## Regressões e integridade

Os XMLs e [recibo consolidado](temporal-rig-receipt.json) registram 146 casos únicos: grafemas/unidades/hold/fontes/layout, nested novo/legado, matte alpha/luminância/inversão/contain/cover, APNG rejeitado sem publicação, legado temporal/máscara/stroke/parenting, trim/speed em 24/60 fps, inspeção/comandos/replay/revisão, stale visual-review, cancelamento/checksum e áudio em três proporções. Os 19 vídeos retidos são 4 rigs +5 exposição +2 tipografia +6 mattes +2 comandos. Outros renders passaram no pytest; não aumentar a contagem de artefatos conservados. Tipografia temporalFalse/True passa quatro casos, mas cada pasta por variante conserva o último temporalTrue.

Uma asserção negativa falhou porque esperava overflow sempre no frame 0; as duas abas podem detectar primeiro o frame 1. Produção já interrompia sem saída. O teste corrigido exige target exato, diagnóstico de reading floor, frame 0 ou 1 e nenhuma publicação; passou na repetição isolada. XML com falha permanece; consolidado usa último resultado por caso. Não somar repetições.

`temporal-rig-sources.json` vincula bytes de produção/fixture e o consolidator rejeita drift. TypeScript ES2022, Ruff e diff-check dos arquivos de código passaram. Licenças do pacote de fontes conservam checksum íntegro, sem alteração nesta rodada; fontes instaladas de teste não foram redistribuídas. Nenhuma dependência/editor/engine foi instalado nem implementação de terceiros copiada nesta rodada.

Rigs levaram 7,3–11,9 s por execução local do job; fases constam no recibo. Uma regressão legada coincidiu com outra suíte de render. Não anunciar p95, realtime, redução de CPU ou desempenho comercial.

## Limites e próximo incremento

Sombras têm defeito anterior: autoria `{x,y,blur,color,opacity}` não corresponde aos aliases lidos no runtime, e opacity é ignorada. Shadows e blur espacial não zero aguardam prova específica; este recibo não os qualifica. Próximo incremento: executar campos canônicos, validar projeção persistida e comprovar deslocamento/atenuação/soft blur em API/job/MP4, versionando antes da alteração.

Mattes sob pai externo animado e máscaras CSS legadas com exposição continuam pendentes. Exposição qualificada é local_subtree em SDR/sRGB de precisão finita; não afirmar HDR/linear-light, blur global ou nested N×M. Três estudos comerciais de 15 s, preferência cega, quatro eixos humanos ≥4/5 e três novos briefs/autonomia continuam pendentes; QC/testes não atribuem notas humanas.

A limpeza foi rejeitada pela revisão automática com `blocked by policy` para o bundle verificado `tmp/temporal-rig-raster-bundle`: 50 arquivos/26.640.368 bytes lógicos. [Registro](temporal-rig-raster/temporary-bundle.json). Clones/bundles anteriores continuam pendentes; nenhuma liberação de espaço confirmada ou tentativa de bypass. Artefatos pequenos de fonte/diagnóstico/checksum permanecem como evidência.
