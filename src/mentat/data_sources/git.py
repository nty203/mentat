from __future__ import annotations

import datetime

from mentat.core.data_source import DataSourceAdapter, Signal


class GitDataSource(DataSourceAdapter):
    async def scan(self, path: str = "") -> list[Signal]:
        try:
            import git as gitpython
        except ImportError:
            return []

        if not path:
            return []

        try:
            repo = gitpython.Repo(path, search_parent_directories=False)
        except (gitpython.InvalidGitRepositoryError, gitpython.NoSuchPathError):
            return []
        except Exception:
            return []

        signals: list[Signal] = []

        try:
            commits = list(repo.iter_commits(max_count=10))
            if commits:
                latest = commits[0]
                now = datetime.datetime.utcnow()
                committed = datetime.datetime.utcfromtimestamp(latest.committed_date)
                delta = now - committed
                hours = int(delta.total_seconds() // 3600)
                time_str = f"{hours}h ago" if hours < 48 else f"{delta.days}d ago"
                signals.append(
                    Signal(
                        type="recent_commits",
                        source="git",
                        path=path,
                        details=f"{len(commits)} commits (last: {time_str})",
                        metadata={"commit_count": len(commits), "last_sha": latest.hexsha[:7]},
                    )
                )
        except Exception:
            pass

        return signals
