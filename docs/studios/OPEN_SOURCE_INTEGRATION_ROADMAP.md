# Clicko Studios — roadmap de integração estratégica de open source

**Data:** 2026-08-24  
**Status:** execução incremental; não representa adoção automática dos candidatos.  
**Objetivo:** completar os Studios com motores substituíveis, mantendo produto, dados, experiência, governança e documentos sob controle da Clicko.

**Plano de IA/avatar/editor autônomo:** `research/AI_AVATAR_AND_AUTONOMOUS_EDITING_STRATEGY_2026-08-26.md` define a API própria, workers GPU externos, seis apresentadores, benchmark 6 → 24 → 96, contratos de edição e motion, especialistas, premortem e gates.

## 1. Ponto de partida real

O Studio atual é uma fundação funcional, não o produto final. Já existem:

- `CreativeBriefV1`, `CreativeDocumentV1`, jobs, eventos, review e export;
- Visual e Carrossel autenticados com persistência, conflito, versões e retorno à revisão;
- feature flag/compatibilidade com o fluxo anterior;
- contratos provider-neutral e um provider determinístico de teste;
- clones e evidências de quinze candidatos fora do monorepo.

Ainda faltam, entre outros:

- Direção Criativa e Editorial completos sobre dados reais;
- preview e render WYSIWYG unificados;
- timeline, ingestão, transcrição, áudio, captions e render assíncrono de vídeo;
- fábrica conectada a jobs reais, capacidade e custo;
- consentimento de identidade, voz PT-BR e avatar juridicamente aceitável;
- workers isolados e storage de artefatos para mídia pesada.

## 2. Regra arquitetural

```text
Produto Clicko
  → Studio Kernel e CreativeDocument
    → porta de capability versionada
      → adapter Clicko
        → worker isolado
          → motor open source
        ← progresso, logs e artefatos
    ← versão, lineage, review e export
```

O código open source não define rotas, banco, autenticação, UI, documento, fila ou política de consentimento. Ele executa uma capability limitada. O adapter deve poder ser removido sem migrar o domínio Clicko.

Regras obrigatórias:

1. Clone e spike ficam fora do monorepo até a decisão de adoção.
2. Somente adapter pequeno e contrato aprovado entram no produto.
3. `CreativeDocument` nunca é substituído por HTML, JSON de canvas, timeline ou payload do provider.
4. Inputs e outputs usam manifestos versionados, checksums e referências de asset.
5. Todo job possui workspace, correlação, idempotência, progresso, cancelamento, retry e estado terminal.
6. Worker não recebe credenciais de produto além do mínimo necessário por job.
7. HTML, mídia, fontes e modelos são tratados como entrada não confiável.
8. Nenhuma engine entra sem licença de código, pesos, datasets, containers e dependências registrada.
9. Provider novo começa desativado e com fallback/rollback.
10. Publicação e identidade sintética continuam sujeitas a revisão humana.

## 3. Mapa de capabilities e motores

