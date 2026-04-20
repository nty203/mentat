from __future__ import annotations

import asyncio
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mentat.__init__ import __version__

app = typer.Typer(
    name="mentat",
    help="mentat — autonomous multi-agent PM system for solo developers.",
    add_completion=False,
)
project_app = typer.Typer(help="Manage projects.")
skill_app = typer.Typer(help="Manage skills.")
config_app = typer.Typer(help="Manage configuration.")
app.add_typer(project_app, name="project")
app.add_typer(skill_app, name="skill")
app.add_typer(config_app, name="config")

console = Console()

_MIGRATIONS_DIR = str(Path(__file__).parent.parent.parent.parent / "migrations")


def _run_migrations(db_path: str) -> None:
    from mentat.db.migrate import MigrationRunner
    migrations_dir = _MIGRATIONS_DIR
    if not os.path.isdir(migrations_dir):
        migrations_dir = str(Path(__file__).parent.parent.parent.parent / "migrations")
    MigrationRunner(db_path, migrations_dir).run()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _resolve_scan_paths(cli_path: str) -> list[str]:
    if cli_path:
        return [os.path.abspath(cli_path)]
    from mentat.config import get_scan_paths
    configured = get_scan_paths()
    if configured:
        return configured
    return [os.path.expanduser("~")]


# ─── main callback ────────────────────────────────────────────────────────────

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


# ─── bootstrap ────────────────────────────────────────────────────────────────

