"""Benutzer-Profil: persistentes Lerngedaechtnis des Systems.

Das Profil lernt aus jeder Interaktion — Dokumente, E-Mails —
und wird automatisch besser: Firmennamen, Betraege, wiederkehrende Aufgaben
und persoenliche Schlagwoerter werden erkannt und gespeichert.

Store: ~/.doc-sorter/user_profile.json

Lernquellen:
  - Dokumente         (Kundennamen, Betraege, Dokumentarten)
  - E-Mails           (Absender, Betreff-Schlagwoerter)
  - Assistent-Store   (Rechnungen, Ausgaben, Abos)
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Wird nach Klassendefinitionen aufgerufen (am Ende des Moduls)

# ---------------------------------------------------------------------------
# Interne Lade-/Speicher-Helfer
# ---------------------------------------------------------------------------

def _profile_path() -> Path:
    """Benutzerspezifischer Profilpfad: <user_dir>/user_profile.json.

    Leitet den Nutzer-Ordner aus dem Archiv-Pfad ab (archive.parent),
    der nach dem Login per _apply_user_paths() gesetzt wird.
    Fallback: ~/.doc-sorter/user_profile.json (globaler Standard).
    """
    try:
        from .config import load_config
        cfg = load_config()
        archive = cfg.get("paths", {}).get("archive", "")
        if archive:
            user_dir = Path(archive).expanduser().parent
            user_dir.mkdir(parents=True, exist_ok=True)
            return user_dir / "user_profile.json"
    except Exception:
        pass
    return Path.home() / ".doc-sorter" / "user_profile.json"


def _load() -> dict:
    p = _profile_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        return _empty_profile()
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _empty_profile()


def _save(profile: dict) -> None:
    """Atomar in user_profile.json schreiben (temp-Datei + rename verhindert Datei-Korruption)."""
    import os, tempfile
    try:
        p = _profile_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        profile["stats"]["last_updated"] = datetime.now().isoformat()
        content = json.dumps(profile, ensure_ascii=False, indent=2, default=str)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, p)  # atomisches Rename
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as exc:
        logger.warning("UserProfile: Speichern fehlgeschlagen: %s", exc)


def _empty_profile() -> dict:
    return {
        "entities":         {},   # name → {count, type, score, first_seen, last_seen, sources}
        "recurring_tasks":  {},   # normalized_key → {canonical, count, last_seen, interval_days}
        "tags":             {},   # tag → count (aus Lernquellen)
        "amounts":          {},   # str(amount) → {count, label, last_seen, entities}
        # Dauerhaft gelernte Korrekturen fuer Erkennungs-Fehler (OCR, Typos):
        # falsche_schreibweise_lower → korrekte_schreibweise
        # z.B. "gasak" → "Gasag", "wattenfall" → "Vattenfall"
        "aliases":          {},
        # Benutzerdefinierte globale Schlagworte — gelten fuer ALLE Quellen:
        # Dokumente, E-Mails, Nachrichten.
        # Format: {keyword_lower: {"original": str, "added": date_str, "hits": int}}
        "global_keywords":  {},
        # Keyword-Qualitaets-Scores pro Dokumentenart:
        # {doctype: {keyword: {"hits": int, "decisive": int, "corrections": int}}}
        # hits      = Wie oft hat dieses Wort zur Klassifikation beigetragen
        # decisive  = Wie oft war es allein/hauptsaechlich entscheidend (≤3 Keywords gesamt)
        # corrections = Wie oft fuehrte es zu einer falschen Klassifikation (Nutzer hat korrigiert)
        "keyword_scores":   {},
        "stats": {
            "total_memos":     0,
            "total_documents": 0,
            "total_emails":    0,
            "last_updated":    "",
        },
    }


# ---------------------------------------------------------------------------
# Entitaets-Update (Firmen, Personen, Orte)
# ---------------------------------------------------------------------------

def _update_entity(profile: dict, name: str, entity_type: str, source: str) -> None:
    """Entitaet im Profil zaehlen / anlegen."""
    name = name.strip()
    if not name or len(name) < 2 or name.lower() in ("unbekannt", "unknown", ""):
        return
    today = str(date.today())
    ent = profile["entities"].setdefault(name, {
        "count":      0,
        "type":       entity_type,
        "score":      0.0,
        "first_seen": today,
        "last_seen":  today,
        "sources":    [],
    })
    ent["count"] += 1
    ent["last_seen"] = today
    if source not in ent["sources"]:
        ent["sources"].append(source)
    # Score: Haeufigkeit + Quellen-Diversitaet + Aktualitaet
    ent["score"] = round(
        ent["count"] * 1.0
        + len(ent["sources"]) * 2.0
        + _recency_bonus(ent["first_seen"]),
        2,
    )


def _recency_bonus(first_seen_str: str) -> float:
    """Juengere Einfuehrung → kleiner Bonus (max. 3.0 innerhalb 30 Tage)."""
    try:
        delta = (date.today() - date.fromisoformat(first_seen_str)).days
        return max(0.0, 3.0 - delta * 0.1)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Betrags-Tracking
# ---------------------------------------------------------------------------

def _update_amount(profile: dict, amount: float, entity_name: str = "") -> None:
    """Bekannten Betrag im Profil speichern."""
    if amount <= 0 or amount > 1_000_000:
        return
    key = str(round(amount, 2))
    today = str(date.today())
    entry = profile["amounts"].setdefault(key, {
        "count":      0,
        "label":      _fmt_amount(amount),
        "last_seen":  today,
        "entities":   [],
    })
    entry["count"] += 1
    entry["last_seen"] = today
    if entity_name and entity_name not in entry["entities"]:
        entry["entities"].append(entity_name)


def _fmt_amount(amount: float) -> str:
    try:
        s = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} Euro"
    except Exception:
        return f"{amount} Euro"


# ---------------------------------------------------------------------------
# Wiederkehrende-Aufgaben-Erkennung
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset([
    "ich", "muss", "soll", "bitte", "mal", "die", "der", "das", "und",
    "oder", "eine", "ein", "den", "dem", "des", "am", "im", "an", "in",
    "fuer", "für", "auf", "mit", "von", "bei", "bis", "zu", "zum", "zur",
])


def _normalize_task(text: str) -> str:
    """Aufgabentext normalisieren fuer Duplikat-Erkennung."""
    # Unicode-Normalisierung
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    # Sonderzeichen entfernen
    text = re.sub(r"[^\w\s]", " ", text)
    # Stop-Woerter entfernen
    words = [w for w in text.split() if w not in _STOP_WORDS and len(w) > 1]
    return " ".join(sorted(words))  # sortiert → reihenfolge-unabhaengig


def _task_similarity(a: str, b: str) -> float:
    """Jaccard-Aehnlichkeit zweier normalisierten Aufgaben (0.0–1.0)."""
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _update_recurring_tasks(profile: dict, todos: list[str], source: str) -> None:
    """Todos auf Wiederholungen pruefen und Muster speichern."""
    today = str(date.today())
    recurring = profile["recurring_tasks"]

    for todo in todos:
        todo = todo.strip()
        if not todo or len(todo) < 5:
            continue
        norm = _normalize_task(todo)

        # Aehnlichsten bestehenden Task suchen
        best_key, best_sim = None, 0.0
        for key in recurring:
            sim = _task_similarity(norm, key)
            if sim > best_sim:
                best_key, best_sim = key, sim

        if best_sim >= 0.5 and best_key:
            # Existierenden Task aktualisieren
            t = recurring[best_key]
            t["count"] += 1
            t["last_seen"] = today
            # Intervall schaetzen
            if t.get("prev_seen") and t["count"] >= 2:
                try:
                    delta = (date.today() - date.fromisoformat(t["prev_seen"])).days
                    old_interval = t.get("interval_days", delta)
                    t["interval_days"] = round((old_interval + delta) / 2)
                except Exception:
                    pass
            t["prev_seen"] = today
            if len(todo) > len(t.get("canonical", "")):
                t["canonical"] = todo  # laengere Schreibweise bevorzugen
        else:
            # Neuen Task anlegen
            recurring[norm] = {
                "canonical":    todo,
                "count":        1,
                "first_seen":   today,
                "last_seen":    today,
                "prev_seen":    today,
                "interval_days": None,
                "source":       source,
            }


# ---------------------------------------------------------------------------
# Oeffentliche Lern-Funktionen
# ---------------------------------------------------------------------------

def learn_from_memo_analysis(
    analysis: dict,
    transcript: str,
    memo_id: str = "",
) -> None:
    """Nach jeder Memo-Transkription aufrufen — lernt Firmen, Betraege, Tags, Muster."""
    try:
        profile = _load()
        today = str(date.today())

        # Tags
        for tag in analysis.get("tags", []):
            if tag:
                profile["tags"][tag.lower()] = profile["tags"].get(tag.lower(), 0) + 1

        # Todos → wiederkehrende Aufgaben erkennen
        todos = analysis.get("todos", [])
        _update_recurring_tasks(profile, todos, source="memo")

        # Entitaeten aus Zusammenfassung + Transkript extrahieren
        combined = " ".join([
            analysis.get("summary", ""),
            " ".join(todos),
            transcript[:1000],
        ])
        _extract_and_learn_entities(profile, combined, source="memo")

        # Betraege aus Transkript
        for amount in _extract_amounts(transcript):
            _update_amount(profile, amount)

        profile["stats"]["total_memos"] = profile["stats"].get("total_memos", 0) + 1
        _save(profile)
        logger.debug("UserProfile: Memo gelernt (id=%s)", memo_id)
    except Exception as exc:
        logger.warning("UserProfile.learn_from_memo_analysis fehlgeschlagen: %s", exc)


def learn_from_document(
    customer: str = "",
    doc_type: str = "",
    amount: float | None = None,
    vendor: str = "",
    extra_text: str = "",
) -> None:
    """Nach Dokument-Verarbeitung aufrufen — lernt Lieferanten, Betraege, Typen."""
    try:
        profile = _load()

        for name in [customer, vendor]:
            if name and name not in ("unbekannt", ""):
                _update_entity(profile, name, "company", "document")

        if doc_type and doc_type not in ("unbekannt", ""):
            profile["tags"][doc_type.lower()] = profile["tags"].get(doc_type.lower(), 0) + 1

        if amount and amount > 0:
            entity = customer or vendor or ""
            _update_amount(profile, amount, entity)

        if extra_text:
            _extract_and_learn_entities(profile, extra_text[:500], source="document")

        profile["stats"]["total_documents"] = profile["stats"].get("total_documents", 0) + 1
        _save(profile)
    except Exception as exc:
        logger.warning("UserProfile.learn_from_document fehlgeschlagen: %s", exc)


def learn_from_email(
    subject: str = "",
    sender: str = "",
    content: str = "",
) -> None:
    """Nach E-Mail-Verarbeitung aufrufen — lernt Absender, Schlagwoerter."""
    try:
        profile = _load()

        # Absender-Domain als Firma
        if sender and "@" in sender:
            domain = sender.split("@")[-1].split(".")[0]
            if len(domain) > 2:
                _update_entity(profile, domain.capitalize(), "company", "email")

        # Entitaeten aus Betreff
        combined = f"{subject} {content[:300]}"
        _extract_and_learn_entities(profile, combined, source="email")

        profile["stats"]["total_emails"] = profile["stats"].get("total_emails", 0) + 1
        _save(profile)
    except Exception as exc:
        logger.warning("UserProfile.learn_from_email fehlgeschlagen: %s", exc)


# ---------------------------------------------------------------------------
# Kontext-Abfragen fuer context_extractor.py
# ---------------------------------------------------------------------------

def get_top_entities(entity_type: str | None = None, n: int = 30) -> list[dict]:
    """Top-N Entitaeten nach Score, optional gefiltert nach Typ."""
    try:
        profile = _load()
        entities = profile.get("entities", {})
        items = [
            {"name": k, **v}
            for k, v in entities.items()
            if entity_type is None or v.get("type") == entity_type
        ]
        return sorted(items, key=lambda x: x.get("score", 0), reverse=True)[:n]
    except Exception:
        return []


def get_top_amounts(n: int = 20) -> list[str]:
    """Haeufigste Betraege als formatierte Strings."""
    try:
        profile = _load()
        amounts = profile.get("amounts", {})
        sorted_amounts = sorted(amounts.values(), key=lambda x: x.get("count", 0), reverse=True)
        return [a["label"] for a in sorted_amounts[:n]]
    except Exception:
        return []


def get_top_tags(n: int = 20) -> list[str]:
    """Haeufigste Tags."""
    try:
        profile = _load()
        tags = profile.get("tags", {})
        return [t for t, _ in sorted(tags.items(), key=lambda x: x[1], reverse=True)[:n]]
    except Exception:
        return []


def get_recurring_tasks(min_count: int = 2) -> list[dict]:
    """Wiederkehrende Aufgaben (min. min_count Wiederholungen)."""
    try:
        profile = _load()
        tasks = profile.get("recurring_tasks", {})
        return [
            t for t in tasks.values()
            if t.get("count", 0) >= min_count
        ]
    except Exception:
        return []


def get_profile_summary() -> dict:
    """Zusammenfassung des gelernten Profils (fuer UI-Anzeige)."""
    try:
        profile = _load()
        return {
            "total_entities":        len(profile.get("entities", {})),
            "top_companies":         [e["name"] for e in get_top_entities("company", 10)],
            "top_tags":              get_top_tags(10),
            "recurring_tasks_count": len([t for t in profile.get("recurring_tasks", {}).values()
                                         if t.get("count", 0) >= 2]),
            "known_amounts_count":   len(profile.get("amounts", {})),
            "stats":                 profile.get("stats", {}),
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Globale Schlagworte — zentrale API fuer alle Quellen
# ---------------------------------------------------------------------------

def get_global_keywords() -> list[str]:
    """Alle benutzerdefinierten Schlagworte (Original-Schreibweise, alphabetisch)."""
    try:
        kws = _load().get("global_keywords", {})
        return sorted(
            (v.get("original", k) for k, v in kws.items()),
            key=str.casefold,
        )
    except Exception:
        return []


def get_global_keywords_lower() -> frozenset[str]:
    """Alle Schlagworte in Kleinschreibung — fuer schnellen `in`-Check."""
    try:
        return frozenset(_load().get("global_keywords", {}).keys())
    except Exception:
        return frozenset()


def add_global_keywords(keywords: list[str]) -> None:
    """Schlagworte hinzufügen (Duplikate werden ignoriert).

    Quelle: Wizard, Einstellungen, Assistent.
    """
    if not keywords:
        return
    try:
        today = str(date.today())
        profile = _load()
        kws = profile.setdefault("global_keywords", {})
        changed = False
        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            key = kw.lower()
            if key not in kws:
                kws[key] = {"original": kw, "added": today, "hits": 0}
                changed = True
                # Auch in tags eintragen (als Lernfutter mit Boost)
                profile.setdefault("tags", {})[key] = profile["tags"].get(key, 0) + 5
        if changed:
            _save(profile)
            logger.info("GlobalKeywords: %d neue Schlagworte hinzugefügt", len(keywords))
    except Exception as exc:
        logger.warning("add_global_keywords fehlgeschlagen: %s", exc)


def remove_global_keyword(keyword: str) -> None:
    """Schlagwort entfernen."""
    try:
        key = keyword.strip().lower()
        if not key:
            return
        profile = _load()
        kws = profile.setdefault("global_keywords", {})
        if key in kws:
            del kws[key]
            _save(profile)
    except Exception as exc:
        logger.warning("remove_global_keyword fehlgeschlagen: %s", exc)


def record_keyword_hit(keyword: str) -> None:
    """Einen Treffer fuer ein Schlagwort registrieren (Lerneffekt).

    Wird aufgerufen wenn das System ein Schlagwort in einem Dokument
    oder einer E-Mail erkennt.
    """
    try:
        key = keyword.strip().lower()
        if not key:
            return
        profile = _load()
        kws = profile.get("global_keywords", {})
        if key in kws:
            kws[key]["hits"] = kws[key].get("hits", 0) + 1
            # Auch als Tag zaehlen → staerkt das Lerngedaechtnis
            profile.setdefault("tags", {})[key] = profile["tags"].get(key, 0) + 1
            _save(profile)
    except Exception:
        pass


def record_classification_feedback(
    old_type: str,
    new_type: str,
    matched_keywords: list[str],
    is_confirmation: bool = False,
) -> None:
    """Feedback aus der Review-Seite im Lern-Profil speichern.

    Wird aufgerufen wenn der Nutzer ein Dokument im Review bestaetigt oder korrigiert:
      - Bestaetigung (is_confirmation=True oder old_type==new_type):
            Alle beteiligten Keywords erhalten Bonus-Hits.
            Waren es ≤3 Keywords → werden sie als "decisive" markiert.
      - Korrektur (old_type != new_type):
            Keywords der falschen Klassifikation erhalten einen Korrektur-Zaehler (+1).
            Der neue korrekte Typ erhaelt einen Tag-Boost (staerkt Tags fuer kuenftige LLM-Prompts).

    Args:
        old_type:         Urspruengliche Klassifikation (vor Review)
        new_type:         Vom Nutzer bestaetigte/korrigierte Klassifikation
        matched_keywords: Keywords die zur Klassifikation gefuehrt haben
        is_confirmation:  True wenn Nutzer explizit bestaetigt (kein Typwechsel)
    """
    try:
        profile = _load()
        kw_scores = profile.setdefault("keyword_scores", {})

        confirmed = is_confirmation or (old_type == new_type)

        if confirmed:
            # Richtig klassifiziert → Keywords staerken
            type_scores = kw_scores.setdefault(new_type, {})
            for kw in matched_keywords:
                entry = type_scores.setdefault(kw, {"hits": 0, "decisive": 0, "corrections": 0})
                entry["hits"] += 2  # Bestaetigung = doppelter Bonus
                # Wenn nur wenige Keywords entscheidend waren → als decisive markieren
                if len(matched_keywords) <= 3:
                    entry["decisive"] += 1

            # Auch global_keywords hit-counter erhoehen
            kws = profile.get("global_keywords", {})
            for kw in matched_keywords:
                key = kw.lower()
                if key in kws:
                    kws[key]["hits"] = kws[key].get("hits", 0) + 1

            logger.info(
                "Lern-Feedback (Bestaetigung): Typ '%s', %d Keywords gestaerkt",
                new_type, len(matched_keywords),
            )

        else:
            # Falsch klassifiziert → Korrektur-Signal fuer alte Keywords
            if old_type and old_type not in ("unbekannt", ""):
                type_scores = kw_scores.setdefault(old_type, {})
                for kw in matched_keywords:
                    entry = type_scores.setdefault(kw, {"hits": 0, "decisive": 0, "corrections": 0})
                    entry["corrections"] += 1  # Negatives Lern-Signal

            # Neuen korrekten Typ als Tag boosten (hilft LLM-Kontext und Wiederholung)
            if new_type and new_type not in ("unbekannt", ""):
                profile.setdefault("tags", {})[new_type.lower()] = (
                    profile["tags"].get(new_type.lower(), 0) + 3
                )

            logger.info(
                "Lern-Feedback (Korrektur): '%s' → '%s', %d Keywords mit Korrektur-Signal",
                old_type, new_type, len(matched_keywords),
            )

        _save(profile)

    except Exception as exc:
        logger.warning("record_classification_feedback fehlgeschlagen: %s", exc)


def get_keyword_relevance_scores(doctype: str) -> list[dict]:
    """Keywords eines Dokumententyps sortiert nach echtem Relevanz-Score.

    Relevanz-Score = decisive * 3 + hits - corrections * 2

    Gibt aus:
      - keyword:     Das Schlagwort
      - hits:        Wie oft bei korrekter Klassifikation beteiligt
      - decisive:    Wie oft allein/hauptsaechlich entscheidend (≤3 Keywords)
      - corrections: Wie oft zu falscher Klassifikation gefuehrt
      - relevance:   Gesamtscore (hoeher = zuverlaessiger)
    """
    try:
        profile = _load()
        type_scores = profile.get("keyword_scores", {}).get(doctype, {})

        result = []
        for kw, data in type_scores.items():
            hits = data.get("hits", 0)
            decisive = data.get("decisive", 0)
            corrections = data.get("corrections", 0)
            relevance = decisive * 3 + hits - corrections * 2
            result.append({
                "keyword":     kw,
                "hits":        hits,
                "decisive":    decisive,
                "corrections": corrections,
                "relevance":   relevance,
            })

        return sorted(result, key=lambda x: x["relevance"], reverse=True)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Alias-System: dauerhaft gelernte Erkennungs-Korrekturen (OCR, Typos)
# ---------------------------------------------------------------------------

def get_aliases() -> dict[str, str]:
    """Gibt alle gelernten Aliase zurueck: {falsch_lower: korrekt}."""
    try:
        return _load().get("aliases", {})
    except Exception:
        return {}


def add_alias(wrong: str, correct: str) -> None:
    """Alias dauerhaft speichern. wrong → correct (z.B. 'gasak' → 'Gasag')."""
    try:
        if not wrong or not correct or wrong.lower() == correct.lower():
            return
        profile = _load()
        profile.setdefault("aliases", {})[wrong.lower().strip()] = correct.strip()
        _save(profile)
        logger.info("UserProfile: Alias gelernt: '%s' → '%s'", wrong, correct)
    except Exception as exc:
        logger.warning("UserProfile.add_alias fehlgeschlagen: %s", exc)


def apply_aliases_to_text(text: str) -> str:
    """Bekannte Erkennungs-Fehler im Text korrigieren.

    Ersetzt alle bekannten Fehlschreibungen durch die korrekten Firmennamen.
    Gross-/Kleinschreibung des Originals wird beachtet (Wortgrenzen).
    """
    try:
        if not text:
            return text or ""
        aliases = get_aliases()
        if not aliases:
            return text
        for wrong, correct in aliases.items():
            # Wortgrenze beachten, case-insensitiv ersetzen
            pattern = re.compile(r"\b" + re.escape(wrong) + r"\b", re.IGNORECASE)
            text = pattern.sub(correct, text)
        return text
    except Exception:
        return text


def learn_aliases_from_context(text: str, known_companies: list[str]) -> None:
    """Fuzzy-Matching: findet Erkennungs-Fehler und speichert sie als Aliase.

    Wenn ein Wort im Text einem bekannten Firmennamen aehnlich ist (>=0.80),
    aber nicht exakt gleich, wird der Alias dauerhaft gespeichert.
    """
    try:
        from difflib import SequenceMatcher
        import re as _re

        words_in_text = _re.findall(r"\b[A-Za-zÄÖÜäöüß]{3,}\b", text)

        for word in words_in_text:
            word_low = word.lower()
            for company in known_companies:
                comp_low = company.lower()
                if word_low == comp_low:
                    break  # exakt korrekt
                ratio = SequenceMatcher(None, word_low, comp_low).ratio()
                if ratio >= 0.80:
                    add_alias(word, company)
                    break
    except Exception as exc:
        logger.debug("learn_aliases_from_context fehlgeschlagen: %s", exc)


# ---------------------------------------------------------------------------
# Interne Helfer
# ---------------------------------------------------------------------------

_COMPANY_SUFFIXES = re.compile(
    # Suffix MUSS eigenes Wort sein (Leerzeichen davor) — verhindert Fehlmatches
    # wie "Gasag" → "Gas" + "ag" (AG case-insensitiv)
    r"\b((?:[\w\-\.]+\s){0,3}[\w\-\.]+)\s+(?:GmbH|AG|KG|e\.V\.|OHG|GbR|SE|Inc|Ltd)\b",
    re.IGNORECASE,
)
_KNOWN_GERMAN_COMPANIES = [
    "Gasag", "Vattenfall", "Berliner Wasserbetriebe", "Vonovia",
    "Deutsche Wohnen", "E.ON", "RWE", "EnBW", "Telekom",
    "Vodafone", "O2", "Lidl", "Aldi", "Edeka", "Rewe", "dm",
    "Deutsche Bahn", "Sparkasse", "Commerzbank", "Deutsche Bank",
    "ING", "DKB", "Postbank", "AOK", "TK", "Barmer",
]

# Seed-Aliase fuer haeufige Erkennungs-Fehler (OCR, Typos) — beim ersten Laden gesetzt
_SEED_ALIASES: dict[str, str] = {
    "gasak":       "Gasag",
    "kasak":       "Gasag",
    "gassag":      "Gasag",
    "wattenfall":  "Vattenfall",
    "battenfall":  "Vattenfall",
    "watten fall": "Vattenfall",
    "badenfall":   "Vattenfall",
    "telekom":      "Telekom",
    "deutsche ban": "Deutsche Bahn",   # 'h' fehlt
    "deutsche bahn":"Deutsche Bahn",   # Korrekte Schreibweise (Kleinschreibung)
}


def _ensure_seed_aliases() -> None:
    """Seed-Aliase beim ersten Laden eintragen falls noch nicht vorhanden."""
    try:
        profile = _load()
        aliases = profile.setdefault("aliases", {})
        changed = False
        for wrong, correct in _SEED_ALIASES.items():
            if wrong not in aliases:
                aliases[wrong] = correct
                changed = True
        if changed:
            _save(profile)
    except Exception:
        pass


# Beim Modul-Import Seed-Aliase sicherstellen
try:
    _ensure_seed_aliases()
except Exception as _seed_exc:
    logger.debug("_ensure_seed_aliases beim Import fehlgeschlagen (wird beim nächsten Zugriff wiederholt): %s", _seed_exc)


_AMOUNT_RE = re.compile(
    r"(\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|Euro|EUR)",
    re.IGNORECASE,
)


def _extract_amounts(text: str) -> list[float]:
    """Geldbetraege aus Text extrahieren."""
    amounts = []
    for m in _AMOUNT_RE.finditer(text):
        raw = m.group(1).replace(".", "").replace(",", ".")
        try:
            amounts.append(float(raw))
        except ValueError:
            pass
    return amounts


def _extract_and_learn_entities(profile: dict, text: str, source: str) -> None:
    """Firmennamen + bekannte Entitaeten aus Text extrahieren und lernen."""
    # Bekannte deutsche Firmen direkt suchen
    for company in _KNOWN_GERMAN_COMPANIES:
        if re.search(re.escape(company), text, re.IGNORECASE):
            _update_entity(profile, company, "company", source)

    # Firmensuffix-Muster (GmbH, AG, ...) — vollstaendiger Match inkl. Suffix
    _INVALID_START = re.compile(r"^\d|^(?:Euro|EUR|€|und|oder|mit|fuer|für)\b", re.IGNORECASE)
    for match in _COMPANY_SUFFIXES.finditer(text):
        name = match.group(0).strip()
        if 3 <= len(name) <= 60 and not _INVALID_START.search(name):
            _update_entity(profile, name, "company", source)
