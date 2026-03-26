# CLI TODO Tool — Design Specification

**Date**: 2026-03-26
**Status**: Draft
**Author**: Lucas Luize + Claude

## Overview

A Python CLI tool for managing personal TODOs across life categories and project directories. Integrates with Claude Code via per-project `.todos.md` files and CLAUDE.md pointers. Designed for single-user use with future cloud sync capability.

## Goals

- Fast, readable CLI for managing TODOs with priorities and life categories
- Project-aware: auto-detects project from working directory
- Claude Code integration: generated `.todos.md` and CLAUDE.md pointers per project
- Professional SDLC: TDD, CI/CD, code reviews, PyPI distribution
- Community-shareable open source tool

## Non-Goals (v1)

- TUI/interactive mode
- Cloud sync implementation (stub only)
- `/grab-todos` skill (designed after core CLI)
- Recurring/repeating TODOs
- Subtasks/dependencies between TODOs

---

## Architecture

### Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.13 (locally via `uv`) |
| CI matrix | Python 3.11, 3.12, 3.13 |
| CLI framework | Typer |
| Terminal output | Rich |
| Data format | YAML (PyYAML) |
| Validation | Pydantic |
| Package manager | `uv` |
| Testing | pytest + pytest-cov |
| Linting | ruff |
| Type checking | mypy |
| Distribution | PyPI via `pipx` |

### Project Structure

```
cli-tools/
├── src/
│   └── todo/
│       ├── __init__.py
│       ├── cli.py            # Typer app, command definitions
│       ├── models.py         # Pydantic models (Todo, Config)
│       ├── store.py          # YAML read/write, master file management
│       ├── renderer.py       # Rich output formatting (tables, colors)
│       ├── project.py        # Project detection, .todos.md generation, CLAUDE.md updates
│       ├── config.py         # User config management (categories, defaults)
│       └── sync.py           # Cloud sync interface (stub for now)
├── tests/
│   ├── conftest.py           # Shared fixtures (temp dirs, sample data)
│   ├── test_cli.py           # CLI integration tests via CliRunner
│   ├── test_models.py        # Pydantic model validation tests
│   ├── test_store.py         # YAML store read/write tests
│   ├── test_renderer.py      # Output formatting tests
│   └── test_project.py       # Project detection & generation tests
├── .github/
│   └── workflows/
│       ├── ci.yml            # Test + lint on every PR
│       └── release.yml       # Publish to PyPI on tag
├── pyproject.toml
├── CLAUDE.md
├── README.md
└── LICENSE
```

### Environment Setup

- `uv venv --python 3.13` at project root
- Always activate the virtual environment when working on this project
- All dependency operations via `uv add`, `uv sync`, `uv run`

---

## Data Models

### Master File: `~/.todo/todos.yml`

```yaml
todos:
  - id: "a3f7b2"
    title: "Implement auth middleware"
    description: "Add JWT validation to all API routes"
    priority: 1
    category: "Work"
    project: "cli-tools"
    status: "todo"
    tags: ["backend", "auth"]
    due_date: "2026-04-01"
    completed_at: null
    created_at: "2026-03-26T10:00:00"
    updated_at: "2026-03-26T10:00:00"
```

### Config File: `~/.todo/config.yml`

```yaml
categories:
  - Work
  - Family
  - Hobbies
  - Health
  - Finance
  - Education
  - Social
defaults:
  category: "Work"
  priority: 3
  projects_roots:
    - "~/projects"
    - "~/work"
```

### Field Definitions

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `id` | string | auto-generated | — | First 6 chars of UUID4 hex, max 3 retries on collision, error if all collide |
| `title` | string | yes | — | Short description of the task |
| `description` | string | no | `""` | Optional longer details |
| `priority` | int (1-5) | yes | 3 (Medium) | 1=Critical, 2=High, 3=Medium, 4=Low, 5=None |
| `category` | string | yes | "Work" | Must exist in config categories |
| `project` | string | no | `null` | Auto-detected from pwd if under any `projects_roots` path |
| `status` | enum | auto | "todo" | `todo`, `in_progress`, `done`, `archived` |
| `tags` | list[string] | no | `[]` | Freeform tags |
| `due_date` | date | no | `null` | ISO format YYYY-MM-DD |
| `created_at` | datetime | auto | now | ISO format |
| `completed_at` | datetime | no | `null` | Set when status transitions to `done`, cleared if reopened |
| `updated_at` | datetime | auto | now | Updated on any edit |

### Priority Labels & Colors

| Value | Label | Rich Color |
|-------|-------|------------|
| 1 | Critical | red |
| 2 | High | orange3 |
| 3 | Medium | yellow |
| 4 | Low | dodger_blue2 |
| 5 | None | dim |

### File Locking

