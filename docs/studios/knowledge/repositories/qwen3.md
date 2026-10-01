# Auditoria — qwen3

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `7a2f61ffc7a20d47efcd2bf97f6f2bf52729042e`  
**Origem:** https://github.com/QwenLM/Qwen3.git  
**Licença detectada:** `NOASSERTION` em `license file not found at repository root`

## Capacidade

language-model planning and critique candidate.

- Manifests: nenhum detectado
- Linguagens amostradas: Python, JavaScript
- Resumo do README, não verificado: 💜 Qwen Chat &nbsp&nbsp &nbsp&nbsp🤗 Hugging Face &nbsp&nbsp &nbsp&nbsp🤖 ModelScope &nbsp&nbsp &nbsp&nbsp 📑 Paper &nbsp&nbsp &nbsp&nbsp 📑 Blog &nbsp&nbsp ｜ &nbsp&nbsp📖 Documentation 🖥️ Demo &nbsp&nbsp &nbsp&nbsp💬 WeChat (微信) &nbsp&nbsp &nbsp&nbsp🫨 Discord &nbsp&nbsp Visit our Hugging Face or ModelScope organization (click links above), search checkpoints with names starting with Qwen3 or visit the , and you will find all you need! Enjoy! To learn more about Qwen3, feel free to read our documentation \ \]. Our documentation consists of the following sections:
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware: GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight
- PT-BR: `unknown`
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Keep outside the production domain until license, model assets, hardware and quality pass focused review.

Tipos do repositório não podem atravessar worker/adapter para domínio, banco ou API. Somente contratos Clicko versionados são persistidos.

## Riscos

- machine inventory does not validate model-weight or dataset licensing
- root license not detected; fail closed

## Benchmark mínimo

license + dependency preflight, fixed fixture, resource envelope, output quality, repeatability, failure observability and PT-BR where relevant.

## Revisão necessária

- [ ] confirmar licença de código, pesos, datasets e exemplos;
- [ ] medir inputs, outputs, hardware, tempo e memória;
- [ ] executar fixture reproduzível sem mídia pessoal;
- [ ] avaliar segurança e cadeia de suprimentos;
- [ ] revisar suporte PT-BR;
- [ ] aprovar ou substituir a decisão provisória.
