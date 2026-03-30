"""Tests for project detection and integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from todo.models import Priority, Status, Todo
from todo.project import detect_project, generate_claude_md_section, generate_todos_md


class TestDetectProject:
    def test_detect_from_project_root(self, tmp_path: Path):
        roots = [str(tmp_path / "projects")]
        proj = tmp_path / "projects" / "my-app"
        proj.mkdir(parents=True)
        assert detect_project(proj, roots) == "my-app"

    def test_detect_from_subdirectory(self, tmp_path: Path):
        roots = [str(tmp_path / "projects")]
        proj = tmp_path / "projects" / "my-app" / "src" / "deep"
        proj.mkdir(parents=True)
        assert detect_project(proj, roots) == "my-app"

    def test_no_match_returns_none(self, tmp_path: Path):
        roots = [str(tmp_path / "projects")]
        assert detect_project(tmp_path / "other" / "dir", roots) is None

    def test_tilde_expansion(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        proj = tmp_path / "projects" / "my-app"
        proj.mkdir(parents=True)
        assert detect_project(proj, ["~/projects"]) == "my-app"

    def test_multiple_roots(self, tmp_path: Path):
        roots = [str(tmp_path / "projects"), str(tmp_path / "work")]
        proj = tmp_path / "work" / "client-app"
        proj.mkdir(parents=True)
        assert detect_project(proj, roots) == "client-app"


class TestGenerateTodosMd:
    def test_generates_markdown(self):
        todos = [
            Todo(
                id="aaa111",
                title="Task one",
                category="Work",
                priority=Priority.CRITICAL,
                status=Status.IN_PROGRESS,
            ),
            Todo(
                id="bbb222",
                title="Task two",
                category="Work",
                priority=Priority.HIGH,
                status=Status.TODO,
            ),
            Todo(id="ccc333", title="Task done", category="Work", status=Status.DONE),
        ]
        md = generate_todos_md("my-project", todos)
        assert "# Project TODOs: my-project" in md
        assert "## In Progress" in md
        assert "## Todo" in md
        assert "## Done" in md
        assert "[aaa111]" in md
        assert "[bbb222]" in md
        assert "~~Task done~~" in md

    def test_excludes_archived(self):
        todos = [
            Todo(id="aaa111", title="Active", category="Work"),
            Todo(id="bbb222", title="Archived", category="Work", status=Status.ARCHIVED),
        ]
        md = generate_todos_md("proj", todos)
        assert "Active" in md
        assert "Archived" not in md

    def test_sorted_by_priority(self):
        todos = [
            Todo(id="low111", title="Low", category="Work", priority=Priority.LOW),
            Todo(id="cri111", title="Critical", category="Work", priority=Priority.CRITICAL),
        ]
        md = generate_todos_md("proj", todos)
        crit_pos = md.index("Critical")
        low_pos = md.index("Low")
        assert crit_pos < low_pos

    def test_empty_todos(self):
        md = generate_todos_md("proj", [])
        assert "# Project TODOs: proj" in md
        assert "No open TODOs" in md


class TestGenerateClaudeMdSection:
    def test_new_file(self, tmp_path: Path):
        claude_md = tmp_path / "CLAUDE.md"
        generate_claude_md_section(claude_md, open_count=3, critical_count=1)
        content = claude_md.read_text()
        assert "<!-- BEGIN TODO CLI -->" in content
        assert "<!-- END TODO CLI -->" in content
        assert "3 open" in content
        assert "1 critical" in content

    def test_update_existing_section(self, tmp_path: Path):
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            "# My Project\n\nSome content.\n\n"
            "<!-- BEGIN TODO CLI -->\nOld content\n<!-- END TODO CLI -->\n\nMore content.\n"
        )
        generate_claude_md_section(claude_md, open_count=5, critical_count=0)
        content = claude_md.read_text()
        assert "5 open" in content
        assert "Old content" not in content
        assert "Some content." in content
        assert "More content." in content

    def test_append_to_existing_file(self, tmp_path: Path):
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# My Project\n\nExisting stuff.\n")
        generate_claude_md_section(claude_md, open_count=2, critical_count=2)
        content = claude_md.read_text()
        assert "Existing stuff." in content
        assert "<!-- BEGIN TODO CLI -->" in content
        assert "2 open" in content

    def test_zero_todos(self, tmp_path: Path):
        claude_md = tmp_path / "CLAUDE.md"
        generate_claude_md_section(claude_md, open_count=0, critical_count=0)
        content = claude_md.read_text()
        assert "0 open" in content
