# Clicko Studios — relatório do Kernel e primeiro corte vertical

Data da verificação: 2026-08-25.

## 1. Resultado alcançado

Studios passou a existir como bounded context dentro do monólito modular, sem duplicar autenticação, workspace, Brand Memory, Radar, campanha, aprovação ou publicação. Visual e Carrossel autenticados percorrem a cadeia real:

`sinal → oportunidade radar-v1.1 → campanha → post → CreativeBrief/CreativeDocument → autosave → versão explícita → review imutável → decisão/Post → export/biblioteca`

O caminho guest e as rotas aprovadas permanecem disponíveis. O Video Studio acrescenta um segundo vertical slice real e limitado: UGC de uma fonte, edição frame-exact, proxy/time-map, waveform, render FFmpeg privado e review vinculada. Avatar, clonagem e publicação automática não foram apresentados como entregues.

## 2. Arquitetura anterior e nova fronteira

Antes, a UI canônica mantinha edição local e o backend criativo conhecia apenas um `creative-v1` de canvas único. Agora:

- o sistema principal fornece referências versionadas e continua dono dos domínios compartilhados;
- o Studio Kernel possui contratos Pydantic/OpenAPI, repository adapter, jobs, eventos, review e export;
- `CreativeDocumentV1` é canônico e provider-neutral; `creative-v1` continua como projeção compatível para o renderer existente;
- feature flag e dual-read/dual-write implementam o strangler sem reescrita total.

## 3. Persistência e migrations

- `0010_studio_kernel`: envelope canônico, revision/correlation/actor, jobs e eventos;
- `0011_studio_production_rail`: `StudioReviewRequest` com snapshot imutável;
- `0012_radar_contextual_v2`: metadata de evidência/feedback e avaliações shadow;
- `0013_studio_document_idempotency`: chave única de criação por Post/tipo.
- `0014`–`0017`: consentimento, cápsulas de identidade/voz, activation gate e deletion plan;
- `0018`–`0019`: ingest/proxy, transcripts, captions e edit decisions;
- `0020_identity_delete_exec`: lifecycle/legal hold/tombstone/receipt e executor físico opt-in.
- `0021_media_waveform`: proxy reconform time-map e ponte para waveform derivada;
- `0022_review_render`: binding de review de vídeo a render job, asset e checksum.
- `0023_worker_execution`: attestation versionada do runtime que executou cada job.

A cadeia completa chega a `0023 (head)`. O ciclo limpo `0001 → 0023 → 0022 → 0023` foi exercitado em SQLite efêmero. O teste anterior também validou `0022 → 0020 → 0022` e corrigiu o naming de FKs no batch downgrade do SQLite; bytes removidos por políticas de lifecycle continuam irrecuperáveis por downgrade de schema.

## 4. Funcionalidades preservadas

- shell, navegação, Production Rail, telas canônicas e 57 referências;
- creative canvas/export legado e upcast de documentos antigos;
- Radar ativo `radar-v1.1`, campanhas, aprovação, histórico, feedback e publicação;
- Presenter, integrações e recursos genéricos existentes;
- rollback Visual/Carrossel via `VITE_STUDIO_KERNEL_ENABLED=false`.

## 5. Contratos introduzidos

- `CreativeBriefV1`, `CreativeDocumentV1`, composição multipágina e refs de brand/campaign/post/opportunity/asset;
- `GenerationJobV1`, providers substituíveis e eventos de domínio;
- `VideoRenderRequestV1`, `VideoRenderResultV1`, spec de output e manifest de artefato provider-neutral;
- `MediaTimeMapV1`, `AudioWaveformManifestV1` e specs/resultados versionados de waveform;
- `StudioWorkerRuntimeManifestV1` e `WorkerExecutionContextV1` para boot, placement e proveniência operacional;
- `StudioReviewRequestV1`, decisão de review e `studio.export-manifest.v1`;
- Radar `SourceEvidenceV2`, `SignalClusterV2`, `OpportunityCandidateV2`, dimensions/gates/provider trace e `radar-eval-v1`.

## 6. Comportamento do primeiro slice

