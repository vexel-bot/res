# Clicko Studios — inventário do estado atual

**Auditoria:** 2026-08-23  
**Commit de referência:** `965a9bbbfceb05d479c67db84ac4582e567da841` (`main`)  
**Escopo:** frontend React, host Express, API FastAPI, SQLAlchemy/Alembic, Celery/Redis, storage local e testes.  
**Regra:** este documento descreve o código observado; relatórios anteriores são evidência auxiliar, não substituem a inspeção.

## 1. Resumo executivo

O repositório já contém um monólito modular funcional com autenticação, workspaces, memória de marca, Radar, campanhas, posts, aprovação, documentos criativos, assets, histórico, métricas, jobs e auditoria. A separação dos Studios deve reaproveitar essas capacidades.

O frontend, porém, possui três gerações coexistindo:

1. `src/canonical/CanonicalProduct.tsx`: experiência visual aprovada e rota prioritária, com 8.225 linhas.
2. `src/product/ProductSurfaceView.tsx`: implementação anterior com integração real de documento, autosave, conflito, exportação e envio à revisão, hoje sombreada nas rotas canônicas.
3. `src/components/*` e `OperationsContext`: superfícies legadas, parte delas persistida apenas em `localStorage` e parte ligada a endpoints Express de IA.

A divergência de maior risco é objetiva: `RouteSurface` envia os modos editorial, visual e carrossel para `Approved*`, que usam estado React, IDs fixos (`post-ritual`, `campaign-aurora`) e assets demonstrativos. O `EditorSurface` que usa o backend não é alcançado por essas rotas. Assim, o E2E atual comprova navegação e acabamento, mas não comprova o fluxo persistente exigido para o primeiro vertical slice.

## 2. Frontend e rotas dos Studios

### Rotas canônicas diretamente relacionadas

| Superfície | Rota | Implementação atual | Estado funcional observado |
| --- | --- | --- | --- |
| Hub de conteúdo | `/content` | `ApprovedContentHub` | Visual aprovado; usa conteúdo demonstrativo em diversos handoffs. |
| Editorial Desk | `/content/:id/edit?mode=editorial` | `ApprovedEditorialDesk` | Edição apenas em estado local; salvar mostra toast. |
| Visual Editor | `/content/:id/edit?mode=visual` | `ApprovedVisualEditor` | Ferramentas e camadas visuais; não salva `CreativeDocument`. |
| Carousel Builder | `/content/:id/edit?mode=carousel` | `ApprovedCarouselBuilder` | Adiciona/reordena estado local; não persiste páginas. |
| Motion/Video | `/content/:id/edit?mode=video` | `VideoStudio` + `useVideoStudio` em `src/studios/` | Superfície própria UGC: upload privado, media bin, player autenticado por Blob URL, pipeline de ingest, timeline canônica, captions manuais, corte frame-exact, overlays de marca, job de proxy/render e revisão. Guest permanece demonstrativo e identificado. |
| Presenter | `/content/:id/edit?mode=presenter` | `PresenterStudioSurface` + Identity Library | O guest mantém demonstração local não publicável. O modo autenticado usa perfis/versões reais de identidade e voz, consentimento versionado, readiness e job `avatar_video`; captura é encaminhada ao ingest privado governado, nunca persistida como booleano. A geração fica bloqueada sem versões ativas, voz vinculada, grant vivo, escopos e provider/modelo benchmarkados. O registry biométrico de produção continua vazio até promoção real. |
| Review | `/approvals/:id?view=creative` | `ApprovedReviewSurface` | Pode chamar decisão backend, mas seleciona o primeiro post do snapshot, não necessariamente o ID da URL. |
| Biblioteca | `/library/assets` | `ApprovedLibrarySurface` | Composição aprovada; parte das ações é demonstrativa. |
| Fábrica | `/factory` | `ApprovedFactorySurface` | Estados e mensagens locais; não acompanha jobs reais de Studio. |
| Campanha | `/campaigns/:id` e subrotas | `CampaignSurface`, `WorldSurface`, `MoodboardSurface` | Campanha criada no backend no intake autenticado; vários links internos usam IDs fixos. |
| Publicação/retorno | `/calendar`, `/publish/:id`, `/content/:id` | superfícies aprovadas | UI preservada; publicação externa continua corretamente bloqueada sem conector. |

