"""Managed ephemeral scan workspaces — no hardcoded user disk paths."""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Resolves and lifecycle-manages ephemeral scan directories."""

    _instance: WorkspaceManager | None = None

    def __init__(self) -> None:
        self._settings = get_settings()
        self._root = self._resolve_root()

    @classmethod
    def instance(cls) -> WorkspaceManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_path(cls, scan_id: str) -> Path:
        """Canonical workspace path for a scan_id."""
        return cls.instance().ensure_root() / scan_id

    @property
    def root(self) -> Path:
        return self._root

    @property
    def ttl_seconds(self) -> int:
        return self._settings.scan_workspace_ttl_seconds

    def _resolve_root(self) -> Path:
        explicit = self._settings.sentinel_workspace_root.strip()
        if explicit:
            return Path(explicit).resolve()

        base = Path(tempfile.gettempdir())
        if self._settings.workspace_storage_type == "tmpfs":
            return (base / "codesentinel_tmpfs").resolve()
        return (base / "codesentinel_workspaces").resolve()

    def ensure_root(self) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root

    def garbage_collect(self) -> list[str]:
        """
        Delete workspace folders older than TTL.
        Returns scan_ids removed.
        """
        self.ensure_root()
        cutoff = time.time() - self.ttl_seconds
        removed: list[str] = []

        for entry in self._root.iterdir():
            if not entry.is_dir():
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if mtime < cutoff:
                scan_id = entry.name
                from core.github_handler import GitHubHandler

                GitHubHandler.cleanup(entry)
                removed.append(scan_id)
                logger.info("GC removed expired workspace %s", scan_id)

        return removed

    def describe_root(self) -> str:
        """Relative-style label for logs (never expose full user paths in tests)."""
        try:
            return self._root.relative_to(Path(tempfile.gettempdir())).as_posix()
        except ValueError:
            return self._root.name
