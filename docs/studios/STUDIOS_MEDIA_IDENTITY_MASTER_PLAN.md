# Clicko Studios — plano mestre de conteúdo, vídeo e identidade

**Versão:** 1.0  
**Data:** 2026-08-24  
**Status:** plano executável; adoções continuam condicionadas aos gates.  
**Documento normativo superior:** `docs/CLICKO_STUDIOS_STRATEGY.md`.  
**Pesquisa e evidências:** `docs/studios/research/report-source.md` e `docs/studios/research/CLAIM_SOURCE_LEDGER.md`.

**Decisão de IA, seis avatares e edição autônoma (26/08/2026):** `docs/studios/research/AI_AVATAR_AND_AUTONOMOUS_EDITING_STRATEGY_2026-08-26.md`.

## 1. Decisão executiva

O produto não será “um gerador de vídeos” nem um fork de CapCut/HeyGem/OpenCut. Ele será uma fábrica governada que transforma contexto de marca e materiais autorizados em peças editáveis, revisáveis e mensuráveis.

Ordem de produto:

1. **UGC real assistido:** material real → transcrição → cortes → captions → marca → variações → revisão → export.
2. **Vozes stock e voz clonada consentida:** roteiro → pronúncia → síntese → QA → versão de áudio.
3. **Apresentador híbrido:** vídeo/template aprovado + nova voz + lip-sync + cenário/branding.
4. **Photo Avatar:** retrato aprovado + motion template + voz + lip-sync.
5. **Avatar generativo:** pessoa/personagem + áudio/texto + corpo/cenário, somente após licença, qualidade e custo provados.

Os open sources assumem motores especializados. A Clicko mantém:

- contexto, direção criativa e memória da marca;
- contratos e documento canônico;
- consentimento, direitos, isolamento e auditoria;
- experiência de edição e revisão;
- orquestração, custo e aprendizado.

## 2. O que significa “colocar o rosto e o anúncio sair do outro lado”

```text
Contexto da marca + objetivo + canal
  → roteiro e plano de cenas
  → escolha do modo de produção
      ├─ UGC real
      ├─ réplica em vídeo
      ├─ photo avatar
      └─ personagem sintético
  → validação de direitos/consentimento
  → voz stock, real ou clonada
  → performance e lip-sync
  → cenário, máscaras, B-roll e overlays
  → timeline editável
  → render e QC
  → revisão humana
  → proveniência, export e publicação
  → performance volta ao aprendizado da marca
```

O sistema nunca deve esconder qual caminho foi usado. A tela de produção mostra fontes, versões, motores, custo estimado e os gates humanos restantes.

## 3. Taxonomia de identidade

### 3.1 UGC real

- identidade está no vídeo original;
- nenhuma síntese biométrica é necessária;
- Clicko melhora roteiro, cortes, ritmo, captions, áudio, reframing, marca e variações;
- é o caminho prioritário para lançar o Video Studio.

### 3.2 Studio Replica

- usa vídeo consentido de 15–60 s como performance-base;
- troca fala/voz e sincroniza a região facial;
- preserva movimento, iluminação e cenário do take original;
- oferece maior previsibilidade que gerar todo o vídeo.

### 3.3 Photo Avatar

- usa uma ou mais fotos aprovadas e motion template/driving video;
- LivePortrait pode transferir pose/expressão após substituir InsightFace;
- MuseTalk/LatentSync demonstram abordagens de lip-sync, mas as cadeias de pesos atuais foram rejeitadas;
- aumenta risco de drift, oclusão, dentes/olhos artificiais e inconsistência temporal.

### 3.4 Generative Character

- pessoa consentida ou personagem que não representa pessoa real;
- EchoMimicV3/LongCat são candidatos futuros para retrato/corpo/cenário;
- toda cena precisa de disclosure e revisão mais rigorosa;
- personagens sintéticos continuam sujeitos a direitos de marca, voz e assets.

## 4. Mapa completo de componentes do produto

| Estação | Responsabilidade | Entrada | Saída canônica | Motor provável |
| --- | --- | --- | --- | --- |
| Direção | objetivo, público, ângulo, promessa, canal, evidência | campanha/Radar/brief | `CreativeBrief` + `CreativeDirection` | Clicko + `ResearchProvider` opcional |
| Editorial | hook, roteiro, beats, CTA, variações, claims | direção + brand memory | `ScriptVersion` + `ShotPlan` | Lexical como interação |
| Capture | upload/gravação, consentimento e QA | câmera/mic/arquivo | `CaptureSession` + samples | Web APIs + FFmpeg/WaveSurfer |
| Ingest | probe, checksum, malware/MIME, proxy, thumbnails | mídia bruta | `MediaAssetVersion` + proxies | FFprobe/FFmpeg |
| Speech | transcrever, alinhar palavras e speakers | áudio/vídeo | `TranscriptVersion` | WhisperX |
| Voice | stock, clone, conversão e pronúncia | texto + voice ref | `AudioPerformanceVersion` | Chatterbox/Kokoro/OpenVoice |
| Identity | cadastrar, versionar, revogar e excluir | capture + consent | `IdentityVersion` | Clicko; providers apenas derivam |
| Motion | pose, gesto e expressão | retrato/vídeo + template | `MotionArtifact` | LivePortrait |
| Lip-sync | sincronizar boca com áudio | vídeo/avatar + áudio | `LipSyncArtifact` | nenhum aprovado; MuseTalk/LatentSync apenas referência |
| Segmentation | pessoa/produto/fundo ao longo do tempo | vídeo + prompts | `MaskTrackVersion` | SAM 2 |
| Scene | fundo, B-roll, iluminação, layouts e marca | assets + masks + shot plan | layers/tracks no documento | Clicko + HyperFrames/FFmpeg |
| Timeline | montagem, trim, split, reorder, keyframes | tracks canônicas | atualização de `CreativeDocument` | UI Clicko; OpenCut/reference |
| Reality | observar câmera, objetos, relações, eventos e trajetórias | mídia + time-map + intenção do shot | `RealityModelV1` | ensemble provider-neutral em worker `vision_gpu` |
| Preview | reprodução WYSIWYG com proxies | documento + assets | frames/preview | browser + HyperFrames projection |
| Render | composição final e encodes | versão fixada | `RenderedArtifact` | HyperFrames + FFmpeg |
| QC | A/V sync, codec, black frames, loudness, identidade | artefato | `QualityEvaluation` | FFprobe/FFmpeg + avaliadores; gate técnico UGC v1 entregue, calibração/identidade pendentes |
| Physical QC | continuidade, permanência, gravidade, contato, causalidade e linguagem cinematográfica | render + `RealityModelV1` + constraints | `PhysicalPlausibilityEvaluationV1` | ensemble calibrado; advisory inicialmente |
| Review | comentários em tempo/região e decisão | versão + artifact | `ReviewRequest/Decision` | sistema principal |
| Factory | lotes, dependências, capacidade, custo, retry | recipes + docs | jobs/artifacts/version lineage | Studio orchestration + Celery inicialmente |
| Provenance | ingredientes, ações, modelo, disclosure | lineage completo | `ProvenanceManifest`/C2PA | Clicko + C2PA tooling |

