# Exposição temporal — prova técnica e limites

Implementação original de `studio.temporal-exposure.v1` na receita existente `velocity_blur`, sobre CreativeDocumentV1/MotionGraphV1, Remotion e FFmpeg. Compiler v4/library 7/provider native.9; finalizador contextual v1.3.0. [Contrato, migração e leitores](TEMPORAL_EXPOSURE_COMPATIBILITY.md). Nenhum código dos editores estudados foi incorporado, nenhuma dependência foi instalada e nenhum motor foi trocado.

A política opt-in amostra midpoints centrados no frame, recorta ao intervalo da receita e renormaliza os pesos. Pais externos permanecem no frame central, conforme contrato. Subárvores comprovadamente idênticas usam uma só renderização: shutter zero e repouso preservam nitidez sem acumular a quantização da soma de amostras. Componentes desconhecidos não autorizam essa redução. As observações DOM registram amostras, pesos e redução; não afirmam cobertura de pixels.

## Prova real API → job → MP4

Cinco variantes de dois segundos, 320×320/30 fps/60 frames, com duas cenas, retângulos semitransparentes em movimento, apoio parado e corte. Mesmos materiais e tracks originais. Planejamento/aplicação/inspeção/revisão, job local, checksum de manifesto/vídeo e QC passaram. Quatro variantes com exposição têm 16 probes independentes cada, nos frames 4/34. O controle não contém receita de blur. As variantes usam explicitamente qualidade high.

| Amostras | Shutter | Render total observado | Bundle | Seleção | Render/encode gráfico | MP4 | Maior erro de luminância nas bordas |
|---|---:|---:|---:|---:|---:|---:|---:|
| Controle 0 | — | 12,718 s | 3,314 s | 3,598 s | 3,710 s | 8.189 B | — |
| 2 | 180° | 11,844 s | 3,202 s | 2,842 s | 3,738 s | 8.107 B | 3,7232 |
| 8 | 180° | 11,203 s | 3,259 s | 2,487 s | 3,558 s | 8.429 B | 6,4028 |
| 16 | 180° | 11,812 s | 3,191 s | 2,695 s | 3,913 s | 8.326 B | 6,9711 |
| 8 | 0° | 11,562 s | 3,021 s | 3,027 s | 3,620 s | 8.189 B | 4,4960 |

Tempo gráfico não isola compilação canônica, finalização posterior ou pico de CPU; preparação dos assets foi 0 ms arredondados porque essas fixtures são gráficos sem assets. Memória livre e concurrency estão nos recibos. Uma observação por variante não mede p95 nem demonstra desempenho em 1080p. As diferenças de tempo não comprovam que mais amostras sejam mais rápidas.

Shutter zero reproduziu **todos os 60 frames RGB decodificados** do controle, diferença máxima zero. No repouso de 2/8/16 samples, a redução usa uma amostra; a comparação dos frames inteiros 10/29/40/59 conserva diferenças de codec, média observada ≤0,117 por canal e máximo ≤17. Isso não é identidade byte a byte dos vídeos nem prova de leitura humana.

## Tipografia durante exposição e hold

Dois jobs adicionais usam fonte real vinculada por checksum, unidades Unicode e medição DOM final: `AÇÃO` decomposto e palavras em múltiplas linhas. No completeFrame authored, a exposição ainda contém amostras da entrada. O compilador rejeita um readingHold sem margem; a inspeção só indica hold quando todas as amostras estão completas. Nos casos corrigidos, o hold efetivo começa nos frames 20 e 11, respectivamente, e a composição reduz a uma amostra.

Comparação dos frames completos decodificados: início/fim do hold com erro médio 0,00222 e 0,02415 por canal; repouso/controle de stagger zero com 0,18951 e 1,11861. Texto, fonte, layout, revisões, vídeo, frames observados e checksum da fonte constam em `temporal-typography-render`. A fonte licenciada local não foi copiada para a evidência retida.

## Contraprovas, compressão e compatibilidade

O experimento inicial conservou CameraMotionBlur instalado e encontrou shutter zero com falha de browser e entrada com fase diferente do frame central. Esse histórico não redefine silenciosamente o legado: shutter zero sem política recebe diagnóstico e correção explícitos, e os caminhos antigos continuam disponíveis para os demais parâmetros.

