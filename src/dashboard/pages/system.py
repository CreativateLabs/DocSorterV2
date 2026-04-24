"""System-Status: Voraussetzungen, Versionen und Pfade pruefen.

UI Design Overhaul: Crisp Status-Cards, bessere Darstellung.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Any

from nicegui import ui

from ...config import load_config, load_config_raw, save_config, get_ocr_languages
from ...prerequisites import run_all_checks
from ...learning_engine import get_status as le_get_status, train as le_train, set_enabled as le_set_enabled
from ...llm_classifier import is_ollama_running, get_ollama_models
from ..theme import callout, page_header, section_title, status_badge
from .install_helper import build_dependency_card


def _build_learning_engine_section() -> None:
    """Lern-Engine — benutzerfreundliches Onboarding mit 3 klaren Zuständen."""

    @ui.refreshable
    def _le_card() -> None:

        def _le_toggle_row(le: dict) -> None:
            """An/Aus-Toggle — oben in Zustand 2 und 3 sichtbar."""
            enabled = le.get("enabled", True)

            with ui.row().classes(
                "items-center justify-between w-full mb-4 pb-3 "
                "border-b border-gray-200 dark:border-gray-700"
            ):
                with ui.column().classes("gap-0"):
                    ui.label("Lern-Engine").classes("font-bold text-base")
                    ui.label(
                        "Aktiv — lernt aus deinen Dokumenten" if enabled
                        else "Pausiert — Daten & Modell bleiben erhalten"
                    ).classes(
                        f"text-xs {'text-green-500' if enabled else 'text-gray-400'}"
                    )

                def _toggle(v: bool) -> None:
                    le_set_enabled(v)
                    ui.notify(
                        "Lern-Engine aktiviert ✓" if v
                        else "Lern-Engine pausiert — alle Daten bleiben erhalten.",
                        type="positive" if v else "info",
                        position="top",
                    )
                    _le_card.refresh()

                ui.switch(
                    value=enabled,
                    on_change=lambda e: _toggle(e.value),
                ).props("color=blue").tooltip("Lern-Engine pausieren / wieder aktivieren")
        le = le_get_status()
        not_installed = not le["embed_installed"] or not le["sklearn_installed"]

        with ui.card().classes("ds-card w-full"):

            # ── ZUSTAND 1: Noch nicht installiert ──────────────────────────────
            if not_installed:
                # Hero-Bereich
                with ui.element("div").classes(
                    "flex flex-col items-center text-center gap-4 py-6 px-4"
                ):
                    with ui.element("div").classes(
                        "w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900 "
                        "flex items-center justify-center"
                    ):
                        ui.icon("psychology").classes("text-3xl text-blue-500")

                    ui.label("Lern-Engine aktivieren").classes(
                        "text-xl font-bold"
                    )
                    ui.label(
                        "Doc-Sorter lernt aus deinen Dokumenten und wird mit der Zeit immer genauer — "
                        "ganz ohne Cloud oder fremde Server. "
                        "Alles läuft lokal auf deinem Gerät."
                    ).classes("text-sm text-gray-500 dark:text-gray-400 max-w-lg leading-relaxed")

                    # 3 Feature-Punkte
                    with ui.element("div").classes(
                        "flex flex-col sm:flex-row gap-4 mt-2 text-left w-full max-w-lg"
                    ):
                        for icon, title, desc in [
                            ("school",        "Lernt von dir",       "Jede Bestätigung wird zum Trainingsbeispiel"),
                            ("offline_bolt",  "100 % offline",       "Kein Internet nötig nach der Einrichtung"),
                            ("trending_up",   "Immer besser",        "Nach ~20 Beispielen klassifiziert sie selbst"),
                        ]:
                            with ui.element("div").classes(
                                "flex items-start gap-3 bg-gray-50 dark:bg-gray-800 "
                                "rounded-xl p-3 flex-1"
                            ):
                                ui.icon(icon).classes("text-blue-500 flex-shrink-0 mt-0.5")
                                with ui.column().classes("gap-0"):
                                    ui.label(title).classes("text-xs font-bold")
                                    ui.label(desc).classes("text-xs text-gray-400 leading-snug")

                    # Einmaliger Download-Hinweis
                    ui.label(
                        "Einmalig ~300 MB herunterladen (Sprachmodell für Deutsch, Englisch & Albanisch)"
                    ).classes("text-xs text-gray-400 mt-1")

                    # Install-Button
                    installing_state = {"running": False}
                    log_output = ui.label("").classes("text-xs font-mono text-gray-400 hidden")

                    async def _install() -> None:
                        if installing_state["running"]:
                            return
                        installing_state["running"] = True
                        btn.props("loading disable")
                        btn.text = "Wird installiert …"
                        log_output.classes(remove="hidden")
                        log_output.text = "Installation läuft — das kann 1–3 Minuten dauern …"

                        import asyncio, subprocess as _sp
                        try:
                            proc = await asyncio.create_subprocess_exec(
                                sys.executable, "-m", "pip", "install",
                                "sentence-transformers", "scikit-learn", "numpy",
                                "-q", "--progress-bar", "off",
                                stdout=_sp.PIPE, stderr=_sp.STDOUT,
                            )
                            stdout, _ = await proc.communicate()
                            if proc.returncode == 0:
                                log_output.text = "✓ Installation erfolgreich! Seite wird neu geladen …"
                                await asyncio.sleep(1.5)
                                _le_card.refresh()
                            else:
                                output = (stdout or b"").decode(errors="replace")[-400:]
                                log_output.text = f"Fehler bei der Installation:\n{output}"
                                ui.notify("Installation fehlgeschlagen — Details unten.", type="negative")
                                btn.props(remove="loading disable")
                                btn.text = "Erneut versuchen"
                        except Exception as exc:
                            log_output.text = f"Fehler: {exc}"
                            ui.notify(str(exc), type="negative")
                            btn.props(remove="loading disable")
                            btn.text = "Erneut versuchen"
                        finally:
                            installing_state["running"] = False

                    btn = ui.button(
                        "Lern-Engine aktivieren",
                        on_click=_install,
                        icon="rocket_launch",
                    ).classes("ds-btn-primary text-base px-8 py-3 mt-2")

                    log_output  # referenziert oben, bleibt versteckt bis Installation

            # ── ZUSTAND 2: Installiert — sammelt noch Daten ────────────────────
            elif not le["available"] or le["total_examples"] < le["retrain_threshold"]:
                _le_toggle_row(le)
                with ui.row().classes("items-center gap-3 mb-4"):
                    with ui.element("div").classes(
                        "w-10 h-10 rounded-full bg-green-100 dark:bg-green-900 "
                        "flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon("check_circle").classes("text-xl text-green-500")
                    with ui.column().classes("gap-0"):
                        ui.label("Lern-Engine ist bereit").classes("font-bold text-base")
                        ui.label(
                            "Sie sammelt jetzt Trainingsdaten. "
                            "Bestätige Dokumente im Review — nach 10 Bestätigungen trainiert sie sich automatisch."
                        ).classes("text-sm text-gray-500 dark:text-gray-400")

                # Fortschrittsbalken
                prog  = le["retrain_progress"]
                total = le["retrain_threshold"]
                pct   = int(prog / total * 100) if total else 0
                with ui.element("div").classes("w-full mb-4"):
                    with ui.row().classes("justify-between mb-1"):
                        ui.label("Trainingsfortschritt").classes("text-xs font-medium text-gray-500")
                        ui.label(f"{prog} / {total} Bestätigungen").classes("text-xs text-gray-400")
                    with ui.element("div").classes(
                        "w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3"
                    ):
                        ui.element("div").classes(
                            "bg-blue-500 h-3 rounded-full transition-all"
                        ).style(f"width:{pct}%")

                # Schritte-Anleitung
                with ui.element("div").classes(
                    "bg-blue-50 dark:bg-blue-900/30 rounded-xl p-4"
                ):
                    ui.label("So geht es weiter:").classes("text-xs font-bold text-blue-700 dark:text-blue-300 mb-2")
                    steps = [
                        ("Dokumente hochladen", "Wirf Dokumente in deine Inbox"),
                        ("Review öffnen", "Unter Einstellungen → Prüfung"),
                        ("Bestätigen oder korrigieren", "Jede Aktion = 1 Trainingsbeispiel"),
                        ("Automatisches Training", "Nach 10 Beispielen trainiert die Engine selbst"),
                    ]
                    for i, (title, desc) in enumerate(steps, 1):
                        with ui.row().classes("items-start gap-3 mb-2"):
                            ui.label(str(i)).classes(
                                "w-5 h-5 rounded-full bg-blue-500 text-white text-xs "
                                "flex items-center justify-center flex-shrink-0 font-bold mt-0.5"
                            )
                            with ui.column().classes("gap-0"):
                                ui.label(title).classes("text-xs font-semibold text-blue-800 dark:text-blue-200")
                                ui.label(desc).classes("text-xs text-blue-600 dark:text-blue-400")

                ui.button(
                    "Zur Prüfungs-Seite", icon="rate_review",
                    on_click=lambda: ui.navigate.to("/review"),
                ).classes("ds-btn-secondary mt-4")

            # ── ZUSTAND 3: Aktiv & trainiert ──────────────────────────────────
            else:
                _le_toggle_row(le)
                with ui.row().classes("items-center gap-4 mb-5"):
                    with ui.element("div").classes(
                        "w-12 h-12 rounded-full bg-green-100 dark:bg-green-900 "
                        "flex items-center justify-center flex-shrink-0"
                    ):
                        ui.icon("psychology").classes("text-2xl text-green-500")
                    with ui.column().classes("gap-0.5"):
                        ui.label("Lern-Engine aktiv").classes("font-bold text-lg")
                        ui.label(
                            "Doc-Sorter klassifiziert Dokumente eigenständig auf Basis deiner Daten."
                        ).classes("text-sm text-gray-500 dark:text-gray-400")

                # Kennzahlen — 4 Mini-Kacheln
                with ui.row().classes("gap-3 mb-5 flex-wrap"):
                    _stat_tile(str(le["trained_on"]),     "Trainings-\nbeispiele", "school",        "text-blue-500")
                    _stat_tile(str(len(le["classes"])),   "Gelernte\nDokumentenarten", "description","text-purple-500")
                    acc = le.get("cv_accuracy")
                    _stat_tile(
                        f"{acc:.0%}" if acc else "—",
                        "Genauigkeit",
                        "verified",
                        "text-green-500" if acc and acc >= 0.85 else "text-amber-500",
                    )
                    _stat_tile(le["last_trained_fmt"] or "—", "Letztes\nTraining", "update", "text-gray-400")

                # Gelernte Dokumentenarten
                if le["classes"]:
                    ui.label("Gelernte Dokumentenarten:").classes(
                        "text-xs font-medium text-gray-400 mb-2"
                    )
                    with ui.element("div").classes("flex flex-wrap gap-2 mb-5"):
                        for cls in le["classes"]:
                            cnt = le["label_counts"].get(cls, 0)
                            ui.label(f"{cls}  ·  {cnt}×").classes(
                                "text-xs px-3 py-1 rounded-full font-medium "
                                "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300"
                            )

                # Fortschrittsbalken neue Daten
                if le["new_since_train"] > 0:
                    prog  = le["retrain_progress"]
                    total = le["retrain_threshold"]
                    pct   = int(prog / total * 100) if total else 0
                    with ui.element("div").classes("w-full mb-4"):
                        with ui.row().classes("justify-between mb-1"):
                            ui.label("Neue Beispiele bis Auto-Training").classes(
                                "text-xs font-medium text-gray-500"
                            )
                            ui.label(f"{prog} / {total}").classes("text-xs text-gray-400")
                        with ui.element("div").classes(
                            "w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2"
                        ):
                            ui.element("div").classes(
                                "bg-blue-500 h-2 rounded-full transition-all"
                            ).style(f"width:{pct}%")

                # Manuelles Training
                def _do_train() -> None:
                    result = le_train(force=True)
                    if result.get("ok"):
                        ui.notify(
                            f"✓ Training abgeschlossen — {result.get('trained_on', 0)} Beispiele"
                            + (f", Genauigkeit: {result['cv_accuracy']:.0%}" if result.get('cv_accuracy') else ""),
                            type="positive", position="top",
                        )
                    else:
                        ui.notify(result.get("reason", "Fehler beim Training"), type="warning", position="top")
                    _le_card.refresh()

                ui.button(
                    "Neu trainieren", on_click=_do_train, icon="model_training"
                ).classes("ds-btn-secondary")

    _le_card()


def _build_ai_providers_section() -> None:
    """KI-Anbieter: OpenAI, Anthropic und Ollama — je eigene Kachel."""

    # ── Hilfsfunktionen ──────────────────────────────────────────────────────

    def _cfg_llm() -> dict:
        return load_config_raw().get("llm", {})

    def _save_llm(key: str, value) -> None:
        cfg = load_config_raw()
        cfg.setdefault("llm", {})[key] = value
        save_config(cfg)

    def _mask_key(key: str) -> str:
        """API-Schlüssel für Anzeige maskieren."""
        if not key or len(key) < 8:
            return "—"
        return key[:4] + "·" * 6 + key[-4:]

    def _provider_header(
        icon_name: str, title: str, subtitle: str,
        icon_bg: str, enabled: bool | None, on_toggle
    ) -> None:
        """Einheitlicher Kachel-Kopf mit optionalem Toggle."""
        with ui.row().classes(
            "items-center justify-between w-full mb-4 pb-3 "
            "border-b border-gray-200 dark:border-gray-700"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    f"w-10 h-10 rounded-xl {icon_bg} "
                    "flex items-center justify-center flex-shrink-0"
                ):
                    ui.icon(icon_name).classes("text-xl text-white")
                with ui.column().classes("gap-0"):
                    ui.label(title).classes("font-bold text-base")
                    ui.label(subtitle).classes("text-xs text-gray-400")
            if enabled is not None and on_toggle:
                ui.switch(
                    value=enabled,
                    on_change=lambda e: on_toggle(e.value),
                ).props("color=blue").tooltip("Aktivieren / Pausieren")

    # ── OpenAI ───────────────────────────────────────────────────────────────

    @ui.refreshable
    def _openai_card() -> None:
        llm = _cfg_llm()
        api_key = os.environ.get("OPENAI_API_KEY", "") or llm.get("openai_api_key", "")
        enabled  = bool(llm.get("openai_enabled", False))

        try:
            import openai as _openai  # noqa: F401
            pkg_ok = True
        except ImportError:
            pkg_ok = False

        ready = pkg_ok and bool(api_key)

        def _toggle(v: bool) -> None:
            _save_llm("openai_enabled", v)
            ui.notify("OpenAI aktiviert ✓" if v else "OpenAI pausiert.", type="positive" if v else "info", position="top")
            _openai_card.refresh()

        with ui.card().classes("ds-card w-full"):
            _provider_header(
                "smart_toy", "OpenAI GPT",
                "Cloud-KI · GPT-4o-mini · API-Schlüssel nötig",
                "bg-emerald-500",
                enabled if ready else None,
                _toggle,
            )

            # ZUSTAND 1: Paket nicht installiert
            if not pkg_ok:
                with ui.element("div").classes("flex flex-col items-center text-center gap-4 py-4"):
                    ui.label("OpenAI-Paket installieren").classes("font-semibold")
                    ui.label(
                        "Einmalige Installation — danach gibst du deinen API-Schlüssel ein."
                    ).classes("text-sm text-gray-400 max-w-xs")

                    installing = {"running": False}
                    log = ui.label("").classes("text-xs font-mono text-gray-400 hidden")

                    async def _install_openai() -> None:
                        if installing["running"]:
                            return
                        installing["running"] = True
                        btn_oa.props("loading disable")
                        log.classes(remove="hidden")
                        log.text = "Wird installiert …"
                        import asyncio, subprocess as _sp
                        try:
                            proc = await asyncio.create_subprocess_exec(
                                sys.executable, "-m", "pip", "install", "openai", "-q",
                                stdout=_sp.PIPE, stderr=_sp.STDOUT,
                            )
                            out, _ = await proc.communicate()
                            if proc.returncode == 0:
                                log.text = "✓ Installiert!"
                                await asyncio.sleep(1)
                                _openai_card.refresh()
                            else:
                                log.text = (out or b"").decode(errors="replace")[-300:]
                                ui.notify("Installation fehlgeschlagen.", type="negative")
                                btn_oa.props(remove="loading disable")
                        finally:
                            installing["running"] = False

                    btn_oa = ui.button("openai installieren", on_click=_install_openai, icon="download").classes("ds-btn-primary")
                    log

            # ZUSTAND 2: Installiert, aber kein API-Schlüssel
            elif not api_key:
                ui.label("API-Schlüssel eingeben").classes("font-semibold mb-1")
                ui.label(
                    "Deinen Schlüssel findest du unter platform.openai.com → API Keys."
                ).classes("text-xs text-gray-400 mb-3")

                key_inp = ui.input(
                    placeholder="sk-...",
                    password=True, password_toggle_button=True,
                ).classes("w-full ds-input mb-3")

                def _save_openai_key() -> None:
                    k = key_inp.value.strip()
                    if not k:
                        ui.notify("Bitte Schlüssel eingeben.", type="warning")
                        return
                    _save_llm("openai_api_key", k)
                    _save_llm("openai_enabled", True)
                    os.environ["OPENAI_API_KEY"] = k
                    ui.notify("✓ OpenAI verbunden!", type="positive", position="top")
                    _openai_card.refresh()

                with ui.row().classes("gap-2 items-center"):
                    ui.button("Verbinden", on_click=_save_openai_key, icon="link").classes("ds-btn-primary")
                    ui.link("API-Schlüssel erstellen ↗", "https://platform.openai.com/api-keys", new_tab=True).classes(
                        "text-xs text-blue-500 hover:underline"
                    )

            # ZUSTAND 3: Verbunden & bereit
            else:
                model = llm.get("openai_model", "gpt-4o-mini")
                with ui.row().classes("items-center gap-3 mb-4"):
                    ui.icon("check_circle").classes("text-green-500 text-xl flex-shrink-0")
                    with ui.column().classes("gap-0"):
                        ui.label("Verbunden und bereit").classes("font-semibold text-sm")
                        ui.label(f"Modell: {model}  ·  Schlüssel: {_mask_key(api_key)}").classes(
                            "text-xs text-gray-400"
                        )

                if not enabled:
                    callout("OpenAI ist pausiert — aktiviere den Schalter oben um ihn zu nutzen.", "info")

                # Modell wechseln
                with ui.expansion("Einstellungen", icon="tune").classes("w-full"):
                    with ui.column().classes("gap-3 p-2"):
                        model_sel = ui.select(
                            label="Modell",
                            options=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                            value=model,
                        ).classes("w-full ds-input")

                        def _save_openai_model() -> None:
                            _save_llm("openai_model", model_sel.value)
                            ui.notify(f"Modell gespeichert: {model_sel.value}", type="positive")
                            _openai_card.refresh()

                        ui.button("Speichern", on_click=_save_openai_model, icon="save").classes("ds-btn-secondary")

                        ui.separator()
                        ui.label("API-Schlüssel ersetzen").classes("text-xs text-gray-400")
                        new_key = ui.input(placeholder="Neuer Schlüssel …", password=True, password_toggle_button=True).classes("w-full ds-input")

                        def _replace_key() -> None:
                            k = new_key.value.strip()
                            if not k:
                                return
                            _save_llm("openai_api_key", k)
                            os.environ["OPENAI_API_KEY"] = k
                            ui.notify("✓ Schlüssel aktualisiert", type="positive")
                            _openai_card.refresh()

                        ui.button("Schlüssel ersetzen", on_click=_replace_key, icon="key").classes("ds-btn-ghost")

    # ── Anthropic ────────────────────────────────────────────────────────────

    @ui.refreshable
    def _anthropic_card() -> None:
        llm = _cfg_llm()
        api_key = os.environ.get("ANTHROPIC_API_KEY", "") or llm.get("anthropic_api_key", "")
        enabled  = bool(llm.get("anthropic_enabled", False))

        try:
            import anthropic as _anthropic  # noqa: F401
            pkg_ok = True
        except ImportError:
            pkg_ok = False

        ready = pkg_ok and bool(api_key)

        def _toggle(v: bool) -> None:
            _save_llm("anthropic_enabled", v)
            ui.notify("Anthropic aktiviert ✓" if v else "Anthropic pausiert.", type="positive" if v else "info", position="top")
            _anthropic_card.refresh()

        with ui.card().classes("ds-card w-full"):
            _provider_header(
                "auto_awesome", "Anthropic Claude",
                "Cloud-KI · Claude Haiku · API-Schlüssel nötig",
                "bg-orange-500",
                enabled if ready else None,
                _toggle,
            )

            # ZUSTAND 1: Paket nicht installiert
            if not pkg_ok:
                with ui.element("div").classes("flex flex-col items-center text-center gap-4 py-4"):
                    ui.label("Anthropic-Paket installieren").classes("font-semibold")
                    ui.label("Einmalige Installation — danach gibst du deinen API-Schlüssel ein.").classes(
                        "text-sm text-gray-400 max-w-xs"
                    )

                    installing = {"running": False}
                    log = ui.label("").classes("text-xs font-mono text-gray-400 hidden")

                    async def _install_anthropic() -> None:
                        if installing["running"]:
                            return
                        installing["running"] = True
                        btn_an.props("loading disable")
                        log.classes(remove="hidden")
                        log.text = "Wird installiert …"
                        import asyncio, subprocess as _sp
                        try:
                            proc = await asyncio.create_subprocess_exec(
                                sys.executable, "-m", "pip", "install", "anthropic", "-q",
                                stdout=_sp.PIPE, stderr=_sp.STDOUT,
                            )
                            out, _ = await proc.communicate()
                            if proc.returncode == 0:
                                log.text = "✓ Installiert!"
                                await asyncio.sleep(1)
                                _anthropic_card.refresh()
                            else:
                                log.text = (out or b"").decode(errors="replace")[-300:]
                                ui.notify("Installation fehlgeschlagen.", type="negative")
                                btn_an.props(remove="loading disable")
                        finally:
                            installing["running"] = False

                    btn_an = ui.button("anthropic installieren", on_click=_install_anthropic, icon="download").classes("ds-btn-primary")
                    log

            # ZUSTAND 2: Kein API-Schlüssel
            elif not api_key:
                ui.label("API-Schlüssel eingeben").classes("font-semibold mb-1")
                ui.label(
                    "Deinen Schlüssel findest du unter console.anthropic.com → API Keys."
                ).classes("text-xs text-gray-400 mb-3")

                key_inp = ui.input(
                    placeholder="sk-ant-...",
                    password=True, password_toggle_button=True,
                ).classes("w-full ds-input mb-3")

                def _save_anthropic_key() -> None:
                    k = key_inp.value.strip()
                    if not k:
                        ui.notify("Bitte Schlüssel eingeben.", type="warning")
                        return
                    _save_llm("anthropic_api_key", k)
                    _save_llm("anthropic_enabled", True)
                    os.environ["ANTHROPIC_API_KEY"] = k
                    ui.notify("✓ Anthropic verbunden!", type="positive", position="top")
                    _anthropic_card.refresh()

                with ui.row().classes("gap-2 items-center"):
                    ui.button("Verbinden", on_click=_save_anthropic_key, icon="link").classes("ds-btn-primary")
                    ui.link("API-Schlüssel erstellen ↗", "https://console.anthropic.com/settings/keys", new_tab=True).classes(
                        "text-xs text-blue-500 hover:underline"
                    )

            # ZUSTAND 3: Verbunden & bereit
            else:
                model = llm.get("anthropic_model", "claude-haiku-4-20250414")
                with ui.row().classes("items-center gap-3 mb-4"):
                    ui.icon("check_circle").classes("text-green-500 text-xl flex-shrink-0")
                    with ui.column().classes("gap-0"):
                        ui.label("Verbunden und bereit").classes("font-semibold text-sm")
                        ui.label(f"Modell: {model}  ·  Schlüssel: {_mask_key(api_key)}").classes(
                            "text-xs text-gray-400"
                        )

                if not enabled:
                    callout("Anthropic ist pausiert — aktiviere den Schalter oben um ihn zu nutzen.", "info")

                with ui.expansion("Einstellungen", icon="tune").classes("w-full"):
                    with ui.column().classes("gap-3 p-2"):
                        model_sel = ui.select(
                            label="Modell",
                            options=[
                                "claude-haiku-4-20250414",
                                "claude-sonnet-4-5",
                                "claude-opus-4-5",
                            ],
                            value=model,
                        ).classes("w-full ds-input")

                        def _save_anthropic_model() -> None:
                            _save_llm("anthropic_model", model_sel.value)
                            ui.notify(f"Modell gespeichert: {model_sel.value}", type="positive")
                            _anthropic_card.refresh()

                        ui.button("Speichern", on_click=_save_anthropic_model, icon="save").classes("ds-btn-secondary")

                        ui.separator()
                        ui.label("API-Schlüssel ersetzen").classes("text-xs text-gray-400")
                        new_key = ui.input(placeholder="Neuer Schlüssel …", password=True, password_toggle_button=True).classes("w-full ds-input")

                        def _replace_an_key() -> None:
                            k = new_key.value.strip()
                            if not k:
                                return
                            _save_llm("anthropic_api_key", k)
                            os.environ["ANTHROPIC_API_KEY"] = k
                            ui.notify("✓ Schlüssel aktualisiert", type="positive")
                            _anthropic_card.refresh()

                        ui.button("Schlüssel ersetzen", on_click=_replace_an_key, icon="key").classes("ds-btn-ghost")

    # ── Ollama ───────────────────────────────────────────────────────────────

    @ui.refreshable
    def _ollama_card() -> None:
        llm        = _cfg_llm()
        host       = llm.get("ollama_host", "http://localhost:11434")
        saved_model = llm.get("ollama_model", "llama3.2")
        enabled    = bool(llm.get("ollama_enabled", False))
        running    = is_ollama_running(host)
        models     = get_ollama_models(host) if running else []
        ready      = running and bool(models)

        def _toggle(v: bool) -> None:
            _save_llm("ollama_enabled", v)
            ui.notify("Ollama aktiviert ✓" if v else "Ollama pausiert.", type="positive" if v else "info", position="top")
            _ollama_card.refresh()

        with ui.card().classes("ds-card w-full"):
            _provider_header(
                "computer", "Ollama",
                "Lokal auf deinem Gerät · Kein API-Schlüssel · Kostenlos",
                "bg-purple-600",
                enabled if ready else None,
                _toggle,
            )

            # ZUSTAND 1: Ollama läuft nicht
            if not running:
                with ui.element("div").classes("flex flex-col items-center text-center gap-4 py-4"):
                    with ui.element("div").classes(
                        "w-14 h-14 rounded-full bg-purple-100 dark:bg-purple-900 "
                        "flex items-center justify-center"
                    ):
                        ui.icon("computer").classes("text-2xl text-purple-500")

                    ui.label("Ollama installieren & starten").classes("font-semibold")
                    ui.label(
                        "Ollama lässt KI-Modelle komplett lokal auf deinem Gerät laufen — "
                        "kein Internet, keine Kosten, keine Datenweitergabe."
                    ).classes("text-sm text-gray-400 max-w-xs leading-relaxed")

                    # OS-spezifische Anleitung
                    os_name = platform.system()
                    with ui.element("div").classes(
                        "bg-gray-50 dark:bg-gray-800 rounded-xl p-4 text-left w-full max-w-xs"
                    ):
                        ui.label("So geht's:").classes("text-xs font-bold mb-2")
                        steps = {
                            "Darwin":  ["ollama.com/download öffnen", "Mac-App herunterladen & installieren", "Ollama starten (Menüleiste)", 'Hier auf "Prüfen" klicken'],
                            "Windows": ["ollama.com/download öffnen", "Windows-Installer herunterladen", "Installieren & starten", 'Hier auf "Prüfen" klicken'],
                            "Linux":   ['Terminal: curl -fsSL https://ollama.com/install.sh | sh', "ollama serve", 'Hier auf "Prüfen" klicken'],
                        }
                        for i, step in enumerate(steps.get(os_name, steps["Linux"]), 1):
                            with ui.row().classes("items-start gap-2 mb-1"):
                                ui.label(str(i)).classes(
                                    "w-4 h-4 rounded-full bg-purple-500 text-white text-xs "
                                    "flex items-center justify-center flex-shrink-0 font-bold mt-0.5"
                                )
                                ui.label(step).classes("text-xs text-gray-500")

                    with ui.row().classes("gap-2"):
                        ui.link(
                            "ollama.com ↗", "https://ollama.com/download", new_tab=True
                        ).classes("text-xs text-purple-500 hover:underline self-center")
                        ui.button(
                            "Prüfen", on_click=_ollama_card.refresh, icon="refresh"
                        ).classes("ds-btn-secondary")

            # ZUSTAND 2: Läuft, aber kein/falsches Modell ausgewählt
            elif not models:
                with ui.element("div").classes("flex flex-col gap-3 py-2"):
                    with ui.row().classes("items-center gap-2 mb-2"):
                        ui.icon("check_circle").classes("text-green-500")
                        ui.label("Ollama läuft ✓").classes("font-semibold text-sm text-green-600")

                    ui.label("Noch kein Modell geladen").classes("font-semibold")
                    ui.label(
                        "Lade ein Modell herunter — llama3.2 ist ein guter Start (2 GB)."
                    ).classes("text-xs text-gray-400 mb-2")

                    pull_inp = ui.input(value="llama3.2", placeholder="z.B. llama3.2, mistral …").classes("w-full ds-input")
                    pulling = {"running": False}
                    pull_log = ui.label("").classes("text-xs font-mono text-gray-400 hidden")

                    async def _pull_model() -> None:
                        if pulling["running"]:
                            return
                        pulling["running"] = True
                        btn_pull.props("loading disable")
                        pull_log.classes(remove="hidden")
                        pull_log.text = f"Lade {pull_inp.value} herunter — kann einige Minuten dauern …"
                        import asyncio, subprocess as _sp
                        try:
                            proc = await asyncio.create_subprocess_exec(
                                "ollama", "pull", pull_inp.value.strip(),
                                stdout=_sp.PIPE, stderr=_sp.STDOUT,
                            )
                            out, _ = await proc.communicate()
                            if proc.returncode == 0:
                                _save_llm("ollama_model", pull_inp.value.strip())
                                _save_llm("ollama_enabled", True)
                                pull_log.text = "✓ Modell geladen!"
                                await asyncio.sleep(1)
                                _ollama_card.refresh()
                            else:
                                pull_log.text = (out or b"").decode(errors="replace")[-300:]
                                ui.notify("Modell konnte nicht geladen werden.", type="negative")
                                btn_pull.props(remove="loading disable")
                        finally:
                            pulling["running"] = False

                    btn_pull = ui.button(
                        "Modell herunterladen", on_click=_pull_model, icon="download"
                    ).classes("ds-btn-primary")
                    pull_log

            # ZUSTAND 3: Läuft & Modell verfügbar
            else:
                with ui.row().classes("items-center gap-3 mb-4"):
                    ui.icon("check_circle").classes("text-green-500 text-xl flex-shrink-0")
                    with ui.column().classes("gap-0"):
                        ui.label("Ollama läuft lokal").classes("font-semibold text-sm")
                        ui.label(
                            f"Aktives Modell: {saved_model}  ·  {len(models)} Modell(e) verfügbar"
                        ).classes("text-xs text-gray-400")

                if not enabled:
                    callout("Ollama ist pausiert — aktiviere den Schalter oben um ihn zu nutzen.", "info")

                with ui.expansion("Einstellungen & Modelle", icon="tune").classes("w-full"):
                    with ui.column().classes("gap-3 p-2"):
                        model_sel = ui.select(
                            label="Aktives Modell",
                            options=models,
                            value=saved_model if saved_model in models else (models[0] if models else ""),
                        ).classes("w-full ds-input")

                        def _save_ollama_model() -> None:
                            _save_llm("ollama_model", model_sel.value)
                            ui.notify(f"Modell gewechselt: {model_sel.value}", type="positive")
                            _ollama_card.refresh()

                        ui.button("Modell wechseln", on_click=_save_ollama_model, icon="swap_horiz").classes("ds-btn-secondary")

                        ui.separator()
                        pull_inp2 = ui.input(placeholder="Neues Modell laden, z.B. mistral …").classes("w-full ds-input")

                        async def _pull_more() -> None:
                            name = pull_inp2.value.strip()
                            if not name:
                                return
                            import asyncio, subprocess as _sp
                            ui.notify(f"Lade {name} …", position="top")
                            proc = await asyncio.create_subprocess_exec(
                                "ollama", "pull", name,
                                stdout=_sp.PIPE, stderr=_sp.STDOUT,
                            )
                            _, _ = await proc.communicate()
                            if proc.returncode == 0:
                                ui.notify(f"✓ {name} geladen", type="positive", position="top")
                            else:
                                ui.notify(f"Fehler beim Laden von {name}", type="negative")
                            _ollama_card.refresh()

                        ui.button("Weiteres Modell laden", on_click=_pull_more, icon="download").classes("ds-btn-ghost")

    # ── Zusammenbauen ────────────────────────────────────────────────────────

    ui.label("KI-Assistenten").style(
        "font-size:0.65rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.06em;color:#9CA3AF;margin-top:8px;margin-bottom:4px"
    )
    ui.label(
        "Verbinde externe KI-Dienste oder nutze Ollama lokal — jeder Anbieter kann "
        "unabhängig aktiviert und pausiert werden."
    ).classes("text-xs text-gray-400 mb-4")

    with ui.element("div").classes("grid grid-cols-1 md:grid-cols-3 gap-4 w-full"):
        _openai_card()
        _anthropic_card()
        _ollama_card()


def _stat_tile(value: str, label: str, icon: str, color: str) -> None:
    """Mini-Kennzahl-Kachel für die Aktiv-Ansicht."""
    with ui.card().classes("ds-card-flat flex-1 min-w-28 text-center"):
        ui.icon(icon).classes(f"{color} text-2xl mb-1")
        ui.label(value).classes(f"text-xl font-bold {color}")
        ui.label(label).classes("text-xs text-gray-400 leading-tight whitespace-pre-line")


def build() -> None:
    """System-Status-Seite aufbauen."""
    cfg = load_config()
    ocr_langs = get_ocr_languages(cfg)
    checks = run_all_checks(ocr_langs)

    page_header(
        "System-Status",
        "Voraussetzungen pruefen und System-Informationen anzeigen.",
    )

    # ── In-App Installations-Hilfe ─────────────────────────────────────────
    build_dependency_card()

    # Voraussetzungen
    with ui.card().classes("ds-card w-full"):
        section_title("Voraussetzungen", "checklist")
        for check in checks:
            with ui.row().classes("items-center gap-3 py-2"):
                if check.ok:
                    ui.icon("check_circle").classes("text-xl text-green-500")
                else:
                    ui.icon("error").classes("text-xl text-red-500")
                ui.label(check.name).classes("font-semibold w-40")
                ui.label(check.message).classes("text-sm text-gray-600 flex-1")
                if check.version:
                    status_badge(check.version, "info")
            if not check.ok and check.fix_hint:
                callout(check.fix_hint, "warning")

    # System-Info
    with ui.card().classes("ds-card w-full"):
        section_title("System-Information", "computer")
        with ui.grid(columns=2).classes("gap-x-6 gap-y-2 mt-2"):
            ui.label("Betriebssystem:").classes("text-sm font-medium text-gray-500")
            ui.label(f"{platform.system()} {platform.release()}").classes("text-sm")
            ui.label("Python:").classes("text-sm font-medium text-gray-500")
            ui.label(f"{sys.version.split()[0]}").classes("text-sm")
            ui.label("Python-Pfad:").classes("text-sm font-medium text-gray-500")
            ui.label(sys.executable).classes("text-sm font-mono break-all")
            ui.label("Projekt:").classes("text-sm font-medium text-gray-500")
            ui.label(str(Path(__file__).resolve().parent.parent.parent.parent)).classes("text-sm font-mono break-all")
            ui.label("Doc-Sorter Version:").classes("text-sm font-medium text-gray-500")
            with ui.row().classes("items-center gap-2"):
                ui.label("0.3.0").classes("text-sm")
                status_badge("v0.3.0", "info")

    # Pfade-Status
    with ui.card().classes("ds-card w-full"):
        section_title("Pfade-Status", "folder")
        for key in ["inbox", "archive", "logs", "review"]:
            path = Path(cfg["paths"].get(key, ""))
            exists = path.exists()
            writable = False
            if exists and path.is_dir():
                try:
                    test_file = path / ".write_test"
                    test_file.touch()
                    test_file.unlink()
                    writable = True
                except OSError:
                    writable = False

            with ui.row().classes("items-center gap-3 py-2"):
                if exists and writable:
                    ui.icon("check_circle").classes("text-xl text-green-500")
                elif exists:
                    ui.icon("warning").classes("text-xl text-amber-500")
                else:
                    ui.icon("error").classes("text-xl text-red-500")
                ui.label(f"{key.capitalize()}:").classes("font-semibold w-24")
                ui.label(str(path)).classes("text-sm font-mono text-gray-600 break-all flex-1")
                if not exists:
                    status_badge("Existiert nicht", "error")
                elif not writable:
                    status_badge("Nicht beschreibbar", "warning")
                else:
                    status_badge("OK", "success")

    # ── Lern-Engine ────────────────────────────────────────────────────────────
    _build_learning_engine_section()

    # ── KI-Anbieter ────────────────────────────────────────────────────────────
    _build_ai_providers_section()
