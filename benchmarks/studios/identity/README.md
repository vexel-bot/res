# Clicko identity benchmark policies

This directory contains pre-run, provider-neutral acceptance policies for voice and avatar candidates. It deliberately contains no voice sample, face image, video, consent record, storage URL or biometric embedding.

## What is frozen

- corpus shape and minimum coverage;
- candidates and exact source/model revisions known at audit time;
- required security, consent, review, provenance and deletion controls;
- metric contracts, sample floors and numerical thresholds;
- evidence needed to reproduce a decision.

`frozen` means the thresholds were fixed before observing Clicko benchmark results. It does **not** mean the policy or a provider is approved for production. A policy must move to `approved` through an auditable product, security and legal decision before the evaluator can return `passed`.

Canonical contract digests for the current frozen artifacts:

- voice clone pt-BR: `dc5e58fa37d91dda8d273b4bfa11ab6e34d797c6cf08fc134bcfcb67d1119dc7`;
- stock voice pt-BR: `97dcfb0f58775e4a6b779c0158a72746d39eb24425cf027d1decab2bf9ef55e7`;
- avatar pt-BR: `4b9b343a70562d615e20f1d297e67104cbc36420c03ffd24d269dcadc6b177e4`.
- avatar ad pt-BR (Ditto/EchoMimic/Wan): `c7cfb5898ef0c8a1621787923fe8ed2ef027174bc2577c7007cb3d140cf9bd8e`;
- staged six-avatar protocol 6/24/96: `6bab1ba9ffd1c9275fc28ac2dd9b246db48e51cbaddc2290bfe156ff27d2674f`.

The contract digest includes normalized schema defaults. Changes to the evaluator contract therefore reopen the policy gate even when a source JSON field did not change.

Approval creates a new policy artifact and therefore a new digest; it must never mutate a completed run in place.

The avatar-ad policy is intentionally separate from the original avatar policy. It freezes the
six-presenter advertising matrix without rewriting the earlier baseline. Its protocol requires
three men and three women, private outputs, a passed predecessor round, a hard spend stop,
human review and a cleanup receipt. The provisional authorization caps are USD 25/100/400 for
6/24/96 outputs; these are experiment stop limits, not target COGS.

## Private corpus boundary

The executable corpus manifest lives in private object storage and references assets through tenant-scoped IDs. It must include active consent grants, purpose, scope, expiry, revocation state and a pseudonymous subject key. The digest of that private manifest is recorded in `BenchmarkRunV1`; raw data never enters Git.

Voice clone requires at least 10 consented adult speakers and 60 cases across Brazilian accents, clean/noisy reference audio, three script lengths, brand terms, acronyms, dates, numbers, currency, emotion and adversarial repeat/off-script cases.

Antes de qualquer chamada à GPU, `validate_private_voice_clone_corpus.py` faz a
admissão fail-closed do manifest privado: confere digest da policy, 10 sujeitos,
60 casos, seis casos mínimos por sujeito, cobertura de consentimento 100%, locale,
cenários e estabilidade da ligação sujeito/consentimento/reference asset. Manifest
e relatório são recusados se estiverem dentro do repositório; o relatório contém
somente contagens, digests e razões, nunca IDs de sujeitos, grants ou assets.

Stock voice is a separate 60-case synthetic-only suite with zero biometric subjects. It has a tighter CPU RTF/cost budget and cannot satisfy clone identity or accent-preservation claims.

Avatar requires at least 10 consented adults and 30 cases spanning 5/15/60 seconds, 9:16/1:1/16:9, face/lighting diversity, glasses/facial hair, head motion, occlusion and pt-BR phonetic stress cases.

## Decision semantics

- `passed`: approved policy, immutable digests, complete evidence, all controls true and every blocking threshold met;
- `failed`: an explicit security/license/consent/environment control failed, the run failed/cancelled, or a blocking metric missed its threshold;
- `incomplete`: the run, evidence, review, sample count, component digest or approval is still missing.

The evaluator never converts missing data into a zero or a pass. A `passed` result requires a private `studio.benchmark-corpus-manifest.v1`, a digest-bound `studio.benchmark-evidence-bundle.v1`, an audited `studio.benchmark-license-manifest.v1`, terminal per-case executions, provenance/checksums and raw observations. It recomputes every aggregate and blocks mismatched units, evaluator digests, evidence IDs, case sets, component revisions/licenses or tampered values. Human MOS also requires blinded candidate labels, three distinct reviewer pseudonyms and three ratings per case where the policy declares those floors.

