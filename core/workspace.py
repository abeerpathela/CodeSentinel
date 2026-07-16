"""Ephemeral scan workspaces — OS temp only, no hardcoded disk paths."""

from __future__ import annotations

import logging
import stat
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """
    Manages per-scan directories under the OS temp folder.

    Each workspace is created via ``tempfile.mkdtemp(prefix='sentinel_')`` so
    Render/Linux ``/tmp`` and Windows ``Temp`` are used automatically.
    """

    _instance: WorkspaceManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        from backend.config import get_settings

        self._settings = get_settings()
        self._registry: dict[str, Path] = {}
        self._created_at: dict[str, float] = {}

    @classmethod
    def instance(cls) -> WorkspaceManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def ttl_seconds(self) -> int:
        return self._settings.scan_workspace_ttl_seconds

    @classmethod
    def get_existing(cls, scan_id: str) -> Path | None:
        """Return workspace path only if already allocated (never creates)."""
        mgr = cls.instance()
        with cls._lock:
            path = mgr._registry.get(scan_id)
        if path is not None and path.exists():
            return path
        return None

    @classmethod
    def get_workspace(cls, scan_id: str) -> Path:
        """Return (and lazily create) the ephemeral workspace for *scan_id*."""
        mgr = cls.instance()
        with cls._lock:
            path = mgr._registry.get(scan_id)
            if path is None or not path.exists():
                path = Path(tempfile.mkdtemp(prefix="sentinel_"))
                mgr._registry[scan_id] = path
                mgr._created_at[scan_id] = time.time()
                logger.debug("Allocated workspace %s -> %s", scan_id, mgr.temp_label(path))
            return path

    @classmethod
    def get_path(cls, scan_id: str) -> Path:
        """Alias used by clone/deploy pipeline."""
        return cls.get_workspace(scan_id)

    @classmethod
    def release_workspace(cls, scan_id: str) -> None:
        """Delete a single workspace and drop registry entry."""
        mgr = cls.instance()
        with cls._lock:
            path = mgr._registry.pop(scan_id, None)
            mgr._created_at.pop(scan_id, None)
        if path and path.exists():
            mgr._remove_tree(path)

    def ensure_root(self) -> Path:
        """Compatibility hook — returns OS temp directory."""
        return Path(tempfile.gettempdir())

    @property
    def root(self) -> Path:
        return Path(tempfile.gettempdir())

    def cleanup_all(self) -> list[str]:
        """Delete workspaces older than TTL. Returns removed scan_ids."""
        cutoff = time.time() - self.ttl_seconds
        removed: list[str] = []

        with self._lock:
            entries = list(self._registry.items())

        for scan_id, path in entries:
            created = self._created_at.get(scan_id, 0.0)
            try:
                mtime = path.stat().st_mtime if path.exists() else created
            except OSError:
                mtime = created
            age_anchor = max(created, mtime)
            if age_anchor < cutoff:
                self.release_workspace(scan_id)
                removed.append(scan_id)
                logger.info("GC removed workspace %s", scan_id)

        removed.extend(self._cleanup_orphan_sentinel_dirs(cutoff))
        return removed

    def garbage_collect(self) -> list[str]:
        """Alias for background cron."""
        return self.cleanup_all()

    def describe_root(self) -> str:
        temp = Path(tempfile.gettempdir())
        if temp.as_posix() == "/tmp":
            return "/tmp"
        if any(p.lower() == "temp" for p in temp.parts):
            return "Temp"
        return temp.name

    @staticmethod
    def temp_label(path: Path) -> str:
        """Safe log label — relative to OS temp when possible."""
        temp = Path(tempfile.gettempdir())
        try:
            return path.resolve().relative_to(temp.resolve()).as_posix()
        except ValueError:
            name = path.name
            if name.startswith("sentinel_"):
                return name
            return "temp"

    def _cleanup_orphan_sentinel_dirs(self, cutoff: float) -> list[str]:
        """Sweep stray sentinel_* folders in OS temp."""
        removed: list[str] = []
        temp = Path(tempfile.gettempdir())
        registered = set(self._registry.values())
        for entry in temp.glob("sentinel_*"):
            if not entry.is_dir() or entry in registered:
                continue
            try:
                if entry.stat().st_mtime < cutoff:
                    self._remove_tree(entry)
                    removed.append(entry.name)
            except OSError:
                continue
        return removed

    @staticmethod
    def _remove_tree(path: Path) -> None:
        import shutil

        def _on_rm_error(func, p, _exc_info) -> None:
            Path(p).chmod(stat.S_IWRITE)
            func(p)

        if path.is_dir():
            shutil.rmtree(path, onerror=_on_rm_error)
        elif path.is_file():
            path.unlink(missing_ok=True)
