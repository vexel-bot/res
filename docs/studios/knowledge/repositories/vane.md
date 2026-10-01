# Auditoria — vane

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `7dc5d088f7262fbc5e39037f84940a8a2193c5fb`  
**Origem:** https://github.com/ItzCrazyKns/Vane.git  
**Licença detectada:** `MIT` em `LICENSE`

## Capacidade

candidate capability whose exact role must be established from code and benchmark.

- Manifests: package.json, Dockerfile
- Linguagens amostradas: TypeScript, TypeScript/React, JavaScript
- Resumo do README, não verificado: Vane is a privacy focused AI answering engine that runs entirely on your own hardware. It combines knowledge from the vast internet with support for local LLMs (Ollama) and cloud providers (OpenAI, Claude, Groq), delivering accurate answers with cited sources while keeping your searches completely private. Want to know more about its architecture and how it works? You can read it . 🤖 Support for all major AI providers Use local LLMs through Ollama or connect to OpenAI, Anthropic Claude, Google Gemini, Groq, and more. Mix and match models based on your needs.
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": true, "test_directory": false, "pt_br_signal": false}`
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
