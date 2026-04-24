"""Tests fuer src/config.py \u2014 Defaults, Validierung, Getters."""

from __future__ import annotations

import yaml
from pathlib import Path

from src.config import (
    _DEFAULTS,
    _apply_defaults,
    get_country_keywords,
    get_document_type_keywords,
    get_file_types,
    get_known_customers,
    get_ocr_languages,
    load_config,
    validate_config,
)


def test_defaults_has_required_sections():
    for key in ("paths", "file_types", "ocr", "document_types", "known_customers", "countries"):
        assert key in _DEFAULTS


def test_apply_defaults_fills_missing():
    cfg = {"paths": {"inbox": "/tmp/inbox"}}
    out = _apply_defaults(cfg)
    assert "file_types" in out
    assert "ocr" in out


def test_validate_config_warns_on_empty_doctypes():
    cfg = {"paths": {"inbox": "/x", "archive": "/y", "logs": "/z"},
           "document_types": {}, "ocr": {"dpi": 200}}
    warnings = validate_config(cfg)
    assert any("Dokumentenart" in w for w in warnings)


def test_load_config_from_file(tmp_path: Path):
    cfg_file = tmp_path / "cfg.yaml"
    cfg_file.write_text(yaml.safe_dump({
        "paths": {"inbox": str(tmp_path / "in"), "archive": str(tmp_path / "out"),
                   "logs": str(tmp_path / "logs"), "review": str(tmp_path / "rev")},
        "file_types": [".pdf"],
        "document_types": {},
    }), encoding="utf-8")
    cfg = load_config(cfg_file)
    assert ".pdf" in cfg["file_types"]


def test_get_document_type_keywords_merges_languages(sample_cfg):
    kws = get_document_type_keywords(sample_cfg)
    assert "rechnung" in kws
    # DE + EN + SQ sollten alle zusammengefuehrt sein
    assert "rechnung" in kws["rechnung"]
    assert "invoice" in kws["rechnung"]


def test_get_known_customers(sample_cfg):
    cs = get_known_customers(sample_cfg)
    assert len(cs) == 2
    assert cs[0]["name"] == "GASAG"


def test_get_country_keywords(sample_cfg):
    ck = get_country_keywords(sample_cfg)
    assert "deutschland" in ck
    assert "berlin" in ck["deutschland"]


def test_get_file_types_returns_set(sample_cfg):
    ft = get_file_types(sample_cfg)
    assert ".pdf" in ft
    assert ".docx" in ft


def test_get_ocr_languages_default(sample_cfg):
    assert "deu" in get_ocr_languages(sample_cfg) or "eng" in get_ocr_languages(sample_cfg)
