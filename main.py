import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer
from typing_extensions import Annotated

app = typer.Typer(help="Claude worktree management CLI")


def launch_claude_wt(
    query: str = "",
    branch: str = "",
):
    """Launch Claude in a dedicated git worktree."""
    try:
        # Get repo root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_root = Path(result.stdout.strip())
        
        # Change to repo root
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
        
        # Print resume and cleanup tips
        print()
        print("🟢 To resume work on this branch:")
        print(f'    cd "{wt_path}" && claude --add-dir "{repo_root}"')
        print()
        print("🧹 To delete this worktree and branch:")
        print(f'    git -C "{repo_root}" worktree remove "{wt_path}" --force && git -C "{repo_root}" branch -D "{branch_name}"')
        print()
        print("🧨 To delete ALL claude-wt branches and worktrees for this repo:")
        print("    claude-wt clean")
        print()
        
        # Launch Claude
        claude_cmd = ["claude", "--add-dir", str(repo_root)]
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
def version():
    """Show version information."""
    typer.echo("claude-wt 0.1.0")


@app.command()
def clean():
    """Delete all claude-wt-* worktrees and branches in the current repo."""
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
        
        # Remove worktrees
        if wt_root.exists():
            print(f"Removing worktrees in {wt_root} ...")
            for wt_dir in wt_root.glob("claude-wt-*"):
                if wt_dir.is_dir():
                    try:
                        subprocess.run(
                            ["git", "-C", str(repo_root), "worktree", "remove", "--force", str(wt_dir)],
                            check=True
                        )
                        print(f"  Removed {wt_dir}")
                    except subprocess.CalledProcessError:
                        print(f"  Failed to remove {wt_dir}")
        
        # Delete branches
        print(f"Deleting branches in {repo_root} ...")
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
                        print(f"  Deleted branch {branch}")
                    except subprocess.CalledProcessError:
                        print(f"  Failed to delete branch {branch}")
        except subprocess.CalledProcessError:
            print("  No claude-wt-* branches found")
        
        print("Cleanup complete!")
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Query to send to Claude")] = "",
    branch: Annotated[str, typer.Option("--branch", help="Branch name suffix")] = "",
):
    """Claude worktree management CLI - launch Claude in dedicated git worktrees."""
    if ctx.invoked_subcommand is None:
        # No subcommand was invoked, so run the main functionality
        launch_claude_wt(query, branch)


if __name__ == "__main__":
    app()
