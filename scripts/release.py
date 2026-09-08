#!/usr/bin/env python
"""Automated Release Script for airun.

Bumps version across all language manifests, validates builds & tests,
commits changes, tags the release, and pushes to GitHub.

Usage:
    python scripts/release.py <new_version> [--dry-run] [--no-push]

Example:
    python scripts/release.py 0.1.4
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd: list[str], check: bool = True) -> str:
    print(f"[*] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"[!] Command failed: {' '.join(cmd)}\n{res.stderr}", file=sys.stderr)
        sys.exit(res.returncode)
    return res.stdout.strip()


def update_file(path: Path, pattern: str, replacement: str) -> None:
    if not path.exists():
        print(f"[-] Skipping non-existent: {path}")
        return
    content = path.read_text(encoding="utf-8")
    new_content, count = re.subn(pattern, replacement, content)
    if count == 0:
        print(f"[!] Warning: Pattern '{pattern}' not matched in {path}")
    else:
        path.write_text(new_content, encoding="utf-8")
        print(f"[+] Updated {path.relative_to(ROOT)} ({count} substitution{'s' if count > 1 else ''})")


def bump_versions(version: str) -> None:
    print(f"\n>> Bumping version to {version} across all manifests...")

    # 1. pyproject.toml
    update_file(
        ROOT / "pyproject.toml",
        r'(?m)^version\s*=\s*"[^"]+"',
        f'version = "{version}"',
    )

    # 2. src/airun/__init__.py
    update_file(
        ROOT / "src" / "airun" / "__init__.py",
        r'__version__\s*=\s*"[^"]+"',
        f'__version__ = "{version}"',
    )

    # 3. src/airun/server/__init__.py
    update_file(
        ROOT / "src" / "airun" / "server" / "__init__.py",
        r'server_version\s*=\s*"airun-server/[^"]+"',
        f'server_version = "airun-server/{version}"',
    )
    update_file(
        ROOT / "src" / "airun" / "server" / "__init__.py",
        r'"version":\s*"[^"]+"',
        f'"version": "{version}"',
    )

    # 4. src/airun/exporters/otlp.py
    update_file(
        ROOT / "src" / "airun" / "exporters" / "otlp.py",
        r'"version":\s*"[^"]+"',
        f'"version": "{version}"',
    )

    # 5. crates/airun-collector/Cargo.toml
    update_file(
        ROOT / "crates" / "airun-collector" / "Cargo.toml",
        r'(?m)^version\s*=\s*"[^"]+"',
        f'version = "{version}"',
    )

    # 6. packages/control-plane/package.json
    update_file(
        ROOT / "packages" / "control-plane" / "package.json",
        r'"version":\s*"[^"]+"',
        f'"version": "{version}"',
    )

    # 7. packages/control-plane/src/index.ts
    update_file(
        ROOT / "packages" / "control-plane" / "src" / "index.ts",
        r"version:\s*'[^']+'",
        f"version: '{version}'",
    )

    # 8. deploy/helm/airun-data-plane/Chart.yaml
    update_file(
        ROOT / "deploy" / "helm" / "airun-data-plane" / "Chart.yaml",
        r'(?m)^version:\s*[^\s]+',
        f'version: {version}',
    )
    update_file(
        ROOT / "deploy" / "helm" / "airun-data-plane" / "Chart.yaml",
        r'(?m)^appVersion:\s*"[^"]+"',
        f'appVersion: "{version}"',
    )

    # 9. deploy/helm/airun-data-plane/values.yaml
    update_file(
        ROOT / "deploy" / "helm" / "airun-data-plane" / "values.yaml",
        r'tag:\s*"[^"]+"',
        f'tag: "{version}"',
    )

    # 10. README.md badge
    update_file(
        ROOT / "README.md",
        r'badge/version-[^-\s]+-blue\.svg',
        f'badge/version-{version}-blue.svg',
    )

    # 11. agent.md
    update_file(
        ROOT / "agent.md",
        r'- \*\*v[^\s]+ \(Current\)\*\*',
        f'- **v{version} (Current)**',
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Automate airun multi-language release workflow.")
    parser.add_argument("version", help="New semantic version number (e.g. 0.1.4)")
    parser.add_argument("--dry-run", action="store_true", help="Perform checks without committing or pushing.")
    parser.add_argument("--no-push", action="store_true", help="Commit and tag locally, but do not push.")
    args = parser.parse_args()

    version = args.version.lstrip("v")
    if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$", version):
        print(f"[!] Invalid semantic version: {version}", file=sys.stderr)
        sys.exit(1)

    tag = f"v{version}"
    print(f"============================================================")
    print(f"  airun Automated Release Pipeline -> {tag}")
    print(f"============================================================")

    bump_versions(version)

    print("\n>> Verifying test suite and package builds...")
    run_cmd([sys.executable, "-m", "pytest"])
    run_cmd([sys.executable, "-m", "build"])
    run_cmd([sys.executable, "-m", "twine", "check", "dist/*"])

    if args.dry_run:
        print("\n[OK] Dry-run completed successfully! No git changes committed.")
        return

    print("\n>> Staging and committing changes...")
    run_cmd(["git", "add", "-A"])
    run_cmd(["git", "commit", "-m", f"chore(release): bump version to {tag}"])
    run_cmd(["git", "tag", "-a", tag, "-m", f"Release {tag}"])

    if args.no_push:
        print(f"\n[OK] Release {tag} committed and tagged locally.")
        return

    print("\n>> Pushing main and tags to GitHub...")
    run_cmd(["git", "push", "origin", "main"])
    run_cmd(["git", "push", "origin", tag])

    print("\n============================================================")
    print(f"  [SUCCESS] Release {tag} pushed to GitHub!")
    print(f"  GitHub Actions is now automatically:")
    print(f"    1. Building Wheel & SDist")
    print(f"    2. Publishing to PyPI (if PYPI_API_TOKEN or Trusted Publisher configured)")
    print(f"    3. Creating GitHub Release with release notes and assets")
    print(f"    4. Building & pushing Docker container to ghcr.io")
    print(f"============================================================")


if __name__ == "__main__":
    main()