## Current candidate gates

- Chatterbox V3 and the pt-BR pack: code/model metadata are MIT and frozen by exact revision, byte size and SHA-256 in `workers/speech-gpu/chatterbox-model-assets.v1.json` (digest `0b3757e1...e5b7f`). Perth was independently cloned at `ce86c49...d2330`; its MIT license and bundled 37.4 MB neural checkpoint were hashed. The official pt-BR demo uses a separate loader and moving downloads, so Clicko instead records an offline `from_local` mapping. The CUDA lock and dependency/import stage passed; large model bytes, final GPU image/SBOM and the consented benchmark remain unexecuted.
- Kokoro 82M: separate stock/CPU policy; code/weights Apache-2.0, pt-BR pipeline and three Brazilian stock voices. Its license gate stays `review_required` until eSpeak NG distribution/source/notice obligations are approved.
- Kokoro + OpenVoice V2: real PT-BR clone quality is unknown until the consented benchmark. Its transitive Misaki/eSpeak chain is now explicit and the candidate also stays in legal review.
- MuseTalk: code MIT, weights CreativeML OpenRAIL-M and its downloaded SyncNet OpenRAIL++; VAE/Whisper/DWPose/face-parsing revisions are pinned separately. It is rejected for Clicko production under the open-source-only rule and remains evidence-only.
- LatentSync 1.6: code Apache-2.0, weights OpenRAIL++, and the pipeline uses non-commercial InsightFace models. It is rejected for Clicko production under the open-source-only rule.
- LivePortrait: core code/weights MIT, but bundled InsightFace detectors are non-commercial. A permissive replacement must be selected, pinned and benchmarked first.
- Ditto upstream: code is Apache-2.0, but the documented checkpoint tree includes an InsightFace detector. The exact upstream chain is rejected; a replacement detector requires a new inventory and complete rebenchmark.
- EchoMimicV3 Flash: code and upstream model claim Apache-2.0, but exact weights, RetinaFace assets, Wan/Wav2Vec2 chain and Linux image are unresolved. Synthetic-only and not activated.
- Wan2.2 Animate 14B: code/model claim Apache-2.0, but shards, runtime and image are unresolved and the resource class is beyond the first 24 GB lane. Advanced horizon only.

The policies are evaluated by `app.domain.studios.benchmarking.evaluate_benchmark_run`. Contract tests prove that missing results cannot be presented as quality evidence. An operator can evaluate an immutable JSON run without activating a provider:

```powershell
cd backend
python scripts/evaluate_studio_benchmark.py `
  ..\benchmarks\studios\identity\voice-pt-br-policy.v1.json `
  C:\private\voice-run.json `
  --corpus-manifest C:\private\voice-corpus-manifest.json `
  --evidence-bundle C:\private\voice-evidence-bundle.json `
  --license-manifest C:\private\voice-license-manifest.json
```

Exit code `0` means passed, `2` failed and `3` incomplete. A `frozen` policy therefore cannot return success until an explicit approval changes the signed policy artifact.

Para preparar apenas o corpus stock sintético, sem sujeitos, assets ou consentimentos, use o gerador fora do repositório:

```powershell
cd backend
python scripts/generate_synthetic_stock_corpus.py `
  ..\benchmarks\studios\identity\voice-stock-pt-br-policy.v1.json `
  --manifest C:\private\clicko\voice-stock-pt-br\corpus-manifest.json `
  --scriptbook C:\private\clicko\voice-stock-pt-br\scriptbook.json
```

O scriptbook contém somente textos sintéticos e o manifest guarda apenas digests; nenhum áudio ou dado biométrico é escrito no Git. A primeira execução real está resumida em `kokoro-pf-dora-local-run-2026-08-26.v1.json`: 64/64 jobs, mas p95 RTF `2,338`, acima do limite `1,0`. Os WAVs e pacotes cegos continuam privados; o resumo não substitui ratings humanos, ASR, cleanup, SBOM/provenance ou aprovação da licença.

Para validar o manifest privado de clone sem executar modelos:

```powershell
cd backend
python scripts/validate_private_voice_clone_corpus.py `
  ..\benchmarks\studios\identity\voice-pt-br-policy.v1.json `
  C:\private\clicko\voice-clone-pt-br\corpus-manifest.json `
  --report C:\private\clicko\voice-clone-pt-br\admission-report.json
```

O comando não abre áudio, não resolve URLs, não acessa storage e não chama provider.
Ele aceita apenas referências opacas já vinculadas a evidência de consentimento.
