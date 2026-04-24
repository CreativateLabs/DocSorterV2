"""Messenger Inbound Webhook — empfaengt Nachrichten von WhatsApp, Telegram, Generic.

Registriert FastAPI-Routen auf dem NiceGUI-App-Objekt.
Eingehende Nachrichten werden in _messages.json gespeichert.
"""

from __future__ import annotations

import hmac
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Payload-Parser pro Plattform
# ---------------------------------------------------------------------------


def _parse_whatsapp(data: dict) -> dict | None:
    """WhatsApp Business Cloud API format -> message dict."""
    try:
        entry = data.get("entry", [])
        if not entry:
            return None
        changes = entry[0].get("changes", [])
        if not changes:
            return None
        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None
        msg = messages[0]

        msg_id = msg.get("id", f"wa-{int(time.time())}")
        text = msg.get("text", {}).get("body", "")
        if not text:
            # Try other message types (image caption, etc.)
            for key in ("image", "document", "audio", "video"):
                if key in msg:
                    text = msg[key].get("caption", f"[{key}]") or f"[{key}]"
                    break
        if not text:
            return None

        from_id = msg.get("from", "unknown")
        # Try to get contact name from contacts list
        contacts = value.get("contacts", [])
        from_name = from_id
        if contacts:
            profile = contacts[0].get("profile", {})
            from_name = profile.get("name", from_id)

        ts = msg.get("timestamp", "")
        try:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            timestamp = dt.isoformat()
        except Exception:
            timestamp = datetime.now(tz=timezone.utc).isoformat()

        return {
            "id": msg_id,
            "platform": "whatsapp",
            "from_id": str(from_id),
            "from_name": from_name,
            "text": text[:4000],
            "timestamp": timestamp,
            "read": False,
        }
    except Exception as e:
        logger.warning("WhatsApp parse error: %s", e)
        return None


def _parse_telegram(data: dict) -> dict | None:
    """Telegram Bot API update format -> message dict."""
    try:
        message = data.get("message")
        if not message:
            # Try channel_post or edited_message
            message = data.get("channel_post") or data.get("edited_message")
        if not message:
            return None

        text = message.get("text", "") or message.get("caption", "")
        if not text:
            return None

        msg_id = str(data.get("update_id", f"tg-{int(time.time())}"))
        from_info = message.get("from", {})
        from_id = str(from_info.get("id", "unknown"))
        first_name = from_info.get("first_name", "")
        last_name = from_info.get("last_name", "")
        username = from_info.get("username", "")
        if first_name or last_name:
            from_name = f"{first_name} {last_name}".strip()
        elif username:
            from_name = f"@{username}"
        else:
            from_name = from_id

        ts = message.get("date", 0)
        try:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            timestamp = dt.isoformat()
        except Exception:
            timestamp = datetime.now(tz=timezone.utc).isoformat()

        return {
            "id": msg_id,
            "platform": "telegram",
            "from_id": from_id,
            "from_name": from_name,
            "text": text[:4000],
            "timestamp": timestamp,
            "read": False,
        }
    except Exception as e:
        logger.warning("Telegram parse error: %s", e)
        return None


def _parse_generic(data: dict) -> dict | None:
    """Simple JSON: {from, text, platform, timestamp} -> message dict."""
    try:
        text = data.get("text", data.get("message", data.get("body", "")))
        if not text:
            return None

        from_id = str(data.get("from", data.get("from_id", data.get("sender", "unknown"))))
        from_name = str(data.get("from_name", data.get("name", from_id)))
        platform = str(data.get("platform", "generic"))
        ts_raw = data.get("timestamp", data.get("date", ""))
        if ts_raw:
            try:
                timestamp = str(ts_raw)
            except Exception:
                timestamp = datetime.now(tz=timezone.utc).isoformat()
        else:
            timestamp = datetime.now(tz=timezone.utc).isoformat()

        msg_id = str(data.get("id", f"gen-{int(time.time())}"))

        return {
            "id": msg_id,
            "platform": platform,
            "from_id": from_id,
            "from_name": from_name,
            "text": str(text)[:4000],
            "timestamp": timestamp,
            "read": False,
        }
    except Exception as e:
        logger.warning("Generic parse error: %s", e)
        return None


# ---------------------------------------------------------------------------
# Persistenz
# ---------------------------------------------------------------------------


def _messages_path(cfg: dict) -> Path:
    """Pfad zur _messages.json im Archiv-Verzeichnis."""
    archive = cfg.get("paths", {}).get("archive", "~/Documents/DocSorter/output")
    p = Path(archive).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p / "_messages.json"


def load_messages(cfg: dict) -> list[dict]:
    """Nachrichten aus {archive}/_messages.json laden."""
    path = _messages_path(cfg)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        logger.warning("Fehler beim Laden der Nachrichten: %s", e)
        return []


def save_messages(cfg: dict, messages: list[dict]) -> None:
    """Nachrichten in {archive}/_messages.json speichern."""
    path = _messages_path(cfg)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Fehler beim Speichern der Nachrichten: %s", e)


