"""Tests fuer src/classifier.py \u2014 Klassifikations-Pipeline."""

from __future__ import annotations

from src.classifier import classify


def test_classify_empty_text_unsicher():
    r = classify(
        text="",
        document_type_keywords={"rechnung": ["rechnung"]},
        known_customers=[],
        country_keywords={},
    )
    assert r.unsicher


def test_classify_rechnung_wird_erkannt():
    text = (
        "Rechnung Nr. 2026-001\n"
        "Rechnungsbetrag: 150,00 EUR\n"
        "MwSt: 19%\n"
        "Gesamtbetrag: 178,50 EUR"
    )
    r = classify(
        text=text,
        document_type_keywords={"rechnung": ["rechnung", "rechnungsbetrag", "mwst", "gesamtbetrag"]},
        known_customers=[],
        country_keywords={},
    )
    assert r.dokumentenart == "rechnung"


def test_classify_customer_from_alias():
    text = "Sehr geehrte Damen und Herren, die Gasag AG freut sich ..."
    r = classify(
        text=text,
        document_type_keywords={},
        known_customers=[{"name": "GASAG", "aliases": ["gasag ag"]}],
        country_keywords={},
    )
    assert r.kunde.lower() == "gasag"


def test_classify_country():
    text = "Ein langes Dokument aus Deutschland mit relevanten Inhalten ueber Berlin und Muenchen."
    r = classify(
        text=text,
        document_type_keywords={},
        known_customers=[],
        country_keywords={"deutschland": ["deutschland", "berlin"]},
    )
    assert r.land == "deutschland"


def test_classify_confidence_range():
    text = "Rechnung Gesamtbetrag 100 EUR"
    r = classify(
        text=text,
        document_type_keywords={"rechnung": ["rechnung", "gesamtbetrag"]},
        known_customers=[],
        country_keywords={},
    )
    assert 0.0 <= r.confidence <= 1.0


def test_classify_matched_keywords_non_empty_on_match():
    text = "Rechnung Rechnungsnummer 123"
    r = classify(
        text=text,
        document_type_keywords={"rechnung": ["rechnung", "rechnungsnummer"]},
        known_customers=[],
        country_keywords={},
    )
    assert len(r.matched_keywords) > 0
