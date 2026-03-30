"""YAML store for TODO persistence."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from todo.models import Priority, Status, Todo, TodoConfig


class TodoStore:
    """Manages TODO persistence in YAML files with file locking."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.home() / ".todo"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.todos_path = self.base_dir / "todos.yml"
        self.config_path = self.base_dir / "config.yml"
        self.lock_path = self.base_dir / ".lock"

        self._todos: list[Todo] = []
        self._load()

        if not self.config_path.exists():
            self._write_config(TodoConfig())

    def _load(self) -> None:
        if not self.todos_path.exists():
            self._todos = []
            self._save()
            return

        text = self.todos_path.read_text()
        if not text.strip():
            self._todos = []
            return

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise ValueError(f"Could not parse {self.todos_path}. File may be corrupted") from e

        if data is None:
            self._todos = []
            return

        raw_todos = data.get("todos", [])
        self._todos = [Todo(**t) for t in raw_todos]

    def _save(self) -> None:
        self._acquire_lock()
        try:
            data = {"todos": [t.model_dump(mode="json") for t in self._todos]}
            self.todos_path.write_text(yaml.dump(data, default_flow_style=False))
        finally:
            self._release_lock()

    def _acquire_lock(self) -> None:
        if self.lock_path.exists():
            lock_age = time.time() - self.lock_path.stat().st_mtime
            try:
                pid = int(self.lock_path.read_text().strip())
                pid_alive = _pid_exists(pid)
            except (ValueError, OSError):
                pid_alive = False

            if lock_age > 60 or not pid_alive:
                self.lock_path.unlink(missing_ok=True)
            else:
                raise OSError(
                    f"Could not acquire lock. Another todo process may be running (PID: {pid})"
                )

        self.lock_path.write_text(str(os.getpid()))

    def _release_lock(self) -> None:
        self.lock_path.unlink(missing_ok=True)

    def _write_config(self, config: TodoConfig) -> None:
        data = config.model_dump(mode="json")
        self.config_path.write_text(yaml.dump(data, default_flow_style=False))

    def load_config(self) -> TodoConfig:
        if not self.config_path.exists():
            return TodoConfig()
        text = self.config_path.read_text()
        if not text.strip():
            return TodoConfig()
        data = yaml.safe_load(text)
        return TodoConfig(**data) if data else TodoConfig()

    def save_config(self, config: TodoConfig) -> None:
        self._write_config(config)

    def add(self, todo: Todo) -> None:
        self._todos.append(todo)
        self._save()

    def get(self, todo_id: str) -> Todo | None:
        for t in self._todos:
            if t.id == todo_id:
                return t
        return None

    def update(self, todo_id: str, **kwargs: Any) -> Todo:
        todo = self.get(todo_id)
        if todo is None:
            raise KeyError(f"No TODO found with ID '{todo_id}'")

        new_status = kwargs.get("status")
        if new_status == Status.DONE and todo.status != Status.DONE:
            kwargs["completed_at"] = datetime.now(UTC)
        elif new_status is not None and new_status != Status.DONE and todo.status == Status.DONE:
            kwargs["completed_at"] = None

        kwargs["updated_at"] = datetime.now(UTC)

        for key, value in kwargs.items():
            setattr(todo, key, value)

        self._save()
        return todo

    def delete(self, todo_id: str) -> None:
        todo = self.get(todo_id)
        if todo is None:
            raise KeyError(f"No TODO found with ID '{todo_id}'")
        self._todos = [t for t in self._todos if t.id != todo_id]
        self._save()

    def list_todos(
        self,
        *,
        status: Status | None = None,
        category: str | None = None,
        project: str | None = None,
        priority: Priority | None = None,
        tag: str | None = None,
    ) -> list[Todo]:
        results = self._todos

        # Exclude archived by default unless explicitly filtering for archived
        if status is None:
            results = [t for t in results if t.status != Status.ARCHIVED]
        else:
            results = [t for t in results if t.status == status]

        if category is not None:
            results = [t for t in results if t.category == category]
        if project is not None:
            results = [t for t in results if t.project == project]
        if priority is not None:
            results = [t for t in results if t.priority == priority]
        if tag is not None:
            results = [t for t in results if tag in t.tags]

        return results


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
