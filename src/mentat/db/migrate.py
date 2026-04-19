from __future__ import annotations

import os
import sqlite3


def _check_fts5() -> None:
    """Raise RuntimeError if SQLite was compiled without FTS5."""
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE _fts5_check USING fts5(x)")
        conn.close()
    except sqlite3.OperationalError:
        raise RuntimeError(
            "SQLite FTS5 extension is not available.\n"
            "Install a Python build with FTS5 support: "
            "https://www.sqlite.org/fts5.html"
        )


class MigrationRunner:
    def __init__(self, db_path: str, migrations_dir: str) -> None:
        self._db_path = db_path
        self._migrations_dir = migrations_dir

    def run(self) -> None:
        _check_fts5()
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        conn = sqlite3.connect(self._db_path)
        try:
            # WAL mode for concurrent reads/writes
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

            conn.execute(
                "CREATE TABLE IF NOT EXISTS _migrations "
                "(name TEXT PRIMARY KEY, applied_at TEXT DEFAULT (datetime('now')))"
            )
            conn.commit()

            migration_files = sorted(
                f for f in os.listdir(self._migrations_dir) if f.endswith(".sql")
            )

            for filename in migration_files:
                row = conn.execute(
                    "SELECT name FROM _migrations WHERE name = ?", (filename,)
                ).fetchone()
                if row:
                    continue

                path = os.path.join(self._migrations_dir, filename)
                with open(path, encoding="utf-8") as f:
                    sql = f.read()

                conn.executescript(sql)
                conn.execute("INSERT INTO _migrations (name) VALUES (?)", (filename,))
                conn.commit()
        finally:
            conn.close()
