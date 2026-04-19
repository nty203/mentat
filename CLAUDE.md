# mentat — Claude Code Project Context

## Quick Start
```bash
uv sync
uv run mentat bootstrap
```

## Architecture
- **src-layout**: package root is `src/mentat/`
- **Entry point**: `mentat.cli.main:app_entry`
- **DB**: SQLite WAL mode, migrations in `migrations/`
- **Introspection API**: FastAPI on port 8765

## Commands
```bash
uv run mypy src/ --strict    # type check
uv run pytest                # run tests
uv run mentat --help         # CLI
```

## Phase 0 Scope
- DiscoveryAgent uses mock LLM (no real API calls)
- ClaudeSessionDataSource returns empty list (stub)
- No TUI (Phase 1)
- DataSource timeout: Phase 1
