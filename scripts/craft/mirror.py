"""Preserve every upstream branch/tag/history separately from the pinned subtrees.

Run before a controlled update. Fetching a mirror does not change the imported
source trees or sources.lock.json. --bundle produces portable full-history backups.
"""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(mirror: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "--git-dir", str(mirror), *args], text=True
    ).strip()


def refs_from_lines(lines: str) -> dict[str, str]:
    return {ref: oid for oid, ref in (line.split() for line in lines.splitlines())}


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify_complete(mirror: Path) -> None:
    if git(mirror, "rev-parse", "--is-shallow-repository") != "false":
        raise ValueError("A shallow mirror cannot preserve full history")
    config = git(mirror, "config", "--local", "--list").lower()
    if "partialclone" in config or ".promisor=" in config:
        raise ValueError("A partial/promisor clone cannot preserve complete sources")
    if (mirror / "objects/info/alternates").exists():
        raise ValueError("The mirror must own its objects, without external alternates")
    if list((mirror / "objects/pack").glob("*.promisor")):
        raise ValueError("Promised objects cannot replace a complete clone")
    # Unlike connectivity-only checks, this also validates blob contents.
    git(mirror, "fsck", "--full", "--no-dangling")


def verify_bundle(mirror: Path, bundle: Path, refs: dict[str, str]) -> dict:
    git(mirror, "bundle", "verify", str(bundle))
    # Do not depend on Git's translated diagnostic messages.
    with bundle.open("rb") as handle:
        for line in handle:
            if line == b"\n":
                break
            if line.startswith(b"-"):
                raise ValueError("The portable bundle must contain history without prerequisites")
    bundled = refs_from_lines(git(mirror, "bundle", "list-heads", str(bundle)))
    if {ref: oid for ref, oid in bundled.items() if ref != "HEAD"} != refs:
        raise ValueError("Bundle refs differ from the complete mirror")
    return {"bundleSha256": sha256(bundle), "bundleBytes": bundle.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", action="store_true")
    parser.add_argument(
        "--seed-from", type=Path,
        help="Restore missing mirrors from verified full bundles in this directory, then fetch upstream",
    )
    args = parser.parse_args()
    if args.seed_from and not args.bundle:
        parser.error("--seed-from requires --bundle to include any new upstream refs")
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
            seed = args.seed_from / (name + ".bundle") if args.seed_from else None
            subprocess.run(
                ["git", "clone", "--mirror", str(seed) if seed else repository, str(mirror)], check=True
            )
            if seed:
                subprocess.run(
                    ["git", "--git-dir", str(mirror), "remote", "set-url", "origin", repository], check=True
                )
        actual = git(mirror, "remote", "get-url", "origin")
        if actual != repository:
            raise ValueError("Upstream mirror origin mismatch")
        verify_complete(mirror)
        # Retain refs removed upstream as historical evidence. Every currently
        # advertised ref must still match; tolerate only a bounded fetch race.
        for attempt in range(3):
            subprocess.run(
                ["git", "--git-dir", str(mirror), "fetch", "origin", "+refs/*:refs/*"],
                check=True,
            )
            advertised = refs_from_lines(git(mirror, "ls-remote", "--refs", "origin"))
            refs = refs_from_lines(git(mirror, "show-ref"))
            if all(refs.get(ref) == oid for ref, oid in advertised.items()):
                break
        else:
            raise ValueError("Upstream refs changed during three consecutive verification attempts")
        pins = {}
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
                ref = "refs/clicko/pins/" + source["name"]
                subprocess.run(
                    ["git", "--git-dir", str(mirror), "update-ref", ref, source["commit"]], check=True
                )
                pins[source["name"]] = source["commit"]
        verify_complete(mirror)
        refs = refs_from_lines(git(mirror, "show-ref"))
        result = {
            "repository": repository,
            "refs": [f"{oid} {ref}" for ref, oid in sorted(refs.items())],
            "advertisedRefsSha256": hashlib.sha256(json.dumps(advertised, sort_keys=True).encode()).hexdigest(),
            "advertisedRefCount": len(advertised),
            "branches": sum(ref.startswith("refs/heads/") for ref in advertised),
            "tags": sum(ref.startswith("refs/tags/") for ref in advertised),
            "retainedRefCount": len(refs.keys() - advertised.keys()),
            "commitCount": int(git(mirror, "rev-list", "--all", "--count")),
            "pins": pins,
            "shallow": False, "partialClone": False, "externalAlternates": False,
            "fsckFull": "passed", "advertisedRefsMatch": True,
        }
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
            result.update(verify_bundle(mirror, bundle, refs))
        manifests.append(result)
        print(f"{name}: full history, {result['branches']} branches, {result['tags']} tags, {result['commitCount']} commits verified", flush=True)
    (output / "mirrors.json").write_text(
        json.dumps(
            {"schemaVersion": "clicko.craft-mirrors.v2", "verifiedAt": datetime.now(timezone.utc).isoformat(), "repositories": manifests},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
