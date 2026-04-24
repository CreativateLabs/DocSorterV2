"""Proaktive Alerts: Vertragsauslauf, Zahlungsziele, Fristen.

Scannt den Assistant-Store (Todos, Invoices, Subscriptions) und den Feed
nach zeit-sensitiven Ereignissen und gibt eine sortierte Alert-Liste zurueck.

Verwendung:
    from .alerts import get_active_alerts, count_alerts_by_severity
    for a in get_active_alerts():
        print(a.title, a.severity, a.due_in_days)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Konfiguration: Schwellen fuer verschiedene Alert-Typen
# ---------------------------------------------------------------------------

# Wann wird ein Todo zum Alert? (Tage bis Faelligkeit)
_TODO_WARN_DAYS = 7

# Annahme-Zahlungsziel fuer Rechnungen ohne explizites due-Datum
_INVOICE_DEFAULT_PAYMENT_DAYS = 14

# Jahresabos: Reminder X Tage vor Verlaengerung
_SUBSCRIPTION_REMINDER_DAYS = 30

# Vertrags-Kuendigungsfristen: typische Patterns im Text
_TERMINATION_PATTERNS = [
    re.compile(r"k\u00fcndigungsfrist[^\n]{0,60}?(\d{1,3})\s*(tag|woche|monat)", re.IGNORECASE),
    re.compile(r"(\d{1,3})\s*(tag|woche|monat)[^\n]{0,30}?k\u00fcndigung", re.IGNORECASE),
    re.compile(r"vertragslaufzeit[^\n]{0,60}?(\d{1,3})\s*(jahr|monat)", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Alert-Datenklasse
# ---------------------------------------------------------------------------

@dataclass
class Alert:
    """Ein Alert den der User sehen soll."""
    id: str                  # stabile ID (fuer Dismiss etc.)
    type: str                # todo | invoice | subscription | contract
    title: str               # Kurze Ueberschrift
    description: str         # Details
    severity: str            # critical | warning | info
    due_date: str            # YYYY-MM-DD oder leer
    due_in_days: int         # negativ = ueberfaellig, 0 = heute, positiv = in X Tagen
    source_id: str = ""      # ID im Store (falls vorhanden)
    source_path: str = ""    # Datei-Pfad (falls aus Dokument)
    action_hint: str = ""    # Empfehlung was zu tun ist

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> date | None:
    """Datum aus String parsen (ISO, deutsch DD.MM.YYYY oder DD.MM.YY)."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    fmts = ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%dT%H:%M:%S")
    for fmt in fmts:
        try:
            return datetime.strptime(value[: len(fmt) + 6], fmt).date() if "T" in fmt else datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _severity_for_days(days: int, *, overdue_critical: bool = True) -> str:
    """Severity basierend auf Tagen-bis-Faelligkeit."""
    if days < 0:
        return "critical" if overdue_critical else "warning"
    if days <= 3:
        return "critical"
    if days <= 14:
        return "warning"
    return "info"


# ---------------------------------------------------------------------------
# Einzelne Scanner
# ---------------------------------------------------------------------------

def _scan_todos() -> list[Alert]:
    """Todos mit Faelligkeit in den naechsten _TODO_WARN_DAYS Tagen."""
    try:
        from .assistant_store import get_todos
    except Exception:
        return []

    today = date.today()
    horizon = today + timedelta(days=_TODO_WARN_DAYS * 2)
    alerts: list[Alert] = []

    for todo in get_todos():
        if todo.get("done"):
            continue
        due = _parse_date(todo.get("due", ""))
        if due is None:
            continue
        if due > horizon:
            continue
        days = (due - today).days
        if days > _TODO_WARN_DAYS:
            continue
        severity = _severity_for_days(days)
        when = (
            "\u00fcberf\u00e4llig" if days < 0
            else "heute" if days == 0
            else "morgen" if days == 1
            else f"in {days} Tagen"
        )
        alerts.append(Alert(
            id=f"todo:{todo.get('id', '')}",
            type="todo",
            title=f"Aufgabe f\u00e4llig {when}",
            description=todo.get("text", "")[:200],
            severity=severity,
            due_date=due.isoformat(),
            due_in_days=days,
            source_id=todo.get("id", ""),
            action_hint="Als erledigt markieren oder neu terminieren",
        ))
    return alerts