As primeiras medições de bordas isoladas falharam, inclusive no próprio controle nítido, com JPEG e depois com PNG intermediário. Capturas PNG reconstruídas no browser distinguiram a rasterização da compressão: 90 probes em 10 capturas, erro máximo de luminância 4,4998, zero shutter com cor exata nos probes. São diagnósticos reconstruídos, **não** substitutos da prova pela API.

A finalização contextual ignorava `quality` e fixava CRF 23. Agora respeita draft/standard/high em 28/23/18, incluindo o primeiro encode nativo e recibos. Standard continua com CRF 23; suas falhas históricas permanecem registradas. A mudança é limitada aos parâmetros/recibos desses encodes e tem versão própria.

A medição atual integra um bloco alinhado de 2×2 pixels, com oráculo geométrico independente sobre o mesmo footprint. O limite de erro continua 8. O teste exige que uma fase errada de um frame seja rejeitada com erro superior a 20. Essa escolha de footprint considera que [yuv420p compartilha crominância por bloco de 2×2](https://ffmpeg.org/doxygen/8.1/pixfmt_8h.html); não implica identidade da cor de cada pixel comprimido. PNG intermediário é configurado conforme [renderMedia](https://www.remotion.dev/docs/renderer/render-media). O [aviso oficial de cor do CameraMotionBlur](https://www.remotion.dev/docs/motion-blur/camera-motion-blur) e as diferenças finitas observadas continuam relevantes: soma sRGB no browser não é exposição linear/HDR.

## Evidência reproduzível e trabalho restante

`temporal-exposure-receipt.json` consolida os testes únicos, SHA das fontes executadas, resultados, artefatos, probes, tempos e diagnósticos históricos. `temporal-exposure-runtime-study.json` contém 22 checks do sampler/reducer original. Os XMLs distinguem regressão, contratos, sete jobs novos e experimentos que falharam; não somar rodadas sobrepostas. A regressão revalida máscara/stroke/parenting/blur legado, mattes, trim/speed em fontes 24/60 fps, fonte/layout, comandos e áudio real na captura nova.

Consolidação: **111 casos pytest únicos aprovados**, sem failures/errors/skips nesta seleção; Ruff, sintaxe dos runners e TypeScript ES2022 passaram. Esse total sobrepõe rodadas de contrato/regressão; não é uma contagem de vídeos nem execução da suíte inteira do repositório.

Artefatos para inspeção: [controle nítido](temporal-exposure-render/samples-0-shutter-180/exposure.mp4), [duas amostras](temporal-exposure-render/samples-2-shutter-180/exposure.mp4), [oito amostras](temporal-exposure-render/samples-8-shutter-180/exposure.mp4), [dezesseis amostras](temporal-exposure-render/samples-16-shutter-180/exposure.mp4), [shutter zero](temporal-exposure-render/samples-8-shutter-0/exposure.mp4), [Unicode com exposição](temporal-typography-render/unicode/typography.mp4) e [palavras com exposição](temporal-typography-render/wrapped_words/typography.mp4). Fixtures técnicas curtas não substituem os três estudos editoriais de quinze segundos.

Revisão humana, preferência cega dos três estudos, quatro eixos ≥4/5 e três briefs inéditos continuam pendentes. Esta prova não promove qualidade comercial nem autonomia. Combinações novas sob rigs afins, exposição aninhada e extremos no celular ainda precisam de pixels reais. Máscaras CSS legadas e matte sob ancestral externo em movimento retornam pending com correção. Não declarar roto/tracking/3D/morph/refração por esta implementação.

Os clones de pesquisa e bundles DOM anteriores continuam com limpeza pendente: a revisão automática recusou a exclusão com `blocked by policy`, sem explicar outra razão. Não houve tentativa de contornar a recusa nem alegação de espaço recuperado.

O bundle novo da contraprova PNG também teve sua exclusão nativa rejeitada antes da execução. A identificação, existência, tamanho lógico e hashes estão em `temporal-raster-diagnostic/temporary-bundle.json`; caminho observado `C:/Users/edugu/AppData/Local/Temp/remotion-webpack-bundle-7lEY6k`. Não foi removido por outro mecanismo.
