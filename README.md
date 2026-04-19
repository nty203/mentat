# mentat

Autonomous multi-agent PM system for solo developers.

Scans your projects, discovers patterns, evolves skills — you approve, it executes.

## Install

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/nty203/mentat/main/install.sh | bash

# Windows (PowerShell)
winget install astral-sh.uv
git clone https://github.com/nty203/mentat.git ~/.mentat
cd ~/.mentat && uv sync && uv run mentat bootstrap
```

## Usage

```bash
mentat bootstrap      # Initialize DB, scan projects, open approval queue
mentat scan .         # Scan for project signals (dry-run)
mentat serve          # Start introspection API on port 8765
mentat review         # Show approval queue
mentat skill list     # List skills (Phase 3+)
```

## Claude Code Plugin

```
/plugin marketplace add nty203/mentat
```

## Development

```bash
uv sync
uv run mypy src/ --strict
uv run pytest
```

Requires Python 3.12+, [uv](https://github.com/astral-sh/uv).
