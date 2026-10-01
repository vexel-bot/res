# Auditoria — depth-anything-v2

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`  
**Origem:** https://github.com/DepthAnything/Depth-Anything-V2.git  
**Licença detectada:** `Apache-2.0` em `LICENSE`

## Capacidade

monocular depth estimation.

- Manifests: requirements.txt
- Linguagens amostradas: Python
- Resumo do README, não verificado: 1 HKU&emsp;&emsp;&emsp; 2 TikTok &dagger;project lead&emsp; corresponding author This work presents Depth Anything V2. It significantly outperforms in fine grained details and robustness. Compared with SD based models, it enjoys faster inference speed, fewer parameters, and higher depth accuracy. 2025 01 22: has been released. It generates consistent depth maps for super long videos (e.g., over 5 minutes). 2024 12 22: has been released. It supports 4K resolution metric depth estimation when low res LiDAR is used to prompt the DA models.
- Sinais estáticos: `{"gpu_signal": true, "container_recipe": false, "test_directory": false, "pt_br_signal": false}`
- Hardware: GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight
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
