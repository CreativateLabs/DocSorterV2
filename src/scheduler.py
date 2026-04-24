"""Nachtarbeiter — Hintergrund-Scheduler fuer automatische Routinen."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, date, time as dtime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Datenmodell
# ---------------------------------------------------------------------------

@dataclass
class ScheduledJob:
    id: str
    name: str
    label: str
    description: str
    enabled: bool
    interval_hours: float
    last_run: str | None
    next_run: str | None
    status: str                         # idle / running / success / error
    last_message: str
    # Erweiterte Felder (ab Version 2)
    schedule_type: str = "interval"     # "interval" | "daily"
    run_times: list = field(default_factory=list)   # ["HH:MM", ...] fuer daily
    category: str = "system"           # "dokumente" | "email" | "assistent" | "system"
    icon: str = "schedule"


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _jobs_file(cfg: dict) -> Path:
    archive = Path(cfg["paths"]["archive"]).expanduser()
    return archive.parent / "_scheduler_jobs.json"


def default_jobs() -> list[ScheduledJob]:
    """Standard-Jobs zurueckgeben."""
    return [
        ScheduledJob(
            id="scan_inbox",
            name="scan_inbox",
            label="Inbox automatisch scannen",
            description="Neue Dokumente erkennen, klassifizieren und Vorschlaege erstellen",
            enabled=True,
            interval_hours=1.0,
            last_run=None,
            next_run=None,
            status="idle",
            last_message="",
            schedule_type="interval",
            run_times=[],
            category="dokumente",
            icon="folder_open",
        ),
        ScheduledJob(
            id="fetch_emails",
            name="fetch_emails",
            label="E-Mails abrufen",
            description="Neue E-Mails von konfigurierten Postfaechern herunterladen",
            enabled=False,
            interval_hours=1.0,
            last_run=None,
            next_run=None,
            status="idle",
            last_message="",
            schedule_type="daily",
            run_times=["08:00", "12:00", "18:00"],
            category="email",
            icon="mail",
        ),
        ScheduledJob(
            id="apply_email_rules",
            name="apply_email_rules",
            label="E-Mail-Regeln anwenden",
            description="Konfigurierte Regeln auf abgerufene Mails anwenden",
            enabled=True,
            interval_hours=6.0,
            last_run=None,
            next_run=None,
            status="idle",
            last_message="",
            schedule_type="interval",
            run_times=[],
            category="email",
            icon="rule",
        ),
        ScheduledJob(
            id="check_subscriptions",
            name="check_subscriptions",
            label="Abonnements pruefen",
            description="Ablaufende Abonnements erkennen und Erinnerungen setzen",
            enabled=True,
            interval_hours=24.0,
            last_run=None,
            next_run=None,
            status="idle",
            last_message="",
            schedule_type="daily",
            run_times=["09:00"],
            category="assistent",
            icon="subscriptions",
        ),
        ScheduledJob(
            id="clean_logs",
            name="clean_logs",
            label="Logs bereinigen",
            description="Log-Dateien aelter als 30 Tage automatisch entfernen",
            enabled=True,
            interval_hours=168.0,
            last_run=None,
            next_run=None,
            status="idle",
            last_message="",
            schedule_type="interval",
            run_times=[],
            category="system",
            icon="cleaning_services",
        ),
    ]


# ---------------------------------------------------------------------------
# Persistenz
# ---------------------------------------------------------------------------

def load_jobs(cfg: dict) -> list[ScheduledJob]:
    """Jobs aus JSON-Datei laden; fehlende Jobs werden mit Defaults ergaenzt."""
    jobs_path = _jobs_file(cfg)
    defaults = {j.id: j for j in default_jobs()}

    if not jobs_path.exists():
        return list(defaults.values())

    try:
        raw: list[dict] = json.loads(jobs_path.read_text(encoding="utf-8"))
        loaded: dict[str, ScheduledJob] = {}
        for item in raw:
            job_id = item.get("id", "")
            if not job_id:
                continue
            default = defaults.get(job_id)
            loaded[job_id] = ScheduledJob(
                id=job_id,
                name=item.get("name", job_id),
                label=item.get("label", default.label if default else job_id),
                description=item.get("description", default.description if default else ""),
                enabled=item.get("enabled", True),
                interval_hours=float(item.get("interval_hours", 1.0)),
                last_run=item.get("last_run"),
                next_run=item.get("next_run"),
                status=item.get("status", "idle"),
                last_message=item.get("last_message", ""),
                # v2-Felder mit Fallback auf Default
                schedule_type=item.get("schedule_type", default.schedule_type if default else "interval"),
                run_times=item.get("run_times", default.run_times if default else []),
                category=item.get("category", default.category if default else "system"),
                icon=item.get("icon", default.icon if default else "schedule"),
            )

        # Fehlende Default-Jobs hinzufuegen
        for job_id, default_job in defaults.items():
            if job_id not in loaded:
                loaded[job_id] = default_job

        # Reihenfolge wie defaults
        ordered = []
        for jid in defaults:
            if jid in loaded:
                ordered.append(loaded[jid])
        return ordered

    except Exception as exc:
        logger.warning("Fehler beim Laden der Jobs: %s", exc)
        return list(defaults.values())


def save_jobs(cfg: dict, jobs: list[ScheduledJob]) -> None:
    """Jobs in JSON-Datei speichern."""
    jobs_path = _jobs_file(cfg)
    try:
        jobs_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps([asdict(j) for j in jobs], ensure_ascii=False, indent=2, default=str)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=jobs_path.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, jobs_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as exc:
        logger.error("Fehler beim Speichern der Jobs: %s", exc)


# ---------------------------------------------------------------------------
# Scheduling-Logik
# ---------------------------------------------------------------------------

def is_job_due(job: ScheduledJob) -> bool:
    """Prueft ob ein Job jetzt ausgefuehrt werden soll."""
    if not job.enabled:
        return False

    now = datetime.now()

    # --- Tageszeit-basiert ---
    if job.schedule_type == "daily" and job.run_times:
        today = now.date()
        last_run_dt: datetime | None = None
        if job.last_run:
            try:
                last_run_dt = datetime.fromisoformat(job.last_run)
            except (ValueError, TypeError):
                pass

        for time_str in job.run_times:
            try:
                parts_t = str(time_str).split(":")
                if len(parts_t) != 2:
                    continue
                h, m = int(parts_t[0]), int(parts_t[1])
                scheduled_dt = datetime.combine(today, dtime(h, m))
                if scheduled_dt <= now:
                    if last_run_dt is None or last_run_dt < scheduled_dt:
                        return True
            except (ValueError, IndexError):
                continue
        return False

    # --- Intervall-basiert ---
    if job.next_run is None:
        return True
    try:
        next_dt = datetime.fromisoformat(job.next_run)
        return now >= next_dt
    except (ValueError, TypeError):
        return True


# ---------------------------------------------------------------------------
# Job-Ausfuehrung
# ---------------------------------------------------------------------------

def _run_scan_inbox(cfg: dict, agent: Any = None) -> str:
    """Inbox scannen und Dateien klassifizieren."""
    if agent is not None:
        try:
            if hasattr(agent, "rescan"):
                result = agent.rescan()
                return f"{result} Datei(en) verarbeitet" if isinstance(result, int) else "Inbox gescannt"
            elif hasattr(agent, "execute_action"):
                agent.execute_action("rescan")
                return "Inbox gescannt"
        except Exception as exc:
            raise RuntimeError(f"Agent-Fehler: {exc}") from exc

    inbox_path = Path(cfg.get("paths", {}).get("inbox", "")).expanduser()
    if not inbox_path.parts:
        return "Inbox-Pfad nicht konfiguriert"
    if not inbox_path.exists():
        return "Inbox-Verzeichnis nicht gefunden"

    file_types = set(cfg.get("file_types", [".pdf", ".docx", ".txt", ".md"]))
    count = sum(1 for f in inbox_path.iterdir() if f.is_file() and f.suffix.lower() in file_types)
    return f"{count} Datei(en) in Inbox gefunden"


def _run_fetch_emails(cfg: dict, agent: Any = None) -> str:
    """Neue E-Mails von konfigurierten Konten abrufen."""
    try:
        from .email_connector import fetch_emails, load_emails, save_emails, EmailAccount
    except ImportError:
        return "E-Mail-Modul nicht verfuegbar"

    accounts_raw = cfg.get("email_accounts", [])
    if not accounts_raw:
        return "Keine E-Mail-Konten konfiguriert"

    total_new = 0
    errors = []

    for acc_data in accounts_raw:
        if not acc_data.get("enabled", True):
            continue
        try:
            account = EmailAccount(
                name=acc_data.get("name", ""),
                imap_host=acc_data.get("imap_host", ""),
                imap_port=acc_data.get("imap_port", 993),
                username=acc_data.get("username", ""),
                password=acc_data.get("password", ""),
                use_ssl=acc_data.get("use_ssl", True),
                enabled=True,
                folders=acc_data.get("folders", ["INBOX"]),
            )
            msgs = fetch_emails(account, max_emails=50)
            # Neue zu vorhandenen hinzufuegen (Deduplizierung via id)
            existing = load_emails(cfg)
            existing_ids = {m.get("id") for m in existing.get("messages", [])}
            new_msgs = [m for m in msgs if m.get("id") not in existing_ids]
            if new_msgs:
                existing.setdefault("messages", []).extend(new_msgs)
                existing["last_sync"] = datetime.now().isoformat()
                save_emails(cfg, existing.get("messages", []))
                total_new += len(new_msgs)
                # Gehirn: neue Mails auf Aktionspunkte pruefen
                try:
                    from .brain import process_email_item
                    from .feed_store import add_item as _feed_add
                    for m in new_msgs:
                        feed_item = {
                            "title": m.get("subject", "(kein Betreff)"),
                            "content": m.get("snippet", "") or m.get("body", ""),
                        }
                        _feed_add(
                            source="email",
                            title=feed_item["title"],
                            content=feed_item["content"],
                            metadata={"from": m.get("sender_email", ""), "date": m.get("date", "")},
                        )
                        process_email_item(feed_item)
                except Exception as _be:
                    logger.debug("Brain E-Mail-Fetch-Verarbeitung fehlgeschlagen: %s", _be)
        except Exception as exc:
            errors.append(str(exc))

    if errors:
        return f"{total_new} neue Mail(s), {len(errors)} Fehler: {errors[0]}"
    return f"{total_new} neue E-Mail(s) abgerufen"


def _run_apply_email_rules(cfg: dict, agent: Any = None) -> str:
    """E-Mail-Regeln auf gecachte Mails anwenden."""
    from . import assistant_store
    rules = assistant_store.get_email_rules()
    active_rules = [r for r in rules if r.get("active", True)]
    if not active_rules:
        return "Keine aktiven E-Mail-Regeln vorhanden"
    return f"{len(active_rules)} Regel(n) geprueft"


def _run_check_subscriptions(cfg: dict, agent: Any = None) -> str:
    """Abonnements pruefen die in 30 Tagen ablaufen."""
    from . import assistant_store
    from datetime import date as d, timedelta as td

    subscriptions = assistant_store.get_subscriptions()
    active_subs = [s for s in subscriptions if s.get("active", True)]
    assistant_store.mark_sub_check_done()

    if not active_subs:
        return "Keine aktiven Abonnements vorhanden"

    cutoff = d.today() - td(days=30)
    needs_review = []
    for sub in active_subs:
        last_review = sub.get("last_review")
        if last_review is None:
            needs_review.append(sub)
        else:
            try:
                if d.fromisoformat(last_review) <= cutoff:
                    needs_review.append(sub)
            except (ValueError, TypeError):
                needs_review.append(sub)

    count = len(needs_review)
    if count == 0:
        return f"{len(active_subs)} Abonnement(s) geprueft — alle aktuell"
    return f"{count} Abonnement(s) benoetigen Ueberpruefung"


def _run_clean_logs(cfg: dict, agent: Any = None) -> str:
    """Log-Dateien aelter als 30 Tage entfernen."""
    logs_path = Path(cfg["paths"]["logs"]).expanduser()
    if not logs_path.exists():
        return "Log-Verzeichnis nicht gefunden"

    cutoff = datetime.now() - timedelta(days=30)
    removed = 0
    for log_file in logs_path.iterdir():
        if not log_file.is_file():
            continue
        try:
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                log_file.unlink()
                removed += 1
        except Exception as exc:
            logger.warning("Fehler beim Loeschen von %s: %s", log_file, exc)
    return f"{removed} Log-Datei(en) entfernt"


_JOB_RUNNERS = {
    "scan_inbox": _run_scan_inbox,
    "fetch_emails": _run_fetch_emails,
    "apply_email_rules": _run_apply_email_rules,
    "check_subscriptions": _run_check_subscriptions,
    "clean_logs": _run_clean_logs,
}


def run_job(job_id: str, cfg: dict, agent: Any = None) -> dict:
    """Einen Job nach ID ausfuehren."""
    jobs = load_jobs(cfg)
    job_map = {j.id: j for j in jobs}

    if job_id not in job_map:
        return {"job_id": job_id, "status": "error", "message": f"Job '{job_id}' nicht gefunden"}

    job = job_map[job_id]
    job.status = "running"
    job.last_run = datetime.now().isoformat()
    save_jobs(cfg, jobs)

    runner = _JOB_RUNNERS.get(job_id)
    if runner is None:
        job.status = "error"
        job.last_message = f"Kein Runner fuer Job '{job_id}'"
        job.next_run = (datetime.now() + timedelta(hours=job.interval_hours)).isoformat()
        save_jobs(cfg, jobs)
        return {"job_id": job_id, "status": "error", "message": job.last_message}

    try:
        message = runner(cfg, agent)
        job.status = "success"
        job.last_message = message
    except Exception as exc:
        logger.error("Job '%s' fehlgeschlagen: %s", job_id, exc)
        job.status = "error"
        job.last_message = str(exc)

    # next_run nur fuer intervall-basierte Jobs setzen
    if job.schedule_type == "interval":
        job.next_run = (datetime.now() + timedelta(hours=job.interval_hours)).isoformat()

    save_jobs(cfg, jobs)

    result = {
        "job_id": job_id,
        "status": job.status,
        "message": job.last_message,
        "timestamp": job.last_run,
    }

    # Gehirn: Job-Ergebnis verarbeiten (Todos, Feed-Items erzeugen)
    try:
        from .brain import process_scheduler_result
        process_scheduler_result(job_id, result)
    except Exception as exc:
        logger.debug("Brain-Verarbeitung fuer Job '%s' fehlgeschlagen: %s", job_id, exc)

    return result


def run_due_jobs(cfg: dict, agent: Any = None) -> list[dict]:
    """Alle aktivierten und faelligen Jobs ausfuehren."""
    jobs = load_jobs(cfg)
    results = []

    for job in jobs:
        if not job.enabled:
            continue
        if not is_job_due(job):
            continue
        logger.info("Starte faelligen Job: %s", job.id)
        result = run_job(job.id, cfg, agent)
        results.append(result)

    return results
