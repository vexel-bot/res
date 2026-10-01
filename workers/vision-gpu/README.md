# Clicko vision-gpu preflight

Este diretório contém a imagem **preflight** do PGV-1. Ela prova o runtime e a attestation antes de qualquer provider real ser admitido. Não é uma imagem promovível: não contém OpenCV/TAPIR/RAFT/Depth Anything, checkpoints ou executor de inferência.

O manifest reserva `reality_analysis` e `video_physical_qc` na queue `studio.gpu.vision`, exige processo isolado, filesystem read-only, credenciais privadas e uma GPU NVIDIA atestada com pelo menos 22.528 MiB visíveis e compute capability 8.0. A lista de providers permanece vazia: os adapters fakes existem somente no harness de testes e não podem ser ativados como capacidade real.

Pinos atuais:

- base Linux AMD64 `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime@sha256:c8268a92...2755`;
- manifest canônico `fbe3c7a55ba2d98a7a12a4ae37e8b97b46d2282bcb89cfe5a657d6b60ac0efb1`;
- lock Python Linux/CPython 3.11 `1a40b7d969f33e72e8886ff898789f0191a5c63a63d958555ea23b736ee97fe0`;
- artifact inventory canônico `d1935d35ed3af59d792a5b0c9607d477ea661a862170f4e8574c7a94015dea0c`;
- physical policy canônica `8f4ff3bb19caf1c50dd6a6cd627ad6cd8b58f20bd6340f2efdd9abf01712aad0`.

O inventário fica em `benchmarks/studios/reality/pgv1-artifact-inventory.v1.json`. TAPIR e Depth Anything V2 Small têm integridade e licença aprovadas; RAFT weights e o bundle PyTorch/CUDA permanecem `review_required`. Por isso, o build preflight é permitido para inspeção, mas ativação e promoção continuam bloqueadas.

## Build preflight

```bash
docker buildx build \
  --file workers/vision-gpu/Dockerfile.preflight \
  --build-arg REQUIREMENTS_LOCK_DIGEST=1a40b7d969f33e72e8886ff898789f0191a5c63a63d958555ea23b736ee97fe0 \
  --build-arg WORKER_MANIFEST_DIGEST=fbe3c7a55ba2d98a7a12a4ae37e8b97b46d2282bcb89cfe5a657d6b60ac0efb1 \
  --sbom=true \
  --provenance=mode=max \
  --tag clicko/vision-gpu:0.1.0-preflight \
  .
```

`verify_build.py` recalcula inventário, manifest, policy e lock durante o build. Qualquer alteração nos bytes, provider não vazio ou inventário rejeitado/incompleto encerra o build.

O processo usa `app.vision_celery_app`, que registra somente o probe `app.tasks.probe_studio_worker`. Ele não importa o catálogo monolítico de tarefas e não expõe Radar, render, identidade ou geração. O provider registry permanece vazio.

Antes de transformar o preflight em runtime funcional:

1. obter decisão jurídica explícita para os pesos do RAFT e o bundle PyTorch/CUDA;
2. gerar license manifest e SBOM completos;
3. fixar os pacotes de visão transitivos e seus wheels Linux por SHA-256;
4. copiar somente os checkpoints aprovados, cada um verificado pelo inventário;
5. executar sem egress público, com object storage privado e workspace efêmero;
6. provar cancelamento, cleanup, quotas e attestation em worker GPU externo;
7. registrar providers reais somente depois dos gates; fakes nunca entram no registry promovido.

A VPS Nexus não é destino para este runtime.

OpenCut também não é dependência desta imagem: ele permanece no boundary do editor/timeline. A compreensão física produz evidências e marcações versionadas que o editor poderá visualizar, sem acoplar a inferência ao código do OpenCut.

## Freeze AI-0 — candidatos ainda inativos

Os inventários de Qwen3-VL, Ditto upstream, EchoMimicV3 Flash e Wan2.2 Animate ficam em
`providers/*.artifacts.json`. Eles congelam commits, lacunas de pesos/runtime e decisões de
licença, mas não adicionam código de inferência nem providers ao manifest:

