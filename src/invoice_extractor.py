"""Rechnungsdaten-Extraktor — liest Betrag, Datum, Lieferant aus Dokumenttext.

Rein regex-basiert, keine KI notwendig. Unterstuetzt deutsche und englische
Rechnungsformate. Wird von agent.py beim Erkennen von Rechnungs-Dokumenten
aufgerufen.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Betrag-Erkennung
# ---------------------------------------------------------------------------

# Reihenfolge: genauere Patterns zuerst
_AMOUNT_PATTERNS = [
    # "Gesamtbetrag: 1.234,56 €" / "Total: EUR 1,234.56"
    r"(?:gesamt|total|summe|rechnungsbetrag|betrag|netto|brutto|zahlbar|fällig)"
    r"[^0-9]{0,30}?(\d{1,6}[.,]\d{2})\s*(?:EUR|€)?",
    # "€ 1.234,56" oder "1.234,56 €"
    r"(?:EUR|€)\s*(\d{1,6}[.,]\d{2})",
    r"(\d{1,6}[.,]\d{2})\s*(?:EUR|€)",
    # Fallback: größte Zahl mit Dezimalstellen
    r"(\d{1,6}[.,]\d{2})",
]


def _parse_amount(raw: str) -> float:
    """Rohstring '1.234,56' oder '1234.56' in float konvertieren."""
    raw = raw.strip()
    if "," in raw and "." in raw:
        # 1.234,56 (deutsch) oder 1,234.56 (englisch)
        if raw.rfind(",") > raw.rfind("."):
            # Deutsch: letztes Komma = Dezimal
            raw = raw.replace(".", "").replace(",", ".")
        else:
            # Englisch: letzter Punkt = Dezimal
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return round(float(raw), 2)
    except ValueError:
        return 0.0


def extract_amount(text: str) -> float:
    """Höchsten wahrscheinlichen Rechnungsbetrag aus Text extrahieren."""
    text_lower = text.lower()
    candidates: list[float] = []

    for pattern in _AMOUNT_PATTERNS:
        for m in re.finditer(pattern, text_lower, re.IGNORECASE):
            val = _parse_amount(m.group(1))
            if val > 0:
                candidates.append(val)

    if not candidates:
        return 0.0

    # Priorisiere: Werte zwischen 1 € und 100.000 €, bevorzuge größten
    valid = [v for v in candidates if 1.0 <= v <= 100_000.0]
    if valid:
        return max(valid)
    return candidates[0]


# ---------------------------------------------------------------------------
# Datum-Erkennung
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    # DD.MM.YYYY
    (r"\b(\d{2})\.(\d{2})\.(\d{4})\b", "%d.%m.%Y"),
    # YYYY-MM-DD
    (r"\b(\d{4})-(\d{2})-(\d{2})\b", "%Y-%m-%d"),
    # DD/MM/YYYY
    (r"\b(\d{2})/(\d{2})/(\d{4})\b", "%d/%m/%Y"),
]

_DATE_CONTEXT_WORDS = [
    "rechnungsdatum", "datum", "ausgestellt", "erstellt", "invoice date",
    "date", "vom", "am", "fällig", "zahlbar bis",
]


def extract_date(text: str) -> str:
    """Rechnungsdatum als ISO-String (YYYY-MM-DD) extrahieren."""
    text_lower = text.lower()

    # Erst: Datum in der Nähe von Kontext-Wörtern suchen
    for ctx in _DATE_CONTEXT_WORDS:
        idx = text_lower.find(ctx)
        if idx == -1:
            continue
        snippet = text[max(0, idx):idx + 60]
        for pattern, fmt in _DATE_PATTERNS:
            m = re.search(pattern, snippet)
            if m:
                try:
                    dt = datetime.strptime(m.group(0), fmt)
                    if 2000 <= dt.year <= 2035:
                        return dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

    # Fallback: erstes valides Datum im gesamten Text
    for pattern, fmt in _DATE_PATTERNS:
        for m in re.finditer(pattern, text):
            try:
                dt = datetime.strptime(m.group(0), fmt)
                if 2000 <= dt.year <= 2035:
                    return dt.strftime("%Y-%m-%d")
            except Exception:
                pass

    return datetime.today().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Lieferant-Erkennung
# ---------------------------------------------------------------------------

def extract_vendor(text: str, filename: str = "") -> str:
    """Lieferanten-/Absendernamen aus Text oder Dateiname extrahieren."""
    text_lines = [l.strip() for l in text.split("\n") if l.strip()][:20]

    # Keyword-Suche: "Firma:", "Absender:", "Von:", "Lieferant:"
    vendor_keywords = ["firma:", "company:", "absender:", "von:", "lieferant:", "supplier:", "issued by:"]
    for line in text_lines:
        ll = line.lower()
        for kw in vendor_keywords:
            if ll.startswith(kw):
                return line[len(kw):].strip()[:80]

    # Dateiname: erste sinnvolle Komponente (vor _ oder Datum)
    if filename:
        stem = Path(filename).stem
        # Entferne Datum-Patterns
        stem_clean = re.sub(r"\d{4}[-_]\d{2}[-_]\d{2}", "", stem)
        stem_clean = re.sub(r"\d{2}[-_.]\d{2}[-_.]\d{4}", "", stem_clean)
        parts = re.split(r"[_\-\s]+", stem_clean)
        candidates = [p for p in parts if len(p) > 2 and not p.isdigit()]
        if candidates:
            return candidates[0].capitalize()[:80]

    # Erste Zeile als Fallback (oft Firmenname oben links)
    if text_lines:
        first = text_lines[0]
        if 3 < len(first) < 80 and not first.startswith("Rechnung"):
            return first

    return "Unbekannt"


# ---------------------------------------------------------------------------
# Rechnungsnummer
# ---------------------------------------------------------------------------

def extract_invoice_number(text: str) -> str:
    """Rechnungsnummer extrahieren."""
    patterns = [
        r"rechnungs(?:nummer|nr\.?)\s*[:\-#]?\s*([A-Z0-9\-/]+)",
        r"invoice\s+(?:no\.?|number)\s*[:\-#]?\s*([A-Z0-9\-/]+)",
        r"re(?:chnungs)?-?nr\.?\s*[:\-]?\s*([A-Z0-9\-/]+)",
        r"belegnummer\s*[:\-]?\s*([A-Z0-9\-/]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            nr = m.group(1).strip()
            if len(nr) <= 30:
                return nr
    return ""


# ---------------------------------------------------------------------------
# Kategorie-Heuristik
# ---------------------------------------------------------------------------

_CATEGORY_MAP = {
    "software": ["software", "lizenz", "subscription", "saas", "cloud", "hosting", "domain"],
    "büro": ["bürobedarf", "papier", "drucker", "büro", "office"],
    "telekommunikation": ["telefon", "internet", "mobilfunk", "telekom", "vodafone", "o2", "1&1"],
    "energie": ["strom", "gas", "energie", "wasser", "eon", "enbw", "vattenfall"],
    "transport": ["bahn", "db ", "flug", "taxi", "mietwagen", "toll", "maut", "benzin", "tanken"],
    "versicherung": ["versicherung", "assurance", "insurance", "allianz", "axa", "huk"],
    "hardware": ["laptop", "computer", "monitor", "drucker", "hardware", "apple", "samsung"],
    "beratung": ["beratung", "consulting", "dienstleistung", "honorar", "rechtsanwalt", "steuer"],
    "marketing": ["werbung", "marketing", "seo", "design", "druck", "flyer"],
    "miete": ["miete", "mietvertrag", "nebenkosten", "kaltmiete", "warmmiete"],
}


def extract_category(text: str, filename: str = "") -> str:
    """Ausgaben-Kategorie aus Inhalt ableiten."""
    combined = (text[:500] + " " + filename).lower()
    for category, keywords in _CATEGORY_MAP.items():
        if any(kw in combined for kw in keywords):
            return category.capitalize()
    return "Sonstiges"


# ---------------------------------------------------------------------------
# Haupt-Funktion
# ---------------------------------------------------------------------------

def extract_invoice_data(text: str, filename: str = "") -> dict:
    """Alle Rechnungsdaten aus Text extrahieren.

    Returns dict mit: amount, date, vendor, invoice_number, category
    """
    return {
        "amount": extract_amount(text),
        "date": extract_date(text),
        "vendor": extract_vendor(text, filename),
        "invoice_number": extract_invoice_number(text),
        "category": extract_category(text, filename),
    }
