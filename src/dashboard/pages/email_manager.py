"""E-Mail Manager — IMAP Posteingang, Konten und Regelanwendung."""

from __future__ import annotations

from nicegui import run, ui

from ..theme import callout, empty_state, page_header, section_title, status_badge
from ...config import load_config, save_config


def _safe_int(value, default: int) -> int:
    """Konvertiert UI-Eingabe sicher zu int, gibt default zurück bei Fehler."""
    try:
        return int(value or default)
    except (ValueError, TypeError):
        return default


def build() -> None:
    """E-Mail Manager aufbauen."""
    cfg = load_config()

    page_header("E-Mail", "E-Mail-Regeln verwalten und Postfach automatisch sortieren")

    with ui.tabs().classes("ds-tabs w-full") as tabs:
        tab_inbox = ui.tab("Posteingang", icon="inbox")
        tab_ki = ui.tab("KI-Analyse", icon="psychology")
        tab_webhook = ui.tab("Empfang", icon="cloud_download")
        tab_accounts = ui.tab("Konten", icon="manage_accounts")
        tab_rules = ui.tab("Regeln", icon="filter_alt")

    with ui.tab_panels(tabs, value=tab_inbox).classes("w-full mt-4"):
        with ui.tab_panel(tab_inbox):
            _build_inbox(cfg)
        with ui.tab_panel(tab_ki):
            _build_ki_analyse(cfg)
        with ui.tab_panel(tab_webhook):
            _build_webhook(cfg)
        with ui.tab_panel(tab_accounts):
            _build_accounts(cfg)
        with ui.tab_panel(tab_rules):
            _build_rules(cfg)


def _build_inbox(cfg: dict) -> None:
    from ...email_connector import load_emails, fetch_emails, apply_email_rules, EmailAccount
    from ...assistant_store import get_email_rules

    emails_container = ui.column().classes("w-full gap-3")

    def _render_emails():
        emails_container.clear()
        messages = load_emails(cfg)
        rules = get_email_rules()

        with emails_container:
            if not messages:
                empty_state("inbox", "Posteingang ist leer", "Klicke 'E-Mails abrufen' um aktuelle E-Mails vom Server zu laden. Stelle sicher, dass unter 'Konten' ein IMAP-Konto eingerichtet ist.")
                return

            matches = apply_email_rules(messages, rules)
            section_title(f"{len(messages)} E-Mails", "email")

            for item in matches:
                msg_d = item["message"]
                target = item.get("target_folder", "")
                matched = item.get("matched_rules", [])

                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-start gap-3 w-full"):
                        ui.icon("mail" if not msg_d.get("read") else "drafts").style(
                            "font-size:1.2rem;color:var(--ds-primary);margin-top:2px;flex-shrink:0"
                        )
                        with ui.column().classes("gap-1 flex-1 min-w-0"):
                            with ui.row().classes("items-center gap-2 flex-wrap"):
                                ui.label(msg_d.get("subject", "")).style(
                                    "font-size:0.85rem;font-weight:600;color:var(--ds-text)"
                                )
                                if msg_d.get("has_attachments"):
                                    ui.icon("attach_file").style("font-size:0.8rem;color:var(--ds-text-2)")
                            with ui.row().classes("items-center gap-2"):
                                ui.label(msg_d.get("sender_email", "")).style(
                                    "font-size:0.72rem;color:var(--ds-text-2)"
                                )
                                ui.label("·").style("color:var(--ds-text-3)")
                                ui.label(msg_d.get("date", "")).style(
                                    "font-size:0.72rem;color:var(--ds-text-3)"
                                )
                            if msg_d.get("snippet"):
                                snippet = msg_d["snippet"]
                                display = (snippet[:120] + "…") if len(snippet) > 120 else snippet
                                ui.label(display).style(
                                    "font-size:0.75rem;color:var(--ds-text-2);line-height:1.4"
                                )
                            if matched:
                                with ui.row().classes("gap-2 mt-1"):
                                    for rule in matched:
                                        ui.label(f"→ {rule.get('target_folder','?')}").style(
                                            "font-size:0.65rem;font-weight:600;padding:2px 8px;"
                                            "border-radius:4px;background:rgba(0,232,125,0.1);"
                                            "color:#00e87d;border:1px solid rgba(0,232,125,0.3)"
                                        )

    _render_emails()

    # Abrufen Button
    accounts_cfg = cfg.get("email_accounts", [])

    async def do_fetch():
        if not accounts_cfg:
            ui.notify("Kein E-Mail-Konto konfiguriert. Gehe zu 'Konten'.", type="warning")
            return
        try:
            from ...email_connector import fetch_emails, save_emails, EmailAccount
            all_msgs = []
            for acc_d in accounts_cfg:
                if not acc_d.get("enabled", True):
                    continue
                acc = EmailAccount(**{k: v for k, v in acc_d.items() if k in EmailAccount.__dataclass_fields__})
                msgs = await run.io_bound(fetch_emails, acc, 50)
                all_msgs.extend(msgs)
            # Vorher geladene IDs merken für Duplikat-Check
            from ...email_connector import load_emails as _le
            existing_ids = {m.id for m in _le(cfg)}
            save_emails(cfg, all_msgs)
            # Neue Mails in Feed-Store schreiben
            try:
                from ...feed_store import add_item
            except ImportError:
                add_item = None
            if add_item:
                for m in all_msgs:
                    if m.id not in existing_ids:
                        add_item(
                            source="email",
                            title=m.subject or "(kein Betreff)",
                            content=m.body or m.snippet or "",
                            metadata={"from": m.sender_email, "date": m.date, "has_attachments": m.has_attachments},
                        )
            _render_emails()
            ui.notify(f"{len(all_msgs)} E-Mails geladen.", type="positive")
        except Exception as e:
            ui.notify(f"Fehler: {e}", type="negative")

    with ui.row().classes("gap-3 mt-2"):
        ui.button("E-Mails abrufen", on_click=do_fetch, icon="refresh").classes("ds-btn-primary").tooltip("E-Mails vom IMAP-Server laden und Regeln anwenden")
        ui.button("E-Mail verfassen", on_click=_show_compose_dialog, icon="edit").classes("ds-btn-secondary").tooltip("Neue E-Mail schreiben und senden")


