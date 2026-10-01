#!/usr/bin/env python3
"""Package an exact committed Skill revision using only Python's standard library."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


SKILL_NAME = "codebase-to-mastery"


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def package(repo: Path, ref: str, output: Path, tag: str | None = None, build_npm: bool = False) -> dict:
    commit = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    timestamp = int(git(repo, "show", "-s", "--format=%ct", commit))
    version = git(repo, "show", f"{commit}:VERSION").decode().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("VERSION must contain a stable MAJOR.MINOR.PATCH version")
    if tag is not None:
        if tag != f"v{version}":
            raise ValueError("Release tag does not match VERSION")
        if git(repo, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}").decode().strip() != commit:
            raise ValueError("Release tag does not point to the packaged commit")

    files: dict[str, tuple[bytes, int]] = {}
    with tarfile.open(fileobj=io.BytesIO(git(repo, "archive", "--format=tar", commit))) as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if path.parts[0] == ".github" or member.name == ".gitignore":
                continue
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe archive path: {member.name}")
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"Release files must be regular files: {member.name}")
            if any(part in {".git", "__pycache__", "node_modules", "dist"} for part in path.parts):
                raise ValueError(f"Unexpected generated file: {member.name}")
            if path.name.startswith(".env") or path.suffix in {".pem", ".key", ".pyc"}:
                raise ValueError(f"Unexpected private/generated file: {member.name}")
            stream = archive.extractfile(member)
            assert stream is not None
            files[member.name] = (stream.read(), 0o755 if member.mode & 0o111 else 0o644)

    for required in ("SKILL.md", "LICENSE", "VERSION", "README.md", "scripts/build_course.py",
                     "assets/course-template/base.html", "references/learning-kit.md", "tests/create_demo.py"):
        if required not in files:
            raise ValueError(f"Missing release resource: {required}")
    if f'  version: "{version}"' not in files["SKILL.md"][0].decode():
        raise ValueError("Skill metadata version does not match VERSION")
    if "package.json" in files:
        metadata = json.loads(files["package.json"][0])
        if metadata.get("name") != SKILL_NAME or metadata.get("version") != version:
            raise ValueError("npm package name/version does not match the Skill release")
    elif build_npm:
        raise ValueError("npm packaging requires a committed package.json")

    output.mkdir(parents=True, exist_ok=True)
    stem = f"{SKILL_NAME}-v{version}"
    names = [f"{stem}.zip", f"{stem}.tar.gz", "release-manifest.json", "SHA256SUMS"]
    npm_name = f"{SKILL_NAME}-{version}.tgz"
    if build_npm:
        names.append(npm_name)
    if any((output / name).exists() for name in names):
        raise ValueError("Use a fresh output directory; release assets are not overwritten")

    tar_bytes = io.BytesIO()
    zip_bytes = io.BytesIO()
    zip_date = dt.datetime.fromtimestamp(max(timestamp, 315532800), dt.timezone.utc)
    with tarfile.open(fileobj=tar_bytes, mode="w", format=tarfile.PAX_FORMAT) as tar, \
            zipfile.ZipFile(zip_bytes, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for name, (data, mode) in sorted(files.items()):
            entry = f"{SKILL_NAME}/{name}"
            info = tarfile.TarInfo(entry)
            info.size, info.mode, info.mtime = len(data), mode, timestamp
            tar.addfile(info, io.BytesIO(data))
            zinfo = zipfile.ZipInfo(entry, zip_date.timetuple()[:6])
            zinfo.create_system = 3
            zinfo.external_attr = (0o100000 | mode) << 16
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(zinfo, data, compresslevel=9)

    gzip_bytes = io.BytesIO()
    with gzip.GzipFile(fileobj=gzip_bytes, mode="wb", filename="", compresslevel=9, mtime=0) as compressed:
        compressed.write(tar_bytes.getvalue())
    artifacts = {names[0]: zip_bytes.getvalue(), names[1]: gzip_bytes.getvalue()}
    if build_npm:
        # Stage only the committed payload, so npm never reads local learner files.
        with tempfile.TemporaryDirectory(prefix="mastery-npm-pack-") as temporary:
            stage = Path(temporary) / "package"
            stage.mkdir()
            for name, (data, mode) in files.items():
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                target.chmod(mode)
            subprocess.run(
                ["npm", "pack", "--offline", "--ignore-scripts", "--json", "--cache", str(Path(temporary) / "cache"),
                 "--pack-destination", str(Path(temporary))],
                cwd=stage, check=True, capture_output=True, text=True,
            )
            packed_path = Path(temporary) / npm_name
            # npm 10/11 return a JSON array; npm 12 can return an object.
            # Verify the actual artifact rather than depending on stdout shape.
            if not packed_path.is_file() or list(Path(temporary).glob("*.tgz")) != [packed_path]:
                raise ValueError("Unexpected npm pack output")
            npm_bytes = packed_path.read_bytes()
            with tarfile.open(fileobj=io.BytesIO(npm_bytes), mode="r:gz") as npm_archive:
                npm_files = {}
                for member in npm_archive:
                    if not member.isfile() or not member.name.startswith("package/"):
                        raise ValueError("Unexpected entry in npm tarball")
                    stream = npm_archive.extractfile(member)
                    assert stream is not None
                    npm_files[member.name.removeprefix("package/")] = stream.read()
                if npm_files != {name: data for name, (data, _) in files.items()}:
                    raise ValueError("npm tarball differs from the complete committed Skill payload")
            artifacts[npm_name] = npm_bytes
    manifest = {
        "schemaVersion": 1, "skill": SKILL_NAME, "version": version, "tag": f"v{version}",
        "commit": commit, "rootDirectory": SKILL_NAME, "fileCount": len(files),
        "excluded": [".github/", ".gitignore"],
        "files": [{"path": name, "sha256": digest(data), "size": len(data), "mode": oct(mode)}
                  for name, (data, mode) in sorted(files.items())],
        "artifacts": [{"name": name, "sha256": digest(data), "size": len(data)}
                      for name, data in artifacts.items()],
    }
    artifacts[names[2]] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    artifacts[names[3]] = "".join(f"{digest(data)}  {name}\n" for name, data in sorted(artifacts.items())).encode()
    for name, data in artifacts.items():
        (output / name).write_bytes(data)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ref", default="HEAD", help="Committed revision; working-tree files are ignored")
    parser.add_argument("--tag", help="Require this tag to match VERSION and the packaged commit")
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--npm", action="store_true", help="Also build and verify a standard npm pack tarball (requires Node/npm)")
    args = parser.parse_args()
    manifest = package(args.repo, args.ref, args.output, args.tag, args.npm)
    print(json.dumps({"version": manifest["version"], "commit": manifest["commit"],
                      "fileCount": manifest["fileCount"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
