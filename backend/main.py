"""CodeSentinel FastAPI backend — Agent mesh, SBOM, and analytics."""

from __future__ import annotations

import logging
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

# Render / uvicorn: ensure project root is on PYTHONPATH before package imports
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from agents.mesh import run_mesh_scan
from backend.analytics.metrics import compute_resilience
from backend.analytics.summary import compute_summary, load_scan_records
from backend.config import PROJECT_ROOT, get_settings
from backend.llm_config import LLMConfig, LLMProvider
from backend.scan_status import scan_status_store
from backend.services.github_deploy import GitHubDeployError, GitHubDeployService, ScanWorkspaceGoneError
from backend.services.progress_stream import ProgressTracker
from backend.services.scan_session import register_workspace, release_workspace, sweep_expired_workspaces
from backend.services.scan_stream import _stage_local_workspace, iter_scan
from backend.services.workspace_gc import start_workspace_gc
from core.github_handler import GitHubCloneError, GitHubHandler
from core.reporter import ReportEngine
from core.workspace import WorkspaceManager

settings = get_settings()
_log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
if settings.is_production:
    _log_level = max(_log_level, logging.WARNING)
logging.basicConfig(level=_log_level)

app = FastAPI(
    title="CodeSentinel",
    description="Cyber-AI agent mesh backend",
    version="0.5.0",
)


@app.on_event("startup")
async def _startup() -> None:
    WorkspaceManager.instance()
    sweep_expired_workspaces()
    start_workspace_gc()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_config = LLMConfig()
deploy_service = GitHubDeployService()


class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    provider: LLMProvider | None = None
    large_context: bool = False


class PromptResponse(BaseModel):
    provider: str
    response: str


class ScanRequest(BaseModel):
    repo_path: str = Field(..., min_length=1)
    async_scan: bool = False


class Finding(BaseModel):
    file_path: str
    vulnerability_type: str
    severity: str
    description: str


class SBOMRisk(BaseModel):
    name: str
    version: str
    risk_level: str
    transitive_of: str | None = None
    notes: str = ""


class ScanResponse(BaseModel):
    scan_id: str
    repo_path: str
    files_scanned: int
    findings: list[Finding]
    scan_file: str
    audit_status: str = "approved"
    retry_count: int = 0
    memory_stored: bool = False
    trace_file: str = ""
    self_correction_triggered: bool = False
    sbom_risks: list[SBOMRisk] = []
    sbom_graph: list[dict[str, str]] = []
    sbom_assessment: str = ""


class ScanStartResponse(BaseModel):
    scan_id: str
    status: str
    message: str


class DeployRequest(BaseModel):
    scan_id: str = Field(..., min_length=1)
    repo_name: str = Field(..., min_length=1)
    description: str = "CodeSentinel secured deployment"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "CodeSentinel"}


@app.get("/switchboard/health")
def switchboard_health() -> dict:
    return llm_config.health_check()


@app.post("/switchboard/invoke", response_model=PromptResponse)
def switchboard_invoke(body: PromptRequest) -> PromptResponse:
    try:
        text = llm_config.invoke(
            body.prompt,
            provider=body.provider,
            large_context=body.large_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    provider = body.provider or llm_config.get_provider(
        large_context=body.large_context
    )
    return PromptResponse(provider=provider.value, response=text)


def _push_feed(scan_id: str | None, message: str, *, stage: str) -> None:
    if scan_id:
        scan_status_store.push(scan_id, message, stage=stage)


def _resolve_scan_target(
    repo_input: str,
    *,
    scan_id: str,
) -> str:
    """
    Stage repository into TEMP_SCAN_ROOT/[scan_id].
    Returns scannable path (always resolve_scan_path(scan_id)).
    """
    stripped = repo_input.strip()

    if GitHubHandler.is_github_url(stripped):
        _push_feed(scan_id, f"🛰️ Detecting Source: {stripped}", stage="cloning")
        _push_feed(scan_id, "📥 Cloning Repository: Depth 1 clone started...", stage="cloning")
        handler = GitHubHandler()
        try:
            handler.clone_repository(stripped, scan_id)
        except GitHubCloneError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        _push_feed(scan_id, "✅ Ingestion Complete: Passing source to Codebreaker...", stage="scanning")
        register_workspace(scan_id)
        return str(WorkspaceManager.get_workspace(scan_id))

    if stripped.lower().startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="Invalid repository URL. Only https://github.com/owner/repo URLs are supported.",
        )

    local = Path(stripped)
    if not local.is_dir():
        raise HTTPException(status_code=404, detail=f"Repository path does not exist: {stripped}")

    _stage_local_workspace(scan_id, local.resolve())
    register_workspace(scan_id)
    return str(WorkspaceManager.get_workspace(scan_id))


