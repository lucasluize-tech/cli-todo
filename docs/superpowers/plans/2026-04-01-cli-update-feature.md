# CLI Update Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `todo --version` flag and `todo update` command that checks PyPI and upgrades via pipx.

**Architecture:** New `updater.py` module handles PyPI version checking and pipx upgrade subprocess calls. The `cli.py` module gets a version callback and a new `update` command that delegates to `updater.py`.

**Tech Stack:** Python stdlib (`urllib.request`, `json`, `subprocess`), Typer, Rich

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/todo/__init__.py` | Bump `__version__` to `"0.3.0"` |
| Modify | `pyproject.toml` | Switch to dynamic versioning from `__init__.py` |
| Create | `src/todo/updater.py` | PyPI version fetch, version comparison, pipx upgrade |
| Modify | `src/todo/cli.py` | `--version` callback, `update` command |
| Create | `tests/test_updater.py` | Unit tests for updater module |
| Modify | `tests/test_cli.py` | Integration tests for `--version` and `update` command |
| Modify | `README.md` | Document new features |

---

### Task 1: Version Infrastructure — Dynamic Versioning

**Files:**
- Modify: `src/todo/__init__.py:3`
- Modify: `pyproject.toml:6-7`

- [ ] **Step 1: Update `__init__.py` version to 0.3.0**

```python
__version__ = "0.3.0"
```

- [ ] **Step 2: Switch pyproject.toml to dynamic versioning**

In `pyproject.toml`, remove the hardcoded `version = "0.2.0"` line and add dynamic versioning:

```toml
[project]
name = "todo-cli-tool"
dynamic = ["version"]
```

Add the hatch version source config:

```toml
[tool.hatch.version]
path = "src/todo/__init__.py"
```

- [ ] **Step 3: Verify the build still resolves the version**

Run: `cd /home/lucasluize/projects/cli-tools && uv run python -c "from todo import __version__; print(__version__)"`
Expected: `0.3.0`

- [ ] **Step 4: Commit**

```bash
git add src/todo/__init__.py pyproject.toml
git commit -m "Switch to dynamic versioning from __init__.py, bump to 0.3.0"
```

---

### Task 2: TDD — `updater.py` Unit Tests (Red Phase)

**Files:**
- Create: `tests/test_updater.py`

- [ ] **Step 1: Write failing tests for the updater module**

```python
"""Unit tests for the updater module."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from todo.updater import check_latest_version, parse_version, run_pipx_upgrade


class TestParseVersion:
    def test_simple_version(self):
        assert parse_version("0.2.0") == (0, 2, 0)

    def test_major_version(self):
        assert parse_version("1.0.0") == (1, 0, 0)

    def test_double_digits(self):
        assert parse_version("1.12.3") == (1, 12, 3)


class TestCheckLatestVersion:
    @patch("todo.updater.urlopen")
    def test_returns_latest_version(self, mock_urlopen: MagicMock):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"info": {"version": "0.4.0"}}
        ).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        assert check_latest_version() == "0.4.0"

    @patch("todo.updater.urlopen")
    def test_network_error_returns_none(self, mock_urlopen: MagicMock):
        mock_urlopen.side_effect = OSError("No internet")

        assert check_latest_version() is None

    @patch("todo.updater.urlopen")
    def test_invalid_json_returns_none(self, mock_urlopen: MagicMock):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        assert check_latest_version() is None


class TestRunPipxUpgrade:
    @patch("todo.updater.shutil.which", return_value="/usr/bin/pipx")
    @patch("todo.updater.subprocess.run")
    def test_upgrade_success(self, mock_run: MagicMock, mock_which: MagicMock):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        success, msg = run_pipx_upgrade(force=False)
        assert success is True
        mock_run.assert_called_once_with(
            ["pipx", "upgrade", "todo-cli-tool"], check=False
        )

    @patch("todo.updater.shutil.which", return_value="/usr/bin/pipx")
    @patch("todo.updater.subprocess.run")
    def test_upgrade_force(self, mock_run: MagicMock, mock_which: MagicMock):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        success, msg = run_pipx_upgrade(force=True)
        assert success is True
        mock_run.assert_called_once_with(
            ["pipx", "upgrade", "--force", "todo-cli-tool"], check=False
        )

    @patch("todo.updater.shutil.which", return_value=None)
    def test_pipx_not_found(self, mock_which: MagicMock):
        success, msg = run_pipx_upgrade(force=False)
        assert success is False
        assert "pipx not found" in msg

    @patch("todo.updater.shutil.which", return_value="/usr/bin/pipx")
    @patch("todo.updater.subprocess.run")
    def test_upgrade_failure(self, mock_run: MagicMock, mock_which: MagicMock):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stderr="error"
        )

        success, msg = run_pipx_upgrade(force=False)
        assert success is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/lucasluize/projects/cli-tools && uv run pytest tests/test_updater.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'todo.updater'`

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_updater.py
git commit -m "Add failing tests for updater module (red phase)"
```

---

### Task 3: Implement `updater.py` (Green Phase)

**Files:**
- Create: `src/todo/updater.py`

- [ ] **Step 1: Implement the updater module**

```python
"""Check PyPI for updates and upgrade via pipx."""

from __future__ import annotations

import json
import shutil
import subprocess
from urllib.request import urlopen

PYPI_URL = "https://pypi.org/pypi/todo-cli-tool/json"


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a version string into a comparable tuple of ints."""
    return tuple(int(part) for part in version.split("."))


