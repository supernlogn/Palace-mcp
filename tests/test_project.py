"""Tests for palace_mcp.tools.project."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from palace_mcp.tools.project import (
    MANIFEST,
    _resolve_project,
    add_run_to_manifest,
    create_project,
    delete_project,
    get_file,
    get_project,
    list_projects,
)


class TestResolveProject:
    def test_valid_name(self, tmp_path: Path):
        result = _resolve_project(tmp_path, "my_project")
        assert result == (tmp_path / "my_project").resolve()

    def test_path_traversal_blocked(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Invalid project name"):
            _resolve_project(tmp_path, "../../etc/passwd")


class TestCreateProject:
    def test_creates_directory_structure(self, tmp_path: Path):
        result = create_project(tmp_path, "test_sim", description="A test")
        project_dir = Path(result["project_dir"])
        assert project_dir.is_dir()
        assert (project_dir / "scripts").is_dir()
        assert (project_dir / "mesh").is_dir()
        assert (project_dir / "config").is_dir()
        assert (project_dir / "results").is_dir()
        assert (project_dir / "results" / "paraview").is_dir()

    def test_creates_manifest(self, tmp_path: Path):
        result = create_project(tmp_path, "test_sim")
        manifest_path = Path(result["project_dir"]) / MANIFEST
        assert manifest_path.is_file()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["name"] == "test_sim"
        assert "created" in manifest
        assert manifest["runs"] == []

    def test_returns_manifest_in_result(self, tmp_path: Path):
        result = create_project(tmp_path, "test_sim", description="desc")
        assert result["manifest"]["name"] == "test_sim"
        assert result["manifest"]["description"] == "desc"

    def test_duplicate_project_raises(self, tmp_path: Path):
        create_project(tmp_path, "dup")
        with pytest.raises(FileExistsError, match="already exists"):
            create_project(tmp_path, "dup")

    def test_palace_version_stored(self, tmp_path: Path):
        result = create_project(tmp_path, "v_test", palace_version="0.12.0")
        assert result["manifest"]["palace_version"] == "0.12.0"


class TestListProjects:
    def test_empty_directory(self, tmp_path: Path):
        assert list_projects(tmp_path) == []

    def test_nonexistent_directory(self, tmp_path: Path):
        assert list_projects(tmp_path / "nope") == []

    def test_lists_existing_projects(self, tmp_path: Path):
        create_project(tmp_path, "proj_a")
        create_project(tmp_path, "proj_b")
        projects = list_projects(tmp_path)
        names = [p["name"] for p in projects]
        assert "proj_a" in names
        assert "proj_b" in names

    def test_ignores_non_project_dirs(self, tmp_path: Path):
        (tmp_path / "random_dir").mkdir()
        assert list_projects(tmp_path) == []


class TestGetProject:
    def test_existing_project(self, tmp_path: Path):
        create_project(tmp_path, "my_proj")
        result = get_project(tmp_path, "my_proj")
        assert result["manifest"]["name"] == "my_proj"
        assert "files" in result

    def test_missing_project_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="not found"):
            get_project(tmp_path, "nonexistent")

    def test_lists_files_in_subdirs(self, tmp_path: Path):
        create_project(tmp_path, "fp")
        # Add a file to mesh/
        (tmp_path / "fp" / "mesh" / "model.msh").write_text("mesh data")
        result = get_project(tmp_path, "fp")
        assert "model.msh" in result["files"]["mesh"]


class TestAddRunToManifest:
    def test_adds_run(self, tmp_path: Path):
        create_project(tmp_path, "run_proj")
        project_dir = tmp_path / "run_proj"
        add_run_to_manifest(project_dir, "abc123", "palace.json")
        manifest = json.loads((project_dir / MANIFEST).read_text())
        assert len(manifest["runs"]) == 1
        assert manifest["runs"][0]["run_id"] == "abc123"
        assert manifest["runs"][0]["config"] == "palace.json"
        assert manifest["runs"][0]["status"] == "running"

    def test_adds_run_with_parameters(self, tmp_path: Path):
        create_project(tmp_path, "param_proj")
        project_dir = tmp_path / "param_proj"
        add_run_to_manifest(
            project_dir, "r1", "sweep.json",
            parameters={"Solver.Driven.MinFreq": 2e9},
        )
        manifest = json.loads((project_dir / MANIFEST).read_text())
        assert manifest["runs"][0]["parameters"]["Solver.Driven.MinFreq"] == 2e9


class TestDeleteProject:
    def test_delete_existing(self, tmp_path: Path):
        create_project(tmp_path, "del_me")
        assert delete_project(tmp_path, "del_me") is True
        assert not (tmp_path / "del_me").exists()

    def test_delete_nonexistent(self, tmp_path: Path):
        assert delete_project(tmp_path, "nope") is False


class TestGetFile:
    def test_valid_file(self, tmp_path: Path):
        create_project(tmp_path, "f_proj")
        file = tmp_path / "f_proj" / "config" / "palace.json"
        file.write_text('{"key": "val"}')
        result = get_file(tmp_path, "f_proj", "config/palace.json")
        assert result == file.resolve()

    def test_file_not_found(self, tmp_path: Path):
        create_project(tmp_path, "f_proj")
        with pytest.raises(FileNotFoundError):
            get_file(tmp_path, "f_proj", "config/nonexistent.json")

    def test_path_traversal_blocked(self, tmp_path: Path):
        create_project(tmp_path, "f_proj")
        with pytest.raises(ValueError, match="Path traversal"):
            get_file(tmp_path, "f_proj", "../../etc/passwd")
