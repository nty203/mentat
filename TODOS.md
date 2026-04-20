# TODOS

## Phase 2

### Responsive Web UI
**What:** Make `mentat serve` web UI responsive for mobile/tablet viewports.
**Why:** Currently desktop-only (`min-w-[900px]`). Phase 1 ships as local dev tool, but future remote hosting (Phase 3+) needs mobile support.
**Pros:** Broader access, cleaner CSS architecture.
**Cons:** Two-panel layout needs rethink on narrow viewports (likely tabs or accordion).
**Depends on:** Phase 1 layout finalized and stable.
**Effort:** CC ~20 min.

### WebSocket bidirectional chat
**What:** Replace SSE with WebSocket for true bidirectional streaming.
**Why:** SSE is one-way (server → client). For agent-initiated updates ("scan complete"), WebSocket lets server push without polling.
**Depends on:** Phase 1 SSE chat working.

### Background daemon + filesystem watcher
**What:** watchdog-based file system monitor that triggers `DiscoveryAgent` automatically when project files change.
**Why:** Currently user must run `mentat bootstrap` manually. Daemon removes that step.
**Depends on:** Phase 1 approval loop stable.
