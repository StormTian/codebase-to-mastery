# Releases

`VERSION`, `SKILL.md` metadata and `package.json` identify the stable release version. ZIP/tar.gz contain a single `codebase-to-mastery/` folder with all committed Skill resources, documentation and original tests; `.github/`, `.gitignore` and the root distribution artifact `codebase-to-mastery.tgz` are excluded. The standard npm `.tgz` has the same files under npm's required `package/` root, including its executable installer. Excluding the root download avoids packing an archive inside itself.

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

Update `VERSION`, `metadata.version` in `SKILL.md` and `package.json`. Both READMEs keep the stable root download URL and latest-release links, with no version selection required. Add `docs/releases/vX.Y.Z.md` with concrete changes and installation instructions. Commit the source changes, build with `--npm` into a fresh directory, copy the versioned npm tarball to the repository root as `codebase-to-mastery.tgz`, and commit that artifact separately. Rebuild from this final commit and compare the root file against the freshly packed `.tgz` with `cmp`; their bytes must match. Then run the packaged demo and push main with its new annotated version tag:

```bash
git tag -a vX.Y.Z -m "Codebase to Mastery vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```

The [Release workflow](../.github/workflows/release.yml) first reuses Python 3.10/3.12 checks and Node installer tests. Its publish job validates the tag/version/commit agreement, builds the assets, verifies that the root download is byte-identical to the fresh npm package, checks checksums, exercises the unpacked Skill and runs the installer through `npm exec` from the actual `.tgz`. It then uses [GitHub CLI](https://cli.github.com/manual/gh_release_create) to publish the release and five assets. Only the publishing job receives repository `contents: write`; authentication uses GitHub Actions' temporary token, with no personal secret required ([GitHub token documentation](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)).

Published assets and tags are not overwritten. If a run fails, inspect its failed step before retrying; check for an existing draft or published release before another creation attempt. GitHub Releases hosts the standard npm tarball and Skill archives. No registry publish command runs in this workflow; direct npx installation uses the full `.tgz` URL, while `npx skills add` remains available for Git sources.

For direct URL installation on npm 12, include `--allow-remote=all` before `--package=URL`; [npm's default is `none`](https://docs.npmjs.com/cli/v12/using-npm/config/#allow-remote). Test the public URL in a fresh temporary project with an empty cache after publication, in addition to the CI install from a local tarball. Verify both clients' installed files against the release manifest and run their demo controls. Keep this setting local to the command; global npm configuration does not need to change. A downloaded tarball can also be selected through `--package=/absolute/path/file.tgz`.
