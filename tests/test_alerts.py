"""Tests fuer src/alerts.py \u2014 Scanner + Severity-Logik."""

from __future__ import annotations

from datetime import date, timedelta

from src.alerts import (
    Alert,
    _parse_date,
    _severity_for_days,
    count_alerts_by_severity,
    get_active_alerts,
)


def test_parse_date_iso():
    assert _parse_date("2026-04-22") == date(2026, 4, 22)


def test_parse_date_german():
    assert _parse_date("22.04.2026") == date(2026, 4, 22)
    assert _parse_date("22.04.26") == date(2026, 4, 22)


def test_parse_date_invalid_returns_none():
    assert _parse_date("") is None
    assert _parse_date("garbage") is None
    assert _parse_date(None) is None  # type: ignore[arg-type]


def test_severity_overdue_is_critical():
    assert _severity_for_days(-5) == "critical"


def test_severity_within_three_days_is_critical():
    assert _severity_for_days(2) == "critical"


def test_severity_within_two_weeks_is_warning():
    assert _severity_for_days(10) == "warning"


def test_severity_far_future_is_info():
    assert _severity_for_days(60) == "info"


def test_get_active_alerts_graceful_without_data(tmp_path, monkeypatch):
    """Ohne Store-Daten darf kein Fehler fliegen, nur leere Liste."""
    store = tmp_path / "empty.json"
    monkeypatch.setattr("src.assistant_store._store_path", lambda: store)
    alerts = get_active_alerts()
    assert isinstance(alerts, list)


def test_count_alerts_by_severity_has_all_keys(tmp_path, monkeypatch):
    store = tmp_path / "empty.json"
    monkeypatch.setattr("src.assistant_store._store_path", lambda: store)
    counts = count_alerts_by_severity()
    assert set(counts.keys()) == {"critical", "warning", "info"}


def test_scan_todos_with_due_date(tmp_path, monkeypatch):
    """Todo mit due=morgen soll einen Alert erzeugen."""
    from src import assistant_store
    store = tmp_path / "assistant.json"
    monkeypatch.setattr("src.assistant_store._store_path", lambda: store)

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assistant_store.add_todo("Miete bezahlen", priority="hoch", due=tomorrow)

    alerts = get_active_alerts()
    todo_alerts = [a for a in alerts if a.type == "todo"]
    assert len(todo_alerts) == 1
    assert todo_alerts[0].due_in_days == 1
    assert "morgen" in todo_alerts[0].title.lower()


def test_scan_todos_overdue_is_critical(tmp_path, monkeypatch):
    from src import assistant_store
    store = tmp_path / "assistant.json"
    monkeypatch.setattr("src.assistant_store._store_path", lambda: store)

    past = (date.today() - timedelta(days=3)).isoformat()
    assistant_store.add_todo("Rechnung zahlen", priority="hoch", due=past)

    alerts = get_active_alerts()
    todo_alerts = [a for a in alerts if a.type == "todo"]
    assert len(todo_alerts) == 1
    assert todo_alerts[0].severity == "critical"
    assert todo_alerts[0].due_in_days < 0


def test_completed_todo_does_not_alert(tmp_path, monkeypatch):
    from src import assistant_store
    store = tmp_path / "assistant.json"
    monkeypatch.setattr("src.assistant_store._store_path", lambda: store)

    today = date.today().isoformat()
    assistant_store.add_todo("Erledigt", priority="normal", due=today)
    # Als erledigt markieren
    todos = assistant_store.get_todos()
    assistant_store.toggle_todo(todos[0]["id"])

    alerts = [a for a in get_active_alerts() if a.type == "todo"]
    assert alerts == []
