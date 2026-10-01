# Auditoria — supervision

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `5f25aa0ee6dc22891415b6e3d2e1689ce7a32952`  
**Origem:** https://github.com/roboflow/supervision.git  
**Licença detectada:** `MIT` em `LICENSE.md`

## Capacidade

provider-isolated organization of detections, tracks, zones and annotations.

- Manifests: pyproject.toml
- Linguagens amostradas: Python, JavaScript
- Resumo do README, não verificado: src="https://media.roboflow.com/open source/supervision/rf supervision banner.png?updatedAt=1678995927529" We are your essential toolkit for computer vision. From data loading to real time zone counting, we provide the building blocks so you can focus on building applications around your models. 🤝 Pip install the supervision package in a environment. pip install supervision Read more about conda, mamba, and installing from source in our . Supervision was designed to be model agnostic. Just plug in any classification, detection, or segmentation model. For your convenience, we have created for t
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
