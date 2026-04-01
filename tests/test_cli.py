"""CLI integration tests via CliRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from todo.cli import app
from todo.store import TodoStore

runner = CliRunner()


@pytest.fixture
def cli_store(mock_home: Path) -> TodoStore:
    """Create a store and patch _get_store / _get_config_manager to use it."""
    store = TodoStore(mock_home / ".todo")
    return store


@pytest.fixture(autouse=True)
def _patch_store(mock_home: Path):
    """Patch store and config manager to use mock home for all CLI tests."""
    todo_dir = mock_home / ".todo"

    with (
        patch("todo.cli._get_store", return_value=TodoStore(todo_dir)),
        patch("todo.cli._get_config_manager") as mock_cm,
        patch("todo.cli._auto_project", return_value=None),
    ):
        from todo.config import ConfigManager

        mock_cm.return_value = ConfigManager(todo_dir)
        yield


class TestAdd:
    def test_add_basic(self, mock_home: Path):
        result = runner.invoke(app, ["add", "Buy groceries"])
        assert result.exit_code == 0
        assert "Created TODO" in result.output
        assert "Buy groceries" in result.output

    def test_add_with_flags(self, mock_home: Path):
        result = runner.invoke(
            app,
            [
                "add",
                "Urgent task",
                "-p",
                "1",
                "-c",
                "Work",
                "-dd",
                "2026-04-01",
                "-t",
                "urgent,api",
            ],
        )
        assert result.exit_code == 0
        assert "Created TODO" in result.output

    def test_add_with_description(self, mock_home: Path):
        result = runner.invoke(app, ["add", "Task", "-d", "A long description"])
        assert result.exit_code == 0

    def test_add_invalid_priority(self, mock_home: Path):
        result = runner.invoke(app, ["add", "Bad", "-p", "0"])
        assert result.exit_code == 1

    def test_add_invalid_category(self, mock_home: Path):
        result = runner.invoke(app, ["add", "Bad", "-c", "NonexistentCategory"])
        assert result.exit_code == 1
        assert "not in config" in result.output


class TestList:
    def test_list_empty(self, mock_home: Path):
        result = runner.invoke(app, ["list", "-a"])
        assert result.exit_code == 0
        assert "No TODOs" in result.output

    def test_list_with_todos(self, mock_home: Path):
        runner.invoke(app, ["add", "Task one"])
        runner.invoke(app, ["add", "Task two"])
        result = runner.invoke(app, ["list", "-a"])
        assert result.exit_code == 0
        assert "Task one" in result.output
        assert "Task two" in result.output

    def test_list_filter_by_category(self, mock_home: Path):
        runner.invoke(app, ["add", "Work task", "-c", "Work"])
        runner.invoke(app, ["add", "Family task", "-c", "Family"])
        result = runner.invoke(app, ["list", "-a", "-c", "Family"])
        assert "Family task" in result.output
        assert "Work task" not in result.output

    def test_list_filter_by_priority(self, mock_home: Path):
        runner.invoke(app, ["add", "Critical", "-p", "1"])
        runner.invoke(app, ["add", "Low", "-p", "4"])
        result = runner.invoke(app, ["list", "-a", "-p", "1"])
        assert "Critical" in result.output
        assert "Low" not in result.output

    def test_list_filter_by_tag(self, mock_home: Path):
        runner.invoke(app, ["add", "Tagged", "-t", "urgent"])
        runner.invoke(app, ["add", "Untagged"])
        result = runner.invoke(app, ["list", "-a", "--tag", "urgent"])
        assert "Tagged" in result.output
        assert "Untagged" not in result.output


class TestShow:
    def test_show_existing(self, mock_home: Path):
        runner.invoke(app, ["add", "Show me"])
        # Get the ID from the add output
        list_result = runner.invoke(app, ["list", "-a"])
        # Extract ID from list output (it's the first column)
        lines = list_result.output.strip().split("\n")
        # Find a line with "Show me" and extract the ID
        todo_id = None
        for line in lines:
            if "Show me" in line:
                # ID is in the first column
                parts = line.split()
                for part in parts:
                    if len(part) == 6 and part.isalnum():
                        todo_id = part
                        break
        assert todo_id is not None
        result = runner.invoke(app, ["show", todo_id])
        assert result.exit_code == 0
        assert "Show me" in result.output

    def test_show_nonexistent(self, mock_home: Path):
        result = runner.invoke(app, ["show", "nope00"])
        assert result.exit_code == 1


class TestEdit:
    def test_edit_title(self, mock_home: Path):
        runner.invoke(app, ["add", "Old title"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Old title")
        assert todo_id is not None
        result = runner.invoke(app, ["edit", todo_id, "--title", "New title"])
        assert result.exit_code == 0
        assert "Updated" in result.output

    def test_edit_no_flags(self, mock_home: Path):
        runner.invoke(app, ["add", "Task"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Task")
        assert todo_id is not None
        result = runner.invoke(app, ["edit", todo_id])
        assert result.exit_code == 1

    def test_edit_nonexistent(self, mock_home: Path):
        result = runner.invoke(app, ["edit", "nope00", "--title", "Fail"])
        assert result.exit_code == 1


class TestDone:
    def test_done_marks_complete(self, mock_home: Path):
        runner.invoke(app, ["add", "Finish me"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Finish me")
        assert todo_id is not None
        result = runner.invoke(app, ["done", todo_id])
        assert result.exit_code == 0
        assert "done" in result.output

    def test_done_nonexistent(self, mock_home: Path):
        result = runner.invoke(app, ["done", "nope00"])
        assert result.exit_code == 1


class TestStart:
    def test_start_marks_in_progress(self, mock_home: Path):
        runner.invoke(app, ["add", "Begin me"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Begin me")
        assert todo_id is not None
        result = runner.invoke(app, ["start", todo_id])
        assert result.exit_code == 0
        assert "Started" in result.output

    def test_start_nonexistent(self, mock_home: Path):
        result = runner.invoke(app, ["start", "nope00"])
        assert result.exit_code == 1

    def test_start_with_llm_launches_process(self, mock_home: Path):
        proj = mock_home / "projects" / "my-project"
        proj.mkdir(parents=True)

        with patch("todo.cli._auto_project", return_value="my-project"):
            runner.invoke(app, ["add", "Build feature"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Build feature")
        assert todo_id is not None

        with (
            patch("todo.cli._auto_project", return_value="my-project"),
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("os.execvp") as mock_exec,
            patch("os.chdir"),
        ):
            result = runner.invoke(app, ["start", todo_id, "claude"])
            assert result.exit_code == 0
            assert "Started" in result.output
            mock_exec.assert_called_once()
            args = mock_exec.call_args
            assert args[0][0] == "claude"
            cmd_list = args[0][1]
            assert "claude" in cmd_list
            assert "Build feature" in cmd_list[1]
            assert "-n" in cmd_list
            assert f"todo:{todo_id}" in cmd_list[cmd_list.index("-n") + 1]

    def test_start_with_llm_uses_default(self, mock_home: Path):
        proj = mock_home / "projects" / "my-project"
        proj.mkdir(parents=True)

        with patch("todo.cli._auto_project", return_value="my-project"):
            runner.invoke(app, ["add", "Build feature"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Build feature")
        assert todo_id is not None

        with (
            patch("todo.cli._auto_project", return_value="my-project"),
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("os.execvp") as mock_exec,
            patch("os.chdir"),
        ):
            result = runner.invoke(app, ["start", todo_id])
            assert result.exit_code == 0
            mock_exec.assert_called_once()
            assert mock_exec.call_args[0][0] == "claude"

    def test_start_llm_not_installed(self, mock_home: Path):
        proj = mock_home / "projects" / "my-project"
        proj.mkdir(parents=True)

        with patch("todo.cli._auto_project", return_value="my-project"):
            runner.invoke(app, ["add", "Build feature"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Build feature")
        assert todo_id is not None

        with (
            patch("todo.cli._auto_project", return_value="my-project"),
            patch("shutil.which", return_value=None),
        ):
            result = runner.invoke(app, ["start", todo_id, "claude"])
            assert result.exit_code == 1
            assert "not installed" in result.output
            assert "https://" in result.output

    def test_start_unsupported_llm(self, mock_home: Path):
        proj = mock_home / "projects" / "my-project"
        proj.mkdir(parents=True)

        with patch("todo.cli._auto_project", return_value="my-project"):
            runner.invoke(app, ["add", "Build feature"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Build feature")
        assert todo_id is not None

        with patch("todo.cli._auto_project", return_value="my-project"):
            result = runner.invoke(app, ["start", todo_id, "unsupported"])
            assert result.exit_code == 1
            assert "Unsupported LLM" in result.output

    def test_start_no_project_no_llm(self, mock_home: Path):
        runner.invoke(app, ["add", "No project task"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "No project task")
        assert todo_id is not None

        result = runner.invoke(app, ["start", todo_id])
        assert result.exit_code == 0
        assert "Started" in result.output

    def test_start_no_project_with_llm_errors(self, mock_home: Path):
        runner.invoke(app, ["add", "No project task"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "No project task")
        assert todo_id is not None

        result = runner.invoke(app, ["start", todo_id, "claude"])
        assert result.exit_code == 1
        assert "Cannot start LLM session without a project" in result.output

    def test_start_codex_command(self, mock_home: Path):
        proj = mock_home / "projects" / "my-project"
        proj.mkdir(parents=True)

        with patch("todo.cli._auto_project", return_value="my-project"):
            runner.invoke(app, ["add", "Build feature"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Build feature")
        assert todo_id is not None

        with (
            patch("todo.cli._auto_project", return_value="my-project"),
            patch("shutil.which", return_value="/usr/bin/codex"),
            patch("os.execvp") as mock_exec,
            patch("os.chdir"),
        ):
            result = runner.invoke(app, ["start", todo_id, "codex"])
            assert result.exit_code == 0
            args = mock_exec.call_args
            assert args[0][0] == "codex"
            assert args[0][1] == ["codex", "Build feature"]

    def test_start_opencode_command(self, mock_home: Path):
        proj = mock_home / "projects" / "my-project"
        proj.mkdir(parents=True)

        with patch("todo.cli._auto_project", return_value="my-project"):
            runner.invoke(app, ["add", "Build feature"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Build feature")
        assert todo_id is not None

        with (
            patch("todo.cli._auto_project", return_value="my-project"),
            patch("shutil.which", return_value="/usr/bin/opencode"),
            patch("os.execvp") as mock_exec,
            patch("os.chdir"),
        ):
            result = runner.invoke(app, ["start", todo_id, "opencode"])
            assert result.exit_code == 0
            args = mock_exec.call_args
            assert args[0][0] == "opencode"
            cmd = args[0][1]
            assert cmd[0] == "opencode"
            assert str(proj) in cmd[1]
            assert "--prompt" in cmd

    def test_start_with_description_in_prompt(self, mock_home: Path):
        proj = mock_home / "projects" / "my-project"
        proj.mkdir(parents=True)

        with patch("todo.cli._auto_project", return_value="my-project"):
            runner.invoke(app, ["add", "Build feature", "-d", "Some details here"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Build feature")
        assert todo_id is not None

        with (
            patch("todo.cli._auto_project", return_value="my-project"),
            patch("shutil.which", return_value="/usr/bin/claude"),
            patch("os.execvp") as mock_exec,
            patch("os.chdir"),
        ):
            result = runner.invoke(app, ["start", todo_id, "claude"])
            assert result.exit_code == 0
            prompt = mock_exec.call_args[0][1][1]
            assert "Build feature" in prompt
            assert "Some details here" in prompt

    def test_start_rejects_symlinked_project_root(self, mock_home: Path):
        real_proj = mock_home / "projects" / "real-project"
        real_proj.mkdir(parents=True)

        symlink_proj = mock_home / "projects" / "my-project"
        symlink_proj.symlink_to(real_proj)

        with patch("todo.cli._auto_project", return_value="my-project"):
            runner.invoke(app, ["add", "Test task"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Test task")
        assert todo_id is not None

        with (
            patch("todo.cli._auto_project", return_value="my-project"),
            patch("shutil.which", return_value="/usr/bin/claude"),
        ):
            result = runner.invoke(app, ["start", todo_id, "claude"])
            assert result.exit_code == 1
            assert "symlink" in result.output.lower()


class TestArchive:
    def test_archive_done_item(self, mock_home: Path):
        runner.invoke(app, ["add", "Archive me"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Archive me")
        assert todo_id is not None
        runner.invoke(app, ["done", todo_id])
        result = runner.invoke(app, ["archive", todo_id])
        assert result.exit_code == 0
        assert "Archived" in result.output

    def test_archive_non_done_rejected(self, mock_home: Path):
        runner.invoke(app, ["add", "Not done"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Not done")
        assert todo_id is not None
        result = runner.invoke(app, ["archive", todo_id])
        assert result.exit_code == 1
        assert "Only done items" in result.output

    def test_archive_no_args(self, mock_home: Path):
        result = runner.invoke(app, ["archive"])
        assert result.exit_code == 1

    def test_archive_all_done(self, mock_home: Path):
        runner.invoke(app, ["add", "Task 1"])
        runner.invoke(app, ["add", "Task 2"])
        list_result = runner.invoke(app, ["list", "-a"])
        id1 = _extract_id(list_result.output, "Task 1")
        id2 = _extract_id(list_result.output, "Task 2")
        runner.invoke(app, ["done", id1])
        runner.invoke(app, ["done", id2])
        result = runner.invoke(app, ["archive", "--all-done"])
        assert result.exit_code == 0
        assert "Archived 2" in result.output


class TestDelete:
    def test_delete_with_confirm(self, mock_home: Path):
        runner.invoke(app, ["add", "Delete me"])
        list_result = runner.invoke(app, ["list", "-a"])
        todo_id = _extract_id(list_result.output, "Delete me")
        assert todo_id is not None
        result = runner.invoke(app, ["delete", todo_id, "-y"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_nonexistent(self, mock_home: Path):
        result = runner.invoke(app, ["delete", "nope00", "-y"])
        assert result.exit_code == 1


class TestSync:
    def test_sync_stub(self, mock_home: Path):
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0
        assert "Coming soon" in result.output


class TestConfigCommands:
    def test_categories_list(self, mock_home: Path):
        result = runner.invoke(app, ["config", "categories", "list"])
        assert result.exit_code == 0
        assert "Work" in result.output

    def test_categories_add(self, mock_home: Path):
        result = runner.invoke(app, ["config", "categories", "add", "Pets"])
        assert result.exit_code == 0
        assert "Added" in result.output

    def test_categories_remove(self, mock_home: Path):
        result = runner.invoke(app, ["config", "categories", "remove", "Social"])
        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_categories_remove_with_todos(self, mock_home: Path):
        runner.invoke(app, ["add", "Work task", "-c", "Work"])
        result = runner.invoke(app, ["config", "categories", "remove", "Work"])
        assert result.exit_code == 1
        assert "TODOs use category" in result.output

    def test_categories_remove_force(self, mock_home: Path):
        runner.invoke(app, ["add", "Work task", "-c", "Work"])
        result = runner.invoke(app, ["config", "categories", "remove", "Work", "--force"])
        assert result.exit_code == 0

    def test_defaults_set_priority(self, mock_home: Path):
        result = runner.invoke(app, ["config", "defaults", "set", "priority", "2"])
        assert result.exit_code == 0
        assert "Set default" in result.output

    def test_defaults_set_category(self, mock_home: Path):
        result = runner.invoke(app, ["config", "defaults", "set", "category", "Family"])
        assert result.exit_code == 0

    def test_defaults_set_invalid(self, mock_home: Path):
        result = runner.invoke(app, ["config", "defaults", "set", "invalid", "value"])
        assert result.exit_code == 1

    def test_roots_list(self, mock_home: Path):
        result = runner.invoke(app, ["config", "roots", "list"])
        assert result.exit_code == 0
        assert "~/projects" in result.output

    def test_roots_add(self, mock_home: Path):
        result = runner.invoke(app, ["config", "roots", "add", "~/code"])
        assert result.exit_code == 0
        assert "Added project root" in result.output

    def test_roots_add_duplicate(self, mock_home: Path):
        result = runner.invoke(app, ["config", "roots", "add", "~/projects"])
        assert result.exit_code == 1

    def test_roots_remove(self, mock_home: Path):
        result = runner.invoke(app, ["config", "roots", "remove", "~/work"])
        assert result.exit_code == 0
        assert "Removed project root" in result.output

    def test_roots_remove_nonexistent(self, mock_home: Path):
        result = runner.invoke(app, ["config", "roots", "remove", "~/nonexistent"])
        assert result.exit_code == 1

    def test_defaults_set_llm(self, mock_home: Path):
        result = runner.invoke(app, ["config", "defaults", "set", "llm", "codex"])
        assert result.exit_code == 0
        assert "Set default" in result.output

    def test_defaults_set_llm_invalid(self, mock_home: Path):
        result = runner.invoke(app, ["config", "defaults", "set", "llm", "bad"])
        assert result.exit_code == 1
        assert "Unsupported LLM" in result.output

    def test_defaults_set_llm_files(self, mock_home: Path):
        result = runner.invoke(app, ["config", "defaults", "set", "llm_files", "claude,agents"])
        assert result.exit_code == 0

    def test_defaults_set_llm_files_local(self, mock_home: Path):
        result = runner.invoke(app, ["config", "defaults", "set", "llm_files_local", "false"])
        assert result.exit_code == 0


class TestGenerate:
    def test_generate_writes_local_files(self, mock_home: Path):
        # Create project structure
        proj = mock_home / "projects" / "my-project"
        proj.mkdir(parents=True)

        # Patch _auto_project to return the project
        with patch("todo.cli._auto_project", return_value="my-project"):
            runner.invoke(app, ["add", "Test task"])
            result = runner.invoke(app, ["generate"])
            assert result.exit_code == 0

        assert (proj / "claude.local.md").exists()
        assert (proj / "AGENTS.local.md").exists()
        content = (proj / "claude.local.md").read_text()
        assert "1 open" in content


class TestVersion:
    def test_version_long_flag(self, mock_home: Path):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "todo-cli-tool v" in result.output

    def test_version_short_flag(self, mock_home: Path):
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "todo-cli-tool v" in result.output


class TestUpdate:
    @patch("todo.cli.check_latest_version", return_value="0.4.0")
    @patch("todo.cli.run_pipx_upgrade", return_value=(True, "Upgrade complete!"))
    def test_update_available_confirm(
        self, mock_upgrade: MagicMock, mock_check: MagicMock, mock_home: Path
    ):
        result = runner.invoke(app, ["update"], input="y\n")
        assert result.exit_code == 0
        assert "Update available" in result.output
        mock_upgrade.assert_called_once_with(force=False)

    @patch("todo.cli.check_latest_version", return_value="0.4.0")
    def test_update_available_decline(self, mock_check: MagicMock, mock_home: Path):
        result = runner.invoke(app, ["update"], input="n\n")
        assert result.exit_code == 0
        assert "Update available" in result.output

    @patch("todo.cli.check_latest_version")
    def test_update_already_latest(self, mock_check: MagicMock, mock_home: Path):
        from todo import __version__

        mock_check.return_value = __version__
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0
        assert "Already up to date" in result.output

    @patch("todo.cli.check_latest_version", return_value=None)
    def test_update_network_error(self, mock_check: MagicMock, mock_home: Path):
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 1
        assert "Could not check" in result.output

    @patch("todo.cli.run_pipx_upgrade", return_value=(True, "Upgrade complete!"))
    def test_update_force(self, mock_upgrade: MagicMock, mock_home: Path):
        result = runner.invoke(app, ["update", "--force"])
        assert result.exit_code == 0
        mock_upgrade.assert_called_once_with(force=True)

    @patch(
        "todo.cli.run_pipx_upgrade",
        return_value=(False, "pipx not found -- install manually with: pipx install todo-cli-tool"),
    )
    def test_update_force_pipx_missing(self, mock_upgrade: MagicMock, mock_home: Path):
        result = runner.invoke(app, ["update", "--force"])
        assert result.exit_code == 1
        assert "pipx not found" in result.output


def _extract_id(output: str, title: str) -> str | None:
    """Extract TODO ID from list output by finding the line with the title."""
    for line in output.split("\n"):
        if title in line:
            for word in line.split():
                cleaned = word.strip("│ ")
                if len(cleaned) == 6 and cleaned.isalnum():
                    return cleaned
    return None
