"""Schlagwörter & Erkennung — Unified keyword management hub.

Alle Schlüsselbegriffe an einem Ort:
  1. Überall aktiv         → Globale Schlagwörter (user_profile)
  2. Was ist das Dokument? → Dokumentenarten + Keywords (config)
  3. Von wem?              → Kunden & Aliase (config)
  4. Woher?                → Länder & Keywords (config)
"""
from __future__ import annotations

from typing import Any

from nicegui import ui

from ...config import load_config_raw, save_config
from ...user_profile import (
    add_global_keywords,
    get_global_keywords,
    remove_global_keyword,
)
from ..theme import callout, page_header


# ── colour palette ────────────────────────────────────────────────────────────
_C_DE  = ("bg-blue-100 dark:bg-blue-900",   "text-blue-700 dark:text-blue-300")
_C_EN  = ("bg-green-100 dark:bg-green-900",  "text-green-700 dark:text-green-300")
_C_SQ  = ("bg-amber-100 dark:bg-amber-900",  "text-amber-700 dark:text-amber-300")
_C_KW  = ("bg-purple-100 dark:bg-purple-900","text-purple-700 dark:text-purple-300")
_C_HOT = ("bg-red-100 dark:bg-red-900",      "text-red-600 dark:text-red-300")


def _chip(label: str, color: tuple[str, str], on_remove: Any | None = None) -> None:
    """Render a single chip with optional ✕ button."""
    bg, fg = color
    with ui.element("div").classes(
        f"inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium {bg} {fg}"
    ):
        ui.label(label)
        if on_remove:
            ui.icon("close").classes(
                f"text-xs cursor-pointer opacity-60 hover:opacity-100 {fg}"
            ).on("click", on_remove)


def _section_header(title: str, subtitle: str, icon: str) -> None:
    with ui.row().classes("items-start gap-3 mb-3"):
        ui.icon(icon).classes("text-2xl text-blue-500 mt-0.5 flex-shrink-0")
        with ui.column().classes("gap-0"):
            ui.label(title).classes("text-base font-bold")
            ui.label(subtitle).classes("text-xs text-gray-500 dark:text-gray-400 leading-relaxed")


def _lang_badge(lang: str) -> None:
    labels = {"keywords_de": "DE 🇩🇪", "keywords_en": "EN 🇬🇧", "keywords_sq": "SQ 🇦🇱"}
    colors = {"keywords_de": _C_DE, "keywords_en": _C_EN, "keywords_sq": _C_SQ}
    bg, fg = colors.get(lang, _C_KW)
    ui.label(labels.get(lang, lang)).classes(
        f"text-xs font-bold px-1.5 py-0.5 rounded {bg} {fg} flex-shrink-0 self-start mt-0.5"
    )


# ---------------------------------------------------------------------------
# Section 1 — Globale Schlagwörter
# ---------------------------------------------------------------------------

