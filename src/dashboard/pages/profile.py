"""Profilseite – Kontodaten, Plan, Version."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from nicegui import app, ui

from ..theme import inject_theme, page_header, section_title, callout, enable_scroll

APP_VERSION = "v0.6.0"

_PLANS = {
    "free":     {"label": "Free",    "color": "#6B7280", "icon": "star_border",  "features": ["3 Test-Dokumente", "Manuelle Sortierung", "1 Benutzerprofil"]},
    "pro":      {"label": "Pro",     "color": "#3B82F6", "icon": "star_half",    "features": ["Unbegrenzte Dokumente", "Auto-Sortierung", "OCR & KI-Erkennung", "Scheduler / Nachtarbeiter"]},
    "platinum": {"label": "Platinum","color": "#F59E0B", "icon": "star",         "features": ["Alles aus Pro", "Supabase-Sync", "Multi-User", "Priority Support", "API-Zugang"]},
}

_STATE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "_state.json"


def _read_state() -> dict:
    if _STATE_PATH.exists():
        try:
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _write_state(data: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=_STATE_PATH.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, _STATE_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def build() -> None:
    username: str = app.storage.user.get("username", "")
    state = _read_state()

    email      = state.get("emails", {}).get(username, "–")
    created_at = state.get("created_at", {}).get(username, "–")
    plan_key   = state.get("plans", {}).get(username, "free")
    plan       = _PLANS.get(plan_key, _PLANS["free"])
    avatar_txt = (username[0].upper() if username else "?")

    page_header("Mein Profil", "Kontodaten, Plan und App-Informationen")

    with ui.column().classes("w-full max-w-3xl mx-auto gap-6"):

        # ── Avatar + Name + E-Mail ──────────────────────────────────────────
        with ui.card().classes("ds-card w-full"):
            with ui.row().classes("items-center gap-6 flex-wrap"):

                # Avatar-Kreis mit Initial
                ui.element("div").style(
                    "width:88px;height:88px;border-radius:50%;"
                    "background:linear-gradient(135deg,#3B82F6,#7C3AED);"
                    "display:flex;align-items:center;justify-content:center;"
                    "font-size:2.2rem;font-weight:700;color:white;"
                    "flex-shrink:0;box-shadow:0 0 0 3px rgba(59,130,246,0.35);"
                ).tooltip("Profilbild – Upload folgt in einer späteren Version"
                ).classes("cursor-default").style("").on(
                    "click", lambda: ui.notify("Profilbild-Upload kommt in einer späteren Version.", type="info")
                )
                # NiceGUI hat kein direktes HTML-child in element → Label drüber legen
                with ui.column().style(
                    "position:relative;width:88px;height:88px;margin-right:-88px;"
                    "display:flex;align-items:center;justify-content:center;"
                    "z-index:1;pointer-events:none"
                ):
                    ui.label(avatar_txt).style(
                        "font-size:2.2rem;font-weight:700;color:white;line-height:1"
                    )

                with ui.column().classes("gap-1 flex-1"):
                    ui.label(username).style("font-size:1.5rem;font-weight:700")
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("email").classes("text-blue-400 text-sm")
                        ui.label(email).style("font-size:0.9rem;color:#9CA3AF")
                    with ui.row().classes("items-center gap-2 mt-1"):
                        # Plan-Badge
                        ui.element("span").style(
                            f"background:{plan['color']}22;color:{plan['color']};"
                            "border:1px solid currentColor;border-radius:999px;"
                            "font-size:0.7rem;font-weight:700;padding:2px 10px;"
                            "text-transform:uppercase;letter-spacing:0.08em"
                        ).classes("flex items-center gap-1")
                        ui.label(plan["label"]).style(
                            f"background:{plan['color']}22;color:{plan['color']};"
                            "border:1px solid currentColor;border-radius:999px;"
                            "font-size:0.7rem;font-weight:700;padding:2px 10px;"
                            "text-transform:uppercase;letter-spacing:0.08em"
                        )

        # ── Kontodaten ──────────────────────────────────────────────────────
        with ui.card().classes("ds-card w-full"):
            section_title("Kontodaten", "manage_accounts")

            def _row(icon: str, label: str, value: str) -> None:
                with ui.row().classes("items-center gap-4 py-2 w-full"):
                    ui.icon(icon).classes("text-blue-400").style("font-size:1.1rem;min-width:20px")
                    ui.label(label).style("font-size:0.8rem;color:#9CA3AF;width:130px;flex-shrink:0")
                    ui.label(value).style("font-size:0.95rem;font-weight:500;flex:1")

            _row("person",       "Benutzername",  username)
            ui.separator().style("margin:2px 0;opacity:0.15")
            _row("email",        "E-Mail",         email)
            ui.separator().style("margin:2px 0;opacity:0.15")
            _row("calendar_today","Mitglied seit", created_at if created_at != "–" else "–")
            ui.separator().style("margin:2px 0;opacity:0.15")
            _row("info",         "App-Version",    APP_VERSION)

        # ── Passwort ändern ─────────────────────────────────────────────────
        with ui.card().classes("ds-card w-full"):
            section_title("Passwort aendern", "lock")

            pw_old  = ui.input(label="Aktuelles Passwort",  password=True, password_toggle_button=True).classes("w-full ds-input mb-2")
            pw_new  = ui.input(label="Neues Passwort",      password=True, password_toggle_button=True).classes("w-full ds-input mb-2")
            pw_new2 = ui.input(label="Neues Passwort bestätigen", password=True, password_toggle_button=True).classes("w-full ds-input")

            def _change_pw() -> None:
                s = _read_state()
                current_hash = s.get("accounts", {}).get(username, "")
                if _hash_pw(pw_old.value) != current_hash:
                    ui.notify("Aktuelles Passwort falsch.", type="negative")
                    return
                if len(pw_new.value) < 4:
                    ui.notify("Neues Passwort muss mind. 4 Zeichen haben.", type="warning")
                    return
                if pw_new.value != pw_new2.value:
                    ui.notify("Neue Passwörter stimmen nicht überein.", type="warning")
                    return
                s.setdefault("accounts", {})[username] = _hash_pw(pw_new.value)
                _write_state(s)
                for f in (pw_old, pw_new, pw_new2):
                    f.value = ""
                ui.notify("Passwort erfolgreich geändert.", type="positive")

            ui.button("Passwort speichern", on_click=_change_pw, icon="save").classes("ds-btn-primary mt-3")

        # ── Plan ────────────────────────────────────────────────────────────
        with ui.card().classes("ds-card w-full"):
            section_title("Dein Plan", "workspace_premium")

            with ui.row().classes("gap-4 w-full flex-wrap"):
                for key, p in _PLANS.items():
                    is_active = key == plan_key
                    border = f"2px solid {p['color']}" if is_active else "1px solid rgba(255,255,255,0.08)"
                    bg     = f"{p['color']}11" if is_active else "transparent"
                    with ui.card().style(
                        f"border:{border};background:{bg};border-radius:12px;"
                        "padding:16px;flex:1;min-width:140px;position:relative"
                    ):
                        if is_active:
                            ui.label("Aktiv").style(
                                f"position:absolute;top:10px;right:10px;"
                                f"background:{p['color']};color:white;"
                                "font-size:0.6rem;font-weight:700;padding:2px 8px;"
                                "border-radius:999px;text-transform:uppercase"
                            )
                        with ui.row().classes("items-center gap-2 mb-2"):
                            ui.icon(p["icon"]).style(f"color:{p['color']};font-size:1.4rem")
                            ui.label(p["label"]).style(f"font-weight:700;font-size:1rem;color:{p['color']}")
                        for feat in p["features"]:
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("check").style("font-size:0.8rem;color:#22C55E")
                                ui.label(feat).style("font-size:0.78rem;color:#9CA3AF")

            if plan_key == "free":
                ui.html('<div style="height:8px"></div>', sanitize=False)
                callout("Upgrade auf <strong>Pro</strong> oder <strong>Platinum</strong> für unbegrenzte Dokumente und KI-Features.", "info", "upgrade")

        # ── Gefahrenzone: Profil löschen ────────────────────────────────────
        with ui.card().classes("w-full").style(
            "border:1px solid rgba(239,68,68,0.3);border-radius:16px;"
            "background:rgba(239,68,68,0.04);padding:24px"
        ):
            with ui.row().classes("items-center gap-3 mb-3"):
                with ui.element("div").style(
                    "width:38px;height:38px;border-radius:10px;"
                    "background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.3);"
                    "display:flex;align-items:center;justify-content:center;flex-shrink:0"
                ):
                    ui.icon("warning").style("font-size:1.2rem;color:#EF4444")
                with ui.column().classes("gap-0"):
                    ui.label("Gefahrenzone").style(
                        "font-size:1rem;font-weight:700;color:#EF4444"
                    )
                    ui.label("Diese Aktionen können nicht rückgängig gemacht werden.").style(
                        "font-size:0.78rem;color:#9CA3AF"
                    )

            ui.label(
                "Durch das Löschen des Profils werden alle gespeicherten Daten dieses Nutzers "
                "unwiderruflich entfernt: Dokumente, Inbox, Archiv, Todos, Rechnungen, "
                "Feed, Lerngedächtnis und Kontoeinstellungen."
            ).style("font-size:0.82rem;color:var(--ds-text-2);margin-bottom:16px;line-height:1.6")

            def _open_delete_dialog() -> None:
                with ui.dialog() as dlg, ui.card().style(
                    "background:#0a1628;border:1px solid rgba(239,68,68,0.4);"
                    "border-radius:16px;padding:28px;max-width:440px;width:100%"
                ):
                    with ui.row().classes("items-center gap-3 mb-4"):
                        ui.icon("delete_forever").style("font-size:2rem;color:#EF4444")
                        with ui.column().classes("gap-0"):
                            ui.label("Profil wirklich löschen?").style(
                                "font-size:1.1rem;font-weight:700;color:#EF4444"
                            )
                            ui.label("Alle Daten werden dauerhaft gelöscht.").style(
                                "font-size:0.78rem;color:#9CA3AF"
                            )

                    ui.label(
                        f'Gib zur Bestätigung deinen Benutzernamen ein: '
                    ).style("font-size:0.82rem;color:var(--ds-text-2);margin-bottom:4px")
                    ui.label(f'„{username}"').style(
                        "font-size:0.9rem;font-weight:700;color:#EF4444;margin-bottom:10px"
                    )

                    confirm_input = ui.input(
                        placeholder=f"Benutzernamen eingeben …"
                    ).classes("w-full ds-input").props("outlined dense")

                    err_label = ui.label("").style(
                        "font-size:0.78rem;color:#EF4444;margin-top:4px"
                    )

                    def _do_delete() -> None:
                        if confirm_input.value.strip() != username:
                            err_label.set_text("Benutzername stimmt nicht überein.")
                            return

                        # ── 1. Benutzerspezifische Ordner löschen ──
                        import shutil
                        state = _read_state()
                        user_paths = state.get("user_dirs", {}).get(username, {})
                        deleted_dirs = 0
                        for p_str in user_paths.values():
                            try:
                                p = Path(p_str).expanduser()
                                if p.exists() and p.is_dir():
                                    shutil.rmtree(p)
                                    deleted_dirs += 1
                            except Exception:
                                pass

                        # ── 2. User-Verzeichnis selbst löschen (stores) ──
                        try:
                            archive = user_paths.get("archive", "")
                            if archive:
                                user_dir = Path(archive).expanduser().parent
                                # Nur spezifische Dateien löschen, kein rmtree auf user_dir
                                for fname in (
                                    "_feed.json", "_assistant.json",
                                    "user_profile.json",
                                ):
                                    fp = user_dir / fname
                                    if fp.exists():
                                        fp.unlink()
                                # User-Verzeichnis selbst (wenn leer)
                                try:
                                    user_dir.rmdir()
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        # ── 3. Aus _state.json entfernen ──
                        for key in ("accounts", "user_dirs", "user_config",
                                    "created_at", "plans", "emails"):
                            state.get(key, {}).pop(username, None)
                        # setup_done auf False wenn keine Accounts mehr
                        if not state.get("accounts"):
                            state["setup_done"] = False
                        _write_state(state)

                        # ── 4. Ausloggen & zur Startseite ──
                        app.storage.user.clear()
                        dlg.close()
                        ui.notify(
                            f'Profil "{username}" wurde vollständig gelöscht.',
                            type="positive", timeout=4000,
                        )
                        ui.navigate.to("/")

                    with ui.row().classes("gap-3 mt-4 justify-end"):
                        ui.button("Abbrechen", on_click=dlg.close).props(
                            "flat no-caps"
                        ).style("color:#9CA3AF")
                        ui.button(
                            "Profil endgültig löschen",
                            on_click=_do_delete,
                            icon="delete_forever",
                        ).style(
                            "background:#EF4444;color:white;border-radius:8px;"
                            "font-weight:700;padding:8px 20px"
                        ).props("no-caps unelevated")

                dlg.open()

            ui.button(
                "Profil löschen …",
                on_click=_open_delete_dialog,
                icon="delete_forever",
            ).style(
                "background:rgba(239,68,68,0.12);color:#EF4444;"
                "border:1px solid rgba(239,68,68,0.35);border-radius:8px;"
                "font-weight:700;padding:8px 20px"
            ).props("no-caps unelevated")
