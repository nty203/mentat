from __future__ import annotations


def notify(title: str, message: str) -> None:
    try:
        from plyer import notification  # type: ignore[import-untyped]
        notification.notify(title=title, message=message, app_name="mentat", timeout=8)
    except Exception:
        pass
