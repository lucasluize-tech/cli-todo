# CLI Update Feature Design

## Overview

Add a `todo update` command that checks PyPI for newer versions and upgrades via `pipx`, plus `--version` / `-v` flags on the main app.

## Version Infrastructure

- **Single source of truth:** `src/todo/__init__.py` holds `__version__`
- **Dynamic versioning:** Configure `hatchling` in `pyproject.toml` to read version from `__init__.py` (remove hardcoded version)
- **Version bump:** Set `__version__ = "0.3.0"` as part of this feature branch, before pushing

## `--version` / `-v` Flag

Typer version callback on the main app. Output format:

```
todo-cli-tool v0.3.0
```

## `todo update` Command

### Flow

1. Fetch `https://pypi.org/pypi/todo-cli-tool/json` via `urllib.request`
2. Parse JSON, extract `info.version` as latest
3. Compare against local `__version__` using tuple comparison (`"0.2.0"` -> `(0, 2, 0)`)
4. **If newer:** Print `"Update available: v0.2.0 -> v0.3.0. Upgrade? [y/N]"` — on confirm, run `pipx upgrade todo-cli-tool`
5. **If current:** Print `"Already up to date (v0.2.0)"`

### `--force` Flag

Skips version check, runs `pipx upgrade --force todo-cli-tool` directly.

### Error Handling

- **Network failure** (no internet, PyPI down): Print friendly error message, exit cleanly
- **`pipx` not found on PATH:** Print `"pipx not found -- install manually with: pipx install todo-cli-tool"`

## README Updates

- Add `**Self-Update**` to the Features bullet list
- Add `todo update`, `todo update --force`, and `todo --version` examples inline to the existing Managing TODOs code block

## Development Workflow

1. **TDD (red-green):** Write tests first for `--version`, `update`, `update --force`, and error cases (network fail, pipx missing, already up to date). Verify they fail.
2. **Green:** Implement version infra, `--version` callback, `update` command, README changes.
3. **Hardening:** Types (no `Any`), ruff check/format, security audit (command injection in subprocess calls, input sanitization on PyPI response data).
4. **Push to CI:** Let CI validate.

## Technical Details

- **PyPI API:** `https://pypi.org/pypi/todo-cli-tool/json` — stable, no auth required
- **Version comparison:** Simple tuple split on `.`, integer comparison — no `packaging` dependency needed
- **Subprocess:** `subprocess.run(["pipx", "upgrade", "todo-cli-tool"])` — no shell=True, no string interpolation
- **No new dependencies:** Uses only `urllib.request`, `json`, `subprocess` from stdlib
