"""Tests for palace_mcp.palace (PalaceRunner, SimulationProgress, etc.)."""

from __future__ import annotations

import asyncio
import re

import pytest

from palace_mcp.palace import (
    PalaceRunner,
    SimulationProgress,
    SimulationStatus,
    _FREQ_STEP_RE,
    _EIGEN_RE,
    _TIME_STEP_RE,
)


class TestSimulationStatus:
    def test_enum_values(self):
        assert SimulationStatus.PENDING == "pending"
        assert SimulationStatus.RUNNING == "running"
        assert SimulationStatus.COMPLETED == "completed"
        assert SimulationStatus.FAILED == "failed"


class TestSimulationProgress:
    def test_defaults(self):
        p = SimulationProgress()
        assert p.status == SimulationStatus.PENDING
        assert p.progress_pct == 0.0
        assert p.current_step == 0
        assert p.return_code is None
        assert p.error_message is None


class TestProgressRegexPatterns:
    def test_freq_step_pattern(self):
        line = "Step 5 / 100 at frequency 5.5 GHz"
        m = _FREQ_STEP_RE.search(line)
        assert m is not None
        assert m.group(1) == "5"
        assert m.group(2) == "100"

    def test_eigen_pattern(self):
        line = "Eigenvalue 3 / 10 converged"
        m = _EIGEN_RE.search(line)
        assert m is not None
        assert m.group(1) == "3"
        assert m.group(2) == "10"

    def test_time_step_pattern(self):
        line = "Time step 42 / 1000 completed"
        m = _TIME_STEP_RE.search(line)
        assert m is not None
        assert m.group(1) == "42"
        assert m.group(2) == "1000"


class TestPalaceRunner:
    def test_init(self):
        runner = PalaceRunner("palace", max_cores=4)
        assert runner._binary == "palace"
        assert runner._max_cores == 4

    def test_get_status_nonexistent(self):
        runner = PalaceRunner("palace")
        assert runner.get_status("nonexistent") is None

    def test_runs_initially_empty(self):
        runner = PalaceRunner("palace")
        assert runner.runs == {}

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self):
        runner = PalaceRunner("palace")
        result = await runner.cancel_simulation("nonexistent")
        assert result is False
