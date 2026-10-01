# Local media generation experiment

Run the installation and execution preflights before provisioning. They have no
ML dependency and use the same controlled cache as the runner:

```powershell
.\.venv\Scripts\python.exe preflight.py --profile-id animatediff-lightning-sd15-a-v1 --phase install --check-environment
.\.venv\Scripts\python.exe preflight.py --profile-id animatediff-lightning-sd15-a-v1 --phase execution --check-environment
```

`resolve-lock.ps1` creates a hashed candidate lock. `qualify-environment.ps1`
installs it in `.venv`, executes the CUDA smoke test and only then marks
`requirements.lock` as qualified. Model download is a separate explicit action:

```powershell
.\.venv\Scripts\python.exe model_store.py provision --profile-id animatediff-lightning-sd15-a-v1
```

Generation is offline and cannot fetch arbitrary model identifiers.

When a host passes admission, set a random token of at least 32 characters and
bind the internal service to loopback only:

```powershell
$env:RES_LOCAL_DIFFUSION_TOKEN = "replace-with-a-random-32-character-token"
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir workers/media-generation-local --host 127.0.0.1 --port 8094
```

The service is intentionally loopback-only. Inference is offline: a generation
request cannot download a missing model or select an arbitrary repository.
