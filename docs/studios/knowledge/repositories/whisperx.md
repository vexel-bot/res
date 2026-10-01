# Auditoria — whisperx

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `2cfd7b7c5c7bba144954364db747319b50e8232b`  
**Origem:** https://github.com/m-bain/whisperX.git  
**Licença detectada:** `BSD-3-Clause` em `LICENSE`

## Capacidade

speech transcription and word alignment candidate.

- Manifests: pyproject.toml
- Linguagens amostradas: Python
- Resumo do README, não verificado: Recall.ai Meeting Transcription API If you’re looking for a transcription API for meetings, consider checking out , an API that works with Zoom, Google Meet, Microsoft Teams, and more. Recall.ai diarizes by pulling the speaker data and separate audio streams from the meeting platforms, which means 100% accurate speaker diarization with actual speaker names. <img src="https://img.shields.io/github/stars/m bain/whisperX.svg?colorA=orange&colorB=orange&logo=github" <img src="https://img.shields.io/github/issues/m bain/whisperx.svg"
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": true, "pt_br_signal": false}`
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