def _scan_invoices() -> list[Alert]:
    """Rechnungen, deren angenommenes Zahlungsziel naht oder ueberschritten."""
    try:
        from .assistant_store import get_invoices
    except Exception:
        return []

    today = date.today()
    alerts: list[Alert] = []

    for inv in get_invoices():
        if inv.get("paid"):
            continue
        inv_date = _parse_date(inv.get("date", ""))
        if inv_date is None:
            continue
        due_date = inv_date + timedelta(days=_INVOICE_DEFAULT_PAYMENT_DAYS)
        days = (due_date - today).days
        # Nur zeigen wenn <=7 Tage bis Faellig oder schon ueberfaellig
        if days > 7:
            continue
        severity = _severity_for_days(days, overdue_critical=True)
        vendor = inv.get("vendor", "Unbekannt")
        amount = inv.get("amount", 0)
        when = "\u00fcberf\u00e4llig" if days < 0 else "heute" if days == 0 else f"in {days} Tagen"
        alerts.append(Alert(
            id=f"invoice:{inv.get('id', '')}",
            type="invoice",
            title=f"Rechnung {vendor}: Zahlung {when}",
            description=f"{amount:.2f} \u20ac vom {inv_date.strftime('%d.%m.%Y')} \u2014 Zahlungsziel {due_date.strftime('%d.%m.%Y')} (Annahme {_INVOICE_DEFAULT_PAYMENT_DAYS} Tage)",
            severity=severity,
            due_date=due_date.isoformat(),
            due_in_days=days,
            source_id=inv.get("id", ""),
            source_path=inv.get("source_file", ""),
            action_hint="Bezahlen oder als bezahlt markieren",
        ))
    return alerts


def _scan_subscriptions() -> list[Alert]:
    """Abos: Erinnerung an Kuendigungsmoeglichkeit / Review."""
    try:
        from .assistant_store import get_subscriptions
    except Exception:
        return []

    today = date.today()
    alerts: list[Alert] = []

    for sub in get_subscriptions():
        if not sub.get("active", True):
            continue
        cycle = (sub.get("cycle", "") or "").lower()
        # Nur jaehrliche Abos alerten (monatliche sind zu haeufig)
        if "jahr" not in cycle and "j\u00e4hrlich" not in cycle and "annual" not in cycle:
            continue
        created = _parse_date(sub.get("created", ""))
        if created is None:
            continue
        # Naechste Verlaengerung = created + 1 Jahr
        try:
            renewal = created.replace(year=created.year + 1)
        except ValueError:
            # 29.02. in Nicht-Schaltjahr
            renewal = created + timedelta(days=365)
        # Wenn schon gepackt wurde, um 1 Jahr verschieben
        while renewal < today:
            try:
                renewal = renewal.replace(year=renewal.year + 1)
            except ValueError:
                renewal = renewal + timedelta(days=365)
        days = (renewal - today).days
        if days > _SUBSCRIPTION_REMINDER_DAYS:
            continue
        severity = "warning" if days <= 14 else "info"
        alerts.append(Alert(
            id=f"sub:{sub.get('id', '')}",
            type="subscription",
            title=f"Abo {sub.get('name', 'Unbekannt')}: Verl\u00e4ngerung in {days} Tagen",
            description=f"{sub.get('amount', 0):.2f} \u20ac \u2014 Verl\u00e4ngerung am {renewal.strftime('%d.%m.%Y')}. Jetzt pr\u00fcfen ob weiter n\u00f6tig.",
            severity=severity,
            due_date=renewal.isoformat(),
            due_in_days=days,
            source_id=sub.get("id", ""),
            action_hint="Abo behalten oder vor Verl\u00e4ngerung k\u00fcndigen",
        ))
    return alerts


