# Clicko Studios — baseline de testes

**Execução:** 2026-08-23  
**Commit:** `965a9bbbfceb05d479c67db84ac4582e567da841`  
**Ambiente:** Windows, Node `v22.15.0`, npm `11.6.1`, Python `3.11.9`.

## Resultado executado antes de alterações estruturais

| Verificação | Resultado | Observação |
| --- | --- | --- |
| `npm run lint` | passou | TypeScript `tsc --noEmit`. |
| `npm run lint:backend` | passou | Ruff: “All checks passed”. |
| `npm run test:stitch` | passou | 38 + 19 = 57; sem iframe/verde legado. |
| `npm run test:design-contract` | passou | três camadas CSS finais sem tipografia abaixo de 12px. |
| `npm run build` | passou | 1.733 módulos; bundle JS 877,18 kB, warning > 500 kB. |
| `npm run test:backend` | `40 passed, 2 warnings` | 103,45 s. |
| `npm run test:e2e` | `14 passed` | 1,8 min; Playwright subiu web + API localmente. |
| Alembic `upgrade head` em banco novo | passou | `0001` → `0009_brand_versions (head)`. |

Banco efêmero preservado como evidência ignorada pelo Git: `artifacts/validation/studios-baseline-migration.sqlite`.

## Cobertura comprovada

### Backend

- autenticação, perfil e workspaces;
- isolamento entre tenants;
- Radar, fontes, ranking, evidências e feedback;
- campanha, kit idempotente e versões;
- creative canvas v1, autosave com 409, versões, restore, export e templates;
- assets privados e limites de upload/render;
- aprovação/comentários persistentes;
- história, métricas e aprendizado;
- jobs Radar com idempotência, retry/falha auditada e autorização;
- estado de Presenter/integração em `workspace_resources`.

### Frontend/E2E

- montagem das 26 superfícies canônicas e 11 alvos adicionais;
- navegação projeto → editor → review → calendário;
- visual/hub/carrossel/Presenter/Apps em modo demonstrativo;
- overlays, foco, deep links, no-iframe e overflow em rotas selecionadas;
- health da API junto ao frontend.

## Limitação de interpretação

Os E2Es rodam sem autenticação e verificam a faixa “Workspace demonstrativo”. As rotas aprovadas dos editores usam componentes locais, portanto os testes não demonstram:

- criação/reabertura de um documento real pela UI aprovada;
- autosave, conflito ou versionamento na UI aprovada;
- uso da marca/campanha/oportunidade reais no documento;
- carrossel persistente multipágina;
- export do mesmo documento enviado à revisão;
- review pinado à versão correta;
- job de Studio, progresso, retry, cancelamento ou custo;
- provider fake/troca de provider;
- rollback do novo Kernel.

## Matriz de novos testes obrigatórios

| Camada | Teste | Critério |
| --- | --- | --- |
| Contrato | round-trip JSON de todos os schemas v1 | sem perda e rejeição de versão inválida. |
| Compatibilidade | upcast `creative-v1` → `CreativeDocumentV1` | fixtures existentes continuam renderizando. |
| Domínio | state machine de `GenerationJob` | só transições válidas; terminal é imutável. |
| Idempotência | mesma key/payload e key/payload divergente | replay seguro; conflito explícito. |
| Retry | erro transitório e permanente | backoff/attempts e estado terminal corretos. |
| Cancelamento | queued/running/race completion | sem output publicável após cancel. |
| Progresso | monotônico 0–100 | não regride e não avança terminal. |
| Provider | fake A/fake B | domínio e documento não mudam. |
| Autorização | dois workspaces em todos os novos endpoints | 404 e nenhum side effect cross-tenant. |
| Migration | upgrade/downgrade/upgrade | dados antigos e novos preservados conforme plano. |
| Integração | campanha/brand/opportunity → brief/document | refs/versões corretas, sem duplicação. |
| Visual | UI aprovada + backend real | save/reload/conflict/version/export. |
| E2E | login → campanha/oportunidade → Studio → review → export/retorno | IDs criados no teste; sem fixture demo no caminho. |
| Visual regression | 1440×900 e 1280×1024 | shell e acabamento aprovados preservados. |

## Comparação pós-migração

Toda fase deve repetir os oito comandos do baseline, classificar falha preexistente versus regressão e anexar evidência do novo slice. A contagem de testes, isoladamente, não autoriza concluir a meta.

## Resultado pós-migração do primeiro slice

| Verificação | Resultado | Comparação/evidência |
| --- | --- | --- |
| `npm run lint` | passou | tipos OpenAPI e hook Studio incluídos. |
| `npm run lint:backend` | passou | domínio, serviços, router, migration e task sem violações Ruff. |
| `npm run test:stitch` | passou | 38 + 19 = 57 preservadas. |
| `npm run test:design-contract` | passou | contrato tipográfico preservado. |
| `npm run build` | passou | 1.734 módulos; JS 890,01 kB; permanece apenas o warning conhecido de chunk > 500 kB. |
| `npm run test:backend` | `51 passed` | contratos, tenant isolation, idempotência, jobs, review imutável, export ZIP, histórico/restauração não destrutiva, shadow e avaliação offline. |
| Alembic upgrade/downgrade/upgrade | passou | `0001` → `0013`; ciclos `0010 ↔ 0012` e `0012 ↔ 0013` em banco efêmero. |
| E2E completo anterior | `15 passed` | suite completa registrada antes do corte de histórico. |
| E2E Studio focado atual | `1 passed` | autosave, conflito, versão explícita, comparação v2/v3, restauração não destrutiva em v5, review fixado, export PNG/ZIP e contexto real. |
| smoke de rollback | passou | jornada guest com `VITE_STUDIO_KERNEL_ENABLED=false`. |
| captura visual 1440×1000 | inspecionada | `artifacts/validation/studios-authenticated-carousel.png`; sete páginas, controles e painel permanecem íntegros, sem iframe ou erro de runtime. |
| smoke HyperFrames externo | passou | composição própria 1080×1920; lint `0 errors, 0 warnings`; 2 renders H.264/60 frames byte a byte idênticos, fora do monorepo. |

O Playwright agora usa SQLite novo por processo em `artifacts/validation`, evitando que `create_all` sobre um banco antigo esconda a necessidade da migration. A suite guest continua separada do teste funcional autenticado.

