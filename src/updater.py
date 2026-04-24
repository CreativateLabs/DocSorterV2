"""Auto-Updater: Prüft auf neue Versionen und installiert sie direkt.

Ablauf (In-App Update):
    1. check_for_update()   — Version via Netlify version.json prüfen
    2. download_update()    — Installer mit Fortschrittsanzeige laden
    3. prepare_install()    — Installer starten, dann App beenden
       macOS:   DMG mounten → neue .app kopieren → Swap-Script → App.shutdown()
       Windows: Inno-Setup /VERYSILENT /CLOSEAPPLICATIONS → App.shutdown()

Fallback (Browser-Download):
    open_download(info)     — Link im Browser öffnen
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Netlify — einzige Quelle der Wahrheit für Versionen + Downloads
VERSION_URL   = "https://doc-sorter-app.netlify.app/version.json"
DOWNLOAD_BASE = "https://doc-sorter-app.netlify.app"

_TIMEOUT_CHECK    = 8    # Sekunden für Update-Check
_TIMEOUT_DOWNLOAD = 600  # Sekunden für Download (10 Min)


# ============================================================================
# Datenklassen
# ============================================================================

@dataclass
class UpdateInfo:
    current_version: str
    latest_version:  str
    has_update:      bool
    download_url:    str   # vollständige URL für dieses Betriebssystem
    release_notes:   str
    checksum:        str = field(default="")  # SHA256 des Installers


# ============================================================================
# Hilfsfunktionen
# ============================================================================

def _parse_version(v: str) -> tuple[int, ...]:
    """'1.2.3' → (1, 2, 3). Ignoriert führendes 'v' und Pre-Release-Suffixe."""
    v = v.lstrip("v").split("-")[0]
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def _pick_download(downloads: dict[str, str]) -> str:
    """Passenden Download-Link für das aktuelle Betriebssystem auswählen."""
    system  = platform.system()
    machine = platform.machine().lower()
    is_arm  = machine in ("arm64", "aarch64")

    if system == "Darwin":
        if is_arm and "mac-arm64" in downloads:
            return DOWNLOAD_BASE + downloads["mac-arm64"]
        if "mac-intel" in downloads:
            return DOWNLOAD_BASE + downloads["mac-intel"]
        for k, v in downloads.items():
            if "mac" in k:
                return DOWNLOAD_BASE + v
    elif system == "Windows":
        if "win" in downloads:
            return DOWNLOAD_BASE + downloads["win"]

    return f"{DOWNLOAD_BASE}/#download"


def _pick_checksum(checksums: dict[str, str]) -> str:
    """SHA256-Prüfsumme passend zur gewählten Plattform auswählen."""
    system  = platform.system()
    machine = platform.machine().lower()
    is_arm  = machine in ("arm64", "aarch64")

    if system == "Darwin":
        if is_arm and "mac-arm64" in checksums:
            return checksums["mac-arm64"]
        if "mac-intel" in checksums:
            return checksums["mac-intel"]
        for k in checksums:
            if "mac" in k:
                return checksums[k]
    elif system == "Windows":
        return checksums.get("win", "")

    return ""


def _get_cache_dir() -> Path:
    """Plattformspezifisches Cache-Verzeichnis für heruntergeladene Updates."""
    system = platform.system()
    if system == "Darwin":
        p = Path.home() / "Library" / "Caches" / "DocSorterV2" / "update"
    elif system == "Windows":
        appdata = os.environ.get("LOCALAPPDATA", str(Path.home()))
        p = Path(appdata) / "DocSorterV2" / "update"
    else:
        p = Path.home() / ".cache" / "docsorterv2" / "update"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _verify_sha256(file_path: Path, expected: str) -> bool:
    """SHA256-Prüfsumme der Datei gegen den erwarteten Wert prüfen."""
    if not expected:
        return True  # Keine Prüfsumme vorhanden → überspringen
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual != expected:
        logger.error("SHA256-Mismatch: erwartet %s, erhalten %s", expected[:16], actual[:16])
        return False
    return True


def _get_current_app_path() -> Path | None:
    """Aktuellen .app-Bundle-Pfad ermitteln (nur macOS, nur frozen)."""
    if not getattr(sys, "frozen", False):
        return None
    # sys.executable = /Applications/DocSorter.app/Contents/MacOS/DocSorter
    exe = Path(sys.executable)
    app_path = exe.parent.parent.parent
    if app_path.suffix == ".app" and app_path.exists():
        return app_path
    return None


# ============================================================================
# Öffentliche API
# ============================================================================

def check_for_update(current_version: str | None = None) -> UpdateInfo | None:
    """Prüft auf neue Version via version.json auf Netlify.

    - Gibt None zurück wenn keine Verbindung möglich (kein Fehler für Nutzer)
    - Gibt UpdateInfo zurück mit has_update=True wenn neuere Version verfügbar
    """
    from .version import __version__
    current = current_version or __version__

    try:
        import httpx
        resp = httpx.get(
            VERSION_URL,
            timeout=_TIMEOUT_CHECK,
            headers={"User-Agent": f"DocSorter/{current}"},
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.debug("Update-Check fehlgeschlagen (kein Netz?): %s", exc)
        return None

    latest = data.get("version", "").lstrip("v")
    if not latest:
        return None

    downloads:  dict[str, str] = data.get("downloads",  {})
    checksums:  dict[str, str] = data.get("checksums",  {})
    notes = data.get("release_notes", "")

    return UpdateInfo(
        current_version=current,
        latest_version=latest,
        has_update=_parse_version(latest) > _parse_version(current),
        download_url=_pick_download(downloads),
        release_notes=notes,
        checksum=_pick_checksum(checksums),
    )


def open_download(info: UpdateInfo) -> None:
    """Fallback: Download-Link im Browser öffnen."""
    import webbrowser
    webbrowser.open(info.download_url)


def download_update(info: UpdateInfo, progress: dict) -> Path | None:
    """Installer herunterladen. Aktualisiert `progress`-Dict laufend.

    progress-Keys:
        bytes  — bereits geladene Bytes
        total  — Gesamtgröße (0 wenn unbekannt)
        done   — True wenn fertig
        error  — Fehlermeldung oder None
        path   — Pfad zur heruntergeladenen Datei (wenn done=True)

    Gibt den Pfad zur Datei zurück, oder None bei Fehler.
    """
    import httpx

    progress.update({"bytes": 0, "total": 0, "done": False, "error": None, "path": None})

    url      = info.download_url
    filename = url.split("/")[-1]
    dest     = _get_cache_dir() / filename

    # Bereits gecachte Datei mit korrekter Prüfsumme? Wiederverwenden.
    if dest.exists() and _verify_sha256(dest, info.checksum):
        logger.info("Gecachte Datei wiederverwendet: %s", dest.name)
        progress.update({"bytes": dest.stat().st_size, "total": dest.stat().st_size, "done": True, "path": str(dest)})
        return dest

    tmp_fd, tmp_path = None, None
    try:
        import httpx
        with httpx.stream(
            "GET", url,
            follow_redirects=True,
            timeout=_TIMEOUT_DOWNLOAD,
            headers={"User-Agent": f"DocSorter/{info.current_version}"},
        ) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            progress["total"] = total

            tmp_fd, tmp_path = tempfile.mkstemp(dir=_get_cache_dir(), suffix=".tmp")
            with os.fdopen(tmp_fd, "wb") as f:
                tmp_fd = None  # fdopen übernimmt
                for chunk in r.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    progress["bytes"] += len(chunk)

            os.replace(tmp_path, dest)
            tmp_path = None

    except Exception as exc:
        logger.error("Download fehlgeschlagen: %s", exc)
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        progress["error"] = str(exc)
        return None

    # Prüfsumme verifizieren
    if not _verify_sha256(dest, info.checksum):
        dest.unlink(missing_ok=True)
        progress["error"] = "Prüfsumme stimmt nicht überein — bitte erneut versuchen"
        return None

    progress.update({"done": True, "path": str(dest)})
    logger.info("Download abgeschlossen: %s (%.1f MB)", dest.name, dest.stat().st_size / 1_000_000)
    return dest


def prepare_install(file_path: str | Path) -> None:
    """Update-Installation vorbereiten (plattformspezifisch).

    Startet den Installer im Hintergrund. Der Aufrufer muss danach
    die App per app.shutdown() beenden.

    macOS:   DMG mounten → .app kopieren → Swap-Script starten
    Windows: Inno-Setup-Installer mit /VERYSILENT starten
    Dev-Mode: RuntimeError (kein Bundle vorhanden)
    """
    p = Path(file_path)
    system = platform.system()

    if system == "Darwin":
        _prepare_install_macos(p)
    elif system == "Windows":
        _prepare_install_windows(p)
    else:
        raise RuntimeError(f"Auto-Update für {system} nicht unterstützt")


# ============================================================================
# Plattform-spezifische Install-Logik
# ============================================================================

def _prepare_install_macos(dmg_path: Path) -> None:
    """macOS: DMG mounten, neue .app kopieren, Swap-Script starten."""
    current_app = _get_current_app_path()
    if current_app is None:
        raise RuntimeError(
            "Auto-Update ist nur in der installierten App verfügbar.\n"
            "Im Entwicklungsmodus bitte manuell updaten."
        )

    install_dir = current_app.parent  # z.B. /Applications
    app_name    = current_app.name    # z.B. DocSorter.app
    temp_new    = install_dir / (app_name + ".new")

    # DMG mounten
    mount_point = Path(tempfile.mkdtemp(prefix="dsupdate-"))
    try:
        subprocess.run(
            ["hdiutil", "attach", str(dmg_path),
             "-mountpoint", str(mount_point),
             "-nobrowse", "-quiet"],
            check=True, timeout=60,
        )

        # .app im DMG suchen
        apps = list(mount_point.glob("*.app"))
        if not apps:
            raise FileNotFoundError("Keine .app-Datei im Update-Paket gefunden")

        # Neue .app kopieren (noch gemountet)
        import shutil
        if temp_new.exists():
            shutil.rmtree(temp_new)
        shutil.copytree(apps[0], temp_new, symlinks=True)

    finally:
        subprocess.run(
            ["hdiutil", "detach", str(mount_point), "-quiet"],
            check=False, timeout=30,
        )
        try:
            mount_point.rmdir()
        except OSError:
            pass

    # Quarantine-Attribut entfernen
    subprocess.run(
        ["xattr", "-dr", "com.apple.quarantine", str(temp_new)],
        check=False, timeout=10,
    )

    # Swap-Script schreiben und starten
    script = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=False, prefix="ds-swap-"
    )
    script.write(f"""#!/bin/bash
# Doc-Sorter Auto-Update Swap-Script — wird nach App-Beenden ausgeführt
sleep 2
rm -rf "{current_app}"
mv "{temp_new}" "{current_app}"
open "{current_app}"
rm -- "$0"
""")
    script.close()
    Path(script.name).chmod(0o755)

    subprocess.Popen(
        ["bash", script.name],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.info("macOS Swap-Script gestartet: %s", script.name)


def _prepare_install_windows(exe_path: Path) -> None:
    """Windows: Inno-Setup-Installer still starten."""
    if not exe_path.exists():
        raise FileNotFoundError(f"Installer nicht gefunden: {exe_path}")

    subprocess.Popen(
        [str(exe_path), "/VERYSILENT", "/NORESTART",
         "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
        start_new_session=True,
    )
    logger.info("Windows Installer gestartet: %s", exe_path.name)
