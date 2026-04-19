-- memory_entries: episodic layer storage
CREATE TABLE IF NOT EXISTS memory_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    layer TEXT NOT NULL DEFAULT 'episodic',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(key, layer)
);

-- FTS5 virtual table for episodic search
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    key,
    value,
    content=memory_entries,
    content_rowid=id
);

-- triggers to keep FTS5 in sync
CREATE TRIGGER IF NOT EXISTS memory_entries_ai AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_fts(rowid, key, value) VALUES (new.id, new.key, new.value);
END;

CREATE TRIGGER IF NOT EXISTS memory_entries_ad AFTER DELETE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, key, value) VALUES ('delete', old.id, old.key, old.value);
END;

CREATE TRIGGER IF NOT EXISTS memory_entries_au AFTER UPDATE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, key, value) VALUES ('delete', old.id, old.key, old.value);
    INSERT INTO memory_fts(rowid, key, value) VALUES (new.id, new.key, new.value);
END;

-- user profiles
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    preferences TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- user feedback
CREATE TABLE IF NOT EXISTS user_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    feedback TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- approval requests
CREATE TABLE IF NOT EXISTS approval_requests (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    data TEXT NOT NULL DEFAULT '{}',
    approved INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- projects
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- agent runs
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT
);
