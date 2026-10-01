# Auditoria — kimi-k2.5

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `c119f68d1a9a13f88f6a59b8e5e0840983b22689`  
**Origem:** https://github.com/MoonshotAI/Kimi-K2.5.git  
**Licença detectada:** `MIT` em `LICENSE`

## Capacidade

language-model planning research candidate.

- Manifests: nenhum detectado
- Linguagens amostradas: não identificadas
- Resumo do README, não verificado: 📰&nbsp;&nbsp; Tech Blog &nbsp;&nbsp;&nbsp; 📄&nbsp;&nbsp; Full Report 1. Model Introduction Kimi K2.5 is an open source, native multimodal agentic model built through continual pretraining on approximately 15 trillion mixed visual and text tokens atop Kimi K2 Base. It seamlessly integrates vision and language understanding with advanced agentic capabilities, instant and thinking modes, as well as conversational and agentic paradigms. Native Multimodality : Pre trained on vision–language tokens, K2.5 excels in visual knowledge, cross modal reasoning, and agentic tool use grounded in visual input
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
