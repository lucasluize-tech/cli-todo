"""Tests for Pydantic models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from todo.models import Priority, Status, Todo, TodoConfig


class TestPriority:
    def test_priority_values(self):
        assert Priority.CRITICAL == 1
        assert Priority.HIGH == 2
        assert Priority.MEDIUM == 3
        assert Priority.LOW == 4
        assert Priority.NONE == 5

    def test_priority_label(self):
        assert Priority.CRITICAL.label == "Critical"
        assert Priority.HIGH.label == "High"
        assert Priority.MEDIUM.label == "Medium"
        assert Priority.LOW.label == "Low"
        assert Priority.NONE.label == "None"

    def test_priority_color(self):
        assert Priority.CRITICAL.color == "red"
        assert Priority.HIGH.color == "orange3"
        assert Priority.MEDIUM.color == "yellow"
        assert Priority.LOW.color == "dodger_blue2"
        assert Priority.NONE.color == "dim"


class TestStatus:
    def test_status_values(self):
        assert Status.TODO == "todo"
        assert Status.IN_PROGRESS == "in_progress"
        assert Status.DONE == "done"
        assert Status.ARCHIVED == "archived"


class TestTodo:
    def test_create_with_required_fields(self):
        todo = Todo(title="Buy groceries", category="Work")
        assert todo.title == "Buy groceries"
        assert todo.category == "Work"
        assert len(todo.id) == 6
        assert todo.priority == Priority.MEDIUM
        assert todo.status == Status.TODO
        assert todo.description == ""
        assert todo.project is None
        assert todo.tags == []
        assert todo.due_date is None
        assert todo.completed_at is None
        assert todo.created_at is not None
        assert todo.updated_at is not None

    def test_create_with_all_fields(self):
        now = datetime.now(UTC)
        todo = Todo(
            id="abc123",
            title="Test todo",
            description="A detailed description",
            priority=Priority.HIGH,
            category="Family",
            project="my-project",
            status=Status.IN_PROGRESS,
            tags=["urgent", "frontend"],
            due_date="2026-04-01",
            created_at=now,
            updated_at=now,
        )
        assert todo.id == "abc123"
        assert todo.priority == Priority.HIGH
        assert todo.tags == ["urgent", "frontend"]
        assert todo.due_date == "2026-04-01"

    def test_auto_generated_id_is_6_chars(self):
        todo = Todo(title="Test", category="Work")
        assert len(todo.id) == 6
        assert todo.id.isalnum()

    def test_unique_ids_generated(self):
        ids = {Todo(title="Test", category="Work").id for _ in range(20)}
        assert len(ids) == 20  # all unique

    def test_timestamps_auto_populated(self):
        before = datetime.now(UTC)
        todo = Todo(title="Test", category="Work")
        after = datetime.now(UTC)
        assert before <= todo.created_at <= after
        assert before <= todo.updated_at <= after

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValueError):
            Todo(title="Test", category="Work", priority=0)
        with pytest.raises(ValueError):
            Todo(title="Test", category="Work", priority=6)
        with pytest.raises(ValueError):
            Todo(title="Test", category="Work", priority=-1)

    def test_invalid_status_rejected(self):
        with pytest.raises(ValueError):
            Todo(title="Test", category="Work", status="invalid")

    def test_empty_title_rejected(self):
        with pytest.raises(ValueError):
            Todo(title="", category="Work")

    def test_valid_due_date_accepted(self):
        todo = Todo(title="Test", category="Work", due_date="2026-04-01")
        assert todo.due_date == "2026-04-01"

    def test_invalid_due_date_rejected(self):
        with pytest.raises(ValueError):
            Todo(title="Test", category="Work", due_date="not-a-date")

    def test_invalid_due_date_partial_rejected(self):
        with pytest.raises(ValueError):
            Todo(title="Test", category="Work", due_date="2026-13-01")

    def test_none_due_date_accepted(self):
        todo = Todo(title="Test", category="Work", due_date=None)
        assert todo.due_date is None

    def test_valid_project_name_accepted(self):
        todo = Todo(title="Test", category="Work", project="my-project_v2")
        assert todo.project == "my-project_v2"

    def test_project_name_rejects_path_traversal(self):
        with pytest.raises(ValueError):
            Todo(title="Test", category="Work", project="../../etc")

    def test_project_name_rejects_slashes(self):
        with pytest.raises(ValueError):
            Todo(title="Test", category="Work", project="foo/bar")

    def test_none_project_accepted(self):
        todo = Todo(title="Test", category="Work", project=None)
        assert todo.project is None

    def test_priority_int_coerced_to_enum(self):
        todo = Todo(title="Test", category="Work", priority=1)
        assert todo.priority == Priority.CRITICAL

    def test_to_dict_roundtrip(self):
        todo = Todo(id="abc123", title="Test", category="Work")
        d = todo.model_dump()
        assert d["id"] == "abc123"
        assert d["title"] == "Test"
        restored = Todo(**d)
        assert restored.id == todo.id
        assert restored.title == todo.title


class TestTodoConfig:
    def test_default_config(self):
        config = TodoConfig()
        assert "Work" in config.categories
        assert config.defaults.category == "Work"
        assert config.defaults.priority == Priority.MEDIUM

    def test_custom_categories(self):
        config = TodoConfig(categories=["Pets", "Garden"])
        assert config.categories == ["Pets", "Garden"]

    def test_custom_defaults(self):
        from todo.models import ConfigDefaults

        config = TodoConfig(defaults=ConfigDefaults(category="Family", priority=Priority.HIGH))
        assert config.defaults.category == "Family"
        assert config.defaults.priority == Priority.HIGH

    def test_projects_roots_default(self):
        config = TodoConfig()
        assert "~/projects" in config.defaults.projects_roots
        assert "~/work" in config.defaults.projects_roots
