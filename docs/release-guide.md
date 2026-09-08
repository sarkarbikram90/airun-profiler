# Automated Release & Publishing Runbook

`airun` provides a fully automated CI/CD release pipeline via GitHub Actions (`.github/workflows/release.yml`).

---

## 1-Command Automated Release

Run the release script with your target semantic version:

```bash
python scripts/release.py 0.1.4
```

This single command automatically:
1. Updates the version across all manifests (`pyproject.toml`, `src/airun/__init__.py`, `crates/airun-collector/Cargo.toml`, `packages/control-plane/package.json`, Helm charts, README).
2. Runs the complete test suite (`pytest`) and packaging build (`python -m build`).
3. Verifies package metadata with `twine check`.
4. Commits: `chore(release): bump version to v0.1.4`.
5. Tags: `v0.1.4`.
6. Pushes `main` and tag `v0.1.4` to GitHub.

---

## What GitHub Actions Does Automatically

When tag `v*.*.*` is pushed to GitHub, [`.github/workflows/release.yml`](../.github/workflows/release.yml) automatically triggers:

1. **Builds Wheel & SDist**: Builds Python `.whl` and `.tar.gz` distribution packages.
2. **Publishes to PyPI**: Uploads the packages to PyPI (via PyPI Trusted Publishing or `PYPI_API_TOKEN`).
3. **Creates GitHub Release**: Automatically publishes an official GitHub Release with release notes and attaches the built `.whl` and `.tar.gz` assets.
4. **Publishes Docker Image**: Builds the multi-stage Docker container and publishes `ghcr.io/sarkarbikram90/airun-profiler:v0.1.4` and `:latest` to GitHub Packages.

---

## One-Time Setup: Connecting PyPI for Automated Publishing

You have two options to enable automatic PyPI publishing from GitHub Actions:

### Option A: PyPI Trusted Publishing (Recommended - Zero Secrets)

Trusted Publishing uses OpenID Connect (OIDC) between GitHub and PyPI, eliminating the need to store long-lived API tokens.

1. Go to your PyPI project: [https://pypi.org/manage/project/airun-profiler/settings/publishing/](https://pypi.org/manage/project/airun-profiler/settings/publishing/)
2. Under **"Add a publisher"**, select **"GitHub"**.
3. Fill in:
   - **Owner**: `sarkarbikram90`
   - **Repository name**: `airun-profiler`
   - **Workflow name**: `release.yml`
   - **Environment name**: *(leave blank)*
4. Click **"Add publisher"**.
*Done! Every time you push a tag, GitHub Actions will publish to PyPI automatically without any token.*

---

### Option B: PyPI API Token (Traditional Secret)

1. Create a PyPI API Token on PyPI: [https://pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)
   - Scope: Project `airun-profiler` (or all projects).
2. Go to your GitHub repository:
   - **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions** $\rightarrow$ **New repository secret**.
3. Name: `PYPI_API_TOKEN`
4. Secret: `pypi-...` (your token).
5. Click **"Add secret"**.