def _build_global(cfg: dict) -> None:
    _section_header(
        "Überall aktiv",
        "Diese Begriffe erkennt Doc-Sorter in Dokumenten und E-Mails. "
        "Sie helfen dem Assistenten wichtige Inhalte zu priorisieren und schneller zu lernen.",
        "bolt",
    )

    @ui.refreshable
    def render_global() -> None:
        raw_kws = get_global_keywords()  # list of original-spelling strings

        # Load hit counts from profile
        try:
            from ...user_profile import _load as _prof_load
            _hits = {
                v.get("original", k).lower(): v.get("hits", 0)
                for k, v in _prof_load().get("global_keywords", {}).items()
            }
        except Exception:
            _hits = {}

        if not raw_kws:
            with ui.element("div").classes(
                "border-2 border-dashed border-gray-300 dark:border-gray-600 "
                "rounded-xl px-4 py-6 text-center text-gray-400 text-sm mb-3"
            ):
                ui.label("Noch keine globalen Schlagwörter — füge deinen ersten Begriff unten hinzu.")
        else:
            with ui.element("div").classes("flex flex-wrap gap-2 mb-3"):
                for kw in raw_kws:
                    hits = _hits.get(kw.lower(), 0)
                    color = _C_HOT if hits >= 10 else _C_KW

                    def _make_remove(k: str):
                        def _do():
                            remove_global_keyword(k)
                            # also sync to config list
                            gl: list = cfg.setdefault("global_keywords", [])
                            if k in gl:
                                gl.remove(k)
                            save_config(cfg)
                            render_global.refresh()
                        return _do

                    with ui.element("div").classes(
                        f"inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold "
                        f"{color[0]} {color[1]} border border-current border-opacity-30"
                    ):
                        ui.label(kw)
                        if hits > 0:
                            ui.label(f"· {hits}×").classes("opacity-60 text-xs font-normal")
                        ui.icon("close").classes(
                            "text-xs cursor-pointer opacity-50 hover:opacity-100"
                        ).on("click", _make_remove(kw))

            ui.label("🔴 = oft erkannt (≥10×)  ·  Zahl = Treffer in deinen Dokumenten & E-Mails").classes(
                "text-xs text-gray-400 mb-3"
            )

        # Add input
        with ui.row().classes("items-center gap-2 w-full"):
            inp = ui.input(
                placeholder="Begriff eingeben … mehrere mit Komma trennen",
            ).classes("flex-1 ds-input")

            def _add() -> None:
                raw = inp.value.strip()
                if not raw:
                    return
                parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
                add_global_keywords(parts)
                # sync to config list too
                gl: list = cfg.setdefault("global_keywords", [])
                for p in parts:
                    if p not in gl:
                        gl.append(p)
                save_config(cfg)
                inp.value = ""
                render_global.refresh()
                ui.notify(f"{len(parts)} Schlagwort/e hinzugefügt", type="positive", position="top")

            inp.on("keydown.enter", _add)
            ui.button("Hinzufügen", on_click=_add, icon="add").classes("ds-btn-primary")

    render_global()


# ---------------------------------------------------------------------------
# Section 2 — Dokumentenarten
# ---------------------------------------------------------------------------