## 5. Fluxos detalhados

### 5.1 UGC real assistido

1. Usuário escolhe marca, objetivo, canal e duração.
2. Direção gera de 2–4 conceitos comparáveis, nunca o vídeo diretamente.
3. Usuário escolhe conceito; Editorial cria roteiro, shot list e guia de gravação.
4. Usuário grava no produto ou envia takes.
5. Ingest valida, calcula checksum, extrai metadados e cria proxies.
6. WhisperX produz transcript/palavras; usuário corrige termos de marca.
7. Clicko sugere selects, silêncios, fillers, hook e cortes; tudo aparece como diff/timeline editável.
8. Timeline aplica trim/split/reorder, captions, música, B-roll, logo e CTA.
9. SAM 2 pode rastrear pessoa/produto para reframing ou text-behind-person.
10. HyperFrames/FFmpeg renderizam a versão fixada.
11. QC técnico e humano bloqueia export quando necessário.
12. Review aprova a versão exata; export inclui lineage e disclosure aplicável.

### 5.2 Matrícula de rosto/identidade

1. Titular recebe explicação de finalidade, marcas, canais, tipos de peça, prazo e revogação.
2. Consentimento específico é registrado com versão do texto, timestamp, actor, IP/device quando juridicamente apropriado e hash da evidência.
3. Captura pede frase aleatória, movimentos de cabeça e expressões; liveness é controle antifraude, não garantia absoluta.
4. QA exige uma face adulta autorizada, iluminação, foco, cobertura de ângulos, boca visível e ausência de terceiros.
5. Originais entram criptografados e com retenção curta.
6. Derivações — crops, masks, motion templates, embeddings — recebem hashes e `IdentityVersion` imutável.
7. Usuário revisa amostras privadas antes de ativar.
8. Todo job valida consentimento no submit e novamente antes de export/publicação.
9. Revogação bloqueia novos jobs, cancela fila compatível e inicia deleção em DAG.

Não haverá treinamento per-user na primeira versão. Zero-shot e templates versionados reduzem retenção, custo e superfície de risco.

### 5.3 Matrícula/clonagem de voz

1. Consentimento de voz é separado do consentimento de rosto.
2. Captura orientada coleta 10–60 s limpos, com frases balanceadas e variação controlada.
3. QA mede clipping, silêncio, SNR, múltiplos speakers e conteúdo impróprio.
4. `VoiceVersion` guarda refs de amostras, idioma/sotaque declarado, hash de embedding e permissões; nunca o payload do motor.
5. Chatterbox V3/pt-BR gera voz zero-shot; Kokoro gera voz stock; OpenVoice converte timbre sobre TTS-base quando necessário.
6. Dicionário de pronúncia resolve marcas, siglas, números, moedas e nomes próprios.
7. A interface permite ajustar velocidade, pausas, ênfase e emoção dentro do que o provider suporta honestamente.
8. QA bloqueia off-script, repetição, alucinação, identidade fraca e pronúncia crítica.
9. Watermark do modelo é preservado/testado e complementado por lineage/C2PA.

### 5.4 Apresentador híbrido

1. Selecionar `IdentityVersion`, `VoiceVersion`, roteiro e cenário.
2. Gerar áudio aprovado primeiro; vídeo nunca dirige texto não revisado.
3. Escolher vídeo/template de performance ou motion template.
4. Um futuro `LipSyncProvider` aprovado sincroniza a boca. MuseTalk e LatentSync não entram sob a regra open-source-only vigente.
5. Opcionalmente LivePortrait aplica pose/expressão com detector permissivo.
6. SAM 2 separa foreground/fundo; cenário continua camada independente.
7. Timeline recebe foreground, áudio, captions, B-roll, música e overlays como tracks editáveis.
8. QC faz comparação de identidade, temporalidade, boca/dentes/olhos, A/V sync e bordas de máscara.
9. Revisão humana mostra lado a lado source/resultado e identifica trechos sintéticos.

### 5.5 Cenários

Primeira versão:

- fundos próprios, brand templates e stock com direitos verificados;
- background blur/color, crop/reframe e iluminação/grade controlada;
- B-roll e overlays derivados do shot plan;
- máscaras/tracking corrigíveis pelo usuário.

Versão posterior:

