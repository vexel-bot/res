"""Read back isolated QA deliveries after restart; decode real MP4s and verify hashes.

Uses the same signed service bridge as the in-process governance fixture. It
does not log into the browser or grant a commercial license/session.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import httpx
import jwt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.studios.timeline_ffmpeg import probe, tool  # noqa: E402

OUTPUT = ROOT / (
    ".codex-runtime/stage3-validation"
    if "--stage3" in sys.argv
    else ".codex-runtime/step2-review-validation"
    if "--review" in sys.argv
    else ".codex-runtime/step2-validation"
)
PROFILE = ROOT / ".codex-runtime/stage1-local"


def main():
    status = json.loads(
        subprocess.check_output(
            ["node", "scripts/dev-local.mjs", "status"], cwd=ROOT, text=True
        )
    )
    assert (
        Path(status["dataDirectory"]).resolve() == PROFILE.resolve() and status["ready"]
    )
    evidence = json.loads((OUTPUT / "evidence.json").read_text(encoding="utf-8"))
    assert Path(evidence["isolatedProfile"]).resolve() == PROFILE.resolve()
    secret = (PROFILE / "bridge-key").read_text().strip()

    def headers():
        now = datetime.now(UTC)
        return {
            "Authorization": "Bearer "
            + jwt.encode(
                {
                    "iss": "clicko-governance",
                    "aud": "clicko-studios",
                    "type": "studio_bridge",
                    "sub": "usr-master",
                    "workspaceId": "ws-1",
                    "clientId": None,
                    "module": "create-video",
                    "name": "Isolated governance fixture",
                    "workspaceName": "QA",
                    "role": "Owner",
                    "allowedModules": ["create-video", "create-image"],
                    "iat": now,
                    "exp": now + timedelta(seconds=60),
                },
                secret,
                algorithm="HS256",
            )
        }

    verification = {
        "persisted": False,
        "inference": "none",
        "paidProviderCalls": evidence["paidProviderCalls"],
        "deliveries": {},
    }
    with httpx.Client(base_url="http://127.0.0.1:8018", timeout=30) as client:
        for label, entry in (("v1", evidence["first"]), ("v2", evidence["second"])):
            local = OUTPUT / f"motion-{label}.mp4"
            expected = hashlib.sha256(local.read_bytes()).hexdigest()
            response = client.get(entry["result"]["downloadUrl"], headers=headers())
            response.raise_for_status()
            assert hashlib.sha256(response.content).hexdigest() == expected
            info = probe(local)
            assert abs(float(info["format"]["duration"]) - 15) < 0.1
            video = next(
                stream for stream in info["streams"] if stream["codec_type"] == "video"
            )
            assert (
                video["codec_name"] == "h264"
                and video["width"] == 640
                and video["height"] == 360
            )
            decoded = subprocess.run(
                [tool("ffmpeg"), "-v", "error", "-i", str(local), "-f", "null", "-"],
                capture_output=True,
                timeout=60,
            )
            assert decoded.returncode == 0, decoded.stderr[:400]
            verification["deliveries"][label] = {
                "sha256": expected,
                "durationSeconds": 15,
                "width": 640,
                "height": 360,
                "decoded": True,
            }
        document = client.get(
            "/api/v1/studios/v1/documents/" + evidence["documentId"], headers=headers()
        )
        document.raise_for_status()
        doc = document.json()
        assert doc["revision"] == evidence["revision"]
        assert len(doc["composition"]["pages"][0]["layers"]) == 9
        assert len(doc["composition"]["narrative"]["localProduction"]["scenes"]) == 3
        verification.update(
            persisted=True, revision=doc["revision"], documentId=doc["documentId"]
        )
    extracted = subprocess.run(
        [
            tool("ffmpeg"),
            "-v",
            "error",
            "-y",
            "-ss",
            "1.5",
            "-i",
            str(OUTPUT / "motion-v2.mp4"),
            "-frames:v",
            "1",
            str(OUTPUT / "rendered-frame.png"),
        ],
        capture_output=True,
        timeout=30,
    )
    assert extracted.returncode == 0, extracted.stderr[:400]
    (OUTPUT / "verification.json").write_text(
        json.dumps(verification, indent=2), encoding="utf-8"
    )
    evidence["persistenceAfterRestart"] = True
    (OUTPUT / "evidence.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    print(json.dumps(verification))


if __name__ == "__main__":
    main()
