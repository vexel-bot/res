# Auditoria — echomimic_v3

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `7e89489ca51c0d008fc1963ec6c03fc5bd0b9397`  
**Origem:** https://github.com/antgroup/echomimic_v3.git  
**Licença detectada:** `Apache-2.0` em `LICENSE.txt`

## Capacidade

audio-driven portrait animation candidate.

- Manifests: requirements.txt
- Linguagens amostradas: Python
- Resumo do README, não verificado: EchoMimicV3: 1.3B Parameters are All You Need for Unified Multi Modal and Multi Task Human Animation Ruobing Zheng &emsp; Terminal Technology Department, Alipay, Ant Group. 1 Core Contributor&emsp; 2 Corresponding Authors & x1F680; EchoMimic Series EchoMimicV1: Lifelike Audio Driven Portrait Animations through Editable Landmark Conditioning. EchoMimicV2: Towards Striking, Simplified, and Semi Body Human Animation. EchoMimicV3: 1.3B Parameters are All You Need for Unified Multi Modal and Multi Task Human Animation.
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
