"""Lokaler Kalender-Eintrags-Store – benutzerdefinierte Termine, Aufgaben & Notizen."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


def _store_path() -> Path:
    try:
        from .config import load_config
        cfg = load_config()
        return Path(cfg["paths"]["archive"]).expanduser().parent / "_calendar.json"
    except Exception:
        return Path.home() / ".docsorter_calendar.json"


def _load() -> dict:
    p = _store_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"entries": []}


def _save(data: dict) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, p)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


_TYPE_COLORS = {
    "termin": "#3B82F6",
    "todo":   "#F59E0B",
    "notiz":  "#8B5CF6",
}

_TYPE_ICONS = {
    "termin": "event",
    "todo":   "task_alt",
    "notiz":  "note",
}


def get_entries() -> list[dict]:
    return _load().get("entries", [])


def add_entry(
    title: str,
    date_str: str,
    time_str: str = "",
    description: str = "",
    entry_type: str = "termin",
) -> str:
    """Neuen Eintrag hinzufügen. Gibt ID zurück."""
    color = _TYPE_COLORS.get(entry_type, "#3B82F6")
    icon  = _TYPE_ICONS.get(entry_type, "event")
    data  = _load()
    entry_id = datetime.now().isoformat()
    data["entries"].append({
        "id":          entry_id,
        "title":       title,
        "date":        date_str,
        "time":        time_str,
        "description": description,
        "type":        entry_type,
        "color":       color,
        "icon":        icon,
        "created":     entry_id,
    })
    _save(data)
    return entry_id


def delete_entry(entry_id: str) -> None:
    data = _load()
    data["entries"] = [e for e in data["entries"] if e["id"] != entry_id]
    _save(data)


def update_entry(entry_id: str, **kwargs) -> None:
    data = _load()
    for e in data["entries"]:
        if e["id"] == entry_id:
            e.update(kwargs)
    _save(data)
