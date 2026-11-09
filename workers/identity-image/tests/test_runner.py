"""Contract/process tests use tiny images and a fake pipeline; never an ML benchmark."""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from PIL import Image  # noqa: E402

from app.domain.studios.appearance_image import (  # noqa: E402
    PROVIDER_VERSION,
    AppearanceImageRequestV1,
    AppearanceModelManifestV1,
    canonical_digest,
    file_digest,
    verify_model_assets,
)
from app.providers.studios.qwen_appearance import QwenAppearanceProvider  # noqa: E402
from app.models import LibraryAsset, StudioIdentityVersion  # noqa: E402
from app.services.studios.project_appearance import plan_project_appearance  # noqa: E402
from scripts import download_appearance_model_assets as downloader  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "qwen_appearance_runner", ROOT / "workers/identity-image/runner.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def fixture_models(root):
    original = json.loads(
        (ROOT / "workers/identity-image/model-assets.v1.json").read_text()
    )
    for entry in original["files"]:
        path = root / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"explicit-tiny-model-fixture-not-real-weights")
        entry.update(sizeBytes=path.stat().st_size, checksumSha256=file_digest(path))
    return AppearanceModelManifestV1.model_validate(original)


class AppearanceRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="clicko-appearance-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.models = self.root / "models"
        self.manifest = fixture_models(self.models)
        self.reference, self.source = (
            self.root / "reference.png",
            self.root / "source.png",
        )
        Image.new("RGB", (64, 64), "red").save(self.reference)
        Image.new("RGB", (64, 64), "blue").save(self.source)
        self.request = AppearanceImageRequestV1(
            identity_ref={
                "id": "explicit-synthetic-test-character",
                "version": 2,
                "consentGrantId": None,
            },
            reference_asset_id="test-reference",
            reference_checksum_sha256=file_digest(self.reference),
            source_asset_id="test-scene",
            source_checksum_sha256=file_digest(self.source),
            direction="Personagem em pé no cenário escolhido.",
            width=256,
            height=256,
            inference_steps=2,
        )
        self.output = self.root / "output.png"

    def test_real_model_inventory_and_memory_floor_are_explicit(self):
        manifest = AppearanceModelManifestV1.model_validate_json(
            (ROOT / "workers/identity-image/model-assets.v1.json").read_text()
        )
        status = runner.preflight(
            manifest, self.root / "not-installed", inventory="4096, 4096"
        )
        self.assertEqual(status["weightBytes"], 57699249798)
        self.assertFalse(status["usableForEvaluation"])
        self.assertFalse(status["qualityQualified"])
        self.assertEqual(
            set(status["blockers"]),
            {
                "appearance_weights_not_installed",
                "appearance_single_gpu_memory_insufficient",
            },
        )
        # Two small cards cannot masquerade as one large GPU.
        status = runner.preflight(
            manifest, self.models, inventory="32768,32768\n32768,32768"
        )
        self.assertIn("appearance_single_gpu_memory_insufficient", status["blockers"])

    def test_manifest_path_traversal_duplicate_and_missing_shard_are_rejected(self):
        for mode in ("path", "duplicate", "missing"):
            with self.subTest(mode=mode):
                payload = self.manifest.model_dump(mode="json", by_alias=True)
                if mode == "path":
                    payload["files"][0]["path"] = "../outside"
                elif mode == "duplicate":
                    payload["files"].append(payload["files"][0])
                else:
                    payload["files"] = [
                        f for f in payload["files"] if f["path"] != "vae/config.json"
                    ]
                with self.assertRaises(ValueError):
                    AppearanceModelManifestV1.model_validate(payload)

    def test_every_asset_is_hashed_and_unknown_executable_is_rejected(self):
        self.assertEqual(
            verify_model_assets(self.manifest, self.models),
            canonical_digest(self.manifest),
        )
        (self.models / "model_index.json").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "asset_mismatch"):
            verify_model_assets(self.manifest, self.models)
        (self.models / "injected.py").write_text("not allowed")
        with self.assertRaisesRegex(ValueError, "unmanifested"):
            verify_model_assets(self.manifest, self.models)

    def test_source_checksum_pair_and_dimensions_are_required(self):
        for patch_value in (
            {"source_checksum_sha256": None},
            {"width": 257},
            {"direction": "   "},
        ):
            with self.subTest(patch_value=patch_value), self.assertRaises(ValueError):
                AppearanceImageRequestV1.model_validate(
                    {**self.request.model_dump(), **patch_value}
                )

    def fake_loader(self, cancel=None, wrong_size=False):
        calls = {}

        class Generator:
            def __init__(self, device):
                calls["device"] = device

            def manual_seed(self, seed):
                calls["seed"] = seed
                return self

        def pipeline(**kwargs):
            calls.update(kwargs)
            for index in range(2):
                if cancel:
                    cancel(index)
                kwargs["callback_on_step_end"](None, index, None, {})
            return SimpleNamespace(
                images=[
                    Image.new("RGB", (128, 128) if wrong_size else (256, 256), "green")
                ]
            )

        torch = SimpleNamespace(
            inference_mode=contextlib.nullcontext, Generator=Generator
        )
        return lambda _: (pipeline, torch), calls

    def render(self, **kwargs):
        return runner.render(
            self.request,
            manifest=self.manifest,
            model_root=self.models,
            reference_path=self.reference,
            source_path=self.source,
            output_path=self.output,
            inventory="81920,81920",
            **kwargs,
        )

    def test_worker_binds_both_images_seed_and_output_with_a_fake_pipeline(self):
        loader, calls = self.fake_loader()
        result = self.render(loader=loader)
        self.assertEqual(calls["image"][0].getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(calls["image"][1].getpixel((0, 0)), (0, 0, 255))
        self.assertIn(self.request.direction, calls["prompt"])
        self.assertEqual(calls["seed"], self.request.seed)
        self.assertEqual(result.request_digest_sha256, canonical_digest(self.request))
        self.assertEqual(result.identity_ref, self.request.identity_ref)
        self.assertEqual(result.artifact_checksum_sha256, file_digest(self.output))
        self.assertTrue(result.review_required)
        self.assertFalse(result.quality_qualified)

    def test_cancel_during_steps_and_wrong_dimensions_never_persist(self):
        cancelled = False

        def cancel(_):
            nonlocal cancelled
            cancelled = True

        loader, _ = self.fake_loader(cancel=cancel)
        with self.assertRaises(InterruptedError):
            self.render(loader=loader, cancelled=lambda: cancelled)
        self.assertFalse(self.output.exists())
        loader, _ = self.fake_loader(wrong_size=True)
        with self.assertRaisesRegex(ValueError, "dimensions_mismatch"):
            self.render(loader=loader)
        self.assertFalse(self.output.exists())

    def test_reference_tampering_is_rejected_before_loader(self):
        self.reference.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum_mismatch"):
            self.render(loader=lambda _: self.fail("Must not load a model"))

    def test_absent_weights_fail_before_loading_the_pipeline(self):
        (self.models / "vae/diffusion_pytorch_model.safetensors").unlink()
        with self.assertRaisesRegex(ValueError, "weights_not_installed"):
            self.render(loader=lambda _: self.fail("Must not load a model"))

    def provider(self, mutation="", sleep_seconds=0):
        # Actual subprocess transport, explicit fixture output; no neural model.
        script = self.root / "explicit-process-fixture.py"
        script.write_text(
            """
import argparse, json, os, time
from pathlib import Path
from PIL import Image
from app.domain.studios.appearance_image import *
p=argparse.ArgumentParser()
for name in ('model-root','model-manifest','request','reference','source','output','result','progress','cancel-file'):
    p.add_argument('--'+name)
a=p.parse_args()
assert os.environ.get('APPEARANCE_TEST_SECRET') is None
assert os.environ['HF_HUB_OFFLINE']=='1'
time.sleep(SLEEP)
r=AppearanceImageRequestV1.model_validate_json(Path(a.request).read_text(encoding='utf-8'))
m=AppearanceModelManifestV1.model_validate_json(Path(a.model_manifest).read_text(encoding='utf-8'))
Image.new('RGB',(r.width,r.height),'purple').save(a.output)
result=AppearanceImageResultV1(provider_version=PROVIDER_VERSION,
    request_digest_sha256=canonical_digest(r), model_manifest_digest_sha256=canonical_digest(m),
    identity_ref=r.identity_ref, reference_checksum_sha256=r.reference_checksum_sha256,
    source_checksum_sha256=r.source_checksum_sha256, artifact_checksum_sha256=file_digest(Path(a.output)),
    width=r.width,height=r.height,wall_seconds=0.1)
payload=result.model_dump(mode='json',by_alias=True)
MUTATE
Path(a.result).write_text(json.dumps(payload))
""".replace("SLEEP", str(sleep_seconds)).replace("MUTATE", mutation),
            encoding="utf-8",
        )
        manifest = self.root / "manifest.json"
        manifest.write_text(
            self.manifest.model_dump_json(by_alias=True), encoding="utf-8"
        )
        return QwenAppearanceProvider(
            python_executable=Path(sys.executable),
            runner_path=script,
            runner_digest_sha256=file_digest(script),
            manifest_path=manifest,
            model_root=self.models,
        )

    def test_actual_process_transport_keeps_receipt_and_does_not_inherit_secrets(self):
        provider = self.provider()
        with patch.dict(os.environ, {"APPEARANCE_TEST_SECRET": "must-not-reach-child"}):
            result = provider.generate(
                self.request,
                self.reference,
                self.source,
                self.output,
                lambda _: None,
                lambda: False,
            )
        self.assertEqual(result.provider_version, PROVIDER_VERSION)
        self.assertEqual(result.artifact_checksum_sha256, file_digest(self.output))

    def test_process_receipt_tampering_does_not_persist_output(self):
        for field in (
            "identityRef",
            "requestDigestSha256",
            "modelManifestDigestSha256",
            "sourceChecksumSha256",
        ):
            with self.subTest(field=field):
                provider = self.provider(mutation=f"payload[{field!r}] = 'wrong'")
                with self.assertRaises(ValueError):
                    provider.generate(
                        self.request,
                        self.reference,
                        self.source,
                        self.output,
                        lambda _: None,
                        lambda: False,
                    )
                self.assertFalse(self.output.exists())

    def test_process_cancel_and_timeout_do_not_leave_output_or_a_live_child(self):
        for timeout in (False, True):
            provider = self.provider(sleep_seconds=30)
            provider.timeout_seconds = 0.2 if timeout else 10
            checks = 0

            def cancelled():
                nonlocal checks
                checks += 1
                return not timeout and checks > 2

            started, start = [], subprocess.Popen

            def launch(*args, **kwargs):
                child = start(*args, **kwargs)
                started.append(child)
                return child

            with patch(
                "app.providers.studios.qwen_appearance.subprocess.Popen",
                side_effect=launch,
            ):
                with self.assertRaises((InterruptedError, TimeoutError)):
                    provider.generate(
                        self.request,
                        self.reference,
                        self.source,
                        self.output,
                        lambda _: None,
                        cancelled,
                    )
            self.assertTrue(started)
            self.assertTrue(all(child.poll() is not None for child in started))
            self.assertFalse(self.output.exists())

    def test_existing_destination_is_preserved(self):
        provider = self.provider()
        self.output.write_bytes(b"existing-private-output")
        with self.assertRaisesRegex(ValueError, "must_be_new"):
            provider.generate(
                self.request,
                self.reference,
                self.source,
                self.output,
                lambda _: None,
                lambda: False,
            )
        self.assertEqual(self.output.read_bytes(), b"existing-private-output")

    def test_project_plan_binds_selected_appearance_scene_and_cast(self):
        identity = {"id": "identity-1", "version": 2, "consentGrantId": "grant-1"}
        voice = {"id": "voice-1", "version": 1, "consentGrantId": "voice-grant"}
        refs = {"identity": identity, "voice": voice}
        portrait = SimpleNamespace(
            id="portrait",
            workspace_id="brand",
            lifecycle_status="active",
            storage_key="brand/original/portrait.png",
            storage_backend="local",
            media_type="image/png",
            checksum_sha256="a" * 64,
        )
        scene = SimpleNamespace(
            id="scene",
            workspace_id="brand",
            lifecycle_status="active",
            storage_key="brand/original/scene.png",
            storage_backend="local",
            media_type="image/png",
            checksum_sha256="b" * 64,
        )
        version = SimpleNamespace(
            capabilities=["avatar.generate"], sample_asset_ids=["portrait"]
        )
        records = {
            (LibraryAsset, "portrait"): portrait,
            (LibraryAsset, "scene"): scene,
            (StudioIdentityVersion, "identity-1"): version,
        }
        db = SimpleNamespace(get=lambda model, key, **_: records.get((model, key)))
        row = SimpleNamespace(
            id="project",
            workspace_id="brand",
            payload={
                "format": "image",
                "directionId": "guide",
                "identityVersionId": "identity-1",
                "voiceVersionId": "voice-1",
                "casting": refs,
                "sourceAssetId": "scene",
                "revision": 4,
            },
        )
        with patch(
            "app.services.studios.project_appearance.resolve_cast", return_value=refs
        ):
            plan = plan_project_appearance(db, row, "Aparência na cena escolhida")
            self.assertEqual(plan["request"]["identityRef"], identity)
            self.assertEqual(plan["request"]["sourceAssetId"], "scene")
            self.assertEqual(plan["casting"]["voice"], voice)
            self.assertEqual(len(plan["planDigestSha256"]), 64)
            scene.workspace_id = "other-brand"
            with self.assertRaisesRegex(ValueError, "asset_unavailable"):
                plan_project_appearance(db, row, "Aparência na cena escolhida")
            scene.workspace_id = "brand"
            row.payload["casting"] = {"identity": identity}
            with self.assertRaisesRegex(ValueError, "cast_version_reference_mismatch"):
                plan_project_appearance(db, row, "Aparência na cena escolhida")

    def test_downloader_streams_frozen_bytes_and_reuses_valid_existing_files(self):
        target, calls = self.root / "download", []

        def fetch(url, timeout):
            self.assertEqual(timeout, 60)
            name = url.split(f"/resolve/{self.manifest.model_revision}/", 1)[1]
            calls.append(name)
            return io.BytesIO((self.models / name).read_bytes())

        with (
            patch.object(downloader, "urlopen", side_effect=fetch),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(
                downloader.download(self.manifest, target),
                canonical_digest(self.manifest),
            )
            self.assertEqual(len(calls), len(self.manifest.files))
            downloader.download(self.manifest, target)
            self.assertEqual(len(calls), len(self.manifest.files))

    def test_downloader_rejects_bad_existing_bytes_insufficient_space_and_corrupt_download(
        self,
    ):
        for reason in ("existing", "disk", "corrupt"):
            with self.subTest(reason=reason):
                target = self.root / reason
                if reason == "existing":
                    target.mkdir()
                    (target / self.manifest.files[0].path).write_bytes(b"wrong")
                free = 0 if reason == "disk" else 1024**4
                with patch.object(
                    downloader.shutil,
                    "disk_usage",
                    return_value=SimpleNamespace(free=free),
                ):
                    with patch.object(
                        downloader, "urlopen", return_value=io.BytesIO(b"corrupt")
                    ) as fetch:
                        with self.assertRaises(ValueError):
                            downloader.download(self.manifest, target)
                        if reason != "corrupt":
                            fetch.assert_not_called()
                if reason == "corrupt":
                    self.assertFalse(any(path.is_file() for path in target.rglob("*")))


if __name__ == "__main__":
    unittest.main()
