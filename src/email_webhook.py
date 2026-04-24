"""E-Mail Inbound Webhook — empfaengt Kunden-E-Mails via HTTP.

Unterstuetzte Provider:
- Mailgun  (multipart/form-data, HMAC-SHA256 Signatur)
- SendGrid (multipart/form-data, Inbound Parse)
- Postmark (JSON)
- Generic  (eigene JSON-Weiterleitung / Zapier / Make.com)

Registriert FastAPI-Routen direkt auf dem NiceGUI-App-Objekt.
Eingehende E-Mails werden in _emails.json gespeichert und Regeln angewandt.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Payload-Parser pro Provider
# ---------------------------------------------------------------------------

def _parse_mailgun(form: dict, files: dict) -> dict | None:
    """Mailgun Inbound Route multipart/form-data -> EmailMessage dict."""
    subject = form.get("subject", "(kein Betreff)")
    sender_raw = form.get("from", "")
    recipient = form.get("recipient", "")
    body = form.get("body-plain", "") or form.get("stripped-text", "")
    date_str = form.get("Date", "") or form.get("date", "")
    msg_id = form.get("Message-Id", "") or form.get("message-id", "")
    timestamp = form.get("timestamp", "")

    import re as _re
    m = _re.search(r"<([^>]+)>", sender_raw)
    sender_email = m.group(1).lower() if m else sender_raw.lower()

    try:
        dt = datetime.fromtimestamp(float(timestamp)) if timestamp else datetime.now()
        date_fmt = dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        date_fmt = date_str[:20] if date_str else datetime.now().strftime("%d.%m.%Y %H:%M")

    return {
        "id": msg_id or f"mg-{int(time.time())}",
        "uid": f"mg-{int(time.time())}",
        "subject": subject,
        "sender": sender_raw,
        "sender_email": sender_email,
        "date": date_fmt,
        "snippet": body[:200].replace("\n", " ").strip(),
        "body": body[:5000],
        "folder": "INBOX",
        "read": False,
        "flagged": False,
        "has_attachments": bool(files),
        "account": "Mailgun Inbound",
    }


def _parse_sendgrid(form: dict, files: dict) -> dict | None:
    """SendGrid Inbound Parse multipart/form-data -> EmailMessage dict."""
    envelope_raw = form.get("envelope", "{}")
    try:
        envelope = json.loads(envelope_raw)
    except Exception:
        envelope = {}

    subject = form.get("subject", "(kein Betreff)")
    sender_raw = form.get("from", "")
    body = form.get("text", "") or form.get("html", "")
    msg_id = form.get("headers", "").split("Message-ID:")[-1].split("\n")[0].strip() if "Message-ID:" in form.get("headers", "") else ""

    import re as _re
    m = _re.search(r"<([^>]+)>", sender_raw)
    sender_email = m.group(1).lower() if m else sender_raw.lower()

    return {
        "id": msg_id or f"sg-{int(time.time())}",
        "uid": f"sg-{int(time.time())}",
        "subject": subject,
        "sender": sender_raw,
        "sender_email": sender_email,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "snippet": body[:200].replace("\n", " ").strip(),
        "body": body[:5000],
        "folder": "INBOX",
        "read": False,
        "flagged": False,
        "has_attachments": bool(files),
        "account": "SendGrid Inbound",
    }


def _parse_postmark(data: dict) -> dict | None:
    """Postmark Inbound JSON -> EmailMessage dict."""
    subject = data.get("Subject", "(kein Betreff)")
    sender_raw = data.get("From", "")
    body = data.get("TextBody", "") or data.get("HtmlBody", "")
    msg_id = data.get("MessageID", f"pm-{int(time.time())}")
    date_str = data.get("Date", "")

    import re as _re
    m = _re.search(r"<([^>]+)>", sender_raw)
    sender_email = m.group(1).lower() if m else sender_raw.lower()

    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        date_fmt = dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        date_fmt = datetime.now().strftime("%d.%m.%Y %H:%M")

    attachments = data.get("Attachments", [])
    return {
        "id": msg_id,
        "uid": f"pm-{int(time.time())}",
        "subject": subject,
        "sender": sender_raw,
        "sender_email": sender_email,
        "date": date_fmt,
        "snippet": body[:200].replace("\n", " ").strip(),
        "body": body[:5000],
        "folder": "INBOX",
        "read": False,
        "flagged": False,
        "has_attachments": bool(attachments),
        "account": "Postmark Inbound",
    }


def _parse_generic(data: dict) -> dict | None:
    """Generisches JSON-Format (Zapier, Make.com, eigene Skripte)."""
    return {
        "id": data.get("id", f"gen-{int(time.time())}"),
        "uid": f"gen-{int(time.time())}",
        "subject": data.get("subject", data.get("Subject", "(kein Betreff)")),
        "sender": data.get("from", data.get("From", "")),
        "sender_email": data.get("sender_email", data.get("from", "")).lower(),
        "date": data.get("date", datetime.now().strftime("%d.%m.%Y %H:%M")),
        "snippet": data.get("snippet", data.get("body", ""))[:200],
        "body": data.get("body", data.get("text", ""))[:5000],
        "folder": "INBOX",
        "read": False,
        "flagged": False,
        "has_attachments": bool(data.get("attachments")),
        "account": "Webhook Inbound",
    }


# ---------------------------------------------------------------------------
# Signatur-Validierung
# ---------------------------------------------------------------------------

def _verify_mailgun_signature(api_key: str, token: str, timestamp: str, signature: str) -> bool:
    """Mailgun HMAC-SHA256 Signatur pruefen."""
    try:
        value = f"{timestamp}{token}".encode()
        expected = hmac.new(api_key.encode(), value, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def _verify_token(secret: str, request_token: str) -> bool:
    """Einfache Token-Validierung fuer Generic/SendGrid/Postmark."""
    if not secret:
        return True  # Kein Secret konfiguriert -> offen (Entwicklung)
    return hmac.compare_digest(secret, request_token)


# ---------------------------------------------------------------------------
# Route-Registrierung
# ---------------------------------------------------------------------------

def register_routes(nicegui_app: Any, cfg_loader) -> None:
    """FastAPI-Routen auf dem NiceGUI-App registrieren.

    nicegui_app: das `app`-Objekt aus `from nicegui import app`
    cfg_loader: callable ohne Argumente, gibt aktuellen cfg-dict zurueck
    """
    from fastapi import Request, Response
    from fastapi.responses import JSONResponse

    @nicegui_app.post("/api/email/inbound")
    async def inbound_email(request: Request) -> Response:
        """Eingehende E-Mail via Webhook empfangen und speichern."""
        try:
            cfg = cfg_loader()
            wh_cfg = cfg.get("email_webhook", {})

            if not wh_cfg.get("enabled", True):
                return JSONResponse({"status": "disabled"}, status_code=200)

            provider = wh_cfg.get("provider", "generic")
            secret = wh_cfg.get("secret", "")
            content_type = request.headers.get("content-type", "")

            msg_dict: dict | None = None

            if "application/json" in content_type:
                data = await request.json()

                # Token-Validierung
                req_token = request.headers.get("X-Webhook-Token", "")
                if secret and not _verify_token(secret, req_token):
                    logger.warning("Webhook: ungültiger Token")
                    return JSONResponse({"error": "unauthorized"}, status_code=401)

                if provider == "postmark":
                    msg_dict = _parse_postmark(data)
                else:
                    msg_dict = _parse_generic(data)

            elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
                form = await request.form()
                form_dict = dict(form)
                files_dict = {k: v for k, v in form_dict.items() if hasattr(v, "filename")}
                text_dict = {k: v for k, v in form_dict.items() if k not in files_dict}

                if provider == "mailgun":
                    # Mailgun Signatur pruefen
                    mg_api_key = wh_cfg.get("mailgun_api_key", "")
                    if mg_api_key:
                        token = text_dict.get("token", "")
                        timestamp = text_dict.get("timestamp", "")
                        signature = text_dict.get("signature", "")
                        if not _verify_mailgun_signature(mg_api_key, token, timestamp, signature):
                            logger.warning("Webhook: ungültige Mailgun-Signatur")
                            return JSONResponse({"error": "unauthorized"}, status_code=401)
                    msg_dict = _parse_mailgun(text_dict, files_dict)

                elif provider == "sendgrid":
                    req_token = request.headers.get("X-Webhook-Token", "")
                    if secret and not _verify_token(secret, req_token):
                        return JSONResponse({"error": "unauthorized"}, status_code=401)
                    msg_dict = _parse_sendgrid(text_dict, files_dict)

                else:
                    req_token = request.headers.get("X-Webhook-Token", "")
                    if secret and not _verify_token(secret, req_token):
                        return JSONResponse({"error": "unauthorized"}, status_code=401)
                    msg_dict = _parse_generic(text_dict)

            else:
                return JSONResponse({"error": "unsupported content-type"}, status_code=415)

            if not msg_dict:
                return JSONResponse({"status": "ignored"}, status_code=200)

            # In _emails.json speichern
            from .email_connector import load_emails, save_emails, EmailMessage
            existing = load_emails(cfg)

            # Duplikat-Check via ID
            existing_ids = {m.id for m in existing}
            if msg_dict["id"] in existing_ids:
                logger.info("Webhook: Duplikat ignoriert %s", msg_dict["id"])
                return JSONResponse({"status": "duplicate"}, status_code=200)

            new_msg = EmailMessage(**msg_dict)
            save_emails(cfg, [new_msg] + existing)
            logger.info("Webhook: E-Mail empfangen von %s: %s", new_msg.sender_email, new_msg.subject)

            # Feed-Store: auch im Archiv-Chat sichtbar machen
            try:
                from .feed_store import add_item
                feed_item = {
                    "title": new_msg.subject or "(kein Betreff)",
                    "content": new_msg.body or new_msg.snippet or "",
                }
                add_item(
                    source="email",
                    title=feed_item["title"],
                    content=feed_item["content"],
                    metadata={
                        "from": new_msg.sender_email,
                        "date": new_msg.date,
                        "has_attachments": new_msg.has_attachments,
                    },
                )
                # Gehirn: ggf. Todo aus E-Mail erzeugen
                try:
                    from .brain import process_email_item
                    process_email_item(feed_item)
                except Exception as _be:
                    logger.debug("Brain E-Mail-Verarbeitung fehlgeschlagen: %s", _be)
            except Exception as _fe:
                logger.debug("Feed-Store Fehler: %s", _fe)

            return JSONResponse({"status": "ok", "id": new_msg.id}, status_code=200)

        except Exception as e:
            logger.exception("Webhook Fehler: %s", e)
            return JSONResponse({"error": str(e)}, status_code=500)

    @nicegui_app.get("/api/email/inbound")
    async def inbound_test(_: Request) -> Response:
        """Liveness-Check fuer Webhook-Konfiguration."""
        return JSONResponse({"status": "ok", "endpoint": "/api/email/inbound"})


# ---------------------------------------------------------------------------
# Hilfsfunktionen fuer Config
# ---------------------------------------------------------------------------

def generate_secret() -> str:
    """Zufaelliges Webhook-Secret generieren."""
    return secrets.token_urlsafe(32)


def get_webhook_url(cfg: dict) -> str:
    """Vollstaendige Webhook-URL aus Config zusammensetzen."""
    public_url = cfg.get("email_webhook", {}).get("public_url", "").rstrip("/")
    if not public_url:
        return "http://localhost:8080/api/email/inbound"
    return f"{public_url}/api/email/inbound"