def _build_doctypes(cfg: dict) -> None:
    doc_types: dict[str, Any] = cfg.setdefault("document_types", {})

    _section_header(
        "Was ist das Dokument?",
        "Dokumentenarten und ihre Erkennungswörter in Deutsch, Englisch und Albanisch. "
        "Doc-Sorter liest diese Begriffe im Dokument und ordnet es der richtigen Kategorie zu.",
        "description",
    )

    lang_cfg = [
        ("keywords_de", _C_DE,  "DE 🇩🇪"),
        ("keywords_en", _C_EN,  "EN 🇬🇧"),
        ("keywords_sq", _C_SQ,  "SQ 🇦🇱"),
    ]

    @ui.refreshable
    def render_doctypes() -> None:
        def _remove_doctype(name: str) -> None:
            doc_types.pop(name, None)
            save_config(cfg)
            render_doctypes.refresh()

        if not doc_types:
            with ui.element("div").classes(
                "border-2 border-dashed border-gray-300 dark:border-gray-600 "
                "rounded-xl px-4 py-6 text-center text-gray-400 text-sm mb-3"
            ):
                ui.label("Noch keine Dokumentenarten — füge die erste unten hinzu.")
        else:
            with ui.column().classes("w-full gap-2 mb-3"):
                for dtype, lang_kw in list(doc_types.items()):
                    with ui.card().classes("ds-card-flat w-full"):
                        with ui.row().classes("items-center gap-2 mb-2"):
                            ui.icon("description").classes("text-blue-500 flex-shrink-0")
                            ui.label(dtype.title()).classes("font-semibold text-sm flex-1")
                            ui.button(
                                icon="delete",
                                on_click=lambda d=dtype: _remove_doctype(d),
                            ).classes("ds-btn-danger").props("round size=sm flat")

                        # Keywords per language — compact rows
                        for lang_key, color, badge_label in lang_cfg:
                            kws = lang_kw.get(lang_key, [])
                            if not kws:
                                continue
                            with ui.row().classes("items-start gap-1.5 flex-wrap"):
                                bg, fg = color
                                ui.label(badge_label).classes(
                                    f"text-xs font-bold px-1.5 py-0.5 rounded {bg} {fg} flex-shrink-0 self-start"
                                )
                                for kw in kws:
                                    def _make_del(d=dtype, lk=lang_key, k=kw):
                                        def _do():
                                            doc_types[d][lk] = [x for x in doc_types[d][lk] if x != k]
                                            save_config(cfg)
                                            render_doctypes.refresh()
                                        return _do
                                    _chip(kw, color, on_remove=_make_del())

                        # Inline add per language
                        with ui.expansion("Schlüsselwörter bearbeiten", icon="edit").classes("w-full mt-1"):
                            for lang_key, color, badge_label in lang_cfg:
                                with ui.row().classes("items-center gap-2 mt-1"):
                                    bg, fg = color
                                    ui.label(badge_label).classes(
                                        f"text-xs font-bold px-1.5 py-0.5 rounded {bg} {fg} w-16 flex-shrink-0"
                                    )
                                    add_inp = ui.input(
                                        placeholder="Begriff, kommagetrennt …"
                                    ).classes("flex-1 ds-input")

                                    def _make_add(d=dtype, lk=lang_key, inp_ref=add_inp):
                                        def _do():
                                            raw = inp_ref.value.strip()
                                            parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
                                            existing = doc_types[d].setdefault(lk, [])
                                            for p in parts:
                                                if p not in existing:
                                                    existing.append(p)
                                            save_config(cfg)
                                            inp_ref.value = ""
                                            render_doctypes.refresh()
                                        return _do

                                    add_inp.on("keydown.enter", _make_add())
                                    ui.button(icon="add", on_click=_make_add()).props("round size=sm flat").classes("text-blue-500")

        # Add new doc type
        ui.separator().classes("my-2")
        with ui.row().classes("items-center gap-2 w-full"):
            from .config_editor import _lookup_keywords
            new_dt = ui.input(
                placeholder="Neue Dokumentenart … z.B. rechnung, vertrag",
                autocomplete=list(doc_types.keys()),
            ).classes("flex-1 ds-input")

            async def _add_dt() -> None:
                n = new_dt.value.strip().lower()
                if not n:
                    return
                if n in doc_types:
                    ui.notify(f'"{n}" existiert bereits', type="warning")
                    return
                found = _lookup_keywords(n)
                if found:
                    doc_types[n] = found
                else:
                    doc_types[n] = {"keywords_de": [n], "keywords_en": [], "keywords_sq": []}
                save_config(cfg)
                new_dt.value = ""
                render_doctypes.refresh()
                if found:
                    ui.notify(f'"{n}" mit Vorschlägen angelegt', type="positive", position="top")
                else:
                    ui.notify(f'"{n}" angelegt — bitte Schlüsselwörter ergänzen', type="info", position="top")

            new_dt.on("keydown.enter", _add_dt)
            ui.button("Hinzufügen", on_click=_add_dt, icon="add").classes("ds-btn-primary")

    render_doctypes()


# ---------------------------------------------------------------------------
# Section 3 — Kunden
# ---------------------------------------------------------------------------

