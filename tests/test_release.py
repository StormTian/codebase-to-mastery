"""Behavioral checks for reproducible, complete and revision-bound release assets."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
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

    def test_root_download_is_excluded_from_skill_archives(self) -> None:
        (self.repo / "codebase-to-mastery.tgz").write_bytes(b"previous distribution artifact")
        self.run_git("add", "codebase-to-mastery.tgz")
        self.run_git("commit", "-qm", "Root download fixture")
        output = self.root / "no-recursion"
        manifest = release.package(self.repo, "HEAD", output)
        self.assertEqual(manifest["fileCount"], len(self.source))
        self.assertIn("codebase-to-mastery.tgz", manifest["excluded"])
        with zipfile.ZipFile(output / "codebase-to-mastery-v1.0.0.zip") as archive:
            self.assertNotIn("codebase-to-mastery/codebase-to-mastery.tgz", archive.namelist())
        with tarfile.open(output / "codebase-to-mastery-v1.0.0.tar.gz") as archive:
            self.assertNotIn("codebase-to-mastery/codebase-to-mastery.tgz", archive.getnames())

    def test_npm_metadata_version_mismatch_is_rejected(self) -> None:
        (self.repo / "package.json").write_text(json.dumps({"name": "codebase-to-mastery", "version": "9.0.0"}), encoding="utf-8")
        self.run_git("add", "package.json")
        self.run_git("commit", "-qm", "Mismatched npm version")
        with self.assertRaisesRegex(ValueError, "name/version"):
            release.package(self.repo, "HEAD", self.root / "mismatch")

    @unittest.skipUnless(shutil.which("npm"), "npm is needed for the optional npm distribution check")
    def test_npm_pack_uses_complete_committed_payload(self) -> None:
        metadata = {"name": "codebase-to-mastery", "version": "1.0.0", "license": "MIT",
                    "bin": {"codebase-to-mastery": "bin/fixture.mjs"},
                    "files": ["SKILL.md", "VERSION", "scripts/", "assets/", "references/", "tests/", "bin/"]}
        self.source["package.json"] = json.dumps(metadata) + "\n"
        self.source["bin/fixture.mjs"] = "#!/usr/bin/env node\nconsole.log('fixture');\n"
        for name in ("package.json", "bin/fixture.mjs"):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(self.source[name], encoding="utf-8")
        (self.repo / "bin/fixture.mjs").chmod(0o755)
        (self.repo / "codebase-to-mastery.tgz").write_bytes(b"previous npm archive")
        self.run_git("add", "package.json", "bin/fixture.mjs", "codebase-to-mastery.tgz")
        self.run_git("commit", "-qm", "npm fixture")
        (self.repo / "README.md").write_text("uncommitted local change", encoding="utf-8")
        output = self.root / "npm"
        manifest = release.package(self.repo, "HEAD", output, build_npm=True)
        with tarfile.open(output / "codebase-to-mastery-1.0.0.tgz") as archive:
            actual = {}
            for member in archive:
                stream = archive.extractfile(member)
                assert stream is not None
                actual[member.name] = stream.read()
        self.assertEqual(actual, {f"package/{name}": data.encode() for name, data in self.source.items()})
        self.assertEqual(len(manifest["artifacts"]), 3)


if __name__ == "__main__":
    unittest.main()
