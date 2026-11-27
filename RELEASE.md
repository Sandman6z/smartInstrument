# Release Process

This project uses GitHub Actions to automatically build and release the executable.

## How to create a release

1. If updating the package version in `pyproject.toml`, run `uv lock` and include `uv.lock` in the same PR.
2. After the PR merges, switch to `main` and update it from `origin/main`.
3. Tag the release commit with a tag starting with `v` (e.g., `v1.0.0`) and push that tag.

### Commands

```bash
git switch main
git pull --ff-only
git tag v1.0.0
git push origin v1.0.0
```

## What happens next

1. GitHub Actions will trigger the `Build and Release` workflow.
2. On Windows, it installs the locked dependencies with `uv` and builds `dist_nuitka/SmartInstrument.exe` using Nuitka.
3. It uploads the executable as a workflow artifact. For a tag push it also creates a GitHub Release and attaches `SmartInstrument.exe`.

To check a build without publishing, manually run the workflow from a branch in the Actions tab. The executable will be available as a workflow artifact, not a release asset.

## Download

Users can download the `SmartInstrument.exe` directly from the [Releases](https://github.com/Sandman6z/smartInstrument/releases) page of the repository.
