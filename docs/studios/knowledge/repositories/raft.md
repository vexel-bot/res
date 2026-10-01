# Auditoria — raft

**Status:** `machine_inventory_complete_human_review_pending`  
**Decisão provisória:** `adapt`  
**Commit:** `2888e15a51fa41140771d3f498ed8023cff098d1`  
**Origem:** https://github.com/princeton-vl/RAFT.git  
**Licença detectada:** `BSD-3-Clause` em `LICENSE`

## Capacidade

optical flow candidate.

- Manifests: nenhum detectado
- Linguagens amostradas: Python, C++
- Resumo do README, não verificado: This repository contains the source code for our paper: Zachary Teed and Jia Deng The code has been tested with PyTorch 1.6 and Cuda 10.1. conda create name raft conda install pytorch=1.6.0 torchvision=0.7.0 cudatoolkit=10.1 matplotlib tensorboard scipy opencv c pytorch Pretrained models can be downloaded by running ./download models.sh You can demo a trained model on a sequence of frames python demo.py model=models/raft things.pth path=demo frames To evaluate/train RAFT, you will need to download the required datasets.
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
