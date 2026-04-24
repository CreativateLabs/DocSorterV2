"""Pytest-Fixtures fuer Doc-Sorter Tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Projekt-Root in sys.path haengen, damit `from src.xxx import yyy` geht
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture
def tmp_archive(tmp_path: Path) -> Path:
    """Temporaeres Archiv-Verzeichnis."""
    archive = tmp_path / "archive"
    archive.mkdir()
    return archive


@pytest.fixture
def sample_cfg(tmp_path: Path) -> dict:
    """Minimal-Config fuer Tests."""
    return {
        "paths": {
            "inbox": str(tmp_path / "inbox"),
            "archive": str(tmp_path / "archive"),
            "logs": str(tmp_path / "logs"),
            "review": str(tmp_path / "archive" / "_review"),
        },
        "document_types": {
            "rechnung": {
                "keywords_de": ["rechnung", "rechnungsnummer", "gesamtbetrag", "mwst"],
                "keywords_en": ["invoice", "amount due"],
                "keywords_sq": [],
            },
            "vertrag": {
                "keywords_de": ["vertrag", "unterzeichnet", "laufzeit"],
                "keywords_en": ["contract", "agreement"],
                "keywords_sq": [],
            },
        },
        "known_customers": [
            {"name": "GASAG", "aliases": ["gasag ag", "gasversorgung berlin"]},
            {"name": "Vattenfall", "aliases": []},
        ],
        "countries": {
            "deutschland": {"keywords": ["deutschland", "berlin", "münchen"]},
        },
        "file_types": [".pdf", ".docx", ".txt"],
        "ocr": {"languages": "eng+deu", "dpi": 200, "max_pages": 5},
        "confidence": {"min_text_length": 30, "uncertain_if_missing": ["kunde", "dokumentenart"]},
        "taxonomy": {
            "filename_pattern": "{dokumentenart}_{kunde}_{land}_{datum}",
            "folder_pattern": "{dokumentenart}/{land}/{kunde}/{jahr}",
        },
    }


@pytest.fixture
def isolated_store(tmp_path: Path, monkeypatch):
    """Assistant-Store auf temp-Verzeichnis umbiegen."""
    store_path = tmp_path / "_assistant.json"
    monkeypatch.setattr(
        "src.assistant_store._store_path",
        lambda: store_path,
    )
    yield store_path
