# ADR-016 — Baseline clássica OpenCV para evidência de realidade

**Status:** aceito para avaliação; registro e promoção bloqueados  
**Data:** 2026-08-25

## Contexto

RAFT e o runtime CUDA continuam em revisão. Esperar esses itens para produzir qualquer sinal real deixaria o PGV-1 sem referência mensurável e aumentaria o risco de atribuir ao futuro world model ganhos que uma baseline clássica já entregaria.

Uma baseline útil não pode fingir “compreensão da física”. Ela precisa observar sinais reproduzíveis da imagem, localizar evidência, declarar limitações e se abster de suporte, contato, colisão, causalidade, material e biomecânica.

## Decisão

Implementar três providers substituíveis, sem registro global:

- `opensource.opencv-geometry`: Hough/cluster dominante para horizonte, Lucas-Kanade + affine RANSAC para movimento de câmera, direção vertical apenas quando existe horizonte suportado;
- `opensource.opencv-point-tracking`: tracks esparsos Lucas-Kanade representados explicitamente como features não semânticas;
- `builtin.canonical-reality-scene`: merge determinístico de contributions/evidências, sem criar conclusões; retorna `partial` apenas quando há câmera ou motion suportado e `incomplete` caso contrário.

Lineage contém SHA-256 do módulo, checksum do vídeo, parâmetros canônicos, versão OpenCV e timestamps. O resultado continua ligado ao asset/time-map/policy exatos pelo `RealityAnalysisOrchestrator`.

O bundle candidato fica em `workers/vision-gpu/providers/opencv-baseline.provider.json`, status `evaluation`, `advertisedByWorkerManifest=false`. O manifest principal continua `providers: []`. O Dockerfile preflight não instala OpenCV ou NumPy.

## Evidência

- corpus congelado `benchmarks/studios/reality/opencv-baseline-corpus.v1.json`, digest `c4ed7f2ff783be28e541353c47f73dd076749bb702a7bbeb72bc84b1a0f8a0ed`, com 11 casos/11 cenários: static, pan, tilt, roll, zoom, no-horizon, low-texture, cut, blur, foreground e distractors;
- runner recomputável `backend/scripts/run_opencv_reality_benchmark.py`: gera MP4s sintéticos em diretório efêmero, executa geometry + tracking + cena canônica e grava o bundle de relatório/gate sem tocar no registry;
- o runner compara as versões instaladas de NumPy e da distribuição `opencv-python-headless` com o lock do candidato e encerra antes da análise quando há divergência;
- execução real bloqueada pela primeira vez de forma honesta: o primeiro corpus procedural marcou `pan-no-horizon`, `tilt`, `roll` e `zoom` como falhos; a investigação corrigiu somente a fixture (recorte vertical, estímulo sem horizonte e variação por frame), sem relaxar thresholds;
- execução final no venv externo com Python 3.11.9, OpenCV 4.13.0, NumPy 2.2.6 e lock `ff9128c9...011e76`: 11/11 casos e 6/6 métricas em 1,0; evidência resumida em `benchmarks/studios/reality/opencv-baseline-run-2026-08-25.v1.json` e relatório integral referenciado pelo `external_report_ref`;
- integração real OpenCV 4.13.0 detectou `pan`, horizonte próximo de 0,5, up/gravity image-plane e tracks com deslocamento;
- o primeiro baseline unitário revelou que a média de linhas confundia horizonte com bordas do objeto; a implementação passou a selecionar o cluster horizontal dominante e o teste passou;
- o modelo resultante preservou evidência/lineage e continuou abstendo `support_gravity` e demais princípios não demonstrados;
- cancelamento antes da observação foi comprovado;
- wheel Linux OpenCV `0525a3d2...a5bd22`, NumPy `ba10f841...e6dbbdf` e lock `ff9128c9...011e76` foram congelados fora do produto;
- candidate manifest canônico: `4be8fc9c8f66d56279543324c1c5bb74a0a42e62ba33b7ed21b96bd5a0417fcd`;
- backend completo: 175 coletados, `172 passed, 3 skipped`; as duas integrações OpenCV skipped no ambiente padrão passaram no venv pinado 4.13.0/NumPy 2.2.6; contratos do corpus/gate/promoção/Reality Lane, do CLI de promoção e dos manifests preflight de fala também passam; Ruff limpo;
- nenhuma mídia de usuário, peso, GPU ou VPS foi usada.

## OpenCut e Reality Lane

OpenCut não entra no runtime de inferência. A primeira projeção provider-neutral da Reality Lane agora está em `backend/app/domain/studios/reality.py` (`RealityLaneProjectionV1` + `project_reality_lane`); ela ainda é uma superfície de revisão, não um segundo documento/store. Ela projeta os resultados Clicko em:

- marker por shot com label/confiança de câmera;
- overlay de horizonte e direção vertical corrigível;
- trajetórias esparsas com toggle de evidência;
- inspector que mostra provider, versão, frame range, limitações e abstention;
- commands/undo para correção humana que geram nova contribution, sem editar o output original do provider.

Markers, snapping, overlays e hit-testing podem se inspirar seletivamente no OpenCut Classic MIT. Store, auth, documento, banco e compositor OpenCut continuam fora.

## Consequências

A Clicko ganha um piso real, barato e sem pesos para medir TAPIR/RAFT/V-JEPA. A baseline não reconhece objetos nem valida física. Um track visual não pode virar pessoa/produto, e um vetor vertical não prova gravidade ou suporte.

## Próximo gate

1. revisar os notices binários dos wheels e refletir obrigações no SBOM/NOTICE;
2. repetir o mesmo corpus em Linux/AMD64 na imagem pinada, com provenance, assinatura e cleanup verificável;
3. adicionar oclusão, deformação e casos reais consentidos somente no benchmark privado aprovado;
4. implementar TAPIR/Depth Anything V2 Small/RAFT condicionado atrás dos mesmos contratos e comparar contra esta baseline;
5. promover somente com inventário aprovado, benchmark recomputável, referência jurídica e atualização atômica do worker manifest. O resultado técnico atual permanece `activation_decision=incomplete` porque o candidato ainda está `evaluation`.
