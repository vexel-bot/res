"""CPU/media/transport acceptance. These tests do not run or qualify an ML model."""

import ast
import hashlib
import json
import math
import shutil
import sys
import tempfile
import threading
import time
import unittest
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

WORKER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKER))

import api as service  # noqa: E402
import runner  # noqa: E402
from clean_audio import patched_demo  # noqa: E402
from protocol import PROFILE, AvatarExecutionRequest, request_digest  # noqa: E402


def metadata(image=b"image", audio=b"speech", **overrides):
    payload = {
        "schemaVersion": "studio.avatar-video-request.v2",
        "profileId": PROFILE,
        "operation": "image_audio_to_avatar",
        "width": 832,
        "height": 480,
        "fps": 25,
        "referenceImageChecksumSha256": hashlib.sha256(image).hexdigest(),
        "drivingAudioChecksumSha256": hashlib.sha256(audio).hexdigest(),
        "drivingAudioDurationMs": 1000,
        "performanceDirection": "Plano médio com fala calma.",
        "seed": 123,
        "script": "Uma ideia.",
    }
    payload.update(overrides)
    return {
        "execution_id": "avatar-fixture-001",
        "profile_id": PROFILE,
        "avatar_request": payload,
        "request_digest_sha256": request_digest(payload),
        "reference_image_checksum_sha256": hashlib.sha256(image).hexdigest(),
        "driving_audio_checksum_sha256": hashlib.sha256(audio).hexdigest(),
        "segment_count": 1,
        "produced_frames": 93,
        "trim_tail_ms": 2720,
    }


class ProtocolTests(unittest.TestCase):
    def test_exact_upstream_patch_removes_separator_and_preserves_input_audio(self):
        source = (WORKER / "tests/fixtures/upstream_demo.py.txt").read_bytes()
        patched = patched_demo(source)
        ast.parse(patched)
        self.assertNotIn("from audio_separator", patched)
        self.assertNotIn("os.remove(temp_vocal_path)", patched)
        self.assertIn("global_seed = int(input_data['seed'])", patched)
        self.assertIn("temp_vocal_path = raw_speech_path", patched)
        self.assertIn("pipe.generate_avc(", patched)
        with self.assertRaisesRegex(ValueError, "source_mismatch"):
            patched_demo(source + b"\n")

    def test_protocol_rejects_digest_parameters_checksums_and_timing_changes(self):
        original = metadata()
        self.assertEqual(
            AvatarExecutionRequest.model_validate(original).avatar_request["seed"], 123
        )
        for field, value in [
            ("seed", True),
            ("fps", 30),
            ("drivingAudioChecksumSha256", None),
            ("referenceImageChecksumSha256", "f" * 64),
            ("performanceDirection", ""),
        ]:
            changed = {
                **original,
                "avatar_request": {**original["avatar_request"], field: value},
            }
            changed["request_digest_sha256"] = request_digest(changed["avatar_request"])
            with self.subTest(field=field), self.assertRaises(ValueError):
                AvatarExecutionRequest.model_validate(changed)
        for field, value in [
            ("request_digest_sha256", "f" * 64),
            ("segment_count", 2),
            ("trim_tail_ms", 0),
        ]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                AvatarExecutionRequest.model_validate({**original, field: value})


