"""Long-term vector memory for Autopsy self-correction."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb

STANDARD_PRACTICE_RCE_ID = "standard-practice-rce-fixed-args"
STANDARD_PRACTICE_RCE_TEXT = (
    "RCE requires untrusted input flow; static subprocess calls with shell=False are safe."
)


class VectorMemory:
    """ChromaDB-backed store for vulnerability corrections (past mistakes)."""

    COLLECTION_NAME = "autopsy_corrections"

    def __init__(self, persist_dir: Path | str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        self.persist_dir = Path(persist_dir or root / "data" / "chroma")
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_standard_practice(
        self,
        *,
        memory_id: str,
        rule: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Upsert an immutable standard-practice memory node."""
        meta = {
            "type": "standard_practice",
            "rule": rule,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        self._collection.upsert(
            ids=[memory_id],
            documents=[f"Standard Practice: {rule}"],
            metadatas=[meta],
        )
        return memory_id

    def ensure_standard_practices(self) -> None:
        """Seed required standard practices (idempotent upsert)."""
        self.upsert_standard_practice(
            memory_id=STANDARD_PRACTICE_RCE_ID,
            rule=STANDARD_PRACTICE_RCE_TEXT,
            metadata={"category": "RCE", "pattern": "fixed-args-subprocess"},
        )

    def has_standard_practice(self, memory_id: str) -> bool:
        try:
            result = self._collection.get(ids=[memory_id])
            return bool(result.get("ids"))
        except Exception:
            return False

    def store_correction(
        self,
        *,
        vulnerability: str,
        corrected_logic: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Persist a corrected finding as a memory node."""
        memory_id = str(uuid.uuid4())
        document = (
            f"Vulnerability: {vulnerability}\n"
            f"Corrected Logic: {corrected_logic}"
        )
        meta = {
            "vulnerability": vulnerability,
            "corrected_logic": corrected_logic,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        self._collection.add(
            ids=[memory_id],
            documents=[document],
            metadatas=[meta],
        )
        return memory_id

    def query_past_mistakes(self, query: str, *, n_results: int = 5) -> str:
        """Return formatted past-mistake context for Codebreaker pre-fetch."""
        if self._collection.count() == 0:
            return ""

        results = self._collection.query(
            query_texts=[query],
            n_results=min(n_results, self._collection.count()),
        )
        documents = results.get("documents", [[]])[0]
        if not documents:
            return ""

        lines = ["Past mistakes and standard practices to apply:"]
        for idx, doc in enumerate(documents, start=1):
            lines.append(f"{idx}. {doc}")
        return "\n".join(lines)

    def count(self) -> int:
        return self._collection.count()

    def get_recent_corrections(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent memory nodes (for validation)."""
        if self._collection.count() == 0:
            return []
        data = self._collection.get(limit=limit)
        items: list[dict[str, Any]] = []
        for idx, doc_id in enumerate(data.get("ids", [])):
            meta = (data.get("metadatas") or [{}])[idx] or {}
            doc = (data.get("documents") or [""])[idx]
            items.append({"id": doc_id, "document": doc, "metadata": meta})
        return items

    def get_by_id(self, memory_id: str) -> dict[str, Any] | None:
        try:
            data = self._collection.get(ids=[memory_id])
            if not data.get("ids"):
                return None
            return {
                "id": data["ids"][0],
                "document": (data.get("documents") or [""])[0],
                "metadata": (data.get("metadatas") or [{}])[0],
            }
        except Exception:
            return None
