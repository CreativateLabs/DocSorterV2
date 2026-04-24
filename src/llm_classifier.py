"""LLM-basierte Dokumenten-Klassifikation.

Nutzt OpenAI oder Anthropic API fuer intelligente Klassifikation,
wenn die keyword-basierte Erkennung unsicher ist.

Features:
- Fallback: Nur bei unsicheren Ergebnissen oder auf Wunsch
- Provider: OpenAI (GPT-4o-mini) oder Anthropic (Claude Haiku)
- Caching: Ergebnisse werden in _llm_cache.json gespeichert
- Batch-faehig: Mehrere Dokumente auf einmal
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    """Ergebnis einer LLM-Klassifikation."""
    dokumentenart: str = "unbekannt"
    kunde: str = "unbekannt"
    land: str = "unbekannt"
    datum: str = ""
    zusammenfassung: str = ""
    confidence: float = 0.0
    provider: str = ""
    model: str = ""
    cached: bool = False
    # Lern-System: True wenn LLM einen Dokumententyp vorschlaegt,
    # der noch nicht in der Config existiert → Review-Seite zeigt "Neu anlegen"-Angebot
    is_new_type: bool = False


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
class LLMCache:
    """Einfacher dateisystem-basierter Cache fuer LLM-Ergebnisse."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_file = cache_dir / "_llm_cache.json"
        self._cache: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        content = json.dumps(self._cache, ensure_ascii=False, indent=2)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=self.cache_dir, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, self.cache_file)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def get(self, text_hash: str) -> dict | None:
        return self._cache.get(text_hash)

    def put(self, text_hash: str, result: dict) -> None:
        self._cache[text_hash] = result
        self._save()

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text[:5000].encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------
def _build_prompt(
    text: str,
    document_types: list[str],
    known_customers: list[str],
    countries: list[str],
    global_keywords: list[str] | None = None,
) -> str:
    """System-Prompt fuer LLM-Klassifikation bauen."""
    kw_hint = ""
    if global_keywords:
        kw_hint = (
            f"\n\nWichtige Hinweis-Schlagworte des Benutzers (erhoehen Konfidenz wenn vorhanden): "
            f"{', '.join(global_keywords[:40])}"
        )
    return f"""Du bist ein Dokumenten-Klassifikations-Assistent.
Analysiere den folgenden Dokumenttext und extrahiere diese Informationen:

1. **dokumentenart**: Eine der folgenden Kategorien: {', '.join(document_types)} oder "unbekannt"
2. **kunde**: Der Absender, Kunde oder Vertragspartner. Bekannte Kunden: {', '.join(known_customers)}. Oder "unbekannt".
3. **land**: Das Land aus dem das Dokument stammt. Bekannte Laender: {', '.join(countries)}. Oder "unbekannt".
4. **datum**: Das Hauptdatum des Dokuments im Format DD.MM.YYYY (z.B. Rechnungsdatum, Vertragsdatum).
5. **zusammenfassung**: Eine kurze Zusammenfassung in 1-2 Saetzen (deutsch).
6. **confidence**: Wie sicher bist du dir bei der Klassifikation? (0.0 bis 1.0){kw_hint}

Antworte NUR mit einem JSON-Objekt, ohne Markdown-Formatierung oder Code-Bloecke:

{{"dokumentenart": "...", "kunde": "...", "land": "...", "datum": "DD.MM.YYYY", "zusammenfassung": "...", "confidence": 0.95}}

Dokumenttext (gekuerzt auf max 3000 Zeichen):
---
{text[:3000]}
---"""


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------
def _classify_openai(prompt: str, model: str = "gpt-4o-mini") -> dict[str, Any]:
    """Klassifikation via OpenAI API."""
    try:
        import openai
    except ImportError:
        raise ImportError(
            "OpenAI nicht installiert. Installation: pip install openai"
        )

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY nicht gesetzt. "
            "Setze: export OPENAI_API_KEY=sk-..."
        )

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Du bist ein praeziser Dokumenten-Klassifikations-Assistent. Antworte nur mit JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=500,
    )

    content = response.choices[0].message.content.strip()
    # JSON aus der Antwort extrahieren
    return _parse_json_response(content)


