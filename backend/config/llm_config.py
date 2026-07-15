"""Central LLM switchboard for CodeSentinel — Groq (fast logic) and Gemini (large code)."""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


class LLMProvider(str, Enum):
    GROQ = "groq"
    GEMINI = "gemini"


class LLMConfig:
    """Switchboard that routes requests to Groq or Gemini based on task profile."""

    # llama-3.1-70b-versatile was decommissioned by Groq (Jan 2025).
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    # gemini-1.5-flash is retired on current API keys; 2.5-flash keeps free-tier quota.
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    MAX_RETRIES = 2  # MVP loop limit: 2 retry attempts maximum

    def __init__(self) -> None:
        self._groq_key = os.getenv("GROQ_API_KEY", "")
        self._gemini_key = os.getenv("GEMINI_API_KEY", "")

    def get_provider(self, *, large_context: bool = False) -> LLMProvider:
        """Select provider: Gemini for large code files, Groq for fast logic."""
        return LLMProvider.GEMINI if large_context else LLMProvider.GROQ

    def _build_groq(self) -> ChatGroq:
        if not self._groq_key:
            raise ValueError("GROQ_API_KEY is not set")
        return ChatGroq(
            model=self.GROQ_MODEL,
            api_key=self._groq_key,
            temperature=0,
            max_retries=self.MAX_RETRIES,
        )

    def _build_gemini(self) -> ChatGoogleGenerativeAI:
        if not self._gemini_key:
            raise ValueError("GEMINI_API_KEY is not set")
        return ChatGoogleGenerativeAI(
            model=self.GEMINI_MODEL,
            google_api_key=self._gemini_key,
            temperature=0,
            max_retries=self.MAX_RETRIES,
        )

    def get_llm(
        self,
        *,
        provider: LLMProvider | None = None,
        large_context: bool = False,
    ) -> BaseChatModel:
        """Return a LangChain chat model for the requested provider."""
        selected = provider or self.get_provider(large_context=large_context)
        if selected == LLMProvider.GROQ:
            return self._build_groq()
        if selected == LLMProvider.GEMINI:
            return self._build_gemini()
        raise ValueError(f"Unknown provider: {selected}")

    def invoke(
        self,
        prompt: str,
        *,
        provider: LLMProvider | None = None,
        large_context: bool = False,
    ) -> str:
        """Send a prompt through the switchboard and return text content."""
        llm = self.get_llm(provider=provider, large_context=large_context)
        response = llm.invoke(prompt)
        return _extract_content(response)

    def health_check(self) -> dict[str, Any]:
        """Ping both providers with a minimal prompt."""
        results: dict[str, Any] = {}
        for provider in LLMProvider:
            try:
                text = self.invoke("Reply with exactly: OK", provider=provider)
                results[provider.value] = {"status": "ok", "response": text.strip()}
            except Exception as exc:
                results[provider.value] = {
                    "status": "error",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
        return results


def _extract_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
        return "".join(parts)
    return str(content)
