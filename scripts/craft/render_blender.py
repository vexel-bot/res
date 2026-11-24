"""Build and render a Claude-authored Blender scene independently of any Clicko edit."""

import argparse
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.services.studios.craft_blender import availability, build_local, dimensions, render_local


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="A Blender Python script or an existing .blend")
    parser.add_argument("output", type=Path)
    parser.add_argument("--asset", type=Path, action="append", default=[])
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=1280)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--first", type=int, default=1)
    parser.add_argument("--last", type=int, required=True)
    parser.add_argument("--alpha", action="store_true")
    parser.add_argument("--final", action="store_true")
    args = parser.parse_args()
    image = availability()
    if not image:
        parser.error("Build workers/craft/Blender.Dockerfile using the tag clicko-blender:local")
    size = dimensions({"width": args.width, "height": args.height, "fps": args.fps,
                       "startFrame": args.first, "endFrame": args.last, "alpha": args.alpha,
                       "quality": "final" if args.final else "preview"})
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    for asset in args.asset:
        target = root / asset.name
        if target.exists() or asset.name in {"scene.blend", "create.py", "build.py", "render.json", "render.py", "frames"}:
            parser.error("Duplicate or reserved input name: " + asset.name)
        shutil.copyfile(asset, target)
    deadline = time.monotonic() + 1500
    if args.source.suffix.lower() == ".blend":
        shutil.copyfile(args.source, root / "scene.blend")
    else:
        build_local(root, args.source.read_text(encoding="utf-8-sig"), image, deadline)
    print(render_local(root, image, size, deadline))


if __name__ == "__main__":
    main()
