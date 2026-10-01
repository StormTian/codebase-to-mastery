"""Behavioral checks for reproducible, complete and revision-bound release assets."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path


spec = importlib.util.spec_from_file_location("package_release", Path(__file__).resolve().parents[1] / "scripts/package_release.py")
assert spec and spec.loader
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.run_git("init", "-q")
        self.run_git("config", "user.name", "Release Test")
        self.run_git("config", "user.email", "release-test@example.invalid")
        self.source = {
            "VERSION": "1.0.0\n", "SKILL.md": '---\nname: codebase-to-mastery\nmetadata:\n  version: "1.0.0"\n---\n',
            "LICENSE": "Original fixture license\n", "README.md": "Fixture\n",
            "scripts/build_course.py": "print('fixture')\n", "assets/course-template/base.html": "<html></html>\n",
            "references/learning-kit.md": "Fixture guide\n", "tests/create_demo.py": "# fixture\n",
        }
        for name, content in {**self.source, ".github/workflows/checks.yml": "# maintenance\n", ".gitignore": ".env\n"}.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "Original fixture")
        self.run_git("tag", "v1.0.0")

    def run_git(self, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.STDOUT).decode().strip()

    def test_reproducible_committed_payload_and_checksums(self) -> None:
        (self.repo / "README.md").write_text("uncommitted change", encoding="utf-8")
        (self.repo / ".env").write_text("untracked fixture", encoding="utf-8")
        first, second = self.root / "first", self.root / "second"
        manifest = release.package(self.repo, "HEAD", first, "v1.0.0")
        release.package(self.repo, "HEAD", second, "v1.0.0")
        for path in first.iterdir():
            self.assertEqual(path.read_bytes(), (second / path.name).read_bytes())
        expected = {f"codebase-to-mastery/{name}": content.encode() for name, content in self.source.items()}
        with zipfile.ZipFile(first / "codebase-to-mastery-v1.0.0.zip") as zipped:
            self.assertEqual({name: zipped.read(name) for name in zipped.namelist()}, expected)
        with tarfile.open(first / "codebase-to-mastery-v1.0.0.tar.gz") as archive:
            actual = {}
            for member in archive:
                self.assertTrue(member.isfile())
                self.assertEqual(member.uid, 0)
                stream = archive.extractfile(member)
                assert stream is not None
                actual[member.name] = stream.read()
            self.assertEqual(actual, expected)
        self.assertEqual(manifest["commit"], self.run_git("rev-parse", "HEAD"))
        self.assertEqual(manifest["fileCount"], len(expected))
        self.assertEqual(json.loads((first / "release-manifest.json").read_text()), manifest)
        for line in (first / "SHA256SUMS").read_text().splitlines():
            checksum, filename = line.split("  ")
            self.assertEqual(checksum, hashlib.sha256((first / filename).read_bytes()).hexdigest())
        for item in manifest["files"]:
            self.assertEqual(item["sha256"], hashlib.sha256(expected[f'codebase-to-mastery/{item["path"]}']).hexdigest())

    def test_tag_must_match_version_and_commit(self) -> None:
        with self.assertRaisesRegex(ValueError, "match VERSION"):
            release.package(self.repo, "HEAD", self.root / "bad", "v2.0.0")
        (self.repo / "README.md").write_text("committed update", encoding="utf-8")
        self.run_git("add", "README.md")
        self.run_git("commit", "-qm", "Next commit")
        with self.assertRaisesRegex(ValueError, "packaged commit"):
            release.package(self.repo, "HEAD", self.root / "wrong-commit", "v1.0.0")

    def test_symlink_resource_is_rejected(self) -> None:
        (self.repo / "references/link.md").symlink_to("learning-kit.md")
        self.run_git("add", "references/link.md")
        self.run_git("commit", "-qm", "Symlink fixture")
        with self.assertRaisesRegex(ValueError, "regular files"):
            release.package(self.repo, "HEAD", self.root / "linked")

    def test_existing_assets_are_not_overwritten(self) -> None:
        output = self.root / "existing"
        output.mkdir()
        asset = output / "SHA256SUMS"
        asset.write_text("preserve", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "not overwritten"):
            release.package(self.repo, "HEAD", output)
        self.assertEqual(asset.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