- Qwen3-VL: `incomplete`; 4B/8B, vLLM/Transformers e imagem ainda sem bytes/digests;
- Ditto upstream: `rejected`; o bundle documentado inclui detector InsightFace;
- EchoMimicV3 Flash: `incomplete`; pesos, RetinaFace, dependências e imagem pendentes;
- Wan2.2 Animate: `incomplete`; lane avançada, fora do orçamento MVP de 24 GB.

O manifest continua com `providers: []`. Uma futura variante corrigida recebe novo inventário;
nenhum desses registros pode ser editado para apagar uma decisão anterior.

## Candidato OpenCV desativado

`providers/opencv-baseline.provider.json` descreve a primeira baseline clássica real: geometria/horizonte, movimento de câmera, tracks esparsos e assembly com abstenção. Seu status é `evaluation`, o digest canônico é `4be8fc9c8f66d56279543324c1c5bb74a0a42e62ba33b7ed21b96bd5a0417fcd` e o lock Linux separado é `ff9128c901530e0285efe0e258f6bef7314a72782d7650e25a315b41e7011e76`.

Esse lock não é copiado pelo `Dockerfile.preflight`; o worker continua sem providers. A prova real usa um venv externo e vídeo sintético, não representa promoção.

O corpus e o gate recomputáveis estão em `benchmarks/studios/reality/opencv-baseline-corpus.v1.json` e `benchmarks/studios/reality/opencv-baseline-run-2026-08-25.v1.json`. O runner `backend/scripts/run_opencv_reality_benchmark.py` recusa NumPy/OpenCV instalados que não correspondam ao lock e escreve o relatório fora do repositório por padrão. O run pinado passou 11/11 casos e 6/6 métricas, mas a ativação permanece `incomplete` enquanto o candidato estiver em `evaluation`; Docker/BuildKit Linux, SBOM, provenance, assinatura e revisão jurídica continuam gates separados.

`ProviderPromotionEvidenceV1`/`evaluate_provider_promotion_gate` são o gate de promoção: o candidato só pode ser anunciado quando os digests do inventário, benchmark, imagem OCI, SBOM, provenance e manifest coincidirem e attestation, no-egress, cleanup e storage tenant-scoped estiverem comprovados. O preflight atual falha fechado porque o inventário está `review_required` e o manifest não anuncia providers.

O workflow manual `.github/workflows/studios-vision-preflight.yml` reproduz esse build em runner Ubuntu `linux/amd64`, gera somente um OCI tar efêmero com SBOM/provenance e publica o artefato por sete dias. O passo `backend/scripts/verify_preflight_oci.py` valida também a plataforma, os blobs, os attestations e o label `io.clicko.providers=none`. Ele não faz push para registry, não registra provider e não implanta na VPS. Os digests canônicos do inventário, manifest e policy ficam pinados no workflow; uma alteração sem revisão quebra o build deliberadamente.

Quando uma imagem funcional for construída fora deste checkout, a decisão pode ser
recomputada sem alterar o registry do worker:

```bash
python backend/scripts/evaluate_provider_promotion.py \
  --backend backend \
  --candidate workers/vision-gpu/providers/opencv-baseline.provider.json \
  --inventory benchmarks/studios/reality/pgv1-artifact-inventory.v1.json \
  --evidence /secure/release/pgv1-provider-promotion-evidence.json \
  --manifest workers/vision-gpu/worker.manifest.json \
  --evaluated-at 2026-08-25T23:00:00Z
```

O comando imprime o `ProviderPromotionGateResultV1` canônico e retorna `0` somente
para `eligible`; `2` significa binding inválido/bloqueado e `3` significa evidência
externa ainda incompleta. `--allow-incomplete` existe apenas para inspeção local e
nunca transforma uma decisão incompleta em autorização de ativação. O arquivo de
evidência deve vir do pipeline que construiu a imagem e conter os digests reais,
assinatura/attestation, SBOM, provenance, testes de no-egress/cleanup e storage
tenant-scoped; não é permitido preencher esses campos com placeholders.