def _finalize_scan_result(result: dict) -> dict:
    """Generate per-scan SENTINEL_ADVISORY artifact."""
    try:
        advisory_path = ReportEngine().save_sentinel_advisory(result)
        result["advisory_file"] = str(advisory_path)
    except Exception:
        result["advisory_file"] = ""
    return result


def _execute_scan(repo_input: str, scan_id: str) -> None:
    try:
        scan_path = _resolve_scan_target(repo_input, scan_id=scan_id)
        result = run_mesh_scan(
            scan_path,
            llm_config,
            scan_id=scan_id,
            status_store=scan_status_store,
        )
        _finalize_scan_result(result)
    except HTTPException as exc:
        scan_status_store.fail(scan_id, str(exc.detail))
    except Exception as exc:
        scan_status_store.fail(scan_id, str(exc))


def _run_scan_sync(body: ScanRequest) -> ScanResponse | ScanStartResponse:
    stripped = body.repo_path.strip()
    is_remote = GitHubHandler.is_github_url(stripped)

    if not is_remote:
        local = Path(stripped)
        if not local.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Repository path does not exist: {body.repo_path}",
            )

    scan_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if body.async_scan:
        scan_status_store.create(scan_id, body.repo_path)
        thread = threading.Thread(
            target=_execute_scan, args=(body.repo_path, scan_id), daemon=True
        )
        thread.start()
        return ScanStartResponse(
            scan_id=scan_id,
            status="running",
            message="Scan started. Poll /scan/{scan_id}/status for live feed.",
        )

    try:
        scan_path = _resolve_scan_target(body.repo_path, scan_id=scan_id)
        result = run_mesh_scan(
            scan_path,
            llm_config,
            scan_id=scan_id,
            status_store=scan_status_store,
        )
        result = _finalize_scan_result(result)
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ScanResponse(**result)


@app.post("/scan")
def scan_sse(body: ScanRequest) -> StreamingResponse:
    """Live SSE stream — primary scan entry point for Phase 6 UX."""
    stripped = body.repo_path.strip()
    if not GitHubHandler.is_github_url(stripped):
        local = Path(stripped)
        if not local.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Repository path does not exist: {body.repo_path}",
            )

    def event_generator():
        for evt in iter_scan(stripped, llm_config):
            if "ui_status" not in evt:
                evt["ui_status"] = ProgressTracker().ui_scan_status(
                    evt.get("stage", "PARSING"),
                    evt.get("status", "active"),
                    evt.get("result"),
                )
            yield ProgressTracker.sse_line(evt)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/scan/sync")
def scan_sync(body: ScanRequest) -> ScanResponse | ScanStartResponse:
    """Synchronous JSON scan (legacy / validation tests)."""
    return _run_scan_sync(body)


@app.post("/codebreaker/scan")
def codebreaker_scan(body: ScanRequest, background_tasks: BackgroundTasks):
    if body.async_scan:
        return _run_scan_sync(body)
    return scan_sse(body)


@app.post("/scan/legacy")
def scan_legacy(body: ScanRequest, background_tasks: BackgroundTasks):
    return _run_scan_sync(body)


