# Auditoria — opencv

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adopt`  
**Commit:** `8b7dc43c227746366213a65ad1477ed37fb8d365`  
**Origem:** https://github.com/opencv/opencv.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

classical vision, geometry, color and measurement.

- Manifests: nenhum detectado
- Linguagens amostradas: C++, C, Python, JavaScript
- Resumo do README, não verificado: OpenCV: Open Source Computer Vision Library previous forum (read only): Additional OpenCV functionality: Please read the before starting work on a pull request. Summary of the guidelines: One pull request per issue; Choose the right base branch; Include tests and documentation; Clean up "oops" commits before submitting; Additional Resources for inclusion in Community Friday on opencv.org featuring OpenCV Live, an hour long streaming show for daily posts showing the state of the art in computer vision & AI to help organize events and online campaigns as well as amplify them
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
