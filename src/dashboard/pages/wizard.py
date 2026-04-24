"""Ersteinrichtung: Schritt-fuer-Schritt Wizard fuer neue Nutzer.

UI Design Overhaul: Crisp Cards, bessere Anleitung, benutzerfreundliche Sprache.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from nicegui import app, ui

from ...config import DEFAULT_CONFIG_PATH, get_ocr_languages, load_config, load_config_raw, save_config
from ...prerequisites import run_all_checks
from ..theme import callout, enable_scroll, page_header, section_title, status_badge


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _safe_port(value, default: int) -> int:
    """Konvertiert UI-Port-Eingabe sicher zu int, gibt default zurück bei Fehler."""
    try:
        return int(value or default)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Auth-Helpers
# ---------------------------------------------------------------------------

def _state_path() -> Path:
    """Fester, globaler Pfad fuer _state.json (neben config.yaml).
    Unveraenderlich – unabhaengig von user-spezifischen Archiv-Pfaden.
    """
    return DEFAULT_CONFIG_PATH.parent / "_state.json"


def _read_state() -> dict:
    p = _state_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _write_state(data: dict) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2)
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


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_login(username: str, password: str) -> bool:
    state = _read_state()
    accounts = state.get("accounts", {})
    if username not in accounts:
        return False
    return accounts[username] == _hash_pw(password)


def is_logged_in() -> bool:
    return bool(app.storage.user.get("logged_in"))


# ---------------------------------------------------------------------------
# Branchen-Templates
# ---------------------------------------------------------------------------
TEMPLATES: dict[str, dict[str, Any]] = {
    "leer": {
        "label": "Leer starten (empfohlen)",
        "icon": "add_circle_outline",
        "description": "Keine Voreinträge — du legst Dokumentenarten und Länder selbst an, sobald deine ersten Dokumente da sind.",
        "document_types": {},
        "countries": {},
    },
    "allgemein": {
        "label": "Allgemein",
        "icon": "folder",
        "description": "Rechnungen, Vertraege, Angebote, Briefe -- fuer jedes Buero geeignet.",
        "document_types": {
            "rechnung": {
                "keywords_de": ["rechnung", "invoice", "rechnungsnummer", "rechnungsbetrag"],
                "keywords_en": ["invoice", "bill", "billing"],
                "keywords_sq": ["fature", "fatura"],
            },
            "vertrag": {
                "keywords_de": ["vertrag", "vereinbarung", "vertragspartner"],
                "keywords_en": ["contract", "agreement"],
                "keywords_sq": ["kontrate", "marreveshje"],
            },
            "angebot": {
                "keywords_de": ["angebot", "kostenvoranschlag"],
                "keywords_en": ["offer", "proposal", "quotation", "quote"],
                "keywords_sq": ["oferte"],
            },
            "mahnung": {
                "keywords_de": ["mahnung", "inkasso", "forderung", "zahlungserinnerung"],
                "keywords_en": ["reminder", "collection", "debt", "overdue"],
                "keywords_sq": ["perkujtim"],
            },
            "brief": {
                "keywords_de": ["sehr geehrte", "mit freundlichen gruessen", "betreff"],
                "keywords_en": ["dear sir", "dear madam", "sincerely", "regards"],
                "keywords_sq": ["i nderuar", "me respekt"],
            },
            "bericht": {
                "keywords_de": ["bericht", "zusammenfassung", "auswertung"],
                "keywords_en": ["report", "summary", "analysis"],
                "keywords_sq": ["raport"],
            },
        },
        "countries": {},
    },
    "rechtsanwalt": {
        "label": "Rechtsanwalt / Kanzlei",
        "icon": "gavel",
        "description": "Vertraege, Schriftsaetze, Gutachten, Korrespondenz, Gerichtsurteile.",
        "document_types": {
            "vertrag": {
                "keywords_de": ["vertrag", "vereinbarung", "vertragspartner", "vertragswerk", "nachtrag"],
                "keywords_en": ["contract", "agreement", "deed"],
                "keywords_sq": ["kontrate", "marreveshje"],
            },
            "schriftsatz": {
                "keywords_de": ["schriftsatz", "klage", "klageschrift", "berufung", "antrag", "erwiderung", "replik"],
                "keywords_en": ["brief", "complaint", "motion", "pleading"],
                "keywords_sq": [],
            },
            "gutachten": {
                "keywords_de": ["gutachten", "sachverstaendiger", "bewertung", "expertise"],
                "keywords_en": ["expert opinion", "appraisal", "assessment"],
                "keywords_sq": [],
            },
            "urteil": {
                "keywords_de": ["urteil", "beschluss", "gericht", "aktenzeichen", "amtsgericht", "landgericht"],
                "keywords_en": ["judgment", "verdict", "court order", "ruling"],
                "keywords_sq": [],
            },
            "korrespondenz": {
                "keywords_de": ["sehr geehrte", "mit freundlichen gruessen", "mandant", "betreff"],
                "keywords_en": ["dear sir", "sincerely", "regards", "client"],
                "keywords_sq": [],
            },
            "vollmacht": {
                "keywords_de": ["vollmacht", "bevollmaechtigung", "prozessvollmacht"],
                "keywords_en": ["power of attorney", "authorization"],
                "keywords_sq": [],
            },
            "rechnung": {
                "keywords_de": ["rechnung", "honorar", "gebuehren", "kostenrechnung", "RVG"],
                "keywords_en": ["invoice", "fee note", "billing"],
                "keywords_sq": ["fature"],
            },
        },
        "countries": {},
    },
    "steuerberater": {
        "label": "Steuerberater / Buchhaltung",
        "icon": "calculate",
        "description": "Rechnungen, Belege, Steuerbescheide, Jahresabschluesse, Lohnabrechnungen.",
        "document_types": {
            "rechnung": {
                "keywords_de": ["rechnung", "invoice", "rechnungsnummer", "netto", "brutto", "MwSt", "USt"],
                "keywords_en": ["invoice", "bill", "billing", "VAT"],
                "keywords_sq": ["fature"],
            },
            "beleg": {
                "keywords_de": ["beleg", "quittung", "kassenbon", "kassenzettel", "ausgabe"],
                "keywords_en": ["receipt", "voucher"],
                "keywords_sq": [],
            },
            "steuerbescheid": {
                "keywords_de": ["steuerbescheid", "finanzamt", "einkommensteuerbescheid", "festsetzung"],
                "keywords_en": ["tax assessment", "tax notice"],
                "keywords_sq": [],
            },
            "jahresabschluss": {
                "keywords_de": ["jahresabschluss", "bilanz", "gewinn", "verlust", "GuV", "bilanzierung"],
                "keywords_en": ["annual report", "balance sheet", "profit and loss"],
                "keywords_sq": [],
            },
            "lohnabrechnung": {
                "keywords_de": ["lohnabrechnung", "gehaltsabrechnung", "bruttolohn", "nettolohn", "sozialversicherung"],
                "keywords_en": ["payslip", "salary statement", "payroll"],
                "keywords_sq": [],
            },
            "vertrag": {
                "keywords_de": ["vertrag", "vereinbarung", "arbeitsvertrag", "mietvertrag"],
                "keywords_en": ["contract", "agreement", "lease"],
                "keywords_sq": ["kontrate"],
            },
            "kontoauszug": {
                "keywords_de": ["kontoauszug", "bankbeleg", "ueberweisung", "lastschrift", "IBAN"],
                "keywords_en": ["bank statement", "account statement"],
                "keywords_sq": [],
            },
        },
        "countries": {},
    },
    "handwerker": {
        "label": "Handwerker / Bau",
        "icon": "construction",
        "description": "Angebote, Auftraege, Rechnungen, Lieferscheine, Abnahmeprotokolle.",
        "document_types": {
            "angebot": {
                "keywords_de": ["angebot", "kostenvoranschlag", "leistungsverzeichnis", "position", "einheitspreis"],
                "keywords_en": ["offer", "quotation", "estimate"],
                "keywords_sq": ["oferte"],
            },
            "auftrag": {
                "keywords_de": ["auftrag", "auftragsbestaetigung", "bestellung", "beauftragung"],
                "keywords_en": ["order", "order confirmation", "purchase order"],
                "keywords_sq": [],
            },
            "rechnung": {
                "keywords_de": ["rechnung", "schlussrechnung", "abschlagsrechnung", "teilrechnung", "MwSt"],
                "keywords_en": ["invoice", "final invoice", "interim invoice"],
                "keywords_sq": ["fature"],
            },
            "lieferschein": {
                "keywords_de": ["lieferschein", "lieferung", "wareneingang", "empfaenger"],
                "keywords_en": ["delivery note", "packing slip", "shipping note"],
                "keywords_sq": [],
            },
            "abnahme": {
                "keywords_de": ["abnahme", "abnahmeprotokoll", "maengel", "uebergabe", "bauabnahme"],
                "keywords_en": ["acceptance", "handover", "defect report"],
                "keywords_sq": [],
            },
            "vertrag": {
                "keywords_de": ["vertrag", "werkvertrag", "bauvertrag", "VOB"],
                "keywords_en": ["contract", "construction contract"],
                "keywords_sq": ["kontrate"],
            },
            "plan": {
                "keywords_de": ["plan", "bauplan", "grundriss", "zeichnung", "skizze"],
                "keywords_en": ["plan", "blueprint", "drawing", "layout"],
                "keywords_sq": [],
            },
        },
        "countries": {},
    },
}


def _apply_user_paths(username: str) -> None:
    """Lädt benutzerspezifische Pfade und Klassifikations-Config aus dem State."""
    try:
        state = _read_state()
        user_paths = state.get("user_dirs", {}).get(username)
        if not user_paths:
            return
        cfg = load_config_raw()
        cfg.setdefault("paths", {}).update(user_paths)
        # Benutzerspezifische Klassifikations-Config wiederherstellen
        user_config = state.get("user_config", {}).get(username, {})
        if user_config.get("document_types"):
            cfg["document_types"] = user_config["document_types"]
        if user_config.get("known_customers"):
            cfg["known_customers"] = user_config["known_customers"]
        if user_config.get("countries"):
            cfg["countries"] = user_config["countries"]
        if user_config.get("global_keywords"):
            cfg["global_keywords"] = user_config["global_keywords"]
        save_config(cfg)
    except Exception:
        pass


def is_first_run() -> bool:
    try:
        p = _state_path()
        if not p.exists():
            return True
        data = json.loads(p.read_text(encoding="utf-8"))
        return not data.get("setup_done", False)
    except Exception:
        return True


def build() -> None:
    """Wizard-Seite aufbauen."""
    cfg = load_config_raw()
    ocr_langs = cfg.get("ocr", {}).get("languages", "eng+deu+sqi")

    page_header(
        "Ersteinrichtung",
        "Richte Doc-Sorter in wenigen Schritten ein.",
    )

    enable_scroll()

    with ui.stepper().props("vertical").classes("w-full") as stepper:

        # Schritt 1: Willkommen
        with ui.step("Willkommen", icon="waving_hand"):
            ui.label(
                "Willkommen bei Doc-Sorter! "
                "Dieses Tool sortiert und benennt deine Dokumente automatisch."
            ).classes("text-base mb-4")

            callout(
                "<strong>So funktioniert es:</strong><br>"
                "1. Lege Dokumente in den Eingabe-Ordner<br>"
                "2. Doc-Sorter liest und erkennt die Inhalte<br>"
                "3. Automatische Erkennung (Typ, Kunde, Land, Datum)<br>"
                "4. Dateien werden umbenannt und sortiert abgelegt",
                "info", "auto_awesome",
            )

            # System-Check
            ui.html('<div style="height:16px"></div>', sanitize=False)
            section_title("System-Pruefung", "checklist")
            checks = run_all_checks(ocr_langs)
            all_ok = True
            for check in checks:
                with ui.row().classes("items-center gap-2 py-1"):
                    if check.ok:
                        ui.icon("check_circle").classes("text-lg text-green-500")
                    else:
                        ui.icon("error").classes("text-lg text-red-500")
                        all_ok = False
                    ui.label(check.name).classes("w-32 text-sm")
                    ui.label(check.message).classes("text-sm text-gray-500")

            if not all_ok:
                callout(
                    "Einige Voraussetzungen fehlen. Doc-Sorter funktioniert trotzdem, "
                    "aber die Texterkennung (fuer gescannte Dokumente) ist eingeschraenkt.",
                    "warning",
                )

            with ui.stepper_navigation():
                ui.button("Weiter", on_click=stepper.next, icon="arrow_forward").classes("ds-btn-primary")

        # Schritt 2: Konto erstellen
        with ui.step("Konto", icon="person_add"):

            # Benutzer-Limit anzeigen
            _state_now = _read_state()
            _existing_count = len(_state_now.get("accounts", {}))
            _slots_left = max(0, 3 - _existing_count)

            with ui.element("div").style(
                "display:flex;gap:12px;margin-bottom:20px;width:100%"
            ):
                for i in range(3):
                    _filled = i < _existing_count
                    _color = "#00d4ff" if _filled else "rgba(255,255,255,0.08)"
                    _icon = "person" if _filled else "person_outline"
                    _label = "Belegt" if _filled else ("Verfügbar" if i == _existing_count else "Frei")
                    with ui.element("div").style(
                        f"flex:1;border-radius:12px;border:1px solid {_color}40;"
                        f"background:{_color}10;padding:14px 10px;"
                        f"display:flex;flex-direction:column;align-items:center;gap:6px"
                    ):
                        ui.icon(_icon).style(f"font-size:1.8rem;color:{_color}")
                        ui.label(f"Nutzer {i+1}").style(
                            f"font-size:0.72rem;font-weight:700;color:{_color}"
                        )
                        ui.label(_label).style(
                            "font-size:0.65rem;color:var(--ds-text-2)"
                        )

            if _slots_left == 0:
                callout(
                    "Maximale Nutzeranzahl (3) erreicht. Melde dich mit einem bestehenden Konto an.",
                    "warning", "group",
                )
            else:
                _slots_suffix = "Platz verfügbar." if _slots_left == 1 else "Plätze verfügbar."
                ui.label(
                    f"Noch {_slots_left} {_slots_suffix}"
                ).style("font-size:0.8rem;color:var(--ds-text-2);margin-bottom:12px")

            reg_credentials: dict = {}

            reg_user = ui.input(
                label="Benutzername", placeholder="z.B. Max"
            ).classes("w-full ds-input mb-2").props("outlined dense")
            reg_pw = ui.input(
                label="Passwort", password=True, password_toggle_button=True,
                placeholder="Mindestens 4 Zeichen"
            ).classes("w-full ds-input mb-2").props("outlined dense")
            reg_pw2 = ui.input(
                label="Passwort bestätigen", password=True, password_toggle_button=True,
            ).classes("w-full ds-input").props("outlined dense")

            def _save_account() -> None:
                u = reg_user.value.strip()
                p = reg_pw.value
                p2 = reg_pw2.value
                if not u:
                    ui.notify("Benutzername darf nicht leer sein.", type="warning")
                    return
                if len(u) < 2:
                    ui.notify("Benutzername muss mindestens 2 Zeichen haben.", type="warning")
                    return
                if len(p) < 4:
                    ui.notify("Passwort muss mindestens 4 Zeichen haben.", type="warning")
                    return
                if p != p2:
                    ui.notify("Passwörter stimmen nicht überein.", type="warning")
                    return
                state = _read_state()
                if len(state.get("accounts", {})) >= 3:
                    ui.notify("Maximale Nutzeranzahl (3) erreicht.", type="negative")
                    return
                if u in state.get("accounts", {}):
                    ui.notify("Dieser Benutzername ist bereits vergeben.", type="negative")
                    return
                reg_credentials["username"] = u
                reg_credentials["password_hash"] = _hash_pw(p)
                stepper.next()

            with ui.stepper_navigation():
                ui.button("Zurück", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button("Weiter", on_click=_save_account, icon="arrow_forward").classes("ds-btn-primary").props(
                    f"{'disabled' if _slots_left == 0 else ''}"
                )

        # Schritt 3: Branche
        with ui.step("Branche", icon="business"):
            ui.label(
                "Waehle deine Branche. Die Dokumentenarten werden entsprechend vorkonfiguriert."
            ).classes("text-base mb-4")

            selected_template = {"value": "leer"}
            tile_refs: dict[str, ui.element] = {}
            check_refs: dict[str, ui.icon] = {}

            def _update_branch_styles() -> None:
                for k, tile in tile_refs.items():
                    if k == selected_template["value"]:
                        tile.style(
                            "border:2px solid #00d4ff;"
                            "box-shadow:0 0 18px rgba(0,212,255,0.3);"
                            "background:rgba(0,212,255,0.08);cursor:pointer;"
                            "border-radius:12px;padding:18px;transition:all 0.2s"
                        )
                        if k in check_refs:
                            check_refs[k].style("display:block")
                    else:
                        tile.style(
                            "border:1px solid rgba(255,255,255,0.1);"
                            "box-shadow:none;background:rgba(10,22,40,0.7);cursor:pointer;"
                            "border-radius:12px;padding:18px;transition:all 0.2s"
                        )
                        if k in check_refs:
                            check_refs[k].style("display:none")

            # 2-Spalten-Grid
            with ui.element("div").style(
                "display:grid;grid-template-columns:repeat(2,1fr);"
                "gap:14px;width:100%"
            ):
                for key, tmpl in TEMPLATES.items():
                    tile = ui.element("div")
                    tile_refs[key] = tile
                    with tile:
                        def _make_select(k=key):
                            def _select():
                                selected_template["value"] = k
                                _update_branch_styles()
                            return _select

                        tile.on("click", _make_select())

                        # Icon oben
                        with ui.row().classes("items-center gap-3 mb-2"):
                            ui.icon(tmpl["icon"]).style(
                                "font-size:1.6rem;color:#00d4ff;"
                                "filter:drop-shadow(0 0 6px rgba(0,212,255,0.4))"
                            )
                            ui.label(tmpl["label"]).style(
                                "font-size:0.95rem;font-weight:700;color:var(--ds-text)"
                            )
                            check = ui.icon("check_circle").style(
                                "font-size:1.1rem;color:#00d4ff;margin-left:auto;display:none"
                            )
                            check_refs[key] = check

                        ui.label(tmpl["description"]).style(
                            "font-size:0.78rem;color:var(--ds-text-2);line-height:1.4"
                        )
                        n_dt = len(tmpl.get("document_types", {}))
                        ui.label(
                            "Ohne Voreinträge — alles selbst anlegen" if n_dt == 0
                            else f"{n_dt} Dokumentenarten voreingestellt"
                        ).style("font-size:0.7rem;color:#9CA3AF;margin-top:6px")

            # Initial-Style setzen
            _update_branch_styles()

            def _apply_template() -> None:
                key = selected_template["value"]
                tmpl = TEMPLATES[key]
                cfg["document_types"] = tmpl.get("document_types", {})
                cfg["countries"] = tmpl.get("countries", {})
                ui.notify(f"Vorlage '{tmpl['label']}' geladen", type="positive")
                stepper.next()

            with ui.stepper_navigation():
                ui.button("Zurueck", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button("Vorlage laden & Weiter", on_click=_apply_template, icon="arrow_forward").classes("ds-btn-primary")

        # Schritt: Dokumentenarten
        with ui.step("Dokumentenarten", icon="description"):
            ui.label(
                "Welche Dokumentenarten soll Doc-Sorter erkennen? "
                "Die Vorlage hat bereits einige angelegt — du kannst sie anpassen oder eigene hinzufügen."
            ).style("font-size:0.9rem;color:var(--ds-text-2);margin-bottom:16px")

            doc_types: dict = cfg.setdefault("document_types", {})
            dt_container = ui.column().classes("w-full gap-2")

            def _refresh_dt() -> None:
                dt_container.clear()
                with dt_container:
                    if not doc_types:
                        ui.label("Noch keine Dokumentenarten — füge die erste unten hinzu.").style(
                            "font-size:0.8rem;color:#9CA3AF;font-style:italic;padding:4px 0"
                        )
                    for dtype, lang_kw in list(doc_types.items()):
                        with ui.element("div").style(
                            "border:1px solid rgba(0,212,255,0.2);border-radius:12px;"
                            "background:rgba(0,212,255,0.04);padding:12px 16px;width:100%"
                        ):
                            with ui.row().classes("items-center gap-2 w-full mb-2"):
                                ui.icon("description").style("color:#00d4ff;font-size:1.1rem;flex-shrink:0")
                                ui.label(dtype.title()).style(
                                    "font-size:0.88rem;font-weight:700;color:var(--ds-text);flex:1"
                                )
                                ui.button(icon="close", on_click=lambda d=dtype: (
                                    doc_types.pop(d, None), _refresh_dt()
                                )).props("round flat size=sm").style("color:#ff3366;flex-shrink:0")

                            # Keywords compact (all langs)
                            _lang_pairs = [
                                ("keywords_de", "#00d4ff", "DE"),
                                ("keywords_en", "#00e87d", "EN"),
                                ("keywords_sq", "#ff9f0a", "SQ"),
                            ]
                            for lk, lc, ll in _lang_pairs:
                                kws = lang_kw.get(lk, [])
                                if not kws:
                                    continue
                                with ui.row().classes("items-center gap-1 flex-wrap mb-1"):
                                    ui.label(ll).style(
                                        f"font-size:0.6rem;font-weight:700;padding:1px 6px;"
                                        f"border-radius:4px;background:{lc}18;color:{lc};flex-shrink:0"
                                    )
                                    for kw in kws:
                                        with ui.element("div").style(
                                            "display:inline-flex;align-items:center;gap:3px;"
                                            "padding:2px 8px;border-radius:999px;"
                                            f"background:{lc}12;border:1px solid {lc}30"
                                        ):
                                            ui.label(kw).style(f"font-size:0.72rem;color:{lc}")
                                            ui.icon("close").style(
                                                f"font-size:0.7rem;color:{lc};cursor:pointer;opacity:0.6"
                                            ).on("click", lambda k=kw, d=dtype, l=lk: (
                                                doc_types[d].__setitem__(l, [x for x in doc_types[d].get(l, []) if x != k]),
                                                _refresh_dt()
                                            ))

            _refresh_dt()

            # Add new doc type
            ui.html('<div style="height:12px"></div>', sanitize=False)
            with ui.row().classes("items-center gap-2 w-full"):
                dt_inp = ui.input(
                    label="Neue Dokumentenart",
                    placeholder="z.B. rechnung, vertrag, mahnung …"
                ).classes("flex-1 ds-input").props("outlined dense")

                async def _add_dt() -> None:
                    from .config_editor import _lookup_keywords
                    n = dt_inp.value.strip().lower()
                    if not n:
                        return
                    if n in doc_types:
                        ui.notify(f'"{n}" existiert bereits', type="warning")
                        return
                    found = _lookup_keywords(n)
                    doc_types[n] = found if found else {"keywords_de": [n], "keywords_en": [], "keywords_sq": []}
                    dt_inp.value = ""
                    _refresh_dt()
                    ui.notify(f'"{n}" hinzugefügt' + (" mit Vorschlägen" if found else ""), type="positive")

                dt_inp.on("keydown.enter", _add_dt)
                ui.button(icon="add", on_click=_add_dt).props("round dense unelevated").style(
                    "background:rgba(0,212,255,0.12);color:#00d4ff;min-width:36px;min-height:36px"
                )

            ui.label("Tipp: Schlüsselwörter werden automatisch vorgeschlagen. Alles jederzeit in den Einstellungen änderbar.").style(
                "font-size:0.7rem;color:#9CA3AF;margin-top:6px"
            )

            with ui.stepper_navigation():
                ui.button("Zurück", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button("Weiter", on_click=stepper.next, icon="arrow_forward").classes("ds-btn-primary")

        # Schritt: Länder
        with ui.step("Länder", icon="public"):
            ui.label(
                "Aus welchen Ländern kommen deine Dokumente? "
                "Doc-Sorter erkennt das Herkunftsland anhand von Städten, Ländernamen und typischen Begriffen."
            ).style("font-size:0.9rem;color:var(--ds-text-2);margin-bottom:16px")

            countries: dict = cfg.setdefault("countries", {})
            ctry_container = ui.column().classes("w-full gap-2")

            def _refresh_countries() -> None:
                ctry_container.clear()
                with ctry_container:
                    if not countries:
                        ui.label("Noch keine Länder — füge das erste Land unten hinzu.").style(
                            "font-size:0.8rem;color:#9CA3AF;font-style:italic;padding:4px 0"
                        )
                    for cname, cdata in list(countries.items()):
                        kws = cdata.get("keywords", [])
                        with ui.element("div").style(
                            "border:1px solid rgba(0,232,125,0.2);border-radius:12px;"
                            "background:rgba(0,232,125,0.04);padding:12px 16px;width:100%"
                        ):
                            with ui.row().classes("items-center gap-2 w-full mb-2"):
                                ui.icon("flag").style("color:#00e87d;font-size:1.1rem;flex-shrink:0")
                                ui.label(cname.title()).style(
                                    "font-size:0.88rem;font-weight:700;color:var(--ds-text);flex:1"
                                )
                                ui.button(icon="close", on_click=lambda c=cname: (
                                    countries.pop(c, None), _refresh_countries()
                                )).props("round flat size=sm").style("color:#ff3366;flex-shrink:0")

                            with ui.row().classes("items-center gap-1 flex-wrap"):
                                for kw in kws:
                                    with ui.element("div").style(
                                        "display:inline-flex;align-items:center;gap:3px;"
                                        "padding:2px 8px;border-radius:999px;"
                                        "background:rgba(0,232,125,0.1);border:1px solid rgba(0,232,125,0.25)"
                                    ):
                                        ui.label(kw).style("font-size:0.72rem;color:#00e87d")
                                        ui.icon("close").style(
                                            "font-size:0.7rem;color:#00e87d;cursor:pointer;opacity:0.6"
                                        ).on("click", lambda k=kw, c=cname: (
                                            countries[c].__setitem__(
                                                "keywords", [x for x in countries[c].get("keywords", []) if x != k]
                                            ), _refresh_countries()
                                        ))

                                # Inline add keyword
                                ctry_kw_inp = ui.input(placeholder="+ Begriff …").props(
                                    "outlined dense"
                                ).style("max-width:120px;font-size:0.75rem")

                                def _make_add_kw(c=cname, inp=ctry_kw_inp):
                                    def _do():
                                        parts = [p.strip() for p in inp.value.replace(";", ",").split(",") if p.strip()]
                                        existing = countries[c].setdefault("keywords", [])
                                        for p in parts:
                                            if p not in existing:
                                                existing.append(p)
                                        inp.value = ""
                                        _refresh_countries()
                                    return _do

                                ctry_kw_inp.on("keydown.enter", _make_add_kw())
                                ui.button(icon="add", on_click=_make_add_kw()).props(
                                    "round flat size=sm"
                                ).style("color:#00e87d")

            _refresh_countries()

            ui.html('<div style="height:12px"></div>', sanitize=False)
            with ui.row().classes("items-center gap-2 w-full"):
                ctry_inp = ui.input(
                    label="Land hinzufügen",
                    placeholder="z.B. deutschland, schweiz, kosovo …"
                ).classes("flex-1 ds-input").props("outlined dense")

                def _add_country() -> None:
                    n = ctry_inp.value.strip().lower()
                    if not n:
                        return
                    if n in countries:
                        ui.notify(f'"{n}" existiert bereits', type="warning")
                        return
                    countries[n] = {"keywords": [n]}
                    ctry_inp.value = ""
                    _refresh_countries()

                ctry_inp.on("keydown.enter", _add_country)
                ui.button(icon="add", on_click=_add_country).props("round dense unelevated").style(
                    "background:rgba(0,232,125,0.12);color:#00e87d;min-width:36px;min-height:36px"
                )

            ui.label("Erkennungsbegriffe: Städte, Ländernamen in anderen Sprachen, typische Abkürzungen.").style(
                "font-size:0.7rem;color:#9CA3AF;margin-top:6px"
            )

            with ui.stepper_navigation():
                ui.button("Zurück", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button("Weiter", on_click=stepper.next, icon="arrow_forward").classes("ds-btn-primary")

        # Schritt: Benennung
        with ui.step("Benennung", icon="drive_file_rename_outline"):
            ui.label(
                "Wie sollen erkannte Dokumente benannt und in Ordner einsortiert werden? "
                "Die Platzhalter in {} werden automatisch durch erkannte Werte ersetzt."
            ).style("font-size:0.9rem;color:var(--ds-text-2);margin-bottom:16px")

            taxonomy: dict = cfg.setdefault("taxonomy", {
                "filename_pattern": "{dokumentenart}_{kunde}_{land}_{datum}",
                "folder_pattern":   "{dokumentenart}/{land}/{kunde}/{jahr}",
            })

            # Muster-Inputs
            fn_inp = ui.input(
                label="Dateiname-Muster",
                value=taxonomy.get("filename_pattern", "{dokumentenart}_{kunde}_{land}_{datum}"),
            ).classes("w-full ds-input").props("outlined dense")
            ui.label("Platzhalter: {dokumentenart}  {kunde}  {land}  {datum}").style(
                "font-size:0.7rem;color:#9CA3AF;margin-bottom:10px;margin-top:2px"
            )

            folder_inp = ui.input(
                label="Ordner-Muster",
                value=taxonomy.get("folder_pattern", "{dokumentenart}/{land}/{kunde}/{jahr}"),
            ).classes("w-full ds-input").props("outlined dense")
            ui.label("Platzhalter: {dokumentenart}  {land}  {kunde}  {jahr}  (/ erzeugt Unterordner)").style(
                "font-size:0.7rem;color:#9CA3AF;margin-bottom:14px;margin-top:2px"
            )

            # Live-Vorschau
            preview_box = ui.element("div").style(
                "border:1px solid rgba(0,212,255,0.2);border-radius:12px;"
                "background:rgba(0,212,255,0.04);padding:14px 16px;width:100%"
            )

            def _update_tax_preview() -> None:
                from datetime import datetime as _dt
                sample = {
                    "dokumentenart": "rechnung", "kunde": "GASAG",
                    "land": "deutschland",
                    "datum": _dt.now().strftime("%d.%m.%y"),
                    "jahr": _dt.now().strftime("%Y"),
                }
                try:
                    fn_ex = fn_inp.value.format(**sample) + ".pdf"
                    fd_ex = folder_inp.value.format(**sample)
                except (KeyError, ValueError):
                    fn_ex = "(Muster ungültig)"
                    fd_ex = "(Muster ungültig)"
                preview_box.clear()
                with preview_box:
                    ui.label("Beispiel-Vorschau (Rechnung von GASAG):").style(
                        "font-size:0.68rem;font-weight:700;color:#00d4ff;"
                        "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px"
                    )
                    with ui.element("div").style("font-family:monospace;font-size:0.82rem"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("folder_open").style("color:#ff9f0a;font-size:1rem")
                            ui.label("archive/").style("color:var(--ds-text-2)")
                        with ui.row().classes("items-center gap-2").style("margin-left:20px"):
                            ui.icon("folder").style("color:#ff9f0a;font-size:1rem")
                            ui.label(fd_ex + "/").style("color:#00d4ff")
                        with ui.row().classes("items-center gap-2").style("margin-left:40px"):
                            ui.icon("description").style("color:#a78bfa;font-size:1rem")
                            ui.label(fn_ex).style("color:var(--ds-text);font-weight:700")

            _update_tax_preview()
            fn_inp.on("keyup", lambda _: (
                taxonomy.update({"filename_pattern": fn_inp.value}),
                _update_tax_preview()
            ))
            folder_inp.on("keyup", lambda _: (
                taxonomy.update({"folder_pattern": folder_inp.value}),
                _update_tax_preview()
            ))

            def _save_taxonomy() -> None:
                taxonomy["filename_pattern"] = fn_inp.value
                taxonomy["folder_pattern"]   = folder_inp.value
                stepper.next()

            with ui.stepper_navigation():
                ui.button("Zurück", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button("Weiter", on_click=_save_taxonomy, icon="arrow_forward").classes("ds-btn-primary")

        # Schritt 3: Pfade
        with ui.step("Pfade", icon="folder"):

            # Visuelle Erklärung — Kacheln
            _path_cards = [
                ("inbox",   "📥", "Eingang",  "Hier legst du neue Dokumente ab.",          "#00d4ff"),
                ("archive", "📁", "Archiv",   "Sortierte Dokumente landen hier.",            "#00e87d"),
                ("review",  "🔍", "Prüfung",  "Dokumente die du manuell prüfen möchtest.",   "#ff9f0a"),
                ("logs",    "📋", "Protokoll","Verarbeitungs-History wird hier gespeichert.", "#a78bfa"),
            ]

            with ui.element("div").style(
                "display:grid;grid-template-columns:repeat(2,1fr);gap:12px;width:100%;margin-bottom:16px"
            ):
                for _key, _emoji, _title, _desc, _color in _path_cards:
                    with ui.element("div").style(
                        f"border-radius:12px;border:1px solid {_color}30;"
                        f"background:{_color}08;padding:16px;display:flex;flex-direction:column;gap:6px"
                    ):
                        ui.label(_emoji).style("font-size:1.8rem;line-height:1")
                        ui.label(_title).style(
                            f"font-size:0.9rem;font-weight:700;color:{_color}"
                        )
                        ui.label(_desc).style(
                            "font-size:0.75rem;color:var(--ds-text-2);line-height:1.4"
                        )

            ui.label(
                "✅ Die Ordner werden automatisch für dich angelegt. Du musst nichts manuell erstellen."
            ).style("font-size:0.82rem;color:var(--ds-text-2);margin-bottom:8px")

            # Erweiterte Pfad-Einstellungen (eingeklappt)
            from ...config import _DEFAULTS as _PATH_DEFAULTS
            _default_paths = {k: str(Path(v).expanduser()) for k, v in _PATH_DEFAULTS["paths"].items()}
            paths = cfg.setdefault("paths", {})
            path_inputs: dict[str, ui.input] = {}

            with ui.expansion("Erweiterte Einstellungen (für Profis)", icon="settings").style(
                "border:1px solid rgba(255,255,255,0.07);border-radius:10px;width:100%"
            ):
                ui.label("Hier kannst du die Ordnerpfade manuell anpassen.").style(
                    "font-size:0.75rem;color:var(--ds-text-2);margin-bottom:8px"
                )
                _path_labels = {
                    "inbox":   ("Eingabe-Ordner", "Wo neue Dokumente abgelegt werden"),
                    "archive": ("Archiv-Ordner",  "Wo sortierte Dokumente gespeichert werden"),
                    "logs":    ("Protokoll-Ordner","Wo Logs gespeichert werden"),
                    "review":  ("Prüfungs-Ordner", "Wo unsichere Dokumente abgelegt werden"),
                }
                for key, (label, hint) in _path_labels.items():
                    path_inputs[key] = ui.input(
                        label=label, value=_default_paths.get(key, ""),
                        validation={"Darf nicht leer sein": lambda v: bool(v and v.strip())},
                    ).classes("w-full ds-input").props("outlined dense")
                    ui.label(hint).style("font-size:0.68rem;color:#9CA3AF;margin-bottom:8px;margin-top:-4px")

            def _save_paths() -> None:
                for key, inp in path_inputs.items():
                    paths[key] = inp.value
                stepper.next()

            with ui.stepper_navigation():
                ui.button("Zurück", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button("Weiter", on_click=_save_paths, icon="arrow_forward").classes("ds-btn-primary")

        # Schritt 4: Kunden
        with ui.step("Kunden", icon="people"):
            ui.label(
                "Füge deine Kunden oder Vertragspartner hinzu — Doc-Sorter erkennt sie dann automatisch in Dokumenten."
            ).style("font-size:0.9rem;color:var(--ds-text-2);margin-bottom:16px")

            # Beispiel-Karte (nur Illustration, nicht editierbar)
            with ui.element("div").style(
                "border:1px dashed rgba(0,212,255,0.3);border-radius:12px;"
                "background:rgba(0,212,255,0.04);padding:14px 16px;margin-bottom:16px;width:100%"
            ):
                ui.label("Beispiel — so sieht ein Kunde aus:").style(
                    "font-size:0.68rem;font-weight:700;color:#00d4ff;text-transform:uppercase;"
                    "letter-spacing:0.06em;margin-bottom:10px"
                )
                with ui.row().classes("items-center gap-4 w-full"):
                    with ui.element("div").style(
                        "width:44px;height:44px;border-radius:10px;"
                        "background:rgba(0,212,255,0.12);border:1px solid rgba(0,212,255,0.3);"
                        "display:flex;align-items:center;justify-content:center;flex-shrink:0"
                    ):
                        ui.icon("business").style("font-size:1.4rem;color:#00d4ff")
                    with ui.column().classes("gap-0 flex-1"):
                        ui.label("Mustermann GmbH").style(
                            "font-size:0.9rem;font-weight:700;color:var(--ds-text)"
                        )
                        ui.label("Musterstraße 1 · 10115 Berlin").style(
                            "font-size:0.75rem;color:var(--ds-text-2)"
                        )
                    with ui.element("div").style(
                        "background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.25);"
                        "border-radius:6px;padding:3px 10px"
                    ):
                        ui.label("Erkannt ✓").style(
                            "font-size:0.68rem;font-weight:700;color:#00d4ff"
                        )

            # Kundenliste (startet leer)
            customers: list[dict] = []
            cfg["known_customers"] = customers
            cust_container = ui.column().classes("w-full gap-3")

            def _refresh_customers() -> None:
                cust_container.clear()
                with cust_container:
                    if not customers:
                        ui.label("Noch keine Kunden hinzugefügt.").style(
                            "font-size:0.8rem;color:#9CA3AF;font-style:italic;padding:4px 0"
                        )
                        return
                    for i, c in enumerate(customers):
                        with ui.element("div").style(
                            "border:1px solid rgba(0,232,125,0.2);border-radius:12px;"
                            "background:rgba(0,232,125,0.04);padding:12px 16px;width:100%"
                        ):
                            with ui.row().classes("items-center gap-3 w-full"):
                                with ui.element("div").style(
                                    "width:38px;height:38px;border-radius:8px;"
                                    "background:rgba(0,232,125,0.12);border:1px solid rgba(0,232,125,0.3);"
                                    "display:flex;align-items:center;justify-content:center;flex-shrink:0"
                                ):
                                    ui.icon("business").style("font-size:1.1rem;color:#00e87d")
                                with ui.column().classes("gap-0 flex-1 min-w-0"):
                                    ui.label(c.get("name", "")).style(
                                        "font-size:0.88rem;font-weight:700;color:var(--ds-text)"
                                    )
                                    meta = " · ".join(filter(None, [
                                        c.get("address", ""), c.get("phone", "")
                                    ]))
                                    if meta:
                                        ui.label(meta).style(
                                            "font-size:0.72rem;color:var(--ds-text-2);"
                                            "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                                        )
                                ui.button(
                                    icon="close",
                                    on_click=lambda idx=i: (_remove_customer(idx)),
                                ).props("round flat size=sm").style("color:#ff3366;flex-shrink:0")

            def _remove_customer(idx: int) -> None:
                if 0 <= idx < len(customers):
                    customers.pop(idx)
                    _refresh_customers()

            _refresh_customers()

            # Formular: neuen Kunden hinzufügen
            with ui.element("div").style(
                "border:1px solid rgba(255,255,255,0.08);border-radius:12px;"
                "background:rgba(10,22,40,0.6);padding:16px;margin-top:8px;width:100%"
            ):
                ui.label("Kunden hinzufügen").style(
                    "font-size:0.8rem;font-weight:700;color:var(--ds-text);margin-bottom:12px"
                )
                with ui.element("div").style(
                    "display:grid;grid-template-columns:1fr 1fr;gap:10px;width:100%"
                ):
                    new_name    = ui.input(label="Name *",    placeholder="z.B. GASAG AG").props("outlined dense")
                    new_address = ui.input(label="Adresse",   placeholder="z.B. Musterstr. 1, Berlin").props("outlined dense")
                    new_phone   = ui.input(label="Telefon",   placeholder="z.B. +49 30 123456").props("outlined dense")
                    new_aliases = ui.input(label="Erkennungsbegriffe", placeholder="z.B. GASAG, GASAG AG").props("outlined dense")

                def _add_customer() -> None:
                    name = new_name.value.strip()
                    if not name:
                        ui.notify("Name darf nicht leer sein", type="warning")
                        return
                    aliases = [a.strip() for a in new_aliases.value.split(",") if a.strip()]
                    if not aliases:
                        aliases = [name]
                    customers.append({
                        "name":    name,
                        "aliases": aliases,
                        "address": new_address.value.strip(),
                        "phone":   new_phone.value.strip(),
                    })
                    for inp in (new_name, new_address, new_phone, new_aliases):
                        inp.value = ""
                    _refresh_customers()

                ui.button("Hinzufügen", on_click=_add_customer, icon="add").classes(
                    "ds-btn-primary mt-3"
                ).props("dense unelevated no-caps")

            ui.label("Kunden kannst du jederzeit in den Einstellungen ergänzen oder ändern.").style(
                "font-size:0.72rem;color:#9CA3AF;margin-top:10px"
            )

            with ui.stepper_navigation():
                ui.button("Zurück", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button("Weiter", on_click=stepper.next, icon="arrow_forward").classes("ds-btn-primary")

        # Schritt 5: Schlagworte
        with ui.step("Schlagworte", icon="label"):
            ui.label(
                "Definiere Schlüsselbegriffe, die das System überall erkennen soll — in Dokumenten, "
                "E-Mails und Nachrichten. Sie fließen direkt in den lernenden Assistenten ein."
            ).style("font-size:0.9rem;color:var(--ds-text-2);margin-bottom:16px")

            global_keywords: list[str] = []
            cfg["global_keywords"] = global_keywords

            kw_chips_wrap = ui.element("div").style(
                "display:flex;flex-wrap:wrap;gap:8px;min-height:52px;padding:12px;"
                "border:1px solid rgba(255,255,255,0.1);border-radius:10px;"
                "background:rgba(10,22,40,0.5);margin-bottom:12px;width:100%"
            )
            _KW_COLORS = ["#00d4ff", "#a78bfa", "#00e87d", "#ff9f0a", "#ff3366"]

            def _refresh_kw_chips() -> None:
                kw_chips_wrap.clear()
                with kw_chips_wrap:
                    if not global_keywords:
                        ui.label("Noch keine Schlagworte …").style(
                            "font-size:0.78rem;color:#6B7280;font-style:italic;padding:4px 0"
                        )
                        return
                    for idx, kw in enumerate(global_keywords):
                        c = _KW_COLORS[idx % len(_KW_COLORS)]
                        with ui.element("div").style(
                            f"display:inline-flex;align-items:center;gap:6px;"
                            f"padding:5px 12px;border-radius:999px;"
                            f"background:{c}18;border:1px solid {c}40"
                        ):
                            ui.label(kw).style(
                                f"font-size:0.82rem;font-weight:600;color:{c}"
                            )
                            ui.icon("close").style(
                                f"font-size:0.88rem;color:{c};cursor:pointer;opacity:0.75"
                            ).on("click", lambda kw_=kw: _remove_kw(kw_))

            def _remove_kw(kw: str) -> None:
                if kw in global_keywords:
                    global_keywords.remove(kw)
                    _refresh_kw_chips()

            def _add_kw() -> None:
                raw = kw_input.value.strip()
                if not raw:
                    return
                added = 0
                for part in [k.strip() for k in raw.replace(";", ",").split(",") if k.strip()]:
                    if part and part.lower() not in [k.lower() for k in global_keywords]:
                        global_keywords.append(part)
                        added += 1
                kw_input.value = ""
                if added:
                    _refresh_kw_chips()

            _refresh_kw_chips()

            with ui.row().classes("items-center gap-2 w-full"):
                kw_input = ui.input(
                    label="Schlagwort eingeben",
                    placeholder="z.B. Mahnung, Frist, dringend …"
                ).classes("flex-1 ds-input").props("outlined dense")
                kw_input.on("keydown.enter", _add_kw)
                ui.button(icon="add", on_click=_add_kw).props("round dense unelevated").style(
                    "background:rgba(0,212,255,0.12);color:#00d4ff;min-width:36px;min-height:36px"
                )

            ui.label('Mehrere Begriffe mit Komma trennen: „Frist, Deadline, dringend"').style(
                "font-size:0.7rem;color:#9CA3AF;margin-top:4px;margin-bottom:12px"
            )

            # Vorschläge nach Branche
            _KW_SUGGESTIONS: dict[str, list[str]] = {
                "allgemein":     ["Rechnung", "Mahnung", "Vertrag", "Angebot", "Frist", "dringend", "Zahlung", "Termin"],
                "rechtsanwalt":  ["Klage", "Frist", "Urteil", "Mandant", "Vollmacht", "Aktenzeichen", "Termin", "Verhandlung"],
                "steuerberater": ["Steuerbescheid", "Finanzamt", "Frist", "Bilanz", "USt", "Jahresabschluss", "Belege", "Abgabe"],
                "handwerker":    ["Auftrag", "Abnahme", "Baustelle", "Liefertermin", "Gewährleistung", "VOB", "Mängel", "Abschlag"],
                "arzt":          ["Patient", "Befund", "Rezept", "Überweisung", "Termin", "Diagnose", "Krankenkasse"],
            }
            _branch_key = selected_template.get("value", "allgemein")
            _sugg_list  = _KW_SUGGESTIONS.get(_branch_key, _KW_SUGGESTIONS["allgemein"])

            with ui.expansion("Vorschläge für deine Branche", icon="tips_and_updates").style(
                "border:1px solid rgba(255,255,255,0.07);border-radius:10px;width:100%"
            ):
                ui.label("Klicke auf einen Vorschlag, um ihn hinzuzufügen.").style(
                    "font-size:0.72rem;color:#9CA3AF;margin-bottom:8px"
                )
                with ui.element("div").style(
                    "display:flex;flex-wrap:wrap;gap:8px;padding:4px 0"
                ):
                    for _s in _sugg_list:
                        def _make_sugg_handler(_kw=_s):
                            def _do():
                                if _kw.lower() not in [k.lower() for k in global_keywords]:
                                    global_keywords.append(_kw)
                                    _refresh_kw_chips()
                            return _do
                        with ui.element("div").style(
                            "display:inline-flex;align-items:center;gap:5px;"
                            "padding:5px 12px;border-radius:999px;cursor:pointer;"
                            "background:rgba(255,255,255,0.05);"
                            "border:1px solid rgba(255,255,255,0.12)"
                        ).on("click", _make_sugg_handler(_s)):
                            ui.icon("add").style("font-size:0.78rem;color:#9CA3AF")
                            ui.label(_s).style("font-size:0.8rem;color:var(--ds-text-2)")

            callout(
                "Schlagworte werden als Lernfutter für den KI-Assistenten verwendet — "
                "je mehr du eingibst, desto präziser wird die Erkennung in Dokumenten und E-Mails.",
                "info", "psychology",
            )

            ui.label("Schlagworte können jederzeit in den Einstellungen angepasst werden.").style(
                "font-size:0.72rem;color:#9CA3AF;margin-top:10px"
            )

            with ui.stepper_navigation():
                ui.button("Zurück", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button("Weiter", on_click=stepper.next, icon="arrow_forward").classes("ds-btn-primary")

        # Schritt: E-Mail & Nachrichten (optional)
        with ui.step("E-Mail & Nachrichten", icon="mail"):
            ui.label(
                "Verbinde dein E-Mail-Postfach oder einen Messenger — dann erkennt Doc-Sorter "
                "auch eingehende Dokumente per Mail automatisch."
            ).style("font-size:0.9rem;color:var(--ds-text-2);margin-bottom:4px")

            ui.label("Dieser Schritt ist optional — du kannst ihn jederzeit in den Einstellungen nachholen.").style(
                "font-size:0.78rem;color:#ff9f0a;margin-bottom:16px;display:flex;align-items:center;gap:4px"
            )

            # Provider-Kacheln
            _email_providers = [
                ("gmail",   "📧", "Gmail",           "imap.gmail.com",        993, "smtp.gmail.com",        587),
                ("outlook", "📧", "Outlook / M365",  "outlook.office365.com", 993, "smtp.office365.com",    587),
                ("gmx",     "📧", "GMX / Web.de",    "imap.gmx.net",          993, "mail.gmx.net",          587),
                ("custom",  "⚙️", "Eigener Server",  "",                      993, "",                      587),
            ]
            email_sel = {"provider": None}
            email_tile_refs: dict[str, ui.element] = {}

            with ui.element("div").style(
                "display:grid;grid-template-columns:repeat(2,1fr);gap:10px;width:100%;margin-bottom:14px"
            ):
                for pid, emoji, plabel, _ih, _ip, _sh, _sp in _email_providers:
                    tile = ui.element("div").style(
                        "border:1px solid rgba(255,255,255,0.08);border-radius:12px;"
                        "background:rgba(10,22,40,0.7);padding:14px;cursor:pointer;transition:all 0.2s"
                    )
                    email_tile_refs[pid] = tile
                    with tile:
                        ui.label(f"{emoji}  {plabel}").style(
                            "font-size:0.85rem;font-weight:700;color:var(--ds-text)"
                        )

                    def _make_email_select(p=pid, ih=_ih, ip=_ip, sh=_sh, sp=_sp):
                        def _sel():
                            email_sel["provider"] = p
                            for k, t in email_tile_refs.items():
                                t.style(
                                    "border:2px solid #00d4ff;background:rgba(0,212,255,0.08);border-radius:12px;"
                                    "padding:14px;cursor:pointer;transition:all 0.2s" if k == p
                                    else "border:1px solid rgba(255,255,255,0.08);border-radius:12px;"
                                    "background:rgba(10,22,40,0.7);padding:14px;cursor:pointer;transition:all 0.2s"
                                )
                            email_host_imap.value = ih
                            email_port_imap.value = str(ip)
                            email_host_smtp.value = sh
                            email_port_smtp.value = str(sp)
                        return _sel
                    tile.on("click", _make_email_select())

            # Formular
            email_form = ui.element("div").style(
                "border:1px solid rgba(255,255,255,0.08);border-radius:12px;"
                "background:rgba(10,22,40,0.5);padding:16px;width:100%"
            )
            with email_form:
                ui.label("Zugangsdaten").style(
                    "font-size:0.75rem;font-weight:700;color:var(--ds-text-2);"
                    "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px"
                )
                with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:10px;width:100%"):
                    email_user = ui.input(label="E-Mail-Adresse *", placeholder="dein@postfach.de").props("outlined dense")
                    email_pw   = ui.input(label="Passwort / App-Passwort *", password=True,
                                         password_toggle_button=True).props("outlined dense")
                    email_host_imap = ui.input(label="IMAP Host",  placeholder="imap.example.com").props("outlined dense")
                    email_port_imap = ui.input(label="IMAP Port",  value="993").props("outlined dense")
                    email_host_smtp = ui.input(label="SMTP Host",  placeholder="smtp.example.com").props("outlined dense")
                    email_port_smtp = ui.input(label="SMTP Port",  value="587").props("outlined dense")

            email_accounts: list = cfg.setdefault("email_accounts", [])
            email_added_label = ui.label("").style("font-size:0.8rem;color:#00e87d;margin-top:6px")

            def _add_email_account() -> None:
                u = email_user.value.strip()
                p = email_pw.value
                ih = email_host_imap.value.strip()
                sh = email_host_smtp.value.strip()
                if not u or not p or not ih:
                    ui.notify("E-Mail-Adresse, Passwort und IMAP-Host sind erforderlich.", type="warning")
                    return
                account = {
                    "email": u, "password": p,
                    "imap_host": ih, "imap_port": _safe_port(email_port_imap.value, 993),
                    "smtp_host": sh, "smtp_port": _safe_port(email_port_smtp.value, 587),
                    "enabled": True,
                }
                email_accounts.append(account)
                email_user.value = email_pw.value = ""
                email_added_label.set_text(f"✅ {u} hinzugefügt")
                ui.notify(f"{u} verbunden", type="positive")

            with ui.row().classes("gap-2 mt-3"):
                ui.button("Postfach verbinden", on_click=_add_email_account, icon="link").classes("ds-btn-secondary")

            with ui.expansion("💡 Wie bekomme ich ein App-Passwort?", icon="help_outline").style(
                "border:1px solid rgba(255,255,255,0.07);border-radius:10px;width:100%;margin-top:12px"
            ):
                for step, text in [
                    ("Gmail",   "Google-Konto → Sicherheit → 2-Schritt-Verifizierung → App-Passwörter → 'Mail' wählen"),
                    ("Outlook", "Microsoft-Konto → Sicherheit → App-Kennwörter → Neues App-Kennwort erstellen"),
                    ("GMX",     "GMX → Einstellungen → E-Mail → Sicherheit → App-spezifische Passwörter"),
                ]:
                    with ui.row().classes("items-start gap-3 py-1"):
                        ui.label(step).style(
                            "font-size:0.68rem;font-weight:700;padding:2px 8px;border-radius:4px;"
                            "background:rgba(0,212,255,0.12);color:#00d4ff;flex-shrink:0;min-width:60px;text-align:center"
                        )
                        ui.label(text).style("font-size:0.78rem;color:var(--ds-text-2);line-height:1.5")

            with ui.stepper_navigation():
                ui.button("Zurück", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button("Überspringen", on_click=stepper.next, icon="skip_next").classes("ds-btn-ghost")
                ui.button("Weiter", on_click=stepper.next, icon="arrow_forward").classes("ds-btn-primary")

        # Schritt 6: Fertig
        with ui.step("Fertig", icon="check_circle"):
            ui.label("Alles eingerichtet!").classes("text-2xl font-bold mb-4")

            callout(
                "<strong>Zusammenfassung:</strong><br>"
                f"Eingabe-Ordner: {cfg.get('paths', {}).get('inbox', '?')}<br>"
                f"Ausgabe-Ordner: {cfg.get('paths', {}).get('archive', '?')}<br>"
                f"Dokumentenarten: {len(cfg.get('document_types', {}))}<br>"
                f"Länder: {len(cfg.get('countries', {}))}<br>"
                f"Kunden: {len(cfg.get('known_customers', []))}<br>"
                f"E-Mail-Konten: {len(cfg.get('email_accounts', []))}<br>"
                f"Dateiname-Muster: {cfg.get('taxonomy', {}).get('filename_pattern', '—')}",
                "success", "check_circle",
            )

            def _finish() -> None:
                username = reg_credentials.get("username", "default")

                # Immer das feste Basis-Verzeichnis aus den Defaults nutzen,
                # damit kein Pfad-Nesting entsteht wenn mehrere User sich registrieren.
                from ...config import _DEFAULTS
                archive_base = Path(_DEFAULTS["paths"]["archive"]).expanduser().parent
                # archive_base = z.B. ~/Documents/DocSorter  (Eltern-Ordner von "output")

                # --- Benutzerspezifische Ordner anlegen ---
                user_dir = archive_base / "users" / username
                user_paths = {
                    "inbox":   str(user_dir / "inbox"),
                    "archive": str(user_dir / "output"),
                    "logs":    str(user_dir / "logs"),
                    "review":  str(user_dir / "_review"),
                }
                for p in user_paths.values():
                    Path(p).expanduser().mkdir(parents=True, exist_ok=True)

                # --- Config auf User-Pfade umstellen und speichern ---
                cfg.setdefault("paths", {}).update(user_paths)
                save_config(cfg)

                # --- State: setup_done + Account + user_paths ---
                from datetime import date as _date
                existing = _read_state()
                existing["setup_done"] = True
                if reg_credentials:
                    existing.setdefault("accounts", {})[username] = reg_credentials["password_hash"]
                existing.setdefault("user_dirs", {})[username] = user_paths
                existing.setdefault("created_at", {})[username] = _date.today().strftime("%d.%m.%Y")
                existing.setdefault("plans", {})[username] = "free"
                # Benutzerspezifische Klassifikations-Config speichern
                existing.setdefault("user_config", {})[username] = {
                    "document_types":  cfg.get("document_types", {}),
                    "known_customers": cfg.get("known_customers", []),
                    "countries":       cfg.get("countries", {}),
                    "global_keywords": cfg.get("global_keywords", []),
                    "taxonomy":        cfg.get("taxonomy", {}),
                }
                _write_state(existing)

                # Schlagworte ins Gehirn (user_profile) als global_keywords schreiben
                try:
                    from ...user_profile import add_global_keywords as _add_kws
                    _add_kws(cfg.get("global_keywords", []))
                except Exception:
                    pass

                # Direkt einloggen
                if reg_credentials:
                    app.storage.user["logged_in"] = True
                    app.storage.user["username"] = username
                ui.notify("Einrichtung abgeschlossen! Einstellungen gespeichert.", type="positive")
                ui.navigate.to("/")

            with ui.card().classes("ds-card w-full mt-4"):
                section_title("Naechste Schritte", "rocket_launch")
                steps = [
                    "Lege ein paar Test-Dokumente in den Eingabe-Ordner",
                    "Gehe zum Terminal und starte eine Vorschau",
                    "Pruefe die Ergebnisse -- passe ggf. Schluesselwoerter an",
                    "Starte 'Jetzt sortieren' um die Dateien zu verarbeiten",
                ]
                for i, step in enumerate(steps, 1):
                    with ui.row().classes("items-center gap-3 py-1"):
                        status_badge(str(i), "info")
                        ui.label(step).classes("text-sm")

            with ui.stepper_navigation():
                ui.button("Zurueck", on_click=stepper.previous, icon="arrow_back").classes("ds-btn-ghost")
                ui.button(
                    "Einrichtung abschliessen", on_click=_finish, icon="check",
                ).classes("ds-btn-success text-lg")


def build_login() -> None:
    """Login-Seite fuer bereits registrierte Nutzer."""
    enable_scroll()

    with ui.column().classes("items-center justify-center w-full min-h-screen gap-6"):
        with ui.card().classes("w-full max-w-sm p-8 shadow-xl rounded-2xl"):
            with ui.column().classes("items-center gap-2 mb-6"):
                ui.icon("folder_special").classes("text-5xl text-blue-500")
                ui.label("Doc-Sorter").classes("text-2xl font-bold")
                ui.label("Willkommen zurueck").classes("text-sm text-gray-500")

            login_user = ui.input(label="Benutzername").classes("w-full ds-input")
            login_pw = ui.input(
                label="Passwort", password=True, password_toggle_button=True,
            ).classes("w-full ds-input mt-2")

            error_label = ui.label("").classes("text-red-500 text-sm hidden")

            def _do_login() -> None:
                u = login_user.value.strip()
                p = login_pw.value
                if verify_login(u, p):
                    app.storage.user["logged_in"] = True
                    app.storage.user["username"] = u
                    # User-spezifische Pfade in Config laden
                    _apply_user_paths(u)
                    ui.navigate.to("/")
                else:
                    error_label.text = "Benutzername oder Passwort falsch."
                    error_label.classes(remove="hidden")

            login_pw.on("keydown.enter", _do_login)

            ui.button("Anmelden", on_click=_do_login, icon="login").classes(
                "ds-btn-primary w-full mt-4"
            )