def _show_compose_dialog() -> None:
    """E-Mail verfassen Dialog."""
    from ...config import load_config
    from ...email_connector import send_email, EmailAccount

    cfg = load_config()
    accounts_cfg = cfg.get("email_accounts", [])

    with ui.dialog() as dlg, ui.card().style(
        "min-width:500px;background:rgba(10,22,40,0.97);border:1px solid rgba(0,212,255,0.2)"
    ):
        with ui.column().classes("gap-3 w-full").style("padding:20px"):
            ui.label("E-Mail verfassen").style(
                "font-size:1rem;font-weight:700;color:var(--ds-text)"
            )
            acc_names = [a.get("name", a.get("username", "")) for a in accounts_cfg]
            acc_sel = ui.select(label="Absender-Konto", options=acc_names or ["(kein Konto)"]).classes("w-full")
            to_inp = ui.input(label="An", placeholder="empfaenger@example.com").classes("w-full")
            cc_inp = ui.input(label="CC (optional)").classes("w-full")
            subj_inp = ui.input(label="Betreff").classes("w-full")
            body_inp = ui.textarea(label="Nachricht").classes("w-full").style("min-height:120px")

            async def do_send():
                if not acc_names or not accounts_cfg:
                    ui.notify("Kein Konto konfiguriert.", type="warning")
                    return
                idx = acc_names.index(acc_sel.value) if acc_sel.value in acc_names else 0
                acc_d = accounts_cfg[idx]
                acc = EmailAccount(**{k: v for k, v in acc_d.items() if k in EmailAccount.__dataclass_fields__})
                ok, msg = await run.io_bound(send_email, acc, to_inp.value, subj_inp.value, body_inp.value, cc_inp.value)
                ui.notify(msg, type="positive" if ok else "negative")
                if ok:
                    dlg.close()

            with ui.row().classes("gap-2 justify-end w-full"):
                ui.button("Abbrechen", on_click=dlg.close).props("flat").style("color:var(--ds-text-2)")
                ui.button("Senden", on_click=do_send, icon="send").classes("ds-btn-primary")

    dlg.open()


