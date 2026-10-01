# ADR-007 — Transcrições, legendas e decisões de edição versionadas

**Status:** aceito para contratos, edição manual e timeline direta; provider automático pendente  
**Data:** 2026-08-25

## Contexto

UGC assistido precisa sincronizar fala, texto, player, legendas e sugestões como remoção de silêncio. Persistir a resposta de WhisperX ou o estado de um editor externo como fonte de verdade acoplaria a Clicko a um provider, dificultaria correções humanas e faria uma sugestão automática parecer uma edição já aplicada.

## Decisão

`StudioTranscript` é o documento canônico `studio.transcript.v1`. Ele referencia um ingest `ready`, preserva asset, locale, provider e versão do provider, e contém segmentos/palavras ordenados com intervalos em microssegundos e confiança opcional. Correções criam nova `revision`/`version`, guardam até 50 snapshots anteriores e usam optimistic concurrency.

O primeiro provider é `manual`. O contrato permite um provider futuro, mas uma correção não pode trocar silenciosamente sua proveniência. WhisperX só entra por um adapter após benchmark PT-BR, revisão de licença de código/pesos/container, avaliação de diarização/alinhamento e sizing do worker.

`StudioEditDecisionSet` armazena sugestões e decisões editoriais separadamente do transcript. Cada decisão possui intervalo, operação (`keep`, `remove` ou `marker`), razão, confiança, origem e estado `suggested`, `accepted` ou `rejected`. IDs são únicos, referências a ingest/transcript/document são imutáveis durante uma atualização e nenhuma sugestão altera a timeline automaticamente.

`apply-captions` projeta segmentos para uma `CaptionTrackV1` editável no `CreativeDocument`. A conversão microssegundos → frames usa aritmética inteira racional: início arredondado para baixo e fim para cima. Cada cue preserva `sourceSegmentId` e confiança. A operação versiona o documento existente e respeita sua revisão esperada.

## Isolamento e idempotência

- toda consulta é limitada ao workspace do usuário e recurso alheio responde 404;
- criação exige `Idempotency-Key` e rejeita replay com payload divergente;
- segmentos, palavras e decisões não podem ultrapassar a duração provada pelo ingest;
- transcript e edit decisions produzem eventos de domínio auditáveis;
- aplicar captions requer que o asset do transcript esteja referenciado no documento de vídeo.

## Rollback e evidência

- migration aditiva `0019_transcript_edits`; o ciclo `0001 → 0019 → 0018 → 0019` passou em banco novo;
- 17 testes focados do Studio passaram após a mudança, incluindo o fluxo transcript → captions → edit decisions;
- Ruff passou nos contratos, serviços, router, models, migration e teste;
- OpenAPI/TypeScript foi regenerado após os novos endpoints;
- nenhum provider, peso, worker ou configuração da VPS foi ativado.

## Consequências e próximos gates

A UI manual, aplicação de decisões, waveform, proxy/reconform, manipulação direta por handles/reorder e E2E visual foram concluídos para o subconjunto UGC de fonte única. Toda interação gera um único `PUT` otimista no fim do gesto; conflito `409` recarrega o documento canônico. O reducer usa frames inteiros e remapeia vídeo, áudio, captions, overlays e markers sem mutar o input.

Ainda faltam edição por palavra, geração automática/WhisperX, smart cut/silence removal, snapping, undo/redo, múltiplos assets, volume/fades e render de captions/overlays. Sugestões automáticas continuarão revisáveis: somente decisões aceitas podem gerar nova revisão do documento.
