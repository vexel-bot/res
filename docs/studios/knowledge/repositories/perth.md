# Auditoria — perth

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `ce86c49d029f42272c1902eccb675556b9ed2330`  
**Origem:** https://github.com/resemble-ai/Perth.git  
**Licença detectada:** `MIT` em `LICENSE`

## Capacidade

candidate capability whose exact role must be established from code and benchmark.

- Manifests: pyproject.toml
- Linguagens amostradas: Python
- Resumo do README, não verificado: Perth is a comprehensive Python library for audio watermarking and detection. Perth enables you to embed imperceptible watermarks in audio files and later detect them, even after the audio has undergone various transformations or manipulations. The library implements multiple watermarking techniques including neural network based approaches. Multiple Watermarking Techniques : Including the Perth Net Implicit neural network approach Robust Watermarks : Watermarks can survive common audio transformations like compression, resampling, and more
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": true, "pt_br_signal": false}`
- Hardware: GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight
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
