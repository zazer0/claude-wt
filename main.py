import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from typing_extensions import Annotated

app = typer.Typer(help="Claude worktree management CLI", no_args_is_help=True)
console = Console()


@app.command()
def new(
    query: Annotated[str, typer.Argument(help="Query to send to Claude")] = "",
    branch: Annotated[str, typer.Option("--branch", help="Branch name suffix")] = "",
):
    """Create a new worktree and launch Claude."""
    try:
        # Get repo root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_root = Path(result.stdout.strip())
        
        # Sync with origin
        subprocess.run(["git", "-C", str(repo_root), "fetch", "origin"], check=True)
        subprocess.run(["git", "-C", str(repo_root), "switch", "--quiet", "main"], check=True)
        subprocess.run(["git", "-C", str(repo_root), "pull", "--ff-only", "--quiet"], check=True)
        
        # Generate branch name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = branch or timestamp
        branch_name = f"claude-wt-{suffix}"
        
        # Create branch if needed
        try:
            subprocess.run(
                ["git", "-C", str(repo_root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
                check=True
            )
        except subprocess.CalledProcessError:
            subprocess.run(
                ["git", "-C", str(repo_root), "branch", branch_name, "main"],
                check=True
            )
        
        # Setup worktree path
        repo_name = repo_root.name
        wt_path = Path(f"/tmp/claude/worktrees/{repo_name}/{branch_name}")
        wt_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create worktree if needed
        if not wt_path.exists():
            subprocess.run(
                ["git", "-C", str(repo_root), "worktree", "add", "--quiet", str(wt_path), branch_name],
                check=True
            )
        
        # Print helpful info
        panel_content = f"""[green]🟢 Resume this session:[/green] [bold]claude-wt resume {suffix}[/bold]
[blue]🧹 Delete this session:[/blue] [bold]claude-wt clean {suffix}[/bold]
[red]🧨 Delete all sessions:[/red] [bold]claude-wt clean --all[/bold]"""
        
        console.print(Panel(panel_content, title="[bold cyan]Session Created[/bold cyan]", border_style="cyan"))
        
        # Launch Claude
        claude_path = shutil.which("claude") or "/Users/jlowin/.claude/local/claude"
        claude_cmd = [claude_path, "--add-dir", str(repo_root)]
        if query:
            claude_cmd.extend(["--", query])
        
        subprocess.run(claude_cmd, cwd=wt_path)
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def resume(branch_name: Annotated[str, typer.Argument(help="Branch name to resume")]):
    """Resume an existing worktree session."""
    try:
        # Get repo root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_root = Path(result.stdout.strip())
        repo_name = repo_root.name
        
        # Find worktree path
        full_branch_name = f"claude-wt-{branch_name}"
        wt_path = Path(f"/tmp/claude/worktrees/{repo_name}/{full_branch_name}")
        
        if not wt_path.exists():
            typer.echo(f"Error: Worktree for branch '{branch_name}' not found at {wt_path}", err=True)
            raise typer.Exit(1)
        
        console.print(f"[yellow]🔄 Resuming session for branch:[/yellow] [bold]{branch_name}[/bold]")
        
        # Launch Claude with --continue to resume conversation
        claude_path = shutil.which("claude") or "/Users/jlowin/.claude/local/claude"
        claude_cmd = [claude_path, "--add-dir", str(repo_root), "--continue"]
        subprocess.run(claude_cmd, cwd=wt_path)
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def clean(
    branch_name: Annotated[str, typer.Argument(help="Specific branch to clean")] = "",
    all: Annotated[bool, typer.Option("--all", help="Clean all claude-wt sessions")] = False,
):
    """Delete claude-wt worktrees and branches."""
    try:
        # Require either branch_name or --all
        if not branch_name and not all:
            typer.echo("Error: Must specify either a branch name or --all flag", err=True)
            raise typer.Exit(1)
        
        if branch_name and all:
            typer.echo("Error: Cannot specify both branch name and --all flag", err=True)
            raise typer.Exit(1)
        
        # Get repo root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_root = Path(result.stdout.strip())
        repo_name = repo_root.name
        wt_root = Path(f"/tmp/claude/worktrees/{repo_name}")
        
        if branch_name:
            # Clean specific branch
            full_branch_name = f"claude-wt-{branch_name}"
            wt_path = wt_root / full_branch_name
            
            # Remove worktree
            if wt_path.exists():
                subprocess.run(
                    ["git", "-C", str(repo_root), "worktree", "remove", "--force", str(wt_path)],
                    check=True
                )
                console.print(f"[green]✅ Removed worktree:[/green] {wt_path}")
            
            # Delete branch
            try:
                subprocess.run(
                    ["git", "-C", str(repo_root), "branch", "-D", full_branch_name],
                    check=True
                )
                console.print(f"[green]✅ Deleted branch:[/green] {full_branch_name}")
            except subprocess.CalledProcessError:
                console.print(f"[yellow]⚠️  Branch {full_branch_name} not found[/yellow]")
        else:
            # Clean all claude-wt branches/worktrees
            with console.status("[bold cyan]Cleaning all claude-wt sessions..."):
                # Remove worktrees
                if wt_root.exists():
                    console.print(f"[cyan]Removing worktrees in {wt_root} ...[/cyan]")
                    for wt_dir in wt_root.glob("claude-wt-*"):
                        if wt_dir.is_dir():
                            try:
                                subprocess.run(
                                    ["git", "-C", str(repo_root), "worktree", "remove", "--force", str(wt_dir)],
                                    check=True
                                )
                                console.print(f"  [green]✅ Removed {wt_dir.name}[/green]")
                            except subprocess.CalledProcessError:
                                console.print(f"  [red]❌ Failed to remove {wt_dir.name}[/red]")
                
                # Delete branches
                console.print(f"[cyan]Deleting branches in {repo_root.name} ...[/cyan]")
                try:
                    result = subprocess.run(
                        ["git", "-C", str(repo_root), "branch", "--list", "claude-wt-*"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    branches = [b.strip().lstrip('* ') for b in result.stdout.split('\n') if b.strip()]
                    
                    for branch in branches:
                        if branch:
                            try:
                                subprocess.run(
                                    ["git", "-C", str(repo_root), "branch", "-D", branch],
                                    check=True
                                )
                                console.print(f"  [green]✅ Deleted branch {branch}[/green]")
                            except subprocess.CalledProcessError:
                                console.print(f"  [red]❌ Failed to delete branch {branch}[/red]")
                except subprocess.CalledProcessError:
                    console.print("  [yellow]No claude-wt-* branches found[/yellow]")
            
            console.print("[green bold]🧹 Cleanup complete![/green bold]")
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command(name="list")
def list_sessions():
    """List all claude-wt worktrees."""
    try:
        # Get repo root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_root = Path(result.stdout.strip())
        repo_name = repo_root.name
        wt_root = Path(f"/tmp/claude/worktrees/{repo_name}")
        
        if not wt_root.exists():
            console.print("[yellow]No claude-wt worktrees found.[/yellow]")
            return
        
        # Find all claude-wt worktrees
        worktrees = list(wt_root.glob("claude-wt-*"))
        
        if not worktrees:
            console.print("[yellow]No claude-wt worktrees found.[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Claude-wt worktrees for [bold cyan]{repo_name}[/bold cyan]")
        table.add_column("Status", style="green", justify="center")
        table.add_column("Session", style="cyan", min_width=15)
        table.add_column("Path", style="dim", overflow="fold")
        
        for wt_path in sorted(worktrees):
            branch_name = wt_path.name
            suffix = branch_name.replace("claude-wt-", "")
            
            # Check if branch still exists
            try:
                subprocess.run(
                    ["git", "-C", str(repo_root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
                    check=True
                )
                status = "[green]✅[/green]"
            except subprocess.CalledProcessError:
                status = "[red]❌[/red]"
            
            table.add_row(status, suffix, str(wt_path))
        
        console.print(table)
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    typer.echo("claude-wt 0.1.0")


if __name__ == "__main__":
    app()