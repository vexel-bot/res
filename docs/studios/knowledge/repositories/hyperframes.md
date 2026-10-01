# Auditoria — hyperframes

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `2ca578f9455ca928ab168e7dd08a1a3a9d834788`  
**Origem:** https://github.com/heygen-com/hyperframes.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

programmatic motion/video composition candidate.

- Manifests: package.json
- Linguagens amostradas: JavaScript, TypeScript
- Resumo do README, não verificado: Write HTML. Render video. Built for agents. HyperFrames is an open source framework for turning HTML, CSS, media, and seekable animations into deterministic MP4 videos. Use it locally with the CLI, from AI coding agents with skills, or as the rendering core behind hosted authoring workflows. With an AI coding agent Install the HyperFrames skills, then describe the video you want: npx skills add heygen com/hyperframes The picker opens with nothing pre selected — the Core Skills group is all you need: the /hyperframes router installs each creation workflow on demand. Agents and non interactive r
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware: GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight
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
