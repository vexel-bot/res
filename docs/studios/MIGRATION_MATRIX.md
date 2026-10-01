# Clicko Studios — matriz de migração

**Data:** 2026-08-23  
**Estratégia:** strangler por vertical slice, com adapters e compatibilidade de rota.

| Existente | Destino | Estratégia de migração | Risco | Teste/gate |
| --- | --- | --- | --- | --- |
| `ApprovedEditorialDesk` local | Studio Editorial consumindo `CreativeBriefV1` e documento real | manter markup/CSS; substituir estado local por adapter do Kernel | alto: regressão visual ou perda de copy | screenshot + E2E autenticado + reabertura |
| `ApprovedVisualEditor` local | Studio Visual sobre `CreativeDocumentV1` | portar state/actions do `ProductSurfaceView.EditorSurface` para a UI aprovada | alto: E2E atual mascara ausência de persistência | autosave, conflito, reload, export e visual diff |
| `ApprovedCarouselBuilder` local | slice multipágina do mesmo documento | modelar pages/narrative; adaptar slide atual sem trocar engine | alto: quebra do documento atual | contract round-trip + reorder/version/export E2E |
| `ProductSurfaceView.EditorSurface` | adapter de compatibilidade | extrair lógica de criação/autosave/review e reutilizar; manter componente até paridade | médio: dois editores divergirem | teste compartilhado contra ambos durante transição |
| `useCreativeAutosave` | `useStudioDocument`/adapter v1 | reaproveitar debounce e 409; mudar para version/correlation explícitos | médio | fake timer + conflito concorrente + unload |
| `CreativeCanvas creative-v1` | composição de `CreativeDocumentV1` | envolver o canvas atual em contrato maior; migração lazy/read-compatible | alto: documentos existentes ilegíveis | fixtures v1, upcast, downgrade/rollback |
| ORM `CreativeDocument` com JSON | aggregate/provider-neutral | adicionar colunas/entidades mínimas sem apagar `document`; dual-read/dual-write temporário | alto: perda de dados | migration upgrade/downgrade + snapshot antes/depois |
| versões embutidas (máx. 20) | versões auditáveis | preservar leitura; introduzir version record gradualmente | médio | restore de versão antiga e nova |
| `Campaign.brief/strategy` JSON | `CreativeBriefV1` | adapter de leitura com referências, sem duplicar campanha | médio: drift semântico | contract test e lineage campanha/oportunidade |
| `BrandProfile.versions` | `BrandMemoryVersionRefV1` | resolver revisão na abertura do Studio; persistir apenas ref/snapshot mínimo imutável | alto: conteúdo usa marca errada | teste com duas revisões e dois workspaces |
| `Opportunity`/Radar | `OpportunityEvidenceRefV1` | adapter mantém URL, evidência, score version e temporalidade | médio | fonte/tempo/confiança preservados no documento |
| `LibraryAsset` + storage local | `AssetReferenceV1` + `ObjectStorage` | adapter local/S3, chave tenant-scoped e lineage; manter endpoint autenticado | alto: migração/lifecycle e direitos ainda incompletos | traversal, isolamento, checksum, asset inexistente, export e migration |
| export Pillow síncrono | `VisualRenderProvider` + job | primeiro encapsular engine atual; mover execução para worker depois de contrato | alto: timeout/duplicação | provider fake + idempotência + mesmo hash de saída |
| `JobAudit` Radar | `GenerationJobV1` | não renomear; criar semântica Studio e adapter quando compatível | alto: estados insuficientes | state machine, retry, cancel, progress, idempotência |
| Celery tasks Radar | workers Studios | placement por capability persistido; roteamento isolado atrás de flag até workers dedicados | médio | dispatch default/isolado, eager integration + worker real smoke |
| `GET /jobs/:id` | API de job Studio | preservar endpoint legado; adicionar progresso/cancelamento versionado | médio | tenant isolation e transições inválidas |
| Approval `Post`/`ApprovalEvent` | review handoff compartilhado | Studio cria request/ref; principal continua decidindo e publicando | alto: aprovar artefato errado | URL ID real, version pinning e decisão concorrente |
| Presenter em `workspace_resources` | Presenter/Identity boundary | Identity Library e Presenter autenticado já usam grant/perfil/versões reais; sessão genérica resta apenas para demonstração compatível. `avatar_video` é port especializado, persiste MP4 privado com lineage e retorna ao Video Studio; registry de produção inicia vazio | crítico jurídico | grant/revoke/expire, rosto/voz separados, ativação humana, tenant/role, provider/model benchmark, execução revalida direitos e adapter fake prova artefato/review-required |
| Express `/api/ai/*` e fallbacks | provider ports | encapsular gradualmente por capacidade; não usar fallback como sucesso real | alto: saída não rastreada | provider trace, unavailable state e sem segredo em log |
| `VideoEditorView`/`video-edit` | Video Studio | rota canônica estrangulada para `src/studios/VideoStudio`; `0018` entrega ingest/probe/proxy, `0019` transcript/captions/decisions, `0021` waveform/time-map, `0022` binding render→review e `0023` attestation do worker; contratos CX, telemetria neutra, handoff Editorial→Vídeo→Review e recuperação cross-session do render foram incorporados sem remover o legado de rollback | alto: escopo/GPU/licença | E2E guest/mobile/autenticado atravessa upload→edição→render/QC→reload→review e prova isolamento do artefato; faltam rollout externo, codec audit, custo medido e paridade audiovisual ampla |
| `Movimento · Depois` decorativo no Visual | Motion Inspector contextual sobre `MotionGraphV1` | mesma rota/documento; preview local, sugestão persistida e review são estados separados; projeção HyperFrames continua atrás do contrato provider-neutral | médio: aplicar grafo stale ou animar camada errada | E2E guest/reduced-motion + E2E autenticado + domain/API/projection tests; layer ID, document revision e constraints falham fechados |
| Express legado `image-edit` | Image Lab canônico + `ImageEditProvider` | rota por asset; original privado imutável; derivação PNG com checksum, mask, locks, idempotência e lineage; Pillow apenas adapter local substituível | alto: sobrescrever source, vazar mídia ou alegar lock inexistente | tests de bytes/checksum/tenant/idempotência + Playwright upload→derive→return; detecção automática permanece bloqueada |
| Radar RSS connector | `ResearchProvider` (se necessário) | Radar próprio permanece; Vane apenas adapter de pesquisa opcional | médio | citations/temporalidade e scoring inalterado |
| Rotas canônicas atuais | mesmas rotas | feature flag/adapters internos, sem URL paralela | médio | smoke das 37 telas + deep links |
| `OperationsContext` local | compatibilidade guest | manter demo claramente rotulada; produção autenticada usa backend | médio: mock vaza para produção | E2E autenticado falha se dado demo aparecer |
| `CanonicalProduct.tsx` monolítico | módulos `src/studios/*` | extrair somente componentes tocados por cada slice | médio: conflitos com founder UX | diff pequeno + lint/build/visual regression |

