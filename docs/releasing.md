# Releases

`VERSION` and `SKILL.md` metadata identify the stable release version. Downloadable packages contain a single `codebase-to-mastery/` folder with all committed Skill resources, documentation and original tests; `.github/` and `.gitignore` are maintenance-only and excluded.

## Build locally

Commit release content first. The packager reads a committed Git revision, never uncommitted files:

```bash
python3 scripts/package_release.py --ref HEAD --output /tmp/mastery-release-new
cd /tmp/mastery-release-new
shasum -a 256 -c SHA256SUMS
```

Use a fresh output directory. The ZIP and tar.gz include identical files; the manifest records the full commit, sizes, modes and per-file hashes. File order, permissions and timestamps are normalized. Two builds from the same commit and compression-library version produce the same bytes; different zlib versions may change compressed bytes while retaining identical file contents.

## Publish a version

Update `VERSION`, `metadata.version` in `SKILL.md`, and both README version examples. Add `docs/releases/vX.Y.Z.md` with concrete changes and installation instructions. Run the tests and packaged demo, review the committed files, then push main and its new annotated version tag:

```bash
git tag -a vX.Y.Z -m "Codebase to Mastery vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```

The [Release workflow](../.github/workflows/release.yml) first reuses Python 3.10/3.12 checks. Its publish job validates the tag/version/commit agreement, builds the assets, verifies checksums, exercises the unpacked Skill, then uses [GitHub CLI](https://cli.github.com/manual/gh_release_create) to publish the release and four assets. Only the publishing job receives repository `contents: write`; authentication uses GitHub Actions' temporary token, with no personal secret required ([GitHub token documentation](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)).

Published assets and tags are not overwritten. If a run fails, inspect its failed step before retrying; check for an existing draft or published release before another creation attempt. Release downloads are Skill archives. Installing through `npx skills add` does not require publishing this repository to the npm registry.