## Revalidação antes da próxima onda — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| `npm run lint` | passou |
| `npm run build` | passou; warning conhecido do chunk JS de 895,42 kB |
| `npm run test:backend` antes do contrato de render | `51 passed, 5 warnings` em 143,77 s |
| `npm run test:backend` após o contrato de render | `52 passed, 5 warnings` em 113,75 s |
| `npm run test:e2e` isolado | `15 passed` em 1,1 min |
| HyperFrames com projeção do CreativeDocument | lint limpo; dois MP4s idênticos, SHA-256 `3448032BE22E89F5618CF30FE83655365C16D78F143B73CB56857D1CE08DE4B7` |

Uma execução inicial colocou build, backend e E2E simultaneamente e produziu quatro timeouts/falhas de navegação guest. Os quatro testes passaram isoladamente em 25,6 s e a suíte completa passou quando executada sem contenção. A evidência foi classificada como interferência do ambiente de teste, não regressão do produto; as suítes pesadas devem ser serializadas neste host.

## Fundação mídia/identidade MI-0 — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| Ruff focado em contratos, identidade, storage, jobs, routers e migrations | passou |
| `test_studio_media_identity.py` | `3 passed`; consentimento, isolamento, revogação, registry e timeline tipada |
| suíte focada storage + API upload + criativos + Kernel + identidade | passou; uploads/exports antigos preservados e lineage novo validado |
| `test_object_storage.py` | `7 passed`; escopo tenant, hash, materialização, deleção, traversal e config inválida |
| `test_studio_execution.py` | `2 passed`; placement CPU/speech/vision e dispatch protegido por flag |
| Alembic novo `0001 → 0015 → 0014 → 0015` | passou; colunas de asset e placement verificadas após upgrade e ausentes após downgrade |
| suíte backend completa após MI-0 | `63 passed, 5 warnings` em 237,57 s |

O adapter S3 permanece sem smoke contra bucket real e a flag de filas isoladas permanece desligada. Esses são gates de infraestrutura, não funcionalidades declaradas como entregues.

### Gate de ativação Identity/Voice — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| suíte Studio focada após `0016` | passou; Kernel, mídia/identidade, activation, storage e execution |
| activation integration | passou; role, preview privado, human review, identidade+voz, vínculo do consentimento e expiração |
| Alembic `0001 → 0016 → 0015 → 0016` | passou em banco novo; tabela de avaliações e colunas de review verificadas |
| Alembic `0001 → 0017 → 0016 → 0017` | passou; tabela/rollback do deletion plan verificados |
| Ruff backend completo | passou |

O primeiro ciclo de downgrade detectou ordem incorreta de remoção do índice SQLite. A migration foi corrigida para remover o índice antes do batch rebuild e o ciclo completo passou em um segundo banco novo; a falha não atingiu banco do produto.

### UGC ingest/probe — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| suíte Studio focada até `0018` | `22 passed`; Kernel, identidade, deletion plan, storage, placement e media ingest |
| media ingest integration | passou; upload privado, tenant, idempotência, endpoint dedicado, worker fake e lineage |
| Alembic `0001 → 0018 → 0017 → 0018` | passou |
| smoke ffmpeg/ffprobe real | passou; MP4 H.264/AAC 360×640, 30000/1001 fps, 1.001.000 µs, dois streams normalizados |
| backend completo após `0018` | `65 passed, 5 warnings` em 177,77 s |
| TypeScript + Ruff | passaram após regenerar OpenAPI types |
| build de produção | passou; 1.734 módulos, warning conhecido de chunk JS 895,42 kB |

A build local do smoke tem GPL/version3/x264/x265 e permanece explicitamente não aprovada para produção. A VPS não foi alterada.

### Transcript, captions e edit decisions — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| suíte Studio focada após `0019` | `17 passed`; Kernel, identidade/voz, activation gate, execution, ingest e transcript/captions/edit decisions |
| integração transcript → captions → decisions → timeline | passou; idempotência, tenant 404, revisão otimista, snapshots, projeção racional para frames e aplicação frame-exact de cortes aceitos |
| ripple editável | passou; remoção de 300 ms converteu 150 em 141 frames, criou dois selects com source ranges imutáveis e remapeou/splitou captions sem alterar o asset original |
| Alembic `0001 → 0019 → 0018 → 0019` | passou; tabelas e colunas canônicas verificadas |
| Ruff focado | passou |
| OpenAPI/TypeScript | regenerado com `edit-decision-sets/{id}/apply`; facade tipada cobre ingest, transcript, captions, decisions, render e lifecycle de jobs |

Não houve integração com WhisperX nem ativação de worker/VPS. O provider entregue neste slice é manual e serve para fechar o contrato antes do benchmark.

### Proxy editável — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| suíte Studio focada com proxy | `19 passed`; inclui os 17 checks anteriores e dois testes do proxy |
| integração async | passou; endpoint dedicado, replay idempotente, tenant 404, fila `studio.media.cpu`, job fora da request e bloqueio do endpoint genérico |
| lineage/cancel | passou; novo asset em `derived`, checksum, `derivedFromAssetId`, pointer no ingest e cancelamento queued sem nova saída |
| smoke FFmpeg real | passou; proxy H.264/AAC 360×640, 30 fps, saída reprobed pelo adapter |
| TypeScript + build | passaram após regenerar OpenAPI; warning conhecido do chunk JS 895,42 kB |
| backend completo após proxy | `68 passed` |

A build FFmpeg local continua apenas evidência de desenvolvimento por conter GPL/version3/x264/x265. A flag de filas isoladas continua desligada e a VPS não foi alterada.

### Orquestração de render — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| contrato/job dedicado | passou; output tipado, placement `media_cpu`, idempotência e bloqueio do endpoint genérico |
| snapshot imutável | passou; documento alterado para revisão 2 após enqueue, provider recebeu e resultou revisão/versão 1 |
| artefato/lineage | passou com fake; asset privado, checksum, URI autenticada, provider/version, request e `generationJobId` |
| provider indisponível | passou; registry vazio retorna 422 e não enfileira render |
| Ruff + regressão Studio focada | passaram |
| backend completo após orquestração de render | `69 passed` |

Este bloco valida a orquestração com fake; a evidência do adapter real está registrada separadamente abaixo. A VPS não participou de nenhum render.

