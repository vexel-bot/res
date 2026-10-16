# Matte e exposição temporal — qualificação técnica native.14

03/10/2026. A combinação de PNG matte com exposição temporal sob ancestrais externos móveis foi incorporada ao código original de `C:/Users/edugu/Downloads/res`. O renderer passa de `4.0.527-native.13` para `4.0.527-native.14`; o finalizador contextual passa de `1.4.0` para `1.4.1`, com qualidade high em CRF 10. A admissão é técnica e específica às fixtures documentadas. Revisão humana dos estudos comerciais, preferência cega, três briefs novos de autonomia e inspeção desta combinação na UI real permanecem pendentes.

[Recibo de incorporação e fontes atuais](temporal-matte-native14-local-admission/admission.json). [Qualificação anterior à incorporação](temporal-matte-quantized-qualification.json). O segundo recibo conserva o estado `productionAdmission:pending` daquele instante; o primeiro registra os bytes incorporados e os quatro testes dos contratos atuais aprovados. Serviços compartilhados não foram reiniciados nesta rodada; não há alegação de que uma instância antiga em memória tenha sido atualizada.

## O que mudou na execução

- A exposição temporal combina as imagens por uma árvore balanceada de `plus-lighter` e opacidade de composição. Cada folha conserva peso `1/N`, inclusive com número ímpar de amostras. Amostras, intervalos, tempo dos ancestrais externos, diagnóstico e redução de conteúdo parado permanecem os mesmos.
- A máscara usa clip vetorial do target, viewport ampliado e uma margem transparente que evita o recorte arredondado da caixa coincidente. Na inversão, subtrai a máscara fonte de uma máscara SVG branca limitada pelo target; evita a perda de complementaridade junto à borda da imagem fonte.
- A combinação antes recusada pelo diagnóstico `temporal_matte_moving_external_ancestor_pending` passa a compilar. Permanecem os diagnósticos de política inválida, binding obsoleto, legado sem controle, ciclos, pais ausentes, exposição aninhada sobreposta e hold de leitura insuficiente.
- O finalizador high usa CRF 10 e registra esse valor. Draft continua 28; standard continua 23. A intermediária high permanece H.264/yuv444p/CRF 1. O percurso visual continua Remotion; áudio e finalização continuam FFmpeg.

Os cinco arquivos de execução são **idênticos, byte a byte, aos do candidato validado**; não houve limpeza estética ou outra mudança entre a prova e a incorporação. Três módulos de teste atualizaram expectativas dos contratos atuais. O diagnóstico histórico `backend/tests/temporal_matte_kernel_diagnostic.py`, suas probes, tolerâncias e vereditos ficaram intactos e arquivados.

## A referência independente

Os controles anteriores já haviam provado que o oráculo histórico suavizava indevidamente texels em escala 1:1. Uma outra divergência vinha de tratar coordenadas projetadas como contínuas. A investigação leu nove fontes primárias selecionadas em memória, com URL imutável e SHA, sem clone ou cópia de implementação. [Inventário SwiftShader](swiftshader-subpixel-study.json).

