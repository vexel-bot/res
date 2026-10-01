# Auditoria — motion-canvas

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `7b91435c301d530351dcf5ebb91dd139c002e405`  
**Origem:** https://github.com/motion-canvas/motion-canvas.git  
**Licença detectada:** `MIT` em `LICENSE`

## Capacidade

programmatic TypeScript motion design candidate.

- Manifests: package.json
- Linguagens amostradas: TypeScript, TypeScript/React, JavaScript
- Resumo do README, não verificado: Motion Canvas is two things: A TypeScript library that uses generators to program animations. An editor providing a real time preview of said animations. It's a specialized tool designed to create informative vector animations and synchronize them with voice overs. Aside from providing the preview, the editor allows you to edit certain aspects of the animation which could otherwise be tedious. Check out our [getting started][docs] guide to learn how to use Motion Canvas. Developing Motion Canvas locally
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
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
