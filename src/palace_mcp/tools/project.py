"""Project management MCP tools."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_DIRS = ["scripts", "mesh", "config", "results", "results/paraview"]
MANIFEST = "project.json"


def _resolve_project(projects_dir: Path, name: str) -> Path:
    """Resolve and validate a project path, preventing path traversal."""
    project_dir = (projects_dir / name).resolve()
    if not str(project_dir).startswith(str(projects_dir.resolve())):
        raise ValueError(f"Invalid project name: {name}")
    return project_dir


def create_project(
    projects_dir: Path,
    name: str,
    description: str = "",
    palace_version: str = "",
) -> dict[str, Any]:
    """Create a new project directory with standard structure."""
    project_dir = _resolve_project(projects_dir, name)
    if project_dir.exists():
        raise FileExistsError(f"Project '{name}' already exists at {project_dir}")

    for subdir in PROJECT_DIRS:
        (project_dir / subdir).mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": name,
        "description": description,
        "created": datetime.now(timezone.utc).isoformat(),
        "palace_version": palace_version,
        "runs": [],
    }
    manifest_path = project_dir / MANIFEST
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return {
        "project_dir": str(project_dir),
        "manifest": manifest,
    }


def list_projects(projects_dir: Path) -> list[dict[str, Any]]:
    """List all projects in the projects directory."""
    projects: list[dict[str, Any]] = []
    if not projects_dir.is_dir():
        return projects
    for item in sorted(projects_dir.iterdir()):
        manifest_file = item / MANIFEST
        if item.is_dir() and manifest_file.is_file():
            try:
                manifest = json.loads(manifest_file.read_text())
                projects.append({
                    "name": manifest.get("name", item.name),
                    "description": manifest.get("description", ""),
                    "created": manifest.get("created", ""),
                    "runs_count": len(manifest.get("runs", [])),
                    "path": str(item),
                })
            except json.JSONDecodeError:
                projects.append({
                    "name": item.name,
                    "description": "(corrupt manifest)",
                    "path": str(item),
                })
    return projects


def get_project(projects_dir: Path, name: str) -> dict[str, Any]:
    """Get full project manifest and file listing."""
    project_dir = _resolve_project(projects_dir, name)
    manifest_path = project_dir / MANIFEST
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Project '{name}' not found")

    manifest = json.loads(manifest_path.read_text())

    files: dict[str, list[str]] = {}
    for subdir in PROJECT_DIRS:
        subdir_path = project_dir / subdir
        if subdir_path.is_dir():
            files[subdir] = [
                f.name for f in subdir_path.iterdir() if f.is_file()
            ]

    return {
        "manifest": manifest,
        "files": files,
        "path": str(project_dir),
    }


def add_run_to_manifest(
    project_dir: Path,
    run_id: str,
    config_file: str,
    parameters: dict[str, Any] | None = None,
) -> None:
    """Record a new simulation run in the project manifest."""
    manifest_path = project_dir / MANIFEST
    manifest = json.loads(manifest_path.read_text())
    manifest["runs"].append({
        "run_id": run_id,
        "config": config_file,
        "parameters": parameters or {},
        "started": datetime.now(timezone.utc).isoformat(),
        "status": "running",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2))


def update_run_status(
    project_dir: Path, run_id: str, status: str, results_summary: dict[str, Any] | None = None
) -> None:
    """Update the status of a run in the project manifest."""
    manifest_path = project_dir / MANIFEST
    manifest = json.loads(manifest_path.read_text())
    for run in manifest["runs"]:
        if run["run_id"] == run_id:
            run["status"] = status
            run["finished"] = datetime.now(timezone.utc).isoformat()
            if results_summary:
                run["results_summary"] = results_summary
            break
    manifest_path.write_text(json.dumps(manifest, indent=2))


def delete_project(projects_dir: Path, name: str) -> bool:
    """Delete a project directory."""
    project_dir = _resolve_project(projects_dir, name)
    if not project_dir.is_dir():
        return False
    shutil.rmtree(project_dir)
    return True


def get_file(projects_dir: Path, project_name: str, relative_path: str) -> Path:
    """Resolve a file path within a project, with path traversal protection."""
    project_dir = _resolve_project(projects_dir, project_name)
    file_path = (project_dir / relative_path).resolve()
    if not str(file_path).startswith(str(project_dir)):
        raise ValueError(f"Path traversal detected: {relative_path}")
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {relative_path}")
    return file_path
