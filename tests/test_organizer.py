"""Tests fuer src/organizer.py \u2014 Dateiname, Ordnerstruktur, Move-Logik."""

from __future__ import annotations

from pathlib import Path

from src.classifier import Classification
from src.organizer import build_filename, build_target_folder, safe_name


def test_safe_name_basic():
    assert safe_name("Hello World") == "Hello_World"


def test_safe_name_removes_forbidden_chars():
    assert "/" not in safe_name("a/b")
    assert "\\" not in safe_name("a\\b")
    assert "*" not in safe_name("a*b")
    assert "?" not in safe_name("a?b")


def test_safe_name_empty_defaults_to_unbekannt():
    assert safe_name("") == "unbekannt"
    assert safe_name("   ") == "unbekannt"


def test_safe_name_length_limit():
    long_text = "x" * 200
    assert len(safe_name(long_text, max_len=60)) == 60


def test_build_filename_standard():
    cls = Classification(
        dokumentenart="rechnung",
        kunde="GASAG",
        land="deutschland",
        datum="15.03.26",
    )
    name = build_filename(cls, ".pdf")
    assert name == "rechnung_GASAG_deutschland_15.03.26.pdf"


def test_build_filename_preserves_extension_case():
    cls = Classification(dokumentenart="brief", kunde="x", land="y", datum="01.01.26")
    assert build_filename(cls, ".PDF").endswith(".pdf")


def test_build_filename_length_safe():
    cls = Classification(
        dokumentenart="x" * 50,
        kunde="y" * 50,
        land="z" * 50,
        datum="11.11.99",
    )
    out = build_filename(cls, ".pdf")
    assert len(out) <= 200


def test_build_target_folder_normal(tmp_path: Path):
    cls = Classification(
        dokumentenart="rechnung",
        kunde="GASAG",
        land="deutschland",
        datum="15.03.26",
        jahr="2026",
    )
    target = build_target_folder(tmp_path, cls, is_review=False)
    # Erwartet: archive / rechnung / deutschland / GASAG / 2026
    parts = target.relative_to(tmp_path).parts
    assert parts[0] == "rechnung"
    assert "deutschland" in parts
    assert "GASAG" in parts
    assert "2026" in parts


def test_build_target_folder_review(tmp_path: Path):
    cls = Classification(dokumentenart="rechnung", unsicher=True)
    target = build_target_folder(tmp_path, cls, is_review=True)
    parts = target.relative_to(tmp_path).parts
    assert parts[0] == "_review"
    assert "rechnung" in parts
