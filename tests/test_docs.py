"""Tests for palace_mcp.tools.docs."""

from __future__ import annotations

from pathlib import Path

import pytest

from palace_mcp.tools.docs import DocSnippet, DocsIndex


@pytest.fixture()
def docs_dir(tmp_path: Path) -> Path:
    """Create a temporary docs directory with sample files."""
    d = tmp_path / "docs"
    d.mkdir()

    (d / "getting_started.md").write_text(
        "# Getting Started\n\n"
        "Palace is an electromagnetic simulation tool for quantum devices.\n"
        "Install Palace using pip or from source.\n"
    )
    (d / "boundaries.md").write_text(
        "# Boundary Conditions\n\n"
        "Palace supports PEC, PMC, impedance, and absorbing boundaries.\n"
        "Use LumpedPort for driven simulations.\n"
    )
    (d / "solver.md").write_text(
        "# Solver Settings\n\n"
        "The eigenmode solver uses SLEPc for computing resonant frequencies.\n"
        "Set Solver.Eigenmode.N to control the number of modes.\n"
    )
    return d


class TestDocsIndex:
    def test_search_returns_results(self, docs_dir: Path):
        idx = DocsIndex(docs_dir)
        results = idx.search("eigenmode solver")
        assert len(results) > 0
        assert any("solver" in r.file for r in results)

    def test_search_empty_query(self, docs_dir: Path):
        idx = DocsIndex(docs_dir)
        results = idx.search("")
        assert results == []

    def test_search_no_match(self, docs_dir: Path):
        idx = DocsIndex(docs_dir)
        results = idx.search("xyznonexistent123")
        assert results == []

    def test_search_respects_max_results(self, docs_dir: Path):
        idx = DocsIndex(docs_dir)
        results = idx.search("Palace", max_results=1)
        assert len(results) <= 1

    def test_search_results_sorted_by_score(self, docs_dir: Path):
        idx = DocsIndex(docs_dir)
        results = idx.search("boundary PEC")
        if len(results) >= 2:
            assert results[0].score >= results[1].score

    def test_list_topics(self, docs_dir: Path):
        idx = DocsIndex(docs_dir)
        topics = idx.list_topics()
        assert len(topics) == 3
        titles = [t["title"] for t in topics]
        assert "Getting Started" in titles
        assert "Boundary Conditions" in titles
        assert "Solver Settings" in titles

    def test_get_document_found(self, docs_dir: Path):
        idx = DocsIndex(docs_dir)
        content = idx.get_document("solver.md")
        assert content is not None
        assert "eigenmode" in content.lower()

    def test_get_document_not_found(self, docs_dir: Path):
        idx = DocsIndex(docs_dir)
        assert idx.get_document("nonexistent.md") is None

    def test_empty_docs_dir(self, tmp_path: Path):
        empty = tmp_path / "empty_docs"
        empty.mkdir()
        idx = DocsIndex(empty)
        assert idx.search("anything") == []
        assert idx.list_topics() == []

    def test_nonexistent_docs_dir(self, tmp_path: Path):
        idx = DocsIndex(tmp_path / "no_such_dir")
        assert idx.search("anything") == []
        assert idx.list_topics() == []


class TestDocSnippet:
    def test_to_dict(self):
        snippet = DocSnippet(
            file="test.md", title="Test", content="Some content", score=0.5
        )
        d = snippet.to_dict()
        assert d["file"] == "test.md"
        assert d["title"] == "Test"
        assert d["content"] == "Some content"
        assert d["score"] == 0.5
