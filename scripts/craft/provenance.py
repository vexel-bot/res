"""Inventory full upstream source trees and verify the imported snapshots.

Only packaging/build outputs are excluded from Git, never source files. Running
--write records immutable Git tree/blob identities and SHA-256 inventory digests.
Running without --write checks the saved manifest against the complete sources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "workers/craft/sources.lock.json"
SOURCES = [
    ("photocraft", "a7f26522ff84cd427c8a5d54b0e8ded7b56fb296", "0.7.0"),
    ("filmcraft", "0800a8b0aa4a703ba42172f415b45a61f8d8a5e1", "0.6.0"),
    ("effectcraft", "67434e90388b6dca4417555346fa6850b6f96033", "0.8.0"),
    ("craft-libs", "5c874d51eeb3de70e735c8ce87a59a7dedd47675", "0.1.0"),
    ("craft-fonts", "abb83316d96aa59c1cf64784289e378fe9fa5695", None),
    ("filmcraft-compat", "2c5ba7a72619935f0481f99d59409e0d1844b234", None),
]


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, check=True
    ).stdout


def verify_tracked_snapshot(root: Path, source: dict) -> None:
    expected = {
        f"{source['sourceDirectory']}/{entry['path']}": (entry["mode"], entry["gitBlob"])
        for entry in source["files"]
    }
    listing = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "--stage", "-z", "--", source["sourceDirectory"]]
    ).decode()
    actual = {}
    for line in listing.split("\0"):
        if not line:
            continue
        metadata, path = line.split("\t", 1)
        mode, oid, stage = metadata.split()
        if stage != "0":
            raise ValueError("The source import has unresolved Git conflicts")
        actual[path] = (mode, oid)
    if actual != expected:
        differences = sorted(path for path in actual.keys() | expected.keys()
                             if actual.get(path) != expected.get(path))
        raise ValueError(f"Tracked upstream files/modes differ in {source['name']}: {differences[:8]}")


def inventory(name: str, sha: str, version: str | None) -> dict:
    # The compatibility commit is present in the imported FilmCraft history.
    listing = git("ls-tree", "-r", "-z", sha).split(b"\0")
    files = []
    missing = []
    base = ROOT / "third_party/craft" / name
    for entry in listing:
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        path = raw_path.decode()
        if kind != "blob":
            raise ValueError(f"Unmaterialized gitlink in {name}: {path}")
        if not (base / path).is_file():
            missing.append(path)
        files.append({"path": path, "mode": mode, "gitBlob": blob})
    if missing:
        raise ValueError(f"Incomplete {name} source import: {missing[:8]}")
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    upstream = "filmcraft" if name == "filmcraft-compat" else name
    return {
        "name": name,
        "repository": f"https://github.com/storytold/{upstream}.git",
        "commit": sha,
        "version": version,
        "gitTree": git("rev-parse", f"{sha}^{{tree}}").decode().strip(),
        "sourceDirectory": base.relative_to(ROOT).as_posix(),
        "sourceFileCount": len(files),
        "inventorySha256": hashlib.sha256(canonical).hexdigest(),
        "files": files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        manifest = {
            "schemaVersion": "clicko.craft-sources.v1",
            "rustToolchain": "1.95.0",
            "wasmBindgenVersion": "0.2.129",
            "sources": [inventory(*source) for source in SOURCES],
        }
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        DESTINATION.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    else:
        # A CI checkout need not fetch the original upstream histories. Verify
        # every normalized source blob against their audited immutable inventory.
        manifest = json.loads(DESTINATION.read_text(encoding="utf-8"))
        pins = {name: sha for name, sha, _version in SOURCES}
        if {source["name"]: source["commit"] for source in manifest["sources"]} != pins:
            raise SystemExit(
                "Craft source manifest differs from the pinned complete revisions"
            )
        for source in manifest["sources"]:
            verify_tracked_snapshot(ROOT, source)
            files = source["files"]
            canonical = json.dumps(
                files, sort_keys=True, separators=(",", ":")
            ).encode()
            if hashlib.sha256(canonical).hexdigest() != source["inventorySha256"]:
                raise SystemExit(f"Changed immutable inventory for {source['name']}")
            paths = [f"{source['sourceDirectory']}/{entry['path']}" for entry in files]
            missing = [path for path in paths if not (ROOT / path).is_file()]
            if missing:
                raise SystemExit(f"Missing upstream sources: {missing[:8]}")
            hashes = (
                subprocess.run(
                    ["git", "-C", str(ROOT), "hash-object", "--stdin-paths"],
                    input=("\n".join(paths) + "\n").encode(),
                    capture_output=True,
                    check=True,
                )
                .stdout.decode()
                .splitlines()
            )
            changed = [
                entry["path"]
                for entry, actual in zip(files, hashes, strict=True)
                if entry["gitBlob"] != actual
            ]
            if changed:
                raise SystemExit(
                    f"Changed upstream sources in {source['name']}: {changed[:8]}"
                )
    for source in manifest["sources"]:
        print(
            f"{source['name']}: {source['sourceFileCount']} complete upstream files @ {source['commit']}"
        )


if __name__ == "__main__":
    main()
