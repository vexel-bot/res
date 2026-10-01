# Auditoria — openmontage

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `cd9f3c1f03368be87b140af494914b8ee4e3c7a4`  
**Origem:** https://github.com/calesthio/OpenMontage.git  
**Licença detectada:** `AGPL-3.0` em `LICENSE`

## Capacidade

reference architecture for manifests, checkpoints, human gates and post-render inspection.

- Manifests: requirements.txt, setup.py
- Linguagens amostradas: Python, TypeScript/React, TypeScript, JavaScript
- Resumo do README, não verificado: Monty the Clapper — the official mascot of OpenMontage The first open source, agentic video production system. Paste A Video &nbsp;·&nbsp; Quick Start &nbsp;·&nbsp; Try These Prompts &nbsp;·&nbsp; Pipelines &nbsp;·&nbsp; How It Works &nbsp;·&nbsp; Sponsors &nbsp;·&nbsp; Providers &nbsp;·&nbsp; Review Guide &nbsp;·&nbsp; Want to support OpenMontage? . Bloome lets multiple AI agents (Claude, ChatGPT, DeepSeek, and more) collaborate in one conversation for agentic video pipelines. It has zero setup, runs in the cloud, works on web and mobile, and lets you share a configured agent with your whole 
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": true, "pt_br_signal": false}`
- Hardware: GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight
- PT-BR: `unknown`
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Reimplement manifest, checkpoint, decision-log and validation patterns independently; do not copy AGPL backend code without legal review.

Tipos do repositório não podem atravessar worker/adapter para domínio, banco ou API. Somente contratos Clicko versionados são persistidos.

## Riscos

- machine inventory does not validate model-weight or dataset licensing
- strong copyleft requires explicit legal/architecture review

## Benchmark mínimo

license + dependency preflight, fixed fixture, resource envelope, output quality, repeatability, failure observability and PT-BR where relevant.

## Revisão necessária

- [ ] confirmar licença de código, pesos, datasets e exemplos;
- [ ] medir inputs, outputs, hardware, tempo e memória;
- [ ] executar fixture reproduzível sem mídia pessoal;
- [ ] avaliar segurança e cadeia de suprimentos;
- [ ] revisar suporte PT-BR;
- [ ] aprovar ou substituir a decisão provisória.
