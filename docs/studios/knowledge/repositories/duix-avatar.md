# Auditoria — duix-avatar

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `1328feb5871448c8fa3d0e45b3bbc87e7c1d458a`  
**Origem:** https://github.com/duixcom/Duix-Avatar.git  
**Licença detectada:** `OTHER` em `LICENSE`

## Capacidade

authorized avatar generation candidate.

- Manifests: package.json
- Linguagens amostradas: JavaScript
- Resumo do README, não verificado: 🚀🚀🚀 Duix Avatar — Truly open source AI avatar toolkit for offline video generation and digital human cloning 1. What's Duix.Avatar Duix.Avatar is a free and open source AI avatar project developed by Duix.com . Seven years ago, a group of young pioneers chose an unconventional technical path, developing a method to train digital human models using real person video data. Unlike traditional costly 3D digital human approaches, we leveraged AI generated technology to create ultra realistic digital humans, slashing production costs from hundreds of thousands of dollars to just $1,000. This innovat
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
