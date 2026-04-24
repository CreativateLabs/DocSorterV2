"""Einstellungen: Config-YAML ueber Formulare bearbeiten.

UI Design Overhaul:
- Nicht-technische Sprache (OCR -> Texterkennung, LLM -> KI-Unterstuetzung, etc.)
- Crisp Buttons und Karten
- Konsistentes Tailwind-Design
"""

from __future__ import annotations

import copy
from datetime import datetime
from pathlib import Path
from typing import Any

from nicegui import ui

from ...config import load_config_raw, save_config
from ..theme import callout, page_header, section_title


def _notify_saved(section: str) -> None:
    ui.notify(f"{section} gespeichert!", type="positive", position="top")


# ---------------------------------------------------------------------------
# Eingebautes Schlüsselwort-Wörterbuch (Dokumentenart → DE / EN / SQ)
# ---------------------------------------------------------------------------
_KEYWORD_DICT: dict[str, dict[str, list[str]]] = {
    "rechnung": {
        "keywords_de": ["rechnung", "rechnungsnummer", "rechnungsbetrag", "invoice", "MwSt", "USt", "netto", "brutto", "zahlbar", "fällig", "gesamtbetrag"],
        "keywords_en": ["invoice", "bill", "billing", "payment due", "amount due", "total amount", "VAT"],
        "keywords_sq": ["fature", "fatura", "faturë", "TVSH", "shuma totale", "pagesa"],
    },
    "vertrag": {
        "keywords_de": ["vertrag", "vereinbarung", "vertragspartner", "unterzeichnet", "vertragswerk", "laufzeit", "kündigung", "parteien"],
        "keywords_en": ["contract", "agreement", "signed", "parties", "term", "termination", "clause"],
        "keywords_sq": ["kontratë", "kontrate", "marreveshje", "nënshkruar", "palët", "afati"],
    },
    "mahnung": {
        "keywords_de": ["mahnung", "zahlungserinnerung", "zahlungsverzug", "inkasso", "forderung", "überfällig", "offener betrag", "letzte mahnung"],
        "keywords_en": ["reminder", "dunning", "overdue", "collection", "payment reminder", "outstanding", "debt"],
        "keywords_sq": ["kujtesë pagese", "perkujtim", "paralajmërim", "detyrim", "i papaguar"],
    },
    "angebot": {
        "keywords_de": ["angebot", "kostenvoranschlag", "angebotsnummer", "unverbindlich", "leistungsverzeichnis", "gültig bis"],
        "keywords_en": ["offer", "proposal", "quotation", "quote", "estimate", "valid until"],
        "keywords_sq": ["ofertë", "oferte", "propozim", "vlerësim", "vlefshme deri"],
    },
    "brief": {
        "keywords_de": ["sehr geehrte", "mit freundlichen grüßen", "betreff", "hiermit", "zu ihrer information", "wir teilen mit"],
        "keywords_en": ["dear sir", "dear madam", "sincerely", "regards", "yours faithfully", "please find enclosed"],
        "keywords_sq": ["i nderuar", "me respekt", "ju njoftojmë", "lidhur me"],
    },
    "bericht": {
        "keywords_de": ["bericht", "zusammenfassung", "auswertung", "protokoll", "ergebnis", "feststellung", "empfehlung"],
        "keywords_en": ["report", "summary", "analysis", "review", "findings", "recommendation", "assessment"],
        "keywords_sq": ["raport", "përmbledhje", "analizë", "gjetje", "rekomandim"],
    },
    "lieferschein": {
        "keywords_de": ["lieferschein", "lieferung", "empfänger", "wareneingang", "versand", "menge", "artikel"],
        "keywords_en": ["delivery note", "packing slip", "shipping note", "dispatch note", "goods received"],
        "keywords_sq": ["faturë dërgese", "dërgesë", "marrës", "mallra"],
    },
    "quittung": {
        "keywords_de": ["quittung", "beleg", "kassenbon", "kassenzettel", "erhalten", "bar bezahlt", "zahlungsbeleg"],
        "keywords_en": ["receipt", "voucher", "proof of payment", "cash receipt", "paid"],
        "keywords_sq": ["faturë pagese", "kupon", "faturë arkë", "paguar"],
    },
    "kontoauszug": {
        "keywords_de": ["kontoauszug", "IBAN", "überweisung", "lastschrift", "saldo", "kontonummer", "buchung", "wertstellung"],
        "keywords_en": ["bank statement", "account statement", "balance", "transaction", "debit", "credit"],
        "keywords_sq": ["pasqyrë bankare", "llogari bankare", "bilancë", "transaksion"],
    },
    "steuerbescheid": {
        "keywords_de": ["steuerbescheid", "finanzamt", "einkommensteuer", "festsetzung", "steuererstattung", "steuervorauszahlung"],
        "keywords_en": ["tax assessment", "tax notice", "tax return", "income tax", "tax refund"],
        "keywords_sq": ["vlerësim tatimor", "zyra e tatimeve", "tatim mbi të ardhurat", "rimbursim tatimor"],
    },
    "lohnabrechnung": {
        "keywords_de": ["lohnabrechnung", "gehaltsabrechnung", "bruttolohn", "nettolohn", "sozialversicherung", "steuerklasse", "arbeitnehmer"],
        "keywords_en": ["payslip", "salary statement", "payroll", "gross salary", "net salary", "tax deduction"],
        "keywords_sq": ["listë pagash", "pagë bruto", "pagë neto", "sigurim shoqëror"],
    },
    "vollmacht": {
        "keywords_de": ["vollmacht", "bevollmächtigung", "hiermit bevollmächtige", "prozessvollmacht", "generalvollmacht"],
        "keywords_en": ["power of attorney", "authorization", "proxy", "authority to act"],
        "keywords_sq": ["autorizim", "prokurë", "e autorizoj"],
    },
    "kündigung": {
        "keywords_de": ["kündigung", "fristgerecht", "ordentliche kündigung", "kündigungsfrist", "zum nächstmöglichen", "mietvertrag kündigung"],
        "keywords_en": ["termination", "notice", "cancellation", "notice period", "end of contract"],
        "keywords_sq": ["ndërprerje", "njoftim", "anulim", "afat njoftimi"],
    },
    "gutachten": {
        "keywords_de": ["gutachten", "sachverständiger", "bewertung", "expertise", "stellungnahme", "beurteilung"],
        "keywords_en": ["expert opinion", "appraisal", "assessment", "evaluation", "expert report"],
        "keywords_sq": ["ekspertizë", "vlerësim eksperti", "mendim eksperti"],
    },
    "urteil": {
        "keywords_de": ["urteil", "beschluss", "gericht", "aktenzeichen", "amtsgericht", "landgericht", "im namen des volkes"],
        "keywords_en": ["judgment", "verdict", "ruling", "court order", "in the name of the people", "court decision"],
        "keywords_sq": ["vendim gjykate", "gjykatë", "aktgjykim", "urdhër gjykate"],
    },
    "protokoll": {
        "keywords_de": ["protokoll", "sitzungsprotokoll", "teilnehmer", "tagesordnung", "beschluss", "besprechung"],
        "keywords_en": ["minutes", "meeting minutes", "protocol", "agenda", "attendees", "resolution"],
        "keywords_sq": ["procesverbal", "protokoll", "rend dite", "pjesëmarrës"],
    },
    "zeugnis": {
        "keywords_de": ["zeugnis", "schulzeugnis", "arbeitszeugnis", "bescheinigung", "note", "beurteilung"],
        "keywords_en": ["certificate", "reference", "attestation", "school report", "work reference"],
        "keywords_sq": ["dëshmi", "certifikatë", "vërtetim", "referencë pune"],
    },
    "bescheinigung": {
        "keywords_de": ["bescheinigung", "bestätigung", "nachweis", "zertifikat", "hiermit wird bestätigt"],
        "keywords_en": ["confirmation", "certificate", "proof", "attestation", "hereby certified"],
        "keywords_sq": ["konfirmim", "vërtetim", "dëshmi", "certifikatë"],
    },
    "antrag": {
        "keywords_de": ["antrag", "beantragen", "formular", "antragsteller", "hiermit beantrage", "bewilligung"],
        "keywords_en": ["application", "request", "form", "applicant", "approval", "submission"],
        "keywords_sq": ["kërkesë", "aplikim", "formular", "aplikant", "miratim"],
    },
    "versicherung": {
        "keywords_de": ["versicherungsschein", "police", "versicherungsnehmer", "schadensmeldung", "deckungssumme", "prämie"],
        "keywords_en": ["insurance", "policy", "coverage", "claim", "premium", "insured"],
        "keywords_sq": ["sigurim", "policë sigurimi", "mbulim", "prim sigurimi", "dëmshpërblim"],
    },
    "auftrag": {
        "keywords_de": ["auftrag", "auftragsbestätigung", "bestellung", "beauftragung", "auftragsnummer"],
        "keywords_en": ["order", "purchase order", "commission", "order confirmation", "order number"],
        "keywords_sq": ["porosi", "urdhër", "konfirmim porosie", "numër porosie"],
    },
    "beleg": {
        "keywords_de": ["beleg", "kassierbeleg", "ausgabe", "einnahme", "buchungsbeleg", "buchung"],
        "keywords_en": ["receipt", "voucher", "document", "booking record", "expense"],
        "keywords_sq": ["dokument", "faturë", "shpenzim", "regjistrim"],
    },
    "bewerbung": {
        "keywords_de": ["bewerbung", "anschreiben", "lebenslauf", "stellenausschreibung", "bewerbungsmappe", "bewerber", "referenzen", "motivationsschreiben", "werdegang"],
        "keywords_en": ["application", "cover letter", "cv", "curriculum vitae", "resume", "applicant", "motivation letter", "references"],
        "keywords_sq": ["aplikim pune", "letër motivimi", "cv", "biografi", "aplikant", "referenca"],
    },
}

# Aliases — häufige Schreibvarianten auf den Haupteintrag mappen
_KEYWORD_ALIASES: dict[str, str] = {
    "rechnungen": "rechnung",
    "invoice": "rechnung",
    "invoices": "rechnung",
    "verträge": "vertrag",
    "vertraege": "vertrag",
    "contracts": "vertrag",
    "mahnungen": "mahnung",
    "angebote": "angebot",
    "offers": "angebot",
    "briefe": "brief",
    "letter": "brief",
    "letters": "brief",
    "berichte": "bericht",
    "report": "bericht",
    "reports": "bericht",
    "lieferscheine": "lieferschein",
    "quittungen": "quittung",
    "receipt": "quittung",
    "kontoauszüge": "kontoauszug",
    "kontoauszuege": "kontoauszug",
    "kündigungen": "kündigung",
    "kuendigung": "kündigung",
    "kuendigungen": "kündigung",
    "gutachten": "gutachten",
    "urteile": "urteil",
    "protokolle": "protokoll",
    "minutes": "protokoll",
    "zeugnisse": "zeugnis",
    "bescheinigungen": "bescheinigung",
    "anträge": "antrag",
    "antraege": "antrag",
    "vollmachten": "vollmacht",
    "aufträge": "auftrag",
    "auftraege": "auftrag",
    "belege": "beleg",
    "lohnabrechungen": "lohnabrechnung",
    "gehaltsabrechnung": "lohnabrechnung",
    "payslip": "lohnabrechnung",
}


def _ensure_name_in_keywords(name: str, kw: dict[str, list[str]]) -> dict[str, list[str]]:
    """Stellt sicher dass der Name selbst immer als erstes Schlüsselwort in keywords_de steht."""
    for lang in ("keywords_de", "keywords_en", "keywords_sq"):
        kw.setdefault(lang, [])
    # Name selbst immer vorne in keywords_de
    if name not in kw["keywords_de"]:
        kw["keywords_de"] = [name] + kw["keywords_de"]
    return kw


def _lookup_keywords(name: str) -> dict[str, list[str]] | None:
    """Suche Schlüsselwörter im eingebauten Wörterbuch (inkl. Aliases).
    Stellt sicher, dass der Name selbst immer als erstes Keyword enthalten ist.
    """
    key = name.lower().strip()
    key = _KEYWORD_ALIASES.get(key, key)
    result = _KEYWORD_DICT.get(key)
    if result is None:
        return None
    # Deep copy damit das Dict nicht verändert wird
    import copy as _copy
    result = _copy.deepcopy(result)
    return _ensure_name_in_keywords(name, result)