PID-based write lock at `~/.todo/.lock`. The lock file contains the PID of the holding process. Acquire before write, release after. Stale lock detection: if the lock is >60s old OR the PID is no longer alive, auto-cleanup and re-acquire.

---

## CLI Commands

### `todo add "title"`

Create a new TODO.

**Flags:**
- `-p` / `--priority` (int, default: from config)
- `-c` / `--category` (string, default: from config)
- `-pj` / `--project` (string, default: auto-detect from pwd)
- `-dd` / `--due` (date string)
- `-t` / `--tags` (comma-separated string)
- `-d` / `--description` (string)

**Behavior:**
- Generates a 6-char ID (max 3 retries on collision)
- Auto-detects project if pwd is under any configured `projects_roots` path
- Auto-runs `generate` for the affected project
- Prints the created TODO summary

### `todo list`

List TODOs with optional filters.

**Flags:**
- `-p` / `--priority` (int)
- `-c` / `--category` (string)
- `-pj` / `--project` (string)
- `-s` / `--status` (string)
- `-a` / `--all` (bool)
- `--tag` (string, no short flag — filters TODOs containing the given tag)

Note: Short flags are scoped per-subcommand (Typer handles this naturally).

**Behavior:**
- No flags in a project directory: auto-filters to that project
- No flags outside a project directory: shows all TODOs (equivalent to `--all`)
- `-a` / `--all`: explicitly shows all TODOs across all projects
- Multiple filters stack (AND logic)
- Output: Rich table with columns — ID, Priority (colored label), Title, Category, Status, Due
- Overdue items highlighted in red

### `todo show <id>`

Display full details of a single TODO in a Rich panel.

### `todo edit <id>`

Update fields on an existing TODO.

**Flags:** Same as `add`, plus:
- `-s` / `--status` (string) — allows setting any valid status (`todo`, `in_progress`, `done`, `archived`). This is the way to revert a mistaken status transition (e.g., `todo edit <id> -s todo` to reopen a done item).

Only provided flags are updated.

**Behavior:**
- Updates `updated_at` timestamp
- If status transitions to `done`, sets `completed_at`; if transitioning away from `done`, clears `completed_at`
- Auto-runs `generate` for the affected project

### `todo done <id>`

Mark a TODO as done. Sets `status` to `done`, updates `updated_at`. Auto-runs `generate`.

### `todo start <id>`

Mark a TODO as in_progress. Sets `status` to `in_progress`, updates `updated_at`. Auto-runs `generate`.

### `todo archive`

Archive completed TODOs.

**Arguments:** `<id>` (required positional) to archive one, or `--all-done` flag to archive all completed. Running `todo archive` with neither argument nor flag produces an error. Only TODOs with `done` status can be archived — archiving a `todo` or `in_progress` item is rejected with an error.

Auto-runs `generate` for affected projects.

### `todo delete <id>`

Remove a TODO permanently. Prompts for confirmation before deleting. Auto-runs `generate`.

### `todo sync`

Stub command for v1. Prints: "Cloud sync not yet configured. Coming soon."

### `todo config`

Manage categories and defaults.

**Subcommands:**
- `todo config categories list`
- `todo config categories add "Pets"`
- `todo config categories remove "Social"` (refuses if TODOs exist with that category; use `--force` to override)
- `todo config defaults set priority 2`
- `todo config defaults set category "Work"`

### `todo generate`

Regenerate per-project `.todos.md` and CLAUDE.md pointer.

**Flags:**
- `-pj` / `--project` (string, default: auto-detect)
- `-a` / `--all` (bool, regenerate for all projects)

---

## Project Integration

### Per-Project `.todos.md`

Generated markdown file placed at the project root. Should be added to `.gitignore` (the `generate` command will offer to do this automatically if `.gitignore` exists and `.todos.md` is not already listed).

```markdown
<!-- AUTO-GENERATED by todo CLI - Do not edit manually -->
<!-- Last updated: 2026-03-26T10:00:00 -->

# Project TODOs: cli-tools

## In Progress (1)
- [a3f7b2] **Implement auth middleware** — Priority: Critical — Due: 2026-04-01

## Todo (2)
- [b8c4d1] **Write unit tests for store** — Priority: High
- [e2f9a0] **Add README examples** — Priority: Medium — Tags: docs

## Done (1)
- [c1d5e3] ~~Set up project structure~~ — Completed: 2026-03-25
```

- Grouped by status: In Progress → Todo → Done (archived items excluded)
- Sorted by priority within each group (1/Critical first)
- Done items shown with strikethrough

### CLAUDE.md Pointer

Auto-injected/updated section at the end of the project's CLAUDE.md, using sentinel comments for safe detection and replacement:

```markdown
<!-- BEGIN TODO CLI -->
## Project TODOs
This project has **3 open** TODOs (1 critical). See `.todos.md` for the full list.
Run `todo list` for details or invoke the `/grab-todos` skill.
<!-- END TODO CLI -->
```

