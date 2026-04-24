"""Finanzen — Rechnungen, Monatsübersicht und Dokument-Todo-Ausgabe-Verknüpfungen."""

from __future__ import annotations

import csv
import io
from datetime import datetime, date

from nicegui import run, ui

from ...assistant_store import (
    get_invoices,
    add_invoice,
    delete_invoice,
    get_expenses,
    get_todos,
    link_invoice_todo,
    unlink_invoice_todo,
    link_todo_doc,
    unlink_todo_doc,
    get_linked_docs,
    get_linked_todos_for_invoice,
)
from ..theme import empty_state, page_header, section_title, status_badge

# ---------------------------------------------------------------------------
# Shared style constants
# ---------------------------------------------------------------------------

_CARD = (
    "background:rgba(10,22,40,0.85);"
    "border:1px solid rgba(0,212,255,0.2);"
    "border-radius:12px;"
    "padding:16px;"
    "backdrop-filter:blur(8px);"
)

_BTN_CYAN = (
    "color:#00d4ff;"
    "border:1px solid rgba(0,212,255,0.35);"
    "border-radius:8px;"
    "padding:4px 14px;"
)

_BTN_RED = (
    "color:#ff3366;"
    "border:1px solid rgba(255,51,102,0.3);"
    "border-radius:8px;"
    "padding:2px 10px;"
)

_CATEGORIES = [
    "Sonstiges", "Software", "Hardware", "Büro", "Reise", "Marketing",
    "Personal", "Miete", "Strom", "Versicherung", "Steuer", "Beratung",
]


def _category_color(cat: str) -> str:
    mapping = {
        "software":    "#3b82f6",
        "hardware":    "#06b6d4",
        "büro":        "#a855f7",
        "reise":       "#f97316",
        "marketing":   "#ec4899",
        "personal":    "#22c55e",
        "miete":       "#eab308",
        "strom":       "#ff9f0a",
        "versicherung":"#64748b",
        "steuer":      "#ef4444",
        "beratung":    "#8b5cf6",
    }
    return mapping.get(cat.lower(), "#64748b")


def _fmt_amount(amount: float) -> str:
    try:
        return f"{float(amount):,.2f} €"
    except (ValueError, TypeError):
        return f"{amount} €"


def _last_12_months() -> list[str]:
    today = date.today()
    months = []
    for i in range(12):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append(f"{y}-{m:02d}")
    return months


# ---------------------------------------------------------------------------
# Tab 1: Rechnungen (Invoices)
# ---------------------------------------------------------------------------

