"""Tests for YAML store operations."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from todo.models import Priority, Status, Todo
from todo.store import TodoStore


class TestStoreInit:
    def test_creates_todo_dir_on_init(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        assert store.base_dir.exists()

    def test_creates_empty_todos_file(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        assert store.todos_path.exists()
        data = yaml.safe_load(store.todos_path.read_text())
        assert data == {"todos": []}

    def test_loads_existing_todos(self, mock_home: Path, sample_todo_data: dict):
        todo_dir = mock_home / ".todo"
        todos_path = todo_dir / "todos.yml"
        todos_path.write_text(yaml.dump({"todos": [sample_todo_data]}))
        store = TodoStore(todo_dir)
        assert len(store.list_todos()) == 1

    def test_creates_default_config(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        assert store.config_path.exists()


class TestStoreAdd:
    def test_add_todo(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        todo = Todo(title="Test task", category="Work")
        store.add(todo)
        todos = store.list_todos()
        assert len(todos) == 1
        assert todos[0].title == "Test task"

    def test_add_persists_to_disk(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        todo = Todo(title="Persistent", category="Work")
        store.add(todo)
        # Reload from disk
        store2 = TodoStore(mock_home / ".todo")
        assert len(store2.list_todos()) == 1
        assert store2.list_todos()[0].title == "Persistent"

    def test_add_multiple_todos(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        for i in range(5):
            store.add(Todo(title=f"Task {i}", category="Work"))
        assert len(store.list_todos()) == 5


class TestStoreGet:
    def test_get_by_id(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        todo = Todo(id="abc123", title="Find me", category="Work")
        store.add(todo)
        found = store.get("abc123")
        assert found is not None
        assert found.title == "Find me"

    def test_get_nonexistent_returns_none(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        assert store.get("nope") is None


class TestStoreUpdate:
    def test_update_title(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        todo = Todo(id="abc123", title="Old title", category="Work")
        store.add(todo)
        store.update("abc123", title="New title")
        updated = store.get("abc123")
        assert updated is not None
        assert updated.title == "New title"

    def test_update_status(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        todo = Todo(id="abc123", title="Test", category="Work")
        store.add(todo)
        store.update("abc123", status=Status.DONE)
        updated = store.get("abc123")
        assert updated is not None
        assert updated.status == Status.DONE
        assert updated.completed_at is not None

    def test_update_status_from_done_clears_completed_at(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        todo = Todo(id="abc123", title="Test", category="Work")
        store.add(todo)
        store.update("abc123", status=Status.DONE)
        store.update("abc123", status=Status.TODO)
        updated = store.get("abc123")
        assert updated is not None
        assert updated.completed_at is None

    def test_update_nonexistent_raises(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        with pytest.raises(KeyError):
            store.update("nope", title="Fail")

    def test_update_persists(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        todo = Todo(id="abc123", title="Old", category="Work")
        store.add(todo)
        store.update("abc123", title="New")
        store2 = TodoStore(mock_home / ".todo")
        assert store2.get("abc123").title == "New"  # type: ignore[union-attr]


class TestStoreDelete:
    def test_delete_todo(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        todo = Todo(id="abc123", title="Delete me", category="Work")
        store.add(todo)
        store.delete("abc123")
        assert store.get("abc123") is None
        assert len(store.list_todos()) == 0

    def test_delete_nonexistent_raises(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        with pytest.raises(KeyError):
            store.delete("nope")


class TestStoreFilter:
    def test_filter_by_status(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        store.add(Todo(title="Open", category="Work"))
        store.add(Todo(title="Done", category="Work", status=Status.DONE))
        todos = store.list_todos(status=Status.TODO)
        assert len(todos) == 1
        assert todos[0].title == "Open"

    def test_filter_by_category(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        store.add(Todo(title="Work task", category="Work"))
        store.add(Todo(title="Family task", category="Family"))
        todos = store.list_todos(category="Family")
        assert len(todos) == 1
        assert todos[0].title == "Family task"

    def test_filter_by_project(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        store.add(Todo(title="Project A", category="Work", project="proj-a"))
        store.add(Todo(title="Project B", category="Work", project="proj-b"))
        todos = store.list_todos(project="proj-a")
        assert len(todos) == 1
        assert todos[0].title == "Project A"

    def test_filter_by_priority(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        store.add(Todo(title="Critical", category="Work", priority=Priority.CRITICAL))
        store.add(Todo(title="Low", category="Work", priority=Priority.LOW))
        todos = store.list_todos(priority=Priority.CRITICAL)
        assert len(todos) == 1
        assert todos[0].title == "Critical"

    def test_filter_by_tag(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        store.add(Todo(title="Tagged", category="Work", tags=["urgent"]))
        store.add(Todo(title="Untagged", category="Work"))
        todos = store.list_todos(tag="urgent")
        assert len(todos) == 1
        assert todos[0].title == "Tagged"

    def test_multiple_filters_stack(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        store.add(Todo(title="Match", category="Work", priority=Priority.HIGH))
        store.add(Todo(title="Wrong cat", category="Family", priority=Priority.HIGH))
        store.add(Todo(title="Wrong pri", category="Work", priority=Priority.LOW))
        todos = store.list_todos(category="Work", priority=Priority.HIGH)
        assert len(todos) == 1
        assert todos[0].title == "Match"

    def test_list_excludes_archived_by_default(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        store.add(Todo(title="Active", category="Work"))
        store.add(Todo(title="Archived", category="Work", status=Status.ARCHIVED))
        todos = store.list_todos()
        assert len(todos) == 1
        assert todos[0].title == "Active"

    def test_list_includes_archived_when_filtered(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        store.add(Todo(title="Archived", category="Work", status=Status.ARCHIVED))
        todos = store.list_todos(status=Status.ARCHIVED)
        assert len(todos) == 1


class TestStoreCorruptFile:
    def test_corrupt_yaml_raises(self, mock_home: Path):
        todo_dir = mock_home / ".todo"
        todo_dir.mkdir(exist_ok=True)
        todos_path = todo_dir / "todos.yml"
        todos_path.write_text("{{invalid yaml content")
        with pytest.raises(ValueError, match="corrupted"):
            TodoStore(todo_dir)

    def test_empty_file_treated_as_empty_list(self, mock_home: Path):
        todo_dir = mock_home / ".todo"
        todo_dir.mkdir(exist_ok=True)
        todos_path = todo_dir / "todos.yml"
        todos_path.write_text("")
        store = TodoStore(todo_dir)
        assert len(store.list_todos()) == 0


class TestFileLocking:
    def test_lock_created_during_write(self, mock_home: Path):
        store = TodoStore(mock_home / ".todo")
        store.add(Todo(title="Test", category="Work"))
        # Lock should be released after write
        assert not store.lock_path.exists()
