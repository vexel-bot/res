# Speech GPU clone candidate locks

These are two independent Linux AMD64/CUDA evaluation environments. They are
deliberately not worker provider bundles and do not enable any Clicko registry.

- `chatterbox/` resolves the minimal inference dependencies used by the pinned
  Chatterbox source commit. Gradio is excluded and Perth is bound to the audited
  commit instead of upstream `master`.
- `openvoice/` resolves Kokoro pt-BR, direct OpenVoice tone conversion and local
  WavMark. Faster Whisper, Whisper Timestamped, MeloTTS, Silero and Gradio are
  excluded because the selected entrypoint never imports those paths.

The OpenVoice source package and Chatterbox source package are installed without
their upstream dependency declarations by the candidate recipes. Their exact Git
commits remain separately bound in the artifact inventories. This prevents the
upstream demo dependency sets from silently reintroducing networked or unused
software.

Locks are generated for Python 3.11 on Linux x86_64 with the PyTorch CUDA 12.4
index and a resolution cutoff. A lock is evidence for dependency resolution only;
it does not approve weights, the WavMark wheel license, the eSpeak distribution,
an OCI image, benchmark quality or provider promotion.

`build-verification.v1.json` records the 2026-08-27 Docker Desktop verification.
Both source-audit stages, dependency installations and offline import smokes passed
on Linux AMD64. Final local evaluation images were then materialized and tested
with no network, a read-only root filesystem, all capabilities dropped,
`no-new-privileges` and UID/GID 10001. The ephemeral tmpfs must be mounted with
`uid=10001,gid=10001`; it hosts Numba, Hugging Face and Torch caches. No external
voice-clone weights, inference, biometric data, reviewed SBOM, signature or provider
promotion was produced. Chatterbox does contain the already audited bundled Perth
watermark checkpoint.

`license-review.v1.json` binds a package-focused SPDX inventory to both local image
digests. It records the GPL/LGPL/proprietary surfaces and a dependency-minimization
revision without treating the result as a legal conclusion. The full filesystem scan
was intentionally stopped to preserve the Windows host disk reserve, so complete
file/layer SBOM, notices and commercial-distribution approval remain blocking gates.
