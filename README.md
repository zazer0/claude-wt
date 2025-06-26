# claude-wt

A command-line tool for managing Claude AI sessions in dedicated git worktrees. Automatically creates isolated branches and directories for each Claude conversation, keeping your main branch clean while allowing for easy session management.

## Usage

Run without installing using uvx:

```bash
uvx claude-wt new "implement user authentication"
```

Or install globally:

```bash
uv add claude-wt
```

Or install from source:

```bash
git clone https://github.com/anthropics/claude-wt.git
cd claude-wt
uv install -e .
```

## Commands

### Create New Session

Start a new Claude session in a dedicated worktree:

```bash
uvx claude-wt new "implement user authentication"
```

This creates a new branch, sets up a worktree in `/tmp/claude/worktrees/`, and launches Claude with your query.

You can specify a custom branch suffix:

```bash
uvx claude-wt new "fix bug in parser" --branch parser-fix
```

### Resume Session

Continue an existing Claude session:

```bash
uvx claude-wt resume 20241201-143022
```

Use the branch suffix shown when you created the session.

### List Sessions

View all active Claude worktree sessions:

```bash
uvx claude-wt list
```

### Clean Up

Remove a specific session:

```bash
uvx claude-wt clean 20241201-143022
```

Remove all Claude worktree sessions:

```bash
uvx claude-wt clean --all
```

## How It Works

1. **Branch Creation**: Each session gets a unique branch named `claude-wt-{timestamp}` or `claude-wt-{custom-suffix}`
2. **Worktree Setup**: A git worktree is created in `/tmp/claude/worktrees/{repo-name}/{branch-name}`
3. **Claude Launch**: Claude is launched in the worktree directory with access to your main repository
4. **Session Management**: Resume, list, and clean up sessions as needed

## Benefits

- **Isolation**: Each Claude session works in its own branch and directory
- **Clean History**: Keep experimental changes separate from your main branch
- **Easy Switching**: Resume any previous session instantly
- **Automatic Cleanup**: Remove branches and worktrees when done
- **Repository Safety**: Your main branch stays untouched during Claude sessions

## Requirements

- Python 3.12+
- Git with worktree support
- Claude CLI installed and configured

## Development

This project uses uv for dependency management:

```bash
uv sync
uv run claude-wt --help
```

Or run directly with uvx during development:

```bash
uvx --from . claude-wt --help
```