### Componentes canônicos e legados

- Canônicos: `CanonicalProduct`, `ApprovedEditorialDesk`, `ApprovedVisualEditor`, `ApprovedCarouselBuilder`, `VideoStudio`, `ApprovedReviewSurface`, `ApprovedFactorySurface`, `PresenterStudioSurface`.
- Motor funcional legado a migrar: `ProductSurfaceView.EditorSurface` e `useCreativeAutosave`.
- Legados ainda preservados: `CreationStudioView`, `ImageStudioView`, `VideoEditorView`, `StudioImmersiveView`, `CreativeMatrixView`, `SmartBriefingView`, `TemplatesView` e superfícies de operações/governança.
- O roteador é History API próprio (`src/app/router/navigation.ts`); não há React Router.
- `isCanonicalPath()` tem precedência em `App.tsx`, por isso as rotas aprovadas não chegam ao editor funcional anterior.

### Chamadas de API

- Cliente tipado OpenAPI: `src/api/productApi.ts`, consumindo `/api/v1` para workspaces, campanhas, posts, creatives, assets, aprovação, Radar, analytics e `workspace_resources`.
- Contexto principal autenticado: `ProductDataContext`, com snapshot por workspace e refresh após mutation.
- Compatibilidade legada: `ServerStateContext` e `OperationsContext`; este último mantém domínio paralelo no navegador e usa `localStorage`.
- IA Express: `/api/ai/chat`, `generate-campaign`, `generate-copy`, `analyze-metrics`, `generate-image`, `creative-matrix`, `intelligent-briefing`, `image-edit` e `video-edit`.
- IA FastAPI: apenas `chat`, `generate-campaign`, `generate-copy`, `analyze-metrics` e `generate-image` aparecem no OpenAPI. O host Express possui fallbacks próprios e ainda não implementa um contrato de provider de Studio.

## 3. Backend, dados e migrations

### Entidades persistidas relevantes

| Entidade | Ownership atual | Observação para Studios |
| --- | --- | --- |
| `User`, `Workspace`, `Membership` | principal | Reutilizar; não duplicar autenticação ou tenant. |
| `BrandProfile` | principal | Memória versionada em JSON; Studio deve referenciar a revisão aplicada. |
| `Opportunity`, `ExternalSignal`, `RadarSource` | Radar/principal | Fornecer `OpportunityEvidence`; não mover scoring ao Studio. |
| `Campaign` | principal | `brief`, `strategy` e `provider_trace` são JSON; origem útil para `CreativeBrief`. |
| `Post`, `ApprovalEvent` | principal | Artefato volta para revisão/publicação por referência. |
| `CreativeDocument` | transição/Studios | Tabela existente é o ponto de strangler; hoje guarda um `CreativeCanvas` v1 e até 20 snapshots embutidos. |
| `LibraryAsset` | compartilhado | Metadados e binários separados, mas faltam hash, direitos/licença e proveniência estruturados. |
| `FeedbackEvent` | compartilhado | Já liga oportunidade, campanha, conteúdo e creative; eventos não são contratos versionados. |
| `JobAudit` | infraestrutura | Usado apenas por Radar; não possui progresso, cancelamento, payload/result, correlation ou estado terminal de cancelado. |
| `WorkspaceResource` | compatibilidade | Armazena integração, presenter e outros payloads genéricos; não é substituto do domínio de Studio. |
| `AuditEvent` | principal | Reutilizar para ações administrativas e trilhas compartilhadas. |

### Cadeia Alembic

- `0001_initial` a `0009_brand_versions`.
- `0005_creative_documents` criou a tabela atual de documento criativo.
- `0006_history_learning` ligou feedback e métricas.
- `0007_workspace_features` criou recursos genéricos e auditoria.
- `0008_approval_events` persistiu revisão.
- Upgrade limpo até `0009_brand_versions (head)` foi executado em SQLite durante esta auditoria.

### Documento e assets atuais

`CreativeCanvas` (`schemaVersion = creative-v1`) contém dimensões, safe area, background, tokens de marca e camadas discriminadas de texto, forma e imagem. É serializável e não depende de Fabric/Konva, o que é um bom ponto de partida, mas ainda não representa:

- estratégia/briefing e evidências;
- páginas/cenas e narrativa de carrossel;
- tracks/timing para vídeo;
- referências tipadas a oportunidade, versão de marca e assets;
- direitos, hash e proveniência;
- lineage de provider/modelo/parâmetros;
- review/export estruturados no próprio contrato;
- versão do contrato externo independente do canvas v1.

Uploads privados usam `LibraryAsset.storage_key` e endpoint autenticado. Desde a migration `0015`, upload e exports passam pelo port `ObjectStorage`, com adapter local padrão e S3-compatible opcional; chaves novas são escopadas por workspace e persistem checksum SHA-256, MIME, bytes e metadados mínimos. Exportação ainda é síncrona na requisição web via Pillow. Bucket, multipart, quarantine, lifecycle e política de retenção ainda não foram provisionados/entregues.

## 4. Jobs e workers

- Celery 5.6 + Redis estão configurados.
- Tasks atuais: sincronização de fontes Radar, limpeza de sinais e ranking por workspace.
- Pontos existentes: `Idempotency-Key`, retry exponencial limitado, `acks_late`, rejeição quando worker morre, time limit e auditoria de falha.
- Lacunas para `GenerationJob`: não há criação genérica de jobs de Studio, progresso, cancelamento, dependências, prioridade, artefatos, custo, provider/modelo, correlation ID, payload/result versionado ou dead-letter explícito.
- O endpoint `GET /api/v1/jobs/:id` aplica isolamento por membership, mas jobs sem workspace ficam inacessíveis por definição.
- Render criativo continua síncrono no processo web.

## 5. Dependências de domínio

- Workspace: validado por membership em routers; recursos de outro tenant retornam 404.
- Marca: não é duplicada no backend, porém telas aprovadas usam `demoBrands` quando guest e nem sempre carregam a revisão real no documento.
- Radar: oportunidade pode originar campanha e preserva fonte/evidência; o editor aprovado não recebe esse contexto tipado.
- Campanha: `campaign_id` existe em post/document/asset; telas têm handoffs com IDs fixos.
- Aprovação: eventos e transições são persistentes e isolados; a rota aprovada deve passar o ID real até a mutation.
- Publicação: conexão externa real é deliberadamente bloqueada; pacote/manual scheduling existem como experiência honesta.

## 6. Funções sem UI aprovada ou sem execução real

- `image-edit`, `video-edit`, `creative-matrix` e `intelligent-briefing` existem como endpoints Express/legados, não como contratos versionados do Kernel.
- Motion avançado agora possui `MotionGraphV1`, evaluator fail-closed, projeções HyperFrames/Motion Canvas e persistência/API tenant-scoped em `0026`; o runtime HyperFrames offline responde a seek somente para projeção revisada. Motion Canvas executável, paridade visual, smart resize, layout generativo, coedição, provider ASR real e GPU worker funcional ainda não existem ponta a ponta. O rail provider-neutral de transcrição já persiste resultados validados em teste, e o render UGC limitado já existe localmente; nenhum deles equivale a rollout de produção.
- Consentimento, perfis/versões de identidade e voz, avaliação, preview privado, ativação humana e exclusão física governada agora existem no backend (`0014`/`0016`/`0017`/`0020`). Ainda não há UI da cápsula nem provider biométrico aprovado; a execução destrutiva permanece desativada por padrão.
- Ingest/probe e proxy editável existem desde `0018`. `0021` adiciona waveform determinística e `MediaTimeMapV1` validado por checksum, frame rate racional, offsets de stream e limite de drift para reconciliar proxy e original. Transcript manual, captions e decisões continuam canônicos em `0019`; `0024` liga jobs ao ator solicitante e `0025` adiciona checksum/proveniência/métricas ao transcript automático. A timeline Clicko executa trim por handles e reorder-ripple em frames inteiros, sincronizando vídeo, áudio, captions, overlays e markers sem adotar store/formato OpenCut. `builtin.ffmpeg-ugc-v1` renderiza do original os cortes, captions lower-third, rectangle e texto de marca suportados, registrando IDs materializados no lineage; `0022` obriga review de vídeo a apontar para job, asset e checksum da revisão/versão exatas. `0023` persiste `workerExecutionContext`; manifest, boot gate, probe, retry e cancelamento foram provados em worker Docker local. Provider ASR real/benchmark, múltiplos assets, radius, ênfase, transitions, volume/fades, undo/redo, thumbnails e rollout externo de produção continuam pendentes.
- Consentimento, expiração, revogação, plano e executor físico possuem entidades/serviços próprios. O executor faz preflight de jobs, legal hold, tenant e referências compartilhadas, remove objetos idempotentemente e mantém tombstones/recibos. `IDENTITY_DELETION_EXECUTION_ENABLED=false` preserva o rollout seguro; UI da cápsula, control worker dedicado e validação operacional do storage de produção continuam pendentes.
- A UI de vídeo faz polling dos jobs de proxy, waveform e render, carrega artefatos privados por Blob autenticado e oferece atualizar/cancelar/repetir. A leitura filtrada `GET /studios/v1/jobs` agora recupera o último render do documento após reload, recompõe sua prova privada e mantém o gate de revisão ligado à revisão/versão/QC exatos. O custo continua honestamente exposto como não medido neste worker; telemetria de custo real ainda falta.
- Exportação multipágina, comparação/restauração persistente e retorno Studio → aprovação permanecem comprovados no E2E canônico; vídeo agora acrescenta binding obrigatório ao artefato renderizado.
- Funções legadas devem permanecer registradas e compatíveis; ausência de frame não autoriza remoção.