O [DEPS do Chromium 149.0.7790.0](https://chromium.googlesource.com/chromium/src/+/149.0.7790.0/DEPS) fixa SwiftShader em `89556131bf9d48af3c5c9fbb9a3322e706da89a3`. O [BUILD.gn](https://swiftshader.googlesource.com/SwiftShader/+/89556131bf9d48af3c5c9fbb9a3322e706da89a3/src/Pipeline/BUILD.gn) declara precisão legada; [VkConfig.hpp](https://swiftshader.googlesource.com/SwiftShader/+/89556131bf9d48af3c5c9fbb9a3322e706da89a3/src/Vulkan/VkConfig.hpp) define quatro bits subpixel nesse modo. [VertexRoutine.cpp](https://swiftshader.googlesource.com/SwiftShader/+/89556131bf9d48af3c5c9fbb9a3322e706da89a3/src/Pipeline/VertexRoutine.cpp) arredonda as coordenadas projetadas para a grade fixa. O [Skia QuadPerEdgeAA](https://skia.googlesource.com/skia/+/0cb35533022b3912904831c2290680bb8eea0363/src/gpu/ganesh/ops/QuadPerEdgeAA.cpp) informa o estudo da faixa de antialiasing de meio pixel e da cobertura interpolada; os metadados selecionados estão em [skia-quad-coverage-study.json](skia-quad-coverage-study.json).

Uma consulta WebGL em navegador novo do renderer confirmou `SUBPIXEL_BITS:4` e ANGLE/SwiftShader. O navegador Google Chrome for Testing 149.0.7790.0 foi conferido por SHA. Apenas esse navegador próprio foi fechado; nenhum navegador do usuário foi encerrado. [Recibo de runtime](swiftshader-subpixel-runtime.json).

A nova referência `swiftshader4_affine_png_v1` deriva geometria dos parâmetros authored, projeta vértices em passos de 1/16 pixel, interpola cobertura/UV por triângulos e separa multiplicações quantizadas de alpha. Não usa matrizes DOM nem pixels observados para calcular o esperado. Preserva a textura premultiplicada, amostrada no centro do pixel, e distingue cobertura do conteúdo, imagem e clip. A grade veio da fonte e da capacidade WebGL, não de ajuste aos probes que falharam.

| Contraprova | Comparações | Resultado |
|---|---:|---|
| 64 PNGs novos: 16 fases de translação e 16 de escala, com/sem máscara | 1.674.508 pixels | Modelo contínuo chega a 8,7047; grade + alpha em bytes tem máximo 1 |
| 28 controles afins uniformes retidos, reavaliados | 179.328 pixels verificados | Máximo 5; escala não uniforme tem erro 0 |
| 7 controles texturizados retidos, todos os pixels de cada imagem | 716.800 pixels | Máximo 5 na inversão; imagem direta e máscara normal têm máximo 1 |

[Fases subpixel](temporal-matte-subpixel-phase-controls/analysis.json), [quads e clips](temporal-matte-quad-raster-conformance.json), [textura afim](temporal-matte-textured-source-conformance.json). Os 28 e sete controles retidos não foram contados como capturas novas. A referência não anuncia precisão para perspectiva, malhas degeneradas, pequenos quads colapsados ou caminhos arbitrários.

## Prova nova pela API

Uma suíte nova e explícita verifica a calibração, os hashes da referência e o navegador antes de executar. Usa exatamente os sete cenários authored, frames 0/4/7/8/10/15 e probes anteriores; limite exclusivo de pixels 8 e de matriz 0,002. Não substitui nem modifica o diagnóstico histórico.

Plano tipado → apply/revisão 2 → inspeção da mesma revisão → job real → Remotion → FFmpeg → MP4/checksum → QC → pixels decodificados. Somente a entrega assíncrona do job é interceptada para executá-lo sincronamente no teste; render, finalização, armazenamento, QC e leitura de pixels são reais. Não houve API paga. [Sete testes novos](temporal-matte-native14-balanced-vector-guard-svg-subtract-quantized-full/tests.xml), com fontes completas arquivadas ao lado.

| Cenário | Máximo de erro de canal |
|---|---:|
| Controle / externo / alpha normal | 2,7500 |
| Filho / externo / alpha normal | 2,7500 |
| Filho / externo / alpha invertido | 3,0313 |
| Rig / externo / alpha normal | 3,9688 |
| Rig / externo / luminância invertida | 4,3750 |
| Filho / pai comum / alpha normal | 3,5000 |
| Rig / pai comum / luminância normal | 2,0000 |

Todos passaram, sem skips/errors: **1.164 probes, 42 matrizes, sete MP4s novos com QC passed**. Maior erro de matriz: 0,0002743. O ensaio histórico CRF 10 conserva seis passes e uma falha do oráculo antigo; a contraprova e a nova suíte não reescrevem esse resultado.

## Regressões e contratos

A seleção anterior de 188 casos foi executada integralmente contra o candidato: 179 passaram; nove falharam exclusivamente por expectativas intencionalmente substituídas — três da versão/CRF do finalizador, uma do antigo bloqueio da combinação e cinco de metadados high/CRF 14. Não houve outro erro, skip ou falha não planejada. [Vereditos originais dessa execução](temporal-matte-native14-quantized-candidate-regression/historical-tests.xml).

Os quatro novos contratos de versão/encode/admissão passaram. Os cinco casos de exposição foram repetidos mudando **uma única asserção de recibo, CRF 14→10**; inputs, cores, probes, tolerâncias e asserções de fase/hold permaneceram iguais, e todos passaram. [Quatro contratos](temporal-matte-native14-quantized-candidate-regression/proposed-contract-tests.xml), [cinco exposições](temporal-matte-native14-quantized-exposure-regression/tests.xml). As versões originais dos testes foram arquivadas antes das mudanças. Portanto há 188 casos atuais de regressão/contrato aprovados em execuções complementares; não se afirma que o XML histórico de 188 casos ficou verde.

Foram retidos **29 MP4s novos**: sete da combinação e 22 das capacidades anteriores. O job APNG negativo não publicou artefato, e o overflow da fonte final continuou sem publicação. Controle sem blur e shutter zero têm os mesmos 18.432.000 bytes RGB decodificados em 60 frames. Tipografia, hierarquias, comandos, mattes, sombra/blur e exposição conservaram suas verificações existentes. Mais [38 verificações da árvore React](temporal-matte-native14-balanced-runtime.json) comprovam pesos/tempo/redução, sem alegação de pixels por esse teste.

## Compatibilidade e limites

`CreativeDocumentV1`, `MotionGraphV1`, `MotionRecipeV1`, política de exposição v1, formato de planos, revisão e modelo de assets permanecem intactos. Não há migração SQL ou modelo de projeto novo. Mudanças de significado: admissão da combinação antes bloqueada; implementação da ponderação/inversão; qualidade high do finalizador. Leitores afetados: validação de exposição, projeção nativa, worker Remotion, provider contextual, recibos e consumidores dos testes de versão/qualidade. Provider/finalizador mudam explicitamente de versão; artefatos antigos continuam identificados por versão, digest, revisão e checksum. Os recibos experimentais native.14 anteriores conservam status e hashes próprios, sem promoção retroativa.

A referência matemática é de teste, não vira outro renderer. As evidências não atribuem aprovação humana ao QC. A inspeção API foi comprovada; a inspeção da combinação na UI real é a etapa seguinte. A revisão dos três estudos A/B/controle exige clareza, ritmo, continuidade e acabamento ≥4/5 e preferência cega; autonomia exige os três briefs novos depois dessa revisão.

Nas sete fixtures locais 320×320, 16 frames, 30 fps, o tempo do job ficou entre 8.156 e 10.469 ms, mediana 8.485 ms. Os recibos conservam bundle, seleção e render/encode separados. Não é p95 nem promessa de realtime/1080p/15 s. CRF 10 aumentou os arquivos dessas sete fixtures em 15,2% a 20,8% contra o mesmo candidato em CRF 14; o custo não é extrapolado a vídeos comerciais.

A revisão automática recusou a limpeza recursiva anterior dos repositórios de estudo e bundles DOM/PNG com `blocked by policy`. Os alvos continuam presentes; não houve nova tentativa ou contorno. Esta rodada não criou clones. Fonte primária adicional foi lida em memória e somente seus metadados foram retidos.