async def _llm_suggest_keywords(name: str, cfg: dict) -> dict[str, list[str]] | None:
    """Schlüsselwörter via LLM generieren, wenn konfiguriert."""
    llm_cfg = cfg.get("llm", {})
    if not llm_cfg.get("enabled"):
        return None
    provider = llm_cfg.get("provider", "ollama")
    try:
        from nicegui import run as _run
        prompt = (
            f"Generiere Schlüsselwörter für die Dokumentenart '{name}'.\n"
            "Antworte NUR mit einem JSON-Objekt (kein Markdown, keine Erklärung):\n"
            '{"keywords_de": ["wort1", "wort2", ...], '
            '"keywords_en": ["word1", "word2", ...], '
            '"keywords_sq": ["fjale1", "fjale2", ...]}\n'
            "Wichtige Regeln:\n"
            f"- Das erste Element in keywords_de MUSS das Wort '{name}' selbst sein\n"
            f"- Das erste Element in keywords_en MUSS die direkte englische Übersetzung von '{name}' sein\n"
            f"- Das erste Element in keywords_sq MUSS die direkte albanische Übersetzung von '{name}' sein\n"
            "- keywords_de: danach 5-9 weitere deutsche Synonyme und Begriffe die in solchen Dokumenten vorkommen\n"
            "- keywords_en: danach 4-7 weitere englische Synonyme\n"
            "- keywords_sq: danach 3-5 weitere albanische Synonyme\n"
            "Nur einzelne Wörter oder kurze Phrasen, keine ganzen Sätze."
        )
        if provider == "openai":
            import openai, os, json as _json
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                return None
            def _call():
                client = openai.OpenAI(api_key=api_key)
                r = client.chat.completions.create(
                    model=llm_cfg.get("model") or "gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3, max_tokens=300,
                )
                return r.choices[0].message.content
            raw = await _run.io_bound(_call)
        elif provider == "anthropic":
            import anthropic, os, json as _json
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                return None
            def _call_ant():
                client = anthropic.Anthropic(api_key=api_key)
                r = client.messages.create(
                    model=llm_cfg.get("model") or "claude-haiku-4-20250414",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                )
                return r.content[0].text
            raw = await _run.io_bound(_call_ant)
        elif provider == "ollama":
            import httpx, json as _json
            host = llm_cfg.get("ollama_host", "http://localhost:11434")
            model = llm_cfg.get("ollama_model", "llama3.2")
            def _call_ol():
                resp = httpx.post(
                    f"{host.rstrip('/')}/api/chat",
                    json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False},
                    timeout=30,
                )
                return resp.json()["message"]["content"]
            raw = await _run.io_bound(_call_ol)
        else:
            return None

        import json as _json, re as _re
        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
        if m:
            data = _json.loads(m.group())
            result = {
                "keywords_de": [str(k) for k in data.get("keywords_de", [])],
                "keywords_en": [str(k) for k in data.get("keywords_en", [])],
                "keywords_sq": [str(k) for k in data.get("keywords_sq", [])],
            }
            # Name selbst immer als erstes Keyword sicherstellen
            return _ensure_name_in_keywords(name, result)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Tab: Pfade