### Adapter HyperFrames local — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| projeção provider-neutral | passou; pages/layers, vídeo/áudio/overlay, captions, media-start e FPS racional |
| segurança da projeção | passou; escaping de texto hostil, nomes aleatórios de assets, CSP sem conexão e ausência de URLs remotas |
| activation gate | passou; HyperFrames não inicia sem fila isolada e CLI configurada |
| cancelamento de processo | passou; processo Node longo foi terminado cooperativamente |
| smoke real 0.8.12 | passou; H.264 360×640, 30 fps, 1 s, 15.043 bytes, SHA-256 `A0D65A68D662A274DA34C548CFA793D6030C9B4BA23B7505D097F3754DB658BA` |

### Worker `media-cpu` isolado — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| build local | passou; AMD64, 861.962.598 bytes, digest OCI `sha256:bbfdabed4b7e9f0049d57c2877b6f1146886d89b3c864fe320c929b6c2cb7595` |
| runtime | UID `10001`; Node 22.15.0, HyperFrames 0.8.12, Chromium 151.0.7922.173, FFmpeg 5.1.9, Python 3.11.2 e Celery 5.6.2 |
| isolamento | passou sem rede, root filesystem read-only, home efêmero e tmpfs executável/limitado em `/tmp/clicko-hyperframes` |
| render no-egress | lint limpo; MP4 H.264 1080×1920, 30 fps, 2 s, 548.089 bytes; pipeline 24,4 s |
| SBOM da imagem | CycloneDX, 809 componentes, 1.792.604 bytes, SHA-256 `AF5531A3CF188EEBC95E70F41D601CE5566A3DD5A3070D86D3392ED2E0E65204` |
| backend completo, execução serial | `72 passed`, `1 skipped` opt-in entre 73 testes coletados |
| TypeScript + build após facade UGC | passaram; 1.734 módulos, chunk JS 897,82 kB com warning de code-splitting já conhecido |

### Superfície Video Studio UGC — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| TypeScript | passou após integrar upload privado, Blob autenticado, ingest/proxy, transcript/captions, edit decisions, render e lifecycle de jobs na facade/UI |
| build de produção | passou; 1.737 módulos, CSS 496,37 kB / gzip 80,40 kB, JS 925,53 kB / gzip 247,47 kB; warning de chunk já conhecido permanece |
| inspeção visual | passou em 1280×720; laboratório com media bin, preview 9:16, inspector e timeline sem iframe; banner guest reposicionado para não sobrepor o cabeçalho |
| E2E direcionado | `1 passed`; abre `/content/draft/edit?mode=video`, troca para cortes, aplica feedback demonstrativo não destrutivo, verifica gates `media_cpu`/`hyperframes.cli` e ausência de overflow horizontal |
| E2E completo | `17 passed` em 1,4 min com servidor, storage e SQLite isolados; inclui todas as rotas/referências existentes, Presenter, segunda marca, Visual/Carrossel autenticado e dois cenários de vídeo |
| caminho UGC autenticado | passou; FFmpeg gera fixture H.264/AAC de 2 s, UI faz upload privado, Celery eager exclusivo de teste executa FFprobe, cria documento/timeline, aplica captions e remove 0,4–0,8 s em duas seleções antes de fixar review |
| gate de produção | `CELERY_TASK_ALWAYS_EAGER` é falso por padrão e startup de produção rejeita `true`; proxy/reconform e render HyperFrames no mesmo E2E continuam pendentes |

A imagem foi construída e testada somente no Docker Desktop local. Nenhum serviço da VPS foi consultado, alterado ou reiniciado.

O smoke usou o clone/spike externo já auditado; o monorepo contém somente o adapter e a projeção Clicko. O registry continua vazio por padrão e a VPS continua sem alterações.

### Políticas de benchmark de voz/avatar — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| políticas JSON | passaram validação `studio.benchmark-policy.v1`; voz pt-BR e avatar estão `frozen`, sem assets, paths ou embeddings biométricos |
| candidatos/revisões | Chatterbox, Kokoro, OpenVoice, MuseTalk, LatentSync e LivePortrait fixados por commit/model revision; nenhum peso foi baixado |
| decisão provider-neutral | passou; somente policy aprovada + digests + corpus + controles + evidência + métricas pode retornar `passed` |
| ausência de evidência | passou; policy congelada/run pendente retorna bloqueios e nunca alega qualidade |
| licença bloqueante | passou; LatentSync retorna `failed` por pesos OpenRAIL++/InsightFace, mesmo com scores artificiais no limiar |
| regressão focada | `6 passed`; Ruff limpo nos contratos/testes do benchmark |
| backend completo | exit `0`; 80 testes coletados, 79 passaram e 1 smoke HyperFrames opt-in foi skipped |
| frontend | `npm run lint` e build passaram; 1.737 módulos, CSS 496,37 kB e JS 925,53 kB, com warning conhecido de chunk grande |

Os thresholds são política pré-run, não resultado. Corpus privado consentido, worker GPU, imagens/SBOM e execução real continuam pendentes. A VPS não foi consultada nem alterada.

### Evidência verificável de voz PT-BR — 2026-08-25

| Verificação | Resultado |
| --- | --- |
| separação de suites | `clicko.voice-stock.pt-br.v1` usa 64 casos sintéticos, zero sujeitos e budget CPU; `clicko.voice-clone.pt-br.v1` exige 10 sujeitos consentidos, 60 casos e GPU |
| manifesto privado | `studio.benchmark-corpus-manifest.v1` valida IDs de asset, checksums, pseudônimos, consent grant/evidence, locales e cenários; não aceita paths nem biometria no Git |
| evidência por caso | `studio.benchmark-evidence-bundle.v1` exige job/provider, estado terminal, output/checksum/provenance e observações brutas por caso |
| recomputação | evaluator recompõe mean/rate/p50/p95/min/max/count e bloqueia unidade, evaluator/digest, evidence ID, case set ou agregado divergente |
| review humano | MOS de voz exige candidate label cegado, três reviewers pseudônimos e três ratings por caso: 192 ratings para os 64 casos stock; 180 é apenas o piso da policy |
| licença transitiva | Misaki/eSpeak foram adicionados ao Kokoro+OpenVoice; o wheel `espeakng-loader==0.2.4` foi inventariado por SHA-256 e bloqueado porque embute revisão antiga e omite licença; Kokoro stock/clone ficam `review_required` até build exato, corresponding source, notices e revisão da imagem |
| licença por componente | `studio.benchmark-license-manifest.v1` liga revisão, artifact/license digests, permissão SaaS, obrigações e evidence asset; cadeia divergente ou extra bloqueia |
| regressão focada | `14 passed`; Ruff limpo nos contratos, CLI e testes do benchmark |