def check_latest_version() -> str | None:
    """Fetch the latest version from PyPI. Returns None on failure."""
    try:
        with urlopen(PYPI_URL, timeout=5) as response:  # noqa: S310
            data = json.loads(response.read())
            return str(data["info"]["version"])
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def run_pipx_upgrade(*, force: bool) -> tuple[bool, str]:
    """Run pipx upgrade. Returns (success, message)."""
    if shutil.which("pipx") is None:
        return False, "pipx not found -- install manually with: pipx install todo-cli-tool"

    cmd = ["pipx", "upgrade"]
    if force:
        cmd.append("--force")
    cmd.append("todo-cli-tool")

    result = subprocess.run(cmd, check=False)  # noqa: S603
    if result.returncode != 0:
        return False, "Upgrade failed. Run 'pipx upgrade todo-cli-tool' manually."
    return True, "Upgrade complete!"
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/lucasluize/projects/cli-tools && uv run pytest tests/test_updater.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add src/todo/updater.py
git commit -m "Implement updater module: PyPI check + pipx upgrade"
```

---

### Task 4: TDD — `--version` Flag Tests (Red Phase)

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add failing tests for `--version` at the end of `tests/test_cli.py`**

```python
class TestVersion:
    def test_version_long_flag(self, mock_home: Path):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "todo-cli-tool v" in result.output

    def test_version_short_flag(self, mock_home: Path):
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "todo-cli-tool v" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/lucasluize/projects/cli-tools && uv run pytest tests/test_cli.py::TestVersion -v`
Expected: FAIL — no such option `--version`

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_cli.py
git commit -m "Add failing tests for --version flag (red phase)"
```

---

### Task 5: Implement `--version` Flag (Green Phase)

**Files:**
- Modify: `src/todo/cli.py:1-20`

- [ ] **Step 1: Add version callback to cli.py**

Add the import at the top of `cli.py` (after the existing imports from `todo`):

```python
from todo import __version__
```

Add the version callback function before the `app` definition (before line 20):

```python
def _version_callback(value: bool) -> None:
    if value:
        console = Console()
        console.print(f"todo-cli-tool v{__version__}")
        raise typer.Exit()
```

Update the `app` definition to include the version callback:

```python
@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", help="Show version and exit.", callback=_version_callback, is_eager=True),
    ] = False,
) -> None:
    """CLI TODO tool for managing personal TODOs."""
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/lucasluize/projects/cli-tools && uv run pytest tests/test_cli.py::TestVersion -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add src/todo/cli.py
git commit -m "Add --version / -v flag to CLI"
```

---

### Task 6: TDD — `todo update` Command Tests (Red Phase)

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add failing tests for the update command at the end of `tests/test_cli.py`**

```python
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

    @patch("todo.cli.run_pipx_upgrade", return_value=(False, "pipx not found -- install manually with: pipx install todo-cli-tool"))
    def test_update_force_pipx_missing(self, mock_upgrade: MagicMock, mock_home: Path):
        result = runner.invoke(app, ["update", "--force"])
        assert result.exit_code == 1
        assert "pipx not found" in result.output
```

Add `MagicMock` to the existing `unittest.mock` import at the top of `tests/test_cli.py`:

