# Auditoria — ditto-talkinghead

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `c3e47eee2e626500017a0556b470d6d4182f85e8`  
**Origem:** https://github.com/antgroup/ditto-talkinghead.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

authorized talking-head animation candidate.

- Manifests: nenhum detectado
- Linguagens amostradas: Python, C
- Resumo do README, não verificado: Ditto: Motion Space Diffusion for Controllable Realtime Talking Head Synthesis ✨ For more results, visit our Project Page ✨ [2025.11.12] 🔥🔥 We noticed the community's enthusiasm for open source training code. is now available, since there have been multiple versions and limited time to organize, it may differ slightly from the paper version. [2025.07.11] 🔥 The is now available. [2025.07.07] 🔥 Ditto is accepted by ACM MM 2025. [2025.01.21] 🔥 We update the demo, welcome to try it. [2025.01.10] 🔥 We release our inference and .
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware: GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight
- PT-BR: `unknown`
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Keep outside the production domain until license, model assets, hardware and quality pass focused review.

Tipos do repositório não podem atravessar worker/adapter para domínio, banco ou API. Somente contratos Clicko versionados são persistidos.

## Riscos

- machine inventory does not validate model-weight or dataset licensing
- biometric/identity use requires explicit consent, private benchmark and deletion controls

## Benchmark mínimo

license + dependency preflight, fixed fixture, resource envelope, output quality, repeatability, failure observability and PT-BR where relevant.

## Revisão necessária

- [ ] confirmar licença de código, pesos, datasets e exemplos;
- [ ] medir inputs, outputs, hardware, tempo e memória;
- [ ] executar fixture reproduzível sem mídia pessoal;
- [ ] avaliar segurança e cadeia de suprimentos;
- [ ] revisar suporte PT-BR;
- [ ] aprovar ou substituir a decisão provisória.
