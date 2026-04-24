"""IMAP E-Mail Connector — lokaler E-Mail-Abruf und Regelanwendung.

Nutzt imaplib (Python stdlib) — keine Extra-Abhaengigkeiten.
E-Mails werden lokal in _emails.json gespeichert.
Regeln aus assistant_store werden automatisch angewendet.
"""

from __future__ import annotations

import email
import email.header
import imaplib
import json
import logging
import os
import re
import tempfile
import ssl
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    id: str
    uid: str
    subject: str
    sender: str
    sender_email: str
    date: str
    snippet: str
    body: str
    folder: str
    read: bool = False
    flagged: bool = False
    has_attachments: bool = False
    account: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EmailMessage":
        return cls(**d)


@dataclass
class EmailAccount:
    name: str
    imap_host: str
    imap_port: int = 993
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    enabled: bool = True
    last_sync: str = ""
    folders: list[str] = field(default_factory=lambda: ["INBOX"])
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True


# ---------------------------------------------------------------------------
# Decode helpers
# ---------------------------------------------------------------------------

def _decode_header(raw: str) -> str:
    """E-Mail Header dekodieren (MIME encoded words)."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            except Exception:
                decoded.append(part.decode("utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded).strip()


def _extract_body(msg: email.message.Message) -> tuple[str, bool]:
    """Text-Body und Anhang-Flag extrahieren."""
    body = ""
    has_attachments = False

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                has_attachments = True
                continue
            if content_type == "text/plain" and not body:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")
        except Exception:
            pass

    return body.strip(), has_attachments


def _extract_sender_email(from_str: str) -> str:
    """E-Mail-Adresse aus From-Header extrahieren."""
    match = re.search(r"<([^>]+)>", from_str)
    if match:
        return match.group(1).lower()
    # Nur Adresse ohne Name
    parts = from_str.strip().split()
    for p in parts:
        if "@" in p:
            return p.strip("<>").lower()
    return from_str.lower()


# ---------------------------------------------------------------------------
# IMAP Connection
# ---------------------------------------------------------------------------

def fetch_emails(
    account: EmailAccount,
    max_emails: int = 50,
    folder: str = "INBOX",
) -> list[EmailMessage]:
    """E-Mails von IMAP-Server abrufen."""
    messages = []
    try:
        if account.use_ssl:
            context = ssl.create_default_context()
            imap = imaplib.IMAP4_SSL(account.imap_host, account.imap_port, ssl_context=context)
        else:
            imap = imaplib.IMAP4(account.imap_host, account.imap_port)

        imap.login(account.username, account.password)
        imap.select(folder, readonly=True)

        # Neueste E-Mails abrufen
        _, data = imap.search(None, "ALL")
        if not data or not data[0]:
            imap.logout()
            return []

        uids = data[0].split()
        # Neueste zuerst
        uids = uids[-max_emails:][::-1]

        for uid in uids:
            try:
                _, msg_data = imap.fetch(uid, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue

                raw = msg_data[0][1]
                if isinstance(raw, bytes):
                    msg = email.message_from_bytes(raw)
                else:
                    continue

                subject = _decode_header(msg.get("Subject", ""))
                from_raw = _decode_header(msg.get("From", ""))
                date_raw = msg.get("Date", "")
                body, has_att = _extract_body(msg)

                # Datum parsen
                try:
                    dt = email.utils.parsedate_to_datetime(date_raw)
                    date_str = dt.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    date_str = date_raw[:20] if date_raw else ""

                msg_id = _decode_header(msg.get("Message-ID", str(uid.decode())))
                sender_email = _extract_sender_email(from_raw)

                messages.append(EmailMessage(
                    id=msg_id,
                    uid=uid.decode(),
                    subject=subject or "(kein Betreff)",
                    sender=from_raw,
                    sender_email=sender_email,
                    date=date_str,
                    snippet=body[:200].replace("\n", " ").strip(),
                    body=body[:5000],
                    folder=folder,
                    has_attachments=has_att,
                    account=account.name,
                ))
            except Exception as e:
                logger.warning("E-Mail %s konnte nicht gelesen werden: %s", uid, e)
                continue

        imap.logout()
    except imaplib.IMAP4.error as e:
        logger.error("IMAP Fehler: %s", e)
        raise
    except Exception as e:
        logger.error("Verbindungsfehler: %s", e)
        raise

    return messages


def test_connection(account: EmailAccount) -> tuple[bool, str]:
    """IMAP-Verbindung testen."""
    try:
        if account.use_ssl:
            context = ssl.create_default_context()
            imap = imaplib.IMAP4_SSL(account.imap_host, account.imap_port, ssl_context=context)
        else:
            imap = imaplib.IMAP4(account.imap_host, account.imap_port)
        imap.login(account.username, account.password)
        # Ordner auflisten
        _, folders = imap.list()
        imap.logout()
        folder_names = []
        for f in (folders or []):
            if f and isinstance(f, bytes):
                parts = f.decode().split('"')
                folder_names.append(parts[-1].strip() if parts else "")
        return True, f"Verbindung erfolgreich. Ordner: {', '.join(folder_names[:8])}"
    except imaplib.IMAP4.error as e:
        return False, f"Login fehlgeschlagen: {e}"
    except Exception as e:
        return False, f"Verbindungsfehler: {e}"


# ---------------------------------------------------------------------------
# Regel-Anwendung
# ---------------------------------------------------------------------------

def apply_email_rules(messages: list[EmailMessage], rules: list[dict]) -> list[dict]:
    """E-Mail-Regeln auf Nachrichten anwenden, gibt Match-Liste zurueck."""
    results = []
    active_rules = [r for r in rules if r.get("active", True)]

    for msg in messages:
        matched_rules = []
        for rule in active_rules:
            sender_pat = rule.get("sender_pattern", "").lower()
            subject_pat = rule.get("subject_pattern", "").lower()
            matches = True
            if sender_pat and sender_pat not in msg.sender_email.lower():
                matches = False
            if subject_pat and subject_pat not in msg.subject.lower():
                matches = False
            if matches and (sender_pat or subject_pat):
                matched_rules.append(rule)

        results.append({
            "message": msg.to_dict(),
            "matched_rules": matched_rules,
            "target_folder": matched_rules[0].get("target_folder", "") if matched_rules else "",
        })
    return results


# ---------------------------------------------------------------------------
# Lokaler E-Mail Store
# ---------------------------------------------------------------------------

def _store_path(cfg: dict) -> Path:
    archive = Path(cfg.get("paths", {}).get("archive", "~/Documents/DocSorter/output")).expanduser()
    return archive / "_emails.json"


def load_emails(cfg: dict) -> list[EmailMessage]:
    path = _store_path(cfg)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [EmailMessage.from_dict(d) for d in data.get("messages", [])]
    except Exception:
        return []


def save_emails(cfg: dict, messages: list[EmailMessage]) -> None:
    path = _store_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_sync": datetime.now().isoformat(),
        "messages": [m.to_dict() for m in messages],
    }
    content = json.dumps(data, ensure_ascii=False, indent=2)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# SMTP — E-Mail senden
# ---------------------------------------------------------------------------

def send_email(
    account: EmailAccount,
    to: str,
    subject: str,
    body: str,
    cc: str = "",
) -> tuple[bool, str]:
    """E-Mail via SMTP versenden."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = account.smtp_host or account.imap_host.replace("imap.", "smtp.")
    smtp_port = account.smtp_port or 587

    msg = MIMEMultipart()
    msg["From"] = account.username
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        if smtp_port == 465:
            # SMTPS (implicit SSL)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                server.login(account.username, account.password)
                recipients = [to] + ([cc] if cc else [])
                server.sendmail(account.username, recipients, msg.as_string())
        else:
            # STARTTLS
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                if account.smtp_use_tls:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                server.login(account.username, account.password)
                recipients = [to] + ([cc] if cc else [])
                server.sendmail(account.username, recipients, msg.as_string())
        return True, "E-Mail erfolgreich gesendet."
    except Exception as e:
        logger.error("SMTP Fehler: %s", e)
        return False, f"Sendefehler: {e}"