- geração de fundo/corpo/cena atrás de `GenerativeSceneProvider`;
- modelo, pesos, dataset e direitos passam por gate próprio;
- Stable Diffusion/FLUX ou outro “open weight” não entram só por estarem disponíveis.

## 6. Arquitetura-alvo

```text
Clicko Web
  ├─ Direction / Editorial / Video / Presenter / Factory UI
  └─ projeções UI (Lexical, timeline, waveform, canvas)
          ↓ contratos versionados
Clicko API + Studio Kernel
  ├─ CreativeDocument / versions / review / jobs
  ├─ Consent + Identity + Voice + rights
  ├─ Provider Registry + Model Registry
  └─ Orchestrator / policy / cost / audit
          ↓ filas capability-specific
Workers isolados
  ├─ CPU media: probe, proxy, FFmpeg, HyperFrames
  ├─ GPU speech: WhisperX, Chatterbox/OpenVoice
  ├─ GPU identity: LivePortrait sem InsightFace + futuro lip-sync aprovado
  └─ GPU vision: SAM 2 / generative avatar
          ↕ signed, scoped asset access
Object Storage
  ├─ quarantine/raw
  ├─ proxy/derived
  ├─ artifacts/exports
  └─ manifests/provenance
```

PostgreSQL/pgvector guarda metadados, documentos, versões, políticas e embeddings permitidos. Redis guarda fila/cache/locks efêmeros. Binários não ficam no banco nem no filesystem da VPS.

### Regras de execução

- um job pesado executa em processo/container isolado por workspace;
- egress negado por padrão; models e fonts vêm de cache pinado/read-only;
- inputs chegam por URLs assinadas de curta duração ou volume efêmero;
- limites de duração, frames, resolução, CPU, RAM/VRAM, disco e tempo;
- progresso normalizado por estágio; cancelamento TERM → grace → KILL;
- output tardio de job cancelado é descartado;
- logs não contêm mídia, voz, embeddings ou prompts sensíveis;
- checksum e manifest são calculados antes de o artefato se tornar publicável.

## 7. Contratos e modelo de dados

### 7.1 Entidades novas

| Entidade | Campos essenciais | Regra |
| --- | --- | --- |
| `ConsentGrant` | subject, owner, purpose, scopes, brands/channels, policy version, granted/expires/revoked | específico, versionado e revogável |
| `CaptureSession` | type, instructions, device, samples, QA, consent ref | raw com retenção limitada |
| `IdentityProfile` | subject/owner/workspace, state | contêiner lógico, sem payload de provider |
| `IdentityVersion` | consent ref, sample refs, derived refs, capabilities, hashes | imutável; revogação invalida uso |
| `VoiceProfile/Version` | samples, locale/accent, embedding ref, pronunciation profile | separado do rosto |
| `AvatarProfile/Version` | identity ref, mode, motion refs, approved previews | aponta para versões autorizadas |
| `ScenePreset/Version` | layers, rights, brand/channel, safe areas | identidade não inclui cenário |
| `ScriptVersion` | structured blocks, pronunciations, claims, approvals | fonte editorial canônica |
| `ShotPlan` | beats, shots, duration, assets, performance direction | liga roteiro a timeline |
| `MediaAssetVersion` | storage ref, checksum, media metadata, rights, parent | imutável e tenant-scoped |
| `TranscriptVersion` | words, speakers, corrections, model lineage | correções nunca somem |
| `ProviderArtifact` | capability, request/result schema, provider/model digest, assets | descartável/substituível |
| `QualityEvaluation` | metric, threshold, result, evaluator, human decision | gate auditável |
| `RealityModelV1` | asset/checksum/time-map, câmera, orientação, entidades, tracks, relações, eventos, hipóteses | imutável por execução; toda inferência tem confiança e lineage |
| `ShotRealityConstraintV1` | mode, entidades/estados, precondições, ação/outcome, continuidade e técnicas declaradas | distingue erro de cut, slow motion, reverse, VFX e surrealismo intencional |
| `PhysicalPlausibilityEvaluationV1` | revision/render, policy/model digests, dimensões, intervalos, entidades, evidências, incerteza, decisão humana | localizado, calibrável e capaz de se abster |
| `ProvenanceManifest` | ingredients, actions, model/weights, identity/consent refs | acompanha export |
| `ProductionRecipe` | ordered capabilities, policies, variants, budget | base da Factory |

### 7.2 Evolução do CreativeDocument

`CreativeDocumentV1` permanece provider-neutral. A evolução v1.x tipa:

- `VideoTrack`, `AudioTrack`, `CaptionTrack`, `OverlayTrack`, `MaskTrack` e `MarkerTrack`;
- `Clip` com source range, timeline range, rate, transform, volume e transitions;
- refs para `ScriptVersion`, `ShotPlan`, `IdentityVersion`, `VoiceVersion` e `ScenePresetVersion`;
- frame rate racional/timebase; evitar floats como fonte de verdade;
- proxy/original refs e reconform;
- effect/keyframe envelopes versionados;
- estado editorial separado do estado operacional dos jobs.

Lexical, OpenCut, React Timeline Editor, Fabric/Konva e HyperFrames recebem projeções bidirecionais testadas. Nenhum JSON dessas bibliotecas substitui o documento.

### 7.3 Ports de capability

- `MediaProbeProvider`
- `MediaNormalizeProvider`
- `ProxyGenerationProvider`
- `TranscriptionAlignmentProvider`
- `StockVoiceProvider`
- `VoiceCloneProvider`
- `VoiceConversionProvider`
- `IdentityEnrollmentProvider`
- `AvatarMotionProvider`
- `LipSyncProvider`
- `SegmentationTrackingProvider`
- `VisualGeometryProvider`
- `ObjectTrackingProvider`
- `PhysicalSceneUnderstandingProvider`
- `VideoWorldModelProvider`
- `PhysicalPlausibilityProvider`
- `RealityCalibrationProvider`
- `GenerativeAvatarProvider`
- `GenerativeSceneProvider`
- `VideoCompositionProvider`
- `VideoRenderProvider`
- `QualityEvaluationProvider`
- `ProvenanceProvider`

