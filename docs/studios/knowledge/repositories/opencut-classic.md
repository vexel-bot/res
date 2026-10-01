# Auditoria — opencut-classic

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `cf5e79e919144200294fb9fed22a222592a0aeea`  
**Origem:** https://github.com/opencut-app/opencut-classic.git  
**Licença detectada:** `OTHER` em `LICENSE`

## Capacidade

legacy OpenCut editor architecture reference.

- Manifests: package.json, Cargo.toml, docker-compose.yml
- Linguagens amostradas: TypeScript, TypeScript/React, Rust
- Resumo do README, não verificado: This is the original OpenCut codebase. It's archived and no longer maintained. The rewrite is happening at . Thanks to and for their support of open source software. Privacy : Your videos stay on your device Free features : Most basic CapCut features are now paywalled Simple : People want editors that are easy to use CapCut proved that apps/web/ : Next.js web application apps/desktop/ : Native desktop app built with GPUI (in progress) rust/ : Platform agnostic core: GPU compositor, effects, masks, and WASM bindings. We're actively migrating business logic here from TypeScript.
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": true, "test_directory": false, "pt_br_signal": false}`
- Hardware: GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight
- PT-BR: `unknown`
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Keep outside the production domain until license, model assets, hardware and quality pass focused review.

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
