# Auditoria — qwen3-vl

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `96588727e44c78b25ba03ea03b8e12f7e64fd0da`  
**Origem:** https://github.com/QwenLM/Qwen3-VL.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

semantic visual description candidate.

- Manifests: nenhum detectado
- Linguagens amostradas: Python
- Resumo do README, não verificado: 💜 Qwen Chat &nbsp&nbsp &nbsp&nbsp🤗 Hugging Face &nbsp&nbsp &nbsp&nbsp🤖 ModelScope &nbsp&nbsp &nbsp&nbsp📑 Blog &nbsp&nbsp &nbsp&nbsp📚 Cookbooks &nbsp&nbsp &nbsp&nbsp📑 Paper &nbsp&nbsp 🖥️ Demo &nbsp&nbsp &nbsp&nbsp💬 WeChat (微信) &nbsp&nbsp &nbsp&nbsp🫨 Discord &nbsp&nbsp &nbsp&nbsp📑 API &nbsp&nbsp &nbsp&nbsp🖥️ PAI DSW Meet Qwen3 VL — the most powerful vision language model in the Qwen series to date. This generation delivers comprehensive upgrades across the board: superior text understanding & generation, deeper visual perception & reasoning, extended context length, enhanced spatial and video dy
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