def _build_webhook(cfg: dict) -> None:
    """Empfang-Tab: Webhook-Einrichtung fuer eingehende Kunden-E-Mails."""
    from ...email_webhook import generate_secret, get_webhook_url
    from ...config import save_config, load_config_raw

    wh_cfg = cfg.setdefault("email_webhook", {
        "enabled": True, "provider": "generic",
        "secret": "", "public_url": "", "mailgun_api_key": "",
    })

    # Secret auto-generieren wenn leer
    if not wh_cfg.get("secret"):
        wh_cfg["secret"] = generate_secret()

    section_title("Wie kommen Kunden-E-Mails rein?", "help_outline")
    callout(
        "Es gibt zwei Wege: <b>IMAP-Abruf</b> (unter 'Konten' ein echtes Postfach verbinden — "
        "die App holt Mails regelmässig ab) oder <b>Inbound-Webhook</b> (ein E-Mail-Dienst leitet "
        "eingehende Mails sofort per HTTP an die App weiter — Echtzeit, kein Polling).",
        "info", "info"
    )

    with ui.grid(columns=2).classes("gap-6 w-full mt-4"):

        # --- Weg 1: IMAP ---
        with ui.card().classes("ds-card").style("border:1px solid rgba(0,212,255,0.2)"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ui.icon("mail").style("color:#00d4ff;font-size:1.3rem")
                ui.label("Weg 1: IMAP-Abruf").style("font-size:0.95rem;font-weight:700;color:var(--ds-text)")
            ui.label("Verbinde dein bestehendes Postfach (Gmail, Outlook, etc.) unter 'Konten'. "
                     "Der Nachtarbeiter-Scheduler fragt automatisch neue Mails ab.").style(
                "font-size:0.8rem;color:var(--ds-text-2);line-height:1.5"
            )
            ui.label("✓ Kein extra Dienst nötig  ✓ Funktioniert mit jedem IMAP-Provider").style(
                "font-size:0.72rem;color:#00e87d;margin-top:8px"
            )
            ui.button("→ Konto einrichten", on_click=lambda: ui.navigate.to("/email"), icon="settings").props(
                "flat no-caps dense"
            ).style("color:#00d4ff;margin-top:8px")

        # --- Weg 2: Webhook ---
        with ui.card().classes("ds-card").style("border:1px solid rgba(0,232,125,0.2)"):
            with ui.row().classes("items-center gap-2 mb-3"):
                ui.icon("cloud_download").style("color:#00e87d;font-size:1.3rem")
                ui.label("Weg 2: Inbound Webhook").style("font-size:0.95rem;font-weight:700;color:var(--ds-text)")
            ui.label("Ein E-Mail-Dienst (Mailgun, SendGrid, Postmark) empfängt E-Mails für deine Domain "
                     "und sendet sie sofort per HTTP an die App. Echtzeit ohne Polling.").style(
                "font-size:0.8rem;color:var(--ds-text-2);line-height:1.5"
            )
            ui.label("✓ Echtzeit  ✓ Skalierbar  ✓ Gratis-Tiers verfügbar").style(
                "font-size:0.72rem;color:#00e87d;margin-top:8px"
            )
            ui.button("→ Webhook einrichten", on_click=lambda: ui.navigate.to("/email"), icon="webhook").props(
                "flat no-caps dense"
            ).style("color:#00e87d;margin-top:8px")

    # --- Webhook-Konfiguration ---
    section_title("Webhook konfigurieren", "webhook")

    with ui.card().classes("ds-card-flat w-full"):
        with ui.column().classes("gap-4 w-full"):

            # Provider + Enable
            with ui.row().classes("items-center gap-4 flex-wrap"):
                provider_sel = ui.select(
                    label="Provider",
                    options={
                        "generic":  "Generic / Zapier / Make.com",
                        "mailgun":  "Mailgun",
                        "sendgrid": "SendGrid",
                        "postmark": "Postmark",
                    },
                    value=wh_cfg.get("provider", "generic"),
                ).classes("ds-input").style("min-width:220px")

                enabled_sw = ui.switch("Webhook aktiv", value=wh_cfg.get("enabled", True))

            # Public URL + Secret
            with ui.grid(columns=2).classes("gap-3 w-full"):
                public_url_inp = ui.input(
                    label="Deine öffentliche URL",
                    placeholder="https://meinserver.de  oder  https://abc.ngrok.io",
                    value=wh_cfg.get("public_url", ""),
                ).classes("ds-input w-full").tooltip(
                    "URL unter der die App von außen erreichbar ist. Lokal: ngrok verwenden."
                )

                secret_inp = ui.input(
                    label="Webhook-Secret (Token)",
                    value=wh_cfg.get("secret", ""),
                ).classes("ds-input w-full")

            # Mailgun API Key (nur wenn mailgun gewählt)
            mailgun_row = ui.row().classes("w-full")
            with mailgun_row:
                mailgun_key_inp = ui.input(
                    label="Mailgun API-Key (fuer Signaturpruefung)",
                    value=wh_cfg.get("mailgun_api_key", ""),
                    password=True, password_toggle_button=True,
                ).classes("ds-input w-full")

            def _update_mailgun_visibility():
                mailgun_row.set_visibility(provider_sel.value == "mailgun")

            provider_sel.on_value_change(lambda _: _update_mailgun_visibility())
            _update_mailgun_visibility()

            # Webhook-URL anzeigen
            webhook_url_label = ui.label("").style(
                "font-size:0.78rem;font-family:monospace;padding:10px 14px;border-radius:8px;"
                "background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.15);"
                "color:#00d4ff;word-break:break-all;cursor:pointer"
            ).tooltip("Klicken zum Kopieren")

            def _update_url_label():
                pub = public_url_inp.value.rstrip("/") or "http://localhost:8080"
                webhook_url_label.set_text(f"{pub}/api/email/inbound")

            public_url_inp.on_value_change(lambda _: _update_url_label())
            _update_url_label()

            webhook_url_label.on("click", lambda: ui.run_javascript(
                f"navigator.clipboard.writeText('{get_webhook_url(cfg)}')"
            ))

            def save_webhook():
                raw_cfg = load_config_raw()
                wh = raw_cfg.setdefault("email_webhook", {})
                wh["provider"] = provider_sel.value
                wh["enabled"] = enabled_sw.value
                wh["public_url"] = public_url_inp.value.strip()
                wh["secret"] = secret_inp.value.strip()
                wh["mailgun_api_key"] = mailgun_key_inp.value.strip()
                save_config(raw_cfg)
                ui.notify("Webhook-Einstellungen gespeichert.", type="positive")
                _update_url_label()

            def regen_secret():
                secret_inp.value = generate_secret()
                ui.notify("Neues Secret generiert — bitte speichern!", type="info")

            with ui.row().classes("gap-2"):
                ui.button("Speichern", on_click=save_webhook, icon="save").classes("ds-btn-primary")
                ui.button("Secret neu generieren", on_click=regen_secret, icon="refresh").props(
                    "flat no-caps"
                ).style("color:var(--ds-text-2)")

    # --- Anleitung pro Provider ---
    section_title("Einrichtungsanleitung", "menu_book")

    _GUIDES = {
        "mailgun": (
            "Mailgun", "#FF6C2C",
            [
                "Kostenloser Account auf mailgun.com — 1.000 E-Mails/Monat gratis",
                "Domain verifizieren oder Sandbox-Domain nutzen (kein DNS nötig)",
                "Receiving → Routes → 'Create Route' → Aktion: 'Forward to URL'",
                f"URL: <code>{{webhook_url}}</code>",
                "Mailgun API-Key oben eintragen (für Signaturprüfung)",
                "Kunden schicken an: <b>contact@deine-domain.mailgun.org</b>",
            ]
        ),
        "sendgrid": (
            "SendGrid", "#1A82E2",
            [
                "Kostenloses Konto auf sendgrid.com — 100 E-Mails/Tag gratis",
                "Settings → Inbound Parse → 'Add Host & URL'",
                "MX-Record deiner Domain auf mx.sendgrid.net setzen",
                f"Webhook URL: <code>{{webhook_url}}</code>",
                "Header <b>X-Webhook-Token: {secret}</b> per Custom Header (Zapier o.ä.) oder manuell",
                "Kunden schicken an: <b>contact@deine-domain.com</b>",
            ]
        ),
        "postmark": (
            "Postmark", "#FFDE00",
            [
                "Konto auf postmarkapp.com — 100 E-Mails/Monat gratis",
                "Server → Inbound → Inbound Webhook URL eintragen",
                f"URL: <code>{{webhook_url}}</code>",
                "MX-Record: <b>inbound.postmarkapp.com</b> für deine Domain",
                "Kunden schicken an: <b>contact@inbound.postmarkapp.com</b> (Hash-Adresse)",
                "Header <b>X-Webhook-Token</b> wird nicht benötigt — Postmark hat eigene Signierung",
            ]
        ),
        "generic": (
            "Generic / Zapier / Make.com", "#7C3AED",
            [
                "Jeder Dienst der HTTP POST kann: Zapier, Make.com, n8n, eigenes Skript",
                f"URL: <code>{{webhook_url}}</code>  (POST, JSON)",
                "Header setzen: <b>X-Webhook-Token: {secret}</b>",
                'JSON-Body: <code>{"subject":"...","from":"...","body":"...","sender_email":"..."}</code>',
                "Auch für <b>E-Mail-Weiterleitungen</b>: Gmail → Zapier → Webhook",
                "Oder: Eigenes Python-Skript das imaplib nutzt und an den Webhook postet",
            ]
        ),
    }

    first_tab_ref = None
    with ui.tabs().classes("ds-tabs w-full") as tabs2:
        tab_refs = {}
        for key, (name, color, _) in _GUIDES.items():
            tab_refs[key] = ui.tab(name).classes("ds-tab")
            if first_tab_ref is None:
                first_tab_ref = tab_refs[key]
    tabs2.set_value(first_tab_ref)

    with ui.tab_panels(tabs2, value=first_tab_ref).classes("w-full mt-3"):
        for key, (name, color, steps) in _GUIDES.items():
            with ui.tab_panel(tab_refs[key]):
                current_url = get_webhook_url(cfg)
                current_secret = wh_cfg.get("secret", "")
                with ui.card().classes("ds-card-flat w-full"):
                    for i, step in enumerate(steps, 1):
                        step_html = step.replace("{webhook_url}", current_url).replace("{secret}", current_secret)
                        with ui.row().classes("items-start gap-3").style("padding:6px 0"):
                            ui.label(str(i)).style(
                                f"font-size:0.7rem;font-weight:700;padding:2px 7px;border-radius:50%;"
                                f"background:{color}20;color:{color};border:1px solid {color}40;flex-shrink:0"
                            )
                            ui.html(f'<span style="font-size:0.8rem;color:var(--ds-text);line-height:1.5">{step_html}</span>',
                                    sanitize=False)


def _build_ki_analyse(cfg: dict) -> None:
    """KI-Analyse Tab: Priorisierung und Todo-Generierung aus E-Mails."""
    from ...email_connector import load_emails, prioritize_emails, extract_action_items
    from ...assistant_store import add_todo

    _PRIORITY_STYLE = {
        "high":   ("Hoch",   "#ff3366", "priority_high"),
        "medium": ("Mittel", "#ff9f0a", "drag_handle"),
        "low":    ("Niedrig","#00e87d", "low_priority"),
    }

    results_col = ui.column().classes("w-full gap-3")
    todos_col = ui.column().classes("w-full gap-3")

    async def do_analyse():
        messages = await run.io_bound(load_emails, cfg)
        if not messages:
            ui.notify("Keine E-Mails geladen. Zuerst Posteingang abrufen.", type="warning")
            return

        prioritized = await run.io_bound(prioritize_emails, messages)
        results_col.clear()
        with results_col:
            section_title(f"{len(prioritized)} E-Mails priorisiert", "psychology")
            for item in prioritized[:20]:
                msg = item["message"]
                priority = item["priority"]
                label_text, color, icon = _PRIORITY_STYLE[priority]
                reasons = ", ".join(item["reasons"]) if item["reasons"] else "–"

                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-3 w-full"):
                        with ui.element("div").style(
                            f"width:32px;height:32px;border-radius:8px;flex-shrink:0;"
                            f"background:{color}18;border:1px solid {color}30;"
                            f"display:flex;align-items:center;justify-content:center"
                        ):
                            ui.icon(icon).style(f"font-size:1rem;color:{color}")
                        with ui.column().classes("gap-0 flex-1 min-w-0"):
                            ui.label(msg.subject).style(
                                "font-size:0.82rem;font-weight:600;color:var(--ds-text);"
                                "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                            )
                            with ui.row().classes("items-center gap-2"):
                                ui.label(msg.sender_email).style("font-size:0.68rem;color:var(--ds-text-2)")
                                if reasons != "–":
                                    ui.label(f"· {reasons}").style("font-size:0.65rem;color:var(--ds-text-3)")
                        ui.label(label_text).style(
                            f"font-size:0.6rem;font-weight:700;padding:2px 8px;border-radius:4px;"
                            f"background:{color}15;color:{color};border:1px solid {color}30;white-space:nowrap"
                        )

    async def do_generate_todos():
        messages = await run.io_bound(load_emails, cfg)
        if not messages:
            ui.notify("Keine E-Mails geladen. Zuerst Posteingang abrufen.", type="warning")
            return

        items = await run.io_bound(extract_action_items, messages)
        if not items:
            ui.notify("Keine Aktionspunkte gefunden.", type="info")
            return

        count = 0
        for item in items:
            todo_text = f"{item['action']} — Von: {item['sender_email']}"
            await run.io_bound(add_todo, todo_text, item["priority"])
            count += 1

        todos_col.clear()
        with todos_col:
            section_title(f"{count} Todos erstellt", "check_circle")
            for item in items:
                _, color, icon = _PRIORITY_STYLE.get(item["priority"], ("", "#00d4ff", "task"))
                with ui.row().classes("items-center gap-3").style(
                    "padding:8px 12px;border-radius:8px;background:rgba(10,22,40,0.6);"
                    "border:1px solid rgba(0,212,255,0.1)"
                ):
                    ui.icon(icon).style(f"font-size:0.9rem;color:{color}")
                    with ui.column().classes("gap-0 flex-1 min-w-0"):
                        ui.label(item["action"]).style("font-size:0.8rem;font-weight:600;color:var(--ds-text)")
                        ui.label(f"Von: {item['sender_email']}").style("font-size:0.68rem;color:var(--ds-text-2)")

        ui.notify(f"{count} Todos in den Assistenten eingetragen.", type="positive")

    # Was ist KI-Analyse?
    with ui.card().classes("ds-card-flat w-full mb-4"):
        with ui.row().classes("items-start gap-3"):
            ui.icon("psychology").style("font-size:1.8rem;color:#00d4ff;flex-shrink:0;margin-top:2px")
            with ui.column().classes("gap-2 flex-1"):
                ui.label("Was macht die KI-Analyse?").style(
                    "font-size:0.9rem;font-weight:700;color:var(--ds-text)"
                )
                ui.label(
                    "Die KI liest Betreff und Inhalt deiner E-Mails und bewertet sie nach Dringlichkeit "
                    "(Hoch / Mittel / Niedrig). Außerdem erkennt sie Aufgaben (z.B. 'Bitte bis Freitag antworten') "
                    "und trägt diese direkt als Todos in deinen Assistenten ein."
                ).style("font-size:0.8rem;color:var(--ds-text-2);line-height:1.6")
                ui.label("Voraussetzung: Posteingang muss zuerst abgerufen sein (Tab 'Posteingang' → Abrufen).").style(
                    "font-size:0.75rem;color:#f59e0b;line-height:1.5"
                )

    with ui.row().classes("gap-3 mb-4"):
        ui.button("E-Mails priorisieren", on_click=do_analyse, icon="sort").classes("ds-btn-primary").tooltip("E-Mails nach Wichtigkeit sortieren — Hoch, Mittel, Niedrig")
        ui.button("Aufgaben automatisch erkennen", on_click=do_generate_todos, icon="add_task").classes("ds-btn-secondary").tooltip("Aktionspunkte aus E-Mails erkennen und als Aufgaben speichern")

    results_col
    ui.separator().classes("my-2")
    todos_col


def _build_accounts(cfg: dict) -> None:
    from ...email_connector import test_connection, EmailAccount

    accounts = cfg.setdefault("email_accounts", [])

    # Einrichtungsanleitung (immer sichtbar wenn kein Konto)
    if not accounts:
        with ui.card().classes("ds-card-flat w-full mb-4"):
            with ui.row().classes("items-start gap-3 mb-3"):
                ui.icon("help_outline").style("font-size:1.6rem;color:#00d4ff;flex-shrink:0")
                with ui.column().classes("gap-1 flex-1"):
                    ui.label("Wie verbinde ich mein E-Mail-Postfach?").style(
                        "font-size:0.9rem;font-weight:700;color:var(--ds-text)"
                    )
                    ui.label(
                        "Hier kannst du dein bestehendes Postfach (Gmail, Outlook, GMX, etc.) verbinden. "
                        "Die App ruft dann automatisch neue Mails ab und analysiert sie."
                    ).style("font-size:0.8rem;color:var(--ds-text-2);line-height:1.6")

            with ui.expansion("🟢 Einfache Variante: Gmail in 2 Schritten").classes("w-full ds-card mb-2"):
                with ui.column().classes("gap-2 pl-2"):
                    for step, text in [
                        ("1", "Google-Konto öffnen → Sicherheit → 2-Schritt-Verifizierung aktivieren"),
                        ("2", "Dann: Google-Konto → Sicherheit → App-Passwörter → 'Mail' + 'Mac/Windows' wählen → Passwort kopieren"),
                        ("3", "Unten: IMAP Host = <b>imap.gmail.com</b>, Port = <b>993</b>, SMTP = <b>smtp.gmail.com</b>, Port = <b>587</b>"),
                        ("4", "Benutzername = deine Gmail-Adresse, Passwort = das App-Passwort (nicht dein normales!)"),
                    ]:
                        with ui.row().classes("items-start gap-3 py-1"):
                            ui.label(step).style(
                                "font-size:0.68rem;font-weight:700;padding:2px 7px;border-radius:50%;"
                                "background:rgba(0,232,125,0.12);color:#00e87d;border:1px solid rgba(0,232,125,0.3);flex-shrink:0"
                            )
                            ui.html(f'<span style="font-size:0.8rem;color:var(--ds-text);line-height:1.5">{text}</span>',
                                    sanitize=False)

            with ui.expansion("🔵 Für Outlook / Microsoft 365").classes("w-full ds-card mb-2"):
                with ui.column().classes("gap-2 pl-2"):
                    for step, text in [
                        ("1", "IMAP Host: <b>outlook.office365.com</b>, Port: <b>993</b> (SSL)"),
                        ("2", "SMTP Host: <b>smtp.office365.com</b>, Port: <b>587</b> (STARTTLS)"),
                        ("3", "Benutzername: deine vollständige E-Mail-Adresse"),
                        ("4", "Passwort: dein normales Microsoft-Passwort oder App-Passwort bei aktivierter 2FA"),
                    ]:
                        with ui.row().classes("items-start gap-3 py-1"):
                            ui.label(step).style(
                                "font-size:0.68rem;font-weight:700;padding:2px 7px;border-radius:50%;"
                                "background:rgba(0,212,255,0.12);color:#00d4ff;border:1px solid rgba(0,212,255,0.3);flex-shrink:0"
                            )
                            ui.html(f'<span style="font-size:0.8rem;color:var(--ds-text);line-height:1.5">{text}</span>',
                                    sanitize=False)

            with ui.expansion("⚙️ Technische Variante: Eigener Mail-Server / IMAP").classes("w-full ds-card"):
                with ui.column().classes("gap-2 pl-2"):
                    ui.label("Für erfahrene Nutzer mit eigenem Server (z.B. Hetzner, cPanel, Postfix):").style(
                        "font-size:0.8rem;color:var(--ds-text-2)"
                    )
                    for key, val in [
                        ("IMAP Host", "mail.deinedomain.de"),
                        ("IMAP Port", "993 (SSL) oder 143 (STARTTLS)"),
                        ("SMTP Host", "mail.deinedomain.de"),
                        ("SMTP Port", "587 (STARTTLS) oder 465 (SSL)"),
                        ("Benutzername", "vollständige E-Mail-Adresse"),
                        ("Passwort", "E-Mail-Passwort des Accounts"),
                    ]:
                        with ui.row().classes("items-center gap-3"):
                            ui.label(f"{key}:").style("font-size:0.78rem;color:var(--ds-text-2);min-width:120px")
                            ui.label(val).style(
                                "font-size:0.78rem;font-family:monospace;color:#00d4ff;"
                                "background:rgba(0,212,255,0.06);padding:2px 8px;border-radius:4px"
                            )

    container = ui.column().classes("w-full gap-4")

    def _render():
        container.clear()
        with container:
            if not accounts:
                pass  # Anleitung oben angezeigt

            for i, acc in enumerate(accounts):
                with ui.card().classes("ds-card w-full"):
                    with ui.row().classes("items-center gap-3 mb-3"):
                        ui.icon("email").style("color:var(--ds-primary);font-size:1.3rem")
                        ui.label(acc.get("name", f"Konto {i+1}")).style(
                            "font-size:0.95rem;font-weight:700;color:var(--ds-text);flex:1"
                        )
                        status = "success" if acc.get("enabled") else "neutral"
                        status_badge("Aktiv" if acc.get("enabled") else "Inaktiv", status)

                    with ui.grid(columns=2).classes("gap-3 w-full"):
                        ui.label("IMAP Host:").style("font-size:0.8rem;color:var(--ds-text-2)")
                        ui.label(f"{acc.get('imap_host','')}:{acc.get('imap_port',993)}").style("font-size:0.8rem;color:var(--ds-text)")
                        ui.label("Benutzername:").style("font-size:0.8rem;color:var(--ds-text-2)")
                        ui.label(acc.get("username","")).style("font-size:0.8rem;color:var(--ds-text)")

                    with ui.row().classes("gap-2 mt-3"):
                        def make_test(a=acc):
                            async def handler():
                                obj = EmailAccount(
                                    name=a.get("name",""),
                                    imap_host=a.get("imap_host",""),
                                    imap_port=a.get("imap_port",993),
                                    username=a.get("username",""),
                                    password=a.get("password",""),
                                    use_ssl=a.get("use_ssl",True),
                                )
                                ok, msg = await run.io_bound(test_connection, obj)
                                ui.notify(msg, type="positive" if ok else "negative")
                            return handler

                        def make_delete(idx=i):
                            def handler():
                                accounts.pop(idx)
                                save_config(cfg)
                                _render()
                            return handler

                        ui.button("Testen", on_click=make_test(), icon="wifi").classes("ds-btn-secondary").props("dense")
                        ui.button("Entfernen", on_click=make_delete(), icon="delete").classes("ds-btn-danger").props("dense").tooltip("Konto dauerhaft entfernen")

            # Neues Konto
            section_title("Konto hinzufügen", "add")
            with ui.card().classes("ds-card-flat w-full"):
                with ui.column().classes("gap-3 w-full"):
                    with ui.grid(columns=2).classes("gap-3 w-full"):
                        name_inp = ui.input(label="Kontoname", placeholder="z.B. Arbeit").classes("ds-input w-full")
                        user_inp = ui.input(label="Benutzername / E-Mail").classes("ds-input w-full")
                        host_inp = ui.input(label="IMAP Host", placeholder="imap.gmail.com").classes("ds-input w-full")
                        port_inp = ui.number(label="IMAP Port", value=993).classes("ds-input w-full")
                        smtp_host_inp = ui.input(label="SMTP Host", placeholder="smtp.gmail.com").classes("ds-input w-full")
                        smtp_port_inp = ui.number(label="SMTP Port", value=587).classes("ds-input w-full")
                    pw_inp = ui.input(label="Passwort", password=True, password_toggle_button=True).classes("ds-input w-full")
                    ssl_sw = ui.switch("IMAP SSL/TLS", value=True)
                    tls_sw = ui.switch("SMTP STARTTLS", value=True)

                    callout(
                        "Passwörter werden lokal in config.yaml gespeichert. "
                        "Für Gmail: App-Passwort unter Google-Konto → Sicherheit → App-Passwörter erstellen.",
                        "warning", "lock"
                    )

                    def add_account():
                        if not host_inp.value or not user_inp.value:
                            ui.notify("Host und Benutzername sind Pflichtfelder.", type="warning")
                            return
                        accounts.append({
                            "name": name_inp.value or user_inp.value,
                            "imap_host": host_inp.value,
                            "imap_port": _safe_int(port_inp.value, 993),
                            "username": user_inp.value,
                            "password": pw_inp.value,
                            "use_ssl": ssl_sw.value,
                            "smtp_host": smtp_host_inp.value,
                            "smtp_port": _safe_int(smtp_port_inp.value, 587),
                            "smtp_use_tls": tls_sw.value,
                            "enabled": True,
                        })
                        save_config(cfg)
                        ui.notify("Konto hinzugefügt!", type="positive")
                        _render()

                    ui.button("Konto hinzufügen", on_click=add_account, icon="add").classes("ds-btn-success")

    _render()


def _build_rules(cfg: dict) -> None:
    from ...assistant_store import get_email_rules, add_email_rule, delete_email_rule, toggle_email_rule

    container = ui.column().classes("w-full gap-3")

    def _render():
        container.clear()
        with container:
            rules = get_email_rules()
            if not rules:
                empty_state("filter_alt", "Noch keine E-Mail-Regeln", "Erstelle unten eine Regel um E-Mails automatisch zu sortieren — z.B. alle E-Mails von @amazon.de in den Ordner 'Bestellungen' verschieben.")
            for rule in rules:
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-3 w-full"):
                        active_color = "#00e87d" if rule.get("active") else "var(--ds-text-3)"
                        ui.icon("filter_alt").style(f"color:{active_color};font-size:1.1rem;flex-shrink:0")
                        with ui.column().classes("gap-0 flex-1 min-w-0"):
                            parts = []
                            if rule.get("sender_pattern"):
                                parts.append(f"Von: {rule['sender_pattern']}")
                            if rule.get("subject_pattern"):
                                parts.append(f"Betreff: {rule['subject_pattern']}")
                            ui.label(" · ".join(parts) or "Alle E-Mails").style(
                                "font-size:0.8rem;font-weight:600;color:var(--ds-text)"
                            )
                            ui.label(f"→ {rule.get('target_folder','?')}").style(
                                "font-size:0.72rem;color:var(--ds-text-2)"
                            )
                        def make_toggle(rid=rule.get("id","")):
                            def handler():
                                toggle_email_rule(rid)
                                _render()
                            return handler
                        def make_del(rid=rule.get("id","")):
                            def handler():
                                delete_email_rule(rid)
                                _render()
                            return handler
                        ui.button(icon="toggle_on" if rule.get("active") else "toggle_off",
                                  on_click=make_toggle()).props("flat round dense").style(
                            f"color:{'#00e87d' if rule.get('active') else 'var(--ds-text-3)'}"
                        )
                        ui.button(icon="delete", on_click=make_del()).props("flat round dense").style("color:var(--ds-error)").tooltip("Regel entfernen")

            # Neue Regel
            section_title("Neue E-Mail-Regel", "add")
            with ui.card().classes("ds-card-flat w-full"):
                with ui.grid(columns=2).classes("gap-3 w-full"):
                    sender_inp = ui.input(label="Absender enthält (optional)", placeholder="z.B. @amazon.de oder noreply@gasag.de").classes("ds-input w-full")
                    subject_inp = ui.input(label="Betreff enthält (optional)", placeholder="z.B. Rechnung, Kündigung, Angebot").classes("ds-input w-full")
                    folder_inp = ui.input(label="Ziel-Ordner", placeholder="z.B. Rechnungen, Lieferanten").classes("ds-input w-full")
                    action_sel = ui.select(label="Aktion", options=["Verschieben", "Markieren", "Ignorieren"],
                                           value="Verschieben").classes("ds-input w-full")

                def add_rule():
                    if not folder_inp.value:
                        ui.notify("Ziel-Ordner ist Pflichtfeld.", type="warning")
                        return
                    add_email_rule(
                        sender_pattern=sender_inp.value,
                        subject_pattern=subject_inp.value,
                        target_folder=folder_inp.value,
                        action=action_sel.value.lower(),
                    )
                    ui.notify("Regel hinzugefügt!", type="positive")
                    _render()

                ui.button("Regel hinzufügen", on_click=add_rule, icon="add").classes("ds-btn-primary")

    _render()