- If CLAUDE.md doesn't exist, creates one with just this section
- If the sentinel comments already exist, replaces everything between them
- If CLAUDE.md exists but has no sentinels, appends the section at the end
- Only counts open items (`todo` + `in_progress` statuses)

### Project Auto-Detection

When the user runs a command from within a subdirectory of any configured `projects_roots` path:
1. Walk up from `pwd` to find the first directory directly under a `projects_roots` entry
2. Use that directory name as the project name
3. Example: `pwd` is `~/projects/cli-tools/src/todo/` → project is `cli-tools`

---

## Error Handling

All errors print to stderr via `rich.console.Console(stderr=True)`.

### Exit Codes

| Code | Meaning | Examples |
|------|---------|---------|
| 0 | Success | — |
| 1 | User error | Invalid ID, validation failure, category not found, invalid priority |
| 2 | System error | IO error, permission denied, corrupt YAML file, lock acquisition failed |

### Common Error Messages

| Scenario | Message |
|----------|---------|
| Invalid TODO ID | `Error: No TODO found with ID 'abc123'` |
| Invalid priority | `Error: Priority must be between 1 and 5` |
| Unknown category | `Error: Category 'Foo' not in config. Run 'todo config categories list' to see available categories` |
| Category removal with existing TODOs | `Error: 3 TODOs use category 'Work'. Use --force to remove anyway` |
| Corrupt YAML | `Error: Could not parse ~/.todo/todos.yml. File may be corrupted` |
| Lock acquisition failed | `Error: Could not acquire lock. Another todo process may be running (PID: 12345)` |
| Archive non-done item | `Error: TODO 'abc123' has status 'todo'. Only done items can be archived` |

---

## Testing Strategy

### Approach: Test-Driven Development

All code is written test-first. Tests are organized by module.

### Test Modules

**`test_models.py`** — Pydantic model validation:
- Valid TODO creation with all fields
- Default values applied correctly
- Invalid priority (0, 6, -1) rejected
- Invalid status rejected
- Category must exist in config
- Timestamps auto-populated

**`test_store.py`** — YAML store operations:
- Create master file on first write
- Read/write roundtrip preserves data
- Add, update, delete operations
- File locking (concurrent write prevention)
- Corrupt file handling (graceful error)
- Empty file handling

**`test_cli.py`** — CLI integration via CliRunner:
- `add` creates a TODO and outputs confirmation
- `list` displays filtered table
- `show` displays full detail panel
- `edit` updates specified fields only
- `done` / `start` transition status
- `delete` prompts for confirmation
- `config` subcommands modify config.yml
- Flag shorthands work (-p, -c, -pj, -dd, -t, -s, -a)
- Auto project detection from pwd

**`test_project.py`** — Project integration:
- Auto-detect project from various pwd depths
- `.todos.md` generation matches expected format
- CLAUDE.md section injection (new file)
- CLAUDE.md section update (existing file, existing section)
- `generate` only affects specified project

**`test_renderer.py`** — Output formatting:
- Table columns present and ordered
- Priority labels and colors correct
- Overdue items highlighted
- Empty list message

### Test Infrastructure

- All tests use `tmp_path` / `tmp_home` fixtures — never touch real `~/.todo/`
- `conftest.py` provides: sample TODOs, sample config, mock home directory
- Target: 90%+ code coverage

---

## CI/CD

### `ci.yml` — Continuous Integration

Triggers: push to any branch, pull requests to `main`.

Steps:
1. Matrix: Python 3.11, 3.12, 3.13
2. Setup: `uv sync`
3. `ruff check` — linting
4. `ruff format --check` — formatting
5. `mypy src/` — type checking
6. `pytest --cov --cov-report=xml` — tests + coverage
7. Coverage gate: fail if below 90%

### `release.yml` — Release to PyPI

Triggers: push tag matching `v*`.

Steps:
1. Run full CI suite
2. `python -m build`
3. Publish to PyPI via trusted publisher (OIDC)

### Claude Code Review

- GitHub Action using `claude-code-action` on PRs
- Reviews for code quality, test coverage, and project conventions

### Branch Strategy

- `main` — protected, requires passing CI + approved review
- `feat/<name>` — feature branches
- `fix/<name>` — bug fix branches

---

## Future Work (Post-v1)

- **Cloud sync**: Google Drive API integration via `todo sync` command
- **`/grab-todos` skill**: On-demand skill that loads `.todos.md` into Claude context
- **Session start hook**: Optional hook that runs `todo summary --project auto` on Claude Code startup
- **TUI mode**: Interactive terminal UI for browsing/managing TODOs
- **Recurring TODOs**: Repeating tasks with configurable schedules
- **Subtasks**: Parent/child relationships between TODOs
