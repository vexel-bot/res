# Auditoria — kokoro

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `dfb907a02bba8152ca444717ca5d78747ccb4bec`  
**Origem:** https://github.com/hexgrad/kokoro.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

speech synthesis candidate.

- Manifests: pyproject.toml
- Linguagens amostradas: Python, JavaScript
- Resumo do README, não verificado: An inference library for . You can . Kokoro is an open weight TTS model with 82 million parameters. Despite its lightweight architecture, it delivers comparable quality to larger models while being significantly faster and more cost efficient. With Apache licensed weights, Kokoro can be deployed anywhere from production environments to personal projects. You can run this basic cell on . . !pip install q kokoro =0.9.4 soundfile !apt get qq y install espeak ng /dev/null 2 &1 from kokoro import KPipeline
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": true, "pt_br_signal": true}`
- Hardware: GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight
- PT-BR: `partial_signal`
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
