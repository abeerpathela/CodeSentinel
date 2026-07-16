"""Fresh-source Git deployment — purge shallow clone history before push."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

GIT_USER_NAME = "CodeSentinel-Bot"
GIT_USER_EMAIL = "sentinel@codesentinel.local"
COMMIT_MESSAGE = "CodeSentinel Security Audit: Clean Snapshot"


class GitDeployError(Exception):
    """Raised when a local Git operation fails."""


ProgressCallback = Callable[[str], None]


def _on_rm_error(func, p, _exc_info) -> None:
    Path(p).chmod(stat.S_IWRITE)
    func(p)


def _run_git(
    args: list[str],
    cwd: Path,
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if check and proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "unknown git error").strip()
        raise GitDeployError(f"git {' '.join(args)} failed: {err}")
    return proc


def purge_git_metadata(workspace: Path) -> None:
    """Remove existing .git directory (shallow-clone artifacts, stale remotes)."""
    git_dir = workspace / ".git"
    if not git_dir.exists():
        return
    shutil.rmtree(git_dir, onerror=_on_rm_error)


def prepare_fresh_repository(
    workspace: Path,
    *,
    on_progress: ProgressCallback | None = None,
) -> None:
    """
    Scrub old metadata, init a new repo, commit all files on main.

    Git sequence:
      rm -rf .git  →  git init  →  config user  →  add .  →  commit  →  branch -M main
    """
    if not workspace.is_dir():
        raise GitDeployError(f"Workspace is not a directory: {workspace.name}")

    def notify(message: str) -> None:
        if on_progress:
            on_progress(message)

    notify("🧹 Scrubbing Metadata: Removing source Git history...")
    purge_git_metadata(workspace)

    notify("🔨 Initializing: Creating fresh audit repository...")
    _run_git(["init"], workspace)
    _run_git(["config", "user.name", GIT_USER_NAME], workspace)
    _run_git(["config", "user.email", GIT_USER_EMAIL], workspace)
    _run_git(["add", "."], workspace)
    _run_git(["commit", "-m", COMMIT_MESSAGE], workspace)
    _run_git(["branch", "-M", "main"], workspace)


def push_fresh_to_origin(
    workspace: Path,
    origin_url: str,
    *,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Add origin remote and push main (expects a fresh, empty remote)."""
    if on_progress:
        on_progress("🚀 Pushing: Sending clean code to GitHub...")

    add = _run_git(["remote", "add", "origin", origin_url], workspace, check=False)
    if add.returncode != 0:
        _run_git(["remote", "set-url", "origin", origin_url], workspace)
    _run_git(["push", "-u", "origin", "main"], workspace)


def is_shallow_repository(workspace: Path) -> bool:
    proc = _run_git(["rev-parse", "--is-shallow-repository"], workspace, check=False)
    if proc.returncode != 0:
        return False
    return proc.stdout.strip().lower() == "true"


def deploy_fresh_source(
    workspace: Path,
    origin_url: str,
    *,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Full fresh-source chain: scrub → init → commit → push."""
    prepare_fresh_repository(workspace, on_progress=on_progress)
    push_fresh_to_origin(workspace, origin_url, on_progress=on_progress)
