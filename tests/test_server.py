"""Tests for palace_mcp.server — _set_nested helper and list_problem_types."""

from __future__ import annotations

import pytest

from palace_mcp.server import _set_nested, _evaluate_objective, list_problem_types
from palace_mcp.palace.result_parser import SimulationResults


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


class TestEvaluateObjective:
    def test_directivity_objective(self):
        r = SimulationResults(
            directivity={"boresight_directivity_dbi": 7.5, "max_directivity_dbi": 10.0}
        )
        assert _evaluate_objective(r, "directivity", 50.0, 10.0) == 7.5

    def test_max_directivity_objective(self):
        r = SimulationResults(
            directivity={"boresight_directivity_dbi": 7.5, "max_directivity_dbi": 10.0}
        )
        assert _evaluate_objective(r, "max_directivity", 50.0, 10.0) == 10.0

    def test_impedance_match_objective(self):
        r = SimulationResults(
            impedances=[{"Z_V1_mag": 50.0}]
        )
        score = _evaluate_objective(r, "impedance_match", 50.0, 10.0)
        assert score == 0.0  # Perfect match → 0% deviation → score = 0

    def test_impedance_match_with_deviation(self):
        r = SimulationResults(
            impedances=[{"Z_V1_mag": 60.0}]
        )
        score = _evaluate_objective(r, "impedance_match", 50.0, 10.0)
        assert score < 0  # Deviation → negative score

    def test_missing_directivity_returns_negative(self):
        r = SimulationResults()
        assert _evaluate_objective(r, "directivity", 50.0, 10.0) == -999.0

    def test_missing_impedances_returns_negative(self):
        r = SimulationResults()
        assert _evaluate_objective(r, "impedance_match", 50.0, 10.0) == -999.0