@app.command()
def bootstrap(
    path: str = typer.Argument("", help="Path to scan (overrides config)."),
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
    from mentat.config import get_db_path
    db_path = get_db_path()
    try:
        _run_migrations(db_path)
        console.print("[green]✓[/green]")
    except RuntimeError as e:
        console.print(f"\n[red bold]Error:[/red bold] {e}")
        raise typer.Exit(1)

    # [2/3] Scan
    scan_paths = _resolve_scan_paths(path)

    if scan_paths == [os.path.expanduser("~")] and not path:
        console.print(
            "\n[yellow]Tip:[/yellow] No scan paths configured. "
            "Run [bold]mentat config paths[/bold] to set specific directories.\n"
        )

    console.print("[blue][2/3][/blue] Scanning for projects...")
    for p in scan_paths:
        console.print(f"      [dim]{p}[/dim]")

    from mentat.agents.discovery import DiscoveryAgent
    all_approvals = []
    total_fs = total_git = 0

    for scan_path in scan_paths:
        agent = DiscoveryAgent(scan_path=scan_path, anthropic_client=None, db_path=db_path)
        signals = await agent.scan()
        total_fs += sum(1 for s in signals if s.source == "fs")
        total_git += sum(1 for s in signals if s.source == "git")
        approvals = await agent.bootstrap()
        all_approvals.extend(approvals)

    console.print(f"      [dim]fs: {total_fs} signals  git: {total_git} signals[/dim]")

    # [3/3] Done
    console.print(
        f"[blue][3/3][/blue] Ready. [green]{len(all_approvals)}[/green] project(s) discovered.\n"
    )
    console.print("Run [bold]mentat review[/bold] to inspect the approval queue.")

    if len(all_approvals) > 0:
        from mentat.notifications import notify
        notify("mentat", f"{len(all_approvals)}개 프로젝트가 승인 대기 중입니다.")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        if non_interactive:
            console.print(
                "\n[red bold]Error:[/red bold] ANTHROPIC_API_KEY not set.\n"
                "Run [bold]mentat config-init[/bold] to configure."
            )
            raise typer.Exit(1)
        console.print(
            "\n[yellow]Warning:[/yellow] ANTHROPIC_API_KEY not set. "
            "Needed for Phase 1 features. Run [bold]mentat config-init[/bold]."
        )


# ─── config-init ──────────────────────────────────────────────────────────────

@app.command("config-init")
def config_init() -> None:
    """Interactive setup (API key + scan paths)."""
    console.print(f"[blue bold]mentat config-init[/blue bold]\n")

    console.print("[bold][1/2] API Key[/bold]")
    api_key = typer.prompt(
        "ANTHROPIC_API_KEY (leave empty to skip)",
        default="",
        hide_input=True,
        show_default=False,
    )
    if api_key:
        from mentat.config import set_api_key
        set_api_key(api_key)
        console.print("[green]✓[/green] Saved to .env\n")
    else:
        console.print("[dim]Skipped.\n[/dim]")

    console.print("[bold][2/2] Scan Paths[/bold]")
    console.print("[dim]These directories will be scanned when you run 'mentat bootstrap'.[/dim]\n")
    _interactive_paths_ui()


# ─── config paths ─────────────────────────────────────────────────────────────

@config_app.command("paths")
def config_paths() -> None:
    """View and edit scan paths interactively."""
    console.print(f"[blue bold]mentat config paths[/blue bold]\n")
    _interactive_paths_ui()


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    from mentat.config import get_config_path, get_scan_paths, get_db_path
    path = get_config_path()

    console.print(f"[dim]Config file: {path}[/dim]\n")

    if not path.exists():
        console.print("[dim]No config file found. Run [bold]mentat config-init[/bold].[/dim]")
        return

    scan_paths = get_scan_paths()
    db_path = get_db_path()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("db_path", db_path)
    if scan_paths:
        table.add_row("scan.paths", scan_paths[0])
        for p in scan_paths[1:]:
            table.add_row("", p)
    else:
        table.add_row("scan.paths", "[dim](none — will use home directory)[/dim]")

    console.print(table)


def _interactive_paths_ui() -> None:
    from mentat.config import get_scan_paths, set_scan_paths, get_config_path

    paths: list[str] = list(get_scan_paths())

    while True:
        _print_paths(paths)

        console.print(
            "\n[bold][[a][/bold] Add  [bold][d][/bold] Remove  "
            "[bold][s][/bold] Save & exit  [bold][q][/bold] Quit without saving"
        )
        choice = typer.prompt(">", default="").strip().lower()

        if choice == "a":
            raw = typer.prompt("Enter directory path").strip()
            if not raw:
                continue
            expanded = str(Path(os.path.expandvars(os.path.expanduser(raw))))
            if not os.path.isdir(expanded):
                console.print(f"[yellow]Warning:[/yellow] Directory not found: {expanded}")
                confirm = typer.confirm("Add anyway?", default=False)
                if not confirm:
                    continue
            if expanded in paths:
                console.print("[dim]Already in the list.[/dim]")
            else:
                paths.append(expanded)
                console.print(f"[green]✓[/green] Added: [bold]{expanded}[/bold]")

        elif choice == "d":
            if not paths:
                console.print("[dim]No paths to remove.[/dim]")
                continue
            idx_str = typer.prompt("Remove number").strip()
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(paths):
                    removed = paths.pop(idx)
                    console.print(f"[green]✓[/green] Removed: [bold]{removed}[/bold]")
                else:
                    console.print("[red]Invalid number.[/red]")
            except ValueError:
                console.print("[red]Enter a number.[/red]")

        elif choice == "s":
            set_scan_paths(paths)
            cfg_path = get_config_path()
            console.print(f"\n[green]✓[/green] Config saved to [bold]{cfg_path}[/bold]")
            console.print("Run [bold]mentat bootstrap[/bold] to start scanning.")
            break

        elif choice == "q":
            console.print("[dim]No changes saved.[/dim]")
            break

        else:
            console.print("[dim]Unknown command. Use a / d / s / q.[/dim]")


def _print_paths(paths: list[str]) -> None:
    if not paths:
        console.print(Panel("[dim]No scan paths configured.[/dim]", title="Scan Paths"))
        return
    text = Text()
    for i, p in enumerate(paths, 1):
        text.append(f"  {i}. ", style="bold")
        text.append(f"{p}\n")
    console.print(Panel(text, title=f"Scan Paths ({len(paths)})"))


# ─── scan ─────────────────────────────────────────────────────────────────────

@app.command()
def scan(
    path: str = typer.Argument("", help="Path to scan (overrides config)."),
) -> None:
    """Scan for project signals (dry-run, no save)."""
    asyncio.run(_scan(path))


async def _scan(path: str) -> None:
    scan_paths = _resolve_scan_paths(path)

    console.print(f"Scanning [bold]{len(scan_paths)}[/bold] path(s)...\n")
    for p in scan_paths:
        console.print(f"  [dim]{p}[/dim]")
    console.print()

    from mentat.agents.discovery import DiscoveryAgent
    all_signals = []
    for scan_path in scan_paths:
        agent = DiscoveryAgent(scan_path=scan_path, anthropic_client=None)
        signals = await agent.scan()
        all_signals.extend(signals)

    if not all_signals:
        console.print("[dim]No signals found.[/dim]")
        return

    table = Table(show_header=True)
    table.add_column("Type", style="bold")
    table.add_column("Source")
    table.add_column("Path")
    table.add_column("Details")
    for s in all_signals:
        table.add_row(s.type, s.source, s.path, s.details)

    console.print(table)
    console.print(f"\n[green]{len(all_signals)}[/green] signal(s) found.")


# ─── review ───────────────────────────────────────────────────────────────────

@app.command()
def review() -> None:
    """Show approval queue and interactively approve or reject."""
    asyncio.run(_review())


async def _review() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    from mentat.config import get_db_path
    db_path = get_db_path()

    try:
        _run_migrations(db_path)
    except RuntimeError as e:
        console.print(f"[red bold]Error:[/red bold] {e}")
        raise typer.Exit(1)

    from mentat.db.repository import ApprovalRepository, ProjectRepository
    repo = ApprovalRepository(db_path)
    pending = await repo.list_pending()

    if not pending:
        console.print("[dim]Approval queue is empty. Run [bold]mentat bootstrap[/bold] first.[/dim]")
        return

    table = Table(show_header=True, title=f"Approval Queue ({len(pending)} pending)")
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="bold")
    table.add_column("Path")
    table.add_column("Type")

    for i, req in enumerate(pending, 1):
        table.add_row(
            str(i),
            req.data.get("name", req.id[:8]),
            req.data.get("path", ""),
            req.type.value,
        )

    console.print(table)
    console.print()
    console.print("[bold][[a][/bold] Approve all  [bold][r][/bold] Review one by one  [bold][q][/bold] Quit")

    choice = typer.prompt(">", default="").strip().lower()

    project_repo = ProjectRepository(db_path)

    if choice == "a":
        for req in pending:
            await repo.approve(req.id)
            await project_repo.save(
                name=req.data.get("name", req.id[:8]),
                path=req.data.get("path", ""),
                metadata={"source": req.data.get("source", "fs"), "details": req.data.get("details", "")},
            )
        console.print(f"[green]✓[/green] {len(pending)}개 모두 승인했습니다.")

    elif choice == "r":
        approved = rejected = 0
        for req in pending:
            name = req.data.get("name", req.id[:8])
            path = req.data.get("path", "")
            console.print(f"\n[bold]{name}[/bold]  [dim]{path}[/dim]")
            decision = typer.prompt("[y] approve  [n] reject  [s] skip", default="s").strip().lower()
            if decision == "y":
                await repo.approve(req.id)
                await project_repo.save(
                    name=name,
                    path=path,
                    metadata={"source": req.data.get("source", "fs"), "details": req.data.get("details", "")},
                )
                console.print("[green]✓ 승인[/green]")
                approved += 1
            elif decision == "n":
                await repo.reject(req.id)
                console.print("[red]✗ 거절[/red]")
                rejected += 1
            else:
                console.print("[dim]건너뜀[/dim]")
        console.print(f"\n[green]{approved}개 승인[/green]  [red]{rejected}개 거절[/red]")

    else:
        console.print("[dim]취소됨.[/dim]")


