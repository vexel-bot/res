# Auditoria — konva

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `aa3432ebf1c48606764fef0918e68bfc4aec3684`  
**Origem:** https://github.com/konvajs/konva.git  
**Licença detectada:** `MIT` em `LICENSE`

## Capacidade

interactive canvas scene graph for the editor.

- Manifests: package.json
- Linguagens amostradas: TypeScript, JavaScript
- Resumo do README, não verificado: Build interactive graphics, editors, and diagrams for the web. Konva is an open source 2D canvas framework for interactive graphics. Its scene graph gives each shape its own events, drag behavior, transforms, animation, cache, and export controls. Use Konva for design editors, whiteboards, diagrams, annotations, maps, and other visual tools. Konva is MIT licensed and does not require a license key. This repository began as a GitHub fork of . Visit: The and follow on Used by: (design editor SDK) and many others — see the full showcase on the
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": false, "test_directory": true, "pt_br_signal": false}`
- Hardware: no GPU requirement established by static inventory; reproducible preflight still required
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
