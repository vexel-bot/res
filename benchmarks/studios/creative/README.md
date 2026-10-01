# Creative autonomy benchmark

`video-creative-pilot-casebook.v1.json` is the governed P0–P2 corpus for the first
12 Clicko video pilots. It contains exactly three original cases for each
canonical family:

- F1 presenter/UGC contextual;
- F2 split-screen proof/tutorial;
- F3 motion/visual essay;
- F4 cinematic/hybrid/VFX.

The Instagram URLs in two cases are structural references only. The cases
must not copy their wording, assets, identity, or frame-by-frame composition.

Generate the frozen corpus from the repository root:

```powershell
$env:PYTHONPATH = "backend"
python backend/scripts/generate_video_creative_casebook.py
```

The generator intentionally resets animatics to `planned`. Materialize all 12
placeholder animatics locally (no model, voice, identity, network provider, or
publisher is called):

```powershell
$env:PYTHONPATH = "backend"
python backend/scripts/render_video_creative_animatics.py
```

Audit the resulting casebook without invoking a model, network service, or publisher:

```powershell
$env:PYTHONPATH = "backend"
python backend/scripts/audit_video_creative_casebook.py
```

The checked-in P2 batch is at
`artifacts/validation/video-creative-pilot/animatics-20260901-v1/manifest.json`.
It contains 12 QC-passed MP4 placeholders at 540×960/30 fps. These are timing
proofs, not final videos or approvals. The current casebook digest is
`0c0f33b331eb8e389a7a0b1f8d60cb746569ee9568e3f6e0d38001caeb5638b5`.

An eligible casebook audit means the contracts are structurally bound. An
eligible animatic manifest means the low-cost timing artifacts passed technical
QC. Neither result authorizes expensive generation, identity/voice inference,
or publication; those gates remain closed until explicit human review and
rights evidence exist.
