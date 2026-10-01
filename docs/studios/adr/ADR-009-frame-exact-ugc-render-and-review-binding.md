# ADR-009 — Timeline frame-exact, render UGC limitado e binding de review

**Status:** aceito para o primeiro subconjunto UGC local; rollout de produção e composição avançada pendentes  
**Data:** 2026-08-25

## Contexto

O Video Studio precisava deixar de ser apenas uma superfície visual e provar o caminho “take real → edição → artefato revisável” sem adotar store, banco ou documento de um editor externo. Havia quatro riscos centrais: divergência entre proxy e original, operações em segundos/fracionários, render sobre o asset errado e review de uma versão diferente do MP4 apresentado.

## Decisão

### Timeline Clicko

`CreativeDocumentV1.composition.mediaTimeline` permanece canônico. Um reducer puro executa comandos `trim` e `reorder-ripple` em frames inteiros e frame rate racional. O primeiro escopo falha fechado para uma fonte, clips contíguos e tracks desbloqueadas; vídeo e áudio são pareados e captions, overlays e markers são remapeados junto com o ripple.

A UI pode projetar clips e handles livremente, mas envia um único `PUT` otimista no fim de cada gesto. Conflito `409` não faz merge implícito: recarrega a revisão canônica e informa o usuário. OpenCut é referência de ergonomia, não dependência de domínio.

### Reconform e preview

O proxy recebe `MediaTimeMapV1`, com IDs/checksums, frame rates, offsets de streams, segmentos e limite de drift. O player pode reproduzir a representação leve, mas o playhead e as decisões são convertidos para os microssegundos da fonte. Render nunca usa o proxy derivado como original.

### Render audiovisual limitado

`builtin.ffmpeg-ugc-v1` é o provider padrão somente para uma fonte UGC. Ele materializa os source ranges aceitos na ordem da timeline, escala/corta para 9:16 e produz H.264/AAC com timeout e cancelamento cooperativo. O provider suprime áudio embutido duplicado quando existe track de áudio pareada.

O provider também materializa um subconjunto tipado e fail-closed da composição: rectangles, texto de marca e uma track de captions lower-third. Geometria fracionária, rotação, layers fora do canvas, propriedades não suportadas, captions sobrepostas e limites de volume são recusados antes do FFmpeg. Texto do usuário é normalizado e escrito em arquivos temporários usados por `drawtext` com `expansion=none`; nunca entra como sintaxe do filter graph. A fonte é explícita e fixável na imagem do worker.

O resultado registra `renderedLayerIds` e `renderedCaptionTrackIds` no job e em `compositionProjection` no lineage do asset. Raio de rectangle, ênfase por palavra e transitions continuam fora do subconjunto e geram warning explícito. A saída permanece “prova privada” até os gates de worker, build e QC de produção.

### Artefato e revisão

O asset renderizado guarda `generationJobId`, provider/version, source asset bindings, digest do snapshot, revision/version e checksum. Review de documento `video` exige um job `video_render` bem-sucedido da mesma workspace/document/revision/version e valida o asset ativo e seu SHA-256. `StudioReviewRequest` fixa `renderJobId`, `renderAssetId` e `renderChecksumSha256` junto ao snapshot imutável.

## Segurança, isolamento e rollback

- job, ingest, asset e review são sempre filtrados por workspace; recurso externo retorna `404`;
- o original permanece privado e imutável; proxy, waveform e render são derivados com lineage;
- `CELERY_TASK_ALWAYS_EAGER` é permitido somente em teste e rejeitado em produção;
- HyperFrames permanece opt-in; remover o provider FFmpeg não invalida documentos nem snapshots;
- migrations `0021` e `0022` são aditivas e passaram `upgrade → downgrade → upgrade` em SQLite novo.

## Evidência

- 13 testes do reducer de timeline;
- smoke FFmpeg real e teste contra duplicação de áudio;
- E2E autenticado: MP4 real → probe → proxy/time-map → waveform → captions/corte → reorder/trim → render → review;
- output reprobed em 1080×1920, 30 fps, H.264/AAC e 47 frames;
- inspeção RGB do MP4 comprova faixa de marca, CTA e legenda no frame correspondente à cue;
- arredondamento de transcript adjacente é normalizado para não criar overlap de um frame;
- outro tenant recebe `404` no job e no conteúdo;
- regressão integral mais recente, já incluindo QC, runtime atestado e evidência verificável do ADR-012: 120 coletados no backend, `119 passed, 1 skipped`; E2E completo: `17 passed`.

## Próximos gates

1. Adicionar QC de loudness, black frames, A/V sync e limites de codec.
2. Repetir render+QC completo no worker atestado e promover o smoke local para PostgreSQL/S3/broker gerenciado, quotas, métricas e reconciliação; probe/retry/cancelamento de proxy já foram provados localmente na ADR-011.
3. Aprovar build FFmpeg/SBOM, fonte empacotada e benchmark de custo/capacidade.
4. Só depois ampliar para múltiplos assets, volume/fades, transitions, snapping e undo/redo.
