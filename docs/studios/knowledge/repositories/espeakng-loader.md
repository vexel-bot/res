# Auditoria — espeakng-loader

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `0ddc87adf77e5850d7eeb542ac8a87d421b64daa`  
**Origem:** https://github.com/thewh1teagle/espeakng-loader.git  
**Licença detectada:** `MIT` em `LICENSE`

## Capacidade

runtime packaging and loading support for eSpeak NG.

- Manifests: pyproject.toml
- Linguagens amostradas: Python
- Resumo do README, não verificado: This package loads the espeak ng shared library so it will be available for other libraries. Linux (x86 64, arm64) Windows (x86 64, arm64) pip install espeakng loader from espeakng loader import get library path, load library, make library available library path = get library path() Pass it to the library Or use load library() for load it directly Or use make library available() for making it available for other libraries Note: please use phonemizer fork instead of phonemizer package until merged. from phonemizer.backend.espeak.wrapper import EspeakWrapper
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware: no GPU requirement established by static inventory; reproducible preflight still required
- PT-BR: `unknown`
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Keep outside the production domain until license, model assets, hardware and quality pass focused review.

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
