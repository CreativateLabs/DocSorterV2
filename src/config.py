"""Konfiguration aus config.yaml laden, validieren und bereitstellen."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

def _resolve_default_config_path() -> Path:
    """Config-Pfad auflösen: im Frozen-Modus AppData, sonst Projektverzeichnis."""
    try:
        from .app_paths import get_config_path, is_frozen
        if is_frozen():
            return get_config_path()   # ~/Library/Application Support/DocSorter/config.yaml
    except Exception:
        pass
    return Path(__file__).resolve().parent.parent / "config.yaml"  # Dev-Modus


def _bootstrap_config_if_missing(config_path: Path) -> None:
    """Erzeugt config.yaml aus config.default.yaml wenn sie fehlt.

    Erleichtert Fresh-Clone-Setup (Dev- und First-Run-Fall). Still falls die
    Default-Vorlage nicht existiert — dann greift der normale Not-Found-Fehler.
    """
    if config_path.exists():
        return
    default_path = config_path.parent / "config.default.yaml"
    if not default_path.exists():
        return
    try:
        import shutil
        config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(default_path, config_path)
        logger.info("config.yaml aus config.default.yaml erzeugt: %s", config_path)
    except OSError as exc:
        logger.warning("Konnte config.yaml nicht bootstrapen: %s", exc)


DEFAULT_CONFIG_PATH = _resolve_default_config_path()
_bootstrap_config_if_missing(DEFAULT_CONFIG_PATH)

# Pflicht-Sektionen und ihre Defaults
_DEFAULTS: dict[str, Any] = {
    "paths": {
        "inbox": "~/Documents/DocSorter/input",
        "archive": "~/Documents/DocSorter/output",
        "logs": "~/Documents/DocSorter/logs",
        "review": "~/Documents/DocSorter/output/_review",
    },
    "file_types": [".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".tif", ".tiff"],
    "ocr": {"languages": "eng+deu+sqi", "dpi": 200, "max_pages": 5},
    "document_types": {},
    "known_customers": [],
    "countries": {},
    "confidence": {"min_text_length": 30, "uncertain_if_missing": ["kunde", "dokumentenart"]},
    "processing": {"max_files_per_run": 100, "dry_run_default": True},
    "taxonomy": {
        "filename_pattern": "{dokumentenart}_{kunde}_{land}_{datum}",
        "folder_pattern": "{dokumentenart}/{land}/{kunde}/{jahr}",
    },
    "llm": {
        "enabled": False,
        "provider": "ollama",
        "model": "",
        "ollama_host": "http://localhost:11434",
        "ollama_model": "llama3.2",
        "fallback_only": True,
        "cache_results": True,
    },
    "email_accounts": [],
    "calendar_paths": [],
    "email_webhook": {
        "enabled": True,
        "provider": "generic",
        "secret": "",
        "public_url": "",
        "mailgun_api_key": "",
    },
    "messenger_webhook": {
        "enabled": True,
        "secret": "",
        "whatsapp_verify_token": "",
        "public_url": "",
    },
    "watcher": {
        "enabled": False,
        "poll_interval": 5.0,
        "debounce_seconds": 2.0,
        "auto_process": True,
    },
    "feed": {
        "max_entries": 500,
    },
}

# Environment-Variable Mapping: ENV_NAME -> config path
_ENV_OVERRIDES = {
    "DOCSORTER_INBOX": ("paths", "inbox"),
    "DOCSORTER_ARCHIVE": ("paths", "archive"),
    "DOCSORTER_LOGS": ("paths", "logs"),
    "DOCSORTER_DRY_RUN": ("processing", "dry_run_default"),
    "DOCSORTER_MAX_FILES": ("processing", "max_files_per_run"),
    "DOCSORTER_OCR_LANG": ("ocr", "languages"),
}


def _apply_defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    """Fehlende Sektionen mit Defaults auffuellen."""
    for key, default in _DEFAULTS.items():
        if key not in cfg:
            logger.debug("Config-Sektion '%s' fehlt, verwende Default", key)
            cfg[key] = default
        elif isinstance(default, dict) and isinstance(cfg[key], dict):
            for sub_key, sub_default in default.items():
                if sub_key not in cfg[key]:
                    cfg[key][sub_key] = sub_default
    return cfg


def _apply_env_overrides(cfg: dict[str, Any]) -> dict[str, Any]:
    """Environment-Variablen anwenden (ueberschreiben Config-Werte)."""
    for env_name, (section, key) in _ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if value is not None:
            # Typ-Konvertierung
            if key == "dry_run_default":
                cfg.setdefault(section, {})[key] = value.lower() in ("true", "1", "yes")
            elif key == "max_files_per_run":
                try:
                    cfg.setdefault(section, {})[key] = int(value)
                except ValueError:
                    logger.warning("Ungueltige ENV %s=%s (erwartet: Zahl)", env_name, value)
            else:
                cfg.setdefault(section, {})[key] = value
            logger.info("Config-Override via ENV: %s -> %s.%s", env_name, section, key)
    return cfg


def validate_config(cfg: dict[str, Any]) -> list[str]:
    """Config validieren. Gibt Liste von Warnungen zurueck."""
    warnings: list[str] = []

    # Pfade pruefen
    for key in ["inbox", "archive", "logs"]:
        path_str = cfg.get("paths", {}).get(key, "")
        if not path_str:
            warnings.append(f"Pfad '{key}' ist leer")

    # Dokumentenarten pruefen
    if not cfg.get("document_types"):
        warnings.append("Keine Dokumentenarten definiert -- Klassifikation wird immer 'unbekannt' sein")

    # OCR pruefen
    ocr = cfg.get("ocr", {})
    dpi = ocr.get("dpi", 200)
    if not isinstance(dpi, (int, float)) or dpi < 72 or dpi > 600:
        warnings.append(f"OCR DPI unplausibel: {dpi} (erwartet: 72-600)")

    return warnings


def load_config(path: Path | None = None) -> dict[str, Any]:
    """YAML-Konfiguration laden, validieren und Pfade expandieren."""
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config nicht gefunden: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Defaults anwenden
    cfg = _apply_defaults(cfg)

    # Env-Overrides anwenden
    cfg = _apply_env_overrides(cfg)

    # Pfade expandieren (~, env vars)
    for key in cfg.get("paths", {}):
        cfg["paths"][key] = str(Path(cfg["paths"][key]).expanduser())

    # Validierung (nur Warnungen, kein Abbruch)
    warnings = validate_config(cfg)
    for w in warnings:
        logger.warning("Config: %s", w)

    return cfg


def load_config_raw(path: Path | None = None) -> dict[str, Any]:
    """YAML-Konfiguration laden OHNE Pfad-Expansion.

    Fuer die Dashboard-Config-Bearbeitung: Pfade bleiben mit ~ erhalten,
    damit save_config() sie nicht zu absoluten Pfaden konvertiert.
    """
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"Config nicht gefunden: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return _apply_defaults(cfg)


def save_config(cfg_raw: dict[str, Any], path: Path | None = None) -> None:
    """Config-Dict zurueck in die YAML-Datei schreiben (atomic).

    cfg_raw sollte die nicht-expandierten Pfade enthalten (mit ~).
    Schreibt atomar via tempfile + os.replace() um Datenverlust bei
    Prozessabbruch waehrend des Schreibens zu verhindern.
    """
    config_path = path or DEFAULT_CONFIG_PATH
    content = yaml.dump(
        cfg_raw,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    tmp_fd, tmp_path = tempfile.mkstemp(dir=config_path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, config_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    logger.info("Config gespeichert: %s", config_path)


def get_file_types(cfg: dict[str, Any]) -> set[str]:
    """Unterstuetzte Dateiendungen als Set."""
    return set(cfg.get("file_types", [".pdf"]))


def get_ocr_languages(cfg: dict[str, Any]) -> str:
    """OCR-Sprachen als Tesseract-String."""
    return cfg.get("ocr", {}).get("languages", "eng+deu+sqi")


def get_document_type_keywords(cfg: dict[str, Any]) -> dict[str, list[str]]:
    """Alle Keywords pro Dokumentenart zusammenfuehren (alle Sprachen)."""
    result: dict[str, list[str]] = {}
    for doc_type, lang_keywords in cfg.get("document_types", {}).items():
        all_keywords: list[str] = []
        for lang_key, keywords in lang_keywords.items():
            if isinstance(keywords, list):
                all_keywords.extend(keywords)
        result[doc_type] = all_keywords
    return result


def get_known_customers(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Kundenliste mit Name und Aliases."""
    return cfg.get("known_customers", [])


def get_country_keywords(cfg: dict[str, Any]) -> dict[str, list[str]]:
    """Laender mit ihren Erkennungs-Keywords."""
    result: dict[str, list[str]] = {}
    for country, data in cfg.get("countries", {}).items():
        result[country] = data.get("keywords", [])
    return result
