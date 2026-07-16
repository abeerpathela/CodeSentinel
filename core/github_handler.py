"""Remote Source Resolver — clone public GitHub repositories for scanning."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

from core.workspace_manager import WorkspaceManager


class GitHubCloneError(Exception):
    """Raised when a GitHub repository cannot be cloned."""

    CLONE_FAILED_MSG = (
        "GitHub Clone Failed: Ensure the repository is public and the URL is correct."
    )

    def __init__(self, message: str | None = None, *, code: str = "clone_failed") -> None:
        super().__init__(message or self.CLONE_FAILED_MSG)
        self.code = code


GITHUB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[\w.\-]+)/(?P<repo>[\w.\-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


class GitHubHandler:
    """Transparently clone public GitHub repos into isolated temp scan workspaces."""

    def __init__(self) -> None:
        self.temp_root = WorkspaceManager.instance().ensure_root()

    @classmethod
    def ensure_temp_root(cls) -> Path:
        return WorkspaceManager.instance().ensure_root()

    @staticmethod
    def is_github_url(input_string: str) -> bool:
        raw = input_string.strip()
        if not raw.lower().startswith("https://github.com/"):
            return False
        return bool(GITHUB_URL_RE.match(raw))

    @staticmethod
    def normalize_url(url: str) -> str:
        raw = url.strip()
        if not GitHubHandler.is_github_url(raw):
            raise GitHubCloneError(code="invalid_url")
        match = GITHUB_URL_RE.match(raw)
        assert match is not None
        return f"https://github.com/{match.group('owner')}/{match.group('repo')}.git"

    def clone_repository(self, url: str, scan_id: str) -> Path:
        """Shallow-clone into TEMP_SCAN_ROOT/[scan_id] — folder name equals scan_id."""
        clone_url = self.normalize_url(url)
        dest = WorkspaceManager.get_path(scan_id)
        if dest.exists():
            self.cleanup(dest)
        dest.mkdir(parents=True, exist_ok=False)

        clone_env = os.environ.copy()
        # Avoid optional lock files that can block later .git removal on Windows.
        clone_env["GIT_OPTIONAL_LOCKS"] = "0"

        try:
            proc = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(dest)],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                env=clone_env,
            )
        except FileNotFoundError as exc:
            self.cleanup(dest)
            raise GitHubCloneError(
                "GitHub Clone Failed: Git is not installed or not on PATH.",
                code="git_missing",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            self.cleanup(dest)
            raise GitHubCloneError(code="timeout") from exc

        if proc.returncode != 0:
            self.cleanup(dest)
            raise GitHubCloneError()

        self.release_git_locks(dest)
        return dest.resolve()

    def clone(self, url: str, scan_id: str) -> Path:
        """Alias for clone_repository (backward compatibility)."""
        return self.clone_repository(url, scan_id)

    @staticmethod
    def release_git_locks(path: Path | str) -> None:
        """Clear read-only bits on .git so deploy can shutil.rmtree('.git') later."""
        root = Path(path)
        git_dir = root / ".git"
        if not git_dir.exists():
            return
        for dirpath, _dirnames, filenames in os.walk(git_dir):
            for name in filenames:
                target = Path(dirpath) / name
                try:
                    target.chmod(stat.S_IWRITE | stat.S_IREAD)
                except OSError:
                    pass

    @staticmethod
    def cleanup(path: Path | str) -> None:
        """Remove a temporary clone directory."""
        target = Path(path)
        if not target.exists():
            return

        def _on_rm_error(func, p, _exc_info) -> None:
            Path(p).chmod(stat.S_IWRITE)
            func(p)

        if target.is_dir():
            shutil.rmtree(target, onerror=_on_rm_error)
        elif target.is_file():
            target.unlink(missing_ok=True)
