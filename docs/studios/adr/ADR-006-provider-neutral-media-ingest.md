# ADR-006 — Ingestão e probe de mídia provider-neutral

**Status:** aceito para ingest/probe/proxy/reconform/waveform; transcrição automática e rollout físico pendentes  
**Data:** 2026-08-25

## Contexto

O primeiro slice de UGC precisa conhecer duração, streams, frame rate, resolução, áudio, container, bytes e checksum antes de criar timeline, proxy ou transcrição. Ler JSON do ffprobe diretamente na UI/documento acoplaria o produto à ferramenta e impediria troca de provider.

## Decisão

`StudioMediaIngest` referencia um `LibraryAsset` privado e possui state machine `pending → probing → ready|rejected|failed`. O endpoint dedicado cria o ingest e um `GenerationJob` `media_probe` idempotente; chamadas genéricas ao endpoint de jobs não podem fabricar esse job.

O port `MediaProbeProvider` recebe somente um arquivo materializado e retorna `MediaProbeResultV1` normalizado:

- container, duração, bytes e bitrate;
- video streams com codec, dimensões, pixel format, frame rate racional, duração e rotação;
- audio streams com codec, sample rate, canais/layout, duração e bitrate;
- provider/version e trace mínimo, sem copiar o JSON bruto para o domínio.

O adapter inicial usa `ffprobe` via subprocess sem shell, timeout configurável, limite de stdout e path vindo do `ObjectStorage`. O worker recalcula SHA-256 para assets legados sem hash e atualiza a linhagem.

## Execução e isolamento

`media_probe` recebe capability `media_cpu`, fila lógica `studio.media.cpu` e hard limit de 900 s. Como `STUDIO_ISOLATED_QUEUES_ENABLED=false`, nenhum worker novo foi ativado na VPS; o placement já está persistido para rollout futuro.

Um probe concluído pode resultar em:

- `ready`: possui vídeo e duração positiva;
- `rejected`: provider funcionou, mas o asset falhou validação de produto;
- `failed`: falha técnica após política de retry do job.

## Proxy editável

O endpoint dedicado `/media-ingests/{id}/proxy` cria um job idempotente `video_proxy`; a API genérica de jobs não pode fabricá-lo. O port `MediaProxyProvider` recebe o original materializado, `MediaProxySpecV1`, callback de progresso e verificação cooperativa de cancelamento. O adapter inicial `builtin.ffmpeg-proxy` produz MP4 H.264/AAC com dimensões/FPS limitados e valida o resultado novamente por probe.

O original permanece canônico e imutável. A saída é um novo `LibraryAsset` na zona `derived`, com checksum, spec, provider/version, job e `derivedFromAssetId`; `StudioMediaIngest.proxy_asset_id` apenas aponta para o proxy corrente. Cancelamento antes da execução ou observado antes da persistência não publica asset. Corridas tardias de cancelamento, interrupção distribuída e coleta de derivados antigos continuam gates do worker real.

## Licença e smoke local

O smoke real produziu MP4 sintético 360×640, 30000/1001 fps, H.264 + AAC e o adapter normalizou duração de 1.001.000 µs, dois streams e container MP4. A build local é `8.1.1-full_build-www.gyan.dev` com `--enable-gpl`, `--enable-version3`, x264/x265; ela é evidência de desenvolvimento, não build aprovada para redistribuição/produção.

## Rollback e gates

- migrations `0018_media_ingest` e `0021_media_waveform` são aditivas e passaram upgrade/downgrade/upgrade;
- uploads e exports legados permanecem funcionando sem ingest;
- remover/desligar o endpoint não altera assets originais;
- resultados canônicos não dependem do JSON FFprobe.

## Reconform e waveform

`MediaTimeMapV1` liga proxy e original por IDs/checksums, frame rates racionais, offsets de vídeo/áudio, duração, segmentos de taxa e drift máximo de um frame. O proxy só é publicado quando esse mapa passa validação; o player pode usar o proxy, mas decisões e render continuam ancorados nos microssegundos do original.

`builtin.ffmpeg-waveform` decodifica o stream de áudio selecionado como PCM mono em chunks limitados e persiste um manifesto JSON determinístico de buckets min/max/RMS. O decoder é cortado à duração provada para remover padding AAC; o manifesto retém checksum do original, stream, spec digest, provider e versão. A UI apenas projeta os buckets — não promove WaveSurfer ou estado visual a domínio.

Antes do rollout completo faltam: upload grande multipart, quarantine, thumbnails, transcrição automática, codec/build aprovada, worker externo, cancelamento distribuído/race tests, quotas e coleta de derivados antigos. Reconform, waveform e o E2E visual local foram concluídos; `CELERY_TASK_ALWAYS_EAGER` continua restrito ao ambiente de teste.
