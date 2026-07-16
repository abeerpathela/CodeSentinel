"""GitHub repository ingestion for remote scan targets."""

from __future__ import annotations

import re
import shutil
import stat
import subprocess
import uuid
from pathlib import Path


class GitHubCloneError(Exception):
    """Raised when a GitHub repository cannot be cloned."""

    def __init__(self, message: str, *, code: str = "clone_failed") -> None:
        super().__init__(message)
        self.code = code


# Supports https/http, optional .git, optional trailing slash
GITHUB_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[\w.\-]+)/(?P<repo>[\w.\-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


class GitHubManager:
    """Clone public GitHub repositories into ephemeral temp scan directories."""

    def __init__(self, project_root: Path | None = None) -> None:
        root = project_root or Path(__file__).resolve().parents[1]
        self.temp_root = root / "backend" / "data" / "temp_scans"
        self.temp_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_github_url(text: str) -> bool:
        return bool(GITHUB_URL_RE.match(text.strip()))

    @staticmethod
    def normalize_url(url: str) -> str:
        raw = url.strip()
        if not raw.lower().startswith(("http://", "https://")):
            raw = f"https://{raw.lstrip('/')}"
        match = GITHUB_URL_RE.match(raw)
        if not match:
            raise GitHubCloneError(
                "Invalid GitHub URL. Expected format: https://github.com/owner/repo",
                code="invalid_url",
            )
        owner = match.group("owner")
        repo = match.group("repo")
        return f"https://github.com/{owner}/{repo}.git"

    def clone(self, url: str) -> Path:
        """Shallow-clone a public repository into a unique temp directory."""
        clone_url = self.normalize_url(url)
        dest = self.temp_root / f"scan_{uuid.uuid4().hex[:12]}"
        dest.mkdir(parents=True, exist_ok=False)

        try:
            proc = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(dest)],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except FileNotFoundError as exc:
            self.cleanup(dest)
            raise GitHubCloneError(
                "Git is not installed or not on PATH.",
                code="git_missing",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            self.cleanup(dest)
            raise GitHubCloneError(
                "Git clone timed out after 120 seconds.",
                code="timeout",
            ) from exc

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").lower()
            self.cleanup(dest)
            if "not found" in err or "does not exist" in err or "404" in err:
                raise GitHubCloneError(
                    "Repository not found. Check the URL or repository name.",
                    code="repo_not_found",
                )
            if "authentication" in err or "permission" in err or "403" in err:
                raise GitHubCloneError(
                    "Cannot access repository — it may be private or requires authentication.",
                    code="private_repo",
                )
            raise GitHubCloneError(
                f"Git clone failed: {(proc.stderr or proc.stdout or 'unknown error').strip()[:200]}",
                code="clone_failed",
            )

        return dest.resolve()

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
