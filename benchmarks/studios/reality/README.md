# PGV-0 — Reality Model e Physical QC

Este diretório congela a linguagem, os contratos, as fixtures e os thresholds da primeira fase de inteligência de realidade dos Clicko Studios. **Nenhum modelo foi executado ou homologado.** Os três benchmarks estão `frozen`, mas todos os candidatos continuam `review_required`; portanto nenhum run pode produzir decisão `passed` enquanto código, pesos, dependências e artefatos não tiverem manifest legal verificável.

## Contratos

- `studio.reality-analysis-request.v1`: asset/checksum, time-map, frame rate racional, shots e policy de análise.
- `studio.reality-contribution.v1`: contribuição descartável de geometria, tracking, scene graph, world model, regra ou humano.
- `studio.reality-model.v1`: ativo provider-neutral com câmera, entidades, tracks, relações, eventos, hipóteses, evidências, limitações e lineage.
- `studio.shot-reality-constraint.v1` / `set.v1`: intenção física e técnicas editoriais por snapshot/shot.
- `studio.physical-plausibility-policy.v1`: política advisory e metas pré-run.
- `studio.physical-plausibility-evaluation.v1`: checks localizados ligados a documento, render, asset, Reality Model, constraints e policy exatos.

Invariantes relevantes:

- baixa confiança deve resultar em `uncertain`, nunca em `issue`;
- um `issue` exige ao menos dois grupos de sinais independentes;
- status da avaliação é derivado dos checks;
- `none` não pode coexistir com técnica criativa;
- shot surreal aprovado declara quais princípios ainda se aplicam;
- IDs de entidade/evidência/evento e ranges são validados como grafo;
- outputs são advisory, sem autocorreção ou autopublicação.

## Policies congeladas

| Arquivo | Suite | SHA-256 canônico do contrato |
| --- | --- | --- |
| `reality-understanding-policy.v1.json` | pares mínimos e contrafactuais | `16ae8a5985c19ba5a620bb6097baccdc0bb7329ead0cc9bcaec7b0b21a927301` |
| `physical-violation-detection-policy.v1.json` | detecção, grounding e localização | `909f3b556f3928cb099760a0e088eaacb8603194a325ea58cda37613c08190b0` |
| `reality-product-ugc-policy.v1.json` | false block e utilidade no Video Studio | `753eabd940ca10e9d74edab2c52ffdf805f293cb114105fe29ffec533123b4f6` |
| `physical-plausibility-policy.v1.json` | runtime advisory | `8f4ff3bb19caf1c50dd6a6cd627ad6cd8b58f20bd6340f2efdd9abf01712aad0` |

Os números são políticas experimentais definidas antes do primeiro resultado, não claims de qualidade: paired accuracy ≥ 0,75; recall crítico ≥ 0,90; precisão ≥ 0,80; temporal IoU ≥ 0,70; ECE ≤ 0,10; false block em UGC real ≤ 1%.

## Fixtures sintéticas

| Fixture | Digest canônico |
| --- | --- |
| `reality-model-supported-cup.v1.json` | `8a1753a13a43bd121ca2e97216068953165d40e8c8e69f4df092c586fc80efba` |
| `shot-reality-constraints-supported-cup.v1.json` | `f0f4f3e083a36e33a75abd799a4bdec53bdebdc793ef585244450ca72b8cbec1` |
| `physical-evaluation-clear.v1.json` | `271c3d9ed34961734026a863e34f55a3d1f1b94e45e26f9118023c4c2bea59c7` |
| `physical-evaluation-abstained.v1.json` | `b67b2a010e61f002aeedc08e8c97e0da2d3937d91295a82354d01c904165a89c` |

As fixtures só representam o contrato. Não provam visão, tracking, física ou qualidade de modelo.

Verificação local em 25/08/2026: PGV-0 teve 12 testes focados e 41 testes combinados de Reality/Kernel/execução/benchmarking. Após o preflight arquitetural, a regressão completa tinha 137 passes e 1 skip esperado. Com supply chain e baseline OpenCV, o backend completo coletou 159 casos: 156 passaram e 3 skips esperados permaneceram; as duas integrações OpenCV skipped no Python padrão passaram no venv externo pinado. Ruff permaneceu limpo.

## Pins de código auditados em 25/08/2026

| Projeto | Revisão | Estado legal operacional |
| --- | --- | --- |
| OpenCV | `8b7dc43c227746366213a65ad1477ed37fb8d365` | código Apache-2.0; build/deps ainda exigem SBOM |
| TAPNet/TAPIR | `c2cbab81cc06092b5f05bfe2da7bfec54e2079c9` | código e checkpoint panning Apache-2.0; bytes pinados por SHA-256 |
| RAFT | `2888e15a51fa41140771d3f498ed8023cff098d1` | código BSD-3-Clause; Things pinado por SHA-256, direitos do peso em revisão |
| Depth Anything V2 | `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf` | Small Apache-2.0 e pinado; Base/Large/Giant NC bloqueados |
| SAM 2 | `2b90b9f5ceec907a1c18123530e92e794ad901a4` | código/checkpoints Apache-2.0; cadeia/deps pendentes |
| V-JEPA 2 | `204698b45b3712590f06245fbfba32d3be539812` | código MIT/arquivos Apache; checkpoint e cadeia pendentes |

O clone V-JEPA 2 apresenta colisões de paths que diferem apenas por caixa no Windows. Ele serve para auditoria de fonte, mas a imagem Linux do futuro benchmark deve partir do commit e de um checkout limpo reproduzível.

Baseline OpenCV de avaliação em 25/08/2026: wheel Linux 4.13.0.92 `0525a3d2c0b46c611e2130b5fdebc94cf404845d8fa64d2f3a3b679572a5bd22`, NumPy 2.2.6 `ba10f8411898fc418a521833e014a77d3ca01c15b0c6cdcce6a0d2897e6dbbdf` e candidate manifest `4be8fc9c8f66d56279543324c1c5bb74a0a42e62ba33b7ed21b96bd5a0417fcd`. Um MP4 sintético procedural comprovou pan, horizonte, direção vertical, sparse tracks, bindings, abstenção e cancelamento. O wheel contém notices Apache/LGPL/terceiros e permanece `review_required`; ele não está na imagem preflight nem no registry.

## Próximo gate

O preflight PGV-1 já possui adapters fakes, orquestração provider-neutral, bindings exatos, artifact inventory fail-closed, definição pinada da imagem `vision_gpu` e uma baseline OpenCV real porém desativada. A avaliação ampla só começa após: revisão dos wheels e de RAFT/CUDA; build Linux com SBOM/provenance/assinatura; storage privado; persistência/cache tenant-scoped; worker externo; e materialização do corpus sintético/consentido fora do Git. A VPS existente permanece apenas control plane.
