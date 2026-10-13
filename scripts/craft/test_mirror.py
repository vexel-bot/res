"""Integrity regressions against real temporary Git repositories, without network."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from mirror import git, refs_from_lines, verify_bundle, verify_complete


class FullMirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "source"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        for version in ("first", "second"):
            (self.repo / "source.txt").write_text(version)
            subprocess.run(["git", "-C", str(self.repo), "add", "source.txt"], check=True)
            subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Audit", "-c", "user.email=audit@localhost",
                            "commit", "-qm", version], check=True)
        subprocess.run(["git", "-C", str(self.repo), "tag", "reference"], check=True)
        self.mirror = self.root / "mirror.git"
        subprocess.run(["git", "clone", "-q", "--mirror", str(self.repo), str(self.mirror)], check=True)

    def test_portable_bundle_restores_all_refs_and_history(self):
        verify_complete(self.mirror)
        bundle = self.root / "full.bundle"
        git(self.mirror, "bundle", "create", str(bundle), "--all")
        refs = refs_from_lines(git(self.mirror, "show-ref"))
        result = verify_bundle(self.mirror, bundle, refs)
        self.assertEqual(len(result["bundleSha256"]), 64)
        restored = self.root / "restored.git"
        subprocess.run(["git", "clone", "-q", "--mirror", str(bundle), str(restored)], check=True)
        verify_complete(restored)
        self.assertEqual(refs_from_lines(git(restored, "show-ref")), refs)
        self.assertEqual(git(restored, "rev-list", "--all", "--count"), "2")

    def test_shallow_and_promisor_clones_are_rejected(self):
        shallow = self.root / "shallow.git"
        subprocess.run(["git", "clone", "-q", "--bare", "--depth=1", self.repo.as_uri(), str(shallow)], check=True)
        with self.assertRaisesRegex(ValueError, "shallow"):
            verify_complete(shallow)
        git(self.mirror, "config", "remote.origin.promisor", "true")
        with self.assertRaisesRegex(ValueError, "partial/promisor"):
            verify_complete(self.mirror)

    def test_external_object_storage_is_rejected(self):
        alternates = self.mirror / "objects/info/alternates"
        alternates.write_text(str(self.repo / ".git/objects"))
        with self.assertRaisesRegex(ValueError, "alternates"):
            verify_complete(self.mirror)

    def test_incremental_or_incomplete_bundles_are_rejected(self):
        refs = refs_from_lines(git(self.mirror, "show-ref"))
        incomplete = self.root / "incomplete.bundle"
        git(self.mirror, "bundle", "create", str(incomplete), "reference")
        with self.assertRaisesRegex(ValueError, "refs differ"):
            verify_bundle(self.mirror, incomplete, refs)
        incremental = self.root / "incremental.bundle"
        git(self.mirror, "bundle", "create", str(incremental), "HEAD^..HEAD")
        with self.assertRaisesRegex(ValueError, "prerequisites"):
            verify_bundle(self.mirror, incremental, refs)


if __name__ == "__main__":
    unittest.main()