As interfaces compartilham envelope de job, asset refs, progresso, cancelamento e lineage; não fingem que parâmetros específicos são iguais.

## 8. Uso estratégico de cada repositório

| Repositório | Uso principal | Valor além da proposta | Decisão |
| --- | --- | --- | --- |
| HyperFrames | composição/render programático | jobs imutáveis, lint, chunks, determinismo, player e motion templates | encapsular/adotar após worker gate |
| hyperframes-launch-video | referência de produção | storyboard, subcompositions, fallback de shader, disciplina de assets | referenciar; não copiar |
| FFmpeg | probe/transcode/mux/QC | proxies, loudness, thumbnails, silence/scene detect, smart crop, adversarial validation | adotar build auditada |
| OpenCut rewrite | futuro Editor API/Rust/headless | plugin-first, scripting e MCP como direção arquitetural | acompanhar; imaturo hoje |
| OpenCut Classic | timeline/editor local | snapping, keyframes, masks, effects, commands, storage migrations, compositor Rust/WASM | referência/piloto seletivo; arquivado |
| React Timeline Editor | timeline mínima | protótipo rápido de drag/resize/playback | benchmark contra módulos OpenCut |
| WaveSurfer | waveform/regions/record | QA de captura, transcript sync, fades e peaks | UI adapter; pin v7 estável |
| WhisperX | transcript/alignment | busca, highlights, captions, speaker-aware edits | encapsular após PT-BR benchmark |
| SAM 2 | masks/tracking | text-behind-person, product lock, reframe, asset extraction | worker GPU após benchmark |
| V-JEPA 2 | representação/predição latente de vídeo | candidato a world model para estado e surpresa temporal | benchmark após pin/licença; nunca árbitro único |
| TAPIR + RAFT | point tracking e fluxo óptico | trajetórias, continuidade e evidência localizada | candidatos permissivos para PGV-1 |
| Supervision 0.30.1 | normalização/annotations/zones/métricas CV | anti-corruption layer entre modelos e `RealityContributionV1`; overlays explicáveis e harness de benchmark | spike priorizado; sem persistência upstream, sem ByteTrack depreciado e sem provider ativo |
| Depth Anything V2 Small | profundidade monocular | ordem de profundidade, suporte e oclusão | somente checkpoint Small Apache; benchmark |
| Physics-IQ | experiments/benchmark físico | corpus de validação e desenho de avaliação multiview | evidence/benchmark; não runtime |
| IntPhys2, MVPBench e CausalVQA | física intuitiva, pares mínimos e causalidade | taxonomia e protocolo anti-atalho | evidence-only; respeitar licenças de datasets |
| Fabric.js | canvas visual | review annotations, masks, templates e headless thumbnail | favorito inicial; benchmark |
| Konva | scene graph alternativo | hit testing/cache/whiteboard | comparador; não usar junto |
| Lexical | roteiro/brief/captions | nós de scene/beat/voice direction/citation, diffs e colaboração | adotar como UI/editor |
| Chatterbox V3 | clone/TTS PT-BR | voz multilíngue, pack regional, watermark embutido | candidato primário de benchmark |
| Kokoro 82M | TTS stock PT-BR | preview rápido, acessibilidade e fallback CPU | candidato a `StockVoiceProvider` |
| OpenVoice V2 | conversão de timbre | padronização/localização cross-lingual | fallback experimental |
| PersonaPlex | conversa speech-to-speech full-duplex | protocolo de interrupção/backchannel e separação role/voice prompt | checkpoint rejeitado sob open-source-only; referência futura, não voz PT-BR de anúncio |
| MuseTalk 1.5 | lip-sync em vídeo | referência de dublagem mantendo cenário/performance | rejeitado: pesos OpenRAIL-M + SyncNet OpenRAIL++ |
| LivePortrait | pose/expressão | motion templates reutilizáveis e preview | após substituir InsightFace |
| LatentSync 1.6 | lip-sync diffusion | referência de qualidade | rejeitado: pesos OpenRAIL++ e InsightFace não comercial |
| EchoMimicV3 | avatar/corpo/cenário | storyboard generativo e variação de enquadramento | spike avançado |
| LongCat Avatar | avatar generativo longo | multi-person/continuação/cinematográfico | horizonte de pesquisa |
| Vane | pesquisa com fontes | corpus para Creative Research | referência; não implantar app |
| Remotion | padrões de composição | ergonomia React/serverless/chunks | rejeitar dependência |
| HeyGem/Duix | referência de fluxo local | captura, fila e polling | rejeitar código/containers |
| Fish Speech/F5-TTS/XTTS | voz | comparação de qualidade | rejeitar pelo licenciamento atual |

### Decisão específica sobre OpenCut

OpenCut agrega bastante, mas não como “engine pronta” neste momento:

- o repo novo, commit `400f097becba`, é MIT e está no início do rewrite; Editor API, plugins e headless são roadmap;
- o Classic, commit `cf5e79e91914`, é MIT, arquivado e contém o editor material;
- módulos valiosos: timecode/frame rate, placement, snapping, group move/resize, commands/undo, keyframes, masks, effects, waveform, storage migrations e compositor GPU/WASM;
- lacunas: manutenção encerrada, export/preview em refatoração, aplicação inteira com auth/DB/store próprios e ausência de contrato headless estável;
- ação: criar spike que projeta `CreativeDocument` para uma timeline mínima inspirada no Classic e compara com React Timeline Editor. Copiar apenas módulos MIT isoláveis, mantendo NOTICE/atribuição e testes; nunca importar auth, projeto, banco ou documento OpenCut.

