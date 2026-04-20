from __future__ import annotations

import pytest

from mentat.web.chat import Intent, route


def test_route_approve_english() -> None:
    assert route("approve") == Intent.APPROVE_ALL


def test_route_approve_korean() -> None:
    assert route("승인") == Intent.APPROVE_ALL


def test_route_ok_is_approve() -> None:
    assert route("ok") == Intent.APPROVE_ALL


def test_route_reject_english() -> None:
    assert route("reject") == Intent.REJECT_ALL


def test_route_negate_approve() -> None:
    assert route("승인 안 해") == Intent.UNKNOWN


def test_route_negate_reject() -> None:
    assert route("거절 말고") == Intent.UNKNOWN


def test_route_no_approve() -> None:
    assert route("no approve") == Intent.UNKNOWN


def test_route_scan_korean() -> None:
    assert route("스캔") == Intent.SCAN


def test_route_scan_english() -> None:
    assert route("scan now") == Intent.SCAN


def test_route_list_korean() -> None:
    assert route("목록") == Intent.LIST


def test_route_list_english() -> None:
    assert route("list") == Intent.LIST


def test_route_unknown() -> None:
    assert route("오늘 날씨 어때?") == Intent.UNKNOWN


def test_route_empty() -> None:
    assert route("") == Intent.UNKNOWN
