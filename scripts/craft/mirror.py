"""Preserve every upstream branch/tag/history separately from the pinned subtrees.

Run before a controlled update. Fetching a mirror does not change the imported
source trees or sources.lock.json. --bundle produces portable full-history backups.
"""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", action="store_true")
    args = parser.parse_args()
    output = ROOT / ".codex-runtime/craft/upstream"
    output.mkdir(parents=True, exist_ok=True)
    sources = json.loads(
        (ROOT / "workers/craft/sources.lock.json").read_text(encoding="utf-8")
    )["sources"]
    repositories = {source["repository"] for source in sources}
    manifests = []
    for repository in sorted(repositories):
        name = repository.rsplit("/", 1)[1].removesuffix(".git")
        mirror = output / (name + ".git")
        if not mirror.exists():
            subprocess.run(
                ["git", "clone", "--mirror", repository, str(mirror)], check=True
            )
        else:
            actual = subprocess.check_output(
                ["git", "--git-dir", str(mirror), "remote", "get-url", "origin"],
                text=True,
            ).strip()
            if actual != repository:
                raise ValueError("Upstream mirror origin mismatch")
            subprocess.run(
                ["git", "--git-dir", str(mirror), "fetch", "origin", "+refs/*:refs/*"],
                check=True,
            )
        subprocess.run(["git", "--git-dir", str(mirror), "fsck", "--full"], check=True)
        for source in sources:
            if source["repository"] == repository:
                subprocess.run(
                    [
                        "git",
                        "--git-dir",
                        str(mirror),
                        "cat-file",
                        "-e",
                        source["commit"] + "^{commit}",
                    ],
                    check=True,
                )
        refs = subprocess.check_output(
            ["git", "--git-dir", str(mirror), "show-ref"], text=True
        ).splitlines()
        result = {"repository": repository, "refs": refs, "shallow": False}
        if (mirror / "shallow").exists():
            raise ValueError("A shallow mirror cannot preserve full history")
        if args.bundle:
            bundle = output / (name + ".bundle")
            subprocess.run(
                [
                    "git",
                    "--git-dir",
                    str(mirror),
                    "bundle",
                    "create",
                    str(bundle),
                    "--all",
                ],
                check=True,
            )
            subprocess.run(
                ["git", "--git-dir", str(mirror), "bundle", "verify", str(bundle)],
                check=True,
            )
            result["bundleSha256"] = hashlib.sha256(bundle.read_bytes()).hexdigest()
        manifests.append(result)
    (output / "mirrors.json").write_text(
        json.dumps(
            {"schemaVersion": "clicko.craft-mirrors.v1", "repositories": manifests},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