- autosave com debounce não cria versão;
- `Salvar` persiste a revisão corrente; `Criar versão` nomeia um snapshot separadamente;
- `409` mostra conflito e permite recarregar explicitamente; alterações offline ficam pendentes;
- review fixa o snapshot da versão solicitada e não muda quando o documento é editado depois;
- decisão de review atualiza o Post e registra auditoria/feedback com a versão decidida;
- Visual exporta PNG; Carrossel exporta ZIP com `manifest.json` e PNGs `01..NN` na ordem do documento;
- criação concorrente do mesmo documento é idempotente no banco.
- histórico canônico lista snapshots por workspace e permite comparação visual de títulos por página;
- restauração é não destrutiva: cria um backup automático do estado atual e restaura o snapshot como uma nova versão auditável;
- conflito otimista também protege a restauração, e acesso cross-tenant ao histórico retorna `404` sem side effect.
- a timeline UGC executa trim por handles e reorder-ripple em frames inteiros, sincronizando vídeo, áudio, captions, overlays e markers;
- o renderer `builtin.ffmpeg-ugc-v1` recompõe a fonte original em 9:16 com H.264/AAC, materializa captions lower-third, rectangle e texto de marca, registra IDs/source bindings/snapshot digest e falha fechado para propriedades fora do recorte;
- review de vídeo falha fechada sem render bem-sucedido da revisão/versão exatas e persiste job, asset e checksum imutáveis.
- QC técnico `ugc-review-v1` reanalisa o artefato final, persiste métricas/checks no job e lineage e bloqueia review em falhas estruturais.
- dispatcher isolado fixa task ID/headers/time limits; bootstep valida manifest/toolchain e jobs/renders preservam a attestation ou declaram honestamente modo embedded.

## 7. Verificação executada

| Verificação | Resultado |
| --- | --- |
| TypeScript | `npm run lint` passou |
| Ruff | `npm run lint:backend` passou |
| Build | `npm run build` passou; 1.738 módulos, CSS 498,11 kB / gzip 80,81 kB e JS 950,49 kB / gzip 254,66 kB; warning conhecido de chunk > 500 kB |
| Backend | 120 coletados; `119 passed, 1 skipped` (smoke HyperFrames opt-in), exit `0` em execução serial isolada |
| E2E completo | `17 passed` em 1,7 min; produto atual, UGC real e isolamento cross-tenant preservados |
| E2E UGC autenticado | MP4 real → probe → proxy/time-map → waveform → captions/cortes → reorder/trim → render → QC → review; output 1080×1920 H.264/AAC, 47 frames, métricas técnicas e isolamento cross-tenant |
| Stitch | 38 + 19 = 57 preservadas |
| Design contract | passou; nenhuma tipografia abaixo de 12 px nas camadas finais |
| Alembic | `0001 → 0023 → 0022 → 0023` passou em banco novo; regressão anterior `0022 → 0020 → 0022` preservada |
| Worker físico local | Redis + API e Celery em containers distintos; a imagem final `sha256:c636c175…` passou boot inválido, probe/health e FFprobe real; a prova anterior de retry `3 → 4` e cancelamento de proxy terminou sem asset vazado; manifest `24015eb5…` |
| Inspeção visual | `artifacts/validation/video-studio-ugc.png` inspecionada em 1440×1000; materiais, preview, saída e timeline sem overflow |

## 8. Open source

Nenhuma aplicação externa foi incorporada. Vinte e dois candidatos foram clonados fora do monorepo para auditoria reproduzível. OpenCut/Classic são referência seletiva de timeline; HyperFrames permanece encapsulado atrás de `VideoRenderProvider`; FFmpeg é infraestrutura base. Remotion, Duix e HeyGem/Caladog foram rejeitados sob a regra atual, e MuseTalk/LatentSync foram rejeitados para produção pela cadeia de pesos. O registro completo permanece em `OPEN_SOURCE_REGISTER.md`.

## 9. Riscos e pendências reais

