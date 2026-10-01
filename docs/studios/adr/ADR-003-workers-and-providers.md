# ADR-003 — API, workers e providers dos Studios

**Status:** aceito  
**Data:** 2026-08-23

## Contexto

Celery/Redis já processam Radar com retry e idempotência, mas render visual é síncrono e não há jobs de geração com progresso/cancelamento. Vídeo, transcrição e avatar exigirão CPU/GPU e providers com licenças/custos diferentes.

## Decisão

Separar logicamente:

1. API: autentica, autoriza, valida contratos, cria/cancela jobs e consulta estado.
2. Orquestração Studio: casos de uso, state machine, idempotência, dependências e eventos.
3. Worker: executa fora da requisição web, atualiza progresso e respeita cancelamento.
4. Provider adapter: traduz contrato canônico para tecnologia externa e normaliza resultado/erros.

No estágio atual, os módulos continuam no mesmo repositório/deploy de desenvolvimento. O placement é persistido em cada job (`execution_capability`, `queue_name`, `resource_class`, `hard_time_limit_seconds`), porém `STUDIO_ISOLATED_QUEUES_ENABLED=false` mantém o worker existente como caminho padrão. Filas físicas CPU/GPU e serviços separados só serão ativados depois de capacity planning, broker smoke e workers dedicados; a decisão detalhada está na ADR-004.

## Estado de `GenerationJob`

```text
queued → running → succeeded
   │        ├──→ retrying → running
   │        ├──→ failed
   └────────┴──→ cancel_requested → cancelled
```

Estados terminais são imutáveis. Progresso é monotônico. Resultado tardio de job cancelado é descartado. A mesma idempotency key com payload diferente gera conflito.

## Ports iniciais

- `VisualRenderProvider`
- `ResearchProvider`
- `TranscriptionProvider`
- `VideoRenderProvider`
- `VoiceCloneProvider`
- `AvatarProvider`
- `VisualCanvasProvider` apenas se uma engine externa for adotada

Um provider fake é obrigatório para contract/integration tests.

## Persistência e observabilidade

Cada job registra:

- workspace, actor, tipo, schema version e correlation;
- idempotency key + payload hash;
- status, progresso, attempts e timestamps;
- provider/model/version quando escolhido;
- capability, fila lógica, classe de recurso e hard time limit;
- erro normalizado, result/artifact refs e custo quando disponível;
- cancel request e motivo.

Logs não incluem segredos, prompts privados completos ou biometria desnecessária.

## Alternativas rejeitadas

- executar render/vídeo na requisição web;
- chamar SDK de provider diretamente do router/UI;
- usar Celery result backend como fonte única de verdade;
- criar GPU infra antes de medir necessidade;
- mapear todos os providers a uma interface artificialmente idêntica sem capabilities.

## Rollback

- adapters podem ser desligados sem mudar documento canônico;
- Pillow permanece provider compatível durante o primeiro slice;
- filas novas podem ser bloqueadas e drenadas;
- endpoint atual de export permanece até paridade do job;
- nenhum output cancelado/falho avança a review/publicação.

## Verificação

- state machine unitária;
- retry, idempotência, progresso e cancelamento em integração;
- autorização cross-workspace;
- provider fake A/B;
- worker eager + smoke com broker real quando disponível;
- evento/audit trail por transição.
