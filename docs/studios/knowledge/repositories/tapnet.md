# Auditoria — tapnet

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `c2cbab81cc06092b5f05bfe2da7bfec54e2079c9`  
**Origem:** https://github.com/google-deepmind/tapnet.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

point tracking candidate.

- Manifests: pyproject.toml, requirements.txt
- Linguagens amostradas: Python
- Resumo do README, não verificado: Tracking Any Point (TAP) https://github.com/google deepmind/tapnet/assets/4534987/9f66b81a 7efb 48e7 a59c f5781c35bebc Welcome to the official Google Deepmind repository for Tracking Any Point (TAP), home of the TAP Vid and TAPVid 3D Datasets, our top performing TAPIR model, and our RoboTAP extension. is a benchmark for models that perform this task, with a collection of ground truth points for both real and synthetic videos. is a two stage algorithm which employs two stages: 1) a matching stage, which independently locates a suitable candidate point match for the query point on every other fr
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