- o renderer FFmpeg UGC atual é deliberadamente limitado: usa uma fonte e cobre cuts/reorder/áudio, captions lower-third, rectangle e texto. Radius, ênfase, transitions e composição avançada ainda não têm pixel parity;
- Editorial Desk, motion, Presenter provider, UI da cápsula e benchmark biométrico real não pertencem a este corte; consentimento, activation gate e exclusão física governada já existem no domínio;
- o smoke Redis/worker local passou, mas rollout exige PostgreSQL/S3/IAM, broker gerenciado, métricas, reconciliação/dead-letter, quota/autoscaling e imagem promovida com SBOM/assinatura; HyperFrames ainda requer threat model para HTML/assets;
- Radar V2 é somente shadow; faltam dataset julgado e critérios para promoção;
- cohorts não foram implementados e dependem de governança, consentimento e tamanho mínimo.
- `IDENTITY_DELETION_EXECUTION_ENABLED` continua false; produção exige storage/control worker validado, runbook e aprovação de retenção/legal hold.

## 10. Próxima fase recomendada

O próximo corte de infraestrutura deve calibrar o QC e repetir render+QC completo no worker atestado sobre PostgreSQL/S3 local de integração, antes de qualquer rollout; depois amplia radius, ênfase, transitions e múltiplos assets. Em voz, o ADR-012 separou stock/clone e tornou corpus/bundle raw obrigatórios; as fronteiras preflight `speech_cpu`/`speech_gpu` já estão materializadas sem providers, e `studio.capabilities.v1` agora expõe essas lacunas no snapshot autenticado sem autorizar execução. A próxima ação é fechar revisão jurídica, imagens/SBOM e protocolo privado de recrutamento antes de executar Kokoro/Chatterbox/OpenVoice. A VPS Nexus continua inadequada para esses workers e permaneceu intocada. Avatar continua posterior aos gates de licença, consentimento, hardware e benchmark. A sequência detalhada está em `OPEN_SOURCE_INTEGRATION_ROADMAP.md`.

## 11. Auditoria final da meta — 27/08/2026

A meta encerra com o Video Studio UGC real assistido sobre o Studio Kernel e com as fronteiras provider-neutral, de storage, fila, worker, revisão, proveniência e identidade implementadas. Capacidades avançadas não foram maquiadas como prontas: voz clonada, avatar, Replica, modelos multimodais e providers GPU continuam indisponíveis até seus gates próprios. Os manifests finais de `vision_gpu` e `speech_gpu` permanecem com `providers: []`; nenhum peso de Supervision ou PersonaPlex foi ativado e a VPS permaneceu intocada.

| Verificação final | Resultado |
| --- | --- |
| TypeScript e Ruff | `npm run lint` e `npm run lint:backend` passaram |
| Stitch e design contract | 38 + 19 = 57 referências preservadas; contrato visual passou |
| Build | passou com 1.738 módulos; CSS 498,72 kB / gzip 80,97 kB e JS 951,91 kB / gzip 254,97 kB; somente o warning conhecido de chunk > 500 kB |
| Backend completo | 371 coletados; `368 passed, 3 skipped`, sem falhas |
| E2E completo | `18 passed` em 2,7 min, incluindo UGC autenticado, persistência, render, revisão e isolamento |
| Alembic | banco limpo `0001 → 0026 → 0025 → 0026`, sem erro |
| Integridade do diff | `git diff --check` passou; somente avisos de normalização LF/CRLF do Git |
| VPS e deploy | nenhuma conexão, alteração, commit, push ou deploy foi realizado nesta etapa |

Supervision `0.30.1` foi aceito somente como toolkit candidato de visão, atrás de uma camada anticorrupção e com inventário ainda `incomplete`; não é modelo nem mecanismo de compreensão física, e o ByteTrack interno depreciado foi excluído do desenho. PersonaPlex foi preservado apenas como referência arquitetural para protocolo full-duplex e métricas de interrupção/backchannel: seus pesos foram rejeitados pela política open-source-only, além de o modelo publicado ser inglês, pesado e inadequado à VPS e ao caso primário de anúncio PT-BR. As decisões e evidências estão em `research/SUPERVISION_PERSONAPLEX_STRATEGY_2026-08-27.md`, `adr/ADR-019-supervision-vision-toolkit-boundary.md` e `adr/ADR-020-personaplex-duplex-voice-boundary.md`.

O fechamento desta meta significa que a fundação, o primeiro slice real e os mecanismos de promoção segura estão entregues e testados. Os benchmarks com participantes humanos, pesos grandes, GPU externa, revisão jurídica e ativação comercial são fases futuras deliberadamente bloqueadas; não são dívida oculta nem capacidade já prometida ao produto.
