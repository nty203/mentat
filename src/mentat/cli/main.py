from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from mentat.__init__ import __version__

app = typer.Typer(
    name="mentat",
    help="mentat — autonomous multi-agent PM system for solo developers.",
    add_completion=False,
)
project_app = typer.Typer(help="Manage projects.")
skill_app = typer.Typer(help="Manage skills.")
app.add_typer(project_app, name="project")
app.add_typer(skill_app, name="skill")

console = Console()

_DEFAULT_DB = str(Path.home() / ".local" / "share" / "mentat" / "db.sqlite")
_MIGRATIONS_DIR = str(Path(__file__).parent.parent.parent.parent / "migrations")


def _get_db_path() -> str:
    return os.environ.get("MENTAT_DB_PATH", _DEFAULT_DB)


def _run_migrations(db_path: str) -> None:
    from mentat.db.migrate import MigrationRunner
    migrations_dir = _MIGRATIONS_DIR
    if not os.path.isdir(migrations_dir):
        # installed via pip — migrations next to package
        migrations_dir = str(Path(__file__).parent.parent.parent.parent / "migrations")
    MigrationRunner(db_path, migrations_dir).run()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    if version:
        console.print(f"mentat v{__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@app.command()
def bootstrap(
    path: str = typer.Argument("", help="Path to scan (default: home directory)"),
    non_interactive: bool = typer.Option(False, "--non-interactive"),
) -> None:
    """Initialize DB, scan projects, open approval queue."""
    asyncio.run(_bootstrap(path, non_interactive))


async def _bootstrap(path: str, non_interactive: bool) -> None:
    from dotenv import load_dotenv
    load_dotenv()

    console.print(f"[blue]mentat v{__version__}[/blue]\n")

    # [1/3] DB
    console.print("[blue][1/3][/blue] Initializing database...", end=" ")
    db_path = _get_db_path()
    try:
        _run_migrations(db_path)
        console.print("[green]✓[/green]")
    except RuntimeError as e:
        console.print(f"\n[red bold]Error:[/red bold] {e}")
        raise typer.Exit(1)

    # [2/3] Scan
    console.print("[blue][2/3][/blue] Scanning for projects...")
    from mentat.agents.discovery import DiscoveryAgent
    scan_path = path or os.path.expanduser("~")
    agent = DiscoveryAgent(scan_path=scan_path, anthropic_client=None)
    signals = await agent.scan()

    fs_count = sum(1 for s in signals if s.source == "fs")
    git_count = sum(1 for s in signals if s.source == "git")
    console.print(f"      [dim]fs: {fs_count} signals  git: {git_count} signals[/dim]")

    approvals = await agent.bootstrap()

    # [3/3] Done
    console.print(f"[blue][3/3][/blue] Ready. [green]{len(approvals)}[/green] project(s) discovered.\n")
    console.print("Run [bold]mentat review[/bold] to inspect the approval queue.")

    # API key warning
    if not os.environ.get("ANTHROPIC_API_KEY"):
        if non_interactive:
            console.print("\n[red bold]Error:[/red bold] ANTHROPIC_API_KEY not set.\nRun [bold]mentat config-init[/bold] to configure.")
            raise typer.Exit(1)
        console.print(
            "\n[yellow]Warning:[/yellow] ANTHROPIC_API_KEY not set. "
            "Needed for Phase 1 features. Run [bold]mentat config-init[/bold]."
        )


@app.command("config-init")
def config_init() -> None:
    """Interactive setup (API key, config.toml)."""
    console.print("[blue]mentat config-init[/blue]\n")
    api_key = typer.prompt("ANTHROPIC_API_KEY", default="", hide_input=True)
    if api_key:
        env_path = Path(".env")
        with open(env_path, "a") as f:
            f.write(f"\nANTHROPIC_API_KEY={api_key}\n")
        console.print(f"[green]✓[/green] Saved to {env_path}")
    else:
        console.print("[dim]Skipped.[/dim]")


@app.command()
def scan(
    path: str = typer.Argument(".", help="Path to scan"),
) -> None:
    """Scan for project signals (dry-run, no save)."""
    asyncio.run(_scan(path))


async def _scan(path: str) -> None:
    abs_path = os.path.abspath(path)
    console.print(f"Scanning [bold]{abs_path}[/bold]...\n")

    from mentat.agents.discovery import DiscoveryAgent
    agent = DiscoveryAgent(scan_path=abs_path, anthropic_client=None)
    signals = await agent.scan()

    if not signals:
        console.print(f"[dim]No signals found in {abs_path}.[/dim]")
        return

    table = Table(show_header=True)
    table.add_column("Type", style="bold")
    table.add_column("Source")
    table.add_column("Path")
    table.add_column("Details")
    for s in signals:
        table.add_row(s.type, s.source, s.path, s.details)

    console.print(table)
    console.print(f"\n[green]{len(signals)}[/green] signal(s) found.")


@app.command()
def review() -> None:
    """Show approval queue."""
    console.print("[dim]Approval queue is empty. Run [bold]mentat bootstrap[/bold] first.[/dim]")


@app.command()
def serve(
    port: int = typer.Option(8765, "--port", help="Port to listen on"),
) -> None:
    """Start introspection API."""
    import uvicorn
    from mentat.core.introspection import app as fastapi_app

    console.print(f"Starting introspection API on [bold]http://127.0.0.1:{port}[/bold]")
    console.print("Press Ctrl+C to stop.\n")
    try:
        uvicorn.run(fastapi_app, host="127.0.0.1", port=port)
    except OSError as e:
        if "address already in use" in str(e).lower() or "10048" in str(e):
            console.print(f"\n[red bold]Error:[/red bold] Port {port} is in use.")
            console.print(f"  [dim]Cause:[/dim] Another process is listening on that port.")
            console.print(f"  [dim]Fix:[/dim] Kill it or use [bold]--port[/bold] to choose another.")
            raise typer.Exit(1)
        raise


@app.command("propose-project")
def propose_project(
    description: str = typer.Argument(..., help="Project description"),
) -> None:
    """Add a project manually."""
    from mentat.core.approval import ApprovalRequest, ApprovalType
    req = ApprovalRequest(
        type=ApprovalType.PROJECT_CANDIDATE,
        data={"description": description, "source": "manual"},
    )
    console.print(f"[green]✓[/green] Approval request created: [bold]{req.id}[/bold]")
    console.print("Run [bold]mentat review[/bold] to approve.")


@app.command()
def feedback(
    task_id: str = typer.Argument(..., help="Task ID"),
) -> None:
    """Record task feedback."""
    text = typer.prompt("Feedback")
    console.print(f"[green]✓[/green] Feedback recorded for task [bold]{task_id}[/bold].")


@project_app.command("list")
def project_list() -> None:
    """List projects."""
    console.print("[dim]No projects yet. Run [bold]mentat bootstrap[/bold].[/dim]")


@project_app.command("add")
def project_add(path: str = typer.Argument(...)) -> None:
    """Add a project by path."""
    console.print(f"[green]✓[/green] Project added: [bold]{path}[/bold]")


@skill_app.command("list")
def skill_list() -> None:
    """List skills."""
    console.print("[dim]No skills yet.[/dim]")
    console.print("[dim]Skills are discovered in Phase 3 when patterns repeat.[/dim]")


@skill_app.command("show")
def skill_show(skill_id: str = typer.Argument(...)) -> None:
    """Show skill details."""
    console.print(f"[red bold]Error:[/red bold] Skill not found: {skill_id}")
    raise typer.Exit(1)


def app_entry() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app()
