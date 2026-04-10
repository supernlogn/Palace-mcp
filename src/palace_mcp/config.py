"""Server configuration."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServerConfig:
    """Runtime configuration for the Palace MCP server."""

    palace_binary: str = field(
        default_factory=lambda: os.environ.get(
            "PALACE_BINARY", shutil.which("palace") or "palace"
        )
    )
    projects_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("PALACE_PROJECTS_DIR", "./projects")
        ).resolve()
    )
    docs_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "PALACE_DOCS_DIR",
                str(Path(__file__).parent / "data" / "docs"),
            )
        ).resolve()
    )
    host: str = field(
        default_factory=lambda: os.environ.get("PALACE_MCP_HOST", "0.0.0.0")
    )
    port: int = field(
        default_factory=lambda: int(os.environ.get("PALACE_MCP_PORT", "8000"))
    )
    script_timeout: int = field(
        default_factory=lambda: int(
            os.environ.get("PALACE_SCRIPT_TIMEOUT", "300")
        )
    )
    simulation_timeout: int = field(
        default_factory=lambda: int(
            os.environ.get("PALACE_SIM_TIMEOUT", "86400")
        )
    )
    max_cores: int = field(
        default_factory=lambda: int(os.environ.get("PALACE_MAX_CORES", "0"))
    )
    max_memory_gb: float = field(
        default_factory=lambda: float(
            os.environ.get("PALACE_MAX_MEMORY_GB", "0")
        )
    )

    def ensure_dirs(self) -> None:
        self.projects_dir.mkdir(parents=True, exist_ok=True)