## 9. Segurança, consentimento e proveniência

### Controles obrigatórios

- política de adultos autorizados na primeira versão;
- proibir terceiros/pessoas públicas sem revisão reforçada;
- consentimento específico por voz, rosto, finalidade, marca, canal e prazo;
- revalidação no submit, render, export e publicação;
- revogação e deleção em DAG: raw → normalized → crops/masks → embeddings → motion → drafts/exports → CDN/cache → backup tombstone;
- criptografia em trânsito e repouso; chaves e escopo por tenant/identidade;
- recibo de deleção e crypto-erasure quando aplicável;
- revisão humana obrigatória; sem auto-publish sintético;
- disclosure visual/metadado proporcional ao canal;
- C2PA/Content Credentials com ingredients e actions quando suportado;
- registro do que não pode ser apagado de cópias já baixadas/publicadas.

### Gating de licença

O Model Registry registra para cada execução:

- repo/commit/tag;
- imagem por digest e SBOM;
- binário/build flags;
- modelo/peso por digest;
- licença de código, peso, dataset conhecido e dependências;
- uso comercial/SaaS, atribuição e restrições;
- regiões/idiomas autorizados;
- owner da decisão e data de revisão.

Mudança de digest reabre o gate. README não substitui LICENSE/model card.

## 10. Benchmarks e critérios de qualidade

### 10.1 Corpus Clicko consentido

- 10 vozes adultas consentidas, com sotaques brasileiros variados;
- roteiros curto/médio/longo contendo marca, siglas, moedas, datas e emoção;
- vídeos de 5/15/60 s com diversidade de tons de pele, barba, óculos, ângulos e iluminação;
- UGC limpo, ruído moderado e fala sobreposta;
- formatos 9:16, 1:1 e 16:9;
- corpus adversarial de arquivos, SVG/HTML, duração/resolução e paths.

Dados de teste reais não entram no repositório; apenas manifests, métricas e fixtures sintéticas.

### 10.2 Métricas

| Capability | Métricas mínimas |
| --- | --- |
| Transcrição | WER, brand-term accuracy, word timestamp drift, speaker attribution, RTF, RAM/VRAM |
| Voz | naturalidade, similaridade, sotaque, pronúncia, off-script, repetição, RTF, VRAM, custo/min |
| Lip-sync | A/V offset, LSE-D/LSE-C quando válido, dentes/boca, jitter, identity drift, human preference |
| Motion/avatar | identidade, expressão, temporalidade, oclusão, mãos/corpo, background drift, regeneration rate |
| Segmentation | IoU/estabilidade percebida, bordas, oclusão, correction effort, FPS/VRAM |
| Timeline | frame accuracy, 1.000/10.000 clips, drag latency, undo, keyboard/a11y, memory |
| Render | pixel/frame parity, A/V sync, determinismo, black frames, codec, loudness, cancel/cleanup |
| Factory | queue wait, success/retry/cancel, GPU utilization, cost/output, orphan cleanup |

Thresholds numéricos finais são definidos antes do spike e registrados no `QualityPolicy`; não serão inventados depois de ver o resultado.

Estado em 25/08/2026: políticas provider-neutral `studio.benchmark-policy.v1` foram congeladas em `benchmarks/studios/identity/` antes de qualquer resultado. Voz stock e clone agora são suites separadas: stock usa corpus sintético sem sujeitos biométricos e orçamento CPU/custo próprio; clone exige 10 adultos consentidos e worker GPU. Clone exige, entre outros gates, MOS ≥ 4,0, acurácia de termos críticos ≥ 98%, zero off-script crítico, RTF p95 ≤ 1,5, VRAM ≤ 24 GB e cleanup físico de 100%. Avatar exige MOS ≥ 4,0, similaridade ≥ 0,80, aceitação de lip-sync ≥ 95%, offset A/V p95 ≤ 80 ms, RTF p95 ≤ 6, VRAM ≤ 24 GB e cleanup de 100%. Esses números são política preliminar congelada, não alegação de qualidade nem aprovação comercial.

O avaliador retorna `incomplete` quando faltam corpus, métricas, digests, controles, evidência ou aprovação; retorna `failed` para licença/consentimento/isolamento/threshold bloqueante. Desde o ADR-012, um agregado não prova mais qualidade: `passed` exige manifesto privado de corpus, execução terminal por caso, outputs/checksums/proveniência, observações brutas e review humano cego vinculados por digest; o avaliador recompõe cada métrica. Dados biométricos e paths privados ficam fora do Git.

### 10.3 Teste de voz

Comparar:

1. Chatterbox Multilingual V3;
2. Chatterbox pack `pt-br`;
3. Kokoro stock;
4. Kokoro + OpenVoice;
5. OpenVoice com outro TTS-base somente se necessário.

Gate: licença de todos os pesos, ausência de off-script crítico, pronúncia corrigível, qualidade humana aprovada, custo/RTF previsível e deleção dos derivados comprovada.

### 10.4 Teste de avatar

Comparar em camadas:

- MuseTalk e LatentSync permanecem referências rejeitadas; pesquisar candidato com cadeia integralmente open source;
- LivePortrait sem InsightFace para motion;
- LivePortrait + futuro `LipSyncProvider` aprovado para Photo Avatar;
- EchoMimicV3 somente depois para geração completa.

Gate: nenhum modelo não comercial transitivo, qualidade aprovada em PT-BR/diversidade, cancelamento/cleanup, isolamento e custo por minuto dentro do budget.

### 10.5 Teste de compreensão da realidade

