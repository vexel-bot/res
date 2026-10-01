# Auditoria — wavesurfer.js

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `666ba74d4d1138137b235b5aeeac2cb383b7e022`  
**Origem:** https://github.com/katspaugh/wavesurfer.js.git  
**Licença detectada:** `BSD-3-Clause` em `LICENSE`

## Capacidade

waveform visualization and audio navigation.

- Manifests: package.json
- Linguagens amostradas: TypeScript, JavaScript
- Resumo do README, não verificado: Wavesurfer.js is an interactive waveform rendering and audio playback library, perfect for web applications. It leverages modern web technologies to provide a robust and visually engaging audio experience. Gold Sponsor 💖 – Professional Subtitle Editor Install and import the package: npm install save wavesurfer.js import WaveSurfer from 'wavesurfer.js' Alternatively, insert a UMD script tag which exports the library as a global WaveSurfer variable: Create a wavesurfer instance and pass various : const wavesurfer = WaveSurfer.create({
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware: no GPU requirement established by static inventory; reproducible preflight still required
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