# ---------------------------------------------------------------------------
def _build_paths_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    import shutil
    import subprocess

    paths     = cfg.setdefault("paths", {})
    inputs: dict[str, ui.input] = {}
    _PROTECTED = {"inbox", "archive"}

    _FOLDER_META = {
        "inbox":   ("📥", "Eingangs-Ordner",  "Neue Dokumente hier ablegen — Doc-Sorter liest sie automatisch ein.", "#3B82F6"),
        "archive": ("📦", "Archiv",            "Hier landen alle sortierten und verarbeiteten Dokumente.",           "#22C55E"),
        "logs":    ("📋", "Protokoll-Ordner",  "Aufzeichnungen über alle Verarbeitungsschritte.",                   "#8B5CF6"),
        "review":  ("🔍", "Prüfungs-Ordner",   "Dokumente die nicht sicher erkannt wurden — zur manuellen Prüfung.", "#F59E0B"),
    }

    def _folder_exists(val: str) -> bool:
        try:
            return bool(val and val.strip() and Path(val.strip()).expanduser().exists())
        except Exception:
            return False

    def _open_in_finder(val: str) -> None:
        try:
            p = Path(val.strip()).expanduser()
            if p.exists():
                subprocess.Popen(["open", str(p)])
            else:
                ui.notify("Ordner existiert noch nicht.", type="warning")
        except Exception as exc:
            ui.notify(f"Fehler: {exc}", type="negative")

    def _create_folder(val: str, refresh_fn) -> None:
        if not val.strip():
            ui.notify("Kein Pfad gespeichert.", type="warning")
            return
        try:
            Path(val.strip()).expanduser().mkdir(parents=True, exist_ok=True)
            ui.notify("Ordner erstellt ✓", type="positive")
            refresh_fn()
        except Exception as exc:
            ui.notify(f"Fehler: {exc}", type="negative")

    def _delete_folder_dialog(val: str, refresh_fn) -> None:
        p = Path(val.strip()).expanduser()
        if not p.exists():
            ui.notify("Ordner existiert nicht.", type="info")
            return
        with ui.dialog() as dlg, ui.card().style(
            "background:#0a1628;border:1px solid rgba(239,68,68,0.4);"
            "border-radius:14px;padding:24px;max-width:400px;width:100%"
        ):
            with ui.row().classes("items-center gap-3 mb-3"):
                ui.icon("warning").style("color:#EF4444;font-size:1.5rem")
                ui.label("Ordner wirklich löschen?").style("font-weight:700;font-size:1rem")
            ui.label("Der Ordner und alle Inhalte werden unwiderruflich gelöscht:").style(
                "font-size:0.82rem;color:var(--ds-text-2);margin-bottom:4px"
            )
            ui.label(str(p)).style(
                "font-size:0.78rem;font-family:monospace;color:#EF4444;"
                "word-break:break-all;padding:8px;background:rgba(239,68,68,0.08);"
                "border-radius:6px;margin-bottom:16px"
            )
            with ui.row().classes("gap-3 justify-end"):
                ui.button("Abbrechen", on_click=dlg.close).props("flat no-caps").style("color:#9CA3AF")
                def _do_delete(d=dlg, path=p):
                    try:
                        shutil.rmtree(path)
                        ui.notify("Ordner gelöscht.", type="positive")
                        d.close()
                        refresh_fn()
                    except Exception as exc:
                        ui.notify(f"Fehler: {exc}", type="negative")
                ui.button("Löschen", on_click=_do_delete, icon="delete_forever").props(
                    "unelevated no-caps"
                ).style("background:#EF4444;color:white;border-radius:8px;font-weight:700")
        dlg.open()

    # ── Ansichts-Toggle ────────────────────────────────────────────────────────
    mode = {"advanced": False}

    @ui.refreshable
    def render_view() -> None:
        val = paths  # live reference

        if not mode["advanced"]:
            # ── EINFACHE ANSICHT: Statuskarten ──────────────────────────────
            with ui.grid(columns=2).classes("w-full gap-4"):
                for key in ["inbox", "archive", "logs", "review"]:
                    emoji, title, desc, color = _FOLDER_META[key]
                    path_val  = val.get(key, "")
                    exists    = _folder_exists(path_val)
                    protected = key in _PROTECTED

                    with ui.card().classes("ds-card-flat w-full").style(
                        f"border:1px solid {color}22;padding:18px 20px;min-height:160px"
                    ):
                        # Kopfzeile
                        with ui.row().classes("items-center gap-3 mb-3"):
                            with ui.element("div").style(
                                f"width:42px;height:42px;border-radius:12px;flex-shrink:0;"
                                f"background:{color}18;border:1px solid {color}33;"
                                "display:flex;align-items:center;justify-content:center;"
                                "font-size:1.4rem"
                            ):
                                ui.label(emoji)
                            with ui.column().classes("gap-0 flex-1"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.label(title).style(
                                        "font-size:0.95rem;font-weight:700;color:var(--ds-text)"
                                    )
                                    if protected:
                                        ui.label("Geschützt").style(
                                            "font-size:0.58rem;font-weight:700;padding:1px 6px;"
                                            "border-radius:8px;background:rgba(245,158,11,0.15);"
                                            "color:#F59E0B;border:1px solid rgba(245,158,11,0.3)"
                                        )
                                ui.label(desc).style(
                                    "font-size:0.72rem;color:var(--ds-text-2);line-height:1.4"
                                )

                        # Status
                        with ui.row().classes("items-center gap-2 mb-3"):
                            if exists:
                                ui.icon("check_circle").style("color:#22C55E;font-size:1rem")
                                ui.label("Bereit").style("font-size:0.78rem;font-weight:600;color:#22C55E")
                            elif path_val:
                                ui.icon("warning_amber").style("color:#F59E0B;font-size:1rem")
                                ui.label("Ordner fehlt").style("font-size:0.78rem;font-weight:600;color:#F59E0B")
                            else:
                                ui.icon("help_outline").style("color:#6B7280;font-size:1rem")
                                ui.label("Kein Pfad").style("font-size:0.78rem;color:#6B7280")

                        # Aktions-Buttons
                        with ui.row().classes("gap-2 flex-wrap"):
                            if exists:
                                ui.button(
                                    "Im Finder öffnen", icon="folder_open",
                                    on_click=lambda v=path_val: _open_in_finder(v),
                                ).props("unelevated dense no-caps").style(
                                    f"background:{color}18;color:{color};"
                                    f"border:1px solid {color}44;border-radius:8px;"
                                    "font-size:0.78rem;padding:4px 12px"
                                )
                            else:
                                ui.button(
                                    "Jetzt erstellen", icon="create_new_folder",
                                    on_click=lambda v=path_val: _create_folder(v, render_view.refresh),
                                ).props("unelevated dense no-caps").style(
                                    "background:rgba(59,130,246,0.15);color:#3B82F6;"
                                    "border:1px solid rgba(59,130,246,0.4);border-radius:8px;"
                                    "font-size:0.78rem;padding:4px 12px"
                                )

                            if not protected and exists:
                                ui.button(
                                    icon="delete_outline",
                                    on_click=lambda v=path_val: _delete_folder_dialog(v, render_view.refresh),
                                ).props("flat round dense").style(
                                    "color:#EF4444;margin-left:auto"
                                ).tooltip("Ordner löschen")

        else:
            # ── ERWEITERTE ANSICHT: Pfad-Eingabe + Erstellen/Löschen ─────────
            for key in ["inbox", "archive", "logs", "review"]:
                _, title, _, color = _FOLDER_META[key]
                protected = key in _PROTECTED

                with ui.card().classes("ds-card-flat w-full").style(
                    f"border:1px solid {color}22;padding:14px 18px;margin-bottom:10px"
                ):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.label(f"{_FOLDER_META[key][0]}  {title}").style(
                            "font-size:0.88rem;font-weight:700;color:var(--ds-text)"
                        )
                        if protected:
                            ui.label("Geschützt").style(
                                "font-size:0.62rem;font-weight:700;padding:1px 7px;border-radius:10px;"
                                "background:rgba(245,158,11,0.15);color:#F59E0B;"
                                "border:1px solid rgba(245,158,11,0.35)"
                            )

                    with ui.row().classes("items-center gap-2 w-full"):
                        inp = ui.input(
                            placeholder=_FOLDER_META[key][2],
                            value=paths.get(key, ""),
                        ).classes("flex-1 ds-input")
                        inputs[key] = inp

                        # Status-Icon
                        icon_ref: dict = {}
                        iv = "check_circle" if _folder_exists(paths.get(key, "")) else "error_outline"
                        ic = "color:#22C55E" if iv == "check_circle" else "color:#F59E0B"
                        icon_ref["el"] = ui.icon(iv).style(f"{ic};font-size:1.2rem;flex-shrink:0")

                        def _make_upd(ir=inp, iref=icon_ref):
                            def _upd(e=None):
                                ex = _folder_exists(ir.value)
                                iref["el"].props(f'name="{"check_circle" if ex else "error_outline"}"')
                                iref["el"].style(f'{"color:#22C55E" if ex else "color:#F59E0B"};font-size:1.2rem;flex-shrink:0')
                            return _upd

                        inp.on("keyup", _make_upd())
                        inp.on("blur",  _make_upd())

                        def _mk_create(ir=inp):
                            def _c():
                                _create_folder(ir.value, render_view.refresh)
                            return _c
                        ui.button(icon="create_new_folder", on_click=_mk_create()).props(
                            "flat round dense"
                        ).style("color:#3B82F6").tooltip("Ordner erstellen")

                        if not protected:
                            def _mk_del(ir=inp):
                                def _d():
                                    _delete_folder_dialog(ir.value, render_view.refresh)
                                return _d
                            ui.button(icon="delete_outline", on_click=_mk_del()).props(
                                "flat round dense"
                            ).style("color:#EF4444").tooltip("Ordner löschen")

            with ui.row().classes("gap-3 mt-4"):
                def save() -> None:
                    for k, i in inputs.items():
                        paths[k] = i.value
                    save_config(cfg)
                    _notify_saved("Pfade")

                ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

                def discard() -> None:
                    for k, i in inputs.items():
                        i.value = original.get("paths", {}).get(k, "")
                    ui.notify("Änderungen verworfen", type="info")

                ui.button("Verwerfen", on_click=discard, icon="undo").classes("ds-btn-ghost")

    # ── Toggle-Button ──────────────────────────────────────────────────────────
    callout(
        "Hier siehst du den Status deiner Ordner auf einen Blick. "
        "Für technische Einstellungen wie Pfade ändern klicke auf 'Erweitert'.",
        "info", "folder",
    )

    with ui.row().classes("items-center justify-end w-full mb-3"):
        def _toggle_mode():
            mode["advanced"] = not mode["advanced"]
            toggle_btn.set_text("Einfache Ansicht" if mode["advanced"] else "Erweitert")
            toggle_btn.props(
                'icon="tune"' if mode["advanced"] else 'icon="dashboard"'
            )
            render_view.refresh()

        toggle_btn = ui.button(
            "Erweitert", icon="tune", on_click=_toggle_mode
        ).props("flat dense no-caps").style(
            "color:var(--ds-text-2);font-size:0.78rem;"
            "border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:3px 12px"
        )

    render_view()


# ---------------------------------------------------------------------------
# Tab: Dateitypen
# ---------------------------------------------------------------------------
def _build_filetypes_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    file_types: list[str] = cfg.setdefault("file_types", [".pdf"])

    callout("Welche Dateitypen sollen erkannt und verarbeitet werden? Standard: PDF, Word, Bilder. Füge weitere hinzu oder entferne nicht benötigte.", "info", "insert_drive_file")

    container = ui.column().classes("w-full")

    def refresh_chips() -> None:
        container.clear()
        with container:
            with ui.row().classes("gap-2 flex-wrap"):
                for ft in file_types:
                    chip = ui.chip(ft, removable=True, color="primary").classes("ds-chip")
                    chip.on("remove", lambda _, f=ft: _remove_type(f))

    def _remove_type(ft: str) -> None:
        if ft in file_types:
            file_types.remove(ft)
            refresh_chips()

    refresh_chips()

    with ui.row().classes("gap-2 mt-3 items-end"):
        new_type = ui.input(
            label="Neuer Typ (z.B. .xlsx)",
            validation={"Muss mit . beginnen": lambda v: not v or v.startswith(".")},
        ).classes("w-48 ds-input")

        def _add_type() -> None:
            val = new_type.value.strip()
            if val and val.startswith(".") and val not in file_types:
                file_types.append(val)
                new_type.value = ""
                refresh_chips()

        ui.button("+", on_click=_add_type).props("round size=sm").classes("ds-btn-primary")

    with ui.row().classes("gap-3 mt-4"):
        def save() -> None:
            cfg["file_types"] = file_types
            save_config(cfg)
            _notify_saved("Dateitypen")

        ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

        def discard() -> None:
            file_types.clear()
            file_types.extend(original.get("file_types", [".pdf"]))
            refresh_chips()
            ui.notify("Aenderungen verworfen", type="info")

        ui.button("Verwerfen", on_click=discard, icon="undo").classes("ds-btn-ghost")


# ---------------------------------------------------------------------------
# Tab: Texterkennung (OCR)
# ---------------------------------------------------------------------------
def _build_ocr_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    import shutil as _shutil
    from nicegui import run as _run

    ocr  = cfg.setdefault("ocr", {})
    mode = {"advanced": False}

    # Tesseract-Status ermitteln (einmalig beim Laden)
    _tess_ok   = bool(_shutil.which("tesseract"))
    _tess_path = _shutil.which("tesseract") or ""

    def _dpi_label(dpi: int) -> tuple[str, str]:
        if dpi <= 150:  return "Niedrig",  "#F59E0B"
        if dpi <= 250:  return "Standard", "#22C55E"
        if dpi <= 400:  return "Hoch",     "#3B82F6"
        return "Sehr hoch", "#8B5CF6"

    def _lang_chips(lang_str: str) -> list[str]:
        _names = {"eng": "Englisch 🇬🇧", "deu": "Deutsch 🇩🇪", "sqi": "Albanisch 🇦🇱",
                  "fra": "Französisch 🇫🇷", "ita": "Italienisch 🇮🇹", "spa": "Spanisch 🇪🇸"}
        return [_names.get(l.strip(), l.strip()) for l in lang_str.split("+") if l.strip()]

    callout(
        "Texterkennung (OCR) liest den Inhalt von gescannten Dokumenten und Fotos — "
        "auch wenn kein Text direkt im PDF enthalten ist. Benötigt Tesseract (kostenlos).",
        "info", "document_scanner",
    )

    with ui.row().classes("items-center justify-end w-full mb-3"):
        def _toggle():
            mode["advanced"] = not mode["advanced"]
            _btn.set_text("Einfache Ansicht" if mode["advanced"] else "Erweitert")
            _btn.props('icon="tune"' if mode["advanced"] else 'icon="dashboard"')
            render_ocr.refresh()
        _btn = ui.button("Erweitert", icon="tune", on_click=_toggle).props(
            "flat dense no-caps"
        ).style(
            "color:var(--ds-text-2);font-size:0.78rem;"
            "border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:3px 12px"
        )

    @ui.refreshable
    def render_ocr() -> None:
        dpi       = int(ocr.get("dpi", 200))
        max_pages = int(ocr.get("max_pages", 5))
        langs     = ocr.get("languages", "eng+deu+sqi")

        if not mode["advanced"]:
            # ── EINFACHE ANSICHT ────────────────────────────────────────────
            with ui.grid(columns=2).classes("w-full gap-4"):

                # Karte 1: Tesseract-Status
                with ui.card().classes("ds-card-flat").style(
                    "border:1px solid rgba(34,197,94,0.2)" if _tess_ok
                    else "border:1px solid rgba(239,68,68,0.2)"
                ):
                    with ui.row().classes("items-center gap-3 mb-2"):
                        ui.icon("document_scanner").style(
                            f"font-size:1.6rem;color:{'#22C55E' if _tess_ok else '#EF4444'}"
                        )
                        with ui.column().classes("gap-0"):
                            ui.label("Tesseract").style("font-weight:700;font-size:0.9rem")
                            ui.label(
                                "Installiert ✓" if _tess_ok else "Nicht gefunden"
                            ).style(
                                f"font-size:0.75rem;font-weight:600;"
                                f"color:{'#22C55E' if _tess_ok else '#EF4444'}"
                            )
                    if _tess_ok:
                        ui.label("Texterkennung ist einsatzbereit.").style(
                            "font-size:0.72rem;color:var(--ds-text-2)"
                        )
                    else:
                        ui.label(
                            "Tesseract installieren: brew install tesseract"
                        ).style("font-size:0.72rem;color:#EF4444;font-family:monospace")

                # Karte 2: Scan-Qualität
                dpi_lbl, dpi_color = _dpi_label(dpi)
                with ui.card().classes("ds-card-flat").style(
                    f"border:1px solid {dpi_color}22"
                ):
                    with ui.row().classes("items-center gap-3 mb-2"):
                        ui.icon("high_quality").style(f"font-size:1.6rem;color:{dpi_color}")
                        with ui.column().classes("gap-0"):
                            ui.label("Scan-Qualität").style("font-weight:700;font-size:0.9rem")
                            ui.label(f"{dpi_lbl} ({dpi} DPI)").style(
                                f"font-size:0.75rem;font-weight:600;color:{dpi_color}"
                            )
                    ui.label(
                        "Ideal für die meisten Dokumente. Höher = langsamer aber genauer."
                    ).style("font-size:0.72rem;color:var(--ds-text-2)")

                # Karte 3: Sprachen
                with ui.card().classes("ds-card-flat").style(
                    "border:1px solid rgba(59,130,246,0.2)"
                ):
                    with ui.row().classes("items-center gap-3 mb-2"):
                        ui.icon("translate").style("font-size:1.6rem;color:#3B82F6")
                        ui.label("Erkennungssprachen").style("font-weight:700;font-size:0.9rem")
                    with ui.row().classes("gap-2 flex-wrap"):
                        for chip in _lang_chips(langs):
                            ui.label(chip).style(
                                "background:rgba(59,130,246,0.12);color:#3B82F6;"
                                "border:1px solid rgba(59,130,246,0.3);border-radius:20px;"
                                "padding:2px 10px;font-size:0.75rem;font-weight:600"
                            )

                # Karte 4: Seiten-Limit
                with ui.card().classes("ds-card-flat").style(
                    "border:1px solid rgba(139,92,246,0.2)"
                ):
                    with ui.row().classes("items-center gap-3 mb-2"):
                        ui.icon("auto_stories").style("font-size:1.6rem;color:#8B5CF6")
                        with ui.column().classes("gap-0"):
                            ui.label("Seiten-Limit").style("font-weight:700;font-size:0.9rem")
                            ui.label(f"Max. {max_pages} Seiten pro Dokument").style(
                                "font-size:0.75rem;font-weight:600;color:#8B5CF6"
                            )
                    ui.label(
                        "Begrenzt wie viele Seiten pro Dokument gelesen werden."
                    ).style("font-size:0.72rem;color:var(--ds-text-2)")

            # Test-Button
            ocr_status = ui.label("").classes("text-sm mt-3")
            async def _quick_test():
                ocr_status.set_text("🔍 Prüfe Tesseract…")
                def _chk():
                    ts = _shutil.which("tesseract")
                    if not ts:
                        return False, "Tesseract nicht gefunden — installiere es mit: brew install tesseract"
                    import subprocess
                    r = subprocess.run([ts, "--version"], capture_output=True, text=True, timeout=5)
                    return True, (r.stdout or r.stderr or "").split("\n")[0]
                ok, msg = await _run.io_bound(_chk)
                ocr_status.set_text(f"{'✅' if ok else '❌'} {msg}")
                ui.notify(msg, type="positive" if ok else "negative")

            ui.button("Texterkennung testen", icon="document_scanner", on_click=_quick_test).props(
                "unelevated dense no-caps"
            ).style(
                "background:rgba(0,212,255,0.1);color:#00d4ff;"
                "border:1px solid rgba(0,212,255,0.3);border-radius:8px;margin-top:8px"
            )

        else:
            # ── ERWEITERTE ANSICHT ──────────────────────────────────────────
            lang_input = ui.input(
                label="Sprachen (z.B. eng+deu+sqi)",
                value=langs,
                validation={"Sprachen dürfen nicht leer sein": lambda v: bool(v and v.strip())},
            ).classes("w-full ds-input")
            ui.label("Kombiniere Sprachen mit +: eng+deu = Englisch und Deutsch").classes(
                "text-xs text-gray-400 mb-3"
            )

            with ui.row().classes("gap-4"):
                dpi_input = ui.number(
                    label="Scan-Qualität (DPI)", value=dpi, min=72, max=600, step=50,
                ).classes("ds-input")
                pages_input = ui.number(
                    label="Max. Seiten pro Dokument", value=max_pages, min=1, max=50,
                ).classes("ds-input")
            ui.label(
                "DPI 200 = Standard · 300+ = besser für schlechte Scans, aber langsamer"
            ).classes("text-xs text-gray-400 mb-3")

            ocr_test_label = ui.label("").classes("text-sm mt-2")

            async def _test_ocr():
                ocr_test_label.set_text("Teste Tesseract…")
                def _chk():
                    ts = _shutil.which("tesseract")
                    if not ts:
                        return False, "tesseract nicht gefunden"
                    import subprocess
                    r = subprocess.run([ts, "--version"], capture_output=True, text=True, timeout=5)
                    return True, (r.stdout or r.stderr or "").split("\n")[0]
                ok, msg = await _run.io_bound(_chk)
                ocr_test_label.set_text(f"{'✅' if ok else '❌'} {msg}")
                ui.notify(msg, type="positive" if ok else "negative")

            with ui.row().classes("gap-3 mt-4"):
                def save():
                    ocr["languages"] = lang_input.value
                    ocr["dpi"]       = int(dpi_input.value)
                    ocr["max_pages"] = int(pages_input.value)
                    save_config(cfg)
                    _notify_saved("Texterkennung")
                    render_ocr.refresh()

                ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")
                ui.button("Tesseract testen", on_click=_test_ocr, icon="document_scanner").classes("ds-btn-secondary")

                def discard():
                    orig = original.get("ocr", {})
                    lang_input.value   = orig.get("languages", "eng+deu+sqi")
                    dpi_input.value    = orig.get("dpi", 200)
                    pages_input.value  = orig.get("max_pages", 5)
                    ui.notify("Änderungen verworfen", type="info")

                ui.button("Verwerfen", on_click=discard, icon="undo").classes("ds-btn-ghost")

    render_ocr()


# ---------------------------------------------------------------------------
# Tab: Dokumentenarten
# ---------------------------------------------------------------------------
def _build_doctypes_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    doc_types: dict[str, Any] = cfg.setdefault("document_types", {})

    # Default-Dokumentenarten fuer Einklick-Setup
    _DEFAULT_DOCTYPES = [
        "rechnung", "vertrag", "brief", "angebot", "mahnung", "bericht",
        "k\u00fcndigung", "lieferschein", "lohnabrechnung", "bewerbung", "steuerbescheid",
    ]

    callout(
        "Lege hier fest, welche Dokumentenarten Doc-Sorter kennen soll — z.B. Rechnung, Vertrag oder Mahnung. "
        "Für jede Art kannst du Schlüsselwörter in verschiedenen Sprachen hinterlegen, anhand derer das Dokument erkannt wird.",
        "info", "description",
    )

    def _update_keywords(lang_kw: dict, lang_key: str, raw_value: str) -> None:
        lang_kw[lang_key] = [kw.strip() for kw in raw_value.split(",") if kw.strip()]

    def _refresh_chips(chip_row: ui.row, keywords: list[str]) -> None:
        chip_row.clear()
        with chip_row:
            for kw in keywords:
                ui.chip(kw, color="teal").props("dense").classes("ds-chip")

    def _seed_defaults() -> None:
        """11 Standard-Dokumentenarten inkl. Keywords einfuegen (nur fehlende)."""
        added = 0
        for name in _DEFAULT_DOCTYPES:
            if name not in doc_types:
                kw = _lookup_keywords(name)
                if kw:
                    doc_types[name] = kw
                    added += 1
        if added > 0:
            ui.notify(
                f"\u2713 {added} Standard-Dokumentenart(en) eingef\u00fcgt \u2014 Speichern nicht vergessen",
                type="positive", position="top",
            )
        else:
            ui.notify("Alle Standard-Dokumentenarten sind bereits vorhanden", type="info")
        render_doctypes.refresh()

    @ui.refreshable
    def render_doctypes() -> None:
        # ── Empty state mit Quick-Setup ─────────────────────────────────────
        if not doc_types:
            with ui.card().classes("ds-card-flat w-full border-2 border-dashed border-gray-300 dark:border-gray-600"):
                with ui.column().classes("items-center gap-3 py-6 w-full"):
                    ui.icon("description_off").classes("text-4xl text-gray-300 dark:text-gray-600")
                    ui.label("Noch keine Dokumentenarten angelegt").classes("font-semibold text-gray-400")
                    ui.label(
                        "Schnellstart: F\u00fcge die 11 Standard-Dokumentenarten (Rechnung, Vertrag, Brief, "
                        "Angebot, Mahnung, Bericht, K\u00fcndigung, Lieferschein, Lohnabrechnung, Bewerbung, "
                        "Steuerbescheid) mit einem Klick ein \u2014 inklusive mehrsprachiger Schl\u00fcsselw\u00f6rter."
                    ).classes("text-xs text-gray-400 text-center max-w-md leading-relaxed")
                    ui.button(
                        "Standard-Dokumentenarten einf\u00fcgen",
                        on_click=_seed_defaults,
                        icon="auto_awesome",
                    ).classes("ds-btn-primary mt-2").tooltip(
                        "F\u00fcgt alle 11 Standard-Arten inkl. deutscher/englischer/albanischer Keywords ein. "
                        "Du kannst danach jede Art einzeln anpassen oder l\u00f6schen."
                    )
                    ui.label("Oder unten manuell eine einzelne Art anlegen").classes("text-xs text-gray-500 italic")

        # ── Nicht-leerer Zustand: Quick-Action wenn Standards fehlen ────────
        elif any(name not in doc_types for name in _DEFAULT_DOCTYPES):
            missing_count = sum(1 for n in _DEFAULT_DOCTYPES if n not in doc_types)
            with ui.row().classes("items-center gap-2 w-full").style(
                "background:rgba(0,212,255,0.04);border:1px solid rgba(0,212,255,0.2);"
                "border-radius:10px;padding:8px 12px;margin-bottom:8px"
            ):
                ui.icon("auto_awesome").style("color:#00d4ff;font-size:1rem")
                ui.label(
                    f"{missing_count} von 11 Standard-Dokumentenarten fehlen noch."
                ).classes("text-xs flex-1").style("color:var(--ds-text-2)")
                ui.button(
                    "Fehlende hinzuf\u00fcgen",
                    on_click=_seed_defaults,
                    icon="add_circle",
                ).props("flat dense no-caps").classes("text-xs")

        # ── Existing entries ──────────────────────────────────────────────────
        for dtype, lang_kw in doc_types.items():
            with ui.expansion(dtype.title(), icon="description").classes("w-full ds-expansion"):
                label_map = {
                    "keywords_de": ("Deutsch 🇩🇪", "Wörter die im Dokument auf Deutsch auf diese Art hinweisen"),
                    "keywords_en": ("Englisch 🇬🇧", "Words that indicate this type in English"),
                    "keywords_sq": ("Albanisch 🇦🇱", "Fjalët që tregojnë këtë lloj në shqip"),
                }
                for lang_key in ["keywords_de", "keywords_en", "keywords_sq"]:
                    keywords = lang_kw.get(lang_key, [])
                    lang_label, lang_hint = label_map.get(lang_key, (lang_key, ""))
                    with ui.column().classes("w-full mb-3"):
                        ui.label(lang_label).classes("text-sm font-semibold text-gray-600 dark:text-gray-300")
                        ui.label(lang_hint).classes("text-xs text-gray-400 mb-1")
                        chip_row = ui.row().classes("gap-1 flex-wrap mb-1")
                        with chip_row:
                            for kw in keywords:
                                ui.chip(kw, color="teal").props("dense").classes("ds-chip")
                        ta = ui.input(
                            label="Schlüsselwörter bearbeiten (kommagetrennt)",
                            value=", ".join(keywords),
                        ).classes("w-full ds-input")
                        ta.on(
                            "blur",
                            lambda e, lk=lang_key, lkw=lang_kw, cr=chip_row: (
                                _update_keywords(lkw, lk, e.sender.value),
                                _refresh_chips(cr, lkw.get(lk, [])),
                            ),
                        )

                ui.button(
                    "Dokumentenart entfernen",
                    on_click=lambda n=dtype: (doc_types.pop(n, None), render_doctypes.refresh()),
                    icon="delete",
                ).classes("ds-btn-danger mt-2").props("size=sm")

        # ── Add new ───────────────────────────────────────────────────────────
        ui.separator().classes("my-4")

        status_label = ui.label("").classes("text-xs text-gray-400")

        with ui.row().classes("gap-2 items-center w-full"):
            new_name = ui.input(
                label="Neue Dokumentenart hinzufügen",
                placeholder="z.B. rechnung, vertrag, mahnung, kündigung …",
                autocomplete=list(doc_types.keys()),
            ).classes("flex-1 ds-input")

            add_btn = ui.button("Hinzufügen", icon="add").classes("ds-btn-primary")

        ui.label("Tipp: Kleinschreibung empfohlen. Schlüsselwörter werden automatisch vorgeschlagen.").classes("text-xs text-gray-400 mt-1")

        async def add_doctype() -> None:
            n = new_name.value.strip().lower()
            if not n:
                return
            if n in doc_types:
                ui.notify(f'"{n}" existiert bereits', type="warning")
                return

            # 1. Wörterbuch-Lookup (sofort)
            found = _lookup_keywords(n)
            if found:
                doc_types[n] = found
                new_name.value = ""
                status_label.set_text(f'✅ Schlüsselwörter für "{n}" automatisch gefunden.')
                render_doctypes.refresh()
                return

            # 2. Eintrag mit Namen als erstem Keyword anlegen und anzeigen
            doc_types[n] = {"keywords_de": [n], "keywords_en": [], "keywords_sq": []}
            new_name.value = ""
            render_doctypes.refresh()

            # 3. LLM-Fallback (async)
            llm_on = cfg.get("llm", {}).get("enabled", False)
            if llm_on:
                status_label.set_text(f'🤖 KI generiert Schlüsselwörter für "{n}" …')
                add_btn.props("loading=true disabled=true")
                try:
                    suggested = await _llm_suggest_keywords(n, cfg)
                    if suggested and n in doc_types:
                        doc_types[n] = suggested
                        render_doctypes.refresh()
                        status_label.set_text(f'✅ KI hat Schlüsselwörter für "{n}" vorgeschlagen — bitte prüfen.')
                    else:
                        status_label.set_text(f'"{n}" angelegt — bitte Schlüsselwörter manuell eintragen.')
                except Exception:
                    status_label.set_text(f'"{n}" angelegt — bitte Schlüsselwörter manuell eintragen.')
                finally:
                    add_btn.props(remove="loading disabled")
            else:
                status_label.set_text(f'"{n}" angelegt — bitte Schlüsselwörter manuell eintragen. (KI-Vorschläge: KI-Assistent aktivieren)')

        add_btn.on("click", add_doctype)

        # ── Save ──────────────────────────────────────────────────────────────
        with ui.row().classes("gap-3 mt-6"):
            def save() -> None:
                save_config(cfg)
                _notify_saved("Dokumentenarten")

            ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

    render_doctypes()


# ---------------------------------------------------------------------------
# Tab: Kunden
# ---------------------------------------------------------------------------
def _build_customers_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    customers: list[dict[str, Any]] = cfg.setdefault("known_customers", [])

    callout(
        "Lege Kunden und Vertragspartner an. Doc-Sorter erkennt sie automatisch "
        "in Dokumenten anhand der hinterlegten Aliases.",
        "info", "people",
    )

    container = ui.column().classes("w-full")

    def refresh() -> None:
        container.clear()
        with container:
            for i, cust in enumerate(customers):
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("w-full items-center gap-3"):
                        name_input = ui.input(
                            label="Name", value=cust.get("name", ""),
                            placeholder="z.B. GASAG AG",
                        ).classes("w-1/3 ds-input")
                        aliases_input = ui.input(
                            label="Aliases (kommagetrennt)",
                            value=", ".join(cust.get("aliases", [])),
                            placeholder="z.B. GASAG, Gasag Berlin, gasag.de",
                        ).classes("flex-grow ds-input")
                        ui.button(
                            icon="delete",
                            on_click=lambda idx=i: _remove(idx),
                        ).classes("ds-btn-danger").props("round size=sm")

                    name_input.on(
                        "blur",
                        lambda e, c=cust: c.update({"name": e.sender.value}),
                    )
                    aliases_input.on(
                        "blur",
                        lambda e, c=cust: c.update({
                            "aliases": [a.strip() for a in e.sender.value.split(",") if a.strip()]
                        }),
                    )

    def _remove(idx: int) -> None:
        if 0 <= idx < len(customers):
            customers.pop(idx)
            refresh()

    refresh()

    def add_customer() -> None:
        customers.append({"name": "", "aliases": []})
        refresh()

    ui.button("Kunden hinzufügen", on_click=add_customer, icon="person_add").classes("ds-btn-secondary mt-2").tooltip("Neuen Kunden oder Vertragspartner anlegen")

    with ui.row().classes("gap-3 mt-4"):
        def save() -> None:
            save_config(cfg)
            _notify_saved("Kunden")

        ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")


# ---------------------------------------------------------------------------
# Tab: Laender
# ---------------------------------------------------------------------------
def _build_countries_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    countries: dict[str, Any] = cfg.setdefault("countries", {})

    callout(
        "Lege fest, welche Länder Doc-Sorter erkennen soll. "
        "Für jedes Land hinterlegst du Schlüsselwörter — z.B. Städtenamen oder landesspezifische Begriffe — "
        "die in den Dokumenten vorkommen können.",
        "info", "public",
    )

    @ui.refreshable
    def render_countries() -> None:
        # ── Empty state ───────────────────────────────────────────────────────
        if not countries:
            with ui.card().classes("ds-card-flat w-full border-2 border-dashed border-gray-300 dark:border-gray-600"):
                with ui.column().classes("items-center gap-2 py-6 w-full"):
                    ui.icon("public_off").classes("text-4xl text-gray-300 dark:text-gray-600")
                    ui.label("Noch keine Länder angelegt").classes("font-semibold text-gray-400")
                    ui.label(
                        "Füge dein erstes Land hinzu — z.B. 'deutschland'. "
                        "Dann kannst du Wörter wie 'berlin', 'bundesrepublik' oder 'germany' hinterlegen, "
                        "damit Doc-Sorter Dokumente aus diesem Land erkennt."
                    ).classes("text-xs text-gray-400 text-center max-w-sm leading-relaxed")

        # ── Existing entries ──────────────────────────────────────────────────
        for country, data in list(countries.items()):
            with ui.card().classes("ds-card-flat w-full"):
                with ui.row().classes("w-full items-center gap-2 mb-2"):
                    ui.icon("flag").classes("text-blue-500")
                    ui.label(country.title()).classes("font-semibold text-sm flex-1")
                    ui.button(
                        icon="delete",
                        on_click=lambda c=country: (countries.pop(c, None), render_countries.refresh()),
                    ).classes("ds-btn-danger").props("round size=sm flat")

                kw_input = ui.input(
                    label="Erkennungswörter (kommagetrennt)",
                    value=", ".join(data.get("keywords", [])),
                    placeholder="z.B. berlin, germany, bundesrepublik, münchen …",
                ).classes("w-full ds-input")
                ui.label(
                    "Trage Städtenamen, Ländernamen in verschiedenen Sprachen und typische Begriffe ein "
                    "die in Dokumenten aus diesem Land auftauchen."
                ).classes("text-xs text-gray-400 mt-1")

                chip_row = ui.row().classes("gap-1 flex-wrap mt-2")
                with chip_row:
                    for kw in data.get("keywords", []):
                        ui.chip(kw, color="blue").props("dense").classes("ds-chip")

                def _on_blur(e, d=data, cr=chip_row) -> None:
                    d["keywords"] = [k.strip() for k in e.sender.value.split(",") if k.strip()]
                    cr.clear()
                    with cr:
                        for kw in d["keywords"]:
                            ui.chip(kw, color="blue").props("dense").classes("ds-chip")

                kw_input.on("blur", _on_blur)

        # ── Add new ───────────────────────────────────────────────────────────
        ui.separator().classes("my-4")
        with ui.row().classes("gap-2 items-end w-full"):
            new_country = ui.input(
                label="Neues Land hinzufügen",
                placeholder="z.B. deutschland, schweiz, frankreich …",
                autocomplete=list(countries.keys()),
            ).classes("flex-1 ds-input")

            def add_country() -> None:
                n = new_country.value.strip().lower()
                if n and n not in countries:
                    countries[n] = {"keywords": []}
                    render_countries.refresh()
                elif n in countries:
                    ui.notify(f'"{n}" existiert bereits', type="warning")

            ui.button("Hinzufügen", on_click=add_country, icon="add").classes("ds-btn-primary")

        # ── Save ──────────────────────────────────────────────────────────────
        with ui.row().classes("gap-3 mt-6"):
            def save() -> None:
                save_config(cfg)
                _notify_saved("Länder")

            ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

    render_countries()


# ---------------------------------------------------------------------------
# Tab: Erkennungs-Sicherheit
# ---------------------------------------------------------------------------
def _build_confidence_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    conf = cfg.setdefault("confidence", {})

    callout(
        "Hier legst du fest, wie sicher Doc-Sorter bei einer Erkennung sein muss. Unsichere Dokumente landen im Prüfungs-Ordner und können manuell kontrolliert werden.",
        "info", "psychology",
    )

    conf_mode = {"advanced": False}

    with ui.row().classes("w-full items-center justify-between mb-2"):
        ui.label("Erkennungs-Sicherheit").classes("text-base font-semibold")
        toggle_btn_conf = ui.button("Erweitert", icon="tune").classes("ds-btn-ghost text-xs")

    conf_view_container = ui.column().classes("w-full gap-3")

    @ui.refreshable
    def render_conf_view() -> None:
        conf_view_container.clear()
        with conf_view_container:
            min_text = conf.get("min_text_length", 30)
            missing_fields = conf.get("uncertain_if_missing", ["kunde", "dokumentenart"])

            if not conf_mode["advanced"]:
                # ── Simple view ──────────────────────────────────────────────

                # Intro explanation
                with ui.card().classes("ds-card-flat w-full border-l-4 border-blue-400"):
                    with ui.row().classes("items-start gap-3"):
                        ui.icon("help_outline").classes("text-blue-400 text-xl mt-0.5 flex-shrink-0")
                        with ui.column().classes("gap-1"):
                            ui.label("Was macht diese Seite?").classes("font-semibold text-sm")
                            ui.label(
                                "Doc-Sorter liest den Text aus deinen Dokumenten und versucht automatisch zu erkennen, "
                                "um was es sich handelt — z.B. eine Rechnung von GASAG. "
                                "Wenn die Erkennung nicht sicher genug ist, landet das Dokument im Prüfungs-Ordner "
                                "und du kannst es manuell sortieren. Hier stellst du ein, wann Doc-Sorter 'unsicher' ist."
                            ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")

                # Mindest-Textmenge card
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("text_fields").classes("text-blue-500 text-lg")
                        ui.label("Wie viel Text muss lesbar sein?").classes("font-semibold text-sm")
                    ui.label(
                        "Doc-Sorter scannt den Text in deinen Dokumenten. Wenn ein Dokument kaum lesbaren Text enthält "
                        "(z.B. ein schlecht gescanntes Bild oder ein leeres Deckblatt), kann es nicht zuverlässig erkannt werden. "
                        "Dokumente mit weniger Text als dieser Schwellenwert werden automatisch zur manuellen Prüfung weitergeleitet."
                    ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-3")
                    with ui.row().classes("items-center gap-4"):
                        ui.label(f"{min_text} Zeichen").classes("text-2xl font-bold text-blue-500")
                        with ui.column().classes("gap-0"):
                            color = "text-green-500" if min_text <= 50 else "text-amber-500" if min_text <= 150 else "text-red-500"
                            label = "Niedrig — fast alle Dokumente werden automatisch sortiert" if min_text <= 50 else "Mittel — gute Balance (empfohlen)" if min_text <= 150 else "Hoch — viele Dokumente landen zur Kontrolle im Prüfungs-Ordner"
                            ui.label(label).classes(f"text-xs font-semibold {color}")
                            ui.label("Zum Ändern: oben auf 'Erweitert' klicken").classes("text-xs text-gray-400")

                # Pflichtfelder card
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("rule").classes("text-amber-500 text-lg")
                        ui.label("Was muss Doc-Sorter erkennen können?").classes("font-semibold text-sm")
                    ui.label(
                        "Diese Informationen müssen in jedem Dokument gefunden werden, damit Doc-Sorter es automatisch sortieren kann. "
                        "Fehlt eine davon — z.B. weil der Kundenname nicht lesbar ist — wandert das Dokument in den Prüfungs-Ordner "
                        "und du wirst informiert."
                    ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-3")
                    field_labels = {
                        "kunde": ("Kunde", "Wer hat das Dokument geschickt?"),
                        "dokumentenart": ("Dokumentenart", "Rechnung, Vertrag, Brief …"),
                        "land": ("Land", "Woher kommt der Absender?"),
                        "datum": ("Datum", "Wann wurde es ausgestellt?"),
                    }
                    with ui.element("div").classes("flex flex-col gap-2"):
                        for f in missing_fields:
                            lbl, hint = field_labels.get(f, (f, ""))
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("check_circle").classes("text-amber-500 text-base flex-shrink-0")
                                with ui.column().classes("gap-0"):
                                    ui.label(lbl).classes("text-xs font-semibold")
                                    if hint:
                                        ui.label(hint).classes("text-xs text-gray-400")

            else:
                # ── Advanced view ────────────────────────────────────────────
                min_len = ui.number(
                    label="Mindest-Textmenge im Dokument (Zeichen)",
                    value=min_text, min=0, max=1000,
                ).classes("ds-input")
                ui.label("Dokumente mit weniger Text werden als unsicher eingestuft und zur Prüfung weitergeleitet.").classes("text-xs text-gray-400 mb-3")

                uncertain = ui.input(
                    label="Als unsicher markieren wenn fehlt (kommagetrennt)",
                    value=", ".join(missing_fields),
                ).classes("w-full ds-input")
                ui.label("z.B. 'kunde, dokumentenart' — fehlt eines dieser Felder, geht das Dokument in den Prüfungs-Ordner.").classes("text-xs text-gray-400 mb-3")

                with ui.row().classes("gap-3 mt-4"):
                    def save() -> None:
                        conf["min_text_length"] = int(min_len.value)
                        conf["uncertain_if_missing"] = [x.strip() for x in uncertain.value.split(",") if x.strip()]
                        save_config(cfg)
                        _notify_saved("Erkennungs-Sicherheit")

                    ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

                    def discard() -> None:
                        orig_conf = original.get("confidence", {})
                        min_len.value = orig_conf.get("min_text_length", 30)
                        uncertain.value = ", ".join(orig_conf.get("uncertain_if_missing", ["kunde", "dokumentenart"]))
                        ui.notify("Änderungen verworfen", type="info")

                    ui.button("Verwerfen", on_click=discard, icon="undo").classes("ds-btn-ghost")

    def _toggle_conf_view() -> None:
        conf_mode["advanced"] = not conf_mode["advanced"]
        toggle_btn_conf.set_text("Einfache Ansicht" if conf_mode["advanced"] else "Erweitert")
        toggle_btn_conf.props("icon=tune" if not conf_mode["advanced"] else "icon=view_list")
        render_conf_view.refresh()

    toggle_btn_conf.on("click", lambda: _toggle_conf_view())
    render_conf_view()


# ---------------------------------------------------------------------------
# Tab: Verarbeitung
# ---------------------------------------------------------------------------
def _build_processing_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    proc = cfg.setdefault("processing", {})

    callout("Steuere wie viele Dokumente auf einmal verarbeitet werden und ob Änderungen direkt oder erst nach Bestätigung angewendet werden.", "info", "tune")

    proc_mode = {"advanced": False}

    with ui.row().classes("w-full items-center justify-between mb-2"):
        ui.label("Verarbeitungs-Einstellungen").classes("text-base font-semibold")
        toggle_btn_proc = ui.button("Erweitert", icon="tune").classes("ds-btn-ghost text-xs")

    proc_view_container = ui.column().classes("w-full gap-3")

    @ui.refreshable
    def render_proc_view() -> None:
        proc_view_container.clear()
        with proc_view_container:
            max_f = proc.get("max_files_per_run", 100)
            dry = proc.get("dry_run_default", True)

            if not proc_mode["advanced"]:
                # ── Simple view ──────────────────────────────────────────────

                # Intro
                with ui.card().classes("ds-card-flat w-full border-l-4 border-blue-400"):
                    with ui.row().classes("items-start gap-3"):
                        ui.icon("help_outline").classes("text-blue-400 text-xl mt-0.5 flex-shrink-0")
                        with ui.column().classes("gap-1"):
                            ui.label("Was macht diese Seite?").classes("font-semibold text-sm")
                            ui.label(
                                "Hier steuerst du, wie Doc-Sorter beim Sortieren vorgeht: "
                                "Wie viele Dokumente auf einmal bearbeitet werden und ob Dateien direkt verschoben werden "
                                "oder ob du zuerst eine Vorschau siehst."
                            ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")

                # Vorschau-Modus — most important, show first
                dry_border = "border-amber-400" if dry else "border-green-500"
                with ui.card().classes(f"ds-card-flat w-full border-l-4 {dry_border}"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("preview" if dry else "play_arrow").classes(
                            "text-amber-500 text-xl" if dry else "text-green-500 text-xl"
                        )
                        ui.label("Vorschau-Modus").classes("font-semibold text-sm")
                        ui.label("AKTIV" if dry else "INAKTIV").classes(
                            "text-xs font-bold px-2 py-0.5 rounded-full " +
                            ("bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300" if dry
                             else "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300")
                        )
                    if dry:
                        ui.label(
                            "🛡 Sicherheitsmodus ist eingeschaltet: Doc-Sorter analysiert deine Dokumente und zeigt dir, "
                            "wie sie sortiert würden — aber verschiebt noch nichts. "
                            "Du siehst das Ergebnis in der Vorschau und kannst selbst entscheiden, ob es so passt. "
                            "Empfohlen für den Anfang, solange du noch nicht sicher bist ob die Einstellungen stimmen."
                        ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")
                    else:
                        ui.label(
                            "⚡ Aktiv-Modus ist eingeschaltet: Doc-Sorter sortiert Dokumente direkt und verschiebt sie sofort "
                            "in den richtigen Ordner — ohne Rückfrage. "
                            "Stelle sicher, dass deine Einstellungen korrekt sind, bevor du diesen Modus verwendest."
                        ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")

                # Max files card
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("filter_list").classes("text-blue-500 text-xl")
                        ui.label("Wie viele Dokumente werden pro Durchlauf verarbeitet?").classes("font-semibold text-sm")
                    ui.label(
                        "Wenn du auf 'Sortieren' klickst, verarbeitet Doc-Sorter maximal so viele Dokumente auf einmal. "
                        "Bei sehr großen Archiven verhindert dieser Wert, dass die App zu langsam wird. "
                        "Bleiben Dokumente übrig, werden sie beim nächsten Durchlauf verarbeitet."
                    ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-3")
                    with ui.row().classes("items-center gap-4"):
                        ui.label(f"{max_f}").classes("text-3xl font-bold text-blue-500")
                        with ui.column().classes("gap-0"):
                            ui.label("Dokumente pro Durchlauf").classes("text-xs font-semibold text-gray-600 dark:text-gray-300")
                            color = "text-green-500" if max_f <= 100 else "text-amber-500" if max_f <= 500 else "text-red-500"
                            label = "Perfekt für den Alltag" if max_f <= 100 else "Gut für größere Archive" if max_f <= 500 else "Sehr hoch — kann die App verlangsamen"
                            ui.label(label).classes(f"text-xs {color}")

            else:
                # ── Advanced view ────────────────────────────────────────────
                max_files = ui.number(
                    label="Max Dateien pro Durchlauf",
                    value=max_f, min=1, max=10000,
                ).classes("ds-input")
                ui.label("Limitiert wie viele Dokumente pro Scan-Durchlauf verarbeitet werden. Bei großen Archiven empfehlen sich 100-200.").classes("text-xs text-gray-400 mb-3")

                dry_default = ui.switch("Vorschau als Standard", value=dry)
                ui.label(
                    "Vorschau-Modus: Dokumente werden analysiert aber NICHT verschoben. Zum echten Sortieren muss dieser Schalter AUS sein."
                ).classes("text-xs text-gray-400 ml-12")

                with ui.row().classes("gap-3 mt-4"):
                    def save() -> None:
                        proc["max_files_per_run"] = int(max_files.value)
                        proc["dry_run_default"] = dry_default.value
                        save_config(cfg)
                        _notify_saved("Verarbeitung")

                    ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

                    def discard() -> None:
                        orig_proc = original.get("processing", {})
                        max_files.value = orig_proc.get("max_files_per_run", 100)
                        dry_default.value = orig_proc.get("dry_run_default", True)
                        ui.notify("Änderungen verworfen", type="info")

                    ui.button("Verwerfen", on_click=discard, icon="undo").classes("ds-btn-ghost")

    def _toggle_proc_view() -> None:
        proc_mode["advanced"] = not proc_mode["advanced"]
        toggle_btn_proc.set_text("Einfache Ansicht" if proc_mode["advanced"] else "Erweitert")
        toggle_btn_proc.props("icon=tune" if not proc_mode["advanced"] else "icon=view_list")
        render_proc_view.refresh()

    toggle_btn_proc.on("click", lambda: _toggle_proc_view())
    render_proc_view()


# ---------------------------------------------------------------------------
# Tab: Benennungsregeln
# ---------------------------------------------------------------------------
def _build_taxonomy_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    taxonomy = cfg.setdefault("taxonomy", {})

    callout(
        "Bestimme wie sortierte Dateien benannt und in Ordner einsortiert werden. Verwende die Platzhalter um Datum, Kunde und Dokumentenart automatisch einzufügen.",
        "info", "account_tree",
    )

    tax_mode = {"advanced": False}

    # ── helpers ──────────────────────────────────────────────────────────────
    def _sample_preview(fn_pattern: str, folder_pattern: str) -> tuple[str, str]:
        sample = {
            "dokumentenart": "rechnung", "kunde": "GASAG", "land": "deutschland",
            "datum": datetime.now().strftime("%d.%m.%y"), "jahr": datetime.now().strftime("%Y"),
        }
        try:
            fn = fn_pattern.format(**sample) + ".pdf"
            folder = folder_pattern.format(**sample)
        except (KeyError, ValueError):
            fn = "(Muster ungültig)"
            folder = "(Muster ungültig)"
        return fn, folder

    # ── toggle header ─────────────────────────────────────────────────────────
    with ui.row().classes("w-full items-center justify-between mb-2"):
        ui.label("Benennungsregeln").classes("text-base font-semibold")
        toggle_btn_tax = ui.button("Erweitert", icon="tune").classes("ds-btn-ghost text-xs")

    tax_view_container = ui.column().classes("w-full gap-3")

    @ui.refreshable
    def render_tax_view() -> None:
        tax_view_container.clear()
        with tax_view_container:
            fn_pat = taxonomy.get("filename_pattern", "{dokumentenart}_{kunde}_{land}_{datum}")
            folder_pat = taxonomy.get("folder_pattern", "{dokumentenart}/{land}/{kunde}/{jahr}")
            fn_preview, folder_preview = _sample_preview(fn_pat, folder_pat)

            if not tax_mode["advanced"]:
                # ── Simple view ──────────────────────────────────────────────

                # Intro
                with ui.card().classes("ds-card-flat w-full border-l-4 border-blue-400"):
                    with ui.row().classes("items-start gap-3"):
                        ui.icon("help_outline").classes("text-blue-400 text-xl mt-0.5 flex-shrink-0")
                        with ui.column().classes("gap-1"):
                            ui.label("Wie werden Dokumente benannt und einsortiert?").classes("font-semibold text-sm")
                            ui.label(
                                "Wenn Doc-Sorter ein Dokument erkannt hat, speichert es dieses automatisch unter einem "
                                "bestimmten Dateinamen und in einem bestimmten Ordner. "
                                "Hier siehst du wie diese Namen aufgebaut werden — mit Beispieldaten einer "
                                "fiktiven Rechnung von GASAG."
                            ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")

                # Live preview card
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-3"):
                        ui.icon("preview").classes("text-blue-500 text-lg")
                        ui.label("Beispiel: So würde eine Rechnung von GASAG gespeichert").classes("font-semibold text-sm")
                    ui.label(
                        "Die Platzhalter in geschweiften Klammern {} werden automatisch mit den erkannten Informationen "
                        "aus dem Dokument gefüllt."
                    ).classes("text-xs text-gray-500 dark:text-gray-400 mb-3")
                    with ui.element("div").classes("bg-gray-50 dark:bg-gray-800 rounded-lg p-4 font-mono text-sm"):
                        with ui.row().classes("items-center gap-2 text-gray-500"):
                            ui.icon("folder_open").classes("text-amber-500")
                            ui.label("archive/  ← dein Archiv-Ordner")
                        with ui.row().classes("items-center gap-2 text-gray-600 ml-4"):
                            ui.icon("folder").classes("text-amber-400 text-base")
                            ui.label(folder_preview + "/").classes("text-blue-600 dark:text-blue-400")
                        with ui.row().classes("items-center gap-2 ml-8"):
                            ui.icon("description").classes("text-blue-500 text-base")
                            ui.label(fn_preview).classes("font-bold text-gray-800 dark:text-gray-100")

                # Pattern explanation cards
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("description").classes("text-blue-500 text-lg")
                        ui.label("Dateiname — wie heißt die Datei?").classes("font-semibold text-sm")
                    ui.label(
                        "Dieses Muster bestimmt den Namen jeder sortierten Datei. "
                        "Die Werte in {} werden automatisch ersetzt — z.B. wird {dokumentenart} zu 'rechnung', "
                        "{kunde} zu 'GASAG' und {datum} zum heutigen Datum."
                    ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-2")
                    ui.label("Aktuelles Muster:").classes("text-xs text-gray-400")
                    ui.label(fn_pat).classes("font-mono text-xs text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 rounded px-2 py-1 mt-1")

                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("folder").classes("text-amber-500 text-lg")
                        ui.label("Ordnerstruktur — wo landet die Datei?").classes("font-semibold text-sm")
                    ui.label(
                        "Dieses Muster legt fest, in welchem Unterordner eine Datei abgelegt wird. "
                        "Jedes / im Muster erzeugt eine neue Ordner-Ebene. "
                        "So bleiben deine Dokumente übersichtlich nach Kategorie, Land, Kunde und Jahr sortiert."
                    ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-2")
                    ui.label("Aktuelles Muster:").classes("text-xs text-gray-400")
                    ui.label(folder_pat).classes("font-mono text-xs text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 rounded px-2 py-1 mt-1")

                # ── Muster anpassen (direkt in einfacher Ansicht) ─────────────
                with ui.card().classes("ds-card-flat w-full border-l-4 border-green-400 mt-1"):
                    with ui.row().classes("items-center gap-2 mb-3"):
                        ui.icon("edit").classes("text-green-500 text-lg")
                        ui.label("Muster anpassen").classes("font-semibold text-sm")

                    fn_input_simple = ui.input(
                        label="Dateiname-Muster",
                        value=fn_pat,
                    ).classes("w-full ds-input mb-1")
                    ui.label("Platzhalter: {dokumentenart}, {kunde}, {land}, {datum}").classes("text-xs text-gray-400 mb-3")

                    folder_input_simple = ui.input(
                        label="Ordner-Muster",
                        value=folder_pat,
                    ).classes("w-full ds-input mb-1")
                    ui.label("Platzhalter: {dokumentenart}, {land}, {kunde}, {jahr}").classes("text-xs text-gray-400 mb-3")

                    with ui.row().classes("gap-3"):
                        def _save_simple(
                            fn_ref=fn_input_simple,
                            fo_ref=folder_input_simple,
                        ) -> None:
                            taxonomy["filename_pattern"] = fn_ref.value
                            taxonomy["folder_pattern"]   = fo_ref.value
                            save_config(cfg)
                            _notify_saved("Benennungsregeln")

                        def _reset_simple(
                            fn_ref=fn_input_simple,
                            fo_ref=folder_input_simple,
                        ) -> None:
                            orig_tax = original.get("taxonomy", {})
                            fn_ref.value = orig_tax.get(
                                "filename_pattern", "{dokumentenart}_{kunde}_{land}_{datum}"
                            )
                            fo_ref.value = orig_tax.get(
                                "folder_pattern", "{dokumentenart}/{land}/{kunde}/{jahr}"
                            )
                            ui.notify("Änderungen verworfen", type="info")

                        ui.button("Speichern", on_click=_save_simple, icon="save").classes("ds-btn-primary")
                        ui.button("Verwerfen", on_click=_reset_simple, icon="undo").classes("ds-btn-ghost")

            else:
                # ── Advanced view ────────────────────────────────────────────
                fn_input = ui.input(
                    label="Dateiname-Muster",
                    value=fn_pat,
                ).classes("w-full ds-input")
                ui.label("Platzhalter: {dokumentenart}, {kunde}, {land}, {datum}").classes("text-xs text-gray-400 mb-3")

                folder_input = ui.input(
                    label="Ordner-Muster",
                    value=folder_pat,
                ).classes("w-full ds-input")
                ui.label("Platzhalter: {dokumentenart}, {land}, {kunde}, {jahr}").classes("text-xs text-gray-400 mb-1")
                ui.label("Beispiel: {dokumentenart}/{land}/{kunde}/{jahr} → Rechnung/Deutschland/GASAG/2026/").classes("text-xs text-gray-400 mb-3")

                section_title("Vorschau", "preview")
                preview_container = ui.column().classes("w-full")

                def _update_preview() -> None:
                    preview_container.clear()
                    with preview_container:
                        fn, folder = _sample_preview(fn_input.value, folder_input.value)
                        with ui.card().classes("ds-card-flat w-full"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("folder").classes("text-amber-500")
                                ui.label(f"archive/{folder}/").classes("font-mono text-sm")
                            with ui.row().classes("items-center gap-2 ml-6"):
                                ui.icon("description").classes("text-blue-500")
                                ui.label(fn).classes("font-mono text-sm font-bold")

                _update_preview()
                fn_input.on("keyup", lambda _: _update_preview())
                folder_input.on("keyup", lambda _: _update_preview())

                with ui.row().classes("gap-3 mt-4"):
                    def save() -> None:
                        taxonomy["filename_pattern"] = fn_input.value
                        taxonomy["folder_pattern"] = folder_input.value
                        save_config(cfg)
                        _notify_saved("Benennungsregeln")

                    ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

                    def discard() -> None:
                        orig_tax = original.get("taxonomy", {})
                        fn_input.value = orig_tax.get("filename_pattern", "{dokumentenart}_{kunde}_{land}_{datum}")
                        folder_input.value = orig_tax.get("folder_pattern", "{dokumentenart}/{land}/{kunde}/{jahr}")
                        _update_preview()
                        ui.notify("Änderungen verworfen", type="info")

                    ui.button("Verwerfen", on_click=discard, icon="undo").classes("ds-btn-ghost")

    def _toggle_tax_view() -> None:
        tax_mode["advanced"] = not tax_mode["advanced"]
        toggle_btn_tax.set_text("Einfache Ansicht" if tax_mode["advanced"] else "Erweitert")
        toggle_btn_tax.props("icon=tune" if not tax_mode["advanced"] else "icon=view_list")
        render_tax_view.refresh()

    toggle_btn_tax.on("click", lambda: _toggle_tax_view())
    render_tax_view()


# ---------------------------------------------------------------------------
# Tab: KI-Unterstuetzung
# ---------------------------------------------------------------------------
def _build_llm_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    llm = cfg.setdefault("llm", {})

    callout(
        "KI-Unterstützung verbessert die Dokumentenerkennung. Ollama läuft lokal ohne API-Key, OpenAI und Anthropic benötigen einen API-Schlüssel.",
        "info", "smart_toy",
    )

    llm_mode = {"advanced": False}

    with ui.row().classes("w-full items-center justify-between mb-2"):
        ui.label("KI-Assistent Einstellungen").classes("text-base font-semibold")
        toggle_btn_llm = ui.button("Erweitert", icon="tune").classes("ds-btn-ghost text-xs")

    llm_view_container = ui.column().classes("w-full gap-3")

    @ui.refreshable
    def render_llm_view() -> None:
        llm_view_container.clear()
        with llm_view_container:
            is_enabled = llm.get("enabled", False)
            provider_val = llm.get("provider", "ollama")
            fallback_val = llm.get("fallback_only", True)
            cache_val = llm.get("cache_results", True)
            saved_model = llm.get("ollama_model", "llama3.2")
            ollama_host_val = llm.get("ollama_host", "http://localhost:11434")
            model_val = llm.get("model", "")

            provider_icons = {"ollama": ("🟢", "Lokal & kostenlos"), "openai": ("🔵", "GPT-4 (kostenpflichtig)"), "anthropic": ("🟣", "Claude (kostenpflichtig)")}

            if not llm_mode["advanced"]:
                # ── Simple view ──────────────────────────────────────────────

                # Intro
                with ui.card().classes("ds-card-flat w-full border-l-4 border-blue-400"):
                    with ui.row().classes("items-start gap-3"):
                        ui.icon("help_outline").classes("text-blue-400 text-xl mt-0.5 flex-shrink-0")
                        with ui.column().classes("gap-1"):
                            ui.label("Was ist der KI-Assistent?").classes("font-semibold text-sm")
                            ui.label(
                                "Doc-Sorter erkennt Dokumente zunächst alleine durch Textanalyse. "
                                "Der KI-Assistent hilft zusätzlich bei Dokumenten die schwer zu erkennen sind — "
                                "z.B. wenn Absender oder Dokumentenart unklar sind. "
                                "Die KI liest das Dokument und gibt eine zweite Meinung ab, bevor das Dokument einsortiert wird."
                            ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")

                # Main status card
                border_col = "border-green-500" if is_enabled else "border-gray-300 dark:border-gray-600"
                with ui.card().classes(f"ds-card-flat w-full border-l-4 {border_col}"):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("smart_toy").classes(
                            "text-3xl text-green-500" if is_enabled else "text-3xl text-gray-400"
                        )
                        with ui.column().classes("gap-1 flex-1"):
                            ui.label("KI-Assistent ist " + ("eingeschaltet ✓" if is_enabled else "ausgeschaltet")).classes(
                                "font-semibold text-base " + ("text-green-500" if is_enabled else "text-gray-400")
                            )
                            if is_enabled:
                                icon_p, desc_p = provider_icons.get(provider_val, ("🤖", provider_val))
                                ui.label(f"Verwendet wird: {icon_p} {provider_val.title()} — {desc_p}").classes("text-xs text-gray-500 dark:text-gray-400")
                            else:
                                ui.label(
                                    "Dokumente werden nur durch Textanalyse erkannt, ohne KI-Unterstützung."
                                ).classes("text-xs text-gray-500 dark:text-gray-400")

                # Provider status — only when enabled
                if is_enabled:
                    try:
                        from ...llm_classifier import get_available_providers
                        from ..theme import status_badge
                        providers_list = get_available_providers()
                        if providers_list:
                            with ui.card().classes("ds-card-flat w-full"):
                                with ui.row().classes("items-center gap-2 mb-2"):
                                    ui.icon("device_hub").classes("text-purple-500 text-lg")
                                    ui.label("Status der verfügbaren KI-Anbieter").classes("font-semibold text-sm")
                                ui.label(
                                    "Hier siehst du welche KI-Dienste eingerichtet sind und welcher gerade aktiv genutzt wird."
                                ).classes("text-xs text-gray-500 dark:text-gray-400 mb-2")
                                with ui.row().classes("gap-2 flex-wrap"):
                                    for p in providers_list:
                                        variant = "success" if p["ready"] else "warning" if p["installed"] else "error"
                                        lbl = "Bereit" if p["ready"] else "Kein API-Key hinterlegt" if p["installed"] else "Nicht installiert"
                                        status_badge(f"{p['name']}: {lbl}", variant)
                    except ImportError:
                        pass

                # Fallback card
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("savings").classes("text-amber-500 text-xl")
                        ui.label("Wann wird die KI eingesetzt?").classes("font-semibold text-sm")
                    if fallback_val:
                        ui.label(
                            "💡 Sparsamer Modus ist aktiv: Die KI wird nur dann befragt, wenn Doc-Sorter selbst unsicher ist "
                            "— also wenn es ein Dokument nicht eindeutig erkennen kann. "
                            "Bei klaren Dokumenten (z.B. einem eindeutigen Rechnungsformat das du öfter bekommst) "
                            "wird die KI gar nicht erst aufgerufen. Das spart Kosten und Ressourcen."
                        ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")
                    else:
                        ui.label(
                            "⚡ Vollmodus ist aktiv: Die KI analysiert jedes einzelne Dokument, unabhängig davon wie eindeutig "
                            "es erkannt wurde. Das liefert die höchste Genauigkeit, verbraucht aber mehr Ressourcen und "
                            "kann bei kostenpflichtigen Anbietern (OpenAI, Anthropic) Kosten verursachen."
                        ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")

                # Cache card
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("cached").classes("text-blue-500 text-xl" if cache_val else "text-gray-400 text-xl")
                        ui.label("Werden Ergebnisse gespeichert?").classes("font-semibold text-sm")
                    if cache_val:
                        ui.label(
                            "✅ Zwischenspeicher ist aktiv: Wenn Doc-Sorter ein ähnliches Dokument schon einmal gesehen hat, "
                            "merkt es sich das Ergebnis. Das nächste Mal wird dasselbe Dokument nicht nochmals an die KI "
                            "geschickt — es geht einfach schneller und spart bei kostenpflichtigen Diensten Geld."
                        ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")
                    else:
                        ui.label(
                            "⚠ Zwischenspeicher ist deaktiviert: Jedes Dokument wird immer neu analysiert, "
                            "auch wenn Doc-Sorter es schon kennt. Das kann bei kostenpflichtigen KI-Diensten unnötige "
                            "Kosten verursachen."
                        ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")

                with ui.row().classes("items-center gap-2 mt-1"):
                    ui.icon("vpn_key").classes("text-gray-400 text-sm")
                    ui.label('API-Keys einrichten, Anbieter wechseln oder Ollama testen? → "Erweitert" öffnen.').classes("text-xs text-gray-400")

            else:
                # ── Advanced view ────────────────────────────────────────────
                enabled = ui.switch("KI-Erkennung aktivieren", value=is_enabled)

                provider = ui.select(
                    label="Anbieter", options=["ollama", "openai", "anthropic"],
                    value=provider_val,
                ).classes("w-64 ds-input")

                model = ui.input(
                    label="Modell (leer = Standard)", value=model_val,
                    placeholder="z.B. gpt-4o-mini, claude-haiku-4-20250414",
                ).classes("w-full ds-input")
                ui.label("Standard: gpt-4o-mini (OpenAI) oder claude-haiku-4-20250414 (Anthropic)").classes("text-xs text-gray-400 mb-2")

                ollama_host = ui.input(
                    label="Ollama Host", value=ollama_host_val,
                    placeholder="http://localhost:11434",
                ).classes("w-full ds-input")
                ui.label("Ollama lokal installieren: https://ollama.com — dann z.B. 'ollama run llama3.2'").classes("text-xs text-gray-400 mb-2")

                ollama_model_select = ui.select(
                    label="Ollama Modell",
                    options=[saved_model] if saved_model else ["llama3.2"],
                    value=saved_model,
                ).classes("w-full ds-input")
                ui.label("Klicke 'Ollama testen' um installierte Modelle zu laden.").classes("text-xs text-gray-400 mb-2")

                ollama_status = ui.label("").classes("text-sm")

                async def test_ollama():
                    from ...llm_classifier import is_ollama_running, get_ollama_models
                    from nicegui import run as _run
                    host = ollama_host.value.strip()
                    ollama_status.set_text("Verbinde...")
                    running = await _run.io_bound(is_ollama_running, host)
                    if running:
                        models_list = await _run.io_bound(get_ollama_models, host)
                        if models_list:
                            ollama_model_select.options = models_list
                            if ollama_model_select.value not in models_list:
                                ollama_model_select.value = models_list[0]
                            ollama_status.set_text(f"✅ Ollama läuft — {len(models_list)} Modell(e) geladen")
                            ui.notify(f"Modelle: {', '.join(models_list)}", type="positive")
                        else:
                            ollama_status.set_text("⚠ Ollama läuft, aber keine Modelle installiert")
                            ui.notify("Kein Modell gefunden. Starte: ollama pull llama3.2", type="warning")
                    else:
                        ollama_status.set_text(f"❌ Ollama nicht erreichbar unter {host}")
                        ui.notify(f"Ollama nicht erreichbar unter {host}", type="negative")

                ui.button("Ollama testen & Modelle laden", on_click=test_ollama, icon="wifi").classes("ds-btn-secondary")

                fallback = ui.switch("Nur bei unsicheren Ergebnissen verwenden", value=fallback_val)
                ui.label("Wenn aktiv: KI wird nur gerufen wenn die automatische Erkennung unsicher ist. Spart Kosten.").classes("text-xs text-gray-400 ml-12 mb-2")

                cache_switch = ui.switch("Ergebnisse zwischenspeichern", value=cache_val)
                ui.label("Gleiche Dokumente werden nicht erneut an die KI gesendet.").classes("text-xs text-gray-400 ml-12 mb-2")

                # Status der Provider
                try:
                    from ...llm_classifier import get_available_providers
                    from ..theme import status_badge
                    providers_list = get_available_providers()
                    if providers_list:
                        with ui.row().classes("gap-3 mt-3 mb-2 flex-wrap"):
                            for p in providers_list:
                                variant = "success" if p["ready"] else "warning" if p["installed"] else "error"
                                lbl = "Bereit" if p["ready"] else "Kein API-Key" if p["installed"] else "Nicht installiert"
                                status_badge(f"{p['name']}: {lbl}", variant)
                except ImportError:
                    pass

                # API-Key Anleitung
                with ui.card().classes("ds-card-flat w-full mt-3"):
                    with ui.row().classes("items-center gap-2 mb-3"):
                        ui.icon("key").style("color:#f59e0b;font-size:1.3rem")
                        ui.label("Wie bekomme ich einen API-Schlüssel?").style(
                            "font-size:0.9rem;font-weight:700;color:var(--ds-text)"
                        )

                    with ui.expansion("🟢 Einfachste Option: Ollama (kostenlos, lokal)").classes("w-full ds-card mb-2"):
                        with ui.column().classes("gap-2 pl-2"):
                            ui.label("Kein API-Key nötig — läuft komplett auf deinem Computer.").style(
                                "font-size:0.8rem;color:#00e87d;font-weight:600"
                            )
                            for step, text in [
                                ("1", "ollama.com aufrufen und Ollama installieren (wie jede normale App)"),
                                ("2", "Terminal öffnen und eingeben: <code>ollama pull llama3.2</code>"),
                                ("3", "Oben 'Anbieter' auf <b>ollama</b> setzen und 'Ollama testen' klicken"),
                                ("4", "Fertig — KI läuft lokal, keine Kosten, kein Key"),
                            ]:
                                with ui.row().classes("items-start gap-3 py-1"):
                                    ui.label(step).style(
                                        "font-size:0.68rem;font-weight:700;padding:2px 7px;border-radius:50%;"
                                        "background:rgba(0,232,125,0.12);color:#00e87d;border:1px solid rgba(0,232,125,0.3);flex-shrink:0"
                                    )
                                    ui.html(f'<span style="font-size:0.8rem;color:var(--ds-text);line-height:1.5">{text}</span>',
                                            sanitize=False)

                    with ui.expansion("🔵 OpenAI (GPT-4, kostenpflichtig)").classes("w-full ds-card mb-2"):
                        with ui.column().classes("gap-2 pl-2"):
                            for step, text in [
                                ("1", "platform.openai.com aufrufen und registrieren"),
                                ("2", "API → API Keys → 'Create new secret key'"),
                                ("3", "Den Key kopieren (beginnt mit <code>sk-...</code>)"),
                                ("4", "Terminal öffnen und eingeben: <code>export OPENAI_API_KEY=sk-deinkey</code>"),
                                ("5", "App neu starten — der Status oben wechselt auf 'Bereit'"),
                            ]:
                                with ui.row().classes("items-start gap-3 py-1"):
                                    ui.label(step).style(
                                        "font-size:0.68rem;font-weight:700;padding:2px 7px;border-radius:50%;"
                                        "background:rgba(0,212,255,0.12);color:#00d4ff;border:1px solid rgba(0,212,255,0.3);flex-shrink:0"
                                    )
                                    ui.html(f'<span style="font-size:0.8rem;color:var(--ds-text);line-height:1.5">{text}</span>',
                                            sanitize=False)

                    with ui.expansion("🟣 Anthropic Claude (kostenpflichtig)").classes("w-full ds-card"):
                        with ui.column().classes("gap-2 pl-2"):
                            for step, text in [
                                ("1", "console.anthropic.com aufrufen und registrieren"),
                                ("2", "API Keys → 'Create Key'"),
                                ("3", "Den Key kopieren (beginnt mit <code>sk-ant-...</code>)"),
                                ("4", "Terminal: <code>export ANTHROPIC_API_KEY=sk-ant-deinkey</code>"),
                                ("5", "App neu starten"),
                            ]:
                                with ui.row().classes("items-start gap-3 py-1"):
                                    ui.label(step).style(
                                        "font-size:0.68rem;font-weight:700;padding:2px 7px;border-radius:50%;"
                                        "background:rgba(168,85,247,0.12);color:#a855f7;border:1px solid rgba(168,85,247,0.3);flex-shrink:0"
                                    )
                                    ui.html(f'<span style="font-size:0.8rem;color:var(--ds-text);line-height:1.5">{text}</span>',
                                            sanitize=False)

                with ui.row().classes("gap-3 mt-4"):
                    def save() -> None:
                        llm["enabled"] = enabled.value
                        llm["provider"] = provider.value
                        llm["model"] = model.value
                        llm["ollama_host"] = ollama_host.value
                        llm["ollama_model"] = ollama_model_select.value
                        llm["fallback_only"] = fallback.value
                        llm["cache_results"] = cache_switch.value
                        save_config(cfg)
                        _notify_saved("KI-Unterstützung")

                    ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

    def _toggle_llm_view() -> None:
        llm_mode["advanced"] = not llm_mode["advanced"]
        toggle_btn_llm.set_text("Einfache Ansicht" if llm_mode["advanced"] else "Erweitert")
        toggle_btn_llm.props("icon=tune" if not llm_mode["advanced"] else "icon=view_list")
        render_llm_view.refresh()

    toggle_btn_llm.on("click", lambda: _toggle_llm_view())
    render_llm_view()


# ---------------------------------------------------------------------------
# Tab: Automatische Verarbeitung
# ---------------------------------------------------------------------------
def _build_watcher_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    watcher = cfg.setdefault("watcher", {})

    callout(
        "Der Auto-Scanner überwacht deinen Eingangsordner und sortiert neue Dokumente automatisch — auch wenn die App im Hintergrund läuft.",
        "info", "sensors",
    )

    watch_mode = {"advanced": False}

    with ui.row().classes("w-full items-center justify-between mb-2"):
        ui.label("Auto-Scan Einstellungen").classes("text-base font-semibold")
        toggle_btn_watch = ui.button("Erweitert", icon="tune").classes("ds-btn-ghost text-xs")

    watch_view_container = ui.column().classes("w-full gap-3")

    @ui.refreshable
    def render_watch_view() -> None:
        watch_view_container.clear()
        with watch_view_container:
            is_enabled = watcher.get("enabled", False)
            poll_val = watcher.get("poll_interval", 5.0)
            debounce_val = watcher.get("debounce_seconds", 2.0)
            auto_val = watcher.get("auto_process", True)

            if not watch_mode["advanced"]:
                # ── Simple view ──────────────────────────────────────────────

                # Intro
                with ui.card().classes("ds-card-flat w-full border-l-4 border-blue-400"):
                    with ui.row().classes("items-start gap-3"):
                        ui.icon("help_outline").classes("text-blue-400 text-xl mt-0.5 flex-shrink-0")
                        with ui.column().classes("gap-1"):
                            ui.label("Was macht Auto-Scan?").classes("font-semibold text-sm")
                            ui.label(
                                "Auto-Scan beobachtet deinen Eingangsordner im Hintergrund. "
                                "Sobald du ein neues Dokument dort ablegst, erkennt Doc-Sorter es automatisch "
                                "und sortiert es direkt in den richtigen Ordner — ohne dass du etwas tun musst. "
                                "Du kannst also Dokumente einfach einscannen oder runterladen und Doc-Sorter erledigt den Rest."
                            ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")

                # Main status card
                status_col = "border-green-500" if is_enabled else "border-gray-300 dark:border-gray-600"
                with ui.card().classes(f"ds-card-flat w-full border-l-4 {status_col}"):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("sensors" if is_enabled else "sensors_off").classes(
                            "text-3xl text-green-500" if is_enabled else "text-3xl text-gray-400"
                        )
                        with ui.column().classes("gap-1 flex-1"):
                            ui.label("Auto-Scan ist " + ("eingeschaltet ✓" if is_enabled else "ausgeschaltet")).classes(
                                "font-semibold text-base " + ("text-green-500" if is_enabled else "text-gray-400")
                            )
                            if is_enabled:
                                ui.label(
                                    f"Doc-Sorter prüft alle {poll_val:.0f} Sekunden ob neue Dokumente im Eingangsordner liegen."
                                ).classes("text-xs text-gray-500 dark:text-gray-400")
                            else:
                                ui.label(
                                    "Dokumente werden nicht automatisch sortiert. Du musst das Sortieren manuell starten."
                                ).classes("text-xs text-gray-500 dark:text-gray-400")

                # Scan interval card
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("timer").classes("text-blue-500 text-xl")
                        ui.label("Wie oft schaut Doc-Sorter nach neuen Dokumenten?").classes("font-semibold text-sm")
                    ui.label(
                        "Doc-Sorter überprüft deinen Eingangsordner in regelmäßigen Abständen. "
                        "Ein kürzeres Intervall bedeutet schnellere Erkennung, aber etwas mehr Systemlast. "
                        "5 Sekunden ist ein guter Standardwert."
                    ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed mb-3")
                    with ui.row().classes("items-center gap-4"):
                        ui.label(f"Alle {poll_val:.0f} Sek.").classes("text-2xl font-bold text-blue-500")
                        ui.label("≈ " + (
                            "sehr schnell" if poll_val <= 5 else
                            "normal" if poll_val <= 15 else
                            "eher träge — neue Dokumente werden erst nach etwas Wartezeit sortiert"
                        )).classes("text-xs text-gray-500 dark:text-gray-400")

                # Auto-process card
                with ui.card().classes("ds-card-flat w-full"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("bolt" if auto_val else "notifications_active").classes(
                            "text-green-500 text-xl" if auto_val else "text-amber-500 text-xl"
                        )
                        ui.label("Was passiert wenn ein Dokument erkannt wird?").classes("font-semibold text-sm")
                    if auto_val:
                        ui.label(
                            "⚡ Sofortverarbeitung ist aktiv: Das Dokument wird automatisch sortiert und in den richtigen "
                            "Ordner verschoben, sobald es erkannt wird. Du bekommst eine Benachrichtigung was gemacht wurde."
                        ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")
                    else:
                        ui.label(
                            "🔔 Nur-Benachrichtigung ist aktiv: Doc-Sorter erkennt das Dokument, verschiebt es aber nicht. "
                            "Du bekommst stattdessen eine Benachrichtigung und kannst dann selbst entscheiden was passiert."
                        ).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")

            else:
                # ── Advanced view ────────────────────────────────────────────
                enabled = ui.switch("Automatische Verarbeitung aktivieren", value=is_enabled)

                with ui.row().classes("gap-4"):
                    poll = ui.number(
                        label="Prüf-Intervall (Sekunden)",
                        value=poll_val, min=1, max=60, step=1,
                    ).classes("ds-input")
                    debounce = ui.number(
                        label="Wartezeit bei neuen Dateien (Sek.)",
                        value=debounce_val, min=0.5, max=30, step=0.5,
                    ).classes("ds-input")

                auto_proc = ui.switch("Dateien sofort verarbeiten", value=auto_val)
                ui.label("Wenn deaktiviert: Es wird nur eine Benachrichtigung angezeigt.").classes("text-xs text-gray-400 ml-12")

                with ui.row().classes("gap-3 mt-4"):
                    def save() -> None:
                        watcher["enabled"] = enabled.value
                        watcher["poll_interval"] = float(poll.value)
                        watcher["debounce_seconds"] = float(debounce.value)
                        watcher["auto_process"] = auto_proc.value
                        save_config(cfg)
                        _notify_saved("Automatische Verarbeitung")

                    ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

    def _toggle_watch_view() -> None:
        watch_mode["advanced"] = not watch_mode["advanced"]
        toggle_btn_watch.set_text("Einfache Ansicht" if watch_mode["advanced"] else "Erweitert")
        toggle_btn_watch.props("icon=tune" if not watch_mode["advanced"] else "icon=view_list")
        render_watch_view.refresh()

    toggle_btn_watch.on("click", lambda: _toggle_watch_view())
    render_watch_view()


# ---------------------------------------------------------------------------
# Tab: Kalender-Pfade
# ---------------------------------------------------------------------------
def _build_calendar_editor(cfg: dict[str, Any], original: dict[str, Any]) -> None:
    """Kalender .ics-Dateipfade konfigurieren."""
    cal_paths: list[str] = cfg.setdefault("calendar_paths", [])

    callout(
        "Trage hier die Pfade zu deinen .ics-Kalenderdateien ein. "
        "Diese werden auf der Kalender-Seite und in der Morgenplanung angezeigt.",
        "info", "calendar_today",
    )

    container = ui.column().classes("w-full gap-2")

    def _refresh() -> None:
        container.clear()
        with container:
            if not cal_paths:
                ui.label("Noch keine Kalender-Dateien konfiguriert.").classes("text-gray-400 text-sm")
            for i, p in enumerate(cal_paths):
                with ui.row().classes("items-center gap-2 w-full"):
                    ui.icon("event").classes("text-cyan-400")
                    inp = ui.input(value=p, placeholder="/pfad/zur/datei.ics").classes("ds-input flex-1")

                    def _make_update(idx: int, field: ui.input):
                        def _upd(e):
                            cal_paths[idx] = e.value
                        field.on("change", _upd)

                    _make_update(i, inp)

                    def _remove(idx: int = i):
                        cal_paths.pop(idx)
                        _refresh()

                    ui.button(icon="delete", on_click=_remove).classes("ds-btn-ghost").props("flat dense")

    _refresh()

    ui.label("Tipp: Pfad zu einer .ics-Datei — z.B. ~/Downloads/kalender.ics oder absoluter Pfad.").classes("text-xs text-gray-400 mt-2")

    with ui.row().classes("gap-3 mt-3"):
        def _add() -> None:
            cal_paths.append("")
            _refresh()

        ui.button("Kalender hinzufügen", on_click=_add, icon="add").classes("ds-btn-secondary").tooltip("Pfad zu einer .ics-Kalenderdatei eintragen")

        def save() -> None:
            # Leere Eintraege entfernen
            cleaned = [p.strip() for p in cal_paths if p.strip()]
            cfg["calendar_paths"] = cleaned
            cal_paths.clear()
            cal_paths.extend(cleaned)
            save_config(cfg)
            _notify_saved("Kalender")
            _refresh()

        ui.button("Speichern", on_click=save, icon="save").classes("ds-btn-primary")

    # Vorhandene .ics-Dateien automatisch vorschlagen
    section_title("Automatisch erkannte .ics-Dateien", "search")
    found_container = ui.column().classes("w-full")

    async def _scan_ics() -> None:
        from nicegui import run as _run

        def _find():
            import glob
            home = Path.home()
            patterns = [
                str(home / "Downloads" / "*.ics"),
                str(home / "Documents" / "**" / "*.ics"),
                str(home / "Library" / "Calendars" / "**" / "*.ics"),
                "/tmp/*.ics",
            ]
            found = []
            for pat in patterns:
                found.extend(glob.glob(pat, recursive=True))
            return found[:20]

        files = await _run.io_bound(_find)
        found_container.clear()
        with found_container:
            if not files:
                ui.label("Keine .ics-Dateien gefunden.").classes("text-gray-400 text-sm")
            for f in files:
                with ui.row().classes("items-center gap-2"):
                    ui.label(f).classes("font-mono text-sm text-gray-300 flex-1")
                    def _add_path(path: str = f):
                        if path not in cal_paths:
                            cal_paths.append(path)
                            _refresh()
                            ui.notify(f"Hinzugefuegt: {path}", type="positive")
                    ui.button("Hinzufuegen", on_click=_add_path).classes("ds-btn-secondary text-xs")

    ui.button("Suchen", on_click=_scan_ics, icon="search").classes("ds-btn-ghost mt-2")
    with found_container:
        ui.label("Klicke 'Suchen' um .ics-Dateien zu finden.").classes("text-gray-400 text-sm")


# ---------------------------------------------------------------------------
# Haupt-Build-Funktion
# ---------------------------------------------------------------------------
def build() -> None:
    """Einstellungen-Seite aufbauen mit Tabs fuer jede Sektion."""
    cfg = load_config_raw()
    original = copy.deepcopy(cfg)

    page_header(
        "Einstellungen",
        "Doc-Sorter anpassen: Ordner, Dokumentenarten, Kunden",
    )

    # --- Tools & Features Schnellzugriff ---
    from nicegui import ui as _ui
    _tools = [
        ("E-Mail",        "/email",     "email",                 "#00d4ff", "Posteingang, Regeln, KI-Analyse, Konten verwalten"),
        ("Nachrichten",   "/messenger", "forum",                 "#00e87d", "WhatsApp, Telegram, Signal verbinden"),
        ("Kalender",      "/calendar",  "calendar_today",        "#f59e0b", "Termine und Fristen im Überblick"),
        ("Finanzen",      "/finance",   "account_balance_wallet","#a855f7", "Ausgaben, Abos und Rechnungen"),
        ("Bank",          "/bank",      "account_balance",       "#3b82f6", "CSV-Import und Kontoauszüge"),
        ("Automatisierung", "/scheduler", "schedule",              "#ef4444", "Automatische Hintergrundjobs"),
        ("Ordner",        "/folders",   "folder_special",        "#f97316", "Archiv-Verzeichnisbaum"),
        ("Dateien",       "/files",     "folder_open",           "#64748b", "Inbox, Archiv und Prüfung"),
    ]

    with _ui.card().classes("ds-card-flat w-full mb-6"):
        from ..theme import section_title as _st
        _st("Tools & Features", "apps")
        _ui.label("Alle Zusatz-Module auf einen Blick — klicke auf eine Kachel um dorthin zu wechseln.").style(
            "font-size:0.8rem;color:var(--ds-text-2);margin-bottom:12px"
        )
        with _ui.grid(columns=4).classes("gap-3 w-full"):
            for _name, _route, _icon, _color, _desc in _tools:
                def _make_nav(r=_route):
                    return lambda: _ui.navigate.to(r)
                with _ui.card().classes("ds-card-flat cursor-pointer").style(
                    f"border:1px solid {_color}22;transition:border 0.2s;min-height:72px"
                ).on("click", _make_nav()).on("mouseover", lambda e, c=_color: None).on("mouseout", lambda e, c=_color: None):
                    with _ui.row().classes("items-flex-start gap-3").style("align-items:flex-start"):
                        with _ui.element("div").style(
                            f"width:38px;height:38px;border-radius:9px;flex-shrink:0;"
                            f"background:{_color}15;border:1px solid {_color}30;"
                            f"display:flex;align-items:center;justify-content:center"
                        ):
                            _ui.icon(_icon).style(f"font-size:1.1rem;color:{_color}")
                        with _ui.column().classes("gap-0 flex-1 min-w-0"):
                            _ui.label(_name).style(
                                "font-size:0.85rem;font-weight:600;color:var(--ds-text)"
                            )
                            _ui.label(_desc).style(
                                "font-size:0.68rem;color:var(--ds-text-2);line-height:1.3;"
                                "overflow:hidden;white-space:normal;"
                                "display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical"
                            )

    with ui.tabs().classes("w-full ds-tabs") as tabs:
        tab_paths = ui.tab("Pfade", icon="folder")
        tab_taxonomy = ui.tab("Benennung", icon="account_tree")
        tab_filetypes = ui.tab("Dateitypen", icon="insert_drive_file")
        tab_ocr = ui.tab("Texterkennung", icon="document_scanner")
        tab_doctypes = ui.tab("Dokumentenarten", icon="description")
        tab_customers = ui.tab("Kunden", icon="people")
        tab_countries = ui.tab("Länder", icon="public")
        tab_confidence = ui.tab("Genauigkeit", icon="psychology")
        tab_processing = ui.tab("Verarbeitung", icon="tune")
        tab_llm = ui.tab("KI-Assistent", icon="smart_toy")
        tab_watcher = ui.tab("Auto-Scan", icon="sensors")

    with ui.tab_panels(tabs, value=tab_paths).classes("w-full"):
        with ui.tab_panel(tab_paths):
            _build_paths_editor(cfg, original)
        with ui.tab_panel(tab_taxonomy):
            _build_taxonomy_editor(cfg, original)
        with ui.tab_panel(tab_filetypes):
            _build_filetypes_editor(cfg, original)
        with ui.tab_panel(tab_ocr):
            _build_ocr_editor(cfg, original)
        with ui.tab_panel(tab_doctypes):
            _build_doctypes_editor(cfg, original)
        with ui.tab_panel(tab_customers):
            _build_customers_editor(cfg, original)
        with ui.tab_panel(tab_countries):
            _build_countries_editor(cfg, original)
        with ui.tab_panel(tab_confidence):
            _build_confidence_editor(cfg, original)
        with ui.tab_panel(tab_processing):
            _build_processing_editor(cfg, original)
        with ui.tab_panel(tab_llm):
            _build_llm_editor(cfg, original)
        with ui.tab_panel(tab_watcher):
            _build_watcher_editor(cfg, original)