def _build_customers(cfg: dict) -> None:
    customers: list[dict] = cfg.setdefault("known_customers", [])

    _section_header(
        "Von wem?",
        "Kunden und Vertragspartner mit ihren Alias-Namen. "
        "Doc-Sorter erkennt einen Kunden sobald einer dieser Begriffe im Dokument auftaucht.",
        "people",
    )

    @ui.refreshable
    def render_customers() -> None:
        def _cust_remove(idx: int) -> None:
            if 0 <= idx < len(customers):
                customers.pop(idx)
                save_config(cfg)
                render_customers.refresh()

        if not customers:
            with ui.element("div").classes(
                "border-2 border-dashed border-gray-300 dark:border-gray-600 "
                "rounded-xl px-4 py-6 text-center text-gray-400 text-sm mb-3"
            ):
                ui.label("Noch keine Kunden — füge deinen ersten Kontakt unten hinzu.")
        else:
            with ui.column().classes("w-full gap-2 mb-3"):
                for i, cust in enumerate(customers):
                    name = cust.get("name", "") or f"Kunde {i+1}"
                    aliases = cust.get("aliases", [])
                    with ui.card().classes("ds-card-flat w-full"):
                        with ui.row().classes("items-center gap-2 mb-2"):
                            ui.icon("person").classes("text-purple-500 flex-shrink-0")
                            name_inp = ui.input(value=name, placeholder="Name …").classes("flex-1 ds-input text-sm font-semibold")
                            name_inp.on("blur", lambda e, c=cust: c.update({"name": e.sender.value}) or save_config(cfg))
                            ui.button(
                                icon="delete",
                                on_click=lambda idx=i: (_cust_remove(idx)),
                            ).classes("ds-btn-danger").props("round size=sm flat")

                        with ui.row().classes("items-center gap-1.5 flex-wrap"):
                            ui.label("Aliase:").classes("text-xs text-gray-400 flex-shrink-0")
                            for alias in aliases:
                                def _make_alias_del(c=cust, a=alias):
                                    def _do():
                                        c["aliases"] = [x for x in c.get("aliases", []) if x != a]
                                        save_config(cfg)
                                        render_customers.refresh()
                                    return _do
                                _chip(alias, _C_KW, on_remove=_make_alias_del())

                            alias_inp = ui.input(placeholder="+ Alias …").classes("ds-input text-xs w-32")

                            def _make_alias_add(c=cust, inp_ref=alias_inp):
                                def _do():
                                    raw = inp_ref.value.strip()
                                    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
                                    existing = c.setdefault("aliases", [])
                                    for p in parts:
                                        if p not in existing:
                                            existing.append(p)
                                    save_config(cfg)
                                    inp_ref.value = ""
                                    render_customers.refresh()
                                return _do

                            alias_inp.on("keydown.enter", _make_alias_add())
                            ui.button(icon="add", on_click=_make_alias_add()).props("round size=sm flat").classes("text-purple-500")

        ui.separator().classes("my-2")
        with ui.row().classes("items-center gap-2"):
            def _add_cust() -> None:
                customers.append({"name": "", "aliases": []})
                save_config(cfg)
                render_customers.refresh()
            ui.button("Kunde hinzufügen", on_click=_add_cust, icon="person_add").classes("ds-btn-secondary")

    render_customers()


# ---------------------------------------------------------------------------
# Section 4 — Länder
# ---------------------------------------------------------------------------

