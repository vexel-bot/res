# Auditoria — espeak-ng

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `7d426728fe146f4168fa716e29d8e276c7da33f2`  
**Origem:** https://github.com/espeak-ng/espeak-ng.git  
**Licença detectada:** `GPL-3.0` em `COPYING`

## Capacidade

offline speech synthesis runtime and pronunciation fallback.

- Manifests: nenhum detectado
- Linguagens amostradas: C, C++, Python, JavaScript
- Resumo do README, não verificado: eSpeak NG Text to Speech The eSpeak NG is a compact open source software text to speech synthesizer for Linux, Windows, Android and other operating systems. It supports . It is based on the eSpeak engine created by Jonathan Duddington. eSpeak NG uses a "formant synthesis" method. This allows many languages to be provided in a small size. The speech is clear, and can be used at high speeds, but is not as natural or smooth as larger synthesizers which are based on human speech recordings. It also supports Klatt formant synthesis, and the ability
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": false, "test_directory": true, "pt_br_signal": false}`
- Hardware: no GPU requirement established by static inventory; reproducible preflight still required
- PT-BR: `unknown`
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Evaluate behind an isolated worker/adapter; persist only canonical Clicko contracts.

Tipos do repositório não podem atravessar worker/adapter para domínio, banco ou API. Somente contratos Clicko versionados são persistidos.

## Riscos

- machine inventory does not validate model-weight or dataset licensing
- strong copyleft requires explicit legal/architecture review

## Benchmark mínimo

license + dependency preflight, fixed fixture, resource envelope, output quality, repeatability, failure observability and PT-BR where relevant.

## Revisão necessária

- [ ] confirmar licença de código, pesos, datasets e exemplos;
- [ ] medir inputs, outputs, hardware, tempo e memória;
- [ ] executar fixture reproduzível sem mídia pessoal;
- [ ] avaliar segurança e cadeia de suprimentos;
- [ ] revisar suporte PT-BR;
- [ ] aprovar ou substituir a decisão provisória.
