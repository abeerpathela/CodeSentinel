"""Background garbage collection for ephemeral scan workspaces."""

from __future__ import annotations

import asyncio
import logging

from backend.config.settings import get_settings
from backend.services.scan_session import sweep_expired_workspaces
from core.workspace_manager import WorkspaceManager

logger = logging.getLogger(__name__)
_gc_task: asyncio.Task | None = None


async def _workspace_gc_loop() -> None:
    settings = get_settings()
    interval = settings.workspace_gc_interval_seconds
    while True:
        await asyncio.sleep(interval)
        removed = WorkspaceManager.instance().garbage_collect()
        expired = sweep_expired_workspaces()
        if removed or expired:
            logger.info(
                "Workspace GC cycle complete — disk=%s registry=%s",
                len(removed),
                len(expired),
            )


def start_workspace_gc() -> None:
    """Schedule periodic workspace cleanup (every 30 min by default)."""
    global _gc_task
    if _gc_task is not None and not _gc_task.done():
        return
    _gc_task = asyncio.create_task(_workspace_gc_loop())
