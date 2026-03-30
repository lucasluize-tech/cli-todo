"""Tests for Rich output formatting."""

from __future__ import annotations

from rich.console import Console

from todo.models import Priority, Status, Todo
from todo.renderer import render_todo_detail, render_todo_table


def _capture(func, *args, **kwargs) -> str:
    console = Console(file=None, force_terminal=True, width=120)
    from io import StringIO

    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    func(*args, console=console, **kwargs)
    return buf.getvalue()


class TestRenderTable:
    def test_table_has_expected_columns(self):
        todos = [Todo(id="abc123", title="Test task", category="Work")]
        output = _capture(render_todo_table, todos)
        assert "ID" in output
        assert "Pri" in output
        assert "Title" in output
        assert "Category" in output
        assert "Status" in output

    def test_table_shows_todo_data(self):
        todos = [Todo(id="abc123", title="Buy milk", category="Family", priority=Priority.HIGH)]
        output = _capture(render_todo_table, todos)
        assert "abc123" in output
        assert "Buy milk" in output
        assert "Family" in output
        assert "High" in output

    def test_empty_list_message(self):
        output = _capture(render_todo_table, [])
        assert "No TODOs found" in output

    def test_overdue_item_marked(self):
        todos = [
            Todo(
                id="abc123",
                title="Overdue task",
                category="Work",
                due_date="2020-01-01",
            )
        ]
        output = _capture(render_todo_table, todos)
        assert "OVERDUE" in output or "2020-01-01" in output

    def test_multiple_todos_rendered(self):
        todos = [
            Todo(id="aaa111", title="First", category="Work"),
            Todo(id="bbb222", title="Second", category="Family"),
        ]
        output = _capture(render_todo_table, todos)
        assert "First" in output
        assert "Second" in output


class TestRenderDetail:
    def test_detail_shows_all_fields(self):
        todo = Todo(
            id="abc123",
            title="Detailed task",
            description="Full description here",
            priority=Priority.CRITICAL,
            category="Work",
            project="my-project",
            status=Status.IN_PROGRESS,
            tags=["urgent", "api"],
            due_date="2026-04-01",
        )
        output = _capture(render_todo_detail, todo)
        assert "abc123" in output
        assert "Detailed task" in output
        assert "Full description here" in output
        assert "Critical" in output
        assert "Work" in output
        assert "my-project" in output
        assert "in_progress" in output
        assert "urgent" in output
        assert "2026-04-01" in output

    def test_detail_omits_empty_optional_fields(self):
        todo = Todo(id="abc123", title="Simple task", category="Work")
        output = _capture(render_todo_detail, todo)
        assert "abc123" in output
        assert "Simple task" in output