Três suites independentes evitam confundir respostas verbais com utilidade no produto:

1. **understanding:** pares mínimos, contrafactuais e cenários fora da distribuição;
2. **detection:** vídeos reais/gerados com falhas conhecidas e localização temporal/por entidade;
3. **product:** UGC Clicko, câmera em movimento e técnicas editoriais declaradas, medindo falso bloqueio e esforço de correção.

Métricas: paired accuracy, macro-F1, recall/precision crítico, temporal IoU, grounding, ECE/Brier, abstenção, consistência contrafactual, false block, correction effort, latência, VRAM e custo. Metas preliminares pré-run: recall crítico ≥ 0,90; precisão ≥ 0,80; false block em UGC real ≤ 1%; temporal IoU ≥ 0,70; ECE ≤ 0,10; paired accuracy ≥ 0,75. São política experimental, não prova de qualidade. PGV-4 continua advisory mesmo se forem atingidas.

## 11. Roadmap executável

### MI-0 — Fundação de mídia e política

Entregas:

- contratos tipados de tracks/clips/timebase e asset lineage;
- `ConsentGrant`, `IdentityProfile/Version`, `VoiceProfile/Version` sem provider real;
- Model/Provider Registry;
- object storage com quarantine, multipart, signed URL, checksums e lifecycle;
- filas `media.cpu`, `speech.gpu`, `identity.gpu`, `vision.gpu` e políticas de cancel/retry;
- manifests de licença/SBOM e feature flags.

Gate: cross-workspace, revogação, idempotência, cancelamento, migração/rollback e storage comprovados.

### MI-1 — Video Studio UGC assistido

Entregas:

- ingest/probe/proxy/thumbnails;
- player, media bin, timeline mínima e transcript;
- trim, split, reorder, volume, captions e brand overlay;
- render HyperFrames/FFmpeg em worker CPU;
- Review Room ancorada no tempo e export.

Open source: FFmpeg, HyperFrames, WhisperX, WaveSurfer e benchmark OpenCut/React Timeline.

Gate: usuário conclui vídeo 9:16 real, fecha/reabre sem perda, cancela/retry render e aprova a versão exata.

### MI-2 — Inteligência de vídeo e cenário

Entregas:

- highlights/selects explicáveis;
- captions avançadas, silence/filler suggestions e B-roll slots;
- SAM 2 para mask/tracking, reframe e text-behind-person;
- `RealityModelV1` com câmera, entidades, trajetórias, relações e eventos ligados à timebase;
- `ShotRealityConstraintV1` para intenção realista, física estilizada, surreal e técnicas editoriais;
- Physical QC localizado e uma Reality Lane inspirada seletivamente nos markers/overlays do OpenCut Classic;
- scene presets, motion/keyframes e variações por canal;
- batch recipes iniciais.

Execução: PGV-0 contratos/policy → PGV-1 geometria permissiva → PGV-2 scene/event graph → PGV-3 benchmark V-JEPA 2 → PGV-4 QC advisory/Reality Lane → PGV-5 planejamento/ranking → PGV-6 gate de vídeo sintético realista.

Supervision entra apenas dentro de PGV-1/2 como toolkit efêmero de adapter, annotation, zones e métricas. O release 0.30.1 está fixado; `SV-1`/`SV-2` precisam provar fidelidade, determinismo e custo antes de lock/imagem. A existência de um conector não aprova o modelo conectado, e `sv.ByteTrack` está fora por depreciação.

Gate: toda sugestão é editável/desfazível; máscara possui correção manual; toda ocorrência física localiza intervalo/entidades/evidência e pode se abster; custo e worker capacity são conhecidos. Nenhuma correção autônoma ou autoaprovação em PGV-0–4.

### MI-3 — Voz PT-BR

Entregas:

- captura/QA/consentimento de voz;
- `StockVoiceProvider` Kokoro;
- benchmark Chatterbox V3/pt-BR e OpenVoice;
- pronunciation dictionary, versioning, preview, watermark/provenance;
- deleção e revogação ponta a ponta.

Gate: jurídico/licença, benchmark e abuso/safety aprovados. Voz stock pode sair antes de clone.

PersonaPlex não altera MI-3: é inglês e full-duplex, enquanto MI-3 é voz renderizada PT-BR. O código MIT permanece como referência e o checkpoint NVIDIA está rejeitado. Uma capability futura de conversa ao vivo terá port, worker e benchmark próprios.

### MI-4 — Studio Replica e presenter híbrido

Entregas:

- capture/QA/consentimento facial;
- Studio Replica sobre vídeo/template aprovado;
- LivePortrait sem InsightFace; nenhum lip-sync aprovado ainda;
- comparação LatentSync;
- identity QC, side-by-side review, disclosure e C2PA.

Gate: nenhum auto-publish; todos os jobs revalidam consentimento; revogação bloqueia uso e deleção é comprovada.

### MI-5 — Photo Avatar e avatar generativo

Entregas:

- Photo Avatar com motion templates;
- spike EchoMimicV3; LongCat somente se budget justificar;
- foreground/background independentes;
- cenários generativos por provider próprio;
- políticas de maior risco, limites de duração e revisão reforçada.

Gate: licença transitiva, identidade, drift, hardware/custo e transparência aprovados.

### MI-6 — Factory e escala

Entregas:

- `ProductionRecipe`, DAGs, quotas, prioridades e budgets;
- lotes e variantes por canal/idioma/persona;
- autoscaling de workers, GPU scheduling e caches pinados;
- observabilidade de custo/qualidade e dead-letter workflow;
- comparação da capacidade de Celery com workflow engine durável, somente por necessidade medida.

Gate: backpressure, recuperação, custo previsível, zero vazamento cross-tenant e rollback por provider.

### MI-7 — Aprendizado

