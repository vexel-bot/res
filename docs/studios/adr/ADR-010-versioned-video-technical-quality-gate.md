# ADR-010 — QC técnico de vídeo versionado e gate de review

**Status:** aceito para o subconjunto UGC local; calibração em corpus real e operação distribuída pendentes  
**Data:** 2026-08-25

## Contexto

Probe do encoder prova que um arquivo abriu, mas não prova que o artefato apresentado está tecnicamente apto para revisão. O plano mestre exige `QualityEvaluation` auditável para codec, black frames, loudness e A/V sync, com thresholds definidos antes de observar resultados e sem transformar output do FFmpeg em domínio Clicko.

## Decisão

`VideoTechnicalQualityProvider` recebe somente o artefato materializado, o `VideoRenderSpecV1`, duração esperada, policy e cancelamento. O adapter inicial `builtin.ffmpeg-qc-v1` usa FFprobe normalizado e filtros FFmpeg limitados (`blackdetect`, `silencedetect`, `loudnorm`) e retorna `VideoTechnicalQualityEvaluationV1`.

A policy congelada `ugc-review-v1` define:

| Check | Threshold | Severidade |
| --- | ---: | --- |
| streams de vídeo/áudio | exatamente 1/1 | blocker |
| codec/canvas/FPS | igual ao contrato; delta FPS ≤ 0,001 | blocker |
| duração final | delta ≤ 80 ms | blocker |
| início e duração A/V | delta ≤ 80 ms | blocker |
| black frames | razão ≤ 5% (`d` mínimo 100 ms) | blocker |
| loudness integrado | -30 a -10 LUFS | warning |
| true peak | ≤ -1 dBFS | warning |
| silêncio | razão ≤ 20% (`d` mínimo 250 ms, -45 dB) | warning |

Blockers determinam `status=failed`; warnings não fingem falha técnica, mas permanecem visíveis para decisão editorial. O render pode terminar e manter uma prova privada com QC reprovado; o review de vídeo exige avaliação presente e `passed` da mesma revisão/versão. Rerender é o caminho de recuperação.

## Persistência e proveniência

- o resultado do job inclui policy, provider/version, métricas, checks e timestamp;
- o lineage do asset inclui a avaliação completa e a tag `technical-qc-passed|failed`;
- o evento `studio.video.render_ready` carrega `qualityStatus`;
- a UI mostra LUFS, delta A/V e percentual de black frames, e desabilita review quando reprovado;
- resultados antigos sem QC não satisfazem o novo gate e precisam ser renderizados novamente.

## Segurança e limites

- subprocessos têm timeout, limite de output e cancelamento cooperativo;
- análise trabalha no arquivo privado temporário antes do storage final;
- nenhum threshold biométrico ou de identidade é inferido por este provider;
- o gate ainda não cobre freeze frames, clipping temporal por amostra, VMAF, lip-sync facial, identidade, C2PA ou política específica de canal;
- a policy precisa de calibração com corpus consentido antes de produção.

## Evidência

- mídia válida aprova com métricas completas;
- vídeo preto falha no blocker `black_frame_ratio`;
- arquivo sem áudio falha em `audio_stream_count`;
- timeout e cancelamento terminam o subprocesso;
- adulterar um resultado aprovado para QC failed bloqueia o endpoint de review;
- E2E real atravessa render → QC → lineage → review e mantém isolamento tenant.

Regressão integral de 25/08/2026, atualizada após o ADR-012: 120 casos coletados no backend, `119 passed, 1 skipped` (smoke HyperFrames externo opt-in); `13 passed` no reducer de timeline; TypeScript, Ruff e build verdes; `17 passed` no E2E completo em 1,7 min. `git diff --check` é revalidado no fechamento de cada corte.

## Próximos gates

1. Calibrar thresholds com corpus UGC PT-BR consentido e canais-alvo.
2. Acrescentar detecção de freeze frame, clipping e loudness por preset de plataforma.
3. Executar render + QC completo no worker físico atestado `media_cpu`; broker/probe/retry/cancelamento de proxy e cleanup já passaram localmente, mas métricas e rollout PostgreSQL/S3 continuam pendentes.
4. Fixar/aprovar build FFmpeg, fonte e SBOM antes de rollout.