## 7. Testes e lacunas

- Backend: baseline integral atual de 353 itens coletados; 350 passaram e 3 integrações opt-in foram ignoradas, exit `0`. O escopo inclui corpus planning/copy 60/60, `llm_gpu` preflight, evaluator temporal/físico fail-closed, motion offline seekable, migration `0026`, idempotência/revisão/conflito e isolamento tenant do grafo, supply chains e locks CUDA Kokoro/Chatterbox/OpenVoice, entrypoints e recipes candidatos, handoff efêmero consentido, admissão privada 10×6 sem dados humanos, evidência fail-closed do run local e semântica separada de mecanismo versus execução de cleanup.
- A projeção read-only `GET /api/v1/studios/v1/capabilities` retorna `studio.capabilities.v1` por workspace, com status, contagens de registry, consentimento, benchmark/licença, razões e flags `providerReady`/`captureReady`. O snapshot autenticado do frontend consome essa projeção; com `providers: []` e sem corpus/benchmark aprovado, Presenter/voz/avatar/transcrição continuam fechados. `transcription` é uma capability não biométrica na projeção e não pede `publish.synthetic`; ainda assim exige provider, modelo, benchmark e worker anunciados. `publicationAllowed` é um gate separado e exige `publish.synthetic` ativo; preview/captura privados não autorizam publicação por si só.
- O registry agora possui endpoints governados para listar/registrar/aprovar providers e modelos (`/studios/v1/providers` e `/studios/v1/models`), sempre exigindo owner/admin do workspace e registrando eventos de domínio. A aprovação continua exigindo manifesto de SBOM/licença/exit strategy ou weights/dataset/deletion, e não altera os manifests dos workers nem anuncia provider.
- `src/api/productApi.ts` expõe contratos tipados de capabilities, providers, modelos, consentimentos, perfis e versões de identidade/voz e jobs. A Identity Library usa essas entidades reais; o Presenter consulta apenas providers `avatar_video` aprovados e nunca promove candidato automaticamente.
- Frontend E2E: `26 passed` em 2,9 min na regressão integral de 2026-08-29, com execução serial e servidores/storage/SQLite isolados. O cenário UGC autenticado gera MP4 H.264/AAC real, atravessa upload → probe → proxy/time-map → waveform → captions → split → reorder/trim direto → render privado → QC → review vinculada, reprova acesso cross-tenant e reprobe o output em 1080×1920, H.264/AAC e 47 frames. As 59 URLs conhecidas, duas marcas, Biblioteca/Image Lab, Motion, Presenter e Visual/Carrossel continuam verdes; o E2E Presenter segue explicitamente no workspace demonstrativo, enquanto a tela autenticada falha fechada sem provider/evidência.
- Contratos visuais: 57 referências e tipografia mínima passam.
- QC técnico `ugc-review-v1` agora é parte imutável do render e bloqueia review quando faltam streams, codec/canvas/FPS divergem, sync/duração excedem 80 ms ou black frames passam de 5%. Loudness, true peak e silêncio começam como warnings auditáveis; calibração em corpus real permanece pendente.
- Fila isolada nunca pode alegar compatibilidade sem `studio.worker-runtime-manifest.v1`; o job e o render preservam `studio.worker-execution-context.v1`, enquanto modo embedded declara `attested=false`.
- Lacuna crítica atual: o E2E de browser prova a cadeia local completa do subconjunto UGC e continua eager para isolamento determinístico da suíte. Em paralelo, um smoke Docker prova API/controlador e `media_cpu` em processos distintos com Redis, attestation, retry e cancelamento sem vazamento. PostgreSQL/S3/IAM, broker gerenciado, métricas/alertas, reconciliação/dead-letter, quota/autoscaling, calibração da policy e build FFmpeg promovida/assinada continuam gates de produção.
- Player, media bin, waveform, preview com reconform, timeline direta e saída foram inspecionados em 1440×1000. Preview e renderer agora consomem as mesmas cues e camadas canônicas do subconjunto básico; o E2E inspeciona pixels de caption, faixa e CTA. Radius, ênfase e composição avançada permanecem warnings/gates explícitos.
- Voz stock, clone e avatar possuem políticas provider-neutral congeladas, candidatos/revisões, thresholds, controles e evidências versionados. Stock/clone foram separados por corpus, risco, hardware e custo. As fronteiras preflight `speech_cpu`/`speech_gpu` permanecem com `providers: []`. Kokoro stock foi executado localmente como candidato; nenhum corpus biométrico, score humano ou runtime de clone foi introduzido.
- O corpus stock PT-BR sintético foi executado de verdade com Kokoro `pf_dora` em imagem Linux/AMD64 local, offline, não-root e não anunciada: 64/64 WAVs foram produzidos sem falha, RAM máxima `1,385 GB` e custo estimado `US$ 0,000613/min`, mas o p95 RTF foi `2,338` para threshold `≤1,0`; portanto a decisão técnica e de ativação é `failed`. A evidência não biométrica versionada está em `benchmarks/studios/identity/kokoro-pf-dora-local-run-2026-08-26.v1.json`; WAVs, sidecars e três pacotes cegos permanecem fora do Git. Licença composta, revisão humana/ASR, SBOM estritamente local, provenance OCI e cleanup continuam pendentes.
- `app.services.studios.speech` materializa os ports tipados em jobs reais: valida digest do roteiro, checksum do áudio e provenance, grava no zone `voice` do object storage escopado por workspace, persiste `LibraryAsset`/evento/resultado versionado e faz rollback físico em adulteração. TTS stock e clone usam registries separados. A cobertura usa somente providers fake injetados; o control plane exige provider/modelo/benchmark/anúncio aprovados e os registries de execução permanecem vazios.
- O boundary de `voice_clone` é aplicado no router, no serviço de criação e no executor: exige `voiceVersionId`, consentimento ativo, versão vinculada a perfil `cloned` e identidade não destacada. Chamadas HTTP inválidas retornam `422`; chamadas internas e jobs legados falham antes do provider, sem criar asset. O registry de speech continua vazio e nenhum provider é anunciado.
- A supply chain Chatterbox/Perth avançou sem ativação: código Chatterbox `5de7a54...b85c2`, V3 `5bb1f6e...a6d18`, pack pt-BR `b3952f1...770d` e Perth `ce86c49...d2330` foram auditados. O manifesto `studio.chatterbox-model-assets.v1` fixa oito caminhos/tamanhos/SHA-256 e detecta o loader separado do pack pt-BR. O inventário `review_required` agora é `45242126...e0819`. Os quatro assets dedicados pt-BR, 3.206.662.605 bytes, foram materializados em diretório local ignorado pelo Git e revalidados por SHA-256. A imagem v2 aceitou CUDA e o layout read-only, mas o host possui 4.095 MiB contra o piso `speech_gpu` de 16.384 MiB; portanto inferência, biometria e provider continuam bloqueados.
- O handoff privado de clone agora existe sem ativar motores: seleciona uma amostra da `VoiceVersion` ativa, exige asset de áudio no mesmo workspace, revalida consentimento/identidade/checksum, normaliza por FFmpeg para WAV PCM16 mono/24 kHz de 3–30 s em diretório temporário e chama somente `VoiceCloneProvider`. `VoiceCloneReferenceV1` e `SpeechProvenanceV1` ligam versão, grant e checksum; divergência ou adulteração falha antes do provider, e a referência normalizada é removida após o job. O arquivo fonte consentido permanece sob a política de retenção/exclusão da cápsula.
- A supply chain OpenVoice V2 também foi congelada sem baixar pesos grandes nem inferir: código `74a1d147...`, converter `f36e7edf...`, WavMark wheel/checkpoint e três arquivos de modelo estão fixados por SHA-256 em `studio.openvoice-model-assets.v1` (`035360cd...9d7c`). O inventário segue `incomplete` (`6e744823...496e1`) por cadeia Kokoro composta e licença WavMark em revisão. A imagem local `bdadbe1e...7d61c` passou smoke isolado e não contém checkpoints Kokoro/OpenVoice/WavMark; SBOM/notices, assinatura, GPU attestation e benchmark continuam pendentes.
- `AuditedVoiceCloneSidecarProvider` implementa uma única fronteira offline para `chatterbox-multilingual-v3`, `chatterbox-pt-br` e `kokoro-openvoice-v2`, preservando loaders/pipelines distintos. O adapter exige comando absoluto e attestation de imagem/manifest, revalida todos os assets a cada job, verifica formato/watermark/result binding, mede tempo/custo e termina o processo em cancelamento/timeout. Os testes usam sidecar subprocess real com bytes sintéticos; runtimes ML e imagens candidatas ainda não foram executados, logo isso não comprova inferência nem ativa provider.
- Os entrypoints candidatos Chatterbox e Kokoro+OpenVoice usam as APIs reais esperadas, exigem offline/CUDA, preservam o roteiro integral e possuem testes com runtime ML injetado. Os locks CUDA 12.4 congelam 125 e 130 pacotes; as imagens OCI locais finais passaram CLI/UID/import smoke isolado em Docker Linux AMD64. O Chatterbox v2 também enxergou os pesos pt-BR montados read-only e falhou fechado no hardware antes de qualquer áudio. Isso valida assets/empacotamento, não inferência: ainda faltam GPU externa elegível, SBOM/notices, provenance de promoção, assinatura, benchmark privado consentido e promoção.
- Transcrição automática possui `TranscriptionRequestV1`, `TranscriptionResultV1`, `TranscriptionJobResultV1`, port `TranscriptionProvider` e registry separado de síntese. Jobs `transcription` exigem admission própria (`benchmarkStatus`, modelo comercial, worker anunciado), ator solicitante e binding exato de ingest/asset/SHA-256. Um adapter fake injetado prova persistência idempotente em transcript `draft`, timestamps limitados à mídia e provenance/métricas auditáveis; adulteração não produz registro. Com registry vazio, o fluxo falha antes de abrir bytes; o transcript manual continua disponível. WhisperX real segue pendente de benchmark/licença/worker.

