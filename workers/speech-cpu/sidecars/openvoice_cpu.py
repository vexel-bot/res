"""Verified, offline CPU execution of the shared Kokoro/OpenVoice converter."""

import argparse
import json
import resource
import shutil
import tempfile
import time
from pathlib import Path

from app.domain.studios.contracts import SpeechSynthesisRequestV1, VoiceCloneReferenceV1
from app.domain.studios.speech_assets import (
    KokoroModelAssetManifestV1,
    OpenVoiceModelAssetManifestV1,
    verify_kokoro_model_snapshot,
    verify_openvoice_model_assets,
)
from kokoro_openvoice_clone import LocalKokoroOpenVoiceRuntime, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    descriptor = json.loads(args.request.read_text(encoding="utf-8"))
    speech = SpeechSynthesisRequestV1.model_validate(descriptor["speech"])
    reference = VoiceCloneReferenceV1.model_validate(descriptor["reference"])
    import hashlib

    with args.reference.open("rb") as source:
        if (
            hashlib.file_digest(source, "sha256").hexdigest()
            != reference.normalized_checksum_sha256
        ):
            raise ValueError("openvoice_cpu_reference_checksum_mismatch")
    if speech.voice_key != reference.voice_version_id:
        raise ValueError("openvoice_cpu_voice_version_mismatch")
    kokoro = KokoroModelAssetManifestV1.model_validate_json(
        Path("/opt/clicko/kokoro-model-assets.json").read_text(encoding="utf-8")
    )
    converter = OpenVoiceModelAssetManifestV1.model_validate_json(
        Path("/opt/clicko/openvoice-model-assets.json").read_text(encoding="utf-8")
    )
    kokoro_root = Path("/models/kokoro-repo/snapshots") / kokoro.source_revision
    openvoice_root = Path("/models/openvoice")
    kokoro_digest = verify_kokoro_model_snapshot(kokoro, kokoro_root)
    converter_digest = verify_openvoice_model_assets(converter, openvoice_root)
    with tempfile.TemporaryDirectory(prefix="clicko-openvoice-cpu-") as temporary:
        work = Path(temporary)
        request_path, audio_path, result_path = (
            work / "request.json",
            work / "speech.wav",
            work / "result.json",
        )
        request_path.write_text(json.dumps(descriptor), encoding="utf-8")
        run(
            request_path=request_path,
            reference_path=args.reference,
            output_path=audio_path,
            result_path=result_path,
            kokoro_root=kokoro_root,
            openvoice_root=openvoice_root,
            runtime_factory=lambda base, target: LocalKokoroOpenVoiceRuntime(
                base, target, device="cpu"
            ),
        )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result.update(
            {
                "executionDevice": "cpu",
                "kokoroModelManifestDigestSha256": kokoro_digest,
                "openvoiceModelManifestDigestSha256": converter_digest,
                "wallSeconds": time.perf_counter() - started,
                "peakResidentBytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                * 1024,
            }
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(audio_path, args.output)
        args.result.write_text(json.dumps(result, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
