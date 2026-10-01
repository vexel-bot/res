# Auditoria — misaki

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `fba1236595f2d2bf21d414ba6e57d25256afada3`  
**Origem:** https://github.com/hexgrad/misaki.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

grapheme-to-phoneme and language preprocessing candidate.

- Manifests: pyproject.toml
- Linguagens amostradas: Python
- Resumo do README, não verificado: Misaki is a G2P engine designed for models. Hosted demo: https://hf.co/spaces/hexgrad/Misaki G2P You can run this in one cell on : !pip install q "misaki[en]" from misaki import en g2p = en.G2P(trf=False, british=False, fallback=None) no transformer, American English text = ' is a G2P engine designed for models.' phonemes, tokens = g2p(text) print(phonemes) misˈɑki ɪz ə ʤˈitəpˈi ˈɛnʤən dəzˈInd fɔɹ kˈOkəɹO mˈɑdᵊlz. To fallback to espeak: Installing espeak varies across platforms, this silent install works on Colab:
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
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
