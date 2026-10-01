# Auditoria — vjepa2

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `204698b45b3712590f06245fbfba32d3be539812`  
**Origem:** https://github.com/facebookresearch/vjepa2.git  
**Licença detectada:** `MIT` em `LICENSE`

## Capacidade

temporal representation research candidate.

- Manifests: pyproject.toml, requirements.txt, setup.py
- Linguagens amostradas: Python
- Resumo do README, não verificado: 🆕 [2026 03 16]: :fire: V JEPA 2.1 is released :fire: A new familly of models trained with a novel recipe that learns high quality and temporolly consistent dense features !!! [2025 06 25]: V JEPA 2 is released. ] V JEPA 2: Self Supervised Video Models Enable Understanding, Prediction and Planning Mahmoud Assran∗, Adrien Bardes∗, David Fan∗, Quentin Garrido∗, Russell Howes∗, Mojtaba Komeili∗, Matthew Muckley∗, Ammar Rizvi∗, Claire Roberts∗, Koustuv Sinha∗, Artem Zholus , Sergio Arnaud , Abha Gejji , Ada Martin , Francois Robert Hogan , Daniel Dugas , Piotr
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
