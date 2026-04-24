"""Messenger-Seite — Nachrichten von WhatsApp, Telegram, Signal anzeigen
und Verbindungen konfigurieren.

Tabs:
  1. Nachrichten  — Posteingang aller empfangenen Nachrichten
  2. Verbindungen — Setup-Guide für WhatsApp / Telegram / Signal
  3. Einstellungen — Webhook-URL, Token, Secret
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from nicegui import ui

logger = logging.getLogger(__name__)

# Plattform-Farben / Icons
_PLATFORM = {
    "whatsapp": {"color": "#25D366", "icon": "chat_bubble", "label": "WhatsApp"},
    "telegram": {"color": "#2AABEE", "icon": "send",        "label": "Telegram"},
    "signal":   {"color": "#3A76F0", "icon": "lock",        "label": "Signal"},
    "generic":  {"color": "#9CA3AF", "icon": "message",     "label": "Generic"},
}

_CARD = (
    "background:rgba(10,22,40,0.85);border:1px solid rgba(0,212,255,0.12);"
    "border-radius:12px;padding:20px;"
)
_BTN = (
    "background:rgba(0,212,255,0.12);color:#00d4ff;"
    "border:1px solid rgba(0,212,255,0.3);border-radius:8px;"
    "padding:6px 16px;font-size:0.82rem;cursor:pointer;"
)
_CODE_BOX = (
    "background:rgba(0,0,0,0.45);border:1px solid rgba(0,212,255,0.15);"
    "border-radius:8px;padding:12px 16px;font-family:monospace;"
    "font-size:0.82rem;color:#00d4ff;word-break:break-all;"
)
_SECTION = "font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#9CA3AF;margin-bottom:6px"


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        local = dt.astimezone()
        now = datetime.now().astimezone()
        if local.date() == now.date():
            return local.strftime("%H:%M")
        return local.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso[:16] if len(iso) >= 16 else iso


def _load_cfg() -> dict:
    try:
        from ...config import load_config
        return load_config()
    except Exception:
        return {}


def _load_messages() -> list[dict]:
    try:
        from ...messenger_webhook import load_messages
        return load_messages(_load_cfg())
    except Exception:
        return []


def _save_messages(msgs: list[dict]) -> None:
    try:
        from ...messenger_webhook import save_messages
        save_messages(_load_cfg(), msgs)
    except Exception as e:
        logger.warning("save_messages error: %s", e)


def _save_cfg_section(key: str, value: dict) -> None:
    try:
        from ...config import load_config_raw, save_config
        raw = load_config_raw()
        raw[key] = {**raw.get(key, {}), **value}
        save_config(raw)
    except Exception as e:
        logger.warning("save_config error: %s", e)


def _get_public_url(cfg: dict) -> str:
    return (
        cfg.get("messenger_webhook", {}).get("public_url", "")
        or cfg.get("email_webhook", {}).get("public_url", "")
        or "http://localhost:8080"
    ).rstrip("/")


# ---------------------------------------------------------------------------
# Tab 1: Nachrichten
# ---------------------------------------------------------------------------

def _build_messages_tab(cfg: dict) -> None:
    messages = _load_messages()
    container = ui.column().classes("w-full gap-3")

    with container:
        if not messages:
            with ui.column().classes("items-center gap-3").style("padding:60px 0"):
                ui.icon("forum").style("font-size:3rem;color:rgba(0,212,255,0.3)")
                ui.label("Noch keine Nachrichten").style("color:var(--ds-text-2);font-size:1rem")
                ui.label(
                    'Verbinde WhatsApp, Telegram oder Signal im Tab "Verbindungen"'
                ).style("color:var(--ds-text-3);font-size:0.85rem;text-align:center")
            return

        unread = sum(1 for m in messages if not m.get("read", False))
        with ui.row().classes("items-center gap-3 mb-2"):
            ui.label(f"{len(messages)} Nachrichten").style("color:var(--ds-text);font-weight:600")
            if unread:
                ui.label(f"{unread} ungelesen").style(
                    "background:rgba(0,212,255,0.15);color:#00d4ff;"
                    "border-radius:20px;padding:2px 10px;font-size:0.78rem"
                )

            ui.space()

            def _mark_all_read():
                for m in messages:
                    m["read"] = True
                _save_messages(messages)
                container.clear()
                with container:
                    _build_messages_tab_inner(messages)

            ui.button("Alle gelesen", on_click=_mark_all_read).style(_BTN)

        _build_messages_tab_inner(messages)


def _build_messages_tab_inner(messages: list[dict]) -> None:
    for msg in messages[:100]:
        platform = msg.get("platform", "generic")
        p = _PLATFORM.get(platform, _PLATFORM["generic"])
        is_read = msg.get("read", False)

        bg = "rgba(10,22,40,0.85)" if is_read else "rgba(0,212,255,0.05)"
        border_color = "rgba(0,212,255,0.08)" if is_read else "rgba(0,212,255,0.25)"

        with ui.row().classes("w-full items-start gap-3").style(
            f"background:{bg};border:1px solid {border_color};"
            f"border-radius:10px;padding:14px 16px;"
        ):
            # Platform icon
            ui.icon(p["icon"]).style(
                f"font-size:1.5rem;color:{p['color']};margin-top:2px;flex-shrink:0"
            )

            with ui.column().classes("gap-1").style("flex:1;min-width:0"):
                with ui.row().classes("items-center gap-2 w-full"):
                    ui.label(msg.get("from_name", "Unbekannt")).style(
                        "color:var(--ds-text);font-weight:600;font-size:0.9rem"
                    )
                    ui.label(p["label"]).style(
                        f"background:{p['color']}22;color:{p['color']};"
                        f"border-radius:20px;padding:1px 8px;font-size:0.72rem;font-weight:600"
                    )
                    ui.space()
                    ui.label(_fmt_time(msg.get("timestamp", ""))).style(
                        "color:var(--ds-text-3);font-size:0.78rem;white-space:nowrap"
                    )

                ui.label(msg.get("text", "")).style(
                    "color:var(--ds-text-2);font-size:0.87rem;line-height:1.5;"
                    "white-space:pre-wrap;word-break:break-word"
                )

                with ui.row().classes("items-center gap-3 mt-1 flex-wrap"):
                    if not is_read:
                        def _mark_read(m=msg):
                            m["read"] = True
                            _save_messages(messages)
                            ui.notify("Gelesen markiert", color="positive")

                        ui.link("Als gelesen markieren", target="#").on(
                            "click", _mark_read
                        ).style("color:#00d4ff;font-size:0.78rem;cursor:pointer")

                    # Telegram Reply-Button
                    if platform == "telegram":
                        reply_row = ui.row().classes("items-center gap-2 w-full mt-1")
                        with reply_row:
                            reply_inp = ui.input(
                                placeholder="Antwort schreiben...",
                            ).style(
                                "background:rgba(0,0,0,0.3);border:1px solid rgba(42,171,238,0.25);"
                                "border-radius:6px;padding:4px 8px;color:var(--ds-text);"
                                "font-size:0.8rem;flex:1"
                            ).props("outlined dense")

                            async def _send_reply(m=msg, inp=reply_inp):
                                text = inp.value.strip()
                                if not text:
                                    return
                                chat_id = m.get("from_id", "")
                                # Bot-Token aus gespeichertem config (messenger_webhook) holen
                                cfg2 = _load_cfg()
                                bot_token = cfg2.get("messenger_webhook", {}).get("telegram_bot_token", "")
                                if not bot_token:
                                    ui.notify("Kein Telegram Bot-Token konfiguriert (Einstellungen → Nachrichten)", color="warning")
                                    return
                                try:
                                    import httpx as _httpx
                                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                    async with _httpx.AsyncClient(timeout=10) as client:
                                        resp = await client.post(url, json={"chat_id": chat_id, "text": text})
                                    if resp.json().get("ok"):
                                        inp.value = ""
                                        ui.notify("Antwort gesendet!", color="positive")
                                    else:
                                        desc = resp.json().get("description", "Unbekannter Fehler")
                                        ui.notify(f"Fehler: {desc}", color="negative")
                                except Exception as exc:
                                    ui.notify(f"Sendefehler: {exc}", color="negative")

                            ui.button(
                                icon="send",
                                on_click=_send_reply,
                            ).style(
                                "background:rgba(42,171,238,0.15);color:#2AABEE;"
                                "border:1px solid rgba(42,171,238,0.3);border-radius:6px;"
                                "padding:4px 8px;cursor:pointer;min-width:0"
                            ).props("flat dense")


# ---------------------------------------------------------------------------
# Tab 2: Verbindungen
# ---------------------------------------------------------------------------

def _setup_card(title: str, icon: str, color: str) -> ui.column:
    """Gibt einen styled Container zurück."""
    with ui.column().classes("w-full gap-4").style(
        f"{_CARD}border-left:3px solid {color};"
    ) as col:
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon).style(f"font-size:1.4rem;color:{color}")
            ui.label(title).style(f"font-size:1rem;font-weight:700;color:{color}")
    return col


def _code_copy(text: str) -> None:
    """Zeigt ein Code-Feld mit Kopier-Button."""
    with ui.row().classes("w-full items-center gap-2"):
        ui.label(text).style(f"{_CODE_BOX}flex:1")
        ui.button(
            icon="content_copy",
            on_click=lambda: ui.run_javascript(
                f"navigator.clipboard.writeText({repr(text)})"
            ),
        ).style(
            "background:transparent;border:none;color:rgba(0,212,255,0.6);"
            "cursor:pointer;padding:4px;min-width:0"
        ).props("flat dense")


def _step_badge(n: int) -> None:
    ui.label(str(n)).style(
        "background:rgba(0,212,255,0.15);color:#00d4ff;"
        "border-radius:50%;width:22px;height:22px;display:flex;"
        "align-items:center;justify-content:center;"
        "font-size:0.75rem;font-weight:700;flex-shrink:0"
    )


def _build_connections_tab(cfg: dict) -> None:
    public_url = _get_public_url(cfg)
    wh_cfg = cfg.get("messenger_webhook", {})

    # ── WhatsApp ─────────────────────────────────────────────────────────
    with ui.column().classes("w-full gap-3").style(_CARD + "border-left:3px solid #25D366"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("chat_bubble").style("font-size:1.4rem;color:#25D366")
            ui.label("WhatsApp Business").style("font-size:1rem;font-weight:700;color:#25D366")
            ui.label("Meta Cloud API").style(
                "background:rgba(37,211,102,0.12);color:#25D366;"
                "border-radius:20px;padding:2px 10px;font-size:0.75rem"
            )

        ui.label(
            "WhatsApp erfordert ein Meta Business-Konto und eine verifizierte App. "
            "Für lokale Tests kannst du ngrok oder Cloudflare Tunnel nutzen."
        ).style("color:var(--ds-text-2);font-size:0.85rem")

        ui.separator().style("border-color:rgba(255,255,255,0.06)")

        with ui.row().classes("items-start gap-3"):
            _step_badge(1)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Webhook-URL eintragen").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                ui.label("Im Meta Developers Portal unter WhatsApp → Konfiguration:").style("color:var(--ds-text-2);font-size:0.82rem")
                _code_copy(f"{public_url}/api/messenger/inbound")

        with ui.row().classes("items-start gap-3"):
            _step_badge(2)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Verify-Token setzen").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                verify_token = wh_cfg.get("whatsapp_verify_token", "")
                ui.label("Diesen Token im Meta Portal als Verify-Token eintragen:").style("color:var(--ds-text-2);font-size:0.82rem")
                if verify_token:
                    _code_copy(verify_token)
                else:
                    ui.label("⚠ Kein Verify-Token gesetzt — bitte unter Einstellungen konfigurieren").style(
                        "color:#ff9f0a;font-size:0.82rem"
                    )

        with ui.row().classes("items-start gap-3"):
            _step_badge(3)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Verifizierungs-Endpoint").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                ui.label("WhatsApp GET-Challenge wird automatisch beantwortet:").style("color:var(--ds-text-2);font-size:0.82rem")
                _code_copy(f"{public_url}/api/messenger/verify")

        with ui.row().classes("items-start gap-3"):
            _step_badge(4)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Für lokale Tests: ngrok").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                _code_copy("ngrok http 8080")
                ui.label("Dann die ngrok-URL als Public URL in den Einstellungen eintragen.").style("color:var(--ds-text-2);font-size:0.82rem")

        with ui.row().classes("items-center gap-2").style("margin-top:4px"):
            ui.link("Meta Developers Dokumentation →", "https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks", new_tab=True).style(
                "color:#25D366;font-size:0.82rem"
            )

    ui.element("div").style("height:8px")

    # ── Telegram ─────────────────────────────────────────────────────────
    with ui.column().classes("w-full gap-3").style(_CARD + "border-left:3px solid #2AABEE"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("send").style("font-size:1.4rem;color:#2AABEE")
            ui.label("Telegram").style("font-size:1rem;font-weight:700;color:#2AABEE")
            ui.label("Bot API").style(
                "background:rgba(42,171,238,0.12);color:#2AABEE;"
                "border-radius:20px;padding:2px 10px;font-size:0.75rem"
            )

        ui.label(
            "Telegram-Bots sind kostenlos. Erstelle einen Bot über @BotFather "
            "und registriere den Webhook mit einem Klick."
        ).style("color:var(--ds-text-2);font-size:0.85rem")

        ui.separator().style("border-color:rgba(255,255,255,0.06)")

        bot_token_ref: list[str] = [""]
        status_ref: list = [None]

        with ui.row().classes("items-start gap-3"):
            _step_badge(1)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Bot erstellen").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                ui.label("Öffne Telegram → suche @BotFather → /newbot → Namen und Username vergeben").style("color:var(--ds-text-2);font-size:0.82rem")

        with ui.row().classes("items-start gap-3"):
            _step_badge(2)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Bot-Token eingeben").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                bot_input = ui.input(
                    placeholder="123456789:AAHfiqksKZ84cAkq0...",
                ).style(
                    "background:rgba(0,0,0,0.3);border:1px solid rgba(0,212,255,0.2);"
                    "border-radius:8px;padding:8px 12px;color:var(--ds-text);"
                    "font-size:0.85rem;width:100%;font-family:monospace"
                ).props("outlined dense")

                def _on_token(e):
                    bot_token_ref[0] = e.value

                bot_input.on("input", _on_token)

        with ui.row().classes("items-start gap-3"):
            _step_badge(3)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Webhook registrieren").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")

                status_label = ui.label("").style("color:#00d4ff;font-size:0.82rem")
                status_ref[0] = status_label

                async def _register_telegram():
                    import httpx
                    token = bot_token_ref[0].strip()
                    if not token:
                        ui.notify("Bitte Bot-Token eingeben", color="warning")
                        return

                    webhook_url = f"{public_url}/api/messenger/inbound"
                    url = f"https://api.telegram.org/bot{token}/setWebhook"
                    try:
                        async with httpx.AsyncClient(timeout=10) as client:
                            resp = await client.post(url, json={"url": webhook_url})
                        data = resp.json()
                        if data.get("ok"):
                            status_ref[0].set_text("✅ Webhook erfolgreich registriert!")
                            ui.notify("Telegram Webhook registriert", color="positive")
                        else:
                            desc = data.get("description", "Unbekannter Fehler")
                            status_ref[0].set_text(f"❌ Fehler: {desc}")
                            ui.notify(f"Telegram Fehler: {desc}", color="negative")
                    except Exception as ex:
                        status_ref[0].set_text(f"❌ Verbindungsfehler: {ex}")
                        ui.notify("Verbindungsfehler", color="negative")

                ui.button("Webhook registrieren", on_click=_register_telegram).style(
                    "background:rgba(42,171,238,0.15);color:#2AABEE;"
                    "border:1px solid rgba(42,171,238,0.3);border-radius:8px;"
                    "padding:8px 20px;font-size:0.85rem;cursor:pointer"
                )

                ui.label("Webhook-URL die registriert wird:").style("color:var(--ds-text-3);font-size:0.8rem;margin-top:4px")
                _code_copy(f"{public_url}/api/messenger/inbound")

        with ui.row().classes("items-center gap-2").style("margin-top:4px"):
            ui.link("Telegram Bot API Docs →", "https://core.telegram.org/bots/api#setwebhook", new_tab=True).style(
                "color:#2AABEE;font-size:0.82rem"
            )

    ui.element("div").style("height:8px")

    # ── Signal ──────────────────────────────────────────────────────────
    with ui.column().classes("w-full gap-3").style(_CARD + "border-left:3px solid #3A76F0"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("lock").style("font-size:1.4rem;color:#3A76F0")
            ui.label("Signal").style("font-size:1rem;font-weight:700;color:#3A76F0")
            ui.label("signal-cli (lokal)").style(
                "background:rgba(58,118,240,0.12);color:#3A76F0;"
                "border-radius:20px;padding:2px 10px;font-size:0.75rem"
            )
            ui.label("Für lokalen Betrieb").style(
                "background:rgba(0,232,125,0.1);color:#00e87d;"
                "border-radius:20px;padding:2px 10px;font-size:0.75rem"
            )

        ui.label(
            "Signal hat keine offizielle API für Drittanbieter. "
            "signal-cli ist ein Open-Source-Tool das lokal läuft und Nachrichten weiterleitet."
        ).style("color:var(--ds-text-2);font-size:0.85rem")

        ui.separator().style("border-color:rgba(255,255,255,0.06)")

        with ui.row().classes("items-start gap-3"):
            _step_badge(1)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("signal-cli installieren").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                _code_copy("brew install signal-cli   # macOS")
                ui.label("oder").style("color:var(--ds-text-3);font-size:0.78rem")
                _code_copy("# Download: https://github.com/AsamK/signal-cli/releases")

        with ui.row().classes("items-start gap-3"):
            _step_badge(2)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Registrieren (neue Nummer) oder Verknüpfen").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                _code_copy("signal-cli -u +4917XXXXXXXX register")
                _code_copy("signal-cli -u +4917XXXXXXXX verify CODE")

        with ui.row().classes("items-start gap-3"):
            _step_badge(3)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Nachrichten an Webhook weiterleiten").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                ui.label("signal-cli kann eingehende Nachrichten per HTTP weiterleiten:").style("color:var(--ds-text-2);font-size:0.82rem")
                _code_copy(
                    f'signal-cli -u +4917XXXXXXXX receive --output=json '
                    f'| curl -s -X POST {public_url}/api/messenger/inbound '
                    f'-H "Content-Type: application/json" -d @-'
                )

        with ui.row().classes("items-start gap-3"):
            _step_badge(4)
            with ui.column().classes("gap-1").style("flex:1"):
                ui.label("Alternative: Daemon-Modus").style("color:var(--ds-text);font-weight:600;font-size:0.88rem")
                _code_copy("signal-cli -u +4917XXXXXXXX daemon --http localhost:7583")
                ui.label("Dann können Nachrichten per REST abgerufen werden.").style("color:var(--ds-text-2);font-size:0.82rem")

        with ui.row().classes("items-center gap-2").style("margin-top:4px"):
            ui.link("signal-cli GitHub →", "https://github.com/AsamK/signal-cli", new_tab=True).style(
                "color:#3A76F0;font-size:0.82rem"
            )


# ---------------------------------------------------------------------------
# Tab 3: Einstellungen
# ---------------------------------------------------------------------------

def _build_settings_tab(cfg: dict) -> None:
    wh_cfg = cfg.get("messenger_webhook", {})

    with ui.column().classes("w-full gap-4").style(_CARD):
        ui.label("Webhook-Konfiguration").style(
            "font-size:1rem;font-weight:700;color:var(--ds-text)"
        )

        # Aktiviert
        with ui.row().classes("items-center gap-3 w-full"):
            ui.label("Webhook aktiv").style("color:var(--ds-text-2);font-size:0.88rem;flex:1")
            enabled_switch = ui.switch(value=wh_cfg.get("enabled", True))

        ui.separator().style("border-color:rgba(255,255,255,0.06)")

        # Public URL
        ui.label("Öffentliche URL").style(_SECTION)
        ui.label(
            "Deine öffentlich erreichbare URL (z.B. https://abc.ngrok.io). "
            "Wird für die Webhook-URLs verwendet."
        ).style("color:var(--ds-text-3);font-size:0.8rem;margin-bottom:4px")
        public_url_input = ui.input(
            value=wh_cfg.get("public_url", ""),
            placeholder="https://deine-domain.de oder https://abc.ngrok.io",
        ).style(
            "background:rgba(0,0,0,0.3);border:1px solid rgba(0,212,255,0.2);"
            "border-radius:8px;padding:8px 12px;color:var(--ds-text);"
            "font-size:0.85rem;width:100%"
        ).props("outlined dense")

        ui.separator().style("border-color:rgba(255,255,255,0.06)")

        # Telegram Bot Token (für Antworten)
        ui.label("Telegram Bot-Token (fuer Antworten)").style(_SECTION)
        ui.label(
            "Wird benoetigt um auf Telegram-Nachrichten zu antworten. "
            "Erhalte ihn von @BotFather."
        ).style("color:var(--ds-text-3);font-size:0.8rem;margin-bottom:4px")
        tg_token_input = ui.input(
            value=wh_cfg.get("telegram_bot_token", ""),
            placeholder="123456789:AAHfiqksKZ84cAkq0...",
        ).style(
            "background:rgba(0,0,0,0.3);border:1px solid rgba(0,212,255,0.2);"
            "border-radius:8px;padding:8px 12px;color:var(--ds-text);"
            "font-size:0.85rem;width:100%;font-family:monospace"
        ).props("outlined dense password")

        ui.separator().style("border-color:rgba(255,255,255,0.06)")

        # WhatsApp Verify Token
        ui.label("WhatsApp Verify Token").style(_SECTION)
        ui.label("Wird bei der WhatsApp-Webhook-Verifizierung geprüft.").style(
            "color:var(--ds-text-3);font-size:0.8rem;margin-bottom:4px"
        )
        verify_input = ui.input(
            value=wh_cfg.get("whatsapp_verify_token", ""),
            placeholder="z.B. mein-geheimer-token-123",
        ).style(
            "background:rgba(0,0,0,0.3);border:1px solid rgba(0,212,255,0.2);"
            "border-radius:8px;padding:8px 12px;color:var(--ds-text);"
            "font-size:0.85rem;width:100%"
        ).props("outlined dense")

        with ui.row().classes("items-center gap-2"):
            def _gen_token():
                import secrets
                verify_input.value = secrets.token_urlsafe(24)
                ui.notify("Token generiert", color="positive")
            ui.button("Token generieren", on_click=_gen_token).style(_BTN)

        ui.separator().style("border-color:rgba(255,255,255,0.06)")

        # Webhook Secret
        ui.label("Webhook-Secret (X-Webhook-Token)").style(_SECTION)
        ui.label(
            "Optional: Alle Webhook-Anfragen müssen diesen Wert als 'X-Webhook-Token'-Header mitschicken."
        ).style("color:var(--ds-text-3);font-size:0.8rem;margin-bottom:4px")
        secret_input = ui.input(
            value=wh_cfg.get("secret", ""),
            placeholder="Leer lassen = kein Token erforderlich",
        ).style(
            "background:rgba(0,0,0,0.3);border:1px solid rgba(0,212,255,0.2);"
            "border-radius:8px;padding:8px 12px;color:var(--ds-text);"
            "font-size:0.85rem;width:100%"
        ).props("outlined dense password")

        ui.separator().style("border-color:rgba(255,255,255,0.06)")

        # Aktive Webhook-URLs (readonly)
        ui.label("Aktive Endpoints").style(_SECTION)
        current_url = public_url_input.value or "http://localhost:8080"
        with ui.column().classes("gap-2"):
            for label, path in [
                ("POST — Empfang (WhatsApp/Telegram/Generic):", "/api/messenger/inbound"),
                ("GET  — WhatsApp Verify:", "/api/messenger/verify"),
                ("GET  — Liveness-Check:", "/api/messenger/inbound"),
            ]:
                ui.label(label).style("color:var(--ds-text-3);font-size:0.78rem")
                _code_copy(f"{current_url}{path}")

        ui.separator().style("border-color:rgba(255,255,255,0.06)")

        # Speichern
        def _save():
            _save_cfg_section("messenger_webhook", {
                "enabled": enabled_switch.value,
                "public_url": public_url_input.value.strip(),
                "telegram_bot_token": tg_token_input.value.strip(),
                "whatsapp_verify_token": verify_input.value.strip(),
                "secret": secret_input.value.strip(),
            })
            ui.notify("Einstellungen gespeichert", color="positive")

        ui.button("Speichern", on_click=_save).style(
            "background:rgba(0,212,255,0.15);color:#00d4ff;"
            "border:1px solid rgba(0,212,255,0.4);border-radius:8px;"
            "padding:10px 28px;font-weight:600;font-size:0.9rem;cursor:pointer"
        )


# ---------------------------------------------------------------------------
# Main build()
# ---------------------------------------------------------------------------

def build() -> None:
    """Messenger-Seite aufbauen."""
    cfg = _load_cfg()
    messages = _load_messages()
    unread_count = sum(1 for m in messages if not m.get("read", False))

    # Header
    with ui.row().classes("items-center gap-3 w-full mb-4"):
        ui.icon("forum").style("font-size:1.8rem;color:#00d4ff")
        with ui.column().classes("gap-0"):
            ui.label("Nachrichten").style("font-size:1.4rem;font-weight:700;color:var(--ds-text)")
            ui.label("WhatsApp · Telegram · Signal").style("font-size:0.82rem;color:var(--ds-text-2)")

        ui.space()

        if unread_count:
            ui.label(f"{unread_count} ungelesen").style(
                "background:rgba(0,212,255,0.15);color:#00d4ff;"
                "border-radius:20px;padding:4px 14px;font-size:0.82rem;font-weight:600"
            )

        ui.button(
            icon="refresh",
            on_click=lambda: ui.navigate.reload(),
        ).style(
            "background:rgba(0,212,255,0.08);color:#00d4ff;"
            "border:1px solid rgba(0,212,255,0.2);border-radius:8px;"
            "padding:6px;cursor:pointer;min-width:0"
        ).props("flat dense")

    # Tabs
    with ui.tabs().classes("w-full mb-4").props("indicator-color=cyan align=left") as tabs:
        tab_msgs = ui.tab("Nachrichten", icon="inbox")
        tab_conn = ui.tab("Verbindungen", icon="link")
        tab_sett = ui.tab("Einstellungen", icon="settings")

    with ui.tab_panels(tabs, value=tab_msgs).classes("w-full"):
        with ui.tab_panel(tab_msgs):
            _build_messages_tab(cfg)

        with ui.tab_panel(tab_conn):
            _build_connections_tab(cfg)

        with ui.tab_panel(tab_sett):
            _build_settings_tab(cfg)
