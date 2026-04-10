"""Palace subprocess runner — launches and monitors palace simulations."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SimulationProgress:
    status: SimulationStatus = SimulationStatus.PENDING
    progress_pct: float = 0.0
    elapsed_seconds: float = 0.0
    eta_seconds: float | None = None
    current_step: int = 0
    total_steps: int | None = None
    log_tail: list[str] = field(default_factory=list)
    return_code: int | None = None
    error_message: str | None = None


@dataclass
class SimulationRun:
    """Tracks a single palace simulation run."""

    run_id: str
    config_path: Path
    output_dir: Path
    process: asyncio.subprocess.Process | None = None
    progress: SimulationProgress = field(default_factory=SimulationProgress)
    start_time: float | None = None
    _log_lines: list[str] = field(default_factory=list)


# Patterns for parsing Palace log output
_FREQ_STEP_RE = re.compile(
    r"Step\s+(\d+)\s+/\s+(\d+).*frequency", re.IGNORECASE
)
_EIGEN_RE = re.compile(
    r"Eigenvalue\s+(\d+)\s+/\s+(\d+)", re.IGNORECASE
)
_TIME_STEP_RE = re.compile(
    r"Time step\s+(\d+)\s+/\s+(\d+)", re.IGNORECASE
)
_RESIDUAL_RE = re.compile(
    r"residual norm\s*=\s*([\d.eE+-]+)", re.IGNORECASE
)


class PalaceRunner:
    """Manages Palace simulation subprocesses."""

    def __init__(self, palace_binary: str, max_cores: int = 0) -> None:
        self._binary = palace_binary
        self._max_cores = max_cores
        self._runs: dict[str, SimulationRun] = {}

    @property
    def runs(self) -> dict[str, SimulationRun]:
        return self._runs

    def _find_binary(self) -> str:
        if Path(self._binary).is_file():
            return self._binary
        found = shutil.which(self._binary)
        if found:
            return found
        raise FileNotFoundError(
            f"Palace binary not found: {self._binary}. "
            "Set PALACE_BINARY env var to the correct path."
        )

    async def start_simulation(
        self,
        run_id: str,
        config_path: Path,
        output_dir: Path,
        num_procs: int = 1,
        timeout: int = 86400,
    ) -> SimulationRun:
        binary = self._find_binary()
        output_dir.mkdir(parents=True, exist_ok=True)

        if self._max_cores > 0:
            num_procs = min(num_procs, self._max_cores)

        cmd: list[str] = []
        if num_procs > 1:
            mpirun = shutil.which("mpirun") or shutil.which("mpiexec") or "mpirun"
            cmd = [mpirun, "-np", str(num_procs)]
        cmd.extend([binary, str(config_path)])

        run = SimulationRun(
            run_id=run_id,
            config_path=config_path,
            output_dir=output_dir,
        )
        self._runs[run_id] = run

        run.progress.status = SimulationStatus.RUNNING
        run.start_time = time.time()

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(output_dir),
        )
        run.process = process

        # Start background log reader
        asyncio.create_task(self._read_output(run, timeout))
        return run

    async def _read_output(self, run: SimulationRun, timeout: int) -> None:
        assert run.process is not None
        assert run.process.stdout is not None
        try:
            while True:
                try:
                    line_bytes = await asyncio.wait_for(
                        run.process.stdout.readline(), timeout=timeout
                    )
                except asyncio.TimeoutError:
                    run.process.kill()
                    run.progress.status = SimulationStatus.FAILED
                    run.progress.error_message = f"Simulation timed out after {timeout}s"
                    return

                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="replace").rstrip()
                run._log_lines.append(line)
                # Keep only last 200 lines in tail
                run.progress.log_tail = run._log_lines[-200:]
                self._parse_progress(run, line)

            await run.process.wait()
            run.progress.return_code = run.process.returncode
            if run.start_time:
                run.progress.elapsed_seconds = time.time() - run.start_time

            if run.process.returncode == 0:
                run.progress.status = SimulationStatus.COMPLETED
                run.progress.progress_pct = 100.0
            else:
                run.progress.status = SimulationStatus.FAILED
                run.progress.error_message = (
                    f"Palace exited with code {run.process.returncode}"
                )
        except Exception as exc:
            run.progress.status = SimulationStatus.FAILED
            run.progress.error_message = str(exc)
            logger.exception("Error reading Palace output for run %s", run.run_id)

    def _parse_progress(self, run: SimulationRun, line: str) -> None:
        for pattern in (_FREQ_STEP_RE, _EIGEN_RE, _TIME_STEP_RE):
            m = pattern.search(line)
            if m:
                current = int(m.group(1))
                total = int(m.group(2))
                run.progress.current_step = current
                run.progress.total_steps = total
                if total > 0:
                    run.progress.progress_pct = (current / total) * 100.0
                if run.start_time and current > 0:
                    elapsed = time.time() - run.start_time
                    run.progress.elapsed_seconds = elapsed
                    remaining_steps = total - current
                    time_per_step = elapsed / current
                    run.progress.eta_seconds = remaining_steps * time_per_step
                return

    def get_status(self, run_id: str) -> SimulationProgress | None:
        run = self._runs.get(run_id)
        if run is None:
            return None
        if run.start_time:
            run.progress.elapsed_seconds = time.time() - run.start_time
        return run.progress

    async def cancel_simulation(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if run is None or run.process is None:
            return False
        run.process.kill()
        await run.process.wait()
        run.progress.status = SimulationStatus.FAILED
        run.progress.error_message = "Cancelled by user"
        return True
