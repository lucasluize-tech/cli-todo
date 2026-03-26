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
  projects_root: "~/projects"
```

### Field Definitions

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `id` | string | auto-generated | — | First 6 chars of UUID4 hex, regenerate on collision |
| `title` | string | yes | — | Short description of the task |
| `description` | string | no | `""` | Optional longer details |
| `priority` | int (1-5) | yes | 3 (Medium) | 1=Critical, 2=High, 3=Medium, 4=Low, 5=None |
| `category` | string | yes | "Work" | Must exist in config categories |
| `project` | string | no | `null` | Auto-detected from pwd if under projects_root |
| `status` | enum | auto | "todo" | `todo`, `in_progress`, `done`, `archived` |
| `tags` | list[string] | no | `[]` | Freeform tags |
| `due_date` | date | no | `null` | ISO format YYYY-MM-DD |
| `created_at` | datetime | auto | now | ISO format |
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

Simple file-based write lock at `~/.todo/.lock` to prevent corruption from concurrent writes across terminal sessions. Acquire before write, release after. Stale lock detection (>5s age) with auto-cleanup.

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
- Generates a 6-char ID
- Auto-detects project if pwd is under `projects_root`
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

**Behavior:**
- No flags in a project directory: auto-filters to that project
- `-a` / `--all`: shows all TODOs across all projects
- Multiple filters stack (AND logic)
- Output: Rich table with columns — ID, Priority (colored label), Title, Category, Status, Due
- Overdue items highlighted in red

### `todo show <id>`

Display full details of a single TODO in a Rich panel.

### `todo edit <id>`

Update fields on an existing TODO.

**Flags:** Same as `add` — only provided flags are updated.

**Behavior:**
- Updates `updated_at` timestamp
- Auto-runs `generate` for the affected project

### `todo done <id>`

Mark a TODO as done. Sets `status` to `done`, updates `updated_at`. Auto-runs `generate`.

### `todo start <id>`

Mark a TODO as in_progress. Sets `status` to `in_progress`, updates `updated_at`. Auto-runs `generate`.

### `todo archive`

Archive completed TODOs.

**Arguments:** `<id>` to archive one, or `--all-done` flag to archive all completed.

### `todo delete <id>`

Remove a TODO permanently. Prompts for confirmation before deleting. Auto-runs `generate`.

### `todo sync`

Stub command for v1. Prints: "Cloud sync not yet configured. Coming soon."

### `todo config`

Manage categories and defaults.

**Subcommands:**
- `todo config categories list`
- `todo config categories add "Pets"`
- `todo config categories remove "Social"`
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

Generated read-only markdown file placed at the project root.

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

Auto-injected/updated section at the end of the project's CLAUDE.md:

```markdown
## Project TODOs
This project has **3 open** TODOs (1 critical). See `.todos.md` for the full list.
Run `todo list` for details or invoke the `/grab-todos` skill.
```

- If CLAUDE.md doesn't exist, creates one with just this section
- If the section already exists, updates it in place
- Only counts open items (`todo` + `in_progress` statuses)

### Project Auto-Detection

When the user runs a command from within a subdirectory of `projects_root` (default `~/projects`):
1. Walk up from `pwd` to find the first directory directly under `projects_root`
2. Use that directory name as the project name
3. Example: `pwd` is `~/projects/cli-tools/src/todo/` → project is `cli-tools`

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
