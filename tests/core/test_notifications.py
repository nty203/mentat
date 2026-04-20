from __future__ import annotations

from unittest.mock import MagicMock, patch

from mentat.notifications import notify


def test_notify_calls_plyer() -> None:
    mock_notif = MagicMock()
    with patch.dict("sys.modules", {"plyer": MagicMock(notification=mock_notif)}):
        notify("title", "message")
    mock_notif.notify.assert_called_once_with(
        title="title", message="message", app_name="mentat", timeout=8
    )


def test_notify_silent_on_import_error() -> None:
    with patch("builtins.__import__", side_effect=ImportError("no plyer")):
        # must not raise
        notify("title", "message")


def test_notify_silent_on_runtime_error() -> None:
    mock_notif = MagicMock()
    mock_notif.notify.side_effect = RuntimeError("no display")
    with patch.dict("sys.modules", {"plyer": MagicMock(notification=mock_notif)}):
        notify("title", "message")  # must not raise