| Capability Clicko | Candidato | Uso estratégico | Estado/gate |
| --- | --- | --- | --- |
| `VisualCanvasProvider` | engine atual; Fabric.js ou Konva como comparação | edição e projeção visual | preservar engine atual; trocar somente após benchmark de paridade. |
| `VideoRenderProvider` | FFmpeg limitado + HyperFrames opt-in | recomposição UGC do original e composição HTML avançada | `builtin.ffmpeg-ugc-v1` ativo para uma fonte, cuts/reorder e áudio; HyperFrames continua encapsulado. Worker atestado local passou; faltam paridade audiovisual, build aprovada, rollout externo e benchmark multimídia. |
| `MediaProxyProvider` | FFmpeg | proxy editável e reconform para o original | adapter, job, lineage, reprobe e `MediaTimeMapV1` com checksum/offset/drift concluídos; worker atestado local e cancelamento sem leak passaram; build aprovada e rollout externo pendentes. |
| `TranscriptionProvider` | WhisperX | palavras, timestamps e diarização | PT-BR, modelos auxiliares, GPU/CPU, custo e licenças ainda precisam de benchmark. |
| `AudioTimelineProvider` | FFmpeg + UI Clicko; wavesurfer.js como benchmark | waveform, regiões e interação | manifesto determinístico min/max/RMS persistido e projetado na timeline; wavesurfer não é dependência obrigatória e nunca será fonte canônica. |
| `TimelineInteractionProvider` | reducer Clicko; React Timeline Editor como benchmark | drag, resize, snapping e zoom | primeira slice nativa implementa handles e reorder-ripple em frames racionais; ainda faltam escala, snapping e undo/redo. |
| `TimelineInteractionProvider` | OpenCut Classic; acompanhar OpenCut rewrite | snapping, commands, keyframes, masks e compositor como módulos de referência | Classic está arquivado; rewrite ainda não entrega Editor API/headless. Benchmark seletivo, nunca fork. |
| `StockVoiceProvider` | Kokoro 82M | preview/TTS stock pt-BR e TTS-base | código/pesos permissivos; política congelada, benchmark de qualidade/custo e imagem/SBOM pendentes. |
| `VoiceCloneProvider` | Chatterbox V3/pt-BR; Kokoro + OpenVoice V2 | clone zero-shot ou conversão de timbre | código/pesos principais permissivos; consentimento, deleção e benchmark privado ainda bloqueiam ativação. |
| `LipSyncProvider` | MuseTalk | dublagem sobre vídeo/performance existente | pesos OpenRAIL-M + SyncNet OpenRAIL++; rejeitado para produção, somente sintético/evidência. |
| `LipSyncProvider` | LatentSync 1.6 | comparador de lip-sync por difusão | código Apache, mas pesos OpenRAIL++ e InsightFace não comercial; rejeitado para produção. |
| `MotionProvider` | LivePortrait sem InsightFace | pose/expressão/retarget de retrato | core MIT; selecionar detector permissivo e provar paridade antes de dados reais. |
| `AvatarProvider` | nenhum aprovado | orquestra motion + lip-sync + voz + cenário | HeyGem/Duix rejeitados e nenhuma cadeia facial passou licença/benchmark; composição continua provider-neutral. |
| `AvatarProvider` | Ditto | talking head controlável e potencialmente de baixa latência | Apache no repo, mas checkpoints oficiais incluem InsightFace; somente após substituição e rebenchmark. |
| `AvatarProvider` | EchoMimicV3 Flash | áudio → retrato/meio-corpo/corpo | candidato principal de benchmark em GPU externa; cadeia RetinaFace/Wav2Vec2/CLIP/Wan e pesos ainda `review_required`. |
| `GenerativeVideoProvider` | Wan2.2 Animate | character animation/replacement e cenas avançadas | Apache no upstream; requisitos 14B/custo deixam fora do MVP. |
| `PlanningCopyProvider` | Qwen3 4B + 30B-A3B Instruct/Thinking; Kimi K2.5 como teto | brief, copy, storyboard, revisão e propostas estruturadas | contrato/adapter testados; preflight `llm_gpu` Linux AMD64 construído como não-root e registry vazio; corpus sintético 60/60 preparado, ainda sem inferência. Imagem funcional/run externo pendentes. Kimi somente após Qwen. |
| `VideoUnderstandingProvider` | Qwen3-VL 4B/8B + analyzers determinísticos | `MediaIndexV1`, storyboard, selects e QC advisory | Qwen primeiro em GPU externa; API de vídeo apenas comparador posterior; VLM nunca é árbitro único. |
| toolkit interno de observação | Supervision 0.30.1 | normalizar outputs, overlays, zones, datasets e métricas antes de `RealityContributionV1` | inventory `incomplete`; spike sintético primeiro, sem `sv.ByteTrack`, persistência upstream ou provider anunciado. |
| `MotionGraphicsProvider` | HyperFrames + Motion Canvas | motion determinístico e cenas vetoriais | `MotionGraphV1` provider-neutral e projeções determinísticas entregues; HyperFrames principal e Motion Canvas especializado ainda precisam de adapters de execução/benchmark. Ambos permanecem fora do domínio canônico. |
| `EditorialInterchangeProvider` | OpenTimelineIO | import/export de cuts e tracks | não armazena mídia e não substitui `CreativeDocument`. |
| `SceneDetectionProvider` | PySceneDetect | cuts/fades e índices temporais | analyzer BSD; imagem/FFmpeg auditados separadamente. |
| `ImageSegmentationProvider` | SAM 2 | máscaras e tracking | posterior ao vídeo básico; checkpoints/datasets precisam de registro. |
| `VisualGeometryProvider` | Depth Anything V2 Small + baseline própria | profundidade relativa, câmera/orientação e oclusão | somente Small Apache; estimador de up/gravity cues próprio; variantes NC bloqueadas. |
| `ObjectTrackingProvider` | TAPIR + RAFT | tracks/pontos e movimento persistente | candidatos PGV-1; pin de checkpoint e manifest antes de mídia privada. |
| `PhysicalSceneUnderstandingProvider` | ensemble Clicko | entidades, relações, eventos e hipóteses em `RealityModelV1` | construir contrato/fixtures antes do provider; nenhuma saída sem confiança/lineage. |
| `VideoWorldModelProvider` | V-JEPA 2 | representação/predição latente e surpresa temporal | somente benchmark PGV-3; não arbitra nem explica sozinho. |
| `PhysicalPlausibilityProvider` | ensemble + regras calibradas | localizar violações segundo intenção do shot | PGV-4 advisory; abstenção e revisão humana obrigatórias. |
| `RealityCalibrationProvider` | métricas/reliability Clicko | ECE/Brier, threshold, false block e drift | policy/corpus congelados; benchmark público nunca é gate único. |
| `EditorialDocumentProvider` | Lexical | interação de rich text | condicionado; JSON Lexical não será canônico. |
| `ResearchProvider` | Vane | pesquisa e fontes | adapter opcional; não substitui scoring, evidências ou aprendizado do Radar. |
| `DuplexConversationProvider` futuro | nenhuma implementação aprovada; PersonaPlex somente referência | conversa de voz ao vivo, interrupção e backchannel | fora do anúncio PT-BR; checkpoint NVIDIA rejeitado pela política open-source-only e servidor upstream não tenant-safe. |
| challenger duplex PT-BR | Qwen3-Omni-30B-A3B-Instruct | áudio português streaming; código Apache-2.0, licença dos pesos em revisão | research-qualified somente; model card `license: other` sem LICENSE, 70,5 GB, PT-BR dialetal e full-duplex/barge-in ainda não provados; GPU externa, nunca VPS CPU. |
| transporte conversacional opcional | Pipecat | filas, turn detection e cancellation atrás do port Clicko | framework BSD-2-Clause, não modelo; providers têm licenças próprias e não herdam aprovação. |

