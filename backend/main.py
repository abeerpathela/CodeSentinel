"""CodeSentinel FastAPI backend — Agent mesh, SBOM, and analytics."""

from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

import threading
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from agents.mesh import run_mesh_scan
from backend.analytics.metrics import compute_resilience
from backend.analytics.summary import compute_summary, load_scan_records
from backend.config.llm_config import LLMConfig, LLMProvider
from backend.scan_status import scan_status_store
from core.github_repo import GitHubCloneError, GitHubManager
from core.reporter import ReportEngine

app = FastAPI(
    title="CodeSentinel",
    description="Cyber-AI agent mesh backend",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_config = LLMConfig()


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


def _resolve_scan_target(
    repo_input: str,
    *,
    scan_id: str | None = None,
) -> tuple[str, Path | None]:
    """
    Resolve local path or GitHub URL to a scannable directory.
    Returns (scan_path, temp_clone_path) — temp path must be cleaned up after scan.
    """
    stripped = repo_input.strip()
    if stripped.lower().startswith(("http://", "https://")):
        if not GitHubManager.is_github_url(stripped):
            raise HTTPException(
                status_code=400,
                detail="Invalid repository URL. Only public GitHub URLs are supported.",
            )
        manager = GitHubManager()
        try:
            if scan_id:
                scan_status_store.push(
                    scan_id,
                    f"Cloning {stripped} (depth=1)…",
                    stage="cloning",
                )
            cloned = manager.clone(stripped)
            if scan_id:
                scan_status_store.push(
                    scan_id,
                    f"Clone complete: {cloned.name}",
                    stage="scanning",
                )
            return str(cloned), cloned
        except GitHubCloneError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    local = Path(stripped)
    if not local.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Repository path does not exist: {stripped}",
        )
    return str(local.resolve()), None


def _finalize_scan_result(result: dict) -> dict:
    """Generate per-scan SENTINEL_ADVISORY artifact."""
    try:
        advisory_path = ReportEngine().save_sentinel_advisory(result)
        result["advisory_file"] = str(advisory_path)
    except Exception:
        result["advisory_file"] = ""
    return result


def _execute_scan(repo_input: str, scan_id: str) -> None:
    cloned_path: Path | None = None
    try:
        scan_path, cloned_path = _resolve_scan_target(repo_input, scan_id=scan_id)
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
    finally:
        if cloned_path:
            GitHubManager.cleanup(cloned_path)
            entry = scan_status_store.get(scan_id)
            if entry and entry.get("status") != "error":
                scan_status_store.push(
                    scan_id, "Temporary clone cleaned up.", stage="complete"
                )


@app.post("/codebreaker/scan")
def codebreaker_scan(body: ScanRequest, background_tasks: BackgroundTasks):
    stripped = body.repo_path.strip()
    is_remote = stripped.lower().startswith(("http://", "https://"))

    if not is_remote:
        local = Path(stripped)
        if not local.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Repository path does not exist: {body.repo_path}",
            )

    if body.async_scan:
        scan_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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

    cloned_path: Path | None = None
    try:
        scan_path, cloned_path = _resolve_scan_target(body.repo_path)
        result = run_mesh_scan(
            scan_path,
            llm_config,
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
    finally:
        if cloned_path:
            GitHubManager.cleanup(cloned_path)

    return ScanResponse(**result)


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
