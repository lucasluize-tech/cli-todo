"""Rich output formatting for TODO display."""

from __future__ import annotations

from datetime import date

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from todo.models import Todo


def render_todo_table(todos: list[Todo], *, console: Console | None = None) -> None:
    console = console or Console()

    if not todos:
        console.print("[dim]No TODOs found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Pri", width=10)
    table.add_column("Title", min_width=20)
    table.add_column("Category", width=12)
    table.add_column("Status", width=12)
    table.add_column("Due", width=14)

    for todo in todos:
        priority_text = Text(todo.priority.label, style=todo.priority.color)

        due_text = ""
        if todo.due_date:
            try:
                due = date.fromisoformat(todo.due_date)
                if due < date.today():
                    due_text = f"[red]{todo.due_date} OVERDUE[/red]"
                else:
                    due_text = todo.due_date
            except ValueError:
                due_text = todo.due_date

        status_display = todo.status.value.replace("_", " ")

        table.add_row(
            todo.id,
            priority_text,
            todo.title,
            todo.category,
            status_display,
            due_text,
        )

    console.print(table)


def render_todo_detail(todo: Todo, *, console: Console | None = None) -> None:
    console = console or Console()

    lines: list[str] = []
    lines.append(f"[bold]ID:[/bold] {todo.id}")
    lines.append(f"[bold]Title:[/bold] {todo.title}")

    if todo.description:
        lines.append(f"[bold]Description:[/bold] {todo.description}")

    color = todo.priority.color
    lines.append(f"[bold]Priority:[/bold] [{color}]{todo.priority.label}[/{color}]")
    lines.append(f"[bold]Category:[/bold] {todo.category}")
    lines.append(f"[bold]Status:[/bold] {todo.status.value}")

    if todo.project:
        lines.append(f"[bold]Project:[/bold] {todo.project}")
    if todo.tags:
        lines.append(f"[bold]Tags:[/bold] {', '.join(todo.tags)}")
    if todo.due_date:
        lines.append(f"[bold]Due:[/bold] {todo.due_date}")
    if todo.completed_at:
        lines.append(f"[bold]Completed:[/bold] {todo.completed_at.isoformat()}")

    lines.append(f"[bold]Created:[/bold] {todo.created_at.isoformat()}")
    lines.append(f"[bold]Updated:[/bold] {todo.updated_at.isoformat()}")

    content = "\n".join(lines)
    console.print(Panel(content, title=f"TODO: {todo.title}", border_style="blue"))
