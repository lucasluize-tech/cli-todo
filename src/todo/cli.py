"""Typer CLI application with all commands."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from todo.config import ConfigManager
from todo.models import Priority, Status, Todo
from todo.project import detect_project, generate_llm_file_sections, generate_todos_md
from todo.renderer import render_todo_detail, render_todo_table
from todo.store import TodoStore
from todo.sync import sync as sync_stub
from todo import __version__


def _version_callback(value: bool) -> None:
    if value:
        console = Console()
        console.print(f"todo-cli-tool v{__version__}")
        raise typer.Exit()


app = typer.Typer(help="CLI TODO tool for managing personal TODOs.")


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", help="Show version and exit.", callback=_version_callback, is_eager=True),
    ] = False,
) -> None:
    """CLI TODO tool for managing personal TODOs."""
config_app = typer.Typer(help="Manage configuration.")
categories_app = typer.Typer(help="Manage categories.")
defaults_app = typer.Typer(help="Manage defaults.")

roots_app = typer.Typer(help="Manage project roots.")

app.add_typer(config_app, name="config")
config_app.add_typer(categories_app, name="categories")
config_app.add_typer(defaults_app, name="defaults")
config_app.add_typer(roots_app, name="roots")

err_console = Console(stderr=True)

LLM_INSTALL_URLS: dict[str, str] = {
    "claude": "https://docs.anthropic.com/en/docs/claude-code",
    "codex": "https://github.com/openai/codex",
    "gemini": "https://github.com/google-gemini/gemini-cli",
    "opencode": "https://opencode.ai",
}


def _build_llm_command(llm: str, prompt: str, todo_id: str, project_root: Path) -> list[str]:
    """Build the command list for the given LLM."""
    if llm == "claude":
        return ["claude", prompt, "-n", f"todo:{todo_id}"]
    elif llm == "opencode":
        return ["opencode", str(project_root), "--prompt", prompt]
    else:
        # gemini, codex: same pattern
        return [llm, prompt]


def _get_store() -> TodoStore:
    return TodoStore()


def _get_config_manager() -> ConfigManager:
    return ConfigManager()


def _auto_project(project: str | None) -> str | None:
    if project is not None:
        return project
    config = _get_config_manager().load()
    return detect_project(Path.cwd(), config.defaults.projects_roots)


def _auto_generate(project: str | None) -> None:
    """Auto-regenerate .todos.md and LLM files for the given project."""
    if project is None:
        return
    store = _get_store()
    config = store.load_config()
    all_todos = store.list_todos(project=project)

    # Find the project root
    for root in config.defaults.projects_roots:
        root_path = Path(root).expanduser().resolve()
        project_root = root_path / project
        if project_root.exists():
            break
    else:
        return

    # Generate .todos.md
    md_content = generate_todos_md(project, all_todos)
    todos_md_path = project_root / ".todos.md"
    if todos_md_path.is_symlink():
        raise OSError(f"Refusing to write through symlink: {todos_md_path}")
    todos_md_path.write_text(md_content)

    # Update LLM files
    open_todos = [t for t in all_todos if t.status in (Status.TODO, Status.IN_PROGRESS)]
    critical = [t for t in open_todos if t.priority == Priority.CRITICAL]
    generate_llm_file_sections(
        project_root,
        open_count=len(open_todos),
        critical_count=len(critical),
        llm_files=config.defaults.llm_files,
        llm_files_local=config.defaults.llm_files_local,
    )


@app.command()
def add(
    title: str = typer.Argument(..., help="Title of the TODO"),
    priority: int = typer.Option(None, "-p", "--priority", help="Priority (1-5)"),
    category: str | None = typer.Option(None, "-c", "--category", help="Category"),
    project: str | None = typer.Option(None, "-pj", "--project", help="Project name"),
    due: str | None = typer.Option(None, "-dd", "--due", help="Due date (YYYY-MM-DD)"),
    tags: str | None = typer.Option(None, "-t", "--tags", help="Comma-separated tags"),
    description: str | None = typer.Option(None, "-d", "--description", help="Description"),
) -> None:
    """Create a new TODO."""
    store = _get_store()
    config = store.load_config()

    resolved_project = _auto_project(project)
    resolved_category = category or config.defaults.category
    resolved_priority = priority if priority is not None else config.defaults.priority

    if resolved_category not in config.categories:
        err_console.print(
            f"Error: Category '{resolved_category}' not in config. "
            "Run 'todo config categories list' to see available categories"
        )
        raise typer.Exit(1)

    if not (1 <= resolved_priority <= 5):
        err_console.print("Error: Priority must be between 1 and 5")
        raise typer.Exit(1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    todo = Todo(
        title=title,
        description=description or "",
        priority=Priority(resolved_priority),
        category=resolved_category,
        project=resolved_project,
        tags=tag_list,
        due_date=due,
    )
    store.add(todo)
    _auto_generate(resolved_project)

    console = Console()
    console.print(f"[green]Created TODO [{todo.id}]:[/green] {todo.title}")


@app.command("list")
def list_todos(
    priority: int | None = typer.Option(None, "-p", "--priority", help="Filter by priority"),
    category: str | None = typer.Option(None, "-c", "--category", help="Filter by category"),
    project: str | None = typer.Option(None, "-pj", "--project", help="Filter by project"),
    status: str | None = typer.Option(None, "-s", "--status", help="Filter by status"),
    all_todos: bool = typer.Option(False, "-a", "--all", help="Show all TODOs"),
    tag: str | None = typer.Option(None, "--tag", help="Filter by tag"),
) -> None:
    """List TODOs with optional filters."""
    store = _get_store()

    filter_priority = Priority(priority) if priority is not None else None
    filter_status = Status(status) if status is not None else None

    # Auto-filter to current project unless --all or --project specified
    filter_project = project
    if not all_todos and project is None:
        filter_project = _auto_project(None)

    todos = store.list_todos(
        priority=filter_priority,
        category=category,
        status=filter_status,
        project=filter_project,
        tag=tag,
    )
    render_todo_table(todos)


@app.command()
def show(
    todo_id: str = typer.Argument(..., help="TODO ID"),
) -> None:
    """Show full details of a TODO."""
    store = _get_store()
    todo = store.get(todo_id)
    if todo is None:
        err_console.print(f"Error: No TODO found with ID '{todo_id}'")
        raise typer.Exit(1)
    render_todo_detail(todo)


@app.command()
def edit(
    todo_id: str = typer.Argument(..., help="TODO ID"),
    title: str | None = typer.Option(None, "--title", help="New title"),
    priority: int | None = typer.Option(None, "-p", "--priority", help="Priority (1-5)"),
    category: str | None = typer.Option(None, "-c", "--category", help="Category"),
    project: str | None = typer.Option(None, "-pj", "--project", help="Project name"),
    due: str | None = typer.Option(None, "-dd", "--due", help="Due date"),
    tags: str | None = typer.Option(None, "-t", "--tags", help="Comma-separated tags"),
    description: str | None = typer.Option(None, "-d", "--description", help="Description"),
    status: str | None = typer.Option(None, "-s", "--status", help="Status"),
) -> None:
    """Update fields on an existing TODO."""
    store = _get_store()
    todo = store.get(todo_id)
    if todo is None:
        err_console.print(f"Error: No TODO found with ID '{todo_id}'")
        raise typer.Exit(1)

    kwargs: dict[str, str | Priority | Status | list[str]] = {}
    if title is not None:
        kwargs["title"] = title
    if priority is not None:
        if not (1 <= priority <= 5):
            err_console.print("Error: Priority must be between 1 and 5")
            raise typer.Exit(1)
        kwargs["priority"] = Priority(priority)
    if category is not None:
        config = store.load_config()
        if category not in config.categories:
            err_console.print(
                f"Error: Category '{category}' not in config. "
                "Run 'todo config categories list' to see available categories"
            )
            raise typer.Exit(1)
        kwargs["category"] = category
    if project is not None:
        kwargs["project"] = project
    if due is not None:
        kwargs["due_date"] = due
    if tags is not None:
        kwargs["tags"] = [t.strip() for t in tags.split(",")]
    if description is not None:
        kwargs["description"] = description
    if status is not None:
        kwargs["status"] = Status(status)

    if not kwargs:
        err_console.print("No fields to update. Provide at least one flag.")
        raise typer.Exit(1)

    updated = store.update(todo_id, **kwargs)
    _auto_generate(updated.project)

    console = Console()
    console.print(f"[green]Updated TODO [{todo_id}][/green]")


@app.command()
def done(
    todo_id: str = typer.Argument(..., help="TODO ID"),
) -> None:
    """Mark a TODO as done."""
    store = _get_store()
    todo = store.get(todo_id)
    if todo is None:
        err_console.print(f"Error: No TODO found with ID '{todo_id}'")
        raise typer.Exit(1)

    updated = store.update(todo_id, status=Status.DONE)
    _auto_generate(updated.project)

    console = Console()
    console.print(f"[green]Marked [{todo_id}] as done[/green]")


@app.command()
def start(
    todo_id: str = typer.Argument(..., help="TODO ID"),
    llm: Annotated[
        str | None,
        typer.Argument(help="LLM to launch (claude, codex, gemini, opencode)"),
    ] = None,
) -> None:
    """Mark a TODO as in_progress and optionally launch an LLM session."""
    store = _get_store()
    todo = store.get(todo_id)
    if todo is None:
        err_console.print(f"Error: No TODO found with ID '{todo_id}'")
        raise typer.Exit(1)

    updated = store.update(todo_id, status=Status.IN_PROGRESS)
    _auto_generate(updated.project)

    console = Console()
    console.print(f"[green]Started [{todo_id}][/green]")

    # If no project, just mark in_progress and return
    if updated.project is None:
        if llm is not None:
            err_console.print("Error: Cannot start LLM session without a project")
            raise typer.Exit(1)
        return

    # Resolve LLM
    config = store.load_config()
    resolved_llm = llm or config.defaults.llm

    # Validate LLM
    if resolved_llm not in LLM_INSTALL_URLS:
        err_console.print(
            f"Error: Unsupported LLM '{resolved_llm}'. "
            f"Choose from: {', '.join(sorted(LLM_INSTALL_URLS))}"
        )
        raise typer.Exit(1)

    # Check LLM binary is installed
    if shutil.which(resolved_llm) is None:
        err_console.print(
            f"Error: '{resolved_llm}' is not installed. "
            f"Install it from: {LLM_INSTALL_URLS[resolved_llm]}"
        )
        raise typer.Exit(1)

    # Resolve project root
    project_root: Path | None = None
    for root in config.defaults.projects_roots:
        root_path = Path(root).expanduser().resolve()
        candidate = root_path / updated.project
        if candidate.exists():
            project_root = candidate
            break

    if project_root is None:
        err_console.print(f"Error: Could not find project root for '{updated.project}'")
        raise typer.Exit(1)

    # Build prompt
    prompt = updated.title
    if updated.description:
        prompt = f"{updated.title}\n\n{updated.description}"

    # Launch LLM
    cmd = _build_llm_command(resolved_llm, prompt, todo_id, project_root)
    if project_root.is_symlink():
        err_console.print(
            f"Error: Project root is a symlink (potential security issue): {project_root}"
        )
        raise typer.Exit(1)
    os.chdir(project_root)
    os.execvp(cmd[0], cmd)


@app.command()
def archive(
    todo_id: str | None = typer.Argument(None, help="TODO ID to archive"),
    all_done: bool = typer.Option(False, "--all-done", help="Archive all done TODOs"),
) -> None:
    """Archive completed TODOs."""
    store = _get_store()

    if todo_id is None and not all_done:
        err_console.print("Error: Provide a TODO ID or use --all-done")
        raise typer.Exit(1)

    console = Console()
    if all_done:
        done_todos = store.list_todos(status=Status.DONE)
        if not done_todos:
            console.print("[dim]No done TODOs to archive.[/dim]")
            return
        projects = set()
        for t in done_todos:
            store.update(t.id, status=Status.ARCHIVED)
            if t.project:
                projects.add(t.project)
        for p in projects:
            _auto_generate(p)
        console.print(f"[green]Archived {len(done_todos)} TODOs[/green]")
    else:
        todo = store.get(todo_id)  # type: ignore[arg-type]
        if todo is None:
            err_console.print(f"Error: No TODO found with ID '{todo_id}'")
            raise typer.Exit(1)
        if todo.status != Status.DONE:
            err_console.print(
                f"Error: TODO '{todo_id}' has status '{todo.status.value}'. "
                "Only done items can be archived"
            )
            raise typer.Exit(1)
        store.update(todo_id, status=Status.ARCHIVED)  # type: ignore[arg-type]
        _auto_generate(todo.project)
        console.print(f"[green]Archived [{todo_id}][/green]")


@app.command()
def delete(
    todo_id: str = typer.Argument(..., help="TODO ID"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation"),
) -> None:
    """Remove a TODO permanently."""
    store = _get_store()
    todo = store.get(todo_id)
    if todo is None:
        err_console.print(f"Error: No TODO found with ID '{todo_id}'")
        raise typer.Exit(1)

    if not yes:
        confirm = typer.confirm(f"Delete TODO [{todo_id}] '{todo.title}'?")
        if not confirm:
            raise typer.Abort()

    project = todo.project
    store.delete(todo_id)
    _auto_generate(project)

    console = Console()
    console.print(f"[green]Deleted [{todo_id}][/green]")


@app.command("sync")
def sync_cmd() -> None:
    """Sync TODOs to cloud (stub)."""
    console = Console()
    console.print(sync_stub())


@app.command()
def generate(
    project: str | None = typer.Option(None, "-pj", "--project", help="Project name"),
    all_projects: bool = typer.Option(False, "-a", "--all", help="Regenerate for all projects"),
) -> None:
    """Regenerate .todos.md and CLAUDE.md for a project."""
    store = _get_store()

    if all_projects:
        # Get all unique project names
        all_todos = store.list_todos()
        projects = {t.project for t in all_todos if t.project}
        for proj in projects:
            _auto_generate(proj)
        console = Console()
        console.print(f"[green]Regenerated for {len(projects)} projects[/green]")
    else:
        resolved = _auto_project(project)
        if resolved is None:
            err_console.print("Error: Could not detect project. Use -pj to specify.")
            raise typer.Exit(1)
        _auto_generate(resolved)
        console = Console()
        console.print(f"[green]Regenerated for project '{resolved}'[/green]")


# Config subcommands
@categories_app.command("list")
def categories_list() -> None:
    """List configured categories."""
    mgr = _get_config_manager()
    console = Console()
    for cat in mgr.list_categories():
        console.print(f"  - {cat}")


@categories_app.command("add")
def categories_add(name: str = typer.Argument(..., help="Category name")) -> None:
    """Add a new category."""
    mgr = _get_config_manager()
    try:
        mgr.add_category(name)
    except ValueError as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1) from None
    console = Console()
    console.print(f"[green]Added category '{name}'[/green]")


@categories_app.command("remove")
def categories_remove(
    name: str = typer.Argument(..., help="Category name"),
    force: bool = typer.Option(False, "--force", help="Force removal even if TODOs exist"),
) -> None:
    """Remove a category."""
    store = _get_store()
    mgr = _get_config_manager()

    if not force:
        todos_with_cat = store.list_todos(category=name)
        if todos_with_cat:
            err_console.print(
                f"Error: {len(todos_with_cat)} TODOs use category '{name}'. "
                "Use --force to remove anyway"
            )
            raise typer.Exit(1)

    try:
        mgr.remove_category(name)
    except ValueError as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1) from None
    console = Console()
    console.print(f"[green]Removed category '{name}'[/green]")


@defaults_app.command("set")
def defaults_set(
    key: str = typer.Argument(
        ..., help="Default key (category, priority, llm, llm_files, llm_files_local)"
    ),
    value: str = typer.Argument(..., help="Default value"),
) -> None:
    """Set a default value."""
    mgr = _get_config_manager()
    try:
        mgr.set_default(key, value)
    except ValueError as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1) from None
    console = Console()
    console.print(f"[green]Set default {key} = {value}[/green]")


@roots_app.command("list")
def roots_list() -> None:
    """List configured project roots."""
    mgr = _get_config_manager()
    console = Console()
    roots = mgr.list_projects_roots()
    if not roots:
        console.print("  No project roots configured.")
        return
    for root in roots:
        console.print(f"  - {root}")


@roots_app.command("add")
def roots_add(path: str = typer.Argument(..., help="Path to project root directory")) -> None:
    """Add a project root directory."""
    mgr = _get_config_manager()
    try:
        mgr.add_projects_root(path)
    except ValueError as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1) from None
    console = Console()
    console.print(f"[green]Added project root '{path}'[/green]")


@roots_app.command("remove")
def roots_remove(path: str = typer.Argument(..., help="Path to project root directory")) -> None:
    """Remove a project root directory."""
    mgr = _get_config_manager()
    try:
        mgr.remove_projects_root(path)
    except ValueError as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1) from None
    console = Console()
    console.print(f"[green]Removed project root '{path}'[/green]")
