"""Blender authoring inside a job-scoped container and import into the native edit."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from uuid import uuid4

from ...domain.studios.editing_resources import ResourceMetadataV1
from ...models import LibraryAsset
from ..object_storage import get_object_storage, sha256_file
from .craft import scoped_asset, write_asset
from .craft_direction import stage_material
from .editing_resources import analysis_only, store_resource

BLEND = "application/x-blender"
SCENE_ENTRY = """
import bpy, pathlib
bpy.ops.wm.read_factory_settings(use_empty=True) if not bpy.data.filepath else None
exec(compile(pathlib.Path('/job/create.py').read_bytes(), 'clicko_scene.py', 'exec'),
     {'__name__': '__main__'})
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath='/job/scene.blend', compress=False)
"""
RENDER_ENTRY = """
import bpy, json
from pathlib import Path
s = bpy.context.scene
p = json.loads(Path('/job/render.json').read_text())
s.render.resolution_x, s.render.resolution_y = p['width'], p['height']
s.render.resolution_percentage = 100
s.render.fps, s.render.fps_base = p['fps'], 1
s.render.film_transparent = p['alpha']
s.render.image_settings.file_format = 'PNG'
s.render.image_settings.color_mode = 'RGBA' if p['alpha'] else 'RGB'
s.render.threads_mode, s.render.threads = 'FIXED', 2
if s.render.engine == 'CYCLES':
    s.cycles.device = 'CPU'
    s.cycles.samples = min(s.cycles.samples, p['samples'])
for f in range(s.frame_start, p['endFrame'] + 1):
    s.frame_set(f)
    if f < p['startFrame']:
        continue
    output = Path('/job/frames') / ('%06d.png' % f)
    if not output.exists():
        s.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