O corte prova o protocolo e seus gates, não a qualidade de nenhum motor. Não houve download de pesos, áudio real, consentimento, embedding, GPU ou ativação de provider. A VPS não foi acessada nem alterada.

Preparação stock PT-BR — 2026-08-25: o gerador sintético criou 64 casos determinísticos nos oito cenários da policy, com scriptbook separado e binding por digest. Não há sujeito, asset, consentimento, áudio ou dado biométrico; os arquivos privados ficam fora do repositório em `C:\Users\edugu\Downloads\clicko-private-benchmarks\voice-stock-pt-br`. Isso prepara a fixture para uma execução Kokoro isolada, mas não é evidência de qualidade, licença ou autorização de provider.

Lifecycle privado stock — 2026-08-26: o teste integrado percorreu os quatro CLIs com
64 WAVs de fixture, três pacotes cegos, 192 avaliações ligadas a scripts/checksums,
retenção até `post-review`, cleanup 64/64, preservação de provenance e replay
idempotente do recibo/snapshot `post-cleanup`. Paths privados dentro do repositório,
áudio adulterado, binding divergente e snapshot divergente falham fechados. Nenhum
peso, mídia real, provider de produção ou serviço da VPS foi usado.

Hardening eSpeak — 2026-08-26: a inspeção do wheel Linux 0.2.4 confirmou
`libespeak-ng.so.1.52.0`/commit `4870adfa...`, divergente da policy `7d426728...`, e
ausência de arquivos/metadata de licença. O lock agora exige versões/hashes de loader,
phonemizer e Pydantic e sinaliza replacement obrigatório. Contrato, gerador,
Dockerfile-exporter e workflow manual exigem biblioteca, dados, build attestations,
`COPYING` e corresponding source byte a byte; o runner recusa revisão, wheel ou digest
divergente. A receita não foi construída localmente ou em CI e não promove provider.

### Exclusão física governada de identidade — 2026-08-24

| Verificação | Resultado |
| --- | --- |
| feature gate | passou; `IDENTITY_DELETION_EXECUTION_ENABLED=false` mantém requests em `planned` e não remove objetos |
| remoção/tombstone | passou; derivados e previews foram fisicamente removidos, campos reutilizáveis redigidos e receipts persistidos; source foi preservado por padrão |
| legal hold/shared refs | passou fail-closed antes do primeiro delete; nenhum objeto foi removido quando havia hold ou versão externa referenciando a amostra |
| jobs/retry | passou; job ativo vira `cancel_requested`, execução aguarda terminal e replay continua; falha no segundo objeto preserva progresso e conclui idempotentemente na repetição |
| biblioteca/tenant | tombstones retornam `404`, não aparecem na listagem e não podem voltar a ingest/document/render; asset cross-workspace é bloqueio explícito |
| enqueue | passou; flag on enfileira control task e a API não executa delete inline |
| migration `0020` | upgrade `0019 → head` e downgrade `head → 0019` passaram com inspeção das colunas |
| regressão focada | `7 passed`; mais 14 testes existentes de identity/storage/media/render passaram no conjunto dirigido |
| Ruff completo | passou em `app`, `tests`, `scripts` e migrations |
| backend completo | exit `0`; 87 testes coletados, 86 passaram e 1 smoke HyperFrames opt-in foi skipped |
| frontend | `npm run lint` e `npm run build` passaram; 1.737 módulos e somente o warning conhecido de chunk |

O teste de migration inicialmente revelou vazamento de cache de `Settings` na ordem completa; ele foi corrigido para trocar/restaurar somente `database_url` na mesma instância. A sequência migration → ingest → proxy → jornada de produto → render e a suíte integral passaram depois da correção. A flag não foi ativada e a VPS não foi consultada ou alterada.

### Timeline, waveform, render FFmpeg e binding de review — 2026-08-25

| Verificação | Resultado |
| --- | --- |
| reducer de timeline | `13 passed`; trim start/end e reorder-ripple preservam frames racionais, source ranges, vídeo/áudio/captions/overlays/markers, locks e imutabilidade |
| waveform real | AAC é decodificado em chunks limitados, cortado à duração probada e gera buckets determinísticos min/max/RMS; regressão focada `4 passed` |
| renderer FFmpeg real | MP4 de 2 s com H.264/AAC recomposto do original; E2E final produz 1080×1920, 30/1, 47 frames e um único stream de áudio AAC |
| projeção audiovisual básica | testes extraem frames e contam pixels da faixa, CTA e captions; E2E repete a inspeção RGB no artefato autenticado e lineage lista duas layers + uma caption track |
| QC técnico | policy `ugc-review-v1`; UGC válido passa, vídeo preto e ausência de áudio falham fechado, subprocesso cancela/expira, resultado adulterado bloqueia review e E2E expõe métricas no artefato |
| lineage público seguro | listagem expõe metadata de proveniência sem `storage_key`; render contém `renderedFromOriginal`, source bindings, generation job e digest do snapshot |
| review de vídeo | exige render succeeded da mesma workspace/document/revision/version e fixa job, asset e SHA-256; outro tenant recebe `404` no job e conteúdo |
| Alembic | banco novo passou `0001 → 0023 → 0022 → 0023`; regressão anterior `0022 → 0020 → 0022` preservada |
| TypeScript/Ruff/build | passaram; build com 1.738 módulos, CSS 498,11 kB (gzip 80,81 kB), JS 948,83 kB (gzip 254,07 kB) e warning conhecido de chunk > 500 kB |
| backend completo | 120 coletados; `119 passed, 1 skipped`, exit `0` em execução serial isolada; skip é o smoke HyperFrames opt-in |
| E2E completo | `17 passed` em 1,7 min com API/web, SQLite e storage isolados por UUID de execução |
| inspeção visual | `artifacts/validation/video-studio-ugc.png`, 1440×1000; materiais/pipeline, preview 9:16, saída auditável e timeline multi-track sem overflow |

Limite declarado: `builtin.ffmpeg-ugc-v1` entrega a prova privada do subconjunto de uma fonte com cuts/reorder/áudio, captions lower-third, rectangle e texto de marca. `builtin.ffmpeg-qc-v1` acrescenta um gate técnico versionado, mas seus thresholds ainda não foram calibrados em corpus real. Celery eager continua exclusivo da suíte determinística; o smoke separado valida broker/worker físico local, não operação de produção. Build FFmpeg promovida/assinada, PostgreSQL/S3/IAM, observabilidade e rollout não foram validados. A VPS não foi acessada nem alterada.