Entregas:

- performance retorna por `PerformanceFeedback` ao sistema principal;
- avaliação por direção, hook, duração, identidade, voz e formato;
- aprendizado por marca, sem cruzar tenants;
- experimentos e explicações, sem alegar causalidade quando houver apenas correlação.

## 12. Backlog imediato da nova meta

1. Aprovar este documento como baseline de mídia/identidade.
2. ~~Criar ADR para object storage e filas capability-specific.~~ Fundação entregue na ADR-004 e migration `0015`; rollout físico continua condicionado aos gates descritos nela.
3. ~~Desenhar contratos v1 de `ConsentGrant`, `IdentityVersion`, `VoiceVersion` e typed media tracks.~~ Entregue com persistência, autorização e testes em `0014`; avaliação/ativação humana adicionada em `0016`/ADR-005.
4. ~~Definir corpus/thresholds do benchmark antes de rodar motores.~~ Políticas stock/clone/avatar congeladas, evidência por caso e recomputação provider-neutral cobertas por contrato; aprovação jurídica, corpus privado consentido e execução real ainda pendentes.
5. ~~Prototipar a primeira timeline Clicko com fixture real usando OpenCut como referência, sem adotar seu domínio.~~ Reducer nativo entregue para trim e reorder-ripple em frames racionais, com vídeo/áudio/captions/overlays/markers sincronizados. Escala, snapping e undo/redo continuam no benchmark.
6. Transformar o render em worker isolado com cancelamento e manifest. **Parcial avançado:** manifest/boot gate, Redis + worker físico local, attestation persistida, health, retry do mesmo job, cancelamento em `running` sem asset vazado, storage/lineage, `builtin.ffmpeg-ugc-v1` e adapter HyperFrames opt-in estão provados. Rollout PostgreSQL/S3/IAM, reconciliação/dead-letter, observabilidade/autoscaling, SBOM/assinatura da imagem promovida, build FFmpeg aprovada e paridade audiovisual permanecem pendentes.
7. ~~Implementar ingest/probe/proxy e E2E local de UGC assistido até o artefato revisável.~~ O E2E autenticado usa MP4 real, asset privado, FFprobe, proxy/time-map, waveform, documento/timeline, captions, split/reorder/trim, render FFmpeg e review vinculada ao asset/checksum. Um smoke adicional prova API → Redis → processo `media_cpu` separado para probe/retry/cancel; o E2E de browser continua eager e rollout de produção permanece pendente.
8. Somente depois aprovar e executar benchmark WhisperX e voz PT-BR. Contratos/políticas existem e as fronteiras preflight `speech_cpu`/`speech_gpu` foram materializadas com `providers: []`; nenhum motor automático nem score real foi integrado.
9. Avatar começa apenas quando consentimento, storage, workers e review estiverem comprovados.
10. ~~Executar PGV-0 da ADR-013: congelar schemas, taxonomia, policy, fixtures e exemplos de `RealityModelV1`, sem baixar pesos nem tocar na VPS.~~ Contratos/digests, ports, jobs `vision_gpu`, runtime policy advisory, três benchmark policies e fixtures sintéticas foram implementados e testados; nenhum modelo/peso foi executado e a VPS permaneceu intocada.
11. Executar PGV-1 em worker externo: **preflight arquitetural/supply chain, corpus/gate e baseline OpenCV de avaliação concluídos** com orquestradores, bindings, cancelamento/progresso, manifest GPU, artifact inventory, app Celery exclusivo, Dockerfile/locks pinados, runner recomputável e `ProviderPromotionEvidenceV1` fail-closed. A baseline real processou 11/11 casos sintéticos e 6/6 métricas em 1,0 no venv externo pinado, com primeiro run falho registrado e correção de fixture auditável; permanece fora do registry com `activation_decision=incomplete` por candidato `evaluation`. Faltam revisão wheels/RAFT/CUDA, build Linux/SBOM/provenance/assinatura, persistência/cache tenant-scoped, execução externa e TAPIR + Depth Small + RAFT condicionado + estimador próprio. Modelos/datasets NC ficam evidence-only.
12. Executar AI-0 para avatares e edição autônoma: **freeze de policy/protocolo e supply chain concluído**. O catálogo exige seis perfis (3 homens/3 mulheres) e rodadas privadas 6/24/96, com custo, consentimento, revisão e cleanup como gates. O routing de inteligência agora é open-source-first: Qwen3 4B → 30B-A3B Instruct → 30B-A3B Thinking, com Kimi K2.5 apenas como teto. Qwen3 texto, Kimi, Qwen3-VL, EchoMimicV3, Wan2.2, Motion Canvas, OTIO e PySceneDetect permanecem `incomplete`; Ditto upstream está `rejected` por sua cadeia InsightFace. Chatterbox avançou para metadata/Perth bytes resolvidos, mas continua `incomplete` pela imagem/SBOM e benchmark consentido. Nenhum provider novo foi anunciado.
12. ~~Prototipar a Reality Lane consumindo markers/overlays do documento canônico; OpenCut Classic serve de referência MIT, nunca de store/domínio/fork.~~ `RealityLaneProjectionV1`/`project_reality_lane` entregues como projeção provider-neutral, com markers de câmera/horizonte/gravity cue/tracks/abstentions e overlays editáveis; OpenCut Classic continua apenas referência MIT, nunca store/domínio/fork. UI e persistência da correção humana ainda são o próximo slice.
13. Congelar `MediaIndexV1`, `LStoryboardV1`, `EditProposalV1` e `MotionGraphV1`; o VLM/LLM propõe operações com evidência e um reducer determinístico aplica somente operações válidas. **Parcial avançado:** os quatro contratos estão implementados/testados; `remove_range` é a única operação editorial materializada e motion continua projeção de preview até revisão humana. O adapter Qwen passou contra transporte falso, o preflight `llm_gpu` foi construído em Linux AMD64 como não-root/registry vazio e 60 fixtures sintéticas foram geradas com binding por digest, ainda sem inferência. Persistência/API, imagem funcional Qwen, run externo e segunda implementação ainda faltam.
14. Executar benchmark de planner/VLM open-source-first: Qwen3 texto 4B/30B e Qwen3-VL 4B/8B em GPU externa; Kimi K2.5 somente como teto posterior. Medir qualidade, custo, latência, estabilidade de schema e segurança. GPT/Gemini ficam como comparadores opcionais depois que o mecanismo próprio estiver validado.
15. Executar benchmark Chatterbox V3/pt-BR versus OpenVoice e Kokoro, preservando o registry vazio até licença transitiva, revisão cega, imagem/SBOM e cleanup passarem. **Kokoro `pf_dora` já executou 64/64 casos em candidata Linux/AMD64 local e reprovou p95 RTF (`2,338 > 1,0`); RAM/custo passaram, três pacotes cegos foram preparados e o provider continua não anunciado. Chatterbox V3/pt-BR possui lock de oito assets por SHA-256 e Perth auditado. OpenVoice V2 possui lock do converter/WavMark e inventário `incomplete`. Handoff efêmero, adapters e entrypoints Chatterbox e Kokoro+OpenVoice estão implementados/testados com processos/bytes sintéticos, checksums, cancelamento, watermark binding e cleanup. Os dois locks CUDA e imagens OCI locais passaram instalação, CLI/UID e import smoke offline/isolado em Linux AMD64. Faltam pesos montados, SBOM/notices, provenance de promoção, assinatura, GPU attestation e o run privado de 10 sujeitos/60 casos.**
16. Contratar ou produzir seis identidades com direitos próprios — três homens e três mulheres — e materializar cápsulas, vozes, releases e contextos permitidos; não usar rostos raspados da internet.
17. Rodar o protocolo 6 → 24 → 96 vídeos: smoke privado, quatro arquétipos de copy e matriz de duração/cenário, sempre com revisão humana e custo por minuto final.
18. Auditar Ditto e EchoMimicV3 por artefato. Ditto permanece bloqueado por InsightFace; EchoMimicV3 permanece `evaluation` até RetinaFace, Wav2Vec2, CLIP, Wan e checkpoints estarem pinados/licenciados.
19. Implementar motion por `MotionGraphV1`: **contrato, evaluator temporal/físico fail-closed, binding ao `CreativeDocument`/`RealityModelV1`, persistência/API `0026` e projeções HyperFrames/Motion Canvas entregues**. HyperFrames possui runtime offline seekable para grafo revisado; Motion Canvas especializado continua somente como projeção. OTIO segue só import/export e OpenCut apenas referência; adapter executável Motion Canvas e benchmark de paridade ainda faltam.
20. Provar uma única Studio Replica consentida e privada antes de avatar generativo; publicar somente com grant separado `publish.synthetic`, QC e review ligados ao render exato.
21. ~~Auditar Supervision como toolkit de visão sem incorporá-lo ao domínio.~~ Release 0.30.1 pinado, inventory `incomplete`, ADR-019 e pesquisa entregues. `SV-1/SV-2` permanecem o spike seguro: conversão/overlays/métricas em fixtures sintéticas, sem `sv.ByteTrack`, egress ou provider anunciado.
22. ~~Auditar PersonaPlex separando código e pesos.~~ Código MIT registrado; checkpoint NVIDIA `rejected` pela política open-source-only, inglês-only e fora da classe da VPS. ADR-020 preserva apenas padrões full-duplex; nenhum aceite, download, imagem ou provider ocorreu.

