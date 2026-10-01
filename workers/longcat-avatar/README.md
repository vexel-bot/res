# LongCat avatar worker

This is an isolated, disabled integration boundary for LongCat-Video-Avatar 1.5.
It intentionally performs no download and no inference on the current machine.

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