### Worker `media_cpu` atestado — 2026-08-25

| Verificação | Resultado |
| --- | --- |
| manifest | `studio.worker-runtime-manifest.v1`, digest `24015eb5a531d980e187a3484e446a047b3a1bceaa5c0c036a63ce03915dc5ac`; capability/queue/jobs/providers/paths/toolchain/isolation validados |
| boot fail-closed | manifest inexistente encerrou o Celery com exit `1` e `worker_manifest_unreadable`; não anunciou `ready` |
| imagem final | `clicko/media-cpu:0.1.0-attested-local`, 862.252.036 bytes, `sha256:c636c1756e231371cc8af50b7dd05ce9f48202c2b99bf98501cb8b202e2e8eec` |
| probe/health | probe explícito na `studio.media.cpu` e healthcheck direcionado ao hostname passaram; contexto expôs toolchain pinada e `attested=true` |
| isolamento | API e worker em containers/PIDs distintos; rede interna, UID 10001, rootfs read-only, cap drop, no-new-privileges, 2 CPU, 2 GiB, 256 PIDs e tmpfs |
| mídia real | MP4 H.264/AAC → upload privado → Redis → processo worker → FFprobe → job `succeeded` com `workerExecutionContext` persistido |
| retry | incompatibilidade real de fonte tentou 3 vezes e falhou sem output; após correção, retry manual do mesmo job terminou `succeeded`, attempts `3 → 4` |
| cancelamento/cleanup | proxy de fonte de 600 s cancelado após `running`; job `cancelled`, sem `proxyAssetId` e sem asset derivado do job |
| migration | `0001 → 0023 → 0022 → 0023` passou em SQLite novo |

O volume, a rede e os três containers efêmeros do smoke foram verificados por nome e removidos ao final. Os bytes de teste eram descartáveis e não são recuperáveis. A imagem local permanece apenas para reprodução; CI precisa gerar digest promovido, SBOM e assinatura próprios.

### Reality/PGV-1 e baseline OpenCV desativada — 2026-08-25

| Verificação | Resultado |
| --- | --- |
| contratos/orquestração | `RealityModelV1`, constraints, Physical QC advisory, bindings, lineage, progresso e cancelamento passaram |
| supply chain | artifact inventory `d1935d35...15dea0c`, manifest GPU `fbe3c7a5...0efb1`, lock preflight `1a40b7d9...97fe0`; tamper e autopromoção falham fechados |
| OpenCV real isolado | Corpus procedural congelado com 11 casos/6 métricas; run final no venv pinado (Python 3.11.9, OpenCV 4.13.0, NumPy 2.2.6) passou 11/11 casos e 6/6 métricas; cancelamento passou |
| abstention | assembler mantém `support_gravity`, contato, colisão, causalidade, materiais e biomecânica sem suporte explícito |
| candidate manifest | `4be8fc9c...417fcd`, status `evaluation`, `advertisedByWorkerManifest=false`; worker principal continua `providers: []` |
| Presenter autenticado | sem capability de provider, a UI mostra consentimento/benchmark pendentes, scores como `—` e bloqueia geração/captura; o fluxo demo continua coberto pelo E2E |
| readiness de Studios | `GET /api/v1/studios/v1/capabilities` é tenant-isolated, read-only e versionado (`studio.capabilities.v1`); com registry vazio retorna `unavailable`, razões e `providerReady/captureReady=false`; provider candidato não aprovado retorna `blocked` |
| registry governado | `POST /studios/v1/providers` e `/models` exigem owner/admin; aprovação sem manifesto comercial completo falha fechada; aprovação válida registra eventos, mas readiness continua bloqueado enquanto benchmark/corpus não estiverem aprovados |
| backend completo | 246 coletados; `243 passed, 3 skipped`, exit `0`; as duas integrações OpenCV skipped no Python padrão passaram no venv externo pinado (OpenCV 4.13.0/NumPy 2.2.6). Além da cobertura anterior, passaram adapter/runner Kokoro, inventário/candidate fail-closed, lock Linux, model manifest, replacement eSpeak byte-manifested, storage privado, três pacotes cegos/192 ratings, ingestão, cleanup 64/64, replay idempotente, receita candidata não-deployável, bootstrap direto dos sete CLIs operacionais, os limites de `voice_clone`, o gate separado de `publish.synthetic` e o rail de `transcription` source-bound com persistência versionada/proveniência. O terceiro skip continua sendo o smoke HyperFrames opt-in. |
| lint | Ruff completo limpo |
| infraestrutura | nenhuma GPU, mídia privada ou VPS foi acessada; Dockerfile preflight continua sem os wheels/provider |

A prova técnica passou, mas não constitui autorização de ativação: o gate permanece `activation_decision=incomplete` porque o candidato está `evaluation`. O próximo gate é repetir o corpus na imagem Linux/AMD64 pinada com SBOM/provenance/assinatura, revisar notices dos wheels, adicionar oclusão/deformação no corpus e comparar TAPIR/RAFT/Depth Small atrás dos mesmos contratos. OpenCut permanece referência apenas para a projeção dos markers/overlays na Reality Lane.

### Video Studio — E2E autenticado e build do frontend — 2026-08-26

| Verificação | Resultado |
| --- | --- |
| typecheck frontend | `npm run lint` passou (`tsc --noEmit`) |
| build frontend/servidor | `npm run build` passou; Vite transformou 1.738 módulos e o esbuild gerou `dist/server.js`; permanece somente o warning conhecido de chunk grande |
| E2E completo após hardening | `18 passed` em 1,6 min com API/web, SQLite e storage isolados por UUID de execução; inclui a correção da expectativa Presenter para `DEMONSTRAÇÃO LOCAL` e o gate autenticado sem provider |
| E2E Presenter após gate de publicação | `2 passed` em 30,7 s; preview/captura continuam bloqueados sem provider e a UI separa consentimento de publicação da revisão humana |
| E2E demo | passou; laboratório UGC, cortes não destrutivos, referência OpenCut e CreativeDocument provider-neutral sem persistência |
| E2E autenticado | passou; upload de MP4 real → FFprobe → proxy → waveform → captions/edit decisions → trim/reorder → render privado → QC → review versionada |
| evidência de saída | render autenticado reprobed em 1080×1920, H.264/AAC, 30 fps e 47 frames; lineage fixa source asset, document snapshot, job, checksum e layers/captions renderizadas |
| isolamento | segundo workspace recebeu `404` para job e artefato; workspace original recebeu `200` |
| execução speech local | imagem Kokoro/eSpeak Linux/AMD64 construída e executada localmente, sempre `evaluation/providers=none`; nenhum provider foi anunciado nem a VPS acessada |

