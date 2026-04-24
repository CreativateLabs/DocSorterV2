"""Assistent-Daten-Store: Todos, Ausgaben, Abos, E-Mail-Regeln."""

from __future__ import annotations
import json
from datetime import date, datetime
from pathlib import Path


def _store_path() -> Path:
    try:
        from .config import load_config
        cfg = load_config()
        return Path(cfg["paths"]["archive"]).expanduser().parent / "_assistant.json"
    except Exception:
        return Path.home() / ".docsorter_assistant.json"


def _load() -> dict:
    p = _store_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"todos": [], "expenses": [], "subscriptions": [], "email_rules": [], "invoices": [], "last_sub_check": None}


def _save(data: dict) -> None:
    """Atomar in _assistant.json schreiben (temp-Datei + rename verhindert Datei-Korruption)."""
    import os, tempfile
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
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


# TODOS
def get_todos() -> list[dict]:
    return _load().get("todos", [])

def add_todo(text: str, priority: str = "normal", due: str = "") -> None:
    data = _load()
    data["todos"].append({
        "id": datetime.now().isoformat(),
        "text": text,
        "priority": priority,
        "due": due,
        "done": False,
        "created": date.today().isoformat(),
    })
    _save(data)

def toggle_todo(todo_id: str) -> None:
    data = _load()
    for t in data["todos"]:
        if t["id"] == todo_id:
            t["done"] = not t["done"]
    _save(data)

def delete_todo(todo_id: str) -> None:
    data = _load()
    data["todos"] = [t for t in data["todos"] if t["id"] != todo_id]
    _save(data)

# EXPENSES
def get_expenses() -> list[dict]:
    return _load().get("expenses", [])

def add_expense(name: str, amount: float, cycle: str = "monatlich", category: str = "") -> None:
    data = _load()
    data["expenses"].append({
        "id": datetime.now().isoformat(),
        "name": name,
        "amount": amount,
        "cycle": cycle,
        "category": category,
        "active": True,
        "created": date.today().isoformat(),
    })
    _save(data)

def delete_expense(exp_id: str) -> None:
    data = _load()
    data["expenses"] = [e for e in data["expenses"] if e["id"] != exp_id]
    _save(data)

# SUBSCRIPTIONS
def get_subscriptions() -> list[dict]:
    return _load().get("subscriptions", [])

def add_subscription(name: str, amount: float, cycle: str = "monatlich", url: str = "") -> None:
    data = _load()
    data["subscriptions"].append({
        "id": datetime.now().isoformat(),
        "name": name,
        "amount": amount,
        "cycle": cycle,
        "url": url,
        "active": True,
        "last_review": None,
        "created": date.today().isoformat(),
    })
    _save(data)

def review_subscription(sub_id: str, keep: bool) -> None:
    data = _load()
    for s in data["subscriptions"]:
        if s["id"] == sub_id:
            s["active"] = keep
            s["last_review"] = date.today().isoformat()
    _save(data)

def delete_subscription(sub_id: str) -> None:
    data = _load()
    data["subscriptions"] = [s for s in data["subscriptions"] if s["id"] != sub_id]
    _save(data)

def get_last_sub_check() -> str | None:
    return _load().get("last_sub_check")

def mark_sub_check_done() -> None:
    data = _load()
    data["last_sub_check"] = date.today().isoformat()
    _save(data)

# INVOICES (Einzel-Rechnungen aus Dokumenten-Erkennung)
def get_invoices() -> list[dict]:
    return _load().get("invoices", [])

def add_invoice(
    vendor: str,
    amount: float,
    invoice_date: str = "",
    category: str = "Sonstiges",
    invoice_number: str = "",
    source_file: str = "",
    notes: str = "",
) -> str:
    """Rechnung hinzufuegen. Gibt ID zurueck."""
    data = _load()
    inv_id = datetime.now().isoformat()
    _date_val = invoice_date or str(datetime.today().date())
    data.setdefault("invoices", []).append({
        "id": inv_id,
        "vendor": vendor,
        "amount": amount,
        "date": _date_val,
        "category": category,
        "invoice_number": invoice_number,
        "source_file": source_file,
        "notes": notes,
        "created": str(datetime.today().date()),
    })
    _save(data)
    return inv_id

