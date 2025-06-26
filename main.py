import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import typer
from typing_extensions import Annotated

app = typer.Typer(help="Claude worktree management CLI", no_args_is_help=True)


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
        print()
        print(f"🟢 Resume this session: claude-wt resume {suffix}")
        print(f"🧹 Delete this session: claude-wt clean {suffix}")
        print("🧨 Delete all sessions: claude-wt clean")
        print()
        
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
        
        print(f"🔄 Resuming session for branch: {branch_name}")
        print()
        
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
def clean(branch_name: Annotated[str, typer.Argument(help="Specific branch to clean (optional)")] = ""):
    """Delete claude-wt worktrees and branches."""
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
                print(f"✅ Removed worktree: {wt_path}")
            
            # Delete branch
            try:
                subprocess.run(
                    ["git", "-C", str(repo_root), "branch", "-D", full_branch_name],
                    check=True
                )
                print(f"✅ Deleted branch: {full_branch_name}")
            except subprocess.CalledProcessError:
                print(f"⚠️  Branch {full_branch_name} not found")
        else:
            # Clean all claude-wt branches/worktrees
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
                            print(f"  ✅ Removed {wt_dir}")
                        except subprocess.CalledProcessError:
                            print(f"  ❌ Failed to remove {wt_dir}")
            
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
                            print(f"  ✅ Deleted branch {branch}")
                        except subprocess.CalledProcessError:
                            print(f"  ❌ Failed to delete branch {branch}")
            except subprocess.CalledProcessError:
                print("  No claude-wt-* branches found")
            
            print("🧹 Cleanup complete!")
        
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
            print("No claude-wt worktrees found.")
            return
        
        # Find all claude-wt worktrees
        worktrees = list(wt_root.glob("claude-wt-*"))
        
        if not worktrees:
            print("No claude-wt worktrees found.")
            return
        
        print(f"Claude-wt worktrees for {repo_name}:")
        print()
        
        for wt_path in sorted(worktrees):
            branch_name = wt_path.name
            suffix = branch_name.replace("claude-wt-", "")
            
            # Check if branch still exists
            try:
                subprocess.run(
                    ["git", "-C", str(repo_root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
                    check=True
                )
                branch_status = "✅"
            except subprocess.CalledProcessError:
                branch_status = "❌"
            
            print(f"  {branch_status} {suffix}")
            print(f"    Path: {wt_path}")
            print(f"    Resume: claude-wt resume {suffix}")
            print(f"    Clean:  claude-wt clean {suffix}")
            print()
        
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