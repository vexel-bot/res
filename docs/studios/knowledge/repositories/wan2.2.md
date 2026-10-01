# Auditoria — wan2.2

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `42bf4cfaa384bc21833865abc2f9e6c0e67233dc`  
**Origem:** https://github.com/Wan-Video/Wan2.2.git  
**Licença detectada:** `Apache-2.0` em `LICENSE.txt`

## Capacidade

generative video research candidate.

- Manifests: pyproject.toml, requirements.txt
- Linguagens amostradas: Python
- Resumo do README, não verificado: 💜 Wan &nbsp&nbsp ｜ &nbsp&nbsp 🖥️ GitHub &nbsp&nbsp &nbsp&nbsp🤗 Hugging Face &nbsp&nbsp &nbsp&nbsp🤖 ModelScope &nbsp&nbsp &nbsp&nbsp 📑 Paper &nbsp&nbsp &nbsp&nbsp 📑 Blog &nbsp&nbsp &nbsp&nbsp 💬 Discord &nbsp&nbsp 📕 使用指南(中文) &nbsp&nbsp &nbsp&nbsp 📘 User Guide(English) &nbsp&nbsp &nbsp&nbsp💬 WeChat(微信) &nbsp&nbsp We are excited to introduce Wan2.2 , a major upgrade to our foundational video models. With Wan2.2 , we have focused on incorporating the following innovations: 👍 Effective MoE Architecture : Wan2.2 introduces a Mixture of Experts (MoE) architecture into video diffusion models. By separa
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
