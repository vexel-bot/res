# Auditoria — lexical

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `3984d88bf28960dfcb6fa36977b923396ad9ae70`  
**Origem:** https://github.com/facebook/lexical.git  
**Licença detectada:** `MIT` em `LICENSE`

## Capacidade

structured rich-text editing candidate.

- Manifests: package.json
- Linguagens amostradas: TypeScript, TypeScript/React, JavaScript, Python
- Resumo do README, não verificado: An extensible text editor framework that provides excellent reliability, accessibility and performance. Documentation Getting Started Playground Gallery Framework Agnostic Core Works with any UI framework, with official Reliable & Accessible Built in accessibility support and WCAG compliance Extensible Plugin based architecture with powerful extension points Immutable State Model Time travel ready with built in undo/redo Collaborative Editing Real time collaboration via integration Serialization Import/export from JSON, Markdown, and HTML
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