# ---------------------------------------------------------------------------
# KI-Analyse: Priorisierung & Zusammenfassung
# ---------------------------------------------------------------------------

# Schluesselwoerter fuer Dringlichkeits-Erkennung
_URGENT_KEYWORDS = [
    "dringend", "urgent", "sofort", "asap", "deadline", "frist", "ablauf",
    "mahnung", "erinnerung", "ausstehend", "ueberfaellig", "overdue",
    "action required", "wichtig", "kritisch", "notfall",
]
_MEDIUM_KEYWORDS = [
    "bitte", "anfrage", "angebot", "rechnung", "zahlung", "vertrag",
    "termin", "meeting", "aufgabe", "todo", "erledigen", "bestaetigung",
    "antwort", "rueckmeldung", "feedback", "einladung",
]
_ACTION_TRIGGERS = [
    "bitte", "koennen sie", "koennten sie", "please", "action required",
    "erledige", "erledigen sie", "bestaetigen sie", "antworten sie",
    "schicken sie", "senden sie", "ueberweisen", "zahlen sie", "zahlen",
    "unterschreiben", "unterzeichnen", "ausfuellen", "einreichen",
    "bewerben", "registrieren", "anmelden", "buchen",
]


def prioritize_emails(messages: list[EmailMessage]) -> list[dict]:
    """E-Mails nach Dringlichkeit priorisieren (keyword-basiert).

    Returns list of dicts with message + priority (high/medium/low) + score + reason.
    """
    results = []
    for msg in messages:
        combined = (msg.subject + " " + msg.snippet + " " + msg.body[:500]).lower()
        score = 0
        reasons = []

        for kw in _URGENT_KEYWORDS:
            if kw in combined:
                score += 3
                reasons.append(kw)

        for kw in _MEDIUM_KEYWORDS:
            if kw in combined:
                score += 1
                reasons.append(kw)

        if msg.has_attachments:
            score += 1
            reasons.append("Anhang")

        if not msg.read:
            score += 1

        priority = "high" if score >= 5 else "medium" if score >= 2 else "low"
        results.append({
            "message": msg,
            "priority": priority,
            "score": score,
            "reasons": list(dict.fromkeys(reasons))[:4],  # dedup, max 4
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def extract_action_items(messages: list[EmailMessage]) -> list[dict]:
    """Aktionspunkte aus E-Mails extrahieren (heuristisch).

    Returns list of dicts: subject, sender_email, action_hint, priority, date.
    """
    import re as _re
    action_items = []

    for msg in messages:
        combined = (msg.subject + " " + msg.snippet).lower()
        body_lower = msg.body[:1000].lower()

        # Pruefen ob Action-Trigger vorhanden
        has_trigger = any(t in combined or t in body_lower for t in _ACTION_TRIGGERS)
        has_urgency = any(k in combined for k in _URGENT_KEYWORDS)

        if not (has_trigger or has_urgency):
            continue

        # Kurzen Hinweistext ableiten
        if any(k in combined for k in ["rechnung", "zahlung", "ueberweisen"]):
            action = "Rechnung pruefen / Zahlung veranlassen"
            priority = "high"
        elif any(k in combined for k in ["mahnung", "frist", "ablauf", "overdue"]):
            action = "Dringende Antwort / Frist beachten"
            priority = "high"
        elif any(k in combined for k in ["termin", "meeting", "einladung"]):
            action = "Termin bestaetigen / Kalender eintragen"
            priority = "medium"
        elif any(k in combined for k in ["vertrag", "unterschreiben", "unterzeichnen"]):
            action = "Vertrag pruefen und unterschreiben"
            priority = "medium"
        elif any(k in combined for k in ["angebot", "anfrage"]):
            action = "Angebot / Anfrage beantworten"
            priority = "medium"
        else:
            action = f"Auf E-Mail antworten: {msg.subject[:60]}"
            priority = "low"

        action_items.append({
            "subject": msg.subject,
            "sender_email": msg.sender_email,
            "action": action,
            "priority": priority,
            "date": msg.date,
            "msg_id": msg.id,
        })

    return action_items
