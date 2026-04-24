"""Assistent-Gehirn: Zentrale Intelligenz-Schicht.

Verbindet alle Datenquellen (Dokumente, E-Mails, Scheduler, Feed) und
befuellt den Assistenten automatisch mit To-Dos, Ausgaben und Erkenntnissen.

Wird aufgerufen von:
- agent.py  nach jeder Dokument-Klassifikation / Review
- scheduler.py nach jedem Job-Abschluss
- email_connector.py / email_webhook.py bei neuen E-Mails (via process_email_item)
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dokument-Verarbeitung
# ---------------------------------------------------------------------------

def process_classified_document(
    source_path: str,
    doc_type: str,
    customer: str,
    country: str,
    datum: str = "",
    amount: float | None = None,
    confidence: float = 0.0,
) -> list[str]:
    """Ein frisch klassifiziertes / archiviertes Dokument verarbeiten.

    Erzeugt automatisch:
    - Feed-Eintraege (sichtbar in Archiv-Chat + Assistent-Feed)
    - To-Dos je nach Dokumentenart
    - Rechnungs-Eintraege (fuer Rechnungen mit ausreichender Konfidenz)

    Gibt eine Liste der ausgefuehrten Aktionen zurueck (fuer Logging).
    """
    from . import assistant_store
    from .feed_store import add_item

    actions: list[str] = []
    filename = Path(source_path).name
    doc_lower = doc_type.lower()

    # ---- Rechnung → Invoice + Todo ----
    if doc_lower == "rechnung":
        if confidence >= 0.4 or customer != "unbekannt":
            try:
                inv_id = assistant_store.add_invoice(
                    vendor=customer if customer not in ("unbekannt", "") else filename,
                    amount=amount or 0.0,
                    invoice_date=datum or str(date.today()),
                    category="Rechnung",
                    source_file=source_path,
                )
                actions.append(f"invoice:{inv_id}")
                logger.info("Brain: Rechnung erfasst %s (Vendor: %s)", filename, customer)
            except Exception as e:
                logger.warning("Brain: Invoice-Erstellung fehlgeschlagen: %s", e)

        # To-Do nur wenn Betrag unbekannt oder niedrige Konfidenz
        if amount is None or amount == 0.0 or confidence < 0.6:
            try:
                vendor_label = customer if customer not in ("unbekannt", "") else filename
                assistant_store.add_todo(
                    text=f"Rechnung prüfen: {vendor_label}",
                    priority="normal",
                )
                actions.append("todo:rechnung_pruefen")
            except Exception as e:
                logger.warning("Brain: Todo-Erstellung fehlgeschlagen: %s", e)

        add_item(
            source="dokument",
            title=f"Rechnung archiviert: {filename}",
            content=(
                f"Kunde: {customer} | Datum: {datum or '?'}"
                + (f" | {amount:.2f} €" if amount is not None else "")
            ),
            metadata={"doc_type": doc_type, "source_file": source_path,
                       "confidence": confidence, "customer": customer},
        )
        actions.append("feed:rechnung")

    # ---- Mahnung → dringend Todo ----
    elif doc_lower == "mahnung":
        try:
            assistant_store.add_todo(
                text=f"⚠️ Mahnung dringend prüfen: {filename}",
                priority="hoch",
                due=str(date.today()),
            )
            actions.append("todo:mahnung_dringend")
        except Exception as e:
            logger.warning("Brain: Mahnung-Todo fehlgeschlagen: %s", e)

        add_item(
            source="dokument",
            title=f"⚠️ Mahnung erkannt: {filename}",
            content=f"Absender: {customer} — sofort handeln!",
            metadata={"doc_type": doc_type, "source_file": source_path, "priority": "hoch"},
        )
        actions.append("feed:mahnung")

    # ---- Vertrag → Todo prüfen ----
    elif doc_lower == "vertrag":
        try:
            assistant_store.add_todo(
                text=f"Vertrag prüfen & ablegen: {filename}",
                priority="hoch",
            )
            actions.append("todo:vertrag_pruefen")
        except Exception as e:
            logger.warning("Brain: Vertrag-Todo fehlgeschlagen: %s", e)

        add_item(
            source="dokument",
            title=f"Vertrag archiviert: {filename}",
            content=f"Kunde: {customer} | Land: {country}",
            metadata={"doc_type": doc_type, "source_file": source_path, "confidence": confidence},
        )
        actions.append("feed:vertrag")

    # ---- Angebot → Todo ----
    elif doc_lower == "angebot":
        try:
            assistant_store.add_todo(
                text=f"Angebot prüfen: {filename}",
                priority="normal",
            )
            actions.append("todo:angebot_pruefen")
        except Exception as e:
            logger.warning("Brain: Angebot-Todo fehlgeschlagen: %s", e)

        add_item(
            source="dokument",
            title=f"Angebot erhalten: {filename}",
            content=f"Von: {customer} | Land: {country}",
            metadata={"doc_type": doc_type, "source_file": source_path},
        )
        actions.append("feed:angebot")

    # ---- Sonstige bekannte Typen → Feed-Eintrag ----
    elif doc_lower not in ("unbekannt", ""):
        add_item(
            source="dokument",
            title=f"{doc_type.capitalize()} archiviert: {filename}",
            content=f"Kunde: {customer} | Datum: {datum or '?'}",
            metadata={"doc_type": doc_type, "source_file": source_path, "confidence": confidence},
        )
        actions.append(f"feed:{doc_lower}")

    # Benutzer-Profil aktualisieren + Schlagwort-Treffer registrieren
    try:
        from .user_profile import learn_from_document, get_global_keywords_lower, record_keyword_hit
        learn_from_document(
            customer=customer,
            doc_type=doc_type,
            amount=amount,
            vendor=customer,
        )
        # Prüfen ob Schlagworte im Dokument-Kontext vorkommen
        _doc_text = " ".join(filter(None, [source_path, doc_type, customer, country])).lower()
        for _kw in get_global_keywords_lower():
            if _kw in _doc_text:
                record_keyword_hit(_kw)
    except Exception as exc:
        logger.debug("UserProfile-Update (Dokument) fehlgeschlagen: %s", exc)

    return actions


# ---------------------------------------------------------------------------
# E-Mail-Verarbeitung
# ---------------------------------------------------------------------------

_ACTION_KEYWORDS_HIGH = frozenset([
    "dringend", "urgent", "sofort", "frist abgelaufen", "overdue",
    "mahnung", "forderung", "letzte erinnerung", "final notice",
])
_ACTION_KEYWORDS_NORMAL = frozenset([
    "bitte", "anfrage", "antworten", "reply", "action required",
    "deadline", "frist", "bis zum", "bitte bestätigen", "rückmeldung",
    "please respond", "follow up", "followup",
])


def process_email_item(email_item: dict) -> list[str]:
    """Ein neues E-Mail-Feed-Item verarbeiten.

    Erzeugt bei Bedarf automatisch ein Todo im Assistenten.
    """
    from . import assistant_store

    actions: list[str] = []
    subject = email_item.get("title", "")
    content = email_item.get("content", "")
    lower = (subject + " " + content).lower()

    # Benutzerdefinierte Schlagworte aus dem Gehirn laden
    try:
        from .user_profile import get_global_keywords_lower, record_keyword_hit
        _user_kws = get_global_keywords_lower()
    except Exception:
        _user_kws = frozenset()

    priority = None
    if any(kw in lower for kw in _ACTION_KEYWORDS_HIGH):
        priority = "hoch"
    elif any(kw in lower for kw in _ACTION_KEYWORDS_NORMAL | _user_kws):
        priority = "normal"

    # Schlagwort-Treffer im Gehirn registrieren (lernt mit)
    try:
        for _kw in _user_kws:
            if _kw in lower:
                record_keyword_hit(_kw)
    except Exception:
        pass

    if priority:
        try:
            snippet = subject[:80] if subject else content[:60]
            assistant_store.add_todo(
                text=f"E-Mail beantworten: {snippet}",
                priority=priority,
            )
            actions.append(f"todo:email_{priority}")
            logger.info("Brain: E-Mail-Todo erstellt (%s): %s", priority, snippet[:40])
        except Exception as e:
            logger.warning("Brain: E-Mail-Todo fehlgeschlagen: %s", e)

    # Benutzer-Profil aktualisieren
    try:
        from .user_profile import learn_from_email
        learn_from_email(
            subject=email_item.get("title", ""),
            sender=email_item.get("metadata", {}).get("sender", ""),
            content=email_item.get("content", ""),
        )
    except Exception as exc:
        logger.debug("UserProfile-Update (E-Mail) fehlgeschlagen: %s", exc)

    return actions


# ---------------------------------------------------------------------------
# Scheduler-Ergebnis-Verarbeitung
# ---------------------------------------------------------------------------

def process_scheduler_result(job_id: str, result: dict) -> list[str]:
    """Ein Scheduler-Ergebnis verarbeiten und ggf. Todos / Feed-Items erzeugen."""
    from . import assistant_store
    from .feed_store import add_item

    actions: list[str] = []
    status = result.get("status", "")
    message = result.get("message", "")

    # ---- Fehler immer melden ----
    if status == "error":
        try:
            add_item(
                source="system",
                title=f"Job-Fehler: {job_id}",
                content=message,
                metadata={"job_id": job_id, "status": status},
            )
            actions.append("feed:error")
        except Exception:
            pass
        return actions

    # ---- Abonnement-Check → Todo ----
    if job_id == "check_subscriptions" and "benoetigen" in message.lower():
        try:
            assistant_store.add_todo(
                text=f"Abonnements überprüfen ({message})",
                priority="normal",
            )
            actions.append("todo:abonnements")
        except Exception as e:
            logger.warning("Brain: Abo-Todo fehlgeschlagen: %s", e)
        try:
            add_item(
                source="system",
                title="Abonnement-Review fällig",
                content=message,
                metadata={"job_id": job_id},
            )
            actions.append("feed:abo")
        except Exception:
            pass

    # ---- Neue E-Mails ----
    elif job_id == "fetch_emails" and status == "success" and message:
        parts = message.split(" ")
        if parts and parts[0].isdigit() and int(parts[0]) > 0:
            try:
                add_item(
                    source="email",
                    title="Neue E-Mails abgerufen",
                    content=message,
                    metadata={"job_id": job_id},
                )
                actions.append("feed:emails")
            except Exception:
                pass

    # ---- Inbox-Scan ----
    elif job_id == "scan_inbox" and status == "success" and message:
        try:
            add_item(
                source="system",
                title="Inbox gescannt",
                content=message,
                metadata={"job_id": job_id},
            )
            actions.append("feed:scan")
        except Exception:
            pass

    return actions


# ---------------------------------------------------------------------------
# Taeglich-Briefing-Berechnung
# ---------------------------------------------------------------------------

def _invoice_is_this_month(date_str: str) -> bool:
    """Prueft ob ein Rechnungsdatum im aktuellen Monat liegt.

    Unterstuetzt beide Formate:
    - DD.MM.YYYY  (von classifier.py, z.B. "15.03.2026")
    - YYYY-MM-DD  (ISO-Fallback, z.B. "2026-03-15")
    """
    if not date_str:
        return False
    today = date.today()
    try:
        # DD.MM.YYYY — erkennbar am Punkt an Position 2 und 5
        if len(date_str) >= 10 and date_str[2:3] == "." and date_str[5:6] == ".":
            day, month, year = date_str[:2], date_str[3:5], date_str[6:10]
            return int(year) == today.year and int(month) == today.month
        # YYYY-MM-DD (ISO) — erkennbar am Bindestrich an Position 4 und 7
        if len(date_str) >= 10 and date_str[4:5] == "-":
            return date_str[:7] == str(today)[:7]
    except (ValueError, IndexError):
        pass
    return False


def get_briefing() -> dict[str, Any]:
    """Aktuelle Kennzahlen fuer den Assistenten-Morgen-Briefing berechnen.

    Schnell und sicher — wirft nie eine Exception nach aussen.
    """
    try:
        from . import assistant_store
        from .feed_store import get_items

        todos = assistant_store.get_todos()
        open_todos = [t for t in todos if not t.get("done")]
        high_prio = [t for t in open_todos if t.get("priority") == "hoch"]
        overdue = [
            t for t in open_todos
            if t.get("due") and t["due"] < str(date.today())
        ]

        subscriptions = assistant_store.get_subscriptions()
        active_subs = [s for s in subscriptions if s.get("active", True)]
        subs_due = [
            s for s in active_subs
            if _sub_needs_review(s)
        ]

        expenses = assistant_store.get_expenses()
        monthly_total = sum(
            e.get("amount", 0.0)
            for e in expenses
            if e.get("active", True)
            and e.get("cycle", "").lower() in ("monatlich", "monthly")
        )

        invoices = assistant_store.get_invoices()
        invoices_this_month = [
            inv for inv in invoices
            if _invoice_is_this_month(inv.get("date", ""))
        ]

        recent_feed = get_items(limit=20)
        unread_feed = [i for i in recent_feed if not i.get("seen", False)]

        return {
            "open_todos": len(open_todos),
            "high_prio_todos": len(high_prio),
            "overdue_todos": len(overdue),
            "active_subscriptions": len(active_subs),
            "subscriptions_due_review": len(subs_due),
            "monthly_expenses": round(monthly_total, 2),
            "invoices_this_month": len(invoices_this_month),
            "unread_feed": len(unread_feed),
            "recent_feed": recent_feed[:10],
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.warning("Brain: get_briefing fehlgeschlagen: %s", e)
        return {
            "open_todos": 0,
            "high_prio_todos": 0,
            "overdue_todos": 0,
            "active_subscriptions": 0,
            "subscriptions_due_review": 0,
            "monthly_expenses": 0.0,
            "invoices_this_month": 0,
            "unread_feed": 0,
            "recent_feed": [],
            "generated_at": datetime.now().isoformat(),
        }




def _sub_needs_review(sub: dict) -> bool:
    from datetime import timedelta
    last = sub.get("last_review")
    if last is None:
        return True
    try:
        return date.fromisoformat(last) < date.today() - timedelta(days=30)
    except (ValueError, TypeError):
        return True
