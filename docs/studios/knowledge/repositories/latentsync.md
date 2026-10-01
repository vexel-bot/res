# Auditoria — latentsync

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `a229c3948406bc2cf6eaf4873e662e70c6a04746`  
**Origem:** https://github.com/bytedance/LatentSync.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

lip synchronization candidate.

- Manifests: requirements.txt
- Linguagens amostradas: Python
- Resumo do README, não verificado: 2025/06/11 : We released LatentSync 1.6 , which is trained on 512 $\times$ 512 resolution videos to mitigate the blurriness problem. Watch the demo . 2025/03/14 : We released LatentSync 1.5 , which (1) improves temporal consistency via adding temporal layer, (2) improves performance on Chinese videos and (3) reduces the VRAM requirement of the stage2 training to 20 GB through a series of optimizations. Learn more details . We present LatentSync , an end to end lip sync method based on audio conditioned latent diffusion models without any intermediate motion representation, diverging from previ
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