Remotion, HeyGem, Duix, MuseTalk e LatentSync permanecem fora do produto enquanto a regra for “somente open source”. O vídeo `hyperframes-launch-video` é referência de complexidade, não fonte de código/mídia reutilizável.

## 4. Caminho “rosto → anúncio”

O resultado desejado exige uma cadeia governada, não um único repositório:

```text
Consentimento e finalidade
  → captura de rosto/voz ou mídia UGC real
  → controle de qualidade
  → CreativeBrief e roteiro
  → edição de fala/voz
  → take real ou AvatarProvider aprovado
  → composição, captions, marca e CTA
  → render job
  → revisão humana
  → exportação/publicação
```

Existem dois caminhos de produto distintos:

- **UGC assistido com pessoa real:** organiza captura, cortes, roteiro, captions, marca e variações. Pode avançar antes de clonagem de identidade.
- **Apresentador sintético:** usa voz/rosto derivados e depende de consentimento verificável, revogação, exclusão, licença e benchmark de qualidade.

O primeiro caminho é a prioridade comercial e técnica porque entrega valor com menor risco. O segundo reutiliza a mesma fábrica quando seus gates forem satisfeitos.

## 5. Prova HyperFrames concluída

O spike externo em `C:\Users\edugu\Downloads\clicko-oss-evaluation\spikes\hyperframes-minimal` agora:

- recebe uma fixture válida `studio.creative-document.v1`;
- rejeita schema desconhecido, conteúdo não audiovisual, múltiplas páginas e dimensões fora do corte atual;
- produz uma projeção descartável para o renderer;
- usa somente composição e mídia próprias;
- passa `hyperframes lint` com zero erros e zero warnings;
- renderiza 1080×1920, 30 fps e 60 frames;
- gerou duas saídas de 843.713 bytes byte a byte idênticas;
- SHA-256: `3448032BE22E89F5618CF30FE83655365C16D78F143B73CB56857D1CE08DE4B7`;
- completou os renders observados em 22,8 s e 14,5 s no ambiente local.

Essa prova autoriza continuar o spike; ainda não autoriza incorporar HyperFrames ao produto.

## 6. Capacidade da VPS existente

Levantamento somente leitura realizado em 2026-08-24:

- Ubuntu/Oracle Linux kernel, arquitetura x86_64;
- 2 vCPUs AMD EPYC;
- 956 MiB de RAM, cerca de 376 MiB disponíveis no momento da inspeção;
- 2 GiB de swap, já em uso;
- 45 GiB de disco, 37 GiB disponíveis;
- sem GPU, Node, npm ou FFmpeg instalados;
- Docker ativo;
- seis contêineres Nexus ativos, com API, PostgreSQL e Redis saudáveis.

**Decisão:** não executar Chrome/HyperFrames, FFmpeg pesado, WhisperX, OpenVoice ou avatar nessa VPS. Instalar runtimes ou iniciar workers nela criaria contenção e contrariaria a preservação dos serviços existentes.

Uso permitido dessa VPS nesta fase:

- hospedar o produto/controle já existente;
- registrar jobs e estado no stack existente quando houver integração autorizada;
- comunicar-se com um worker externo dedicado;
- receber apenas checksums, manifestos e referências de artefato, não processamento pesado.

Worker recomendado:

- CPU render: instância isolada com pelo menos 4 vCPUs e 8 GiB de RAM;
- transcrição/voz/avatar: worker GPU separado após benchmark, com VRAM definida pelo modelo escolhido;
- storage de objetos separado do filesystem dos contêineres Nexus.

Fronteiras preflight agora versionadas (sem providers anunciados):

- `workers/speech-cpu/worker.manifest.json` reserva `studio.speech.cpu` para `stock_voice`;
- `workers/speech-gpu/worker.manifest.json` reserva `studio.gpu.speech` para `transcription`/`voice_clone`;
- os digests dos manifests são `36f45dd0...b4837` e `561cda8a...c907`; sizing, imagem, SBOM, provenance e benchmark real continuam gates.

