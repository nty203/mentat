from __future__ import annotations

import os
import sqlite3

import pytest

from mentat.db.migrate import MigrationRunner


def test_migrations_applied(db_path: str, migrations_dir: str) -> None:
    runner = MigrationRunner(db_path, migrations_dir)
    runner.run()

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT name FROM _migrations ORDER BY name").fetchall()
    conn.close()

    names = [r[0] for r in rows]
    assert "001_initial_schema.sql" in names
    assert "002_skills_schema.sql" in names


def test_migrations_idempotent(db_path: str, migrations_dir: str) -> None:
    runner = MigrationRunner(db_path, migrations_dir)
    runner.run()
    runner.run()  # second run must not raise

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM _migrations").fetchone()[0]
    conn.close()
    assert count == 2


def test_fts5_available(db_path: str, migrations_dir: str) -> None:
    runner = MigrationRunner(db_path, migrations_dir)
    runner.run()

    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO memory_entries (key, value, layer) VALUES ('k', '\"v\"', 'episodic')")
    conn.commit()
    rows = conn.execute("SELECT key FROM memory_fts WHERE memory_fts MATCH 'k'").fetchall()
    conn.close()
    assert len(rows) == 1


def test_wal_mode(db_path: str, migrations_dir: str) -> None:
    runner = MigrationRunner(db_path, migrations_dir)
    runner.run()

    conn = sqlite3.connect(db_path)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode == "wal"