### Boundary de clonagem de voz — 2026-08-26

| Verificação | Resultado |
| --- | --- |
| job `voice_clone` sem `voiceVersionId` | `422 voice_version_required`; não cria job nem chama provider |
| job `voice_clone` sem consentimento | `422 consent_required`; não cria job nem chama provider |
| job `voice_clone` com perfil não-clonado, identidade destacada, versão sem consentimento ou escopo/sujeito divergente | bloqueio `422`; vínculo de identidade/voz e `voice.clone` continuam obrigatórios |
| readiness sem `publish.synthetic` | `publicationAllowed=false`, mesmo que o gate privado de geração esteja pronto; `transcription` aparece como capability separada e não exige esse escopo |
| job `transcription` sem provider aprovado | `409 transcription_provider_not_approved`; não cai no provider genérico e não lê mídia |
| execução ASR fake injetada | ingest/asset/SHA-256 são validados antes do job; resultado cria transcript `draft` idempotente com provider, versão, provenance, métricas e vínculo ao ator/job; checksum adulterado não persiste transcript |
| migrations `0024`/`0025` | upgrade/downgrade real passou; job guarda `requested_by` e transcript automático guarda checksum/provenance/métricas sem alterar o contrato manual |
| suíte backend completa após hardening | `246 coletados; 243 passed, 3 skipped`, exit `0`, execução serial isolada |
| Ruff | passou em `app`, `tests`, `scripts` e migrations |

### Preflight da cadeia speech Linux/AMD64 — 2026-08-26

| Verificação | Resultado |
| --- | --- |
| lock CPU-only | 91 pacotes, digest `a0d7a19a...2214`, PyTorch `2.13.0+cpu`; verificador rejeita PyPI genérico, Triton e NVIDIA |
| modelo/eSpeak | cinco arquivos Kokoro/pt-BR em manifesto `4c738811...9af9`; replacement eSpeak com 391 arquivos e digest `9af35120...e373`; G2P PT-BR passou |
| imagem candidata | Linux/AMD64 local `sha256:043d7a31...d917b`, 746.102.666 bytes, UID 10001, offline, root read-only, quatro CPUs/3 GB, labels `evaluation/providers=none` |
| benchmark real `pf_dora` | 64/64 jobs, falha `0`; p95 RTF `2,338` reprovou `≤1,0`; RAM `1,385 GB` e custo estimado `US$ 0,000613/min` passaram |
| revisão/retention | três pacotes cegos × 64 atribuições preparados e verificados fora do Git; 192 ratings e cleanup ainda não executados |
| supply chain restante | SBOM local inválido/ausente e Scout interrompido antes de possível indexing remoto; provenance/assinatura e revisão de notices/licença continuam pendentes |
| provider/runtime | nenhum provider registrado ou anunciado; sem acesso à VPS |

Essa evidência comprova execução real do baseline stock, mas também sua reprovação de latência neste hardware. Ela não autoriza relaxar o threshold nem substitui licença, review humano/ASR, cleanup, SBOM/provenance e promoção.

### Planning/copy, `llm_gpu` e MotionGraph — 2026-08-26

| Verificação | Resultado |
| --- | --- |
| corpus planning/copy | 60 fixtures sintéticas, 10 cenários × 6 variações, sem biometria; manifesto externo ao Git `4b625660...4698` |
| preflight `llm_gpu` | imagem Linux AMD64 reconstruída, UID/GID 10001, providers `none`, digest local `sha256:efc205d4...ab326`; sem pesos/runtime de inferência |
| `MotionGraphV1` | timebase, keyframes, easing, unidades, limites, bindings ao documento/RealityModel e digests testados |
| gate determinístico | velocidade, aceleração, safe-area e overshoot; constraints físicas falham como `incomplete` sem hipótese/evidência suportada |
| projeções | HyperFrames e Motion Canvas determinísticas; HyperFrames embute runtime offline seekable e rejeita projeção não revisada |
| persistência/API | migration `0026`; create/list/get/replace/review/projection, idempotência, conflito otimista, eventos e isolamento por workspace |
| migration limpa | `0001 → 0026` passou em SQLite descartável; tabela/índices inspecionados e arquivo removido |
| testes | baseline integral posterior a MotionGraph e ao run Kokoro: 313 itens coletados, 310 passaram e 3 integrações opt-in foram ignoradas, exit `0` |

Limite declarado: nenhum Qwen/Kimi foi executado, nenhum provider foi anunciado, Motion Canvas ainda não possui adapter executável e a paridade visual HyperFrames/Motion Canvas ainda não foi benchmarkada. A VPS não foi acessada nem alterada.

### Supply chain e handoff privado de voice clone — 2026-08-26

| Verificação | Resultado |
| --- | --- |
| Chatterbox V3/pt-BR | lock de oito assets e Perth auditado; inventário `review_required` `45242126...e0819`; quatro assets pt-BR (3.206.662.605 bytes) locais e verificados, sem inferência |
| OpenVoice V2 | converter/config, WavMark wheel/checkpoint e revisões fixados; inventário `6e744823...496e1` continua `incomplete` por cadeia Kokoro/licença transitiva, sem pesos ou inferência |
| locks CUDA | Chatterbox 125 pacotes `93ff3518...ee5`; OpenVoice 130 pacotes `d56c6da1...8dd`; Torch/Torchaudio `2.6.0+cu124`, artefatos de registry com SHA-256 e dependências de demo excluídas |
| Docker Linux AMD64 | imagens locais `5702bdc8...a214a` e `bdadbe1e...7d61c`; CLI, UID/GID 10001 e imports passaram sem rede, com root read-only, capabilities removidas, no-new-privileges e tmpfs owner 10001 |
| fronteira de providers | `VOICE_CLONE_PROVIDERS` separado de TTS stock e do registry genérico; ambos permanecem sem provider real anunciado |
| referência privada | asset ativo do mesmo workspace, consentimento/identidade e checksum revalidados; normalização WAV mono/24 kHz de 3–30 s em diretório temporário |
| proveniência/cleanup | resultado liga `voiceVersionId`, `consentGrantId` e checksum da referência; arquivo normalizado é removido após sucesso e divergência/adulteração falha antes do clone |
| worker GPU | manifest exige FFmpeg 5.1.9, fila GPU isolada e attestation; digest `a2561098...db206`, `providers: []` |
| admissão privada 10×6 | contrato e CLI validam manifest externo, 10 sujeitos, 60 casos, seis casos/sujeito, consentimento 100%, cenários/locale e binding estável; relatório não expõe IDs |
| testes alvo finais | 36 passaram; Ruff passou em todo `app`, `tests`, `scripts` e migrations |
| suíte backend completa | 353 itens coletados; 350 passaram e 3 integrações opt-in foram ignoradas, exit `0` |