## 7. Sequência de implementação

### Slice OSS-1 — contrato de render

1. Transformar a projeção local em adapter de `VideoRenderProvider`.
2. Definir `studio.video-render-request.v1` e `studio.video-render-result.v1`.
3. Normalizar progresso do HyperFrames/FFmpeg para 0–100.
4. Provar cancelamento real de processo e ausência de output publicável após cancelamento.
5. Gerar manifest com codec, dimensões, duração, fps, checksum e lineage.

Gate: dois providers fakes e o adapter HyperFrames produzem o mesmo contrato de resultado sem mudar `CreativeDocument`.

### Slice OSS-2 — worker de mídia isolado

1. Empacotar Node, Chrome, fontes e FFmpeg fixados.
2. Gerar SBOM e registrar `ffmpeg -buildconf`.
3. Executar sem egress e sem fontes remotas.
4. Limitar CPU, RAM, tempo, disco temporário e tamanho de input.
5. Implementar limpeza, retenção e isolamento por workspace/job.

Gate: benchmark em worker dedicado, nunca na VPS Nexus atual.

Estado em 24/08/2026: Dockerfile/lock, imagem AMD64, SBOM CycloneDX e smoke sem rede/read-only/non-root concluídos localmente. O gate permanece aberto até a mesma imagem ser produzida pela CI com provenance, pacotes Debian/FFmpeg aprovados e benchmark no worker externo dedicado.

### Slice OSS-3 — vídeo UGC assistido

1. Ingestão e FFprobe.
2. Proxy e asset lineage.
3. Player, media bin e timeline mínima.
   - comparar React Timeline Editor com módulos isoláveis do OpenCut Classic;
   - acompanhar o OpenCut rewrite sem depender de capabilities que ainda são roadmap.
4. Split, trim, reorder, captions editáveis e brand overlay.
5. Render assíncrono com progresso/cancel/retry.
6. Review da versão exata e export.

Gate: um usuário produz vídeo vertical real sem perder a timeline original.

Estado em 26/08/2026: o E2E autenticado atravessa upload privado → FFprobe → proxy + time-map → waveform → documento → captions → decisão de corte → reorder/trim direto → render FFmpeg privado → QC técnico → review ligada a job/asset/checksum. O output é reprobed em 1080×1920, H.264/AAC e 47 frames, crops RGB provam caption/faixa/CTA, e `ugc-review-v1` mede sync, black frames, loudness e silêncio; outro tenant recebe `404` no job e artefato. Um smoke separado prova Redis + worker físico local atestado para probe/retry/cancel; OpenCut foi somente referência ergonômica. O rail automático de transcrição agora aceita um adapter aprovado, valida ingest/asset/checksum e persiste transcript `draft` versionado; WhisperX real e seu benchmark continuam pendentes. Permanecem abertos calibração do QC, thumbnails, múltiplos assets, snapping/undo, volume/fades, radius/ênfase/transitions, render+QC completo no worker, rollout PostgreSQL/S3/broker e codec/build aprovados.

### Slice OSS-3B — inteligência de realidade e Physical QC

1. **PGV-0 — linguagem e contratos (concluído):** `RealityModelV1`, contributions, constraints, `PhysicalPlausibilityEvaluationV1`, ports, jobs `vision_gpu`, taxonomia, runtime policy, três benchmark policies, digests e fixtures sintéticas foram implementados/testados.
2. **PGV-1 — percepção permissiva (baseline OpenCV em avaliação):** orquestração/bindings provider-neutral, adapters fakes, manifest GPU, artifact inventory, definição de imagem/lock, corpus congelado com 11 casos/6 métricas, runner recomputável e providers clássicos de horizonte/câmera/tracks/assembly foram entregues. A execução real no venv externo pinado (Python 3.11.9/OpenCV 4.13.0/NumPy 2.2.6) passou 11/11 casos e 6/6 métricas; o candidate manifest continua desativado e o gate de ativação é `incomplete` por status `evaluation`. Ainda faltam revisão dos wheels e RAFT/CUDA, build Linux/SBOM/assinatura/provenance, persistência/cache, worker externo e providers TAPIR, Depth Anything V2 Small, RAFT condicionado, SAM 2 auditado e estimador próprio de orientation/gravity cues.
3. **PGV-2 — scene/event graph:** persistência, suporte, contato, contenção, oclusão, colisão e transições de estado com evidência temporal.
4. **PGV-3 — predição:** comparar V-JEPA 2 com a baseline, pares mínimos e holdout Clicko; manter somente se adicionar qualidade calibrada por custo.
5. **PGV-4 — produto advisory:** Reality Lane, inspector, tracks/overlays corrigíveis, abstenção e revisão ligada ao render/checksum exatos.
6. **PGV-5/6 — planejamento e gate:** usar constraints no shot plan/candidate ranking; só depois considerar bloqueio de autoaprovação de vídeo sintético realista.