## Sequência de execução

1. Contratos v1 e tests, sem alterar rotas.
2. Repository/adapters sobre tabelas e canvas atuais.
3. `GenerationJob` com state machine e provider fake.
4. Integrar Visual aprovado ao documento real atrás de flag/adapter.
5. Adicionar carrossel multipágina e versionamento.
6. Fixar artefato/versão no review e export.
7. E2E autenticado do fluxo completo.
8. Só então avaliar remoção do caminho legado, com rollback disponível.

## Estados conhecidos antes da primeira migração

- UI aprovada: renderiza e passa 14 E2Es em guest, mas editores são locais.
- Backend criativo: autosave, conflito, version, restore, export e tenant isolation passam em pytest.
- Contrato: `creative-v1`, canvas único, provider-neutral apenas no nível básico das camadas.
- Rollback inicial: desligar integração Kernel e retornar ao componente aprovado local; dados existentes continuam na coluna `document`.

## Status desta entrega

| Etapa | Estado | Evidência |
| --- | --- | --- |
| Contratos v1 e testes | concluída | Pydantic/OpenAPI tipado, validação de carrossel, referências e tenant tests. |
| Repository/adapters | concluída para o slice | dual-read/dual-write `CreativeDocumentV1` ↔ `creative-v1`; migration `0010`. |
| `GenerationJob` | concluída no Kernel | state machine, idempotência, progresso, cancelamento, retry, eventos e troca de provider em teste. |
| Visual aprovado | concluída para save/version/reopen/export | adapter autenticado na rota existente; guest inalterado. |
| Carrossel multipágina | concluída para páginas/narrativa/save/version/reopen | sete páginas persistidas no E2E autenticado. |
| Review/export handoff | concluída para o slice | `StudioReviewRequest` fixa snapshot/version; decisão sincroniza Post; Visual gera PNG e Carrossel gera ZIP PNG ordenado com manifesto. |
| Autosave/conflito | concluída para o slice | debounce, save separado de versão, estado dirty/saving/conflict/offline e reload explícito. |
| Contexto real | concluída para o slice | E2E cria sinal → oportunidade → campanha → post; documentos preservam `brandRevision=2`, score version e URL da evidência. |
| E2E autenticado | concluída | teste cria usuário/workspace/oportunidade/campanha/post, revisa versão fixada, retorna ao calendário e verifica export multipágina. |
| Storage/placement MI-0 | fundação concluída, rollout condicionado | migration `0015`; uploads/exports via port local/S3; checksum/lineage; filas lógicas e time limits persistidos; flag isolada desligada. |
| Cápsula Identity/Voice | fundação governada e UI de matrícula concluídas; providers reais bloqueados | `0016`: avaliação/review; `0017`: deletion plan; `0020`: lifecycle/legal hold/tombstone/receipt. Identity Library cria asset visual e áudio separados, grant com quatro escopos, perfis/versões draft e revogação. Ativação exige avaliação/review; worker GPU e benchmark real seguem pendentes. |
| Presenter `avatar_video` | boundary e handoff implementados, rollout bloqueado | CreateJob exige documento, IdentityVersion e VoiceVersion ativas/vinculadas, grant vivo, escopos, provider/model aprovado, benchmark e worker anunciado. Execução revalida tudo, materializa samples tenant-scoped, persiste MP4/checksum/disclosure/lineage `reviewRequired` e entrega `sourceAsset` ao Video Studio. Registry vazio falha fechado até um adapter real ser promovido. |
| Motion contextual | concluído para opacity/scale e HyperFrames projection | `MotionGraphV1` sugerido → review humano → projection; reload e stale gate comprovados. Keyframe editor amplo/Motion Canvas runtime seguem pendentes. |
| Image Lab | concluído para ajustes determinísticos e derivação privada | rota/action/screen contracts, mask, regiões protegidas, checksum, provider port, event/lineage e retorno seguro. Smart crop/inpainting/detecção automática seguem pendentes. |
| UGC assistido | cadeia local autenticada concluída para o subconjunto de fonte única | MP4 real → asset privado → FFprobe → proxy/time-map → waveform → documento/captions → split → reorder/trim direto → FFmpeg original → asset/checksum → review exata. UI usa Blob autenticado e `CreativeDocument` continua fonte de verdade. |
| Transcript/captions/edit decisions | backend canônico e UI manual concluídos; rail ASR provider-neutral concluído; provider real pendente | `0019` mantém transcript manual → captions editáveis → decisões aceitas → selects/ripple frame-exact; `0024` registra o ator do job e `0025` persiste checksum/proveniência/métricas. Adapter fake prova ingest/asset/SHA-256, idempotência e transcript `draft`; WhisperX ainda depende de benchmark/licença/worker. |
| Render assíncrono | orquestração, provider FFmpeg e QC técnico ativos; worker `media_cpu` atestado provado localmente, rollout bloqueado | `builtin.ffmpeg-ugc-v1` é default para fonte única; `builtin.ffmpeg-qc-v1` persiste policy/métricas/checks e bloqueia review em blocker. Asset guarda source bindings, snapshot digest, IDs materializados e worker context; `0022` fixa job/asset/checksum e `0023` a execução. Produção exige PostgreSQL/S3/broker externo, calibração e supply chain aprovadas. |
| Remoção do legado | não iniciada | caminhos legados e projeção `creative-v1` permanecem como rollback. |