## 8. Baseline a preservar

- Todas as rotas acima devem continuar abrindo.
- Shell, navigation, Production Rail, tokens e layouts aprovados não serão redesenhados.
- Autenticação, workspaces, marca, Radar, campanhas, aprovação e publicação permanecem no sistema principal.
- Editor por camadas, autosave com conflito, versionamento/restauração, exportação Pillow, assets privados, Presenter e funções legadas permanecem até feature parity comprovada.
- Nenhum código antigo será removido durante a introdução do Kernel.

## 9. Estado após o primeiro corte vertical

O inventário das seções 1–8 permanece como fotografia do baseline. Nesta entrega incremental, as seguintes lacunas foram fechadas sem remover o caminho anterior:

- `CreativeDocumentV1`, `CreativeBriefV1`, composição multipágina, refs de asset/brand/campaign/post/opportunity, lineage, review e export foram definidos em `backend/app/domain/studios` sem dependência de framework ou SDK;
- a tabela existente `creative_documents` ganhou envelope canônico, revision e correlation de forma aditiva, mantendo `document creative-v1` como projeção compatível;
- documentos legados são upcast em leitura; documentos novos fazem dual-write transacional do envelope e do primeiro canvas;
- `/api/v1/studios/v1` fornece criação, listagem/reabertura, replace com revisão otimista, versionamento e jobs;
- `StudioGenerationJob` e `StudioDomainEvent` possuem persistência própria, isolamento por workspace, idempotência escopada, progresso, cancelamento, retry e provider substituível;
- Visual e Carrossel canônicos usam `useStudioDocument` quando autenticados e preservam o comportamento guest; a flag `VITE_STUDIO_KERNEL_ENABLED=false` restaura o adapter local sem downgrade de dados;
- review agora resolve o post pelo ID da URL e exibe headline/versão do documento Visual persistido;
- o E2E autenticado cria IDs reais, salva/reabre Visual e Carrossel, cria versões, exporta e verifica o handoff de review.