OpenCut entra apenas na ergonomia da Reality Lane: markers/bookmarks, commands/undo, snapping, keyframes/masks, overlays e hit testing selecionados do Classic MIT. `RealityLaneProjectionV1` já projeta markers/overlays editáveis e abstentions do `RealityModelV1`; o documento, store, auth, banco e compositor OpenCut não entram por padrão; o rewrite continua monitorado, sem dependência de roadmap.

Gate: policy/corpus/thresholds congelados antes do run; recall crítico ≥ 0,90, precisão ≥ 0,80, false block real ≤ 1%, temporal IoU ≥ 0,70, ECE ≤ 0,10 e paired accuracy ≥ 0,75 como metas preliminares; toda ocorrência inclui intervalo, entidades, evidência, confiança e incerteza. PGV-4 permanece advisory. A VPS atual continua somente control plane.

Estado em 25/08/2026: PGV-0 está entregue em `backend/app/domain/studios/reality.py` e `benchmarks/studios/reality/`. V-JEPA 2, TAPNet/TAPIR, RAFT, Depth Anything V2 e OpenCV foram clonados/pinados fora do produto. O artifact inventory separa código, pesos e container: TAPIR e Depth Anything V2 Small foram aprovados para o gate; RAFT weights e PyTorch/CUDA permanecem `review_required`.

Preflight PGV-1 em 25/08/2026: `RealityAnalysisOrchestrator` e `PhysicalQualityOrchestrator` validam checksum, contributions, lineage/evidence, request/result bindings, progresso e cancelamento. O manifest `vision_gpu` (`fbe3c7a55ba2d98a7a12a4ae37e8b97b46d2282bcb89cfe5a657d6b60ac0efb1`) exige GPU NVIDIA ≥ 22.528 MiB e CC ≥ 8.0, mas mantém providers vazios. O inventário (`d1935d35...15dea0c`) e o lock (`1a40b7d9...97fe0`) são verificados durante o build preflight; `ProviderPromotionEvidenceV1` agora fecha o binding OCI/SBOM/provenance/benchmark/legal/attestation antes de qualquer anúncio. ADR-014/015 registram os gates restantes; não houve execução de pesos nem acesso à VPS.

Regressão após o gate de supply chain: 151 testes passaram, 1 skip esperado permaneceu e Ruff ficou limpo. O Dockerfile foi preparado, mas a imagem ainda não foi construída/SBOMada por ausência de Docker daemon local; o workflow manual `.github/workflows/studios-vision-preflight.yml` agora deixa o build Linux/AMD64 reproduzível em CI, verifica os pins fora do Docker antes do BuildKit e emite apenas OCI/SBOM/provenance, sem push/deploy/provider. Isso não autoriza usar a VPS como substituto.

Baseline clássica em 25/08/2026: OpenCV 4.13.0 real processou o corpus procedural congelado de 11 casos em MP4s efêmeros e produziu 1,0 em motion, horizonte, gravity-presence, tracks, status e abstention compliance. O primeiro run falhou quatro casos por defeitos da fixture; a correção foi registrada antes do run final e não relaxou thresholds. O relatório/gate versionado está em `benchmarks/studios/reality/opencv-baseline-run-2026-08-25.v1.json`; wheel/NumPy/lock/provider manifest foram congelados, mas o candidate está `evaluation`, o worker anuncia zero providers e o Dockerfile preflight não instala os wheels. ADR-016 detalha o resultado, o gate de ativação e o boundary com a Reality Lane/OpenCut.

Lane Supervision em 27/08/2026: o release estável 0.30.1 foi fixado e inspecionado. O inventário `supervision-toolkit-artifacts-2026-08-27` aprova somente a fonte MIT e mantém lock/container `incomplete`. `SV-1` converterá resultados sintéticos para `RealityContributionV1`, produzirá overlays ligados a `evidence_id` e conferirá métricas; `SV-2` medirá fidelidade, determinismo, zones, RAM/throughput e robustez. Objetos `Detections` nunca são persistidos, `sv.ByteTrack` não entra por estar depreciado e o manifest `vision_gpu` continua vazio.

Execução aberta em 27/08/2026: `SUPERVISION_DUPLEX_EXECUTION_PLAN_2026-08-27.md` transforma a pesquisa em nove gates operacionais. A ordem é freeze → spike Supervision sintético → benchmark OpenCV → supply chain → shadow/promoção; a lane full-duplex começa por contratos/fakes e pesquisa de alternativas realmente abertas antes de qualquer peso. PersonaPlex continua referência arquitetural rejeitada para runtime, e ausência de alternativa não autoriza sua adoção automática.

Execução em 28/08/2026: `DuplexConversationProvider` e a sessão assíncrona foram formalizados sem dependência upstream; o corpus/harness PT-BR congelou dez cenários e produziu apenas uma calibração sintética não promotável. O inventário Qwen3-Omni pinou código/modelo e os 15 shards por hash sem baixar bytes, mas corrigiu sua licença para `review_required`: o model card usa `license: other`, apenas nomeia Apache-2.0 e não traz LICENSE. PersonaPlex, Fish Speech e modelos LiveKit com licença customizada permanecem rejeitados; Moshi permanece inglês-only; Pipecat é somente opção de transporte. Hoje nenhuma alternativa satisfaz simultaneamente licença confirmada, PT-BR e full-duplex provado; todos os manifests continuam vazios.

