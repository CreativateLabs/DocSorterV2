"""Bank & Konto — CSV-Import und Transaktionsübersicht."""

from __future__ import annotations

import csv
import io
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nicegui import run, ui

from ..theme import empty_state, page_header, section_title
from ...config import load_config

logger = logging.getLogger(__name__)

_CARD_STYLE = (
    "background:rgba(10,22,40,0.85);"
    "border:1px solid rgba(0,212,255,0.2);"
    "border-radius:12px;"
    "padding:16px"
)
_COLOR_POS = "#00e87d"
_COLOR_NEG = "#ff3366"


# ---------------------------------------------------------------------------
# Persistenz
# ---------------------------------------------------------------------------


def _transactions_path(cfg: dict) -> Path:
    archive = cfg.get("paths", {}).get("archive", "~/Documents/DocSorter/output")
    p = Path(archive).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p / "_bank_transactions.json"


def load_transactions(cfg: dict) -> list[dict]:
    """Transaktionen aus {archive}/_bank_transactions.json laden."""
    path = _transactions_path(cfg)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("Fehler beim Laden der Transaktionen: %s", e)
        return []


def save_transactions(cfg: dict, txns: list[dict]) -> None:
    """Transaktionen in {archive}/_bank_transactions.json speichern."""
    path = _transactions_path(cfg)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(txns, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Fehler beim Speichern der Transaktionen: %s", e)


# ---------------------------------------------------------------------------
# CSV-Parser (Sparkasse, DKB, ING und generisch)
# ---------------------------------------------------------------------------


def _parse_amount(raw: str) -> float:
    """Deutschen Betrag-String zu float parsen (1.234,56 -> 1234.56)."""
    s = raw.strip().replace("\xa0", "").replace(" ", "")
    # Remove currency symbols
    for sym in ("€", "$", "EUR", "USD"):
        s = s.replace(sym, "")
    s = s.strip()
    if not s:
        return 0.0
    # German format: 1.234,56
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _detect_columns(header: list[str]) -> dict[str, str | None]:
    """Spaltenheader-Namen erkennen und mappen."""
    lower = {h.lower().strip(): h for h in header}

    def find(*candidates):
        for c in candidates:
            if c.lower() in lower:
                return lower[c.lower()]
        return None

    return {
        "date": find("buchungsdatum", "datum", "date", "valutadatum", "wertstellung"),
        "description": find(
            "verwendungszweck", "buchungstext", "description",
            "beguenstigter/zahlungspflichtiger", "auftraggeber/beguenstigter",
            "zahlungsempfaenger", "empfaenger", "glaeubiger-id",
        ),
        "amount": find("betrag", "umsatz", "amount", "betrag (eur)", "umsatz eur"),
        "balance": find("glaeubiger saldo", "kontostand", "saldo", "balance", "buchungstext"),
        "account": find("konto", "iban", "kontonummer", "account"),
    }


def parse_bank_csv(content: str | bytes, filename: str = "") -> tuple[list[dict], str]:
    """Bank-CSV parsen. Gibt (transaktionen, fehler_meldung) zurueck."""
    if isinstance(content, bytes):
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                content = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

    # Detect delimiter
    sample = content[:2000]
    delimiter = ";"
    if sample.count(",") > sample.count(";"):
        delimiter = ","

    # Skip leading metadata rows (some banks have bank name / account info first)
    lines = content.splitlines()
    header_idx = 0
    for i, line in enumerate(lines):
        if delimiter in line and len(line.split(delimiter)) >= 3:
            header_idx = i
            break

    cleaned = "\n".join(lines[header_idx:])

    try:
        reader = csv.DictReader(io.StringIO(cleaned), delimiter=delimiter)
        raw_rows = list(reader)
    except Exception as e:
        return [], f"CSV-Lesefehler: {e}"

    if not raw_rows:
        return [], "Keine Daten in der CSV-Datei gefunden."

    cols = _detect_columns(list(raw_rows[0].keys()))

    # Determine account name from filename or fallback
    account_name = Path(filename).stem if filename else "Import"

    transactions: list[dict] = []
    imported_at = datetime.now(tz=timezone.utc).isoformat()

    for row in raw_rows:
        try:
            date_raw = (cols["date"] and row.get(cols["date"], "")) or ""
            desc_raw = (cols["description"] and row.get(cols["description"], "")) or ""
            amount_raw = (cols["amount"] and row.get(cols["amount"], "")) or ""
            balance_raw = (cols["balance"] and row.get(cols["balance"], "")) or ""

            if not date_raw.strip() and not amount_raw.strip():
                continue

            amount = _parse_amount(amount_raw)
            balance = _parse_amount(balance_raw) if balance_raw.strip() else 0.0

            # Normalize date
            date_str = date_raw.strip()
            for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%y"):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    date_str = dt.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

            acc_raw = (cols["account"] and row.get(cols["account"], "")) or account_name
            transactions.append({
                "id": str(uuid.uuid4()),
                "date": date_str,
                "description": desc_raw.strip()[:500],
                "amount": amount,
                "balance": balance,
                "account": acc_raw.strip() or account_name,
                "imported_at": imported_at,
            })
        except Exception as e:
            logger.debug("Row parse error: %s — %s", e, row)
            continue

    if not transactions:
        return [], "Keine Transaktionen erkannt. Bitte Spaltenformat prüfen."

    return transactions, ""


# ---------------------------------------------------------------------------
# Hilfsfunktionen für Styling
# ---------------------------------------------------------------------------


def _amount_color(amount: float) -> str:
    return _COLOR_POS if amount >= 0 else _COLOR_NEG


def _fmt_amount(amount: float) -> str:
    sign = "+" if amount >= 0 else ""
    return f"{sign}{amount:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _mask_iban(iban: str) -> str:
    iban = iban.replace(" ", "")
    if len(iban) > 8:
        return f"{iban[:4]} •••• •••• {iban[-4:]}"
    return iban


# ---------------------------------------------------------------------------
# Tab: Import
# ---------------------------------------------------------------------------


def _build_import_tab(cfg: dict, txns_container) -> None:
    with ui.column().classes("w-full gap-4"):

        # Setup-Guide
        with ui.card().classes("ds-card-flat w-full"):
            with ui.row().classes("items-start gap-3 mb-2"):
                ui.icon("help_outline").style("font-size:1.5rem;color:#00d4ff;flex-shrink:0")
                with ui.column().classes("gap-1"):
                    ui.label("Wie importiere ich meine Bankdaten?").style(
                        "font-size:0.9rem;font-weight:700;color:var(--ds-text)"
                    )
                    ui.label(
                        "Du exportierst eine CSV-Datei aus dem Online-Banking deiner Bank und lädst sie hier hoch. "
                        "Die App erkennt automatisch Sparkasse, DKB, ING, Commerzbank und generische Formate."
                    ).style("font-size:0.8rem;color:var(--ds-text-2);line-height:1.6")

            with ui.expansion("🟢 Einfach: Sparkasse / ING / DKB").classes("w-full ds-card mb-2"):
                with ui.column().classes("gap-2 pl-2"):
                    for step, text in [
                        ("1", "<b>Sparkasse:</b> Online-Banking → Umsätze → Export → CSV-Format wählen"),
                        ("2", "<b>ING:</b> Banking → Mein Konto → Umsätze → Herunterladen → CSV"),
                        ("3", "<b>DKB:</b> Online-Banking → Konto → Kontoauszug → Export → CSV"),
                        ("4", "Die heruntergeladene Datei unten hochladen — fertig!"),
                    ]:
                        with ui.row().classes("items-start gap-3 py-1"):
                            ui.label(step).style(
                                "font-size:0.68rem;font-weight:700;padding:2px 7px;border-radius:50%;"
                                "background:rgba(0,232,125,0.12);color:#00e87d;border:1px solid rgba(0,232,125,0.3);flex-shrink:0"
                            )
                            ui.html(f'<span style="font-size:0.8rem;color:var(--ds-text);line-height:1.5">{text}</span>',
                                    sanitize=False)

            with ui.expansion("⚙️ Technisch: Anderes Format / API-Zugang").classes("w-full ds-card"):
                with ui.column().classes("gap-2 pl-2"):
                    ui.label("Für jede CSV mit Spalten Datum, Beschreibung, Betrag:").style(
                        "font-size:0.8rem;color:var(--ds-text-2)"
                    )
                    ui.html(
                        '<code style="font-size:0.75rem;color:#00d4ff;display:block;padding:8px;'
                        'background:rgba(0,0,0,0.3);border-radius:6px;margin:4px 0">'
                        'Datum;Beschreibung;Betrag<br>'
                        '01.03.2025;Amazon DE;-49,99<br>'
                        '02.03.2025;Gehalt;+3200,00</code>',
                        sanitize=False
                    )
                    ui.label(
                        "Trennzeichen: Semikolon (;) oder Komma (,) — wird automatisch erkannt. "
                        "Encoding: UTF-8 oder ISO-8859-1 (Windows-Exporte)."
                    ).style("font-size:0.78rem;color:var(--ds-text-2);line-height:1.5")

        with ui.element("div").style(_CARD_STYLE):
            ui.label("CSV-Datei hochladen").style(
                "font-size:0.8rem;font-weight:700;color:rgba(0,212,255,0.8);"
                "text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px"
            )
            ui.label(
                "Unterstützte Formate: Sparkasse, DKB, ING und generische Bank-CSV "
                "(Trennzeichen: ; oder ,)"
            ).style("font-size:0.78rem;color:rgba(148,163,184,0.8);margin-bottom:12px")

            preview_container = ui.column().classes("w-full gap-2")
            parsed_rows_state: list[dict] = []

            def handle_upload(e):
                nonlocal parsed_rows_state
                preview_container.clear()
                try:
                    content = e.content.read()
                    filename = getattr(e, "name", "")
                    rows, err = parse_bank_csv(content, filename)
                    parsed_rows_state.clear()
                    parsed_rows_state.extend(rows)
                    with preview_container:
                        if err:
                            ui.label(f"Fehler: {err}").style(f"color:{_COLOR_NEG};font-size:0.82rem")
                            return
                        ui.label(f"{len(rows)} Transaktionen erkannt — Vorschau (erste 10):").style(
                            "font-size:0.8rem;color:rgba(0,212,255,0.8);font-weight:600"
                        )
                        cols = ["Datum", "Beschreibung", "Betrag"]
                        rows_data = [
                            [r["date"], r["description"][:60], _fmt_amount(r["amount"])]
                            for r in rows[:10]
                        ]
                        tbl = ui.table(columns=[
                            {"name": "date", "label": "Datum", "field": "date"},
                            {"name": "desc", "label": "Beschreibung", "field": "desc"},
                            {"name": "amount", "label": "Betrag", "field": "amount"},
                        ], rows=[
                            {"date": r[0], "desc": r[1], "amount": r[2]}
                            for r in rows_data
                        ]).classes("w-full").style(
                            "background:rgba(0,0,0,0.3);border-radius:8px;"
                            "font-size:0.78rem"
                        )
                except Exception as exc:
                    with preview_container:
                        ui.label(f"Upload-Fehler: {exc}").style(
                            f"color:{_COLOR_NEG};font-size:0.82rem"
                        )

            def do_import():
                if not parsed_rows_state:
                    ui.notify("Keine Daten zum Importieren.", type="warning")
                    return

                async def _save():
                    existing = await run.io_bound(load_transactions, cfg)
                    existing_ids = {t["id"] for t in existing}
                    new_rows = [r for r in parsed_rows_state if r["id"] not in existing_ids]
                    merged = new_rows + existing
                    merged.sort(key=lambda x: x.get("date", ""), reverse=True)
                    await run.io_bound(save_transactions, cfg, merged)
                    ui.notify(f"{len(new_rows)} Transaktionen importiert.", type="positive")
                    parsed_rows_state.clear()
                    preview_container.clear()
                    txns_container.refresh()

                import asyncio
                asyncio.ensure_future(_save())

            ui.upload(
                label="CSV hier ablegen oder klicken",
                on_upload=handle_upload,
                auto_upload=True,
            ).props("accept=.csv flat bordered").classes("w-full").style(
                "border:1px dashed rgba(0,212,255,0.3);border-radius:8px;"
                "background:rgba(0,0,0,0.2)"
            )

            with preview_container:
                pass

            ui.button(
                "Importieren",
                icon="cloud_upload",
                on_click=do_import,
            ).props("unelevated no-caps").style(
                "background:rgba(0,212,255,0.15);color:#00d4ff;"
                "border:1px solid rgba(0,212,255,0.3);border-radius:8px;"
                "margin-top:12px"
            )


# ---------------------------------------------------------------------------
# Tab: Transaktionen
# ---------------------------------------------------------------------------


@ui.refreshable
def _txns_table(cfg: dict) -> None:
    txns = load_transactions(cfg)
    if not txns:
        empty_state("account_balance", "Keine Transaktionen", "Importiere eine Bank-CSV-Datei.")
        return

    section_title(f"{len(txns)} Transaktionen", "receipt_long")

    with ui.element("div").style(_CARD_STYLE + ";overflow-x:auto"):
        with ui.column().classes("w-full gap-0"):
            # Header row
            with ui.row().classes("w-full gap-0").style(
                "border-bottom:1px solid rgba(0,212,255,0.2);padding:6px 0;"
                "font-size:0.72rem;font-weight:700;color:rgba(0,212,255,0.7);"
                "text-transform:uppercase;letter-spacing:0.04em"
            ):
                ui.label("Datum").style("width:100px;flex-shrink:0")
                ui.label("Beschreibung").style("flex:1;min-width:200px")
                ui.label("Betrag").style("width:120px;text-align:right;flex-shrink:0")
                ui.label("Konto").style("width:140px;flex-shrink:0;padding-left:12px")
                ui.label("").style("width:120px;flex-shrink:0")  # Aktionen-Spalte

            for txn in txns[:200]:
                amount = txn.get("amount", 0)
                color = _amount_color(amount)
                with ui.row().classes("w-full gap-0 items-center").style(
                    "border-bottom:1px solid rgba(255,255,255,0.04);"
                    "padding:7px 0;font-size:0.78rem"
                ):
                    ui.label(txn.get("date", "")).style(
                        "width:100px;flex-shrink:0;color:rgba(148,163,184,0.9)"
                    )
                    ui.label(txn.get("description", "")[:80]).style(
                        "flex:1;min-width:200px;color:rgba(226,232,240,0.9);"
                        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis"
                    )
                    ui.label(_fmt_amount(amount)).style(
                        f"width:120px;text-align:right;flex-shrink:0;"
                        f"font-weight:600;color:{color}"
                    )
                    ui.label(txn.get("account", "")[:20]).style(
                        "width:140px;flex-shrink:0;padding-left:12px;"
                        "color:rgba(148,163,184,0.7);font-size:0.72rem"
                    )
                    # Als Ausgabe übernehmen
                    def _add_expense(t: dict = txn) -> None:
                        try:
                            from ...assistant_store import add_expense
                            desc = t.get("description", "Bank-Transaktion")[:80]
                            amt = abs(t.get("amount", 0))
                            date_str = t.get("date", "")
                            add_expense(
                                description=desc,
                                amount=amt,
                                category="Bank",
                                date=date_str,
                            )
                            ui.notify(f"Ausgabe gespeichert: {desc[:40]}", color="positive")
                        except Exception as exc:
                            ui.notify(f"Fehler: {exc}", color="negative")

                    if amount < 0:  # Nur Ausgaben (negative Betraege)
                        ui.button(
                            "→ Ausgabe",
                            on_click=_add_expense,
                        ).style(
                            "background:rgba(255,51,102,0.1);color:#ff3366;"
                            "border:1px solid rgba(255,51,102,0.25);border-radius:6px;"
                            "padding:2px 8px;font-size:0.72rem;cursor:pointer;"
                            "width:110px;flex-shrink:0"
                        ).props("flat dense no-caps")
                    else:
                        ui.element("div").style("width:110px;flex-shrink:0")


# ---------------------------------------------------------------------------
# Tab: Konten
# ---------------------------------------------------------------------------


def _build_accounts_tab(cfg: dict) -> None:
    txns = load_transactions(cfg)

    # Aggregate by account
    accounts: dict[str, dict] = {}
    for t in txns:
        acc = t.get("account", "Unbekannt")
        if acc not in accounts:
            accounts[acc] = {"name": acc, "count": 0, "last_import": ""}
        accounts[acc]["count"] += 1
        imp = t.get("imported_at", "")
        if imp > accounts[acc]["last_import"]:
            accounts[acc]["last_import"] = imp

    if not accounts:
        empty_state("account_balance", "Keine Konten", "Importiere eine Bank-CSV-Datei.")
        return

    section_title(f"{len(accounts)} Konten", "account_balance")

    for acc_name, info in accounts.items():
        with ui.element("div").style(_CARD_STYLE + ";margin-bottom:8px"):
            with ui.row().classes("items-center gap-3 w-full"):
                ui.icon("account_balance").style(
                    "font-size:1.4rem;color:rgba(0,212,255,0.7)"
                )
                with ui.column().classes("gap-0 flex-1"):
                    ui.label(acc_name).style(
                        "font-size:0.88rem;font-weight:600;color:rgba(226,232,240,0.95)"
                    )
                    # Try to detect IBAN-like strings
                    iban_like = ""
                    if len(acc_name) > 15 and acc_name[:2].isalpha():
                        iban_like = _mask_iban(acc_name)
                    if iban_like:
                        ui.label(iban_like).style(
                            "font-size:0.72rem;color:rgba(148,163,184,0.7)"
                        )
                with ui.column().classes("items-end gap-0"):
                    ui.label(f"{info['count']} Transaktionen").style(
                        "font-size:0.78rem;color:rgba(0,232,125,0.8);font-weight:600"
                    )
                    if info["last_import"]:
                        try:
                            dt = datetime.fromisoformat(info["last_import"])
                            last_str = dt.strftime("%d.%m.%Y %H:%M")
                        except Exception:
                            last_str = info["last_import"][:10]
                        ui.label(f"Import: {last_str}").style(
                            "font-size:0.7rem;color:rgba(148,163,184,0.5)"
                        )


# ---------------------------------------------------------------------------
# Seiten-Einstiegspunkt
# ---------------------------------------------------------------------------


def build() -> None:
    """Bank-Seite aufbauen."""
    cfg = load_config()

    page_header("Bank & Konto", "CSV-Import und Transaktionsübersicht")

    with ui.tabs().classes("ds-tabs w-full") as tabs:
        tab_import = ui.tab("Import", icon="upload_file")
        tab_txns = ui.tab("Transaktionen", icon="receipt_long")
        tab_accounts = ui.tab("Konten", icon="account_balance")

    with ui.tab_panels(tabs, value=tab_import).classes("w-full mt-4"):
        with ui.tab_panel(tab_import):
            _build_import_tab(cfg, _txns_table)

        with ui.tab_panel(tab_txns):
            _txns_table(cfg)

        with ui.tab_panel(tab_accounts):
            _build_accounts_tab(cfg)