Limite declarado: adapters e entrypoints Chatterbox/Kokoro+OpenVoice existem, e seus ambientes de dependência passaram import smoke offline. Os pesos Chatterbox pt-BR foram baixados e montados read-only, mas o preflight real recusou inferência: 4.095 MiB disponíveis contra 16.384 MiB exigidos. Nenhuma voz humana foi usada e nenhuma capacidade de clone foi promovida. SBOM/notices, provenance, assinatura, GPU externa elegível e benchmark privado continuam pendentes.

### Auditoria final da meta e novos candidatos — 2026-08-27

| Verificação | Resultado |
| --- | --- |
| frontend/static | TypeScript, Stitch 38 + 19, design contract e build passaram; permanece apenas o warning conhecido de chunk grande |
| backend completo | 371 coletados; 368 passaram e 3 integrações opt-in foram ignoradas; exit `0` |
| E2E completo | 18/18 passaram em Chromium, incluindo o Studio autenticado e UGC real |
| migrations | banco novo percorreu `0001 → 0026 → 0025 → 0026` |
| Supervision | fonte MIT fixada em `0.30.1`/`5f25aa0...`; inventário `incomplete`, nenhum pacote/provider ativado e ByteTrack depreciado excluído |
| PersonaPlex | código MIT fixado em `3428dfd...`; pesos/revisão `fdaf409...` classificados `rejected` pela política open-source-only; nenhum peso aceito ou baixado |
| manifests finais | `vision_gpu.providers=[]` e `speech_gpu.providers=[]` |
| ambiente externo | VPS não acessada; nenhum commit, push ou deploy |

Os testes estratégicos falham fechado se PersonaPlex for anunciado, se os pesos aparecerem como aprovados/baixados, se Supervision for ativado antes de completar o inventário ou se qualquer um dos dois surgir nos manifests. A pesquisa, os ADRs e os inventários são evidência de decisão, não autorização de execução.

### Duplex provider-neutral — 2026-08-28

| Evidência | Resultado |
|---|---|
| contratos e fake assíncrono | 10 testes; policy/voice/role digests, consentimento, frame checksum, interrupção, replay, retenção zero e metadata segura |
| corpus/harness PT-BR | 10 cenários sintéticos e thresholds congelados; pausa, jitter, prompt injection e revogação de consentimento explícitos |
| calibração mecânica | TTFA p95 234,5 ms; interrupt ack p95 120 ms; zero false/missed interrupts; sequência, backchannel e error-free 1,0 |
| state machine | `created/listening/speaking/overlap/interrupted/closing/closed/failed`, transições hashadas no replay e dois fakes distintos no mesmo contrato |
| promotion gate | negado: role/semantic/WER, concorrência, VRAM/RAM, custo e human coverage não medidos; providers vazios; calibração não é benchmark de modelo |

Evidências: `backend/app/domain/studios/duplex.py`, `backend/app/domain/studios/duplex_benchmark.py`, `backend/scripts/run_duplex_benchmark.py`, `benchmarks/studios/duplex/duplex-ptbr-corpus.v1.json` e `benchmarks/studios/duplex/duplex-ptbr-calibration-run-2026-08-28.v1.json`.

O Qwen3-Omni foi pinado em código `e423585...` e modelo `26291f7...`; 25 arquivos foram inventariados, incluindo 15 shards safetensors totalizando 70.523.299.202 bytes, todos marcados `downloaded: false`. O model card declara `license: other`/`license_name: apache-2.0` e não contém LICENSE, então os pesos permanecem `review_required`. O verificador de pesquisa confirma seis candidatos, PersonaPlex `rejected`, zero bytes Qwen baixados e nenhum provider ativo. A regressão final desta etapa teve 24 testes aprovados e Ruff limpo.

Bindings finais: corpus duplex SHA-256 `0a99d70edc7f951c603d5212e2e1ee6db913fcbc55ff06c311e4417d4fccb788`; calibração SHA-256 `4de004f816a271115a42ee422e6f7495954fcbd21bd20ef3076b9e993fa70bd4`; vendor manifest Qwen SHA-256 `6140facf4dabdf3dbcd9c23c27ba9e1ca096bbc2578163669e4bfd1092bfedc9`. A regressão integrada Supervision + OCI + promoção + duplex + pesquisa executou 51 testes e passou integralmente.

O inventário Supervision também abriu as 10 wheels nativas offline: todos os notices possuem hash e objetos compartilhados/vendorizados foram enumerados em `native-bundle-review-evidence.v1.json`. O gate permanece humano; nenhum script converte presença de notice em aprovação jurídica.

### Credencial e smoke da API de vídeo — 2026-08-28

Credenciais distintas foram geradas por CSPRNG e armazenadas somente em `.env`/`.env.video-test`, ambos ignorados pelo Git: segredo JWT da Clicko, chave do futuro sidecar OpenAI-compatible, senha e token do usuário de laboratório. Nenhum valor secreto foi gravado em evidência ou documentação. `AI_BASE_URL`/`AI_MODEL` continuam vazios, portanto modelo inexistente não é anunciado como configurado.

O smoke HTTP real autenticou o usuário, limitou-o a um workspace, enviou um MP4 sintético vertical com áudio, criou ingest idempotente e executou FFprobe. Resultado: job `succeeded`, ingest `ready`, duração de 2.000 ms, um stream de vídeo e um de áudio em modo local embedded. Evidência: `benchmarks/studios/video/video-api-eager-smoke-2026-08-28.v1.json`, SHA-256 `eaffdadcda94381c805b1a9faadd341999cdebe42febfe4e89abc4b1c3ddeb49`.