# ---------------------------------------------------------------------------
# Anthropic Provider
# ---------------------------------------------------------------------------
def _classify_anthropic(prompt: str, model: str = "claude-haiku-4-20250414") -> dict[str, Any]:
    """Klassifikation via Anthropic API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "Anthropic nicht installiert. Installation: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY nicht gesetzt. "
            "Setze: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
        system="Du bist ein praeziser Dokumenten-Klassifikations-Assistent. Antworte nur mit JSON.",
    )

    content = response.content[0].text.strip()
    return _parse_json_response(content)


# ---------------------------------------------------------------------------
# Ollama Provider (lokal)
# ---------------------------------------------------------------------------
def _classify_ollama(prompt: str, model: str = "llama3.2", host: str = "http://localhost:11434") -> dict[str, Any]:
    """Klassifikation via Ollama (lokales LLM, kein API-Key noetig)."""
    import httpx

    url = f"{host.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Du bist ein praeziser Dokumenten-Klassifikations-Assistent. Antworte nur mit JSON, ohne Erklaerungen."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
    }
    resp = httpx.post(url, json=payload, timeout=90)
    resp.raise_for_status()
    content = resp.json().get("message", {}).get("content", "").strip()
    return _parse_json_response(content)


def get_ollama_models(host: str = "http://localhost:11434") -> list[str]:
    """Verfuegbare Ollama-Modelle abrufen."""
    try:
        import httpx
        resp = httpx.get(f"{host.rstrip('/')}/api/tags", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [m["name"] for m in models]
    except Exception:
        return []


def is_ollama_running(host: str = "http://localhost:11434") -> bool:
    """Pruefen ob Ollama laeuft."""
    try:
        import httpx
        resp = httpx.get(f"{host.rstrip('/')}/api/version", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JSON Parser (robust)
# ---------------------------------------------------------------------------
def _parse_json_response(content: str) -> dict[str, Any]:
    """JSON aus LLM-Antwort extrahieren (robust gegen Markdown-Wrapper)."""
    # Direkt als JSON versuchen
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Markdown Code-Block entfernen
    if "```" in content:
        lines = content.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block or (not in_block and line.strip().startswith("{")):
                json_lines.append(line)
        try:
            return json.loads("\n".join(json_lines))
        except json.JSONDecodeError:
            pass

    # Letzter Versuch: erstes { bis letztes } extrahieren
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("LLM-Antwort konnte nicht als JSON geparsed werden: %s", content[:200])
    return {}


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
def _safe_float(value: Any, default: float = 0.0) -> float:
    """Konvertiert einen LLM-Wert sicher zu float — kein TypeError/ValueError."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Haupt-Funktion
