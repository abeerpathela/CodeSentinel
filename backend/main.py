"""CodeSentinel FastAPI backend — Phase 1 Switchboard + Phase 2 Codebreaker."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agents.mesh import run_mesh_scan
from backend.config.llm_config import LLMConfig, LLMProvider

app = FastAPI(
    title="CodeSentinel",
    description="Cyber-AI agent mesh backend",
    version="0.2.0",
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


class Finding(BaseModel):
    file_path: str
    vulnerability_type: str
    severity: str
    description: str


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


@app.post("/codebreaker/scan", response_model=ScanResponse)
def codebreaker_scan(body: ScanRequest) -> ScanResponse:
    repo = Path(body.repo_path)
    if not repo.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Repository path does not exist: {body.repo_path}",
        )

    try:
        result = run_mesh_scan(body.repo_path, llm_config)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ScanResponse(**result)