## 10. Estado após fechar o Production Rail do primeiro slice

As lacunas de pin de revisão e export multipágina registradas acima foram fechadas de forma aditiva:

- `StudioReviewRequest` persiste `documentId + documentVersion + snapshot` imutável; decisões atualizam o review e o `Post` na mesma transação e registram `ApprovalEvent`, `FeedbackEvent` e evento de domínio;
- save/autosave altera apenas `revision`; `Criar versão` é uma ação explícita e separada;
- `useStudioDocument` reaproveita o padrão de debounce, trata `409`, offline, reload e aviso de saída com alterações pendentes;
- o Visual exporta PNG e o Carrossel exporta ZIP com PNGs ordenados e `studio.export-manifest.v1`;
- `brandMemoryRef` usa o ID real do `BrandProfile` e sua `brainRevision`; `opportunityRef` preserva ID, `radar-v1.1`, URL e coleta;
- `studio_creation_key` torna a criação por `workspace + post + contentType` idempotente, inclusive quando montagens concorrentes tentam criar o mesmo documento;
- migrations aditivas `0011_studio_production_rail` e `0013_studio_document_idempotency` preservam `0010` e o caminho legado.

Continuam fora deste slice: persistência do Editorial Desk, worker com broker Redis real, renderer audiovisual com paridade total de captions/layers/transitions, provider ASR real/benchmarkado e qualquer provider biométrico efetivamente promovido. O Presenter já possui UI de consentimento, matrícula separada de rosto/voz, fronteira de execução e artefato privado, porém não anuncia geração disponível enquanto o registry estiver vazio. FFmpeg foi adotado somente por ports internos; OpenCut permanece referência seletiva e HyperFrames opt-in.