A bateria de vídeo executou 21 testes e passou: ingestão, proxy, waveform, FFmpeg UGC, job de render e QC técnico. O smoke também encontrou um banco local em `0009`; foi feito backup recuperável e aplicado upgrade até `0026`. A migration `0024_job_actor` foi corrigida para criar a FK por nome no batch SQLite e ganhou teste de upgrade/downgrade por vínculo semântico.

### Supervision SV-1/SV-2 — 2026-08-28

| Verificação | Resultado |
| --- | --- |
| adapter unitário | 10/10 passaram; boxes, masks, tracks, empty set, determinismo, cancelamento e erros fail-closed |
| smoke upstream real | Supervision 0.30.1 real; 3 detecções, 2 tracks, 3 evidências, 2 overlays; rede negada; providers vazios |
| corpus SV-2 | 8 casos sintéticos, sem humano/pesos, thresholds congelados e digest `8b615585...1280bb` |
| fidelidade/determinismo | 1,0 / 1,0 |
| zones/overlay vs OpenCV | parity 1,0 / pixel parity 1,0 contra OpenCV 4.13.0 |
| métricas | precision/recall/F1 `0,714285...`; erro absoluto `0`; caso perfeito mAP@50 `0,99999988` |
| robustez/performance | 4/4 inválidos rejeitados; ~3.877 detecções/s; pico Python ~0,071 MiB no corpus pequeno |
| lock/SBOM | 29 wheels Linux AMD64 por SHA-256; resolução offline com `--require-hashes`; SPDX 2.3 ligado ao lock |
| licença | review `review_required`; dez wheels nativas ainda pendentes de revisão humana |
| OCI | Linux/AMD64 material, manifest `92dbfe13...d6a6`, archive `6507d1eb...6b2c`, BuildKit provenance/SBOM ligados por subject; assinatura ausente |
| runtime hardened | uid 10001, rede `none`, rootfs read-only, capabilities `ALL` removidas, no-new-privileges e limites de PID/memória/CPU; probe `ready` |
| ativação | inventário `review_required`; candidate `evaluation`; `vision_gpu.providers=[]`; VPS não acessada |

### Supervision SV-4 — shadow sintético governado — 2026-08-28

O candidate manifest `supervision-toolkit.provider.json` formaliza a capability `vision_normalization`, liga o adapter, o inventário e o benchmark por SHA-256, permanece `evaluation` e não aparece no manifest do worker. A política de shadow foi congelada antes do run com digest `41c03d5d69cc240c46b80c26cffbdafd0ef4c8aac900b7f0fe010a923a5bdba7`.

O shadow executou Supervision 0.30.1 no runtime isolado, enquanto o backend principal permaneceu sem a dependência. O OpenCV primitive reference continuou autoritativo: oito casos, divergência `0`, falha `0`, abstention `0`, nenhum evidence ID ou derived asset órfão e rollback equivalente sem migration. A evidência `supervision-shadow-run-2026-08-28.v1.json` tem SHA-256 `c20856d08dde178cbfac7df584ecfac0b58f399274445f6c545513339df6984f`.

O resultado técnico é `passed`, mas a ativação continua bloqueada: OCI, provenance/SBOM e runtime hardened agora são materiais; revisão humana de bundles/divergências, assinatura e shadow humano consentido permanecem obrigatórios. O conjunto novo e as regressões de supply chain, adapter e promotion gate somaram 19 testes aprovados; Ruff passou.

O gate de promoção agora exige também o digest de shadow tanto no candidate manifest quanto na evidência de promoção. O verificador OCI deixou de aceitar busca textual: provenance e SBOM precisam ser statements in-toto JSON válidos, com predicate type reconhecido e subject ligado ao digest exato do manifest da imagem. O workflow manual não faz deploy e executará a imagem com usuário 10001, rootfs read-only, rede `none`, todas as capabilities removidas, `no-new-privileges` e limites de CPU, memória e PIDs. As regressões ampliadas de artifacts, shadow, OCI e supply chain tiveram 26 testes aprovados.

### Self-hosted local — Qwen e Chatterbox — 2026-08-28

| Verificação | Resultado |
| --- | --- |
| Qwen local | `Qwen3-4B-Q4_K_M.gguf`, 4.022.468.096 parâmetros, 2.497.280.256 bytes, SHA-256 `7485fe6f...34fdf5` |
| runtime | llama.cpp `b10675-90c26fcd4`, Vulkan; CLI respondeu `OK` e API OpenAI-compatible usa alias estável |
| API | `http://127.0.0.1:18080/v1`, sem chave `401`, com `.env:AI_API_KEY` respondeu `OK`; loopback, não produção |
| Chatterbox pt-BR | 3.206.662.605 bytes de assets por SHA-256; imagem v2 enxergou layout exato e CUDA |
| gate Chatterbox | falhou fechado: RTX 2050 reportou 4.095 MiB, abaixo dos 16.384 MiB do manifest `speech_gpu`; zero áudio/biometria |
| manifests | `llm_gpu.providers=[]`, `speech_gpu.providers=[]`; VPS intocada |

Evidência: `benchmarks/studios/self-hosted/local-self-hosted-readiness-2026-08-28.v1.json`. O Qwen é API local de avaliação; não substitui os tiers Instruct-2507/30B nem autoriza exposição pública. O Chatterbox está asset-ready para GPU externa, não inference-ready neste host.

### Arquitetura CX canônica — regressão final automatizada — 2026-08-29

| Verificação | Resultado |
| --- | --- |
| typecheck | `npm run lint` aprovado |
| rotas/ações | 45 registros, 59 URLs conhecidas, zero issues/órfãs/conflitos; 765 controles, 587 wired e 50 com Action ID |
| contratos CX | 6/6 aprovados |
| build | 1.745 módulos transformados; frontend e servidor aprovados; warning conhecido de chunk grande permanece |
| E2E integral | `26 passed` em 2,9 min, incluindo Biblioteca → Visual, Motion, Image Lab autenticado, móvel 390×844, Vídeo UGC, Presenter governado e persistência/review/export de Visual/Carrossel |
| backend | regressão executada em segmentos sem falhas reproduzíveis; o run monolítico anterior foi interrompido e não é apresentado como execução única limpa |
| gates externos | Figma via MCP e validação com participantes reais continuam pendentes; testes automatizados não substituem first-click/tree test nem auditoria assistiva manual |
