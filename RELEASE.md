# Release Process

This project uses GitHub Actions to automatically build and release the executable.

## How to create a release

1. Update the version in `pyproject.toml` (optional but recommended).
2. Commit your changes.
3. Create a git tag starting with `v` (e.g., `v1.0.0`).
4. Push the tag to GitHub.

### Commands

```bash
# 1. Tag the current commit
git tag v1.0.0

# 2. Push the tag to GitHub
git push origin v1.0.0
```

## What happens next

1. GitHub Actions will trigger the `Build and Release` workflow.
2. It will set up the environment, install dependencies using `uv`.
3. It will build the executable using Nuitka.
4. It will create a GitHub Release for the tag `v1.0.0` and upload `SmartInstrument.exe` to the assets.

## Download

Users can download the `SmartInstrument.exe` directly from the [Releases](../../releases) page of the repository.
