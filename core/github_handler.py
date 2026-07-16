"""Remote Source Resolver — clone public GitHub repositories for scanning."""

from __future__ import annotations

import re
import shutil
import stat
import subprocess
from pathlib import Path

from backend.config.path_config import ensure_temp_scan_root, resolve_scan_path


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
        self.temp_root = ensure_temp_scan_root()

    @classmethod
    def ensure_temp_root(cls) -> Path:
        return ensure_temp_scan_root()

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
        dest = resolve_scan_path(scan_id)
        if dest.exists():
            self.cleanup(dest)
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
                "GitHub Clone Failed: Git is not installed or not on PATH.",
                code="git_missing",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            self.cleanup(dest)
            raise GitHubCloneError(code="timeout") from exc

        if proc.returncode != 0:
            self.cleanup(dest)
            raise GitHubCloneError()

        return dest.resolve()

    def clone(self, url: str, scan_id: str) -> Path:
        """Alias for clone_repository (backward compatibility)."""
        return self.clone_repository(url, scan_id)

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
