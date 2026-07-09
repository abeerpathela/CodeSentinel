"""CodeSentinel FastAPI backend — Phase 1 Switchboard."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.config.llm_config import LLMConfig, LLMProvider

app = FastAPI(
    title="CodeSentinel",
    description="Cyber-AI agent mesh backend",
    version="0.1.0",
)

llm_config = LLMConfig()


class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    provider: LLMProvider | None = None
    large_context: bool = False


class PromptResponse(BaseModel):
    provider: str
    response: str


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