# ---------------------------------------------------------------------------
def classify_with_llm(
    text: str,
    cfg: dict[str, Any],
    provider: str = "openai",
    model: str | None = None,
    use_cache: bool = True,
) -> LLMResult:
    """Dokument mit LLM klassifizieren.

    Args:
        text: Extrahierter Dokumenttext
        cfg: Config-Dict mit document_types, known_customers, countries
        provider: "openai" oder "anthropic"
        model: Optionales spezifisches Modell
        use_cache: Ergebnis cachen (default: True)

    Returns:
        LLMResult mit Klassifikation
    """
    # Verfuegbare Optionen aus Config
    doc_types = list(cfg.get("document_types", {}).keys())
    customers = [
        c["name"] if isinstance(c, dict) else str(c)
        for c in cfg.get("known_customers", [])
    ]
    countries = list(cfg.get("countries", {}).keys())

    if not doc_types:
        doc_types = ["rechnung", "vertrag", "angebot", "mahnung", "brief"]

    # Cache pruefen
    archive = Path(cfg.get("paths", {}).get("archive", "~/Documents/DocSorter/output")).expanduser()
    cache = LLMCache(archive)
    text_hash = LLMCache.hash_text(text)

    if use_cache:
        cached = cache.get(text_hash)
        if cached:
            logger.info("LLM-Ergebnis aus Cache geladen (Hash: %s)", text_hash)
            return LLMResult(
                dokumentenart=cached.get("dokumentenart", "unbekannt"),
                kunde=cached.get("kunde", "unbekannt"),
                land=cached.get("land", "unbekannt"),
                datum=cached.get("datum", ""),
                zusammenfassung=cached.get("zusammenfassung", ""),
                confidence=cached.get("confidence", 0.0),
                provider=cached.get("provider", ""),
                model=cached.get("model", ""),
                cached=True,
                is_new_type=cached.get("is_new_type", False),
            )

    # Globale Schlagworte aus dem Gehirn laden
    try:
        from .user_profile import get_global_keywords
        _global_kws = get_global_keywords()
    except Exception:
        _global_kws = cfg.get("global_keywords", [])

    # Prompt bauen
    prompt = _build_prompt(text, doc_types, customers, countries, _global_kws)

    # Provider-spezifische Klassifikation
    default_models = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-haiku-4-20250414",
        "ollama": "llama3.2",
    }
    model = model or default_models.get(provider, "gpt-4o-mini")

    try:
        if provider == "openai":
            result_data = _classify_openai(prompt, model)
        elif provider == "anthropic":
            result_data = _classify_anthropic(prompt, model)
        elif provider == "ollama":
            ollama_host = cfg.get("llm", {}).get("ollama_host", "http://localhost:11434")
            result_data = _classify_ollama(prompt, model, ollama_host)
        else:
            raise ValueError(f"Unbekannter Provider: {provider}. Verwende 'openai', 'anthropic' oder 'ollama'.")
    except ImportError as e:
        logger.error("LLM-Provider nicht verfuegbar: %s", e)
        return LLMResult(zusammenfassung=str(e))
    except ValueError as e:
        logger.error("LLM-Konfigurationsfehler: %s", e)
        return LLMResult(zusammenfassung=str(e))
    except Exception as e:
        logger.error("LLM-Klassifikation fehlgeschlagen: %s", e)
        return LLMResult(zusammenfassung=f"Fehler: {e}")

    if not result_data:
        return LLMResult(zusammenfassung="LLM-Antwort konnte nicht geparsed werden")

    # Ergebnis erstellen
    suggested_type = result_data.get("dokumentenart", "unbekannt")
    # Erkennen ob LLM eine Dokumentenart vorschlaegt die noch nicht in der Config existiert
    is_new = (
        suggested_type not in ("unbekannt", "")
        and suggested_type not in doc_types
    )
    llm_result = LLMResult(
        dokumentenart=suggested_type,
        kunde=result_data.get("kunde", "unbekannt"),
        land=result_data.get("land", "unbekannt"),
        datum=result_data.get("datum", ""),
        zusammenfassung=result_data.get("zusammenfassung", ""),
        confidence=_safe_float(result_data.get("confidence", 0.0)),
        provider=provider,
        model=model,
        is_new_type=is_new,
    )

    if is_new:
        logger.info(
            "LLM schlaegt neue Dokumentenart vor (nicht in Config): '%s'",
            suggested_type,
        )

    # Cache speichern
    if use_cache:
        cache_entry = {
            "dokumentenart": llm_result.dokumentenart,
            "kunde": llm_result.kunde,
            "land": llm_result.land,
            "datum": llm_result.datum,
            "zusammenfassung": llm_result.zusammenfassung,
            "confidence": llm_result.confidence,
            "provider": provider,
            "model": model,
            "is_new_type": is_new,
        }
        cache.put(text_hash, cache_entry)

    logger.info(
        "LLM-Klassifikation (%s/%s): art=%s kunde=%s confidence=%.2f",
        provider, model,
        llm_result.dokumentenart, llm_result.kunde, llm_result.confidence,
    )

    return llm_result


def is_llm_available(provider: str = "openai") -> bool:
    """Pruefen ob ein LLM-Provider konfiguriert und verfuegbar ist."""
    if provider == "openai":
        try:
            import openai  # noqa: F401
            return bool(os.environ.get("OPENAI_API_KEY"))
        except ImportError:
            return False
    elif provider == "anthropic":
        try:
            import anthropic  # noqa: F401
            return bool(os.environ.get("ANTHROPIC_API_KEY"))
        except ImportError:
            return False
    elif provider == "ollama":
        return is_ollama_running()
    return False


def get_available_providers() -> list[dict[str, Any]]:
    """Alle verfuegbaren LLM-Provider ermitteln."""
    providers = []
    for name, env_key, pip_pkg in [
        ("openai", "OPENAI_API_KEY", "openai"),
        ("anthropic", "ANTHROPIC_API_KEY", "anthropic"),
    ]:
        try:
            __import__(pip_pkg)
            installed = True
        except ImportError:
            installed = False

        providers.append({
            "name": name,
            "installed": installed,
            "configured": bool(os.environ.get(env_key)),
            "ready": installed and bool(os.environ.get(env_key)),
            "env_key": env_key,
            "pip_install": f"pip install {pip_pkg}",
        })

    # Ollama (lokal)
    ollama_host = "http://localhost:11434"
    running = is_ollama_running(ollama_host)
    models = get_ollama_models(ollama_host) if running else []
    providers.append({
        "name": "ollama",
        "installed": True,
        "configured": running,
        "ready": running,
        "env_key": None,
        "pip_install": "https://ollama.com",
        "models": models,
        "host": ollama_host,
    })

    return providers
