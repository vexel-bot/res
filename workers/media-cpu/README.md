# Clicko media CPU worker

Imagem isolada para `media_probe`, `video_proxy` e `video_render`. Ela não deve ser executada na VPS Nexus atual.

## Toolchain pinada

- Node `22.15.0`, imagem AMD64 fixada pelo digest OCI `sha256:01cbafb3...d87a04`;
- HyperFrames `0.8.12` via lockfile próprio;
- Python 3.11 e dependências backend pinadas;
- Chromium, FFmpeg e fontes Liberation vindos do snapshot Debian da imagem construída.

Antes de promoção, a pipeline ainda deve registrar e fixar as versões dos pacotes Debian resultantes. A base já está fixada por digest, mas o Dockerfile sozinho não transforma pacotes `apt` móveis em supply chain totalmente reproduzível.

O lock npm v3 contém 186 pacotes transitivos, todos com licença declarada. A auditoria de 24/08/2026 retornou zero vulnerabilidades conhecidas; esse resultado precisa ser refeito a cada build porque bancos de vulnerabilidade mudam.

## Build e SBOM

```bash
docker buildx build \
  --file workers/media-cpu/Dockerfile \
  --sbom=true \
  --provenance=mode=max \
  --tag clicko/media-cpu:0.1.0 \
  .
```

O artefato de CI precisa conservar: digest OCI, attestations SPDX/CycloneDX, `npm ls`, `pip freeze`, `ffmpeg -buildconf`, `chromium --version` e `hyperframes info`.

Prova local de 24/08/2026:

- imagem AMD64 `clicko/media-cpu:0.1.0-local`, digest OCI `sha256:bbfdabed4b7e9f0049d57c2877b6f1146886d89b3c864fe320c929b6c2cb7595`, 861.962.598 bytes;
- CycloneDX gerado diretamente da imagem: 809 componentes, 1.792.604 bytes, SHA-256 `AF5531A3CF188EEBC95E70F41D601CE5566A3DD5A3070D86D3392ED2E0E65204`;
- Node `22.15.0`, HyperFrames `0.8.12`, Chromium `151.0.7922.173`, FFmpeg `5.1.9`, Python `3.11.2` e Celery `5.6.2` verificados dentro da imagem;
- smoke sem rede, root filesystem read-only e UID `10001`: lint limpo e MP4 H.264 1080×1920, 30 fps, 2 s, 548.089 bytes em 24,4 s.

Prova distribuída de 25/08/2026:

- `worker.manifest.json` (`studio.worker-runtime-manifest.v1`) tem digest `24015eb5a531d980e187a3484e446a047b3a1bceaa5c0c036a63ce03915dc5ac`;
- imagem local final `clicko/media-cpu:0.1.0-attested-local`: 862.252.036 bytes e digest `sha256:c636c1756e231371cc8af50b7dd05ce9f48202c2b99bf98501cb8b202e2e8eec`;
- bootstep fail-closed encerrou com exit `1` quando o manifest não existia; nenhum `ready` foi emitido;
- probe de fila, ingest/FFprobe real, retry do mesmo job e cancelamento de proxy em `running` passaram com attestation persistida e sem asset vazado;
- healthcheck ficou `healthy` sob UID 10001, rootfs read-only, rede interna, 2 CPU, 2 GiB e limite de 256 PIDs.

Os digests acima identificam somente a prova Docker local. A imagem promovida precisa receber novo digest, SBOM e assinatura no CI; não reutilize a attestation/SBOM de 24/08 como se cobrisse bytes posteriores.

O SBOM local fica fora do repositório; CI deve regenerá-lo e publicar o documento junto da attestation da imagem promovida.

## Runtime obrigatório

- usuário não-root;
- filesystem read-only e `/tmp/clicko-hyperframes` montado como tmpfs efêmero, gravável pelo UID/GID `10001`, com pelo menos 4 GiB e `exec` habilitado; HyperFrames copia/executa binários nessa área e recusa pouco espaço livre;
- home efêmero gravável pelo UID/GID `10001`, com telemetria desabilitada antes do worker iniciar;
- bucket privado e credenciais somente para os prefixes do workspace/job;
- rede egress negada; liberar somente PostgreSQL, Redis e object storage privados;
- CPU/memória/PIDs/timeout limitados e um render por processo;
- fila exclusiva `studio.media.cpu`, dead-letter/reconciliação e autoscaling;
- secrets fornecidos pelo orchestrator, nunca incorporados à imagem.

`HYPERFRAMES_ENABLED=true` só é válido nesta classe de worker. O control plane/web continua com o registry desligado.

Os inventários AI-0 em `providers/` registram Motion Canvas, OpenTimelineIO e PySceneDetect como
opções `incomplete`. Eles não foram instalados na imagem e não aparecem no manifest. Motion
Canvas só pode avançar como projeção descartável de `MotionGraphV1`; OTIO como intercâmbio;
PySceneDetect como evidência de cenas. HyperFrames/FFmpeg continuam sendo o caminho real atual.

`STUDIO_WORKER_MANIFEST_PATH` e `STUDIO_WORKER_CAPABILITY` são obrigatórios juntos no worker e permanecem vazios no control plane. Produção também exige `STUDIO_WORKER_IMAGE_DIGEST=sha256:<64 hex>` fornecido pelo orchestrator. O boot valida manifest, paths e versões antes de consumir a fila.
