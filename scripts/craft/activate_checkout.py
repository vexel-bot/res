"""Activate the qualified Craft checkout locally, retaining the primary Git state.

Only the explicitly named primary checkout is changed. Ignored credentials,
databases and uploads stay in place. Late untracked outputs are restored from
the preserved stash, without reviving retired editor code.
"""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from activation_preflight import ROOT, SOURCE, main as preflight


def git(directory, *args):
    result = subprocess.run(["git", "-C", str(directory), *args], capture_output=True, check=True)
    return result.stdout.decode("utf-8", errors="replace").strip()


def main():
    assert SOURCE == Path("C:/Users/edugu/Downloads/res").resolve()
    assert ROOT.resolve() != SOURCE
    if git(ROOT, "status", "--porcelain"):
        raise ValueError("Commit the qualified integration before activation")
    preflight()
    report = json.loads((ROOT / ".codex-runtime/craft/activation-preflight.json").read_text())
    if not report["automaticPromotionSafe"]:
        raise ValueError("Primary source changed or new paths collide; reconcile before activation")
    target = "codex/craft-studios-active"
    refs = git(SOURCE, "for-each-ref", "--format=%(refname)", "refs/heads/" + target)
    if refs:
        raise ValueError("Activation branch already exists; inspect its state before repeating")
    evidence = ROOT / ".codex-runtime/craft" / ("activation-" + uuid4().hex[:12])
    evidence.mkdir()
    index = Path(git(SOURCE, "rev-parse", "--git-path", "index"))
    index = index if index.is_absolute() else SOURCE / index
    assert index.resolve().is_relative_to(SOURCE)
    shutil.copyfile(index, evidence / "primary-index-before-activation")
    previous_branch = git(SOURCE, "branch", "--show-current")
    previous_head = git(SOURCE, "rev-parse", "HEAD")
    qualified_head = git(ROOT, "rev-parse", "HEAD")
    private_data = {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
                    for name in (".env", "nexus.db", "backend/nexus.db") if (SOURCE / name).is_file()}
    git(SOURCE, "stash", "push", "--include-untracked", "--message", "Preserved primary state before Craft activation")
    stash = git(SOURCE, "rev-parse", "stash@{0}")
    backup_branch = "codex/pre-craft-activation-" + evidence.name.removeprefix("activation-")
    git(SOURCE, "branch", backup_branch, stash)
    result = {"sourceCheckout": str(SOURCE), "previousBranch": previous_branch, "previousHead": previous_head,
              "qualifiedHead": qualified_head, "preservedStash": stash, "backupBranch": backup_branch,
              "activeBranch": target, "lateOutputsRestored": 0, "phase": "preserved"}
    result["privateDataChecksumsBefore"] = private_data
    manifest = evidence / "activation.json"
    manifest.write_text(json.dumps(result, indent=2))
    git(SOURCE, "switch", "--create", target, qualified_head)
    result["phase"] = "source_activated"
    manifest.write_text(json.dumps(result, indent=2))
    added = report["addedSinceCapture"]
    if added:
        spec = evidence / "late-outputs.paths"
        spec.write_bytes(b"\0".join(path.encode() for path in added) + b"\0")
        for path in added:
            assert (SOURCE / path).resolve().is_relative_to(SOURCE)
        git(SOURCE, "restore", "--source", stash + "^3", "--worktree",
            "--pathspec-from-file", str(spec), "--pathspec-file-nul")
        result["lateOutputsRestored"] = len(added)
    bundle = SOURCE / "public/craft"
    assert bundle.resolve().is_relative_to(SOURCE)
    if bundle.exists():
        shutil.copytree(bundle, evidence / "previous-browser-bundle")
    shutil.copytree(ROOT / "public/craft", bundle, dirs_exist_ok=True)
    result["phase"] = "source_and_browser_activated"
    result["activeHead"] = git(SOURCE, "rev-parse", "HEAD")
    assert all(hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == digest
               for name, digest in private_data.items()), "A private configuration/database changed during activation"
    result["privateDataChecksumsPreserved"] = True
    manifest.write_text(json.dumps(result, indent=2))
    (ROOT / ".codex-runtime/craft/activation-latest.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"activeBranch": target, "activeHead": result["activeHead"],
                      "lateOutputsRestored": len(added), "backupBranch": backup_branch,
                      "ignoredDataPreserved": True, "browserBundleInstalled": True}))


if __name__ == "__main__":
    main()
