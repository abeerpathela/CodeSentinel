"""Fresh-source Git deployment — purge shallow clone history before push."""

from __future__ import annotations

import shutil
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

from backend.config.settings import get_settings

_settings = get_settings()
GIT_USER_NAME = _settings.git_deploy_user_name
GIT_USER_EMAIL = _settings.git_deploy_user_email
COMMIT_MESSAGE = _settings.git_deploy_commit_message


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
    git_user_name: str | None = None,
    git_user_email: str | None = None,
    commit_message: str | None = None,
) -> None:
    """
    Scrub old metadata, init a new repo, commit all files on main.

    Git sequence:
      rm -rf .git  →  git init  →  config user  →  add .  →  commit  →  branch -M main
    """
    if not workspace.is_dir():
        raise GitDeployError(f"Workspace is not a directory: {workspace.name}")

    user_name = git_user_name or GIT_USER_NAME
    user_email = git_user_email or GIT_USER_EMAIL
    message = commit_message or COMMIT_MESSAGE

    def notify(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    notify("🧹 Scrubbing Metadata: Removing source Git history...")
    purge_git_metadata(workspace)

    notify("🔨 Initializing: Creating fresh audit repository...")
    _run_git(["init"], workspace)
    _run_git(["config", "user.name", user_name], workspace)
    _run_git(["config", "user.email", user_email], workspace)
    _run_git(["add", "."], workspace)
    _run_git(["commit", "-m", message], workspace)
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
    git_user_name: str | None = None,
    git_user_email: str | None = None,
    commit_message: str | None = None,
) -> None:
    """Full fresh-source chain: scrub → init → commit → push."""
    prepare_fresh_repository(
        workspace,
        on_progress=on_progress,
        git_user_name=git_user_name,
        git_user_email=git_user_email,
        commit_message=commit_message,
    )
    push_fresh_to_origin(workspace, origin_url, on_progress=on_progress)
