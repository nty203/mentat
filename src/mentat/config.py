from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

_DEFAULT_CONFIG = Path.home() / ".mentat" / "config.toml"
_DEFAULT_DB = Path.home() / ".local" / "share" / "mentat" / "db.sqlite"


def get_config_path() -> Path:
    return Path(os.environ.get("MENTAT_CONFIG", str(_DEFAULT_CONFIG)))


def load() -> dict[str, Any]:
    path = get_config_path()
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def save(config: dict[str, Any]) -> Path:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for section, values in config.items():
        lines.append(f"\n[{section}]")
        if isinstance(values, dict):
            for k, v in values.items():
                if isinstance(v, list):
                    items = ", ".join(f'"{x}"' for x in v)
                    lines.append(f"{k} = [{items}]")
                elif isinstance(v, str):
                    lines.append(f'{k} = "{v}"')
                elif isinstance(v, bool):
                    lines.append(f"{k} = {'true' if v else 'false'}")
                else:
                    lines.append(f"{k} = {v}")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path


def get_scan_paths() -> list[str]:
    paths = load().get("scan", {}).get("paths", [])
    return [str(Path(os.path.expandvars(os.path.expanduser(p)))) for p in paths]


def get_db_path() -> str:
    db = load().get("agent", {}).get("db_path", str(_DEFAULT_DB))
    return str(Path(os.path.expandvars(os.path.expanduser(str(db)))))


def set_scan_paths(paths: list[str]) -> None:
    cfg = load()
    cfg.setdefault("scan", {})["paths"] = paths
    save(cfg)


def set_api_key(key: str) -> None:
    env_path = Path(".env")
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    new_lines = [ln for ln in lines if not ln.startswith("ANTHROPIC_API_KEY")]
    new_lines.append(f"ANTHROPIC_API_KEY={key}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
