# Kokoro stock-voice candidate lock

This directory is an evaluation boundary, not a production provider bundle.

`pyproject.toml` pins the Kokoro and Misaki Git revisions selected by the frozen
`clicko.voice-stock.pt-br.v1` policy and limits registry resolution to packages
published no later than the policy freeze date. The manual lock workflow creates
`uv.lock` on Linux AMD64, verifies its Git bindings and hashed registry artifacts,
installs it in an isolated runner, and uploads it for review.

The generated lock must not be copied into the candidate image until its SBOM and
licenses have been reviewed. A successful lock job does not resolve model weights,
eSpeak distribution obligations, benchmark quality, cleanup, or promotion.

`espeakng-loader==0.2.4` is pinned explicitly because Misaki imports its library
and data paths. Its Linux wheel is only an input, not an approved runtime: it bundles
eSpeak NG 1.52.0 from commit `4870adfa...`, while the frozen Clicko policy requires
`7d426728...`; the wheel also omits license files and license metadata. The candidate
image must replace those bundled bytes with a separately built and manifested copy
from the policy commit. The lock verifier reports
`requiresEspeakRuntimeReplacement=true` so a successful dependency resolution cannot
be mistaken for image readiness.