def _scan_contracts_in_feed() -> list[Alert]:
    """Feed nach erkannten Vertraegen durchsuchen mit Kuendigungsfrist-Hinweisen."""
    try:
        from .feed_store import _feed_path
    except Exception:
        return []

    import json as _json

    alerts: list[Alert] = []
    fp = _feed_path()
    if not fp or not Path(fp).exists():
        return alerts

    try:
        feed = _json.loads(Path(fp).read_text(encoding="utf-8"))
    except Exception:
        return alerts

    if not isinstance(feed, list):
        return alerts

    today = date.today()
    for item in feed[-200:]:  # nur letzte 200 Items
        meta = item.get("metadata", {}) or {}
        doc_type = (meta.get("doc_type", "") or "").lower()
        if "vertrag" not in doc_type:
            continue
        content = (item.get("content", "") or "")[:1500]
        # Kuendigungsfrist im Text suchen
        frist_match = None
        for pat in _TERMINATION_PATTERNS:
            m = pat.search(content)
            if m:
                frist_match = m
                break
        if not frist_match:
            continue
        # Dokument-Datum
        doc_date_str = meta.get("date", "") or meta.get("document_date", "")
        doc_date = _parse_date(doc_date_str) if doc_date_str else None
        source_path = meta.get("source_file", "") or meta.get("file_path", "")
        title = meta.get("customer", "") or meta.get("vendor", "") or "Vertrag"
        # Wenn Datum bekannt: rechne grob 1 Jahr ab Abschluss, alerte bei <60 Tagen
        if doc_date:
            try:
                yearly = doc_date.replace(year=doc_date.year + 1)
            except ValueError:
                yearly = doc_date + timedelta(days=365)
            days = (yearly - today).days
            if 0 <= days <= 60:
                alerts.append(Alert(
                    id=f"contract:{item.get('id', source_path)}",
                    type="contract",
                    title=f"Vertrag {title}: K\u00fcndigungsfrist n\u00e4hert sich",
                    description=f"Erkannte Frist: {frist_match.group(0)[:80]}. Verlaengerung ca. {yearly.strftime('%d.%m.%Y')}.",
                    severity="warning" if days <= 30 else "info",
                    due_date=yearly.isoformat(),
                    due_in_days=days,
                    source_path=source_path,
                    action_hint="Vertrag pr\u00fcfen und ggf. k\u00fcndigen",
                ))
        else:
            # Kein Datum: nur als Info-Hinweis
            alerts.append(Alert(
                id=f"contract:{item.get('id', source_path)}",
                type="contract",
                title=f"Vertrag {title}: K\u00fcndigungsfrist erkannt",
                description=f"Frist im Dokument: {frist_match.group(0)[:80]}. Kein Datum erkannt \u2014 bitte manuell pr\u00fcfen.",
                severity="info",
                due_date="",
                due_in_days=9999,
                source_path=source_path,
                action_hint="Dokument \u00f6ffnen und Datum pr\u00fcfen",
            ))
    return alerts


# ---------------------------------------------------------------------------
# Hauptzugriff
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def get_active_alerts() -> list[Alert]:
    """Alle aktuellen Alerts, sortiert: Severity > Ueberfaellig zuerst > Datum aufsteigend."""
    alerts: list[Alert] = []
    for scanner in (_scan_todos, _scan_invoices, _scan_subscriptions, _scan_contracts_in_feed):
        try:
            alerts.extend(scanner())
        except Exception as exc:
            logger.debug("Alert-Scanner %s fehlgeschlagen: %s", scanner.__name__, exc)
    # Deduplizieren nach ID
    seen: set[str] = set()
    unique: list[Alert] = []
    for a in alerts:
        if a.id in seen:
            continue
        seen.add(a.id)
        unique.append(a)
    unique.sort(key=lambda a: (_SEVERITY_ORDER.get(a.severity, 9), a.due_in_days))
    return unique


def count_alerts_by_severity() -> dict[str, int]:
    """Zaehlt Alerts pro Severity fuer Badge-Anzeige."""
    counts = {"critical": 0, "warning": 0, "info": 0}
    for a in get_active_alerts():
        counts[a.severity] = counts.get(a.severity, 0) + 1
    return counts
