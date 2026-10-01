# Auditoria — opentimelineio

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adopt`  
**Commit:** `bc5fe2d78dc3f8b2a8feb7e04483d85a12e80072`  
**Origem:** https://github.com/AcademySoftwareFoundation/OpenTimelineIO.git  
**Licença detectada:** `Apache-2.0` em `LICENSE.txt`

## Capacidade

provider-neutral editorial interchange.

- Manifests: pyproject.toml, setup.py
- Linguagens amostradas: Python, C++
- Resumo do README, não verificado: Main web site: http://opentimeline.io/ Documentation: https://opentimelineio.readthedocs.io/ Wiki (more documentation): https://github.com/AcademySoftwareFoundation/OpenTimelineIO/wiki GitHub: https://github.com/AcademySoftwareFoundation/OpenTimelineIO To join, create an account here first: https://slack.aswf.io/ OpenTimelineIO is a mature framework widely deployed across the film and television industries. It is natively supported in most non linear editing applications, and has deep integration in game engines, digital content creation
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": false, "test_directory": true, "pt_br_signal": false}`
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