def delete_invoice(inv_id: str) -> None:
    data = _load()
    data["invoices"] = [i for i in data.get("invoices", []) if i["id"] != inv_id]
    _save(data)

def update_invoice(inv_id: str, **kwargs) -> None:
    data = _load()
    for inv in data.get("invoices", []):
        if inv["id"] == inv_id:
            inv.update(kwargs)
    _save(data)


# VERBINDUNGEN — Dokument ↔ Todo ↔ Ausgabe

def link_todo_doc(todo_id: str, doc_path: str, doc_label: str) -> None:
    """Dokument an Todo verknuepfen."""
    data = _load()
    for t in data["todos"]:
        if t["id"] == todo_id:
            refs = t.setdefault("linked_docs", [])
            if not any(r["path"] == doc_path for r in refs):
                refs.append({"path": doc_path, "label": doc_label})
    _save(data)

def unlink_todo_doc(todo_id: str, doc_path: str) -> None:
    data = _load()
    for t in data["todos"]:
        if t["id"] == todo_id:
            t["linked_docs"] = [r for r in t.get("linked_docs", []) if r["path"] != doc_path]
    _save(data)

def link_invoice_todo(invoice_id: str, todo_id: str, todo_label: str) -> None:
    """Todo an Rechnung verknuepfen."""
    data = _load()
    for inv in data.get("invoices", []):
        if inv["id"] == invoice_id:
            refs = inv.setdefault("linked_todos", [])
            if not any(r["id"] == todo_id for r in refs):
                refs.append({"id": todo_id, "label": todo_label})
    _save(data)

def unlink_invoice_todo(invoice_id: str, todo_id: str) -> None:
    data = _load()
    for inv in data.get("invoices", []):
        if inv["id"] == invoice_id:
            inv["linked_todos"] = [r for r in inv.get("linked_todos", []) if r["id"] != todo_id]
    _save(data)

def get_linked_docs(todo_id: str) -> list[dict]:
    for t in get_todos():
        if t["id"] == todo_id:
            return t.get("linked_docs", [])
    return []

def get_linked_todos_for_invoice(invoice_id: str) -> list[dict]:
    for inv in get_invoices():
        if inv["id"] == invoice_id:
            return inv.get("linked_todos", [])
    return []

def find_todos_linked_to_doc(doc_path: str) -> list[dict]:
    """Alle Todos die ein bestimmtes Dokument verknuepft haben."""
    return [t for t in get_todos() if any(r["path"] == doc_path for r in t.get("linked_docs", []))]


# EMAIL RULES
def get_email_rules() -> list[dict]:
    return _load().get("email_rules", [])

def add_email_rule(
    sender: str = "",
    subject_contains: str = "",
    target_folder: str = "",
    action: str = "verschieben",
    sender_pattern: str = "",
    subject_pattern: str = "",
) -> None:
    """E-Mail-Regel hinzufuegen.

    Akzeptiert sowohl die alten Parameter (sender, subject_contains) als auch
    die neuen Parameter (sender_pattern, subject_pattern) fuer Kompatibilitaet.
    """
    # Neue Parameter haben Vorrang, Fallback auf alte Parameter
    effective_sender = sender_pattern or sender
    effective_subject = subject_pattern or subject_contains
    data = _load()
    data["email_rules"].append({
        "id": datetime.now().isoformat(),
        "sender": effective_sender,
        "subject_contains": effective_subject,
        "sender_pattern": effective_sender,
        "subject_pattern": effective_subject,
        "target_folder": target_folder,
        "action": action,
        "active": True,
        "created": date.today().isoformat(),
    })
    _save(data)

def toggle_email_rule(rule_id: str) -> None:
    data = _load()
    for r in data["email_rules"]:
        if r["id"] == rule_id:
            r["active"] = not r["active"]
    _save(data)

def delete_email_rule(rule_id: str) -> None:
    data = _load()
    data["email_rules"] = [r for r in data["email_rules"] if r["id"] != rule_id]
    _save(data)
