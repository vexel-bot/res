# LongCat avatar worker

This isolated service implements the clean-final-audio execution path for
LongCat-Video-Avatar 1.5. Product inference remains disabled on the current
machine: no model weights were downloaded and no model output was qualified.

`preflight.py` validates pinned artifacts without importing PyTorch. `api.py`
exposes the authenticated internal capability and submission boundary. A target
Linux/CUDA image must first resolve `requirements.in` into a hash-locked file,
record its image digest, pass the dependency/license review, provide the pinned
artifacts in `model-manifest.json`, and qualify the clean-audio runner. The
upstream demo's vocal separator is not part of this profile.

The official runtime parameters are recorded in the manifest. At 25 fps, one
93-frame segment is 3.72 seconds. Each continuation adds 80 new frames (3.2
seconds) because 13 frames overlap. The compositor must trim the generated
result to the immutable driving-audio duration.

## Implemented execution

- `protocol.py` checks the complete request, digest, profile, checksums and timing.
- `clean_audio.py` adapts the exact, SHA-256-bound official demo without changing
  the upstream checkout. It removes the separator and applies the request seed.
- `runner.py` prepares a full portrait with letterboxing, uses normalized 16 kHz
  speech for the model, launches the pinned two-rank INT8/distilled pipeline and
  validates the final MP4. Export uses the original final audio, retaining its
  sample rate rather than replacing it with the model's normalized reference.
- `api.py` owns a bounded, serial inference queue, atomic receipts, progress,
  cancellation and authenticated artifact streaming. Interrupted executions are
  marked failed after a service restart; they are not reported as still running.

The backend transmits the complete V2 request, binds receipts to its digest,
streams the result to disk and cancels the worker on its polling deadline.

## Private execution lifecycle (API v0.3)

The backend verifies the authenticated `/api/v1/lifecycle` contract before
uploading private image/audio files. Each actual render attempt has its own
execution ID; backend job idempotency and the stored result cache remain in
charge of avoiding repeated inference. After the transfer, including errors,
timeouts and cancellation, the backend requests `DELETE /api/v1/executions/{id}`.
An accepted asynchronous deletion and a completed deletion are recorded
separately. A cleanup outage is reported without repeating inference; the
worker retention sweep is the fallback.

The worker removes source uploads, normalized media, generated frames, scripts
and logs after an execution ends. It retains only the receipt and, on success,
the final artifact until it is consumed or expires. Deleting a running execution
first cancels it; files are removed after the inference function stops. Locked
files remain pending, stop being served and are retried by the sweeper.

| Setting | Default | Maximum |
| --- | --- | --- |
| `LONGCAT_ARTIFACT_TTL_SECONDS` | 3600 (1 hour) | 86400 |
| `LONGCAT_EXECUTION_TTL_SECONDS` | 10800 (3 hours) | 86400 |
| `LONGCAT_TOMBSTONE_TTL_SECONDS` | 86400 (1 day) | 604800 |
| `LONGCAT_SWEEP_INTERVAL_SECONDS` | 60 | 60 |

Zero, negative, invalid and unbounded settings are rejected. Startup and periodic
cleanup cover interrupted uploads and executions with missing in-process handles.
A minimal deletion receipt contains the execution/profile IDs, request digest,
deletion timestamp and reason; it contains no image, audio, script or model log.
Deleted IDs cannot be replayed while that receipt exists. Expired receipts are
also removed. Cleanup validates the run directory and does not follow symlinks
or Windows junctions into model/source trees or other executions.

These endpoints affect temporary worker files only. They do not delete the
brand's original library assets, model weights or source checkouts. Qualification
on the final CUDA host must still exercise abrupt container/process termination,
storage permissions and process-tree cleanup; CPU/HTTP tests are not that proof.

Run one API process per private run directory. Set `LONGCAT_SOURCE_ROOT` to a
**full, clean upstream checkout** at `6b3f4b8582a8bc3f20f795735f5383716c4ba794` and
`LONGCAT_MODEL_ROOT` to the directory containing the two pinned model folders.
`LONGCAT_WORKER_TOKEN` protects every endpoint. `LONGCAT_RUN_ROOT` is private
temporary storage, outside public/static directories. The current local full
checkout is `.candidate-build/longcat-source`, excluded from distributable code.

The CLI entry point can run qualification cases on the provisioned Linux/CUDA
host; admission from the product still requires the existing runtime/model gates:

```text
python runner.py --execution-dir /private/run --source-root /opt/LongCat-Video --model-root /models
uvicorn api:app --host 127.0.0.1 --port 8095 --workers 1
```

These are separate execution modes; do not run the CLI against a directory
already owned by the API queue. A request directory contains `request.json`,
`reference-image` and `driving-audio`. The CLI writes `result.json`; the API
owns `receipt.json`. A `cancel` file interrupts subprocesses, including torch
ranks on Linux. Logs remain private in that same directory.

## Validation and remaining work

`python -m unittest discover -s workers/longcat-avatar/tests -v` exercises real
FFmpeg preparation/mux/trim/probing plus process cancellation, source patching,
HTTP lifecycle, idempotency and artifact integrity. Model inference is replaced
by generated color frames in the media test and by a transport fixture in HTTP
tests. These checks do not measure identity, acting or Portuguese lip sync.

The CUDA dependency lock, immutable image, complete model/config inventory,
privacy/process qualification on that image and visual qualification remain pending.
`requirements.in` is a resolver input, not an installation or promotion receipt.
The audio pins come from the pinned upstream `requirements_avatar.txt`;
the Torch/TorchVision pair follows the
[official PyTorch compatibility instructions](https://pytorch.org/get-started/previous-versions/#v260).
The service continues to return `blocked_resources` with the current manifest.
