# Auditoria — hyperframes-launch-video

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `930f89186b8e155d632d9afe49054c02d4d7d85a`  
**Origem:** https://github.com/heygen-com/hyperframes-launch-video.git  
**Licença detectada:** `NOASSERTION` em `license file not found at repository root`

## Capacidade

reference implementation for launch-video composition.

- Manifests: nenhum detectado
- Linguagens amostradas: não identificadas
- Resumo do README, não verificado: HyperFrames Launch Video The composition source for HeyGen's HyperFrames launch video — a real production project you can clone, preview, and render yourself. Use it as a worked example of how to assemble a non trivial video in . Resolution: 1920×1080 @ 30fps Structure: 1 root composition ( index.html ) + 17 sub compositions wired together Techniques on display: CSS animations, GSAP, Lottie, shaders, Three.js, footage compositing, captions, SFX That's it. No package install step — HyperFrames runs via npx .
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
