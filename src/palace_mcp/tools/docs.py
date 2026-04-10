"""Palace documentation search tools."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DocSnippet:
    """A search result from the documentation."""

    file: str
    title: str
    content: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "title": self.title,
            "content": self.content,
            "score": self.score,
        }


class DocsIndex:
    """Full-text search index over Palace documentation files."""

    def __init__(self, docs_dir: Path) -> None:
        self._docs_dir = docs_dir
        self._documents: list[dict[str, str]] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._documents = []
        if not self._docs_dir.is_dir():
            return
        for md_file in sorted(self._docs_dir.rglob("*.md")):
            content = md_file.read_text(encoding="utf-8", errors="replace")
            title = self._extract_title(content)
            self._documents.append({
                "file": str(md_file.relative_to(self._docs_dir)),
                "title": title,
                "content": content,
            })
        for txt_file in sorted(self._docs_dir.rglob("*.txt")):
            content = txt_file.read_text(encoding="utf-8", errors="replace")
            self._documents.append({
                "file": str(txt_file.relative_to(self._docs_dir)),
                "title": txt_file.stem,
                "content": content,
            })
        self._loaded = True

    @staticmethod
    def _extract_title(content: str) -> str:
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    def search(self, query: str, max_results: int = 5) -> list[DocSnippet]:
        """Search documentation for a query string.

        Uses simple term-frequency scoring with snippet extraction.
        """
        self._ensure_loaded()

        if not query.strip():
            return []

        terms = re.split(r"\s+", query.lower().strip())
        results: list[DocSnippet] = []

        for doc in self._documents:
            content_lower = doc["content"].lower()
            score = 0.0
            for term in terms:
                count = content_lower.count(term)
                if count > 0:
                    score += count / max(len(content_lower.split()), 1)

            if score > 0:
                snippet = self._extract_snippet(doc["content"], terms)
                results.append(DocSnippet(
                    file=doc["file"],
                    title=doc["title"],
                    content=snippet,
                    score=score,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    @staticmethod
    def _extract_snippet(content: str, terms: list[str], window: int = 300) -> str:
        """Extract a snippet around the first occurrence of any search term."""
        content_lower = content.lower()
        best_pos = len(content)
        for term in terms:
            pos = content_lower.find(term)
            if pos != -1 and pos < best_pos:
                best_pos = pos

        if best_pos == len(content):
            return content[:window]

        start = max(0, best_pos - window // 2)
        end = min(len(content), best_pos + window)
        snippet = content[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def list_topics(self) -> list[dict[str, str]]:
        """List all available documentation topics."""
        self._ensure_loaded()
        return [
            {"file": doc["file"], "title": doc["title"]}
            for doc in self._documents
        ]

    def get_document(self, file_path: str) -> str | None:
        """Get the full content of a specific documentation file."""
        self._ensure_loaded()
        for doc in self._documents:
            if doc["file"] == file_path:
                return doc["content"]
        return None
