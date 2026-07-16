"""Production environment configuration for CodeSentinel (Render-ready)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    llm_model_groq: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias=AliasChoices("LLM_MODEL_GROQ", "GROQ_MODEL"),
    )
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    llm_model_gemini: str = Field(
        default="gemini-1.5-flash",
        validation_alias=AliasChoices("LLM_MODEL_GEMINI", "GEMINI_MODEL"),
    )
    llm_max_retries: int = Field(default=2, validation_alias="LLM_MAX_RETRIES")

    sentinel_app_url: str = Field(
        default="http://localhost:8000",
        validation_alias=AliasChoices("SENTINEL_APP_URL", "APP_URL"),
    )
    frontend_url: str = Field(default="http://localhost:5173", validation_alias="FRONTEND_URL")

    github_client_id: str = Field(default="", validation_alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(default="", validation_alias="GITHUB_CLIENT_SECRET")
    github_redirect_uri: str = Field(default="", validation_alias="GITHUB_REDIRECT_URI")

    workspace_storage_type: Literal["local", "tmpfs"] = Field(
        default="local",
        validation_alias="WORKSPACE_STORAGE_TYPE",
    )
    sentinel_workspace_root: str = Field(default="", validation_alias="SENTINEL_WORKSPACE_ROOT")

    # Render: GC every 10 min, delete workspaces older than 20 min
    scan_workspace_ttl_seconds: int = Field(
        default=1200,
        validation_alias="SCAN_WORKSPACE_TTL_SECONDS",
    )
    workspace_gc_interval_seconds: int = Field(
        default=600,
        validation_alias="WORKSPACE_GC_INTERVAL_SECONDS",
    )

    logs_dir: Path = Field(default=PROJECT_ROOT / "logs")
    chroma_dir: Path = Field(default=PROJECT_ROOT / "data" / "chroma")

    sbom_manifest_files: tuple[str, ...] = (
        "requirements.txt",
        "package.json",
        "go.mod",
    )

    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    port: int = Field(default=8000, validation_alias="PORT")

    git_deploy_user_name: str = Field(default="CodeSentinel-Bot", validation_alias="GIT_DEPLOY_USER_NAME")
    git_deploy_user_email: str = Field(
        default="sentinel@codesentinel.local",
        validation_alias="GIT_DEPLOY_USER_EMAIL",
    )
    git_deploy_commit_message: str = Field(
        default="CodeSentinel Security Audit: Clean Snapshot",
        validation_alias="GIT_DEPLOY_COMMIT_MESSAGE",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def github_oauth_redirect_uri(self) -> str:
        if self.github_redirect_uri.strip():
            return self.github_redirect_uri.strip()
        return f"{self.sentinel_app_url.rstrip('/')}/auth/callback"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        base = self.frontend_url.rstrip("/")
        alt = base.replace("localhost", "127.0.0.1")
        origins = {base, alt}
        if self.is_production and base.startswith("https://"):
            origins.add(base.replace("https://", "https://www."))
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()
