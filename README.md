<div align="center">
  <h1 align="center">todo-cli-tool</h1>
  <h3>A fast, project-aware CLI for managing personal TODOs across your life.</h3>
</div>

<br/>

<div align="center">
  <a href="https://github.com/lucasluize-tech/cli-todo/stargazers"><img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/lucasluize-tech/cli-todo"></a>
  <a href="https://github.com/lucasluize-tech/cli-todo/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <a href="https://pypi.org/project/todo-cli-tool/"><img alt="PyPI" src="https://img.shields.io/pypi/v/todo-cli-tool"></a>
  <a href="https://github.com/lucasluize-tech/cli-todo/actions"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/lucasluize-tech/cli-todo/ci.yml"></a>
</div>

<br/>

Manage TODOs from the terminal with priorities, life categories, and automatic project detection. Integrates with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) via per-project `.todos.md` files and `CLAUDE.md` pointers.

## Features

- **Life Categories:** Organize TODOs across Work, Family, Health, Hobbies, and custom categories.
- **Priority System:** Five priority levels (Critical to None) with color-coded Rich output.
- **Project-Aware:** Auto-detects your project from the working directory — no flags needed.
- **Claude Code Integration:** Auto-generates `.todos.md` and updates `CLAUDE.md` so your AI assistant always knows your TODOs.
- **Beautiful Output:** Rich-powered tables and detail panels with overdue highlighting.
- **Single YAML Store:** All TODOs in one file (`~/.todo/todos.yml`) — easy to backup, sync, or inspect.

## Demo

```
$ todo add "Implement auth middleware" -p 1 -c Work -dd 2026-04-01 -t backend,auth
Created TODO [a3f7b2]: Implement auth middleware

$ todo list
┏━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ ID       ┃ Pri        ┃ Title                      ┃ Category     ┃ Status       ┃ Due            ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ a3f7b2   │ Critical   │ Implement auth middleware   │ Work         │ todo         │ 2026-04-01     │
└──────────┴────────────┴────────────────────────────┴──────────────┴──────────────┴────────────────┘

$ todo done a3f7b2
Marked [a3f7b2] as done
```

## Tech Stack

- [Python 3.11+](https://www.python.org/) — Language
- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Rich](https://rich.readthedocs.io/) — Terminal output
- [Pydantic](https://docs.pydantic.dev/) — Data validation
- [PyYAML](https://pyyaml.org/) — Data storage
- [uv](https://docs.astral.sh/uv/) — Package management
- [pytest](https://docs.pytest.org/) — Testing
- [ruff](https://docs.astral.sh/ruff/) — Linting & formatting
- [mypy](https://mypy-lang.org/) — Type checking

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install from PyPI

```shell
pipx install todo-cli-tool
```

### Or install from source

```shell
git clone https://github.com/lucasluize-tech/cli-todo.git
cd cli-tools
uv venv --python 3.13
source .venv/bin/activate
uv pip install -e .
```

### Add `todo` to your PATH

Symlink the binary so it's available globally, without needing to activate the venv:

```shell
ln -sf "$(pwd)/.venv/bin/todo" ~/.local/bin/todo
```

Make sure `~/.local/bin` is in your `PATH`. Then you can run `todo` from anywhere.

### Verify the installation

```shell
todo --help
```

## Usage

### Managing TODOs

```shell
# Add a TODO with priority, category, due date, and tags
todo add "Buy groceries" -p 2 -c Family -dd 2026-04-15 -t errands

# List all TODOs
todo list -a

# List TODOs for the current project (auto-detected)
todo list

# Filter by category, priority, status, or tag
todo list -c Work -p 1
todo list --tag backend

# Show full details of a TODO
todo show a3f7b2

# Edit a TODO
todo edit a3f7b2 --title "New title" -p 3

# Mark as in-progress or done
todo start a3f7b2
todo done a3f7b2

# Archive completed TODOs
todo archive a3f7b2
todo archive --all-done

# Delete a TODO (with confirmation)
todo delete a3f7b2
```

### Configuration

#### Project Roots (important!)

Project roots are parent directories that contain your projects. The tool uses these to auto-detect which project you're working in based on your current directory.

By default, `~/projects` and `~/work` are configured. If your projects live elsewhere, add your own roots:

```shell
# List configured project roots
todo config roots list

# Add a project root
todo config roots add ~/code
todo config roots add ~/personal

# Remove a project root
todo config roots remove ~/work
```

**How it works:** If `~/projects` is a root and you run `todo add` from `~/projects/my-app`, the tool detects `my-app` as the project. TODOs are tagged with this project and a `.todos.md` file is generated at `~/projects/my-app/.todos.md`.

If your cwd is not inside any configured root, no project is detected and no `.todos.md` is generated.

#### Categories and Defaults

```shell
# List categories
todo config categories list

# Add/remove categories
todo config categories add "Pets"
todo config categories remove "Social"

# Set defaults
todo config defaults set priority 2
todo config defaults set category "Family"
```

### Project Integration

```shell
# Regenerate .todos.md and CLAUDE.md for the current project
todo generate

# Regenerate for all projects
todo generate -a
```

When you run `todo add` or `todo done` from within a configured project root, the tool automatically:
1. Detects the project from your working directory
2. Regenerates `.todos.md` at the project root
3. Updates the `CLAUDE.md` pointer with open TODO counts

## Project Structure

```
cli-tools/
├── src/todo/
│   ├── cli.py          # Typer app, command definitions
│   ├── models.py       # Pydantic models (Todo, Config)
│   ├── store.py        # YAML read/write, file locking
│   ├── renderer.py     # Rich output formatting
│   ├── project.py      # Project detection, .todos.md generation
│   ├── config.py       # User config management
│   └── sync.py         # Cloud sync interface (stub)
├── tests/              # 109 tests, 84% coverage
├── .github/workflows/  # CI + Release pipelines
└── pyproject.toml
```

## Contributing

This is an open-source project and contributions are welcome.

Fork the repository, make your changes, and open a pull request. Please ensure tests pass before submitting:

```shell
uv run pytest
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

## License

MIT
