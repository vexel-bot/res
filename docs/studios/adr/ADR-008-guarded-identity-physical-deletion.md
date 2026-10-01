# ADR-008 — Exclusão física governada de identidade e voz

**Status:** aceito no domínio; rollout externo bloqueado  
**Data:** 2026-08-24

## Contexto

A migration `0017` já criava um plano idempotente, bloqueava novas gerações e enumerava amostras, derivados, previews e jobs. Faltava remover bytes sem transformar uma referência compartilhada, legal hold, falha de storage ou corrida com worker em perda silenciosa. Apagar a linha de `LibraryAsset` também destruiria proveniência e impediria comprovar o atendimento da solicitação.

## Decisão

A migration `0020_identity_delete_exec` adiciona lifecycle, legal hold e receipt a `LibraryAsset`, e lease/timestamps/attempts/receipt ao pedido de exclusão. O registro do asset sobrevive; o objeto e os dados reutilizáveis não.

```text
planned → queued → running → completed
                     ├──────→ queued   (job ainda cancelando)
                     └──────→ failed   (hold, referência ou storage)
failed ── replay idempotente ─────────→ running
```

Antes do primeiro delete, o executor:

1. re-resolve identidade, vozes vinculadas, versões, avaliações e jobs no mesmo workspace;
2. cancela jobs queued ou solicita cancelamento dos ativos e espera estado terminal;
3. preserva amostras de origem, salvo pedido explícito;
4. bloqueia cross-workspace, legal hold e qualquer referência viva fora do aggregate;
5. marca os candidatos como `deleting`, impedindo nova utilização.

Para cada objeto, a remoção é idempotente. O serviço apaga o blob, redige título/tags/URL/storage key/MIME/tamanho/checksum/metadados reutilizáveis e mantém somente tombstone e receipt sem chave bruta. Commits por objeto permitem retomar uma falha intermediária; o receipt final preserva histórico de tentativas. Perfis/versões são redigidos e marcados `deleted`; IDs e eventos mínimos permanecem para auditoria.

## Rollout e segurança

- `IDENTITY_DELETION_EXECUTION_ENABLED=false` é o padrão e o estado atual.
- A request HTTP apenas planeja quando a flag está off; quando on, enfileira em control worker e nunca apaga inline.
- Assets `deleting/deleted` não aparecem na biblioteca e não podem ser baixados, usados em documentos, ingest, proxy ou render.
- A VPS não foi consultada, alterada ou usada nos testes.

## Alternativas rejeitadas

- **Deletar linha e objeto juntos:** perde lineage/receipt e torna retry frágil.
- **Confiar apenas no plano `0017`:** não atende exclusão física.
- **Apagar mesmo com referência compartilhada:** produz quebra silenciosa e pode atingir outro aggregate.
- **Executar sincronicamente na API:** expõe a request a storage lento/falha parcial.

## Rollback

Desligar a flag impede novas execuções e preserva pedidos/receipts. Falhas podem ser corrigidas e repetidas pela mesma idempotency key. A migration possui downgrade testado para o estado `0019`, mas não deve ser revertida depois de uso comercial sem antes preservar receipts e avaliar tombstones. Bytes fisicamente removidos não são restaurados pelo rollback de schema.

## Evidência

Sete testes cobrem gate off, delete físico, preservação opt-in de source, legal hold sem delete parcial, referência compartilhada, espera/retry de job, falha parcial de storage, enqueue assíncrono, idempotência, invisibilidade do tombstone e upgrade/downgrade. Na regressão de 25/08/2026, após os slices de timeline/render, 97 testes passaram e 1 smoke HyperFrames opt-in ficou skipped entre 98 coletados.
