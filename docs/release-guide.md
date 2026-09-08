# Release & Publishing Runbook

Follow this checklist whenever releasing a new version of `airun` (e.g., `v0.1.2`, `v0.1.3`).

---

## The 4-Step Release Workflow

### Step 1: Bump the Version Number (2 Files)

Update the version string in:
1. [`pyproject.toml`](../pyproject.toml):
   ```toml
   [project]
   version = "0.1.2"  # Update version
   ```
2. [`src/airun/__init__.py`](../src/airun/__init__.py):
   ```python
   __version__ = "0.1.2"  # Update version
   ```
3. Update [`CHANGELOG.md`](../CHANGELOG.md) with key changes, bug fixes, or new features.

---

### Step 2: Run Tests & Build Verification

Ensure all tests and linting checks pass:
```bash
# 1. Run unit, integration, and benchmark tests
pytest -v --cov=airun

# 2. Run linter and formatting checks
ruff check src tests examples validation

# 3. Clean and build distribution packages
python -m build

# 4. Verify package metadata
python -m twine check dist/*
```

---

### Step 3: Commit and Push Code

```bash
git add .
git commit -m "chore(release): bump version to v0.1.2"
git push origin main
```

---

### Step 4: Publish to PyPI & GitHub Packages

#### A. Publish to PyPI
```bash
python -m twine upload dist/airun_profiler-0.1.2*
```
*(Username: `__token__`, Password: your PyPI API token)*

#### B. Create Git Tag (Automatically triggers GitHub Docker Package release)
```bash
git tag v0.1.2
git push origin v0.1.2
```
*GitHub Actions will automatically build the new Docker container and push `ghcr.io/sarkarbikram90/airun-tracing:v0.1.2` and `:latest` to GitHub Packages.*

---

### Step 5: Publish the GitHub Release Note

1. Go to: [https://github.com/sarkarbikram90/airun-tracing/releases/new?tag=v0.1.2](https://github.com/sarkarbikram90/airun-tracing/releases/new?tag=v0.1.2)
2. Set title to `v0.1.2 — [Release Headline]`
3. Paste the changelog notes.
4. Drag and drop the built `.whl` and `.tar.gz` files from `dist/`.
5. Click **"Publish release"**.
