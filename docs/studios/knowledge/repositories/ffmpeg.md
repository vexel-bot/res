# Auditoria — ffmpeg

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adopt`  
**Commit:** `1019f8f036602a8464185baa4857654337eeca14`  
**Origem:** https://github.com/FFmpeg/FFmpeg.git  
**Licença detectada:** `GPL-3.0` em `COPYING.GPLv2`

## Capacidade

deterministic media probe, transform and encode foundation.

- Manifests: nenhum detectado
- Linguagens amostradas: C, C++, Python, JavaScript
- Resumo do README, não verificado: FFmpeg is a collection of libraries and tools to process multimedia content such as audio, video, subtitles and related metadata. libavcodec provides implementation of a wider range of codecs. libavformat implements streaming protocols, container formats and basic I/O access. libavutil includes hashers, decompressors and miscellaneous utility functions. libavfilter provides means to alter decoded audio and video through a directed graph of connected filters. libavdevice provides an abstraction to access capture and playback devices.
- Sinais estáticos: `{"gpu_signal": false, "container_recipe": false, "test_directory": true, "pt_br_signal": false}`
- Hardware: no GPU requirement established by static inventory; reproducible preflight still required
- PT-BR: `unknown`
- Determinismo: `unknown`
- Observabilidade: partial: git provenance and manifests inventoried

## Integração proposta

Use behind a provider-neutral adapter with pinned version, deterministic fixtures and artifact lineage.

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
