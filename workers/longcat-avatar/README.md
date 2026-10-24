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
runtime privacy/retention lifecycle and visual qualification remain pending.
`requirements.in` is a resolver input, not an installation or promotion receipt.
The audio pins come from the pinned upstream `requirements_avatar.txt`;
the Torch/TorchVision pair follows the
[official PyTorch compatibility instructions](https://pytorch.org/get-started/previous-versions/#v260).
The service continues to return `blocked_resources` with the current manifest.
