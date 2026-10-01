# Auditoria — remotion

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adopt`  
**Commit:** `e624eb770082630dd596fa6783ee1be96db64bba`  
**Origem:** https://github.com/remotion-dev/remotion.git  
**Licença detectada:** `OTHER` em `LICENSE.md`

## Capacidade

React-based deterministic video composition and rendering.

- Manifests: package.json
- Linguagens amostradas: TypeScript, TypeScript/React, JavaScript, Rust
- Resumo do README, não verificado: Video tools for the agent era. Make videos agentically : Turn your idea into a video using your coding agent. Make videos interactively : Edit and animate using drag and drop. Make videos programmatically : Connect to data, and manage complexity with code. React Code is the source of truth. Switch your workflow at any point. Design systems : Create a library of animated assets for your organization. Batch rendering : Render millions of videos on your own infrastructure. Applications : Publish a simple tool or a complex video editor.
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware: no GPU requirement established by static inventory; reproducible preflight still required
- PT-BR: `unknown`
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Use behind a provider-neutral adapter with pinned version, deterministic fixtures and artifact lineage.

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
