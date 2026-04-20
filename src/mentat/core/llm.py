from __future__ import annotations

import os
from typing import Any, Optional

# Model names per backend
_MODELS_DIRECT = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5",
}
_MODELS_VERTEX = {
    "haiku": "claude-3-5-haiku@20241022",
    "sonnet": "claude-3-5-sonnet-v2@20241022",
}


def _vertex_config() -> tuple[Optional[str], str]:
    """Returns (project_id, region) from env or config.toml."""
    from mentat.config import load
    cfg = load().get("vertex", {})
    project_id = (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or cfg.get("project_id")
    )
    region = (
        os.environ.get("GOOGLE_CLOUD_REGION")
        or cfg.get("region", "us-east5")
    )
    return project_id, str(region)


def make_client() -> tuple[Any, dict[str, str]]:
    """Return (client, models_dict) using best available auth.

    Priority:
      1. ANTHROPIC_API_KEY  -> anthropic.Anthropic()
      2. Vertex AI config   -> anthropic.AnthropicVertex()
      3. Neither            -> raises RuntimeError
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return anthropic.Anthropic(api_key=api_key), _MODELS_DIRECT

    project_id, region = _vertex_config()
    if project_id:
        client = anthropic.AnthropicVertex(project_id=project_id, region=region)
        return client, _MODELS_VERTEX

    raise RuntimeError(
        "No AI credentials found.\n"
        "  Option A: set ANTHROPIC_API_KEY\n"
        "  Option B: configure Vertex AI (mentat config-init)"
    )


def is_available() -> bool:
    """True if any AI backend is configured."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    project_id, _ = _vertex_config()
    return bool(project_id)


def backend_name() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "Anthropic API"
    project_id, region = _vertex_config()
    if project_id:
        return f"Vertex AI ({project_id} / {region})"
    return "none"
