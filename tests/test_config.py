"""Tests for palace_mcp.config — ServerConfig."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from palace_mcp.config import ServerConfig


class TestServerConfigDefaults:
    """ServerConfig uses sensible defaults when no env vars are set."""

    def test_default_port(self):
        cfg = ServerConfig()
        assert cfg.port == 8000

    def test_default_host(self):
        cfg = ServerConfig()
        assert cfg.host == "0.0.0.0"

    def test_default_script_timeout(self):
        cfg = ServerConfig()
        assert cfg.script_timeout == 300

    def test_default_simulation_timeout(self):
        cfg = ServerConfig()
        assert cfg.simulation_timeout == 86400

    def test_default_max_cores(self):
        cfg = ServerConfig()
        assert cfg.max_cores == 0

    def test_default_max_memory_gb(self):
        cfg = ServerConfig()
        assert cfg.max_memory_gb == 0.0

    def test_projects_dir_is_absolute(self):
        cfg = ServerConfig()
        assert cfg.projects_dir.is_absolute()

    def test_docs_dir_points_to_data(self):
        cfg = ServerConfig()
        assert cfg.docs_dir.name == "docs"
        assert "data" in str(cfg.docs_dir)


class TestServerConfigEnvOverrides:
    """ServerConfig reads overrides from environment variables."""

    @mock.patch.dict(os.environ, {"PALACE_MCP_PORT": "9999"})
    def test_port_override(self):
        cfg = ServerConfig()
        assert cfg.port == 9999

    @mock.patch.dict(os.environ, {"PALACE_MCP_HOST": "127.0.0.1"})
    def test_host_override(self):
        cfg = ServerConfig()
        assert cfg.host == "127.0.0.1"

    @mock.patch.dict(os.environ, {"PALACE_SCRIPT_TIMEOUT": "60"})
    def test_script_timeout_override(self):
        cfg = ServerConfig()
        assert cfg.script_timeout == 60

    @mock.patch.dict(os.environ, {"PALACE_SIM_TIMEOUT": "3600"})
    def test_simulation_timeout_override(self):
        cfg = ServerConfig()
        assert cfg.simulation_timeout == 3600

    @mock.patch.dict(os.environ, {"PALACE_MAX_CORES": "4"})
    def test_max_cores_override(self):
        cfg = ServerConfig()
        assert cfg.max_cores == 4

    @mock.patch.dict(os.environ, {"PALACE_MAX_MEMORY_GB": "16.5"})
    def test_max_memory_gb_override(self):
        cfg = ServerConfig()
        assert cfg.max_memory_gb == 16.5

    @mock.patch.dict(os.environ, {"PALACE_PROJECTS_DIR": "/tmp/test_projects"})
    def test_projects_dir_override(self):
        cfg = ServerConfig()
        assert "test_projects" in str(cfg.projects_dir)

    @mock.patch.dict(os.environ, {"PALACE_BINARY": "/usr/local/bin/palace"})
    def test_palace_binary_override(self):
        cfg = ServerConfig()
        assert cfg.palace_binary == "/usr/local/bin/palace"


class TestServerConfigEnsureDirs:
    """ensure_dirs() creates the projects directory."""

    def test_ensure_dirs_creates_directory(self, tmp_path: Path):
        cfg = ServerConfig()
        cfg.projects_dir = tmp_path / "new_projects"
        assert not cfg.projects_dir.exists()
        cfg.ensure_dirs()
        assert cfg.projects_dir.exists()

    def test_ensure_dirs_idempotent(self, tmp_path: Path):
        cfg = ServerConfig()
        cfg.projects_dir = tmp_path / "projects"
        cfg.ensure_dirs()
        cfg.ensure_dirs()  # Should not raise
        assert cfg.projects_dir.exists()
