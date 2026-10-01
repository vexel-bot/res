# ADR-011 — Runtime atestado do worker `media_cpu`

**Status:** aceito e provado em Docker local; rollout de produção condicionado  
**Data:** 2026-08-25

## Contexto

Persistir `queue_name=studio.media.cpu` não prova que o job foi consumido por um runtime compatível. Um worker incorreto pode escutar a fila, ter versões divergentes de FFmpeg/fontes ou executar no mesmo processo do control plane. O plano exige isolamento, manifest, retry, cancelamento, cleanup e proveniência antes de usar a mesma fronteira para voz ou identidade.

## Decisão

O runtime dedicado possui `studio.worker-runtime-manifest.v1`, validado por Pydantic e por um bootstep obrigatório do Celery. O manifest declara capability, filas, classes de recurso, tipos de job, providers, paths, variáveis, toolchain e política de isolamento. Um manifest ausente, uma versão divergente ou um path inválido encerra o worker com código diferente de zero antes de ele anunciar `ready`.

Cada entrega em fila isolada recebe:

- `task_id` igual ao ID persistido do job;
- fila e soft/hard time limits do placement imutável;
- headers de workspace, correlação, capability e fila;
- `studio.worker-execution-context.v1` persistido no job antes do provider;
- runtime/version, digest canônico do manifest, digest da imagem fornecido pelo orchestrator, instance/host/PID, versões verificadas e timestamp.

O render copia o mesmo contexto para `VideoRenderResultV1`, lineage do asset e evento `studio.video.render_ready`. Execução embutida continua permitida enquanto a flag está desligada, mas declara `mode=embedded` e `attested=false`; não pode se apresentar como worker isolado.

## Probes e health

`app.tasks.probe_studio_worker` é enviado explicitamente à fila esperada e compara capability, queue e digest. `scripts/probe_studio_worker.py` falha se a resposta não vier de runtime isolado atestado. A imagem possui healthcheck por `celery inspect ping` direcionado ao próprio hostname.

## Evidência local

Imagem final testada: `clicko/media-cpu:0.1.0-attested-local`, 862.252.036 bytes, digest local `sha256:c636c1756e231371cc8af50b7dd05ce9f48202c2b99bf98501cb8b202e2e8eec`. Manifest: `sha256:24015eb5a531d980e187a3484e446a047b3a1bceaa5c0c036a63ce03915dc5ac`.

- manifest inexistente: boot terminou com exit `1` e `worker_manifest_unreadable`, sem `ready`;
- manifest válido: probe retornou `ready`, `attested=true`, fila `studio.media.cpu` e versões Node 22.15.0, Python 3.11.2, Celery 5.6.2, FFmpeg/FFprobe 5.1.9, Chromium 151.0.7922.173 e HyperFrames 0.8.12;
- processo separado: API e Celery rodaram em containers/PIDs distintos, UID 10001, rootfs read-only, rede Docker `internal=true`, capabilities removidas, `no-new-privileges`, 2 CPU, 2 GiB, 256 PIDs e tmpfs efêmero;
- mídia real: upload MP4 → Redis → worker → FFprobe terminou `succeeded` e persistiu a attestation;
- retry: um job bloqueado por path de fonte incorreto realizou 3 tentativas, não produziu output; após correção, retry manual do mesmo ID terminou `succeeded` em `attempts=4` no worker atestado;
- cancelamento: proxy de uma fonte sintética de 600 s foi cancelado após `running`, terminou `cancelled` na primeira tentativa e não deixou `proxyAssetId` nem asset com o `generationJobId`;
- migration: `0001 → 0023 → 0022 → 0023` passou em SQLite novo.
- regressão mais recente: 120 casos backend coletados, `119 passed, 1 skipped`; reducer de timeline `13 passed`; TypeScript, Ruff e build verdes; E2E `17 passed` em 1,7 min.

O primeiro smoke revelou que a imagem instala Liberation em `/usr/share/fonts/truetype/liberation`, enquanto o runtime anterior declarava `/liberation2`. O manifest bloqueou o job; Dockerfile e manifest foram corrigidos antes da prova final.

## Limites e rollout

Esta evidência prova separação física e contrato operacional local, não produção. O smoke usou Redis, SQLite e object storage local efêmeros. Antes de ativar `STUDIO_ISOLATED_QUEUES_ENABLED` fora do laboratório ainda são obrigatórios PostgreSQL, bucket S3 privado, IAM/KMS/TLS, broker gerenciado, métricas/alertas, reconciliação/dead-letter, quotas, autoscaling, lifecycle, SBOM/assinatura regenerados para a imagem promovida e runbook de rollback. A flag permanece `false` por padrão e a VPS Nexus não foi acessada nem alterada.
