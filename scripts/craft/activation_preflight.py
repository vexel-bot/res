"""Compare the preserved primary checkout with the captured integration baseline.

Read-only: never checks out, stages, commits, removes or copies primary files.
Reports only paths and Git blob identities; no private file contents are printed.
"""

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path("C:/Users/edugu/Downloads/res").resolve()
BASELINE = "2c030185"


def git(directory, *args, input=None):
    result = subprocess.run(["git", "-C", str(directory), *args], input=input, capture_output=True, check=True)
    return result.stdout


def main():
    assert ROOT.resolve() != SOURCE and (SOURCE / ".git").exists()
    baseline = {}
    for entry in git(ROOT, "ls-tree", "-rz", BASELINE).split(b"\0"):
        if entry:
            metadata, path = entry.split(b"\t", 1)
            baseline[path.decode("utf-8")] = metadata.decode().split()[2]
    paths = sorted(set(path.decode("utf-8") for path in
                       git(SOURCE, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0") if path))
    present = []
    for path in paths:
        absolute = (SOURCE / path).resolve()
        if not absolute.is_relative_to(SOURCE):
            raise ValueError("Eligible source path resolves outside the primary checkout")
        if absolute.is_file():
            present.append(path)
    encoded_paths = "\n".join(json.dumps(path, ensure_ascii=False) for path in present) + "\n"
    hashes = git(SOURCE, "hash-object", "--stdin-paths", input=encoded_paths.encode()).decode().splitlines()
    assert len(hashes) == len(present)
    current = dict(zip(present, hashes, strict=True))
    changed = [path for path in baseline if path in current and baseline[path] != current[path]]
    added = sorted(set(current) - set(baseline))
    deleted = sorted(set(baseline) - set(current))
    collisions = [path for path in added if (ROOT / path).exists()]
    result = {"sourceCheckout": str(SOURCE), "integrationCheckout": str(ROOT),
              "sourceHead": git(SOURCE, "rev-parse", "HEAD").decode().strip(),
              "capturedBaseline": git(ROOT, "rev-parse", BASELINE).decode().strip(),
              "eligiblePrimaryFiles": len(current), "capturedFiles": len(baseline),
              "changedSinceCapture": changed, "addedSinceCapture": added, "deletedSinceCapture": deleted,
              "addedPathsCollidingWithIntegration": collisions,
              "automaticPromotionSafe": not changed and not collisions and not deleted}
    output = ROOT / ".codex-runtime/craft/activation-preflight.json"
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"eligiblePrimaryFiles": len(current), "capturedFiles": len(baseline),
                      "changed": len(changed), "added": len(added), "deleted": len(deleted),
                      "automaticPromotionSafe": result["automaticPromotionSafe"]}))


if __name__ == "__main__":
    main()
