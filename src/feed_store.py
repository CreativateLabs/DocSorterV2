"""Zentraler Eingangs-Feed: alle Quellen (Email, Messenger, Webhook) in einen Stream.

Jede Quelle schreibt per `add_item()` in den Feed.
Der Archiv-Chat liest per `get_new_items(since_id)` neue Eintraege.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Quellen-Definitionen: icon, farbe, label
SOURCE_META: dict[str, dict] = {
    "email":     {"icon": "email",          "color": "#00d4ff", "label": "E-Mail"},
    "webhook":   {"icon": "cloud_download", "color": "#00e87d", "label": "Webhook"},
    "whatsapp":  {"icon": "whatsapp",       "color": "#25d366", "label": "WhatsApp"},
    "telegram":  {"icon": "send",           "color": "#2aabee", "label": "Telegram"},
    "signal":    {"icon": "lock",           "color": "#3a76f0", "label": "Signal"},
    "messenger": {"icon": "forum",          "color": "#0084ff", "label": "Messenger"},
    "dokument":  {"icon": "description",    "color": "#a855f7", "label": "Dokument"},
    "system":    {"icon": "memory",         "color": "#6b7280", "label": "System"},
}


def _feed_path() -> Path | None:
    """Benutzerspezifischer Feed-Pfad: <user_dir>/_feed.json.

    Leitet den Nutzer-Ordner aus dem Archiv-Pfad ab (archive.parent),
    der nach dem Login per _apply_user_paths() gesetzt wird.
    Fallback: Projekt-Root (wenn kein User eingeloggt).
    """
    try:
        from .config import load_config, DEFAULT_CONFIG_PATH
        cfg = load_config()
        archive = cfg.get("paths", {}).get("archive", "")
        if archive:
            user_dir = Path(archive).expanduser().parent
            user_dir.mkdir(parents=True, exist_ok=True)
            return user_dir / "_feed.json"
        return DEFAULT_CONFIG_PATH.parent / "_feed.json"
    except Exception:
        return None


def _max_entries() -> int:
    try:
        from .config import load_config
        cfg = load_config()
        return int(cfg.get("feed", {}).get("max_entries", 500))
    except Exception:
        return 500


def _load() -> list[dict]:
    p = _feed_path()
    if p and p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save(items: list[dict]) -> None:
    p = _feed_path()
    if not p:
        return
    try:
        limit   = _max_entries()
        content = json.dumps(items[-limit:], ensure_ascii=False, indent=2)
        p.parent.mkdir(parents=True, exist_ok=True)
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
    except Exception as e:
        logger.warning("Feed-Store speichern fehlgeschlagen: %s", e)


def add_item(
    source: str,
    title: str,
    content: str,
    metadata: dict | None = None,
) -> str:
    """Neuen Eintrag in den Feed schreiben. Gibt die ID zurueck."""
    item_id = str(uuid.uuid4())[:12]
    items = _load()
    items.append({
        "id":        item_id,
        "source":    source,
        "title":     title,
        "content":   content,
        "timestamp": datetime.now().isoformat(),
        "metadata":  metadata or {},
        "seen":      False,
    })
    _save(items)
    logger.info("Feed: +%s [%s] %s", item_id, source, title[:60])
    return item_id


def get_items(limit: int = 100) -> list[dict]:
    """Letzte N Eintraege (neueste zuerst)."""
    return list(reversed(_load()[-limit:]))


def get_new_items(seen_ids: set[str]) -> list[dict]:
    """Alle Eintraege die noch nicht in seen_ids sind (neueste zuerst)."""
    all_items = list(reversed(_load()))
    return [i for i in all_items if i["id"] not in seen_ids]


def mark_seen(item_ids: list[str]) -> None:
    """Eintraege als gesehen markieren."""
    items = _load()
    id_set = set(item_ids)
    for item in items:
        if item["id"] in id_set:
            item["seen"] = True
    _save(items)