def _build_countries(cfg: dict) -> None:
    countries: dict[str, Any] = cfg.setdefault("countries", {})

    _section_header(
        "Woher?",
        "Länder und ihre Erkennungswörter — Städtenamen, Landesbezeichnungen und typische Begriffe. "
        "Doc-Sorter ordnet damit das Herkunftsland eines Dokuments zu.",
        "public",
    )

    @ui.refreshable
    def render_countries() -> None:
        def _country_remove(name: str) -> None:
            countries.pop(name, None)
            save_config(cfg)
            render_countries.refresh()

        if not countries:
            with ui.element("div").classes(
                "border-2 border-dashed border-gray-300 dark:border-gray-600 "
                "rounded-xl px-4 py-6 text-center text-gray-400 text-sm mb-3"
            ):
                ui.label("Noch keine Länder — füge dein erstes Land unten hinzu.")
        else:
            with ui.column().classes("w-full gap-2 mb-3"):
                for country, data in list(countries.items()):
                    kws = data.get("keywords", [])
                    with ui.card().classes("ds-card-flat w-full"):
                        with ui.row().classes("items-center gap-2 mb-2"):
                            ui.icon("flag").classes("text-blue-500 flex-shrink-0")
                            ui.label(country.title()).classes("font-semibold text-sm flex-1")
                            ui.button(
                                icon="delete",
                                on_click=lambda c=country: (_country_remove(c)),
                            ).classes("ds-btn-danger").props("round size=sm flat")

                        with ui.row().classes("items-center gap-1.5 flex-wrap"):
                            for kw in kws:
                                def _make_kw_del(c=country, k=kw):
                                    def _do():
                                        countries[c]["keywords"] = [x for x in countries[c]["keywords"] if x != k]
                                        save_config(cfg)
                                        render_countries.refresh()
                                    return _do
                                _chip(kw, _C_EN, on_remove=_make_kw_del())

                            kw_inp = ui.input(placeholder="+ Begriff …").classes("ds-input text-xs w-32")

                            def _make_kw_add(c=country, inp_ref=kw_inp):
                                def _do():
                                    raw = inp_ref.value.strip()
                                    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
                                    existing = countries[c].setdefault("keywords", [])
                                    for p in parts:
                                        if p not in existing:
                                            existing.append(p)
                                    save_config(cfg)
                                    inp_ref.value = ""
                                    render_countries.refresh()
                                return _do

                            kw_inp.on("keydown.enter", _make_kw_add())
                            ui.button(icon="add", on_click=_make_kw_add()).props("round size=sm flat").classes("text-blue-500")

        ui.separator().classes("my-2")
        with ui.row().classes("items-center gap-2"):
            new_c = ui.input(
                placeholder="Neues Land … z.B. deutschland, schweiz",
                autocomplete=list(countries.keys()),
            ).classes("flex-1 ds-input")

            def _add_country() -> None:
                n = new_c.value.strip().lower()
                if not n:
                    return
                if n in countries:
                    ui.notify(f'"{n}" existiert bereits', type="warning")
                    return
                countries[n] = {"keywords": [n]}
                save_config(cfg)
                new_c.value = ""
                render_countries.refresh()

            new_c.on("keydown.enter", _add_country)
            ui.button("Hinzufügen", on_click=_add_country, icon="add").classes("ds-btn-primary")

    render_countries()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build() -> None:
    cfg = load_config_raw()

    page_header("Schlagwörter & Erkennung", "label")

    callout(
        "Hier verwaltest du alle Begriffe die Doc-Sorter kennen soll — an einem Ort. "
        "Änderungen werden sofort gespeichert.",
        "info", "lightbulb",
    )

    # Stats bar
    n_global = len(get_global_keywords())
    n_types  = len(cfg.get("document_types", {}))
    n_cust   = len(cfg.get("known_customers", []))
    n_land   = len(cfg.get("countries", {}))

    with ui.row().classes("gap-3 mb-6 flex-wrap"):
        for label, val, icon, col in [
            ("Globale Begriffe", n_global, "bolt",        "text-purple-500"),
            ("Dokumentenarten", n_types,  "description",  "text-blue-500"),
            ("Kunden",          n_cust,   "people",        "text-green-500"),
            ("Länder",          n_land,   "public",        "text-amber-500"),
        ]:
            with ui.card().classes("ds-card-flat flex-1 min-w-24"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon(icon).classes(f"{col} text-xl")
                    with ui.column().classes("gap-0"):
                        ui.label(str(val)).classes(f"text-2xl font-bold {col}")
                        ui.label(label).classes("text-xs text-gray-400")

    # ── Section 1 ─────────────────────────────────────────────────────────────
    with ui.card().classes("ds-card w-full mb-4"):
        _build_global(cfg)

    # ── Section 2 ─────────────────────────────────────────────────────────────
    with ui.card().classes("ds-card w-full mb-4"):
        _build_doctypes(cfg)

    # ── Section 3 ─────────────────────────────────────────────────────────────
    with ui.card().classes("ds-card w-full mb-4"):
        _build_customers(cfg)

    # ── Section 4 ─────────────────────────────────────────────────────────────
    with ui.card().classes("ds-card w-full mb-4"):
        _build_countries(cfg)
