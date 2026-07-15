"""Local repository ingestion for Codebreaker source inspection."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".yaml",
        ".yml",
        ".toml",
        ".json",
        ".md",
        ".sql",
        ".lua",
        ".r",
        ".m",
        ".vue",
        ".svelte",
    }
)

DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "venv",
        ".venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
        "build",
        ".next",
        "target",
        "vendor",
        ".tox",
        ".eggs",
        "*.egg-info",
    }
)

BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".wasm",
        ".pyc",
        ".pyo",
        ".class",
        ".o",
        ".a",
        ".lib",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".sqlite",
        ".db",
    }
)


@dataclass
class FileChunk:
    """A bundle of source files sized for Gemini large-context analysis."""

    file_paths: list[str] = field(default_factory=list)
    content: str = ""
    byte_size: int = 0


class RepositoryReader:
    """Walk a local repo, filter scannable text files, and build LLM chunks."""

    CHUNK_MAX_BYTES = 500_000

    def __init__(
        self,
        root: Path | str,
        *,
        max_file_bytes: int = 512_000,
        chunk_max_bytes: int | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.max_file_bytes = max_file_bytes
        self.chunk_max_bytes = chunk_max_bytes or self.CHUNK_MAX_BYTES
        self._gitignore_patterns = self._load_gitignore_patterns()

    def _load_gitignore_patterns(self) -> list[str]:
        gitignore = self.root / ".gitignore"
        if not gitignore.is_file():
            return []
        patterns: list[str] = []
        for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)
        return patterns

    def _path_matches_gitignore(self, rel_path: str) -> bool:
        normalized = rel_path.replace("\\", "/")
        parts = normalized.split("/")
        for pattern in self._gitignore_patterns:
            if fnmatch.fnmatch(normalized, pattern):
                return True
            if fnmatch.fnmatch(parts[-1], pattern):
                return True
            if pattern.endswith("/") and any(
                fnmatch.fnmatch(part, pattern.rstrip("/")) for part in parts
            ):
                return True
        return False

    def _is_ignored_dir(self, name: str) -> bool:
        if name in DEFAULT_IGNORE_DIRS:
            return True
        return any(fnmatch.fnmatch(name, pat) for pat in DEFAULT_IGNORE_DIRS if "*" in pat)

    def discover_files(self) -> list[Path]:
        """Return scannable source files under root, respecting ignore rules."""
        if not self.root.is_dir():
            return []

        discovered: list[Path] = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue

            rel = path.relative_to(self.root)
            rel_str = rel.as_posix()

            if any(self._is_ignored_dir(part) for part in rel.parts[:-1]):
                continue
            if self._path_matches_gitignore(rel_str):
                continue

            suffix = path.suffix.lower()
            if suffix not in SOURCE_EXTENSIONS:
                continue
            if suffix in BINARY_EXTENSIONS:
                continue

            discovered.append(path)
        return discovered

    @staticmethod
    def _is_binary(data: bytes) -> bool:
        if b"\x00" in data[:8192]:
            return True
        try:
            data[:8192].decode("utf-8")
            return False
        except UnicodeDecodeError:
            return True

    def read_file(self, path: Path) -> str | None:
        """Read a text source file; return None for binary or oversized files."""
        try:
            raw = path.read_bytes()
        except OSError:
            return None

        if len(raw) > self.max_file_bytes:
            raw = raw[: self.max_file_bytes]
        if self._is_binary(raw):
            return None

        return raw.decode("utf-8", errors="replace")

    def _format_file_block(self, rel_path: str, text: str) -> str:
        return f"\n--- FILE: {rel_path} ---\n{text}\n"

    def _split_large_text(self, rel_path: str, text: str) -> list[str]:
        """Split an oversized file into sub-blocks that fit chunk limits."""
        header = f"\n--- FILE: {rel_path} (part {{part}}) ---\n"
        max_body = self.chunk_max_bytes - 256
        parts: list[str] = []
        start = 0
        part_num = 1
        while start < len(text):
            end = start + max_body
            block = header.format(part=part_num) + text[start:end]
            parts.append(block)
            start = end
            part_num += 1
        return parts

    def chunk_for_llm(self) -> list[FileChunk]:
        """Group file contents into ~500KB chunks for Gemini analysis."""
        chunks: list[FileChunk] = []
        current_paths: list[str] = []
        current_blocks: list[str] = []
        current_size = 0

        def flush() -> None:
            nonlocal current_paths, current_blocks, current_size
            if not current_blocks:
                return
            content = "".join(current_blocks)
            chunks.append(
                FileChunk(
                    file_paths=list(current_paths),
                    content=content,
                    byte_size=len(content.encode("utf-8")),
                )
            )
            current_paths = []
            current_blocks = []
            current_size = 0

        for path in self.discover_files():
            text = self.read_file(path)
            if text is None:
                continue

            rel = path.relative_to(self.root).as_posix()
            blocks = self._split_large_text(rel, text) if len(text.encode("utf-8")) > self.chunk_max_bytes else [
                self._format_file_block(rel, text)
            ]

            for block in blocks:
                block_size = len(block.encode("utf-8"))
                if block_size > self.chunk_max_bytes:
                    continue

                if current_size + block_size > self.chunk_max_bytes and current_blocks:
                    flush()

                current_paths.append(rel)
                current_blocks.append(block)
                current_size += block_size

        flush()
        return chunks
