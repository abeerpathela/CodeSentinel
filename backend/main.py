"""CodeSentinel FastAPI backend — Agent mesh, SBOM, and analytics."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.mesh import run_mesh_scan
from backend.analytics import compute_summary, load_scan_records
from backend.config.llm_config import LLMConfig, LLMProvider
from backend.scan_status import scan_status_store

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


def _execute_scan(repo_path: str, scan_id: str) -> None:
    try:
        run_mesh_scan(
            repo_path,
            llm_config,
            scan_id=scan_id,
            status_store=scan_status_store,
        )
    except Exception as exc:
        scan_status_store.fail(scan_id, str(exc))


@app.post("/codebreaker/scan")
def codebreaker_scan(body: ScanRequest, background_tasks: BackgroundTasks):
    repo = Path(body.repo_path)
    if not repo.is_dir():
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

    try:
        result = run_mesh_scan(
            body.repo_path,
            llm_config,
            status_store=scan_status_store,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

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


@app.get("/analytics/scans")
def analytics_scans() -> list[dict]:
    return load_scan_records()


@app.get("/analytics/scans/{scan_id}")
def analytics_scan_detail(scan_id: str) -> dict:
    for record in load_scan_records():
        if record.get("scan_id") == scan_id:
            return record
    raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