@app.get("/scan/{scan_id}/status")
def scan_status(scan_id: str) -> dict:
    entry = scan_status_store.get(scan_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return entry


@app.get("/analytics/summary")
def analytics_summary() -> dict:
    return compute_summary()


@app.get("/analytics/resilience")
def analytics_resilience() -> dict:
    return compute_resilience()


@app.get("/analytics/export")
def analytics_export(scan_id: str | None = None) -> PlainTextResponse:
    """Generate and serve Security Audit Report executive summary (Markdown)."""
    engine = ReportEngine()
    scan_ids = [scan_id] if scan_id else None
    markdown = engine.render_markdown(engine.aggregate(scan_ids))
    engine.generate_and_save(scan_ids)
    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": 'attachment; filename="CodeSentinel_Security_Audit_Report.md"'
        },
    )


FIXTURE_CATALOG = [
    {
        "id": "supply_chain",
        "name": "Compromised Dependencies",
        "category": "Supply Chain",
        "description": "requirements.txt with malicious version hashes (requests, urllib3, pillow).",
        "folder": "supply_chain",
    },
    {
        "id": "logic_bomb",
        "name": "Time-Delayed Logic Bomb",
        "category": "Logic Bomb",
        "description": "Obfuscated base64 payload executed after a maintenance window check.",
        "folder": "logic_bomb/py",
    },
    {
        "id": "complex_rce",
        "name": "Hidden Env RCE Sink",
        "category": "Advanced RCE",
        "description": "Subprocess appears safe but uses untrusted PYTHON_BIN environment input.",
        "folder": "complex_rce",
    },
]


@app.get("/analytics/fixtures")
def analytics_fixtures() -> list[dict]:
    """Red-Team fixture catalog for Security Lab UI."""
    root = Path(__file__).resolve().parents[1]
    fixtures: list[dict] = []
    for entry in FIXTURE_CATALOG:
        path = root / "fixtures" / "exploits" / entry["folder"]
        fixtures.append({**entry, "path": str(path.resolve())})
    return fixtures


@app.get("/analytics/scans")
def analytics_scans() -> list[dict]:
    return load_scan_records()


@app.get("/analytics/scans/{scan_id}")
def analytics_scan_detail(scan_id: str) -> dict:
    for record in load_scan_records():
        if record.get("scan_id") == scan_id:
            return record
    raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")


@app.get("/auth/login")
def auth_login() -> RedirectResponse:
    try:
        state = deploy_service.create_login_state()
        return RedirectResponse(deploy_service.authorize_url(state), status_code=302)
    except GitHubDeployError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/auth/callback")
def auth_callback(code: str, state: str) -> RedirectResponse:
    try:
        session_id = deploy_service.exchange_code(code, state)
        return RedirectResponse(
            f"{settings.frontend_url.rstrip('/')}/?github_session={session_id}",
            status_code=302,
        )
    except GitHubDeployError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/auth/status")
def auth_status(x_github_session: str | None = Header(default=None)) -> dict:
    if not x_github_session:
        return {"authenticated": False, "message": "Unauthorized — login required."}
    try:
        deploy_service.get_token(x_github_session)
        return {"authenticated": True}
    except GitHubDeployError:
        return {"authenticated": False, "message": "Unauthorized — invalid session."}


@app.post("/deploy/ship")
def deploy_ship(
    body: DeployRequest,
    x_github_session: str | None = Header(default=None),
) -> dict:
    try:
        token = deploy_service.get_token(x_github_session)
        result = deploy_service.push_to_private_repo(
            token,
            body.repo_name,
            body.scan_id,
            description=body.description,
            on_progress=lambda msg: _push_feed(body.scan_id, msg, stage="deploying"),
        )
        release_workspace(body.scan_id)
        return result
    except ScanWorkspaceGoneError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except GitHubDeployError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    _settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=_settings.port,
        log_level="warning" if _settings.is_production else "info",
    )