Resultado SV-1/SV-2 em 28/08/2026: adapter, overlays por `evidence_id`, fixtures e smoke real 0.30.1 passaram; o benchmark congelado de oito casos atingiu 100% de fidelidade/determinismo/zones/box parity/rejeição e coincidência exata de precision/recall/F1 com a referência. O lock Linux/AMD64 de 29 wheels e o SBOM SPDX foram materializados. A ativação continua `incomplete`: nove wheels nativos aguardam notices/revisão e ainda não há OCI, image SBOM, provenance, assinatura, attestation ou shadow mode. O manifest continua vazio.

Regressão após o hardening eSpeak e o rail de transcrição em 26/08/2026: 246 casos backend
coletados, `243 passed, 3 skipped`; as duas integrações OpenCV ausentes do Python
padrão passaram no venv externo pinado (OpenCV 4.13.0/NumPy 2.2.6), e o terceiro
skip continua sendo o smoke HyperFrames opt-in. Ruff completo ficou limpo. O CLI de
promoção falha fechado sem evidência externa válida e mapeia candidatos
`stock_voice`/`voice_clone` aos workers `speech_cpu`/`speech_gpu`; os manifests
preflight continuam sem providers. A cobertura inclui corpus sintético,
preflight/attestations OCI, port e executor tipados, armazenamento privado,
readiness ligado ao anúncio real, adapter Kokoro offline/allowlisted/cancelável,
runner recomputável de 64 casos, inventário incompleto, lock Linux, model manifest,
replacement eSpeak byte-manifested e fail-closed, três pacotes cegos/192 ratings,
cleanup 64/64 e replay idempotente do snapshot.

Em 26/08/2026, a jornada E2E específica do Video Studio também passou os dois
casos Chromium: demo sem persistência e fluxo autenticado com MP4 real, FFprobe,
proxy, waveform, captions/edit decisions, trim/reorder, render FFmpeg privado,
QC técnico, review versionada e isolamento `404` entre workspaces. O typecheck e o
build frontend/servidor passaram; isso comprova o vertical slice de vídeo, mas não
promove o candidato de voz nem substitui a execução Linux/AMD64 externa.
Na mesma execução, a suíte E2E completa passou `18/18`; o teste de acabamento foi
alinhado ao estado governado `DEMONSTRAÇÃO LOCAL` e um caso autenticado novo prova
que readiness sem provider mantém geração/captura/publicação bloqueadas, mantendo
explícito que exemplos de identidade não são produção aprovada nem publicáveis.
Após separar o gate `publish.synthetic`, os dois cenários Presenter foram revalidados
em Chromium (`2 passed`): o fluxo demonstrativo continua não publicável e o fluxo
autenticado sem provider mantém geração/captura/publicação bloqueadas.
O boundary de clonagem de voz também foi endurecido: `voice_clone` agora exige
`voiceVersionId`, consentimento ativo com sujeito/escopo `voice.clone` compatíveis,
perfil `cloned` e identidade não destacada antes de criar qualquer job. Sem esses
vínculos a API responde `422` e não há side effect nem chamada de provider; a suíte serial completa passou `243/246`
com três skips opt-in esperados.

Projeção de prontidão em 25/08/2026: `GET /api/v1/studios/v1/capabilities` agora retorna `studio.capabilities.v1` por workspace, com status `unavailable | blocked | review | ready`, contagens de provider/modelo, consentimento, benchmark, licença, razões e flags `providerReady`/`captureReady`. A leitura é somente consulta, deriva dos registros globais de provider/modelo e dos perfis/versões/consents do tenant, e está ligada ao snapshot autenticado do frontend. A projeção cobre Presenter, Avatar, voz stock, clonagem e `transcription`; esta última não exige consentimento biométrico, mas permanece `unavailable` enquanto o registry estiver vazio. Com os manifests speech e vision ainda em `providers: []`, Presenter/voz/avatar/transcrição permanecem fechados; nenhum provider foi cadastrado por esta mudança.
`publicationAllowed` permanece separado de geração/captura e só pode ser verdadeiro
quando existe consentimento ativo com escopo `publish.synthetic`; um preview privado
ou uma captura aprovada não autoriza publicação automaticamente.

O registry de candidatos também ganhou API governada (`/studios/v1/providers` e `/studios/v1/models`) com owner/admin, validação de manifesto e eventos de domínio para registro/aprovação. Isso materializa a trilha de governança sem confundir aprovação documental com anúncio operacional: o worker continua com `providers: []` até o gate de benchmark/promoção.

