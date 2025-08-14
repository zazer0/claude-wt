# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Running the CLI
```bash
# Using uv (recommended)
uv run claude-wt --help

# After global installation
claude-wt --help

# Testing changes without installing
uvx --from . claude-wt --help
```

### Development Setup
```bash
# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Type Checking and Linting
```bash
# Type checking with pyright
uv run pyright

# Linting (configured in pyproject.toml)
uv run ruff check .

# Format code
uv run ruff format .
```

## Architecture Overview

This is a Python CLI tool built with:
- **cyclopts**: For command-line interface parsing
- **rich**: For terminal output formatting
- **git worktrees**: Core functionality for creating isolated work environments

### Key Components

**`claude_wt/cli.py`**: Main CLI application containing all commands:
- `new`: Creates new worktree and launches Claude
- `resume`: Resumes existing worktree session
- `list`: Shows all active worktrees
- `clean`: Removes worktrees and branches
- `init`: Sets up .gitignore for worktree directory

### How It Works

1. **Branch Management**: Creates branches with pattern `claude-wt-{timestamp}` or `claude-wt-{custom-name}`
2. **Worktree Creation**: Sets up isolated directories in `.claude-wt/worktrees/`
3. **Claude Integration**: Launches Claude CLI with `--add-dir` pointing to the main repo
4. **Session Tracking**: Uses branch names as session identifiers for resume/clean operations

### Important Paths

- Worktrees are created in: `{repo_root}/.claude-wt/worktrees/{branch_name}`
- Claude CLI location is determined by `shutil.which("claude")` with fallback to `/Users/jlowin/.claude/local/claude`

### Git Operations

The tool performs several git operations:
- Fetches from origin before creating worktrees
- Switches to source branch and pulls latest changes
- Creates branches only if they don't exist
- Uses `git worktree` commands for all worktree management
- ALWAYS use `uv` for running stuff. There's a venv present at cwd/.venv/bin/activate.