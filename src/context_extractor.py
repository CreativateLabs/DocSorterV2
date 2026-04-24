"""Benutzer-Kontext aus allen System-Quellen sammeln.

Wird genutzt um LLM-Analyse und Klassifikation zu verbessern,
indem bekannte Firmen, Betraege, Tags und Namen als Kontext uebergeben werden.

Quellen:
  - config.yaml        → known_customers, document_types
  - _feed.json         → Kunden/Lieferanten aus verarbeiteten Dokumenten
  - assistant_store    → Invoice-Lieferanten, Ausgaben, Abos
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def get_user_context() -> dict:
    """Alle bekannten Entitaeten aus dem System sammeln.

    Primaere Quelle: user_profile.py (gelerntes Profil, priorisiert nach Score).
    Ergaenzende Quellen: config.yaml, _feed.json, assistant_store.

    Returns:
        {
          "companies":  Liste bekannter Firmen/Lieferanten (nach Score sortiert),
          "amounts":    Liste bekannter Betraege als Strings (z.B. "1.200,00 Euro"),
          "tags":       Bekannte Schlagwoerter aus Memos und Dokumenten,
          "names":      Personennamen (Benutzer-Accounts),
          "doc_types":  Bekannte Dokumentarten,
        }
    """
    companies:       set[str] = set()
    amounts:         set[str] = set()
    tags:            set[str] = set()
    names:           set[str] = set()
    doc_types:       set[str] = set()
    global_keywords: set[str] = set()

    # ── 0. Gelerntes Benutzer-Profil (hoehere Prioritaet / Score-basiert) ──
    try:
        from .user_profile import get_top_entities, get_top_amounts, get_top_tags, get_global_keywords
        for ent in get_top_entities(n=50):
            companies.add(ent["name"])
        for amt in get_top_amounts(n=25):
            amounts.add(amt)
        for tag in get_top_tags(n=25):
            tags.add(tag)
        # Benutzerdefinierte Schlagworte aus dem Gehirn (hoehere Prioritaet)
        for kw in get_global_keywords():
            global_keywords.add(kw)
            tags.add(kw)
    except Exception as exc:
        logger.debug("UserProfile-Kontext nicht verfuegbar: %s", exc)

    # ── 1. config.yaml ─────────────────────────────────────────────────────
    try:
        from .config import load_config
        cfg = load_config()
        for c in cfg.get("known_customers", []):
            if isinstance(c, str) and c.strip():
                companies.add(c.strip())
        for dt in cfg.get("document_types", {}).keys():
            doc_types.add(dt)
        # Benutzerdefinierte globale Schlagworte
        for kw in cfg.get("global_keywords", []):
            if kw and kw.strip():
                global_keywords.add(kw.strip())
                tags.add(kw.strip())
    except Exception as exc:
        logger.debug("Config-Kontext nicht verfuegbar: %s", exc)

    # ── 2. _feed.json (verarbeitete Dokumente / E-Mails) ───────────────────
    try:
        from .feed_store import _feed_path as _get_feed_path
        feed_path = _get_feed_path()
        if feed_path and feed_path.exists():
            feed = json.loads(feed_path.read_text(encoding="utf-8"))
            if isinstance(feed, list):
                for item in feed:
                    meta = item.get("metadata", {})
                    # Kundennamen
                    for key in ("customer", "vendor", "sender", "absender", "kunde"):
                        val = meta.get(key, "")
                        if val and val not in ("unbekannt", ""):
                            companies.add(str(val).strip())
                    # Betraege aus content parsen
                    content = item.get("content", "")
                    for m in re.findall(r"[\d]{1,4}(?:[.,]\d{2,3})*\s*(?:€|Euro)", content):
                        amounts.add(m.strip())
                    # Doc-Typen
                    dt = meta.get("doc_type", "")
                    if dt:
                        doc_types.add(dt)
    except Exception as exc:
        logger.debug("Feed-Kontext nicht verfuegbar: %s", exc)

    # ── 3. assistant_store (Rechnungen, Ausgaben, Abos) ────────────────────
    try:
        from .assistant_store import get_invoices, get_expenses, get_subscriptions
        for inv in get_invoices():
            v = inv.get("vendor", "")
            if v and v not in ("unbekannt", ""):
                companies.add(v.strip())
            a = inv.get("amount", 0)
            if a:
                amounts.add(_fmt_amount(a))
        for exp in get_expenses():
            n = exp.get("name", "")
            if n:
                companies.add(n.strip())
            a = exp.get("amount", 0)
            if a:
                amounts.add(_fmt_amount(a))
        for sub in get_subscriptions():
            n = sub.get("name", "")
            if n:
                companies.add(n.strip())
    except Exception as exc:
        logger.debug("AssistantStore-Kontext nicht verfuegbar: %s", exc)

    # ── 4. _state.json (Benutzer-Namen / E-Mails) ─────────────────────────
    try:
        state_path = Path(__file__).resolve().parent.parent / "_state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            for uname in state.get("accounts", {}).keys():
                names.add(uname.capitalize())
    except Exception as exc:
        logger.debug("State-Kontext nicht verfuegbar: %s", exc)

    return {
        "companies":       _clean_list(companies,       max_items=40),
        "amounts":         _clean_list(amounts,         max_items=30),
        "tags":            _clean_list(tags,            max_items=30),
        "names":           _clean_list(names,           max_items=20),
        "doc_types":       _clean_list(doc_types,       max_items=20),
        "global_keywords": _clean_list(global_keywords, max_items=50),
    }


def build_llm_context(context: dict) -> str:
    """Baut einen Kontext-Abschnitt fuer den LLM-Analyse-Prompt."""
    if not any(context.values()):
        return ""

    lines = ["Bekannter Benutzer-Kontext (hilft bei der Analyse):"]
    if context.get("global_keywords"):
        lines.append(f"  Wichtige Schlagworte (benutzerdefiniert): {', '.join(context['global_keywords'][:30])}")
    if context.get("companies"):
        lines.append(f"  Bekannte Firmen/Lieferanten: {', '.join(context['companies'][:20])}")
    if context.get("amounts"):
        lines.append(f"  Bekannte Betraege: {', '.join(context['amounts'][:15])}")
    if context.get("doc_types"):
        lines.append(f"  Dokumentarten: {', '.join(context['doc_types'][:10])}")
    if context.get("tags"):
        lines.append(f"  Haeufige Tags: {', '.join(context['tags'][:15])}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _fmt_amount(amount: float) -> str:
    """Formatiert einen Betrag als deutschen String z.B. '1.200,00 Euro'."""
    try:
        return f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " Euro"
    except Exception:
        return str(amount)


def _clean_list(s: set[str], max_items: int = 30) -> list[str]:
    """Set bereinigen, sortieren und auf max_items begrenzen."""
    return sorted(
        {v.strip() for v in s if v and len(v.strip()) > 1},
        key=str.casefold
    )[:max_items]