@unittest.skipUnless(
    shutil.which("ffmpeg") and shutil.which("ffprobe"),
    "FFmpeg is required for media acceptance",
)
class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        Image.new("RGB", (64, 96), (12, 190, 60)).save(
            self.root / "reference-image", format="PNG"
        )
        with wave.open(str(self.root / "driving-audio"), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(48000)
            frames = b"".join(
                int(3000 * math.sin(2 * math.pi * 200 * n / 48000)).to_bytes(
                    2, "little", signed=True
                )
                for n in range(48000)
            )
            audio.writeframes(frames)
        self.request = AvatarExecutionRequest.model_validate(
            metadata(
                (self.root / "reference-image").read_bytes(),
                (self.root / "driving-audio").read_bytes(),
            )
        )
        runner.atomic_json(self.root / "request.json", self.request.model_dump())

    def fixture_inference(self, root, request, _source, _models):
        # Color frames stand in for model output; every media operation is real.
        generated = root / "generated"
        generated.mkdir()
        runner.run_process(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=832x480:r=25:d=3.72",
                "-c:v",
                "libx264",
                str(generated / "ai2v_demo_1.mp4"),
            ],
            root=root,
        )

    def test_real_normalization_letterbox_mux_trim_and_output_probe(self):
        result = runner.run(
            self.root, self.root, self.root, inference=self.fixture_inference
        )
        self.assertEqual(result["durationMs"], 1000)
        self.assertEqual(
            result["artifactChecksumSha256"],
            runner.sha256_file(self.root / "artifact.mp4"),
        )
        with Image.open(self.root / "reference.png") as image:
            self.assertEqual(image.size, (832, 480))
            self.assertEqual(image.getpixel((0, 200)), (0, 0, 0))
            self.assertEqual(image.getpixel((416, 200)), (12, 190, 60))
        streams = runner.probe(self.root / "artifact.mp4", "ffprobe")["streams"]
        self.assertEqual({s["codec_type"] for s in streams}, {"audio", "video"})
        self.assertEqual(
            next(s for s in streams if s["codec_type"] == "audio")["sample_rate"],
            "48000",
        )
        with wave.open(str(self.root / "clean-speech.wav"), "rb") as normalized:
            self.assertEqual(normalized.getframerate(), 16000)
        self.assertTrue(all(abs(float(s["duration"]) - 1) <= 0.08 for s in streams))

    def test_changed_inputs_are_rejected_before_inference(self):
        (self.root / "driving-audio").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "input_checksum_mismatch"):
            runner.prepare_media(self.root, self.request, "ffmpeg", "ffprobe")

    def test_wrong_declared_audio_duration_is_rejected(self):
        payload = metadata(
            (self.root / "reference-image").read_bytes(),
            (self.root / "driving-audio").read_bytes(),
            drivingAudioDurationMs=2000,
        )
        payload["trim_tail_ms"] = 1720
        with self.assertRaisesRegex(ValueError, "input_duration_mismatch"):
            runner.prepare_media(
                self.root,
                AvatarExecutionRequest.model_validate(payload),
                "ffmpeg",
                "ffprobe",
            )

    def test_cancelled_and_timed_out_processes_are_stopped(self):
        timer = threading.Timer(0.3, lambda: (self.root / "cancel").touch())
        timer.start()
        self.addCleanup(timer.cancel)
        with self.assertRaises(InterruptedError):
            runner.run_process(
                [sys.executable, "-c", "import time;time.sleep(30)"], root=self.root
            )
        (self.root / "cancel").unlink()
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            runner.run_process(
                [sys.executable, "-c", "import time;time.sleep(30)"],
                root=self.root,
                timeout=0.2,
            )
        self.assertLess(time.monotonic() - start, 8)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "runs"
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(lambda: self.executor.shutdown(wait=True))
        self.contexts = [
            patch.dict(
                "os.environ",
                {
                    "LONGCAT_RUN_ROOT": str(self.root),
                    "LONGCAT_MODEL_ROOT": str(self.root / "models"),
                    "LONGCAT_SOURCE_ROOT": str(self.root / "source"),
                },
            ),
            patch.object(service, "TOKEN", "test-only-token"),
            patch.object(service, "_executor", self.executor),
            patch.object(service, "_futures", {}),
        ]
        for context in self.contexts:
            context.start()
            self.addCleanup(context.stop)
        self.client = TestClient(service.app)
        self.addCleanup(self.client.close)
        self.headers = {"Authorization": "Bearer test-only-token"}
        self.calls = 0

    def submit(self, payload=None, image=b"image", audio=b"speech", headers=None):
        return self.client.post(
            "/api/v1/executions",
            headers=self.headers if headers is None else headers,
            data={"metadata": json.dumps(payload or metadata())},
            files={
                "reference_image": ("image", image),
                "driving_audio": ("audio", audio),
            },
        )

    def fake_run(self, root, _source, _models):
        self.calls += 1
        (root / "generated").mkdir()
        (root / "generated" / "private-frame").write_bytes(b"private-frame")
        (root / "runner.log").write_text("private model diagnostics")
        (root / "artifact.mp4").write_bytes(b"transport-test-only")
        return {
            "artifactChecksumSha256": runner.sha256_file(root / "artifact.mp4"),
            "durationMs": 1000,
        }

    def test_unauthorized_and_unavailable_requests_do_not_create_job_files(self):
        self.assertEqual(self.submit(headers={}).status_code, 401)
        response = self.submit()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["status"], "blocked_resources")
        self.assertFalse(self.root.exists())
        self.assertEqual(self.client.get("/api/v1/lifecycle").status_code, 401)
        policy = self.client.get("/api/v1/lifecycle", headers=self.headers).json()
        self.assertTrue(policy["authenticatedDeletion"])
        self.assertTrue(policy["removeInputsAfterExecution"])
        self.assertEqual(policy["retention"]["artifactTtlSeconds"], 3600)

    def test_lifecycle_duplicate_replay_conflict_and_authenticated_artifact(self):
        with (
            patch.object(service, "evaluate", return_value={"usableNow": True}),
            patch.object(service, "run", self.fake_run),
        ):
            response = self.submit()
            self.assertEqual(response.status_code, 202, response.text)
            service._futures["avatar-fixture-001"].result(timeout=5)
            result = self.client.get(
                "/api/v1/executions/avatar-fixture-001", headers=self.headers
            ).json()
            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(
                {entry.name for entry in (self.root / "avatar-fixture-001").iterdir()},
                {"receipt.json", "artifact.mp4"},
            )
            self.assertEqual(self.submit().json()["status"], "succeeded")
            self.assertEqual(self.calls, 1)
            self.assertEqual(self.submit(metadata(seed=999)).status_code, 409)
            path = "/api/v1/executions/avatar-fixture-001/artifact"
            self.assertEqual(self.client.get(path).status_code, 401)
            self.assertEqual(
                self.client.get(path, headers=self.headers).content,
                b"transport-test-only",
            )
            (self.root / "avatar-fixture-001/artifact.mp4").write_bytes(b"changed")
            self.assertEqual(
                self.client.get(path, headers=self.headers).status_code, 409
            )

    def test_failed_upload_cleans_partial_files_and_allows_correct_retry(self):
        with (
            patch.object(service, "evaluate", return_value={"usableNow": True}),
            patch.object(service, "run", self.fake_run),
        ):
            response = self.submit(image=b"wrong")
            self.assertEqual(response.status_code, 422, response.text)
            self.assertFalse((self.root / "avatar-fixture-001").exists())
            self.assertEqual(self.submit().status_code, 202)
            service._futures["avatar-fixture-001"].result(timeout=5)

    def test_running_cancellation_and_restart_receipts(self):
        started = threading.Event()

        def wait_for_cancel(root, _source, _models):
            started.set()
            deadline = time.monotonic() + 5
            while not (root / "cancel").exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            raise InterruptedError()

        with (
            patch.object(service, "evaluate", return_value={"usableNow": True}),
            patch.object(service, "run", wait_for_cancel),
        ):
            self.assertEqual(self.submit().status_code, 202)
            self.assertTrue(started.wait(2))
            path = "/api/v1/executions/avatar-fixture-001"
            self.assertEqual(
                self.client.post(path + "/cancel", headers=self.headers).status_code,
                200,
            )
            service._futures["avatar-fixture-001"].result(timeout=5)
            self.assertEqual(
                self.client.get(path, headers=self.headers).json()["status"],
                "cancelled",
            )
            self.assertEqual(
                self.client.get(path + "/artifact", headers=self.headers).status_code,
                409,
            )
        other = self.root / "interrupted-001"
        other.mkdir()
        runner.atomic_json(other / "receipt.json", {"status": "running"})
        service.recover_interrupted()
        self.assertEqual(service.read_receipt(other)["errorCode"], "worker_restarted")

    def test_authenticated_deletion_removes_media_and_retains_only_a_minimal_receipt(
        self,
    ):
        with (
            patch.object(service, "evaluate", return_value={"usableNow": True}),
            patch.object(service, "run", self.fake_run),
        ):
            self.assertEqual(self.submit().status_code, 202)
            service._futures["avatar-fixture-001"].result(timeout=5)
            path = "/api/v1/executions/avatar-fixture-001"
            self.assertEqual(self.client.delete(path).status_code, 401)
            response = self.client.delete(path, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["status"], "deleted")
            self.assertNotIn("artifactChecksumSha256", response.json())
            self.assertNotIn("durationMs", response.json())
            self.assertEqual(
                self.client.delete(path, headers=self.headers).json(), response.json()
            )
            self.assertEqual(self.submit().status_code, 410)
            self.assertEqual(
                self.client.get(path + "/artifact", headers=self.headers).status_code,
                409,
            )
            self.assertEqual(
                {p.name for p in (self.root / "avatar-fixture-001").iterdir()},
                {"receipt.json"},
            )

    def test_running_deletion_waits_for_inference_to_stop_before_removing_its_inputs(
        self,
    ):
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def inference(root, _source, _models):
            started.set()
            release.wait(5)
            self.assertTrue((root / "reference-image").is_file())
            raise InterruptedError()

        with (
            patch.object(service, "evaluate", return_value={"usableNow": True}),
            patch.object(service, "run", inference),
        ):
            self.assertEqual(self.submit().status_code, 202)
            self.assertTrue(started.wait(2))
            path = "/api/v1/executions/avatar-fixture-001"
            response = self.client.delete(path, headers=self.headers)
            self.assertEqual(response.status_code, 202)
            self.assertTrue(response.json()["deletionRequested"])
            directory = self.root / "avatar-fixture-001"
            self.assertTrue((directory / "cancel").is_file())
            self.assertTrue((directory / "reference-image").is_file())
            release.set()
            service._futures["avatar-fixture-001"].result(timeout=5)
            self.assertEqual(service.read_receipt(directory)["status"], "deleted")
            self.assertEqual({p.name for p in directory.iterdir()}, {"receipt.json"})

    def test_expired_artifact_is_denied_before_download_and_tombstone_eventually_expires(
        self,
    ):
        with (
            patch.object(service, "evaluate", return_value={"usableNow": True}),
            patch.object(service, "run", self.fake_run),
        ):
            self.assertEqual(self.submit().status_code, 202)
            service._futures["avatar-fixture-001"].result(timeout=5)
        directory = self.root / "avatar-fixture-001"
        expiry = service.read_receipt(directory)["finishedAtUnix"] + 3601
        with patch.object(service.time, "time", return_value=expiry):
            response = self.client.get(
                "/api/v1/executions/avatar-fixture-001/artifact", headers=self.headers
            )
            self.assertEqual(response.status_code, 410)
            self.assertEqual(
                service.read_receipt(directory)["deletionReason"], "expired"
            )
        with patch.object(service.time, "time", return_value=expiry + 86401):
            service.sweep_retention()
        self.assertFalse(directory.exists())

    def test_locked_file_deletion_is_pending_and_retried_without_serving_the_artifact(
        self,
    ):
        with (
            patch.object(service, "evaluate", return_value={"usableNow": True}),
            patch.object(service, "run", self.fake_run),
        ):
            self.assertEqual(self.submit().status_code, 202)
            service._futures["avatar-fixture-001"].result(timeout=5)
        path = "/api/v1/executions/avatar-fixture-001"
        with patch.object(
            service, "cleanup_files", side_effect=PermissionError("locked fixture")
        ):
            self.assertEqual(
                self.client.delete(path, headers=self.headers).status_code, 202
            )
            self.assertEqual(
                self.client.get(path + "/artifact", headers=self.headers).status_code,
                409,
            )
        service.sweep_retention()
        self.assertEqual(
            service.read_receipt(self.root / "avatar-fixture-001")["status"], "deleted"
        )

    def test_interrupted_upload_and_corrupt_receipt_are_cleaned_without_touching_unrelated_directories(
        self,
    ):
        for name in ("orphan-upload-001", "corrupt-receipt-001", "unrelated-dir"):
            directory = self.root / name
            directory.mkdir(parents=True)
            (directory / "private-data").write_bytes(b"fixture")
        (self.root / "orphan-upload-001" / ".initializing").touch()
        (self.root / "corrupt-receipt-001" / "receipt.json").write_text("{invalid")
        service.recover_interrupted()
        service.sweep_retention()
        self.assertFalse((self.root / "orphan-upload-001").exists())
        self.assertEqual(
            service.read_receipt(self.root / "corrupt-receipt-001")["status"], "deleted"
        )
        self.assertFalse((self.root / "corrupt-receipt-001" / "private-data").exists())
        self.assertEqual(
            (self.root / "unrelated-dir" / "private-data").read_bytes(), b"fixture"
        )

    def test_missing_execution_handle_does_not_keep_private_inputs_alive(self):
        directory = self.root / "stale-active-001"
        directory.mkdir(parents=True)
        (directory / "reference-image").write_bytes(b"private fixture")
        runner.atomic_json(
            directory / "receipt.json",
            {
                "status": "running",
                "executionId": directory.name,
                "createdAtUnix": time.time() - 10801,
            },
        )
        service.sweep_retention()
        self.assertEqual(service.read_receipt(directory)["status"], "deleted")
        self.assertEqual(
            service.read_receipt(directory)["deletionReason"], "execution_missing"
        )
        self.assertFalse((directory / "reference-image").exists())

    def test_cleanup_unlinks_symlinks_without_deleting_their_external_targets(self):
        directory = self.root / "symlink-test-001"
        directory.mkdir(parents=True)
        external = Path(self.temporary.name) / "external-models"
        external.mkdir()
        (external / "model").write_bytes(b"must remain")
        try:
            (directory / "linked-models").symlink_to(external, target_is_directory=True)
            (directory / "generated").mkdir()
            (directory / "generated" / "nested-link").symlink_to(
                external, target_is_directory=True
            )
        except OSError:
            self.skipTest("Symlink creation is unavailable for this Windows user")
        runner.atomic_json(directory / "receipt.json", {"status": "failed"})
        service.cleanup_files(directory, keep_artifact=False)
        self.assertEqual((external / "model").read_bytes(), b"must remain")
        self.assertFalse((directory / "linked-models").exists())

    def test_unbounded_or_invalid_retention_settings_are_rejected(self):
        for value in ("0", "-1", "86401", "invalid"):
            with patch.dict("os.environ", {"LONGCAT_ARTIFACT_TTL_SECONDS": value}):
                with self.assertRaises(ValueError):
                    service.retention_seconds(
                        "LONGCAT_ARTIFACT_TTL_SECONDS", 3600, 86400
                    )

    def test_sweeper_cancels_an_expired_live_execution_before_removing_inputs(self):
        started, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def inference(root, _source, _models):
            started.set()
            release.wait(5)
            self.assertTrue((root / "reference-image").exists())
            raise InterruptedError()

        with (
            patch.object(service, "evaluate", return_value={"usableNow": True}),
            patch.object(service, "run", inference),
        ):
            self.assertEqual(self.submit().status_code, 202)
            self.assertTrue(started.wait(2))
            directory = self.root / "avatar-fixture-001"
            with service._lock:
                receipt = service.read_receipt(directory)
                runner.atomic_json(
                    directory / "receipt.json",
                    {**receipt, "createdAtUnix": time.time() - 10801},
                )
            service.sweep_retention()
            self.assertEqual(
                service.read_receipt(directory)["status"], "cancel_requested"
            )
            self.assertTrue((directory / "reference-image").exists())
            release.set()
            service._futures["avatar-fixture-001"].result(timeout=5)
            self.assertEqual(service.read_receipt(directory)["status"], "deleted")
            self.assertFalse((directory / "reference-image").exists())

    def test_background_sweeper_expires_media_while_the_api_is_running(self):
        with (
            patch.dict("os.environ", {"LONGCAT_SWEEP_INTERVAL_SECONDS": "1"}),
            patch.object(service, "evaluate", return_value={"usableNow": True}),
            patch.object(service, "run", self.fake_run),
            TestClient(service.app),
        ):
            self.assertEqual(self.submit().status_code, 202)
            service._futures["avatar-fixture-001"].result(timeout=5)
            directory = self.root / "avatar-fixture-001"
            with service._lock:
                receipt = service.read_receipt(directory)
                runner.atomic_json(
                    directory / "receipt.json",
                    {**receipt, "finishedAtUnix": time.time() - 3601},
                )
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                with service._lock:
                    deleted = service.read_receipt(directory)["status"] == "deleted"
                if deleted:
                    break
                time.sleep(0.05)
            self.assertTrue(
                deleted, "Background cleanup did not remove the expired media"
            )
            self.assertFalse((directory / "artifact.mp4").exists())


if __name__ == "__main__":
    unittest.main()
