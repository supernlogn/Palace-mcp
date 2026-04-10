"""Tests for palace_mcp.server — _set_nested helper and list_problem_types."""

from __future__ import annotations

import pytest

from palace_mcp.server import _set_nested, list_problem_types


class TestSetNested:
    def test_simple_key(self):
        d = {"a": 1}
        _set_nested(d, "a", 2)
        assert d["a"] == 2

    def test_nested_key(self):
        d = {"a": {"b": {"c": 1}}}
        _set_nested(d, "a.b.c", 42)
        assert d["a"]["b"]["c"] == 42

    def test_integer_index(self):
        d = {"a": [10, 20, 30]}
        _set_nested(d, "a.1", 99)
        assert d["a"][1] == 99

    def test_mixed_dict_and_list(self):
        d = {"items": [{"value": 1}, {"value": 2}]}
        _set_nested(d, "items.0.value", 100)
        assert d["items"][0]["value"] == 100


class TestListProblemTypes:
    def test_returns_five_types(self):
        types = list_problem_types()
        assert len(types) == 5

    def test_has_type_and_description(self):
        types = list_problem_types()
        for t in types:
            assert "type" in t
            assert "description" in t

    def test_known_types(self):
        names = [t["type"] for t in list_problem_types()]
        assert "Eigenmode" in names
        assert "Driven" in names
        assert "Transient" in names
        assert "Electrostatic" in names
        assert "Magnetostatic" in names
