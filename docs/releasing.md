# Releases

`VERSION`, `SKILL.md` metadata and `package.json` identify the stable release version. ZIP/tar.gz contain a single `codebase-to-mastery/` folder with all committed Skill resources, documentation and original tests; `.github/` and `.gitignore` are maintenance-only and excluded. The standard npm `.tgz` has the same files under npm's required `package/` root, including its executable installer.

## Build locally

Commit release content first. The packager reads a committed Git revision, never uncommitted files:

```bash
python3 scripts/package_release.py --ref HEAD --npm --output /tmp/mastery-release-new
cd /tmp/mastery-release-new
shasum -a 256 -c SHA256SUMS
```

Use a fresh output directory. `--npm` requires Node/npm and runs `npm pack --offline --ignore-scripts` in a temporary copy containing only the committed payload. Omit it when you only need Python-built ZIP/tar.gz. The three archives contain identical files; the manifest records the full commit, sizes, modes and per-file hashes. File order, permissions and timestamps are normalized in ZIP/tar.gz. Two builds from the same commit and packaging-runtime versions produce the same bytes; different zlib/npm versions may change compressed bytes while retaining identical file contents.

The npm package uses an explicit resource allowlist and no dependencies or install lifecycle hooks. Packaging verifies every tarball file against the committed payload before writing assets. The independent CLI installs complete resources into project/personal skill directories and refuses existing destinations.

## Publish a version

Update `VERSION`, `metadata.version` in `SKILL.md`, `package.json`, and both README version examples. Add `docs/releases/vX.Y.Z.md` with concrete changes and installation instructions. Run the tests and packaged demo, review the committed files, then push main and its new annotated version tag:

```bash
git tag -a vX.Y.Z -m "Codebase to Mastery vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```

The [Release workflow](../.github/workflows/release.yml) first reuses Python 3.10/3.12 checks and Node installer tests. Its publish job validates the tag/version/commit agreement, builds the assets, verifies checksums, exercises the unpacked Skill and runs the installer through `npm exec` from the actual `.tgz`. It then uses [GitHub CLI](https://cli.github.com/manual/gh_release_create) to publish the release and five assets. Only the publishing job receives repository `contents: write`; authentication uses GitHub Actions' temporary token, with no personal secret required ([GitHub token documentation](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)).

Published assets and tags are not overwritten. If a run fails, inspect its failed step before retrying; check for an existing draft or published release before another creation attempt. GitHub Releases hosts the standard npm tarball and Skill archives. No registry publish command runs in this workflow; direct npx installation uses the full `.tgz` URL, while `npx skills add` remains available for Git sources.
