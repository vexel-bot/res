# Clicko llm-gpu preflight

Este diretório separa copy/planejamento dos workers de visão, fala e mídia. A imagem
**preflight** prova somente contrato, supply chain e attestation. Ela não contém vLLM,
SGLang, pesos Qwen/Kimi ou uma tarefa de inferência e não é promovível.

O manifest reserva `planning_copy` na queue `studio.gpu.llm`, exige um processo isolado,
filesystem read-only e uma GPU NVIDIA atestada com pelo menos 22.528 MiB visíveis. A lista
de providers permanece vazia. A VPS Nexus continua sendo control plane e não é destino
deste runtime.

Pinos canônicos:

- policy planning/copy: `88a37ca064d36a8b0f3c58fe4751f0a721b008359a80fe62212c452b4b17bc54`;
- inventory Qwen: `b81d63250d935ca5f6875a57fee0e44051ba706dbf96e8e081bb9c815acd6f67`;
- inventory Kimi: `2f747a155fa2b5182a82cf5804090feeed5968390bf41bc7174311b76d0a251d`;
- manifest: `102c8edaabec362d64be1c1b70955fbb8de4f7124d09d3d298a97265575cc6c1`;
- lock Python Linux/CPython 3.11: `1a40b7d969f33e72e8886ff898789f0191a5c63a63d958555ea23b736ee97fe0`;
- base PyTorch/CUDA: `sha256:c8268a92a69bd500f8be0e665b2630ee006dadaf7bfbc24249141b15ff622755`.

## Build preflight

```bash
docker buildx build \
  --file workers/llm-gpu/Dockerfile.preflight \
  --build-arg REQUIREMENTS_LOCK_DIGEST=1a40b7d969f33e72e8886ff898789f0191a5c63a63d958555ea23b736ee97fe0 \
  --build-arg WORKER_MANIFEST_DIGEST=102c8edaabec362d64be1c1b70955fbb8de4f7124d09d3d298a97265575cc6c1 \
  --sbom=true \
  --provenance=mode=max \
  --tag clicko/llm-gpu:0.1.0-preflight \
  .
```

`verify_build.py` recalcula policy, inventories, manifest e lock. Ele exige que os dois
inventories permaneçam `incomplete` e que `providers` permaneça vazio. Isso permite provar
a fronteira sem converter evidência de pesquisa em autorização de execução.

O processo usa `app.llm_celery_app`, que registra somente o probe comum de attestation.
O workflow manual `.github/workflows/studios-llm-preflight.yml` reproduz o build em
`linux/amd64`, produz um OCI tar efêmero com SBOM/provenance, verifica o label
`io.clicko.providers=none` e não faz push nem deploy.

## Evidência local de build — 26/08/2026

- build Docker/BuildKit concluído com o verificador interno `preflight-verified`;
- imagem local `clicko/llm-gpu:0.1.0-preflight`;
- digest local `sha256:efc205d418dc4d5458a88a457904cea18115c3fa2fd964a0c8050afc195ab326`;
- Linux AMD64, 3.349.739.431 bytes, usuário efetivo `clicko` (`uid/gid 10001`);
- policy, manifest e inventories Qwen/Kimi presentes no container;
- labels `io.clicko.providers=none` e base digest pinado confirmados;
- nenhum peso, vLLM/SGLang, endpoint, push, registry ou deploy foi incluído.

O gerador `backend/scripts/generate_synthetic_planning_corpus.py` também materializou,
fora do Git, 60 fixtures sintéticas (10 cenários × 6 variações). O manifesto resultante
tem digest `4b625660f6b0432191131de1ad8830e594a08868abe5002e29cc6baedebe4698`.
Isso prova a preparação e o binding do corpus, não uma execução de modelo.

Antes de uma imagem Qwen funcional, ainda é obrigatório:

1. escolher vLLM ou SGLang e fixar versão, wheels, CUDA e licença;
2. baixar Qwen3-4B em ambiente Linux externo e gerar manifest SHA-256 completo;
3. criar imagem funcional com SBOM, provenance e assinatura;
4. provar no-egress público, cleanup, cancelamento e isolamento por workspace;
5. executar os 60 casos sintéticos já preparados e medir schema, pt-BR, claims, latência e custo;
6. somente então anunciar o provider; Qwen 30B e Kimi permanecem lanes posteriores.
