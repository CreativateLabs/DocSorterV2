#!/usr/bin/env python3
"""Pre-Build-Validierung: stellt sicher dass KEINE Nutzerdaten im Bundle landen.

Unterscheidet zwischen:
  ❌ FEHLER  — Datei würde tatsächlich im Bundle landen (blockiert Build)
  ⚠  WARNUNG — Datei existiert lokal, ist aber nicht gebundelt (ok für Dev)

Wird automatisch von build_mac.sh und build_win.ps1 aufgerufen.
Auf dem Build-Server (CI/CD) existieren diese Dateien nicht → Check läuft grün.

Verwendung:
    python pre_build_check.py           # Build-Server oder CI
    python pre_build_check.py --dev     # Entwickler-Rechner (Warnungen erlaubt)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEV_MODE = "--dev" in sys.argv  # Entwickler-Modus: Warnungen blockieren nicht

# ── Dateien die NIE im Bundle sein dürfen (spec-seitig ausgeschlossen) ──
# Diese werden in extra_datas in docsorter.spec NICHT aufgeführt.
# Sie dürfen auf dem Entwickler-Rechner existieren (für lokale Entwicklung),
# aber auf dem Build-Server (CI/CD fresh clone) sollten sie nicht da sein.
DEV_ONLY_FILES = {
    "_state.json":         "Benutzerkonten + Passwort-Hashes",
    "_feed.json":          "Persönliche Feed-Daten",
    "_assistant.json":     "Chat-Verlauf",
    "user_profile.json":   "Benutzer-Profil",
    "training_data.json":  "ML-Trainingsdaten (nutzerspezifisch)",
    ".env":                "Secrets und API-Keys",
    ".env.local":          "Lokale Secrets",
    ".env.production":     "Produktions-Secrets",
}

# ── Konfigurationsmuster die NIEMALS in gebundelten Dateien erlaubt sind ──
SENSITIVE_PATTERNS = {
    "/Users/":              "macOS absolute Nutzerpfade",
    "C:\\Users\\":          "Windows absolute Nutzerpfade",
    "C:/Users/":            "Windows absolute Nutzerpfade",
    "supabase.co":          "Persönliche Supabase-URL",
}

errors:   list[str] = []
warnings: list[str] = []

print("🔍 Pre-Build-Check: Nutzerdaten-Scan")
if DEV_MODE:
    print("   (--dev Modus: Warnungen blockieren den Build nicht)\n")
else:
    print()

# ════════════════════════════════════════════════════════════════════════
# 1. config.default.yaml — MUSS vorhanden und sauber sein (wird gebundelt)
# ════════════════════════════════════════════════════════════════════════
default_cfg = ROOT / "config.default.yaml"
if not default_cfg.exists():
    errors.append(
        "❌ config.default.yaml fehlt!\n"
        "   Diese Datei ist die saubere Vorlage für neue Installationen.\n"
        "   Erstelle sie mit: cp config.yaml config.default.yaml und bereinige sie."
    )
else:
    content = default_cfg.read_text(encoding="utf-8", errors="replace")
    bad = {k: v for k, v in SENSITIVE_PATTERNS.items() if k in content}
    if bad:
        errors.append(
            f"❌ config.default.yaml enthält Nutzerdaten:\n"
            + "\n".join(f"     · {v} ({k!r})" for k, v in bad.items()) + "\n"
            "   Diese Datei wird gebundelt → NUR generische Pfade wie ~/Documents/ erlaubt!"
        )
    else:
        print("✓ config.default.yaml      sauber — keine Nutzerdaten")

# ════════════════════════════════════════════════════════════════════════
# 2. config.yaml — DARF NICHT gebundelt werden (ist in .gitignore)
#    Auf Dev-Rechner erlaubt, auf CI-Server: Fehler
# ════════════════════════════════════════════════════════════════════════
cfg_yaml = ROOT / "config.yaml"
if cfg_yaml.exists():
    content = cfg_yaml.read_text(encoding="utf-8", errors="replace")
    bad = {k: v for k, v in SENSITIVE_PATTERNS.items() if k in content}

    # API-Keys und Secrets prüfen
    for line in content.splitlines():
        stripped = line.strip()
        if "secret:" in stripped or "api_key:" in stripped or "anon_key:" in stripped:
            val = stripped.split(":", 1)[-1].strip().strip("'\"")
            if val and val not in ("", "''", '""', "false", "true"):
                bad["secret/api_key"] = "API-Key oder Secret-Wert"
                break

    if bad:
        msg = (
            f"{'⚠ ' if DEV_MODE else '❌'} config.yaml enthält Nutzerdaten:\n"
            + "\n".join(f"     · {v}" for v in bad.values()) + "\n"
            "   config.yaml wird NICHT gebundelt (nur config.default.yaml).\n"
            "   Auf dem Build-Server sollte diese Datei nicht existieren."
        )
        if DEV_MODE:
            warnings.append(msg)
        else:
            errors.append(msg)
    else:
        print("⚠  config.yaml             existiert (wird nicht gebundelt — ok)")

# ════════════════════════════════════════════════════════════════════════
# 3. Nutzerdaten-Dateien — auf Dev-Rechner ok, auf CI-Server: Fehler
# ════════════════════════════════════════════════════════════════════════
for fname, desc in DEV_ONLY_FILES.items():
    path = ROOT / fname
    if path.exists():
        msg = (
            f"{'⚠ ' if DEV_MODE else '❌'} {fname:<25} existiert ({desc})\n"
            f"   {'Wird nicht gebundelt — ok für lokale Entwicklung.' if DEV_MODE else 'Auf dem Build-Server darf diese Datei nicht existieren.'}"
        )
        if DEV_MODE:
            warnings.append(msg)
        else:
            errors.append(msg)

# ════════════════════════════════════════════════════════════════════════
# 4. docsorter.spec: prüfen ob versehentlich Nutzerdateien aufgeführt
# ════════════════════════════════════════════════════════════════════════
spec_file = ROOT / "docsorter.spec"
if spec_file.exists():
    spec_content = spec_file.read_text(encoding="utf-8")
    spec_forbidden = []
    for fname in list(DEV_ONLY_FILES.keys()) + ["config.yaml"]:
        # Suche nach dem Dateinamen in extra_datas (nicht in Kommentaren)
        for line in spec_content.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("#"):
                continue
            if fname in line_stripped and "datas" in spec_content[:spec_content.find(line_stripped)]:
                spec_forbidden.append(fname)
                break
    if spec_forbidden:
        errors.append(
            f"❌ docsorter.spec enthält verbotene Dateien in extra_datas:\n"
            + "\n".join(f"   · {f}" for f in spec_forbidden) + "\n"
            "   Entferne diese Einträge aus extra_datas in docsorter.spec!"
        )
    else:
        print("✓ docsorter.spec           keine Nutzerdateien in extra_datas")

# ════════════════════════════════════════════════════════════════════════
# Ergebnis
# ════════════════════════════════════════════════════════════════════════
print()

if warnings:
    for w in warnings:
        print(w)
    print()

if errors:
    print("═" * 60)
    print("BUILD ABGEBROCHEN — Nutzerdaten im Bundle!\n")
    for e in errors:
        print(e)
        print()
    print("═" * 60)
    print("\nSo beheben:")
    if not DEV_MODE:
        print("  → Auf Build-Server: Diese Dateien sollten nach 'git clone' nicht existieren.")
        print("  → Füge fehlende Einträge zu .gitignore hinzu.")
    print("  → Stelle sicher dass config.default.yaml sauber ist (keine absoluten Pfade).")
    print("  → Für lokalen Test: python pre_build_check.py --dev")
    sys.exit(1)

if warnings and not DEV_MODE:
    # Sollte nicht erreicht werden, aber Sicherheitsnetz
    sys.exit(1)

print("✅ Pre-Build-Check bestanden — Build kann gestartet werden.")
sys.exit(0)
