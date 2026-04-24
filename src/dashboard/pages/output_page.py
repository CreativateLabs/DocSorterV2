"""Output-Seite — Sortier-Laeufe als Accordions mit Live-Status.

Architektur:
- run_worker(run_id, pending): laeuft im Background-Thread, verschiebt
  Dateien einzeln, schreibt State alle 500 ms / 10 Files via atomic JSON.
- build(): rendert die Liste aller Run-State-Files. ui.timer pollt alle
  500 ms — UI-Thread bleibt frei, Reloads ueberleben den State.

Status-Werte: pending | running | done | done_with_errors | failed
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from nicegui import ui

from ..theme import callout, page_header, section_title, status_badge

logger = logging.getLogger(__name__)


RUN_STATE_DIR = Path("~/DocSorterV2/runs").expanduser()
_CASE_INSENSITIVE_FS = sys.platform in ("win32", "darwin")


# ---------------------------------------------------------------------------
# Atomic Writer
# ---------------------------------------------------------------------------

def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Worker — laeuft im Background-Thread, kein NiceGUI-Aufruf erlaubt
# ---------------------------------------------------------------------------

def _safe_move(src: Path, dst: Path) -> Path:
    """Verschiebt src nach dst; bei Kollision automatisch _001 etc. anhaengen."""
    dst.parent.mkdir(parents=True, exist_ok=True)

    final = dst
    if final.exists() or _CASE_INSENSITIVE_FS and final.exists():
        stem, suffix = final.stem, final.suffix
        counter = 1
        while final.exists() and counter <= 999:
            final = dst.parent / f"{stem}_{counter:03d}{suffix}"
            counter += 1
        if final.exists():
            final = dst.parent / f"{stem}_{int(time.time())}{suffix}"

    shutil.move(str(src), str(final))
    return final


def run_worker(run_id: str, pending: dict) -> None:
    """Background-Worker: Dateien aus pending verschieben, State persistieren.

    Wird vom Input-Page-Submit-Handler in einem daemon-Thread gestartet.
    """
    state_path = RUN_STATE_DIR / f"run_{run_id}.json"
    files = pending.get("files", [])
    state = {
        "id": run_id,
        "created_at": pending.get("created_at", datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
        "started_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "running",
        "total": len(files),
        "done": 0,
        "errors": [],
        "files": [],
    }

    try:
        _atomic_write_json(state_path, state)
    except Exception:
        logger.exception("Konnte initialen State nicht schreiben")
        return

    last_flush = 0.0

    for i, item in enumerate(files):
        src = Path(item["src"])
        dst = Path(item["target"])
        record: dict[str, Any] = {
            "src": str(src),
            "original_name": item.get("original_name", src.name),
            "dst_intended": str(dst),
            "ok": False,
        }
        try:
            if not src.exists():
                raise FileNotFoundError(f"Quelldatei verschwunden: {src}")
            final = _safe_move(src, dst)
            record["dst"] = str(final)
            record["ok"] = True
        except Exception as exc:
            err_msg = str(exc)
            logger.warning("Datei-Move fehlgeschlagen: %s -> %s | %s", src, dst, err_msg)
            record["err"] = err_msg
            state["errors"].append({"src": str(src), "err": err_msg})

        state["files"].append(record)
        state["done"] = i + 1

        # Batched Flush: alle 500 ms ODER alle 10 Dateien
        if time.monotonic() - last_flush > 0.5 or (i + 1) % 10 == 0:
            try:
                _atomic_write_json(state_path, state)
                last_flush = time.monotonic()
            except Exception:
                logger.exception("State-Flush fehlgeschlagen")

    state["status"] = "done" if not state["errors"] else "done_with_errors"
    state["finished_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    try:
        _atomic_write_json(state_path, state)
    except Exception:
        logger.exception("Finaler State-Flush fehlgeschlagen")

    # Pending-File aufraeumen
    try:
        (RUN_STATE_DIR / f"pending_{run_id}.json").unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

_STATUS_VARIANT = {
    "running":          ("warning", "In Arbeit", "#ff9f0a"),
    "done":             ("success", "Fertig",    "#00e87d"),
    "done_with_errors": ("error",   "Mit Fehlern", "#ff3366"),
    "pending":          ("neutral", "Wartet",    "#94a3b8"),
    "failed":           ("error",   "Fehlgeschlagen", "#ff3366"),
}


def _list_run_states() -> list[dict]:
    """Alle run_*.json einlesen, neueste zuerst."""
    if not RUN_STATE_DIR.exists():
        return []
    states: list[dict] = []
    for p in sorted(RUN_STATE_DIR.glob("run_*.json"), reverse=True):
        try:
            states.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception as exc:
            logger.debug("Konnte %s nicht lesen: %s", p, exc)
    return states


def build() -> None:
    """Output-Seite aufbauen: Liste aller Runs als Accordions."""
    RUN_STATE_DIR.mkdir(parents=True, exist_ok=True)

    page_header(
        "Output",
        "Sortier-Laeufe und verschobene Dateien.",
    )

    # Container, der per Polling aufgefrischt wird
    runs_container = ui.column().classes("w-full gap-3")

    def _render() -> None:
        runs_container.clear()
        states = _list_run_states()
        with runs_container:
            if not states:
                with ui.card().classes("ds-card-flat w-full").style(
                    "border-style:dashed;text-align:center;padding:32px"
                ):
                    ui.icon("folder_open").style(
                        "font-size:2.5rem;color:var(--ds-text-3);margin-bottom:8px"
                    )
                    ui.label("Noch keine Sortier-Laeufe.").style(
                        "font-size:0.88rem;color:var(--ds-text-2)"
                    )
                    ui.label(
                        "Lade auf der Input-Seite Dokumente hoch und klicke "
                        "'Struktur uebernehmen und sortieren'."
                    ).style("font-size:0.75rem;color:var(--ds-text-3)")
                return

            for st in states:
                _render_run_accordion(st)

    def _render_run_accordion(st: dict) -> None:
        status = st.get("status", "running")
        variant, label, color = _STATUS_VARIANT.get(
            status, ("neutral", status, "#94a3b8")
        )
        total = st.get("total", 0) or 1
        done = st.get("done", 0)
        pct = done / total
        created_at = st.get("created_at", "")
        run_id = st.get("id", "")

        with ui.expansion().classes("ds-expansion w-full").style(
            f"border-left:3px solid {color}"
        ) as exp:
            # Header — wir bauen den Slot manuell
            with exp.add_slot("header"):
                with ui.row().classes("w-full items-center gap-3"):
                    ui.icon("folder_special").style(
                        f"color:{color};font-size:1.2rem"
                    )
                    with ui.column().classes("gap-0").style("flex:1;min-width:0"):
                        ui.label(f"Run {run_id}").style(
                            "font-size:0.88rem;font-weight:700;color:var(--ds-text)"
                        )
                        ui.label(created_at).style(
                            "font-size:0.7rem;color:var(--ds-text-2)"
                        )
                    status_badge(label, variant)
                    ui.label(f"{done}/{total}").style(
                        f"font-size:0.78rem;font-weight:700;color:{color};min-width:60px;text-align:right"
                    )

            # Body
            with ui.column().classes("w-full gap-2").style("padding:8px 4px"):
                # Progress
                ui.linear_progress(value=pct).props(
                    f"color={'green' if status == 'done' else ('red' if status == 'done_with_errors' else 'amber')} rounded"
                ).style("height:8px")

                if status in ("running", "pending"):
                    ui.label(
                        f"Verschiebe {done} von {total} Datei(en)..."
                    ).style("font-size:0.78rem;color:var(--ds-text-2)")

                files = st.get("files", [])
                if not files:
                    ui.label("Noch keine Dateien verarbeitet.").style(
                        "font-size:0.78rem;color:var(--ds-text-3);font-style:italic;padding:8px 0"
                    )
                else:
                    # Tabelle: original_name -> dst (Fehler in rot)
                    for f in files:
                        ok = f.get("ok", False)
                        line_color = "#00e87d" if ok else "#ff3366"
                        with ui.row().classes("w-full items-center gap-2").style(
                            "padding:6px 10px;border-bottom:1px solid var(--ds-border);"
                            f"border-left:2px solid {line_color}"
                        ):
                            ui.icon(
                                "check_circle" if ok else "error"
                            ).style(f"color:{line_color};font-size:1rem;flex-shrink:0")
                            with ui.column().classes("gap-0").style(
                                "flex:1;min-width:0"
                            ):
                                ui.label(f.get("original_name", "")).style(
                                    "font-size:0.8rem;color:var(--ds-text);font-weight:600;"
                                    "overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                                )
                                if ok:
                                    ui.label(f.get("dst", "")).style(
                                        "font-size:0.7rem;color:var(--ds-text-2);"
                                        "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
                                        "font-family:'JetBrains Mono', monospace"
                                    )
                                else:
                                    ui.label(
                                        f.get("err", "Unbekannter Fehler")
                                    ).style(
                                        "font-size:0.72rem;color:#ff3366"
                                    )

    # Initial-Render + Polling
    _render()
    ui.timer(0.5, _render)