# ---------------------------------------------------------------------------
# Token-Validierung
# ---------------------------------------------------------------------------


def _verify_token(secret: str, request_token: str) -> bool:
    """Einfache Token-Validierung. Gibt True zurueck wenn kein Secret konfiguriert."""
    if not secret:
        return True
    return hmac.compare_digest(secret, request_token)


# ---------------------------------------------------------------------------
# Route-Registrierung
# ---------------------------------------------------------------------------


def register_routes(nicegui_app: Any, cfg_loader) -> None:
    """FastAPI-Routen fuer Messenger-Webhooks registrieren.

    nicegui_app: das `app`-Objekt aus `from nicegui import app`
    cfg_loader: callable ohne Argumente, gibt aktuellen cfg-dict zurueck
    """
    from fastapi import Request, Response
    from fastapi.responses import JSONResponse, PlainTextResponse

    @nicegui_app.post("/api/messenger/inbound")
    async def inbound_messenger(request: Request) -> Response:
        """Eingehende Messenger-Nachricht via Webhook empfangen und speichern."""
        try:
            cfg = cfg_loader()
            wh_cfg = cfg.get("messenger_webhook", {})

            if not wh_cfg.get("enabled", True):
                return JSONResponse({"status": "disabled"}, status_code=200)

            secret = wh_cfg.get("secret", "")

            # Token-Validierung
            req_token = request.headers.get("X-Webhook-Token", "")
            if not _verify_token(secret, req_token):
                logger.warning("Messenger Webhook: ungültiger Token")
                return JSONResponse({"error": "unauthorized"}, status_code=401)

            content_type = request.headers.get("content-type", "")
            if "application/json" not in content_type:
                return JSONResponse({"error": "only application/json supported"}, status_code=415)

            data = await request.json()

            # Plattform-Erkennung: WhatsApp -> object field, Telegram -> update_id field
            msg_dict: dict | None = None
            if data.get("object") in ("whatsapp_business_account", "page"):
                msg_dict = _parse_whatsapp(data)
            elif "update_id" in data:
                msg_dict = _parse_telegram(data)
            else:
                msg_dict = _parse_generic(data)

            if not msg_dict:
                return JSONResponse({"status": "ignored"}, status_code=200)

            # In _messages.json speichern (Duplikat-Check)
            existing = load_messages(cfg)
            existing_ids = {m.get("id") for m in existing}
            if msg_dict["id"] in existing_ids:
                logger.info("Messenger Webhook: Duplikat ignoriert %s", msg_dict["id"])
                return JSONResponse({"status": "duplicate"}, status_code=200)

            save_messages(cfg, [msg_dict] + existing)
            logger.info(
                "Messenger Webhook: Nachricht empfangen von %s (%s): %.60s",
                msg_dict["from_name"],
                msg_dict["platform"],
                msg_dict["text"],
            )

            # Feed-Store: auch im Archiv-Chat sichtbar machen
            try:
                from .feed_store import add_item
                platform = msg_dict.get("platform", "messenger").lower()
                source = platform if platform in ("whatsapp", "telegram", "signal") else "messenger"
                add_item(
                    source=source,
                    title=f"{msg_dict.get('from_name', '?')} ({platform})",
                    content=msg_dict.get("text", ""),
                    metadata={
                        "from": msg_dict.get("from_name"),
                        "platform": platform,
                        "chat_id": msg_dict.get("chat_id"),
                    },
                )
            except Exception as _fe:
                logger.debug("Feed-Store Fehler: %s", _fe)

            return JSONResponse({"status": "ok", "id": msg_dict["id"]}, status_code=200)

        except Exception as e:
            logger.exception("Messenger Webhook Fehler: %s", e)
            return JSONResponse({"error": str(e)}, status_code=500)

    @nicegui_app.get("/api/messenger/inbound")
    async def inbound_messenger_liveness(_: Request) -> Response:
        """Liveness-Check fuer Webhook-Konfiguration."""
        return JSONResponse({"status": "ok", "endpoint": "/api/messenger/inbound"})

    @nicegui_app.get("/api/messenger/verify")
    async def messenger_verify(request: Request) -> Response:
        """WhatsApp Webhook-Verifizierung (GET challenge)."""
        try:
            cfg = cfg_loader()
            wh_cfg = cfg.get("messenger_webhook", {})

            mode = request.query_params.get("hub.mode", "")
            verify_token = request.query_params.get("hub.verify_token", "")
            challenge = request.query_params.get("hub.challenge", "")

            expected_token = wh_cfg.get("whatsapp_verify_token", "")

            if mode == "subscribe" and verify_token == expected_token and expected_token:
                logger.info("WhatsApp Webhook verifiziert")
                return PlainTextResponse(challenge)

            logger.warning(
                "WhatsApp Verify fehlgeschlagen: mode=%s token_match=%s",
                mode,
                verify_token == expected_token,
            )
            return JSONResponse({"error": "verification failed"}, status_code=403)

        except Exception as e:
            logger.exception("Messenger Verify Fehler: %s", e)
            return JSONResponse({"error": str(e)}, status_code=500)
