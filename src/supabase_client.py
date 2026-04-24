"""Supabase REST-Client fuer Doc-Sorter.

Speichert ausschliesslich E-Mail-Adressen und Benutzernamen auf dem
Firmen-Server (Supabase). Dokumente und Passwoerter verbleiben lokal.

Konfiguration:
  Entweder Umgebungsvariablen setzen:
    SUPABASE_URL      = https://yuevdwoczyaqondtgmdd.supabase.co
    SUPABASE_ANON_KEY = <anon-key aus dem Supabase-Dashboard>

  Oder in config.yaml ergaenzen:
    supabase:
      url: https://yuevdwoczyaqondtgmdd.supabase.co
      anon_key: <anon-key>

SQL fuer Supabase (einmalig im SQL-Editor ausfuehren):
  CREATE TABLE IF NOT EXISTS user_profiles (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email      text UNIQUE NOT NULL,
    username   text NOT NULL,
    created_at timestamptz DEFAULT now()
  );
  ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
  CREATE POLICY "Anon insert" ON user_profiles
    FOR INSERT TO anon WITH CHECK (true);
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SUPABASE_URL = "https://yuevdwoczyaqondtgmdd.supabase.co"
_TABLE = "user_profiles"


def _load_dotenv() -> None:
    """Lädt .env Datei neben config.yaml wenn vorhanden (nur einmal)."""
    try:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception:
        pass


_dotenv_loaded = False


def _get_credentials() -> tuple[str, str]:
    """URL + Anon-Key laden (ENV > .env > config.yaml)."""
    global _dotenv_loaded
    if not _dotenv_loaded:
        _load_dotenv()
        _dotenv_loaded = True

    url = os.environ.get("SUPABASE_URL", _SUPABASE_URL)
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not anon_key:
        try:
            import yaml
            cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
            if cfg_path.exists():
                with open(cfg_path, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                anon_key = cfg.get("supabase", {}).get("anon_key", "")
                url = cfg.get("supabase", {}).get("url", url)
        except Exception:
            pass

    return url, anon_key


async def register_email(email: str, username: str) -> dict[str, Any]:
    """E-Mail + Benutzername in Supabase speichern (upsert).

    Gibt das Ergebnis-Dict zurueck oder {} bei Fehler.
    """
    url, anon_key = _get_credentials()
    if not anon_key:
        logger.warning(
            "Supabase anon_key nicht konfiguriert – E-Mail wird nicht synchronisiert. "
            "Setze SUPABASE_ANON_KEY oder trage ihn in config.yaml ein."
        )
        return {}

    try:
        import httpx
        endpoint = f"{url}/rest/v1/{_TABLE}"
        headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
        payload = {"email": email, "username": username}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            logger.info("E-Mail '%s' erfolgreich in Supabase gespeichert.", email)
            return {"ok": True}
    except Exception as exc:
        logger.warning("Supabase-Sync fehlgeschlagen: %s", exc)
        return {}


async def lookup_email(email: str) -> dict[str, Any] | None:
    """Profil anhand der E-Mail-Adresse nachschlagen.

    Gibt {'email': ..., 'username': ...} zurueck oder None.
    """
    url, anon_key = _get_credentials()
    if not anon_key:
        return None

    try:
        import httpx
        endpoint = f"{url}/rest/v1/{_TABLE}"
        headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
        }
        params = {
            "email": f"eq.{email}",
            "select": "email,username",
            "limit": "1",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(endpoint, headers=headers, params=params)
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if rows else None
    except Exception as exc:
        logger.warning("Supabase-Lookup fehlgeschlagen: %s", exc)
        return None
