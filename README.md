# 🌴 Claude-Worktree

Run multiple Claude Code instances in parallel without stepping on each other. This CLI creates isolated git worktrees for each Claude session, so you can work on different features simultaneously while keeping your main branch clean.

*Inspired by a script from [aaazzam](https://github.com/aaazzam).*

## 🚀 Quick Start

Jump right in without installing anything:

```bash
uvx claude-wt new "implement user authentication"
```

**That's it.** You're now working in a clean branch where Claude can't mess up your pristine codebase.

### Installation Options

If you prefer global installation:

```bash
uv tool install claude-wt
```

Or from source:

```bash
git clone https://github.com/anthropics/claude-wt.git
cd claude-wt
uv install -e .
```

## 🎯 Commands

### ✨ Start Fresh: `new`

Spin up a new isolated Claude session:

```bash
uvx claude-wt new "implement user authentication"
```

Behind the scenes: creates a timestamp branch, sets up a worktree in `.claude-wt/worktrees/`, and launches Claude with your query.

Want a memorable branch name? Use `--name`:

```bash
uvx claude-wt new "fix the parser" --name parser-fix
```

Need to branch from a specific source? Use `--branch`:

```bash
uvx claude-wt new "hotfix for prod" --branch main --name hotfix-123
```

### 🔄 Pick Up Where You Left Off: `resume`

Claude sessions are like good TV shows—you want to continue watching:

```bash
uvx claude-wt resume 20241201-143022
```

The session ID is shown when you create it.

### 📋 See What's Running: `list`

See all your active worktrees:

```bash
uvx claude-wt list
```

Shows each session with its health status.

### 🧹 Clean Up: `clean`

Remove a specific session when you're done:

```bash
uvx claude-wt clean 20241201-143022
```

Or clean everything:

```bash
uvx claude-wt clean --all  # The Marie Kondo approach
```

## 🔧 How It Works

Think of it like having multiple parallel universes for your code:

1. **Branch Creation** → Each session gets its own branch (`claude-wt-{timestamp}` or your custom name)
2. **Worktree Setup** → Creates a separate directory in `.claude-wt/worktrees/` so files don't conflict
3. **Claude Launch** → Starts Claude in the isolated environment with full repo access
4. **Session Management** → Resume, list, and clean up sessions effortlessly

## 🎁 Why You'll Love This

- **Fear-Free Experimentation** → Claude can't break your main branch even if it tries
- **Mental Clarity** → No more "did I commit that test code?" anxiety
- **Context Switching** → Jump between different Claude conversations effortlessly
- **Easy Cleanup** → One command to remove all experimental branches
- **Clean History** → Your main branch stays pristine for serious work

## 📋 What You Need

- **Python 3.12+**
- **Git with worktree support** (any recent version)
- **Claude CLI** (installed and authenticated)

## 🛠️ Development

Uses uv for dependency management:

```bash
uv sync
uv run claude-wt --help
```

Or test changes without installing:

```bash
uvx --from . claude-wt --help
```

---

*Built with the assumption that your Claude sessions shouldn't be a game of git-roulette with your main branch.*