"""


def configured_image():
    return os.getenv("CLICKO_BLENDER_IMAGE", "clicko-blender:local")


def availability():
    try:
        result = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", configured_image()],
                                capture_output=True, text=True, timeout=12, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    digest = result.stdout.strip()
    return digest if digest.startswith("sha256:") else None


def run_blender(root, image, entry, deadline, *, source=None):
    name = f"clicko-blender-{uuid4().hex}"
    command = [
        "docker", "run", "--rm", "--pull=never", "--name", name,
        "--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--memory=1800m", "--cpus=2", "--pids-limit=160", "--user=65534:65534",
        "--tmpfs=/tmp:rw,nosuid,size=256m", "--mount", f"type=bind,source={root},target=/job",
        "--workdir=/job", image, "-b", "--disable-autoexec", "--python-exit-code", "12",
    ]
    if source:
        command.append("/job/" + source)
    command.extend(["-P", "/job/" + entry])
    if os.name != "nt":
        # The mounted workspace belongs to the host worker. Use the same
        # unprivileged numeric user when the worker itself is unprivileged.
        if os.getuid() != 0:
            command[command.index("--user=65534:65534")] = f"--user={os.getuid()}:{os.getgid()}"
        else:
            root.chmod(0o777)
    try:
        with tempfile.TemporaryFile() as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=min(900, max(1, deadline - time.monotonic())))
            if result.returncode:
                log.seek(max(0, log.seek(0, 2) - 2400))
                detail = log.read().decode("utf-8", errors="replace").strip()
                raise ValueError("craft_blender_failed: " + detail)
    except subprocess.TimeoutExpired as error:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15, check=False)
        raise ValueError("craft_blender_timeout") from error


def copy_asset(db, record, asset_id, destination):
    asset = scoped_asset(db, record.workspace_id, asset_id)
    if analysis_only(asset) or (asset.object_metadata or {}).get("rightsStatus") == "restricted":
        raise ValueError("craft_analysis_asset_not_production")
    if asset.size_bytes > 100 * 1024 * 1024:
        raise ValueError("craft_blender_input_too_large")
    with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
        if sha256_file(source) != asset.checksum_sha256:
            raise ValueError("craft_asset_checksum_mismatch")
        shutil.copyfile(source, destination)
    return asset


def create_scene(db, record, job, draft, args, image):
    script = args["script"]
    if not isinstance(script, str) or not 1 <= len(script) <= 30000:
        raise ValueError("craft_blender_script_invalid")
    inputs = args.get("assetIds", [])
    if not isinstance(inputs, list) or len(inputs) > 12:
        raise ValueError("craft_blender_inputs_invalid")
    parent = None
    with tempfile.TemporaryDirectory(prefix="clicko-blend-") as folder:
        root = Path(folder)
        if args.get("baseSceneId"):
            parent = copy_asset(db, record, args["baseSceneId"], root / "base.blend")
            if parent.media_type != BLEND:
                raise ValueError("craft_blender_scene_required")
        for identifier in inputs:
            asset = scoped_asset(db, record.workspace_id, identifier)
            suffix = Path(asset.storage_key).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".glb", ".hdr"}:
                raise ValueError("craft_blender_input_format_invalid")
            copy_asset(db, record, identifier, root / (asset.id + suffix))
        receival = {"base": parent.checksum_sha256 if parent else None, "inputs": sorted(inputs),
                     "script": hashlib.sha256(script.encode()).hexdigest(), "build": image}
        key = hashlib.sha256(json.dumps(receival, sort_keys=True).encode()).hexdigest()
        previous = (job.result_payload or {}).get("blenderScenes", {})
        if key in previous:
            return previous[key]
        path = build_local(root, script, image, draft.deadline, base="base.blend" if parent else None)
        asset, _, _ = write_asset(db, record, path, suffix=".blend", media_type=BLEND,
                                  asset_type="document", metadata={"craftBlenderScene": receival},
                                  title=args.get("label", "Cena Blender")[:120])
        db.flush()
        info = {"sceneId": asset.id, "checksumSha256": asset.checksum_sha256, "providerChargeUsd": 0,
                "instruction": "Use this scene ID for render_blender_shot or as baseSceneId for a revision."}
        job.result_payload = {**job.result_payload, "blenderScenes": {**previous, key: info}}
        db.commit()
        return info


def build_local(root, script, image, deadline, *, base=None):
    """Author an editable scene without loading an EffectCraft project."""
    (root / "create.py").write_text(script, encoding="utf8")
    (root / "build.py").write_text(SCENE_ENTRY, encoding="utf8")
    run_blender(root, image, "build.py", deadline, source=base)
    path = root / "scene.blend"
    if path.is_symlink() or not path.is_file() or not 12 < path.stat().st_size <= 100 * 1024 * 1024:
        raise ValueError("craft_blender_scene_output_invalid")
    with path.open("rb") as opened:
        if opened.read(7) != b"BLENDER":
            raise ValueError("craft_blender_scene_output_invalid")
    return path


def dimensions(args):
    result = {key: args[key] for key in ("width", "height", "fps", "startFrame", "endFrame")}
    if any(type(value) is not int for value in result.values()):
        raise ValueError("craft_blender_render_range_invalid")
    w, h, fps, start, end = result.values()
    if not (32 <= w <= 1920 and 32 <= h <= 1920 and w % 2 == h % 2 == 0
            and 12 <= fps <= 60 and 1 <= start <= end <= 1800 and end - start < 480):
        raise ValueError("craft_blender_render_range_invalid")
    alpha = args.get("alpha", False)
    quality = args.get("quality", "preview")
    if type(alpha) is not bool or quality not in {"preview", "final"}:
        raise ValueError("craft_blender_render_options_invalid")
    return {**result, "alpha": alpha, "samples": 12 if quality == "preview" else 64, "quality": quality}


def render_shot(db, record, job, user, draft, manifests, args, image):
    settings = dimensions(args)
    scene = scoped_asset(db, record.workspace_id, args["sceneId"])
    if scene.media_type != BLEND:
        raise ValueError("craft_blender_scene_required")
    key = hashlib.sha256(json.dumps([scene.checksum_sha256, image, settings], sort_keys=True).encode()).hexdigest()
    acquisition = "blender:" + key
    previous = (job.result_payload or {}).get("acquiredSources", {}).get(acquisition)
    if previous:
        return previous
    root = draft.directory / "blender" / key
    root.mkdir(parents=True, exist_ok=True)
    copy_asset(db, record, scene.id, root / "scene.blend")
    path = render_local(root, image, settings, draft.deadline)
    asset = store_resource(db, record.workspace_id, args.get("label", "Plano Blender")[:120], path,
                           ResourceMetadataV1(kind="video", usageEvidence="Cena original criada nesta edição."),
                           user.id, provenance={"craftBlenderSource": {"assetId": scene.id, "settings": settings}})
    seconds = (settings["endFrame"] - settings["startFrame"] + 1) / settings["fps"]
    return stage_material(db, job, draft, manifests, asset, acquisition, {
        "assetId": asset.id, "mediaType": asset.media_type, "sceneId": scene.id, "durationSeconds": seconds,
        "settings": settings, "providerChargeUsd": 0,
    })


def render_local(root, image, settings, deadline):
    """Render the scene in this folder and return a standalone media file."""
    frames = root / "frames"
    frames.mkdir(exist_ok=True)
    if os.name != "nt" and os.getuid() == 0:
        frames.chmod(0o777)
    (root / "render.json").write_text(json.dumps(settings), encoding="utf8")
    (root / "render.py").write_text(RENDER_ENTRY, encoding="utf8")
    run_blender(root, image, "render.py", deadline, source="scene.blend")
    from PIL import Image
    for frame in range(settings["startFrame"], settings["endFrame"] + 1):
        path = frames / f"{frame:06d}.png"
        if path.is_symlink() or not path.is_file():
            raise ValueError("craft_blender_frame_missing")
        with Image.open(path) as picture:
            if (picture.size != (settings["width"], settings["height"])
                    or settings["alpha"] and picture.mode != "RGBA"):
                raise ValueError("craft_blender_frame_invalid")
            picture.verify()
    alpha = settings["alpha"]
    path = root / ("shot.webm" if alpha else "shot.mp4")
    try:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-framerate", str(settings["fps"]), "-start_number",
             str(settings["startFrame"]), "-i", str(frames / "%06d.png"),
             "-frames:v", str(settings["endFrame"] - settings["startFrame"] + 1), "-an",
             *(["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0"] if alpha else
               ["-c:v", "libx264", "-pix_fmt", "yuv420p"]), "-threads", "2", str(path)],
            check=True, capture_output=True, timeout=min(180, max(1, deadline - time.monotonic())),
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("craft_blender_encode_failed") from error
    return path