```python
from unittest.mock import MagicMock, patch
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/lucasluize/projects/cli-tools && uv run pytest tests/test_cli.py::TestUpdate -v`
Expected: FAIL — `No such command 'update'`

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_cli.py
git commit -m "Add failing tests for update command (red phase)"
```

---

### Task 7: Implement `todo update` Command (Green Phase)

**Files:**
- Modify: `src/todo/cli.py`

- [ ] **Step 1: Add the update command to cli.py**

Add import at top of `cli.py` (with other `todo` imports):

```python
from todo.updater import check_latest_version, run_pipx_upgrade
```

Add the `update` command (after the `sync_cmd` function, before the `generate` function):

```python
@app.command()
def update(
    force: bool = typer.Option(False, "--force", help="Force reinstall even if up to date."),
) -> None:
    """Check for updates and upgrade via pipx."""
    console = Console()

    if force:
        console.print("[yellow]Forcing reinstall...[/yellow]")
        success, msg = run_pipx_upgrade(force=True)
        if not success:
            err_console.print(f"Error: {msg}")
            raise typer.Exit(1)
        console.print(f"[green]{msg}[/green]")
        return

    latest = check_latest_version()
    if latest is None:
        err_console.print("Error: Could not check for updates. Check your internet connection.")
        raise typer.Exit(1)

    current = __version__
    if parse_version(latest) <= parse_version(current):
        console.print(f"[green]Already up to date (v{current})[/green]")
        return

    console.print(f"[yellow]Update available: v{current} → v{latest}[/yellow]")
    if not typer.confirm("Upgrade?"):
        return

    success, msg = run_pipx_upgrade(force=False)
    if not success:
        err_console.print(f"Error: {msg}")
        raise typer.Exit(1)
    console.print(f"[green]{msg}[/green]")
```

Also add `parse_version` to the import from `todo.updater`:

```python
from todo.updater import check_latest_version, parse_version, run_pipx_upgrade
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/lucasluize/projects/cli-tools && uv run pytest tests/test_cli.py::TestUpdate -v`
Expected: All PASS

- [ ] **Step 3: Run full test suite**

Run: `cd /home/lucasluize/projects/cli-tools && uv run pytest -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add src/todo/cli.py
git commit -m "Add todo update command: PyPI check + pipx upgrade"
```

---

### Task 8: README Updates

**Files:**
- Modify: `README.md:19-27` (Features list)
- Modify: `README.md:105-136` (Managing TODOs code block)

- [ ] **Step 1: Add Self-Update to Features list**

Add after the "Beautiful Output" bullet (line 27):

```markdown
- **Self-Update:** Check for new versions and upgrade in-place with `todo update`.
```

- [ ] **Step 2: Add examples to Managing TODOs code block**

Add at the end of the existing code block (before the closing ````):

```shell
# Check version
todo --version

# Check for updates and upgrade
todo update

# Force reinstall
todo update --force
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Document --version and update command in README"
```

---

### Task 9: Hardening

**Files:**
- All modified files

- [ ] **Step 1: Run ruff check and format**

Run: `cd /home/lucasluize/projects/cli-tools && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/`

Fix any issues found.

- [ ] **Step 2: Run mypy**

Run: `cd /home/lucasluize/projects/cli-tools && uv run mypy src/`

Fix any type errors. Ensure no `Any` types are used.

- [ ] **Step 3: Security audit**

Review `updater.py` for:
- `subprocess.run` uses list args (no `shell=True`) — no command injection vector
- `urlopen` uses a hardcoded URL constant — no user-controlled input in the URL
- PyPI JSON response: only extract `data["info"]["version"]` as `str()` — no eval/exec on response data
- No user input is interpolated into subprocess commands

- [ ] **Step 4: Run full test suite with coverage**

Run: `cd /home/lucasluize/projects/cli-tools && uv run pytest --cov=todo --cov-report=term-missing -v`
Expected: All PASS, coverage >= 80%

- [ ] **Step 5: Commit any fixes**

```bash
git add -u
git commit -m "Hardening: lint, types, and security review"
```

---

### Task 10: Push to CI

- [ ] **Step 1: Push to remote**

```bash
git push origin main
```

- [ ] **Step 2: Monitor CI results**

Check GitHub Actions for the CI workflow. All checks (lint, format, type check, tests on 3.11/3.12/3.13) should pass.
