# Auditoria — liveportrait

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `reference-only`  
**Commit:** `9b294b3d0536135442ea73cb01e6cb3ca7029dd3`  
**Origem:** https://github.com/KwaiVGI/LivePortrait.git  
**Licença detectada:** `MIT` em `LICENSE`

## Capacidade

authorized portrait animation candidate.

- Manifests: requirements.txt
- Linguagens amostradas: Python, C++
- Resumo do README, não verificado: LivePortrait: Efficient Portrait Animation with Stitching and Retargeting Control Jianzhu Guo 1 † &emsp; Dingyun Zhang 1,2 &emsp; Xiaoqiang Liu 1 &emsp; Zhizhou Zhong 1,3 &emsp; Pengfei Wan 1 &emsp; 1 Kuaishou Technology&emsp; 2 University of Science and Technology of China&emsp; 3 Fudan University&emsp; 🔥 For more results, visit our homepage 🔥 2025/06/01 : 🌍 Over the past year, LivePortrait has 🚀 become an efficient portrait animation (humans, cats and dogs) solution adopted by major video platforms—Kuaishou, Douyin, Jianying, WeChat Channels—as well as numerous startups and creators. 🎉
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
