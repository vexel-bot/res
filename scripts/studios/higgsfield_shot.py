"""Quote or generate one reference-guided shot for import as Clicko footage.

Pass a shot directory containing input.json (H3 Lite reference-to-video fields).
Use public reference URLs or image_files/video_files/audio_files for uploads. Keep each shot directory for
resume. Without --max-usd this command only quotes the request.
"""
import argparse
import hashlib
import json
import mimetypes
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import NAMESPACE_URL, uuid5

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.providers.studios.higgsfield import (
    BASE, GenerationReceipt, HiggsfieldProvider, PreparedGeneration, REFERENCE, LTX,
)


def atomic_write(path, data):
    with NamedTemporaryFile(dir=path.parent, delete=False) as scratch:
        scratch.write(data)
    os.replace(scratch.name, path)


def resolve_files(root, body, raw):
    """Upload explicitly named shot inputs once, retaining the provider URLs for resume."""
    for kind in ("image", "video", "audio"):
        paths = body.pop(kind + "_files", [])
        for name in paths:
            path = (root / name).resolve(strict=True)
            content_type = mimetypes.guess_type(path.name)[0] or ""
            if not content_type.startswith(kind + "/"):
                raise ValueError("reference_media_type_mismatch")
            with path.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
            account = hashlib.sha256(raw.encode()).hexdigest()
            cache = root / f".upload-{account[:16]}-{digest}.json"
            if cache.is_file():
                url = json.loads(cache.read_bytes())
            else:
                signing = httpx.post(BASE + "/files/generate-upload-url",
                                     headers={"Authorization": "Key " + raw},
                                     json={"content_type": content_type}, timeout=60)
                signing.raise_for_status()
                fields = signing.json()
                if not all(str(fields[k]).startswith("https://") for k in ("upload_url", "public_url")):
                    raise ValueError("invalid_upload_response")
                with path.open("rb") as source:
                    upload = httpx.put(fields["upload_url"], content=source,
                                       headers=fields["upload_headers"], timeout=120)
                if not upload.is_success:
                    raise ValueError(f"reference_upload_failed_{upload.status_code}")
                url = fields["public_url"]
                atomic_write(cache, json.dumps(url).encode())
            body.setdefault(kind + "_urls", []).append(url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shot", type=Path)
    parser.add_argument("--max-usd", help="Enable generation with this per-shot ceiling")
    args = parser.parse_args()
    root = args.shot.resolve()
    body = json.loads((root / "input.json").read_text(encoding="utf-8-sig"))
    key = str(uuid5(NAMESPACE_URL, root.as_uri()))
    from dotenv import dotenv_values
    env = dotenv_values(Path(__file__).resolve().parents[2] / ".env", interpolate=False)
    raw = next((values.get(name) for values in (os.environ, env)
                for name in ("HF_KEY", "HF_CREDENTIALS", "API_HIGGSFIELD", "HF_API_KEY")
                if values.get(name)), "")
    if ":" not in raw:
        parser.exit(2, "Configure HF_CREDENTIALS on the server (key ID and secret).\n")
    model = body.pop("model", REFERENCE)
    resolve_files(root, body, raw)
    if model == LTX:
        body["image_url"], = body.pop("image_urls")
    intent = PreparedGeneration.prepare(model, body, key)
    provider = HiggsfieldProvider(*raw.split(":", 1), submission_enabled=args.max_usd is not None)
    state_file = root / "receipt.json"
    binding = hashlib.sha256(raw.encode()).hexdigest()
    if state_file.exists():
        state = json.loads(state_file.read_bytes())
        if state["intent"] != intent.digest_sha256 or state["account"] != binding:
            parser.exit(2, "Use a new shot directory for a changed request or account.\n")
        receipt = GenerationReceipt(**state["receipt"])
    else:
        quote = provider.estimate(intent)
        atomic_write(root / "quote.json", json.dumps({"model": model, "usd": str(quote.usd),
                                                      "credits": str(quote.credits)}).encode())
        print(f"USD {quote.usd} ({quote.credits} credits)", flush=True)
        if args.max_usd is None:
            return
        # Bind the request before the first billable POST, including ambiguous timeouts.
        lock = root / "intent.json"
        saved = json.dumps([intent.digest_sha256, binding])
        try:
            with lock.open("x", encoding="utf8") as file:
                file.write(saved)
        except FileExistsError:
            if lock.read_text(encoding="utf8") != saved:
                parser.exit(2, "This shot directory already belongs to another intent.\n")
        receipt = provider.submit(intent, quote, maximum_cost_usd=args.max_usd)
    while True:
        state = dict(intent=intent.digest_sha256, account=binding, receipt=asdict(receipt))
        atomic_write(state_file, json.dumps(state).encode())
        print(receipt.status, flush=True)
        if receipt.terminal:
            break
        time.sleep(5)
        receipt = provider.retrieve(receipt)
    if receipt.status != "completed":
        parser.exit(1, "Generation ended without a video.\n")
    with NamedTemporaryFile(dir=root, delete=False) as scratch:
        path = Path(scratch.name)
    try:
        with httpx.stream("GET", receipt.candidate_urls[0], timeout=120) as response:
            response.raise_for_status()
            with path.open("wb") as file:
                for chunk in response.iter_bytes():
                    file.write(chunk)
        os.replace(path, root / "shot.mp4")
    finally:
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
