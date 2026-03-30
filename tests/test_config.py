"""Tests for config management."""

from __future__ import annotations

from pathlib import Path

import pytest

from todo.config import ConfigManager
from todo.models import Priority


class TestConfigManager:
    def test_load_default_config(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        config = mgr.load()
        assert "Work" in config.categories
        assert config.defaults.priority == Priority.MEDIUM

    def test_load_existing_config(self, mock_home: Path, sample_config_file: Path):
        mgr = ConfigManager(mock_home / ".todo")
        config = mgr.load()
        assert "Work" in config.categories

    def test_add_category(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        mgr.add_category("Pets")
        config = mgr.load()
        assert "Pets" in config.categories

    def test_add_duplicate_category_raises(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        with pytest.raises(ValueError, match="already exists"):
            mgr.add_category("Work")

    def test_remove_category(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        mgr.remove_category("Social")
        config = mgr.load()
        assert "Social" not in config.categories

    def test_remove_nonexistent_category_raises(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        with pytest.raises(ValueError, match="not found"):
            mgr.remove_category("Nonexistent")

    def test_set_default_category(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        mgr.set_default("category", "Family")
        config = mgr.load()
        assert config.defaults.category == "Family"

    def test_set_default_priority(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        mgr.set_default("priority", 2)
        config = mgr.load()
        assert config.defaults.priority == Priority.HIGH

    def test_set_invalid_default_key_raises(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        with pytest.raises(ValueError, match="Invalid default key"):
            mgr.set_default("invalid_key", "value")

    def test_list_categories(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        cats = mgr.list_categories()
        assert isinstance(cats, list)
        assert "Work" in cats

    def test_list_projects_roots(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        roots = mgr.list_projects_roots()
        assert isinstance(roots, list)
        assert "~/projects" in roots

    def test_add_projects_root(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        mgr.add_projects_root("~/code")
        roots = mgr.list_projects_roots()
        assert "~/code" in roots

    def test_add_duplicate_projects_root_raises(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        with pytest.raises(ValueError, match="already configured"):
            mgr.add_projects_root("~/projects")

    def test_remove_projects_root(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        mgr.remove_projects_root("~/work")
        roots = mgr.list_projects_roots()
        assert "~/work" not in roots

    def test_remove_nonexistent_projects_root_raises(self, mock_home: Path):
        mgr = ConfigManager(mock_home / ".todo")
        with pytest.raises(ValueError, match="not found"):
            mgr.remove_projects_root("~/nonexistent")