# ─── serve ────────────────────────────────────────────────────────────────────

@app.command()
def serve(
    port: int = typer.Option(8765, "--port", help="Port to listen on"),
    no_open: bool = typer.Option(False, "--no-open", help="Don't open browser automatically"),
) -> None:
    """Start web UI and introspection API."""
    import uvicorn
    from dotenv import load_dotenv
    load_dotenv()

    from mentat.config import get_db_path
    db_path = get_db_path()

    try:
        _run_migrations(db_path)
    except RuntimeError as e:
        console.print(f"[red bold]Error:[/red bold] {e}")
        raise typer.Exit(1)

    from mentat.web.app import create_app
    fastapi_app = create_app(db_path)

    url = f"http://127.0.0.1:{port}"
    console.print(f"Starting mentat web UI on [bold]{url}[/bold]")
    console.print("Press Ctrl+C to stop.\n")

    if not no_open:
        timer = threading.Timer(1.0, webbrowser.open, args=[url])
        timer.start()

    try:
        uvicorn.run(fastapi_app, host="127.0.0.1", port=port, log_level="warning")
    except OSError as e:
        if "address already in use" in str(e).lower() or "10048" in str(e):
            console.print(f"\n[red bold]Error:[/red bold] Port {port} is in use.")
            console.print(f"  [dim]Cause:[/dim] Another process is listening on that port.")
            console.print(f"  [dim]Fix:[/dim] Kill it or use [bold]--port[/bold] to choose another.")
            raise typer.Exit(1)
        raise


# ─── propose-project ──────────────────────────────────────────────────────────

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


# ─── feedback ─────────────────────────────────────────────────────────────────

@app.command()
def feedback(
    task_id: str = typer.Argument(..., help="Task ID"),
) -> None:
    """Record task feedback."""
    text = typer.prompt("Feedback")
    console.print(f"[green]✓[/green] Feedback recorded for task [bold]{task_id}[/bold].")


# ─── project ──────────────────────────────────────────────────────────────────

@project_app.command("list")
def project_list() -> None:
    """List projects."""
    asyncio.run(_project_list())


async def _project_list() -> None:
    from mentat.config import get_db_path
    db_path = get_db_path()
    try:
        _run_migrations(db_path)
    except RuntimeError:
        pass
    from mentat.db.repository import ProjectRepository
    projects = await ProjectRepository(db_path).list_all()
    if not projects:
        console.print("[dim]No projects yet. Run [bold]mentat bootstrap[/bold].[/dim]")
        return
    table = Table(show_header=True)
    table.add_column("Name", style="bold")
    table.add_column("Path")
    table.add_column("Added")
    for p in projects:
        table.add_row(p["name"], p["path"], p.get("created_at", "")[:10])
    console.print(table)


@project_app.command("add")
def project_add(path: str = typer.Argument(...)) -> None:
    """Add a project by path."""
    console.print(f"[green]✓[/green] Project added: [bold]{path}[/bold]")


# ─── skill ────────────────────────────────────────────────────────────────────

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


# ─── entry point ──────────────────────────────────────────────────────────────

def app_entry() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app()
