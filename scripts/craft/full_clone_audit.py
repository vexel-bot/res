"""Prove complete pinned Craft imports, full Git mirrors and portable bundles.

Run mirror.py --bundle first for a fresh comparison with all advertised upstream
refs. This audit is offline and never modifies the upstream sources or documents.
Builds may have extra ignored files; tracked upstream files must match exactly.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tomllib

from mirror import ROOT, git, refs_from_lines, sha256, verify_bundle, verify_complete


def audit(root: Path, mirrors: Path) -> dict:
    manifest = json.loads((root / "workers/craft/sources.lock.json").read_text())
    # Check materialized, normalized blob identities as well as the Git trees.
    subprocess.run([sys.executable, str(root / "scripts/craft/provenance.py")], check=True, cwd=root)
    receipt = json.loads((mirrors / "mirrors.json").read_text())
    if receipt["schemaVersion"] != "clicko.craft-mirrors.v2":
        raise ValueError("Refresh the mirrors with the complete-ref verification first")
    repositories = {item["repository"]: item for item in receipt["repositories"]}
    reports = []
    known_pins = {item["commit"] for item in manifest["sources"]}
    for source in manifest["sources"]:
        directory = root / source["sourceDirectory"]
        name = source["repository"].rsplit("/", 1)[1].removesuffix(".git")
        mirror = mirrors / (name + ".git")
        verify_complete(mirror)
        repo = repositories[source["repository"]]
        refs = refs_from_lines(git(mirror, "show-ref"))
        if refs != refs_from_lines("\n".join(repo["refs"])) or not repo["advertisedRefsMatch"]:
            raise ValueError("Mirror refs changed after the upstream comparison")
        bundle = mirrors / (name + ".bundle")
        bundle_result = verify_bundle(mirror, bundle, refs)
        if bundle_result["bundleSha256"] != repo["bundleSha256"]:
            raise ValueError("Portable bundle differs from its verified receipt")
        if git(mirror, "rev-parse", source["commit"] + "^{tree}") != source["gitTree"]:
            raise ValueError("Pinned source tree differs from the original Git tree")
        files = []
        for line in git(mirror, "ls-tree", "-r", "-z", source["commit"]).split("\0"):
            if not line:
                continue
            metadata, path = line.split("\t", 1)
            mode, kind, oid = metadata.split()
            if kind != "blob":
                raise ValueError(f"Unmaterialized submodule: {source['name']}/{path}")
            files.append({"path": path, "mode": mode, "gitBlob": oid})
        if files != source["files"]:
            raise ValueError("The import inventory omits or changes original source entries")
        indexed = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "--stage", "-z", "--", source["sourceDirectory"]], text=True
        )
        expected = {source["sourceDirectory"] + "/" + f["path"]: (f["mode"], f["gitBlob"]) for f in files}
        actual = {}
        for line in indexed.split("\0"):
            if not line:
                continue
            metadata, path = line.split("\t", 1)
            mode, oid, stage = metadata.split()
            if stage != "0":
                raise ValueError("The source import has unresolved Git conflicts")
            actual[path] = (mode, oid)
        if actual != expected:
            raise ValueError("The tracked import differs from the entire upstream snapshot")
        lfs_pointers = []
        for file in files:
            with (directory / file["path"]).open("rb") as handle:
                if handle.read(128).startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                    lfs_pointers.append(file["path"])
        if lfs_pointers:
            raise ValueError(f"LFS assets must be materialized and audited: {lfs_pointers}")
        lock = tomllib.loads((directory / "Cargo.lock").read_text())
        registry_count = 0
        git_dependencies = set()
        for package in lock["package"]:
            package_source = package.get("source", "")
            if package_source.startswith("registry+"):
                if len(package.get("checksum", "")) != 64:
                    raise ValueError("Registry dependency lacks a locked checksum")
                registry_count += 1
            elif package_source.startswith("git+"):
                commit = package_source.rsplit("#", 1)[1]
                if commit not in known_pins:
                    raise ValueError(f"Git dependency is missing its full source import: {package_source}")
                git_dependencies.add(package_source)
        paths = [f["path"] for f in files]
        counts = {prefix: sum(path.startswith(prefix) for path in paths) for prefix in
                  ("apps/", "crates/", "crates/ui-egui/", "assets/", "docs/", "docs/images/")}
        screenshots = [{"path": source["sourceDirectory"] + "/" + path,
                        "sha256": sha256(directory / path)} for path in paths
                       if path.startswith("docs/images/") and path.endswith((".png", ".jpg", ".webp"))]
        reports.append({key: source[key] for key in ("name", "repository", "commit", "gitTree", "sourceDirectory", "sourceFileCount", "inventorySha256")} |
                       {"snapshotMatchesEntireUpstreamTree": True, "trackedModesAndBlobsMatch": True,
                        "submodules": 0, "unmaterializedLfsPointers": 0,
                        "sourceCategories": counts, "registryDependenciesWithChecksums": registry_count,
                        "gitDependenciesFullyImported": sorted(git_dependencies),
                        "originalInterfaceReferences": screenshots})
    fonts_root = root / "third_party/craft/craft-fonts"
    fonts = []
    for line in (fonts_root / "fonts/manifest.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        family, style, file, scripts, license_name, license_file, expected_sha, origin = [field.strip() for field in line.split("|")]
        if sha256(fonts_root / file) != expected_sha or not (fonts_root / license_file).is_file():
            raise ValueError("An upstream external font or its license is incomplete")
        fonts.append({"family": family, "style": style, "path": file, "sha256": expected_sha, "license": license_name, "source": origin})
    return {"schemaVersion": "clicko.craft-full-clone-audit.v1",
            "auditedAt": datetime.now(timezone.utc).isoformat(), "upstreamRefsVerifiedAt": receipt["verifiedAt"],
            "scope": "Complete pinned source trees and all advertised Git refs/history; compiled GUIs and feature parity are qualified separately",
            "totalSourceFiles": sum(s["sourceFileCount"] for s in reports), "sources": reports,
            "repositories": [{k: v for k, v in repo.items() if k != "refs"} for repo in repositories.values()],
            "externalFontsVerified": fonts,
            "sharedOriginalInterface": "third_party/craft/craft-libs/crates/ui",
            "visualRedesignStarted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mirrors", type=Path, default=ROOT / ".codex-runtime/craft/upstream")
    parser.add_argument("--output", type=Path, default=ROOT / ".codex-runtime/craft/full-clone-audit.json")
    args = parser.parse_args()
    report = audit(ROOT, args.mirrors.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Verified {report['totalSourceFiles']} complete source files, {len(report['repositories'])} full mirrors/bundles, and {len(report['externalFontsVerified'])} external fonts")


if __name__ == "__main__":
    main()
