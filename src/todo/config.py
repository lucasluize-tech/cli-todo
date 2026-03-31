"""User config management for categories and defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from todo.models import Priority, TodoConfig

SUPPORTED_LLMS = frozenset({"claude", "codex", "gemini", "opencode"})
SUPPORTED_LLM_FILES = frozenset({"claude", "agents"})


class ConfigManager:
    """Manages user configuration (categories, defaults)."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.home() / ".todo"
        self.base_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.config_path = self.base_dir / "config.yml"

        if not self.config_path.exists():
            self._save(TodoConfig())

    def load(self) -> TodoConfig:
        text = self.config_path.read_text()
        if not text.strip():
            return TodoConfig()
        data = yaml.safe_load(text)
        return TodoConfig(**data) if data else TodoConfig()

    def _save(self, config: TodoConfig) -> None:
        data = config.model_dump(mode="json")
        self.config_path.write_text(yaml.dump(data, default_flow_style=False))

    def add_category(self, name: str) -> None:
        config = self.load()
        if name in config.categories:
            raise ValueError(f"Category '{name}' already exists")
        config.categories.append(name)
        self._save(config)

    def remove_category(self, name: str) -> None:
        config = self.load()
        if name not in config.categories:
            raise ValueError(f"Category '{name}' not found")
        config.categories.remove(name)
        self._save(config)

    def list_categories(self) -> list[str]:
        return self.load().categories

    def set_default(self, key: str, value: Any) -> None:
        config = self.load()
        if key == "category":
            config.defaults.category = str(value)
        elif key == "priority":
            config.defaults.priority = Priority(int(value))
        elif key == "llm":
            val = str(value)
            if val not in SUPPORTED_LLMS:
                raise ValueError(
                    f"Unsupported LLM: '{val}'. Choose from: {', '.join(sorted(SUPPORTED_LLMS))}"
                )
            config.defaults.llm = val
        elif key == "llm_files":
            entries = [e.strip() for e in str(value).split(",")]
            invalid = [e for e in entries if e not in SUPPORTED_LLM_FILES]
            if invalid:
                raise ValueError(
                    f"Unsupported llm_files: {', '.join(invalid)}. "
                    f"Choose from: {', '.join(sorted(SUPPORTED_LLM_FILES))}"
                )
            config.defaults.llm_files = entries
        elif key == "llm_files_local":
            val = str(value).lower()
            if val not in ("true", "false"):
                raise ValueError("llm_files_local must be 'true' or 'false'")
            config.defaults.llm_files_local = val == "true"
        else:
            raise ValueError(
                f"Invalid default key: '{key}'. "
                "Use 'category', 'priority', 'llm', 'llm_files', or 'llm_files_local'"
            )
        self._save(config)

    def list_projects_roots(self) -> list[str]:
        return self.load().defaults.projects_roots

    def add_projects_root(self, path: str) -> None:
        config = self.load()
        resolved = str(Path(path).expanduser().resolve())
        for existing in config.defaults.projects_roots:
            if str(Path(existing).expanduser().resolve()) == resolved:
                raise ValueError(f"Root '{path}' already configured")
        config.defaults.projects_roots.append(path)
        self._save(config)

    def remove_projects_root(self, path: str) -> None:
        config = self.load()
        resolved = str(Path(path).expanduser().resolve())
        for existing in config.defaults.projects_roots:
            if str(Path(existing).expanduser().resolve()) == resolved:
                config.defaults.projects_roots.remove(existing)
                self._save(config)
                return
        raise ValueError(f"Root '{path}' not found in config")
