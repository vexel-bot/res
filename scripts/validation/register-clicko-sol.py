"""Register the local Sol film as analysis evidence in a Clicko workspace."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from uuid import UUID

REFERENCE_ID = "workspace.sol-altkid"
SOURCE_HASH = "77065b018a72182d16554fde7ff924a9e55f77cedd6a344869ae03292a173166"
SAMPLES = [3, 16, 31, 42, 57.6, 62.8, 75.8, 96.5, 101.8]


def checksum(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def transcript(path):
    if path is None:
        return []
    return [
        {"startSeconds": float(start), "endSeconds": float(end), "text": text}
        for start, end, text in re.findall(r"(?m)^(\d+\.\d+)-(\d+\.\d+)\s+([^\r\n]+)", path.read_text(encoding="utf8"))
    ]


def register(source, storage, workspace, transcript_path=None):
    from PIL import Image

    if checksum(source) != SOURCE_HASH:
        raise ValueError("The source must be the reviewed Sol MP4.")
    root = storage.resolve() / "_craft_reference_packs" / str(UUID(str(workspace)))
    root.mkdir(parents=True, exist_ok=True)
    catalog = root / "catalog.json"
    manifest = (json.loads(catalog.read_text(encoding="utf-8-sig")) if catalog.exists() else
                {"schemaVersion": "clicko.reference-evidence.v1", "references": []})
    if manifest["schemaVersion"] != "clicko.reference-evidence.v1":
        raise ValueError("Unexpected workspace reference manifest.")
    previous = next((item for item in manifest["references"] if item["id"] == REFERENCE_ID), None)
    segments = transcript(transcript_path)
    if transcript_path and not segments:
        raise ValueError("The transcript must contain timed segments.")
    if previous and not segments:
        segments = previous.get("temporal", {}).get("transcript", [])
    with tempfile.TemporaryDirectory(dir=root, prefix=".sol-") as folder:
        temporary = Path(folder)
        sheet = Image.new("RGB", (960, 540))
        for index, time in enumerate(SAMPLES):
            frame = temporary / "frame.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(time), "-i", str(source),
                            "-frames:v", "1", str(frame)], check=True, timeout=25)
            with Image.open(frame) as image:
                image.thumbnail((320, 180))
                sheet.paste(image, (index % 3 * 320, index // 3 * 180))
        sheet.save(temporary / "sol-altkid.jpg", quality=88)
        evidence_hash = checksum(temporary / "sol-altkid.jpg")
        still_name = f"sol-altkid-{evidence_hash[:12]}.jpg"
        (temporary / "sol-altkid.jpg").replace(root / still_name)
        video = root / "sol-altkid.mp4"
        if not video.exists() or checksum(video) != SOURCE_HASH:
            shutil.copyfile(source, temporary / video.name)
            (temporary / video.name).replace(video)
        entry = {
            "id": REFERENCE_ID, "file": still_name, "sha256": evidence_hash,
            "reference": {"title": "Sol · launch film", "creator": "ALTKID",
                          "url": "https://www.instagram.com/reel/DeOan0hvOol/", "durationSeconds": 104.2},
            "state": "observed_temporal_source",
            "coverage": {"visual": "sampled_playback_frames", "requestedSampleSeconds": SAMPLES,
                         "timing": "editorial_landmarks_not_exact_cuts", "audio": "source_available_for_playback"},
            "temporal": {"file": video.name, "sha256": SOURCE_HASH, "mediaType": "video/mp4", "transcript": segments},
        }
        manifest["references"] = [item for item in manifest["references"] if item["id"] != REFERENCE_ID] + [entry]
        staged = temporary / catalog.name
        staged.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staged.replace(catalog)
    return catalog


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--storage", required=True, type=Path)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--transcript", type=Path)
    args = parser.parse_args()
    print(register(args.source, args.storage, args.workspace, args.transcript))