def _build_invoices_tab() -> None:
    state: dict = {"invoices": []}

    container = ui.column().classes("w-full gap-3")

    async def _reload():
        state["invoices"] = await run.io_bound(get_invoices)
        _redraw()

    def _redraw():
        container.clear()
        invoices = state["invoices"]
        total = sum(float(inv.get("amount", 0)) for inv in invoices)

        with container:
            # Header row
            with ui.row().classes("items-center justify-between w-full"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("receipt_long").style("color:#00d4ff;font-size:1.4rem")
                    ui.label(f"Rechnungen ({len(invoices)})").style(
                        "font-size:1.1rem;font-weight:700;color:#00d4ff"
                    )
                    ui.label(f"Gesamt: {_fmt_amount(total)}").style(
                        "font-size:0.95rem;font-weight:600;color:#00e87d;margin-left:8px"
                    )
                ui.button(
                    "Rechnung erfassen", icon="add",
                    on_click=lambda: _open_add_dialog(),
                ).props("flat dense no-caps").style(_BTN_CYAN).tooltip("Neue Rechnung manuell hinzufügen")

            ui.separator().style("border-color:rgba(0,212,255,0.1);margin:4px 0")

            if not invoices:
                empty_state("receipt", "Noch keine Rechnungen erfasst", "Klicke auf 'Neue Rechnung' um deine erste Rechnung einzutragen — oder lass Rechnungen automatisch aus dem Archiv erkennen.")
                return

            for inv in reversed(invoices):
                _render_invoice_card(inv, _reload)

    def _open_add_dialog():
        f: dict = {
            "vendor": "", "amount": "", "date": str(date.today()),
            "category": "Sonstiges", "invoice_number": "", "source_file": "", "notes": "",
        }

        with ui.dialog() as dlg, ui.card().style(
            "background:#0a1628;border:1px solid rgba(0,212,255,0.3);"
            "border-radius:14px;padding:24px;min-width:420px"
        ):
            ui.label("Neue Rechnung").style(
                "font-size:1.1rem;font-weight:700;color:#00d4ff;margin-bottom:8px"
            )

            vendor_inp = ui.input("Lieferant / Anbieter", placeholder="z.B. GASAG AG, Amazon").props("dense dark outlined").classes("w-full")
            amount_inp = ui.input("Betrag (€)", placeholder="z.B. 49.90").props("dense dark outlined").classes("w-full")
            date_inp = ui.input("Datum", value=str(date.today()), placeholder="JJJJ-MM-TT").props("dense dark outlined").classes("w-full")
            inv_num_inp = ui.input("Rechnungsnummer (optional)", placeholder="z.B. RE-2024-0042").props("dense dark outlined").classes("w-full")
            cat_sel = ui.select(_CATEGORIES, value="Sonstiges", label="Kategorie").props("dense dark outlined").classes("w-full")
            src_inp = ui.input("Quelldatei (optional)", placeholder="Pfad zur PDF-Datei").props("dense dark outlined").classes("w-full")
            notes_inp = ui.input("Notizen (optional)", placeholder="z.B. Jahresrechnung, bereits bezahlt").props("dense dark outlined").classes("w-full")

            async def _save():
                try:
                    amt = float(amount_inp.value.replace(",", "."))
                except ValueError:
                    ui.notify("Ungültiger Betrag", color="red", timeout=3000)
                    return
                await run.io_bound(
                    add_invoice,
                    vendor_inp.value or "Unbekannt",
                    amt,
                    date_inp.value or str(date.today()),
                    cat_sel.value or "Sonstiges",
                    inv_num_inp.value,
                    src_inp.value,
                    notes_inp.value,
                )
                dlg.close()
                await _reload()
                ui.notify("Rechnung gespeichert", color="green", timeout=2500)

            with ui.row().classes("gap-2 justify-end w-full mt-4"):
                ui.button("Abbrechen", on_click=dlg.close).props("flat dense no-caps").style("color:#94a3b8")
                ui.button("Speichern", on_click=_save).props("unelevated dense no-caps").style(
                    "background:rgba(0,212,255,0.15);color:#00d4ff;"
                    "border:1px solid rgba(0,212,255,0.4);border-radius:8px;padding:4px 18px"
                )

        dlg.open()

    # Initial load
    async def _init():
        await _reload()

    ui.timer(0.05, _init, once=True)


def _render_invoice_card(inv: dict, reload_fn) -> None:
    cat = inv.get("category", "Sonstiges")
    cat_color = _category_color(cat)

    with ui.card().style(_CARD).classes("w-full"):
        with ui.row().classes("items-start justify-between w-full gap-2"):
            with ui.column().classes("gap-1 flex-1"):
                with ui.row().classes("items-center gap-3 flex-wrap"):
                    ui.label(inv.get("vendor", "—")).style(
                        "font-size:0.95rem;font-weight:600;color:var(--ds-text,#e2e8f0)"
                    )
                    ui.label(_fmt_amount(inv.get("amount", 0))).style(
                        "font-size:1rem;font-weight:700;color:#00d4ff"
                    )
                    ui.label(cat).style(
                        f"font-size:0.72rem;font-weight:600;padding:2px 10px;"
                        f"border-radius:20px;background:{cat_color}22;color:{cat_color};"
                        f"border:1px solid {cat_color}55;text-transform:uppercase;letter-spacing:0.04em"
                    )

                with ui.row().classes("items-center gap-4 flex-wrap"):
                    ui.label(f"Datum: {inv.get('date', '—')}").style(
                        "font-size:0.78rem;color:var(--ds-text-2,#94a3b8)"
                    )
                    if inv.get("invoice_number"):
                        ui.label(f"Nr: {inv['invoice_number']}").style(
                            "font-size:0.78rem;color:var(--ds-text-2,#94a3b8)"
                        )
                    if inv.get("source_file"):
                        ui.label(f"Datei: {inv['source_file']}").style(
                            "font-size:0.72rem;color:#a78bfa;cursor:pointer"
                        ).tooltip(inv["source_file"])

                if inv.get("notes"):
                    ui.label(inv["notes"]).style(
                        "font-size:0.78rem;color:var(--ds-text-3,#475569);font-style:italic"
                    )

            async def _del(inv_id=inv["id"]):
                await run.io_bound(delete_invoice, inv_id)
                await reload_fn()
                ui.notify("Rechnung gelöscht", color="orange", timeout=2000)

            ui.button(icon="delete_outline", on_click=_del).props("flat round dense").style(
                "color:#ff3366;opacity:0.7"
            ).tooltip("Rechnung dauerhaft entfernen")


# ---------------------------------------------------------------------------
# Tab 2: Monatsübersicht
# ---------------------------------------------------------------------------

def _build_monthly_tab() -> None:
    months = _last_12_months()
    selected_month = {"value": months[0]}
    container = ui.column().classes("w-full gap-4")

    async def _reload():
        invoices = await run.io_bound(get_invoices)
        expenses = await run.io_bound(get_expenses)
        _redraw(invoices, expenses)

    def _redraw(invoices: list, expenses: list):
        container.clear()
        m = selected_month["value"]

        # Filter invoices for month
        month_invoices = [
            inv for inv in invoices
            if str(inv.get("date", "")).startswith(m)
        ]
        # Filter expenses for month (recurring ones always counted)
        month_expenses = [e for e in expenses if e.get("active", True)]

        with container:
            # Month selector + export
            with ui.row().classes("items-center justify-between w-full"):
                month_sel = ui.select(
                    months, value=selected_month["value"], label="Monat"
                ).props("dense dark outlined").style("min-width:160px")

                def _on_month_change(e):
                    selected_month["value"] = e.value
                    async def _r():
                        await _reload()
                    ui.timer(0.01, _r, once=True)

                month_sel.on("update:model-value", _on_month_change)

                async def _export():
                    buf = io.StringIO()
                    writer = csv.writer(buf)
                    writer.writerow(["Typ", "Name/Lieferant", "Betrag", "Kategorie", "Datum"])
                    for inv in month_invoices:
                        writer.writerow([
                            "Rechnung",
                            inv.get("vendor", ""),
                            inv.get("amount", ""),
                            inv.get("category", ""),
                            inv.get("date", ""),
                        ])
                    for exp in month_expenses:
                        writer.writerow([
                            "Ausgabe",
                            exp.get("name", ""),
                            exp.get("amount", ""),
                            exp.get("category", ""),
                            exp.get("created", ""),
                        ])
                    csv_content = buf.getvalue()
                    ui.download(csv_content.encode("utf-8"), f"finanzen_{m}.csv")
                    ui.notify("CSV exportiert", color="green", timeout=2000)

                ui.button("Export CSV", icon="download", on_click=_export).props(
                    "flat dense no-caps"
                ).style(_BTN_CYAN)

            ui.separator().style("border-color:rgba(0,212,255,0.1);margin:4px 0")

            # Category totals from invoices
            cat_totals: dict[str, float] = {}
            for inv in month_invoices:
                cat = inv.get("category", "Sonstiges")
                try:
                    cat_totals[cat] = cat_totals.get(cat, 0.0) + float(inv.get("amount") or 0)
                except (TypeError, ValueError):
                    pass

            invoice_total = sum(cat_totals.values())
            expense_total = 0.0
            for e in month_expenses:
                try:
                    expense_total += float(e.get("amount") or 0)
                except (TypeError, ValueError):
                    pass
            grand_total = invoice_total + expense_total

            # Category breakdown table
            if cat_totals:
                section_title("Rechnungen nach Kategorie", "receipt_long")
                with ui.column().classes("w-full gap-2"):
                    for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
                        color = _category_color(cat)
                        pct = (total / invoice_total * 100) if invoice_total > 0 else 0
                        with ui.card().style(
                            f"background:rgba(10,22,40,0.7);"
                            f"border:1px solid {color}44;"
                            f"border-radius:10px;padding:10px 16px;"
                        ).classes("w-full"):
                            with ui.row().classes("items-center justify-between w-full"):
                                with ui.row().classes("items-center gap-3"):
                                    ui.element("div").style(
                                        f"width:10px;height:10px;border-radius:50%;background:{color}"
                                    )
                                    ui.label(cat).style(
                                        f"font-size:0.88rem;font-weight:600;color:{color}"
                                    )
                                with ui.row().classes("items-center gap-4"):
                                    ui.label(f"{pct:.1f}%").style(
                                        "font-size:0.8rem;color:var(--ds-text-2,#94a3b8)"
                                    )
                                    ui.label(_fmt_amount(total)).style(
                                        "font-size:0.95rem;font-weight:700;color:#00d4ff"
                                    )
            else:
                empty_state("receipt", "Keine Rechnungen", f"Keine Rechnungen für {m}.")

            # Expenses section
            if month_expenses:
                section_title("Laufende Ausgaben", "autorenew")
                with ui.column().classes("w-full gap-2"):
                    for exp in month_expenses:
                        with ui.card().style(_CARD).classes("w-full"):
                            with ui.row().classes("items-center justify-between w-full"):
                                with ui.row().classes("items-center gap-3"):
                                    ui.icon("repeat").style("color:#a78bfa;font-size:1rem")
                                    ui.label(exp.get("name", "—")).style(
                                        "font-size:0.88rem;font-weight:600;color:var(--ds-text,#e2e8f0)"
                                    )
                                    ui.label(exp.get("cycle", "")).style(
                                        "font-size:0.72rem;color:var(--ds-text-2,#94a3b8)"
                                    )
                                ui.label(_fmt_amount(exp.get("amount", 0))).style(
                                    "font-size:0.95rem;font-weight:700;color:#a78bfa"
                                )

            # Grand total
            ui.separator().style("border-color:rgba(0,212,255,0.1);margin:8px 0")
            with ui.row().classes("items-center justify-end w-full gap-4"):
                ui.label("Gesamtausgaben:").style(
                    "font-size:1rem;font-weight:600;color:var(--ds-text-2,#94a3b8)"
                )
                ui.label(_fmt_amount(grand_total)).style(
                    "font-size:1.5rem;font-weight:800;color:#00d4ff;letter-spacing:-0.02em"
                )

    async def _init():
        await _reload()

    ui.timer(0.05, _init, once=True)


# ---------------------------------------------------------------------------
# Tab 3: Verbindungen (Document-Todo-Expense links)
# ---------------------------------------------------------------------------

def _build_links_tab() -> None:
    state: dict = {"todos": [], "invoices": []}
    container = ui.column().classes("w-full gap-4")

    async def _reload():
        state["todos"] = await run.io_bound(get_todos)
        state["invoices"] = await run.io_bound(get_invoices)
        _redraw()

    def _redraw():
        container.clear()
        todos = state["todos"]
        invoices = state["invoices"]

        with container:
            # Link dialog button
            with ui.row().classes("items-center justify-between w-full"):
                ui.label("Dokument-Todo-Rechnungs-Verknüpfungen").style(
                    "font-size:0.95rem;font-weight:600;color:#00d4ff"
                )
                ui.button(
                    "Verknüpfen", icon="link",
                    on_click=lambda: _open_link_dialog(todos, invoices),
                ).props("flat dense no-caps").style(_BTN_CYAN)

            ui.separator().style("border-color:rgba(0,212,255,0.1);margin:4px 0")

            with ui.row().classes("w-full gap-4 items-start"):
                # Left: Todos with linked docs
                with ui.column().classes("flex-1 gap-3"):
                    section_title("Todos & verknüpfte Dokumente", "task_alt")
                    if not todos:
                        empty_state("task_alt", "Keine Todos", "Noch keine Todos vorhanden.")
                    else:
                        for todo in todos:
                            _render_todo_links_card(todo, _reload)

                # Right: Invoices with linked todos
                with ui.column().classes("flex-1 gap-3"):
                    section_title("Rechnungen & verknüpfte Todos", "receipt_long")
                    if not invoices:
                        empty_state("receipt_long", "Keine Rechnungen", "Noch keine Rechnungen vorhanden.")
                    else:
                        for inv in invoices:
                            _render_invoice_links_card(inv, _reload)

    def _open_link_dialog(todos: list, invoices: list):
        if not todos or not invoices:
            ui.notify("Bitte zuerst Aufgaben und Rechnungen anlegen, um sie zu verknüpfen.", color="orange", timeout=3000)
            return

        todo_options = {t["id"]: t.get("text", t["id"])[:60] for t in todos}
        inv_options = {inv["id"]: f"{inv.get('vendor', '?')} — {_fmt_amount(inv.get('amount', 0))}" for inv in invoices}

        sel: dict = {"todo_id": None, "invoice_id": None}

        with ui.dialog() as dlg, ui.card().style(
            "background:#0a1628;border:1px solid rgba(0,212,255,0.3);"
            "border-radius:14px;padding:24px;min-width:400px"
        ):
            ui.label("Todo ↔ Rechnung verknüpfen").style(
                "font-size:1.1rem;font-weight:700;color:#00d4ff;margin-bottom:8px"
            )

            todo_sel = ui.select(
                {v: v for v in todo_options.values()},
                label="Todo auswählen"
            ).props("dense dark outlined").classes("w-full")

            inv_sel = ui.select(
                {v: v for v in inv_options.values()},
                label="Rechnung auswählen"
            ).props("dense dark outlined").classes("w-full")

            # Build reverse maps
            todo_label_to_id = {v: k for k, v in todo_options.items()}
            inv_label_to_id = {v: k for k, v in inv_options.items()}

            async def _save():
                todo_label = todo_sel.value
                inv_label = inv_sel.value
                if not todo_label or not inv_label:
                    ui.notify("Bitte Todo und Rechnung auswählen", color="red", timeout=2500)
                    return
                t_id = todo_label_to_id.get(todo_label)
                i_id = inv_label_to_id.get(inv_label)
                if t_id and i_id:
                    await run.io_bound(link_invoice_todo, i_id, t_id, todo_label)
                    dlg.close()
                    await _reload()
                    ui.notify("Verknüpfung erstellt", color="green", timeout=2500)

            with ui.row().classes("gap-2 justify-end w-full mt-4"):
                ui.button("Abbrechen", on_click=dlg.close).props("flat dense no-caps").style("color:#94a3b8")
                ui.button("Verknüpfen", on_click=_save).props("unelevated dense no-caps").style(
                    "background:rgba(0,212,255,0.15);color:#00d4ff;"
                    "border:1px solid rgba(0,212,255,0.4);border-radius:8px;padding:4px 18px"
                )

        dlg.open()

    async def _init():
        await _reload()

    ui.timer(0.05, _init, once=True)


def _render_todo_links_card(todo: dict, reload_fn) -> None:
    linked_docs = todo.get("linked_docs", [])
    with ui.card().style(_CARD).classes("w-full"):
        with ui.row().classes("items-start gap-2 w-full"):
            ui.icon("check_circle_outline" if todo.get("done") else "radio_button_unchecked").style(
                f"color:{'#00e87d' if todo.get('done') else '#94a3b8'};font-size:1rem;margin-top:2px"
            )
            with ui.column().classes("gap-1 flex-1"):
                ui.label(todo.get("text", "—")).style(
                    "font-size:0.88rem;font-weight:600;color:var(--ds-text,#e2e8f0)"
                )
                if linked_docs:
                    for doc in linked_docs:
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("insert_drive_file").style("color:#a78bfa;font-size:0.85rem")
                            ui.label(doc.get("label", doc.get("path", "?"))).style(
                                "font-size:0.75rem;color:#a78bfa"
                            ).tooltip(doc.get("path", ""))

                            async def _unlink_doc(tid=todo["id"], dpath=doc["path"]):
                                await run.io_bound(unlink_todo_doc, tid, dpath)
                                await reload_fn()
                                ui.notify("Verknüpfung aufgehoben", color="orange", timeout=2000)

                            ui.button(icon="link_off", on_click=_unlink_doc).props(
                                "flat round dense"
                            ).style("color:#ff3366;font-size:0.7rem;opacity:0.7").tooltip("Verknüpfung aufheben")
                else:
                    ui.label("Keine Dokumente verknüpft").style(
                        "font-size:0.75rem;color:var(--ds-text-3,#475569);font-style:italic"
                    )


def _render_invoice_links_card(inv: dict, reload_fn) -> None:
    linked_todos = inv.get("linked_todos", [])
    with ui.card().style(_CARD).classes("w-full"):
        with ui.column().classes("gap-1 w-full"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("receipt").style("color:#00d4ff;font-size:1rem")
                ui.label(inv.get("vendor", "—")).style(
                    "font-size:0.88rem;font-weight:600;color:var(--ds-text,#e2e8f0)"
                )
                ui.label(_fmt_amount(inv.get("amount", 0))).style(
                    "font-size:0.88rem;font-weight:700;color:#00d4ff"
                )

            if linked_todos:
                for lt in linked_todos:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("task_alt").style("color:#00e87d;font-size:0.85rem")
                        ui.label(lt.get("label", lt.get("id", "?"))).style(
                            "font-size:0.75rem;color:#00e87d"
                        )

                        async def _unlink_todo(iid=inv["id"], tid=lt["id"]):
                            await run.io_bound(unlink_invoice_todo, iid, tid)
                            await reload_fn()
                            ui.notify("Verknüpfung aufgehoben", color="orange", timeout=2000)

                        ui.button(icon="link_off", on_click=_unlink_todo).props(
                            "flat round dense"
                        ).style("color:#ff3366;font-size:0.7rem;opacity:0.7").tooltip("Verknüpfung aufheben")
            else:
                ui.label("Keine Todos verknüpft").style(
                    "font-size:0.75rem;color:var(--ds-text-3,#475569);font-style:italic"
                )


# ---------------------------------------------------------------------------
# Main build function
# ---------------------------------------------------------------------------

def build() -> None:
    """Finanzen-Dashboard aufbauen."""

    page_header("Finanzen", "Ausgaben, Abonnements und Rechnungen auf einen Blick")

    ui.separator().style("border-color:rgba(0,212,255,0.1);margin:4px 0 16px 0")

    with ui.tabs().props("dense align=left").style(
        "color:#00d4ff;border-bottom:1px solid rgba(0,212,255,0.15)"
    ) as tabs:
        tab_invoices = ui.tab("Rechnungen", icon="receipt_long")
        tab_monthly = ui.tab("Monatsübersicht", icon="bar_chart")
        tab_links = ui.tab("Verbindungen", icon="account_tree")

    with ui.tab_panels(tabs, value=tab_invoices).classes("w-full").style(
        "background:transparent;padding-top:16px"
    ):
        with ui.tab_panel(tab_invoices):
            _build_invoices_tab()

        with ui.tab_panel(tab_monthly):
            _build_monthly_tab()

        with ui.tab_panel(tab_links):
            _build_links_tab()
