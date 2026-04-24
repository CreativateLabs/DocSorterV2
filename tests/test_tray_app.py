"""Tests fuer src/tray_app.py \u2014 Helper-Funktionen."""

from __future__ import annotations

import socket
from unittest.mock import patch

from src.tray_app import _format_title, _is_dashboard_running


def test_format_title_no_stats():
    assert _format_title({"ok": False, "inbox": 0, "review": 0, "alerts": 0}) == "DS \u2014"


def test_format_title_empty_is_DS():
    assert _format_title({"ok": True, "inbox": 0, "review": 0, "alerts": 0}) == "DS"


def test_format_title_shows_counts():
    title = _format_title({"ok": True, "inbox": 5, "review": 2, "alerts": 1})
    assert "5" in title
    assert "2" in title
    assert "1" in title


def test_is_dashboard_running_false_on_unused_port():
    # Port 65001 sollte frei sein
    assert _is_dashboard_running(65001) is False


def test_is_dashboard_running_true_when_port_bound():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        assert _is_dashboard_running(port) is True
