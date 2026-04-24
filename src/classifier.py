"""Dokumente klassifizieren: Dokumentenart, Kunde, Land, Datum erkennen."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Classification:
    """Ergebnis der Dokumenten-Klassifikation."""
    dokumentenart: str = "unbekannt"
    kunde: str = "unbekannt"
    land: str = "unbekannt"
    datum: str = ""           # DD.MM.YY
    datum_full: str = ""      # DD.MM.YYYY (fuer Logs)
    jahr: str = ""            # YYYY (fuer Ordner)
    sprache: str = "unknown"
    unsicher: bool = False
    unsicher_gruende: list[str] = field(default_factory=list)
    text_laenge: int = 0
    confidence: float = 0.0   # 0.0 - 1.0 Gesamtsicherheit
    # Lern-System: welche Keywords haben zur Klassifikation gefuehrt
    matched_keywords: list[str] = field(default_factory=list)


def classify(
    text: str,
    document_type_keywords: dict[str, list[str]],
    known_customers: list[dict[str, Any]],
    country_keywords: dict[str, list[str]],
    min_text_length: int = 30,
    uncertain_fields: list[str] | None = None,
) -> Classification:
    """Text analysieren und Classification-Objekt zurueckgeben."""
    if uncertain_fields is None:
        uncertain_fields = ["kunde", "dokumentenart"]

    result = Classification(text_laenge=len(text.strip()))

    # Sprache erkennen
    result.sprache = _detect_language(text)

    # Dokumentenart
    doc_type, doc_score, matched_kws = _guess_document_type(text, document_type_keywords)
    result.dokumentenart = doc_type
    result.matched_keywords = matched_kws

    # Kunde / Vertragspartner
    result.kunde = _guess_customer(text, known_customers)

    # Land
    result.land = _guess_country(text, country_keywords)

    # Datum
    datum_full = _guess_date(text)
    result.datum_full = datum_full
    if datum_full:
        parts = datum_full.split(".")
        if len(parts) == 3:
            dd, mm, yyyy = parts
            result.datum = f"{dd}.{mm}.{yyyy[-2:]}"
            result.jahr = yyyy
    else:
        # Kein Datum gefunden → leer lassen; Organizer verwendet "unbekannt" als Ordner
        result.datum = ""
        result.datum_full = ""
        result.jahr = ""
        logger.debug("Kein Datum im Text gefunden, Datum bleibt leer")

    # Confidence berechnen (0.0 - 1.0)
    scores = []
    scores.append(min(doc_score / 3.0, 1.0))  # Doc-Type Score
    scores.append(1.0 if result.kunde != "unbekannt" else 0.0)
    scores.append(1.0 if result.land != "unbekannt" else 0.0)
    scores.append(1.0 if datum_full else 0.2)  # Kein Datum = niedrig
    scores.append(min(result.text_laenge / 200.0, 1.0))  # Mehr Text = sicherer
    result.confidence = round(sum(scores) / len(scores), 2)

    # Unsicherheit pruefen
    gruende = []
    if result.text_laenge < min_text_length:
        gruende.append("zu wenig Text erkannt")
    if "kunde" in uncertain_fields and result.kunde == "unbekannt":
        gruende.append("Kunde nicht erkannt")
    if "dokumentenart" in uncertain_fields and result.dokumentenart == "unbekannt":
        gruende.append("Dokumentenart nicht erkannt")

    if gruende:
        result.unsicher = True
        result.unsicher_gruende = gruende

    logger.info(
        "Klassifiziert: art=%s kunde=%s land=%s confidence=%.2f%s",
        result.dokumentenart, result.kunde, result.land, result.confidence,
        f" UNSICHER: {', '.join(gruende)}" if gruende else "",
    )
    return result


def _detect_language(text: str) -> str:
    """Sprache erkennen mit langdetect."""
    if len(text.strip()) < 20:
        logger.debug("Text zu kurz fuer Spracherkennung (%d Zeichen)", len(text.strip()))
        return "unknown"
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0
        lang = detect(text)
        logger.debug("Sprache erkannt: %s", lang)
        return lang
    except ImportError:
        logger.warning("langdetect nicht installiert -- Spracherkennung deaktiviert")
        return "unknown"
    except Exception as e:
        logger.warning("Spracherkennung fehlgeschlagen: %s", e)
        return "unknown"


def _guess_document_type(text: str, type_keywords: dict[str, list[str]]) -> tuple[str, int, list[str]]:
    """Dokumentenart anhand von Keywords erkennen. Returns (type, score, matched_keywords)."""
    t = text.lower()

    scores: dict[str, int] = {}
    keyword_matches: dict[str, list[str]] = {}
    for doc_type, keywords in type_keywords.items():
        score = 0
        matched: list[str] = []
        for kw in keywords:
            kw_lower = kw.lower()
            # Wortgrenzen-Matching: verhindert Teilstring-Treffer (z.B. "coeo" in "microeo")
            try:
                if re.search(r"\b" + re.escape(kw_lower) + r"\b", t):
                    score += 1
                    matched.append(kw)
            except re.error:
                if kw_lower in t:  # Fallback bei ungueltigem Pattern
                    score += 1
                    matched.append(kw)
        if score > 0:
            scores[doc_type] = score
            keyword_matches[doc_type] = matched

    if scores:
        best = max(scores, key=scores.get)
        logger.debug("Dokumentenart-Scores: %s -> %s", scores, best)
        return best, scores[best], keyword_matches.get(best, [])

    return "unbekannt", 0, []


def _guess_customer(text: str, known_customers: list[dict[str, Any]]) -> str:
    """Kunde / Vertragspartner erkennen."""
    t = text.lower()

    for customer in known_customers:
        for alias in customer.get("aliases", []):
            if alias.lower() in t:
                logger.debug("Kunde erkannt via Alias '%s': %s", alias, customer["name"])
                return customer["name"]

    patterns = [
        r"(?:kunde|customer|client|auftraggeber|vertragspartner|partner|firma|company)[:\s]+([A-Z][A-Za-z\s&.-]{2,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            value = re.split(r"[,\n\r]", value)[0].strip()
            if 2 < len(value) < 50:
                logger.debug("Kunde erkannt via Pattern: %s", value)
                return value

    return "unbekannt"


def _guess_country(text: str, country_keywords: dict[str, list[str]]) -> str:
    """Land anhand von Keywords erkennen."""
    t = text.lower()

    scores: dict[str, int] = {}
    for country, keywords in country_keywords.items():
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            try:
                if re.search(r"\b" + re.escape(kw_lower) + r"\b", t):
                    score += 1
            except re.error:
                if kw_lower in t:
                    score += 1
        if score > 0:
            scores[country] = score

    if scores:
        best = max(scores, key=scores.get)
        logger.debug("Land-Scores: %s -> %s", scores, best)
        return best

    return "unbekannt"


def _guess_date(text: str) -> str:
    """Datum im Format DD.MM.YYYY aus dem Text extrahieren."""
    month_names = {
        "januar": "01", "february": "02", "februar": "02", "march": "03",
        "maerz": "03", "april": "04", "mai": "05", "may": "05",
        "juni": "06", "june": "06", "juli": "07", "july": "07",
        "august": "08", "september": "09", "oktober": "10", "october": "10",
        "november": "11", "dezember": "12", "december": "12",
        "jan": "01", "feb": "02", "mar": "03", "apr": "04",
        "jun": "06", "jul": "07", "aug": "08", "sep": "09",
        "oct": "10", "okt": "10", "nov": "11", "dec": "12", "dez": "12",
    }

    # DD.MM.YYYY
    match = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b", text)
    if match:
        dd, mm, yyyy = match.groups()
        if _valid_date(int(dd), int(mm), int(yyyy)):
            return f"{int(dd):02d}.{int(mm):02d}.{yyyy}"

    # DD.MM.YY  -- dynamischer Cutoff: alles bis (aktuelles Jahr + 20 Jahre) = 2000er, Rest = 1900er
    match = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2})\b", text)
    if match:
        dd, mm, yy = match.groups()
        cutoff = (datetime.now().year + 20) % 100  # z.B. 2026+20=2046 → cutoff=46
        yyyy = f"20{yy}" if int(yy) <= cutoff else f"19{yy}"
        if _valid_date(int(dd), int(mm), int(yyyy)):
            return f"{int(dd):02d}.{int(mm):02d}.{yyyy}"

    # YYYY-MM-DD (ISO)
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        yyyy, mm, dd = match.groups()
        if _valid_date(int(dd), int(mm), int(yyyy)):
            return f"{dd}.{mm}.{yyyy}"

    # DD/MM/YYYY
    match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text)
    if match:
        dd, mm, yyyy = match.groups()
        if _valid_date(int(dd), int(mm), int(yyyy)):
            return f"{int(dd):02d}.{int(mm):02d}.{yyyy}"

    # "15. Januar 2026" / "March 15, 2026"
    for name, mm_str in month_names.items():
        pattern = rf"\b(\d{{1,2}})\.\s*{re.escape(name)}\s+(\d{{4}})\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            dd, yyyy = match.groups()
            return f"{int(dd):02d}.{mm_str}.{yyyy}"

        pattern = rf"\b{re.escape(name)}\s+(\d{{1,2}}),?\s+(\d{{4}})\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            dd, yyyy = match.groups()
            return f"{int(dd):02d}.{mm_str}.{yyyy}"

    return ""


def _valid_date(dd: int, mm: int, yyyy: int) -> bool:
    """Pruefen ob ein Datum gueltig und plausibel ist."""
    try:
        datetime(yyyy, mm, dd)
        return 1900 <= yyyy <= 2099
    except (ValueError, OverflowError):
        return False
