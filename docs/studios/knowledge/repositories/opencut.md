# Auditoria — opencut

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `400f097becba5db0fbc305d5a65348cb81c20356`  
**Origem:** https://github.com/opencut-app/opencut.git  
**Licença detectada:** `OTHER` em `LICENSE`

## Capacidade

open-source video-editor product and architecture reference.

- Manifests: Cargo.toml
- Linguagens amostradas: TypeScript/React, Rust, TypeScript
- Resumo do README, não verificado: A free and open source video editor for web, desktop, and mobile. OpenCut is being rewritten from the ground up. What's coming: First class third party plugins (made possible by a plugin first architecture) Desktop, mobile, and browser from one codebase (Rust core) MCP server (for AI agents) Headless mode (automation, batch rendering) A scripting tab directly in the editor You can still find the previous version at , which is the one to reach for today. still runs the classic version. The rewrite will live at until it's ready to take over.
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware: no GPU requirement established by static inventory; reproducible preflight still required
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