## 11. Estado após o corte Motion + Image Lab

- Motion avançado agora possui UI contextual real no Visual, restaura grafos por documento, diferencia preview local de sugestão persistida e exige review antes da projeção produtiva;
- Visual/Carrossel novos recebem `MediaTimelineV1`; documentos anteriores recebem a timeline de forma aditiva no próximo save;
- a aba decorativa `Movimento · Depois` foi removida; camada ausente, lock e revisão stale têm estados bloqueados explícitos;
- Image Lab possui rota canônica, Blob autenticado, comparação antes/depois, mask e regiões protegidas editáveis;
- o endpoint de derivação cria novo `LibraryAsset` privado e nunca regrava o source; checksum e lineage são verificados e persistidos;
- o contrato de edição é independente do engine; `PillowImageEditProvider` é o adapter local inicial e pode ser substituído sem alterar UX/domínio;
- a Biblioteca abre Image Lab para assets reais com checksum; dados guest continuam identificados como demonstração local;
- `returnTo` é validado e devolve `derivedAsset` ao editor sem inserção ou publicação automática;
- auditoria executável revalidada em 30/08 reporta 45 rotas registradas, 59 URLs conhecidas, zero órfãs/conflitos e 363 controles com atributo de Action ID; 362/362 executáveis no escopo contratual possuem ID, sem gaps no modo estrito;
- a Biblioteca preserva os dois jobs explícitos do plano: abrir o Image Lab sem alterar o original ou entregar o asset selecionado ao Visual Studio;
- o arquivo canônico do Figma foi sincronizado exclusivamente por MCP e auditado em cinco fases; Chrome/Figma desktop não foram usados para mutações.
