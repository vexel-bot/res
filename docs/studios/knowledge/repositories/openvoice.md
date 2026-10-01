# Auditoria — openvoice

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `74a1d147b17a8c3092dd5430504bd83ef6c7eb23`  
**Origem:** https://github.com/myshell-ai/OpenVoice.git  
**Licença detectada:** `OTHER` em `LICENSE`

## Capacidade

authorized voice-clone research candidate.

- Manifests: requirements.txt, setup.py
- Linguagens amostradas: Python
- Resumo do README, não verificado: As we detailed in our and , the advantages of OpenVoice are three fold: 1. Accurate Tone Color Cloning. OpenVoice can accurately clone the reference tone color and generate speech in multiple languages and accents. 2. Flexible Voice Style Control. OpenVoice enables granular control over voice styles, such as emotion and accent, as well as other style parameters including rhythm, pauses, and intonation. 3. Zero shot Cross lingual Voice Cloning. Neither of the language of the generated speech nor the language of the reference speech needs to be presented in the massive speaker multi lingual trai
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
- biometric/identity use requires explicit consent, private benchmark and deletion controls

## Benchmark mínimo

license + dependency preflight, fixed fixture, resource envelope, output quality, repeatability, failure observability and PT-BR where relevant.

## Revisão necessária

- [ ] confirmar licença de código, pesos, datasets e exemplos;
- [ ] medir inputs, outputs, hardware, tempo e memória;
- [ ] executar fixture reproduzível sem mídia pessoal;
- [ ] avaliar segurança e cadeia de suprimentos;
- [ ] revisar suporte PT-BR;
- [ ] aprovar ou substituir a decisão provisória.