O job `transcription` também foi separado do caminho genérico: `TranscriptionRequestV1`
e `TranscriptionProvider` formam o port para WhisperX/ASR futuro, com registry próprio
e admission por benchmark/modelo/worker. Enquanto o registry está vazio, a API retorna
`transcription_provider_not_approved` e o executor não lê mídia nem produz transcript;
o transcript manual permanece explícito, sem simular uma integração automática. Quando
um adapter aprovado é injetado em teste, o rail exige ingest/asset/SHA-256 do mesmo workspace,
verifica o resultado e timestamps, registra ator/proveniência/métricas e cria um transcript
`draft` idempotente. Isso prova a integração, não a qualidade ou promoção do WhisperX.

### Slice OSS-4 — transcrição PT-BR

1. Dataset consentido com três perfis de áudio.
2. WhisperX versus baseline.
3. Medir WER, nomes de marca, timestamps, pontuação, latência, RAM/VRAM e custo.
4. Normalizar palavras/speakers no contrato Clicko.

Gate: qualidade definida pelo produto e licença de todos os modelos registrada.

Estado em 25/08/2026: as filas/capabilities `speech_cpu` e `speech_gpu` já têm
manifests preflight isolados e testados, ambos com `providers: []`. Isso fecha a
fronteira de execução sem ativar Kokoro, WhisperX, Chatterbox ou OpenVoice. Ainda
faltam executar e revisar o lock Linux/AMD64, resolver pesos e imagem candidata,
licença transitiva, execução real e gate de qualidade/custo. A projeção read-only
`studio.capabilities.v1` foi ligada ao snapshot autenticado para que a UI consuma
essas lacunas como estado explícito; ela não cria registros nem autoriza execução.

O `speech_cpu` já possui um preflight de imagem Linux/AMD64 (`Dockerfile.preflight`,
verificador de digests e workflow manual) que emite OCI/SBOM/provenance sem push e
sem provider. Ele valida apenas a policy stock sintética e o contrato de dependências;
isso reduz o risco de infraestrutura, mas não substitui o lock candidato revisado,
a revisão jurídica nem a execução do benchmark.

O Kernel também possui agora um executor `stock_voice`/`voice_clone` provider-neutral:
a admissão no control plane exige provider/modelo aprovados, `benchmarkStatus=passed`
e `workerAdvertised=true`; o worker exige adapter presente em `SPEECH_PROVIDERS`.
Uma fixture de teste gera WAV real, grava em object storage escopado pelo workspace,
verifica checksum e provenance, persiste `studio.speech-synthesis-job-result.v1` e
remove qualquer saída inválida. O registry de produção segue vazio, portanto essa
prova de arquitetura não é promoção nem benchmark de Kokoro.
O readiness autenticado usa o mesmo gate: benchmark aprovado sem
`workerAdvertised=true` permanece em `review` e nunca expõe `providerReady=true`.

Preparação segura em 25/08/2026: o gerador `backend/scripts/generate_synthetic_stock_corpus.py`
produziu, fora do Git, 64 casos PT-BR distribuídos nos oito cenários da policy stock.
O manifest contém somente digests e flags sintéticas; o scriptbook privado contém os
textos determinísticos e valida o digest de cada caso e do corpus. A suíte não possui
sujeitos, áudio, assets, consentimentos ou referências biométricas e passou o teste de
determinismo. Isso habilita a calibração inicial de latência/RTF do Kokoro em uma
imagem isolada, mas não é evidência de qualidade, licença ou autorização de provider.
ADR-017 fixa o gate de execução: imagem Linux/AMD64, SBOM/provenance/notices, métricas
recomputáveis, revisão MOS cega e cleanup antes de qualquer promoção.

O candidato Kokoro agora possui adapter real, mas não registrado, atrás do port
`SpeechSynthesisProvider`. Ele falha fechado fora de cache offline/revisão/digest
pinados, aceita somente as três vozes brasileiras documentadas, faz chunking
determinístico, produz WAV 24 kHz com provenance e custo de CPU e limpa saída parcial
em cancelamento. O runner provider-neutral executa os 64 scripts e emite evidência
bruta por caso; ele deliberadamente não fabrica MOS, inteligibilidade, licença nem
cleanup, portanto não consegue autoaprovar o candidato.

O inventário versionado `kokoro-82m-stock.artifacts.json` permanece `incomplete` e
fail-closed. Fora do Git, os cinco arquivos de modelo/vozes foram ligados ao manifesto
`4c738811...9af9`, o replacement eSpeak a `9af35120...e373` e o lock Clicko CPU-only
a `a0d7a19a...2214`; o verificador agora rejeita PyTorch PyPI genérico, Triton e
qualquer pacote NVIDIA. A imagem candidata local tem digest
`sha256:043d7a31...d917b`, UID 10001 e labels `evaluation/providers=none`, mas não foi
promovida ao inventário versionado porque SBOM estritamente local, provenance e
revisão jurídica ainda faltam. O worker principal e `SPEECH_PROVIDERS` continuam
vazios.

