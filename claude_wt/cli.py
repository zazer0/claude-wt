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


def check_gitignore(repo_root: Path) -> bool:
    """Check if .claude-wt/worktrees is in .gitignore"""
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        return False
    
    gitignore_content = gitignore_path.read_text()
    # Check for exact match or pattern that would include it
    lines = [line.strip() for line in gitignore_content.split('\n')]
    
    for line in lines:
        if line in ['.claude-wt/worktrees', '.claude-wt/worktrees/', 
                   '.claude-wt/*', '.claude-wt/**']:
            return True
    
    return False


@app.command()
def new(
    query: Annotated[str, typer.Argument(help="Query to send to Claude")] = "",
    branch: Annotated[str, typer.Option("--branch", "-b", help="Source branch to create worktree from")] = "",
    name: Annotated[str, typer.Option("--name", "-n", help="Name suffix for the worktree branch")] = "",
):
    """Create a new worktree and launch Claude."""
    # Get repo root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True
    )
    repo_root = Path(result.stdout.strip())
    
    # Check if .claude-wt/worktrees is in .gitignore
    if not check_gitignore(repo_root):
        panel_content = """Claude-wt creates worktrees in [cyan].claude-wt/worktrees[/cyan] to preserve Claude's repo permissions.

This directory must be added to .gitignore to prevent committing worktree data.

[yellow]→[/yellow] Run: [bold]claude-wt init[/bold]"""
        
        console.print(Panel(panel_content, title="[bold red]⚠️  Setup Required[/bold red]", border_style="red", width=60))
        raise typer.Exit(1)
    
    # Get source branch (default to current branch)
    if branch:
        source_branch = branch
    else:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True
        )
        source_branch = result.stdout.strip()
    
    # Sync with origin
    subprocess.run(["git", "-C", str(repo_root), "fetch", "origin"], check=True)
    subprocess.run(["git", "-C", str(repo_root), "switch", "--quiet", source_branch], check=True)
    subprocess.run(["git", "-C", str(repo_root), "pull", "--ff-only", "--quiet"], check=True)
    
    # Generate worktree branch name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = name or timestamp
    branch_name = f"claude-wt-{suffix}"
    
    # Create branch if needed
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            check=True
        )
    except subprocess.CalledProcessError:
        subprocess.run(
            ["git", "-C", str(repo_root), "branch", branch_name, source_branch],
            check=True
        )
    
    # Setup worktree path
    wt_path = repo_root / ".claude-wt" / "worktrees" / branch_name
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create worktree if needed
    if not wt_path.exists():
        subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "add", "--quiet", str(wt_path), branch_name],
            check=True
        )
    
    # Print helpful info
    panel_content = f"""[dim]Source branch:[/dim] [cyan]{source_branch}[/cyan]

[green]🟢 Resume this session:[/green] [bold]claude-wt resume {suffix}[/bold]
[blue]🧹 Delete this session:[/blue] [bold]claude-wt clean {suffix}[/bold]
[red]🧨 Delete all sessions:[/red] [bold]claude-wt clean --all[/bold]"""
    
    console.print(Panel(panel_content, title="[bold cyan]Session Created[/bold cyan]", border_style="cyan", expand=False))
    
    # Launch Claude
    claude_path = shutil.which("claude") or "/Users/jlowin/.claude/local/claude"
    claude_cmd = [claude_path, "--add-dir", str(repo_root)]
    if query:
        claude_cmd.extend(["--", query])
    
    subprocess.run(claude_cmd, cwd=wt_path)


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
        
        # Find worktree path using git
        full_branch_name = f"claude-wt-{branch_name}"
        result = subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse worktree list to find the matching branch
        wt_path = None
        current_wt = {}
        for line in result.stdout.split('\n'):
            if line.startswith('worktree '):
                if current_wt and current_wt.get('branch') == full_branch_name:
                    wt_path = Path(current_wt['path'])
                    break
                current_wt = {'path': line[9:]}
            elif line.startswith('branch '):
                current_wt['branch'] = line[7:]
        
        # Check the last worktree entry
        if current_wt and current_wt.get('branch') == full_branch_name:
            wt_path = Path(current_wt['path'])
        
        if not wt_path or not wt_path.exists():
            typer.echo(f"Error: Worktree for branch '{branch_name}' not found", err=True)
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
        wt_root = repo_root / ".claude-wt" / "worktrees"
        
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
                # Get all worktrees from git and remove claude-wt ones
                console.print(f"[cyan]Removing claude-wt worktrees...[/cyan]")
                try:
                    result = subprocess.run(
                        ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Parse worktree list to find claude-wt worktrees
                    worktrees = []
                    current_wt = {}
                    for line in result.stdout.split('\n'):
                        if line.startswith('worktree '):
                            if current_wt:
                                worktrees.append(current_wt)
                            current_wt = {'path': line[9:]}
                        elif line.startswith('branch '):
                            current_wt['branch'] = line[7:]
                    if current_wt:
                        worktrees.append(current_wt)
                    
                    # Remove claude-wt worktrees
                    for wt in worktrees:
                        branch_name = wt.get('branch', '')
                        if branch_name.startswith('claude-wt-'):
                            try:
                                subprocess.run(
                                    ["git", "-C", str(repo_root), "worktree", "remove", "--force", wt['path']],
                                    check=True
                                )
                                console.print(f"  [green]✅ Removed {branch_name}[/green]")
                            except subprocess.CalledProcessError:
                                console.print(f"  [red]❌ Failed to remove {branch_name}[/red]")
                except subprocess.CalledProcessError:
                    console.print("  [yellow]No worktrees found[/yellow]")
                
                # Delete branches
                console.print(f"[cyan]Deleting claude-wt branches...[/cyan]")
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
        
        # Get all worktrees from git
        result = subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse worktree list output
        worktrees = []
        current_wt = {}
        for line in result.stdout.split('\n'):
            if line.startswith('worktree '):
                if current_wt:
                    worktrees.append(current_wt)
                current_wt = {'path': line[9:]}  # Remove 'worktree ' prefix
            elif line.startswith('branch '):
                current_wt['branch'] = line[7:]  # Remove 'branch ' prefix
        if current_wt:
            worktrees.append(current_wt)
        
        # Filter for claude-wt worktrees
        claude_worktrees = [
            wt for wt in worktrees 
            if wt.get('branch', '').startswith('claude-wt-')
        ]
        
        if not claude_worktrees:
            console.print("[yellow]No claude-wt worktrees found.[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Claude-wt worktrees for [bold cyan]{repo_name}[/bold cyan]")
        table.add_column("Status", style="green", justify="center")
        table.add_column("Session", style="cyan", min_width=15)
        table.add_column("Path", style="dim", overflow="fold")
        
        for wt in sorted(claude_worktrees, key=lambda x: x.get('branch', '')):
            branch_name = wt.get('branch', '')
            suffix = branch_name.replace("claude-wt-", "")
            wt_path = wt['path']
            
            # Check if worktree path still exists
            status = "[green]✅[/green]" if Path(wt_path).exists() else "[red]❌[/red]"
            
            table.add_row(status, suffix, wt_path)
        
        console.print(table)
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def init():
    """Initialize claude-wt for this repository"""
    try:
        # Get repo root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_root = Path(result.stdout.strip())
        
        # Check if already in gitignore
        if check_gitignore(repo_root):
            console.print("[green]✅ .claude-wt/worktrees is already in .gitignore[/green]")
            return
        
        gitignore_path = repo_root / ".gitignore"
        
        # Read existing content
        if gitignore_path.exists():
            existing_content = gitignore_path.read_text()
            # Add a newline if the file doesn't end with one
            if existing_content and not existing_content.endswith('\n'):
                existing_content += '\n'
        else:
            existing_content = ""
        
        # Add the ignore entry
        new_content = existing_content + "\n# Claude worktree management\n.claude-wt/worktrees\n"
        
        # Write back to file
        gitignore_path.write_text(new_content)
        
        console.print("[green]✅ Added .claude-wt/worktrees to .gitignore[/green]")
        
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