# Auditoria — sam2

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `2b90b9f5ceec907a1c18123530e92e794ad901a4`  
**Origem:** https://github.com/facebookresearch/sam2.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

segmentation and mask continuity candidate.

- Manifests: pyproject.toml, setup.py
- Linguagens amostradas: TypeScript, TypeScript/React, Python, JavaScript
- Resumo do README, não verificado: SAM 2: Segment Anything in Images and Videos , , , , , , , , , , , , , , , , , Segment Anything Model 2 (SAM 2) is a foundation model towards solving promptable visual segmentation in images and videos. We extend SAM to video by considering images as a video with a single frame. The model design is a simple transformer architecture with streaming memory for real time video processing. We build a model in the loop data engine, which improves model and data via user interaction, to collect , the largest video segmentation dataset to date. SAM 2 trained on our data provides strong performance acr
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware: GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight
- PT-BR: `unknown`
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Evaluate behind an isolated worker/adapter; persist only canonical Clicko contracts.

Tipos do repositório não podem atravessar worker/adapter para domínio, banco ou API. Somente contratos Clicko versionados são persistidos.

## Riscos

- machine inventory does not validate model-weight or dataset licensing

## Benchmark mínimo

license + dependency preflight, fixed fixture, resource envelope, output quality, repeatability, failure observability and PT-BR where relevant.

## Revisão necessária

- [ ] confirmar licença de código, pesos, datasets e exemplos;
- [ ] medir inputs, outputs, hardware, tempo e memória;
- [ ] executar fixture reproduzível sem mídia pessoal;
- [ ] avaliar segurança e cadeia de suprimentos;
- [ ] revisar suporte PT-BR;
- [ ] aprovar ou substituir a decisão provisória.