O lock separado revelou que `espeakng-loader==0.2.4` embute eSpeak 1.52.0 do commit
`4870adfa...`, enquanto a policy exige `7d426728...`; seu wheel Linux também omite
licença. O inventário agora registra esse wheel por SHA-256 e mantém revisão jurídica.
O contrato `studio.espeak-runtime-assets.v1`, a receita multi-stage e o workflow manual
exportam um replacement sem entrypoint, com biblioteca/dados, `COPYING`, source tar,
builder/compilador/CMake/flags e checksum de todos os arquivos. O runner só aceita o
digest desse bundle ligado ao componente da policy. A receita foi executada localmente:
391 arquivos Linux/AMD64 foram verificados, o eSpeak foi substituído dentro da imagem
e a fonemização PT-BR passou. Isso fecha o gate técnico do replacement, não as
obrigações GPL de corresponding source/notices.

Em 26/08/2026, o lifecycle privado também foi fechado: o sink conserva 64 WAVs e
provenance até a revisão, gera três pacotes cegos independentes, ingere 192 ratings
ligados a script/output, e somente então produz cleanup por caso, recibo e snapshot
final. Os quatro CLIs agora fazem bootstrap próprio do backend e funcionam diretamente
no checkout; o teste integrado cobre geração → revisão → retenção → cleanup 64/64 →
replay idempotente. Snapshots existentes só são reutilizados se o JSON for idêntico;
qualquer conteúdo divergente é recusado sem overwrite. Isso deixa o pacote pronto para
uma imagem externa, sem registrar Kokoro e sem tocar a VPS.

Execução local em 26/08/2026: Docker Linux/AMD64 construiu a candidata CPU-only e o
runner processou 64/64 casos com `pf_dora`, sem falha de job. O resultado falhou o SLA
de preview (`p95 RTF 2,338 > 1,0`), embora RAM e custo tenham passado. Três pacotes
cegos de 64 atribuições foram preparados fora do Git. O plugin SBOM legado produziu
arquivo vazio e o Docker Scout foi interrompido ao iniciar indexing para evitar
publicação remota; SBOM/provenance/assinatura continuam gates. Uma auditoria também
separou `cleanup_mechanism_available` de `cleanup_verified`; execução de cleanup só
pode virar true após review e recibo por caso.

### Slice OSS-5 — identidade e presenter

1. ~~Implementar `ConsentGrant`, revogação lógica, bloqueio por expiração/revogação e exclusão física antes de provider real.~~ Contratos, activation gate, deletion plan, legal hold, shared-reference check, tombstones e executor idempotente foram entregues em `0020`; a flag destrutiva continua desligada até validar storage/control worker de produção.
2. ~~Definir corpus, candidatos, controles, evidências e thresholds antes dos resultados.~~ Políticas `studio.benchmark-policy.v1` congeladas em `benchmarks/studios/identity/` e avaliador provider-neutral testado.
3. Aprovar a política por produto/segurança/jurídico, provisionar worker GPU externo e materializar o corpus privado consentido.
4. Benchmark Chatterbox V3/pt-BR, Kokoro stock e Kokoro + OpenVoice; não promover ausências a zero/pass.
5. Selecionar detector permissivo para LivePortrait e pesquisar um lip-sync cuja cadeia inteira seja open source; MuseTalk/LatentSync permanecem evidence-only.
6. Executar somente com assets privados, no-egress, revisão cega, lineage, cleanup e recibo de deleção.

Gate: jurídico, qualidade, isolamento e revisão humana aprovados.

### Slice OSS-6 — voz conversacional full-duplex (horizonte, não MVP)

1. Validar primeiro se existe job-to-be-done de conversa ao vivo; não misturar com narração/render de anúncio.
2. Definir `DuplexConversationProvider` com sequence, monotonic timestamps, interrupt, close e retention receipt.
3. Pesquisar alternativa permissiva com PT-BR antes de qualquer modelo custom-licensed.
4. PersonaPlex permanece referência de role/voice prompting e métricas. Seu checkpoint está rejeitado; nenhum aceite, download ou provider.
5. Se a política mudar, exigir sidecar novo: IDs opacos, paths confinados, formats seguros, logs redigidos, no runtime download, concorrência isolada e GPU externa.

Gate: necessidade de produto, licença/política, PT-BR, threat model biométrico, custo e benchmark cego. A VPS nunca executa essa lane.

## 8. Critério de adoção

Um candidato só muda de “spike” para “adotar” quando comprovar:

- licença comercial compatível em todas as camadas;
- qualidade superior ou custo menor que a alternativa atual;
- contrato provider-neutral e teste de substituição;
- isolamento multi-tenant;
- progresso, cancelamento, retry e observabilidade;
- custo por artefato e capacidade previsíveis;
- rollback sem perda de documentos;
- UI Clicko completa e honesta para a capability.

O sucesso não é “o repositório rodou”. É o usuário concluir uma etapa real do Studio com qualidade, controle e continuidade.
