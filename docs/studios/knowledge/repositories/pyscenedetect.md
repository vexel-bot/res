# Auditoria — pyscenedetect

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adopt`  
**Commit:** `4fc4cdbe969f347f77eea996a18cae85eaa3ce58`  
**Origem:** https://github.com/Breakthrough/PySceneDetect.git  
**Licença detectada:** `BSD-3-Clause` em `LICENSE`

## Capacidade

shot-boundary candidate detection.

- Manifests: pyproject.toml, Dockerfile
- Linguagens amostradas: Python, JavaScript
- Resumo do README, não verificado: Video Cut Detection and Analysis Tool Latest Release: v0.7.1 (July 21, 2026) Quickstart Example : Discord : https://discord.gg/H83HbJngk7 pip install scenedetect upgrade Requires ffmpeg/mkvmerge for video splitting support. Windows builds (MSI installer/portable ZIP) can be found on . A Docker image with all dependencies included is available as . Quick Start (Command Line) : Split input video on each fast cut using ffmpeg : scenedetect i video.mp4 split video Save some frames from each cut: scenedetect i video.mp4 save images
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": true, "test_directory": true, "pt_br_signal": false}`
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
