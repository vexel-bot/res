# ADR-013 — Inteligência de vídeo ancorada na realidade

**Status:** aceito; PGV-0 implementado, nenhum modelo homologado  
**Data:** 2026-08-25

## Contexto

O Video Studio já preserva timebase, lineage e revisão do render exato, mas o QC atual mede propriedades técnicas. Ele não representa objetos persistentes, suporte, contato, oclusão, trajetórias, causalidade ou intenção editorial. Um VLM pode explicar um vídeo de modo convincente sem detectar que um objeto atravessou outro, mudou de identidade ou caiu contra a gravidade. Benchmarks recentes também mostram que modelos fortes continuam vulneráveis a atalhos, distribuição conhecida e perguntas sem localização temporal.

“Adicionar física” como um efeito de pós-produção não resolve o problema. A necessidade do produto é observar e raciocinar sobre a realidade para planejar, comparar e revisar vídeo, sem assumir que qualquer modelo isolado possui compreensão confiável.

## Decisão

A Clicko introduzirá uma camada provider-neutral de inteligência de realidade, acima da timeline e dos renderers, com três etapas separadas:

1. **observação:** câmera, orientação, entidades, máscaras/pontos, profundidade, visibilidade e trajetórias;
2. **hipótese:** relações de suporte, contato, contenção, oclusão, ligação, eventos e possíveis causas;
3. **avaliação:** previsão/contrafactual, violações localizadas, confiança, incerteza, abstenção e sugestão humana.

O ativo canônico será `RealityModelV1`, ligado ao asset, checksum, frame rate racional e time-map. A intenção de cada shot será registrada em `ShotRealityConstraintV1`, incluindo `realistic`, `stylized_physical` ou `surreal` e técnicas declaradas como cut, slow motion, speed ramp, reverse, timelapse, stop motion e VFX. O resultado será `PhysicalPlausibilityEvaluationV1`, ligado à revisão e ao render exatos, com intervalos, entidades, evidências, policy/model digests e decisão humana.

Serão criados ports substituíveis para geometria visual, tracking, compreensão de cena física, world model em vídeo, plausibilidade e calibração. O runtime será um ensemble: sinais geométricos e object-centric, previsão latente, regras calibradas e modelo semântico apenas para rótulos/explicações. Nenhum modelo poderá aprovar ou corrigir um vídeo sozinho.

`reality_analysis` será cacheado por checksum em worker `vision_gpu`; `video_physical_qc` rodará depois de geração/render. A VPS existente permanece control plane e não receberá processamento pesado ou mudanças de serviço.

## Política de decisão

- a primeira versão é advisory: nunca altera automaticamente frames, trajetória ou edição;
- toda ocorrência precisa indicar intervalo, entidades, confiança, incerteza e evidência reproduzível;
- baixa confiança deve resultar em abstenção, não em acusação;
- a política diferencia erro físico de linguagem cinematográfica intencional;
- vídeo sintético realista poderá bloquear autoaprovação somente após benchmark privado, calibração e revisão de produto/segurança; revisão humana e override auditável continuam obrigatórios;
- qualquer checkpoint, dataset ou código não comercial fica restrito a evidência/pesquisa, fora da produção e de dados privados.

## OpenCut

OpenCut não define o domínio nem o modelo de realidade. O rewrite atual continua imaturo como engine integrada e o Classic está arquivado. Serão usados seletivamente padrões MIT do Classic — markers/bookmarks, snapping, comandos/undo, keyframes/masks, overlays/hit testing e waveform — para um primeiro spike de **Reality Lane** sobre a timeline Clicko. Auth, banco, stores, documento de projeto e aplicação inteira não entram.

## Benchmark obrigatório

O protocolo deve congelar policy, corpus, candidatos e thresholds antes dos resultados. Ele combina:

- compreensão em pares mínimos e contrafactuais;
- detecção/localização de falhas em vídeo real e gerado;
- corpus Clicko privado com cenas físicas simples, UGC, câmera em movimento e técnicas editoriais declaradas;
- métricas de paired accuracy, macro-F1, precision/recall crítico, temporal IoU, grounding, ECE/Brier, abstenção, false block, correction effort, latência, VRAM e custo.

As metas preliminares do produto são hipóteses pré-run: recall crítico ≥ 0,90, precisão ≥ 0,80, false block em UGC real ≤ 1%, temporal IoU ≥ 0,70, ECE ≤ 0,10 e paired accuracy ≥ 0,75. Mesmo que sejam atingidas, PGV-4 permanece advisory até uma decisão posterior.

## Consequências

Positivas: o conhecimento durável fica nos contratos e evidências; modelos podem ser trocados; issues chegam à timeline com localização; intenção criativa reduz falsos positivos; custo pode ser medido por camada.

Custos/riscos: tracking e geometria acumulam erro; benchmarks públicos podem induzir atalhos; avaliação por VLM pode reproduzir o erro avaliado; modelos permissivos ainda exigem auditoria de checkpoints; a Reality Lane pode virar um segundo editor se não consumir o `CreativeDocument` canônico.

## Evidência de PGV-0

- contratos provider-neutral implementados em `backend/app/domain/studios/reality.py`, incluindo contribution envelope e digests canônicos;
- ports adicionados para geometria, tracking, síntese de cena física, world model, plausibilidade e calibração;
- jobs `reality_analysis` e `video_physical_qc` reservados à capability/queue `vision_gpu` externa;
- runtime policy advisory e três benchmark policies congeladas em `benchmarks/studios/reality/`;
- fixtures sintéticas cobrem modelo, constraints, avaliação limpa e abstenção, sem mídia/pesos/dados pessoais;
- testes provam graph/reference integrity, ranges, checksum/timebase, creative intent, digest/status binding, abstenção e exigência de sinais independentes;
- verificação inicial PGV-0: 12 testes focados e 41 combinados; após o preflight PGV-1 da ADR-014, backend completo com 137 passes e 1 skip esperado;
- clones rasos de V-JEPA 2, TAPNet/TAPIR, RAFT, Depth Anything V2 e OpenCV foram pinados sem baixar pesos. O checkout V-JEPA 2 apresenta colisão de caixa no Windows e deverá ser reproduzido em Linux.

PGV-0 não ativa endpoints, providers, modelos, autocorreção ou autopublicação. A VPS não foi acessada nem alterada.

## Próximo gate

Executar PGV-1 após revisão das policies: pin/digest/licença de todos os pesos; license manifests; imagem `vision_gpu` com SBOM; adapters fakes; storage privado; e baseline com FFmpeg/OpenCV/RAFT, Depth Anything V2 Small, TAPIR e estimador próprio de orientação/gravity cues. V-JEPA 2 só entra em PGV-3 após auditoria integral da cadeia; IntPhys2, MVPBench, CausalVQA e modelos/dados NC permanecem evidence-only.

Relatório de base: `docs/studios/research/PHYSICS_GROUNDED_VIDEO_INTELLIGENCE.md`.