## 13. Definition of Done por capability

Uma capability só está entregue quando:

- resolve uma jornada de usuário real e editável;
- possui contrato versionado e provider fake;
- provider pode ser trocado sem migrar o domínio;
- licença de código/pesos/deps/container está registrada;
- storage, tenant isolation, quotas e retenção estão testados;
- job prova progresso, idempotência, retry, cancelamento e cleanup;
- custo/latência/qualidade foram medidos no corpus Clicko;
- estados vazios/loading/error/readonly/conflict estão desenhados;
- acessibilidade e atalhos essenciais foram validados;
- review, lineage, disclosure e rollback funcionam;
- documentação descreve a implementação real.

## 14. Riscos que permanecem gates

- texto jurídico final e base legal de biometria;
- direitos/proveniência granular de datasets de treino;
- detector comercial substituto do InsightFace;
- capacidade GPU e custo por minuto contratados;
- qualidade PT-BR e diversidade fora de demos oficiais;
- sobrevivência de watermark após cadeia de publicação;
- disponibilidade futura de projetos em rápida mudança;
- falsos positivos físicos que tratam linguagem cinematográfica como erro;
- datasets públicos com atalhos/contaminação e avaliadores VLM que repetem o erro avaliado;
- licença separada de código, checkpoint e dataset em modelos de visão/world models;
- custo de tracking/world model e acúmulo de erro geométrico em vídeos longos;
- compatibilidade de codecs/patentes e build FFmpeg por mercado;
- remoção de conteúdos já baixados ou republicados por terceiros.

Esses gates não paralisam MI-0/MI-1. Eles impedem apenas a promoção das capabilities dependentes.

## 15. Princípio final

Os repositórios fizeram o trabalho algorítmico difícil. O trabalho irredutível da Clicko é transformar esses motores em uma linha de produção confiável: contexto de marca, decisão criativa, documento editável, consentimento, qualidade, custo, revisão, proveniência e aprendizado. É isso — e não um clone de uma aplicação open source — que forma a vantagem do produto.
