"""Shared test fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture
def tmp_home(tmp_path: Path) -> Path:
    """Create a temporary home directory with .todo/ structure."""
    todo_dir = tmp_path / ".todo"
    todo_dir.mkdir()
    return tmp_path


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """Return a sample config dictionary."""
    return {
        "categories": ["Work", "Family", "Hobbies", "Health", "Finance", "Education", "Social"],
        "defaults": {
            "category": "Work",
            "priority": 3,
            "projects_roots": ["~/projects", "~/work"],
        },
    }


@pytest.fixture
def sample_config_file(tmp_home: Path, sample_config: dict[str, Any]) -> Path:
    """Create a sample config.yml in the tmp home."""
    config_path = tmp_home / ".todo" / "config.yml"
    config_path.write_text(yaml.dump(sample_config))
    return config_path


@pytest.fixture
def sample_todo_data() -> dict[str, Any]:
    """Return a sample TODO dictionary."""
    now = datetime.now(UTC).isoformat()
    return {
        "id": "a3f7b2",
        "title": "Implement auth middleware",
        "description": "Add JWT validation to all API routes",
        "priority": 1,
        "category": "Work",
        "project": "cli-tools",
        "status": "todo",
        "tags": ["backend", "auth"],
        "due_date": "2026-04-01",
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def sample_todos_file(tmp_home: Path, sample_todo_data: dict[str, Any]) -> Path:
    """Create a sample todos.yml in the tmp home."""
    todos_path = tmp_home / ".todo" / "todos.yml"
    todos_path.write_text(yaml.dump({"todos": [sample_todo_data]}))
    return todos_path


@pytest.fixture
def mock_home(tmp_home: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Monkeypatch HOME to tmp_home so all code uses the temp directory."""
    monkeypatch.setenv("HOME", str(tmp_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_home))  # type: ignore[arg-type]
    return tmp_home


@pytest.fixture
def project_dir(tmp_home: Path) -> Path:
    """Create a fake project directory under projects_roots."""
    proj = tmp_home / "projects" / "my-project"
    proj.mkdir(parents=True)
    return proj
