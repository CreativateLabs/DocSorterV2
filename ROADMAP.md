# Doc-Sorter -- Epic Roadmap

## Gap Analysis Summary

**51 Gaps identifiziert** nach Audit des gesamten Codebasis (CLI + Dashboard).
Stand: MVP funktional, aber nicht produktionsreif.

| Kategorie | Kritisch | Mittel | Klein |
|-----------|----------|--------|-------|
| UX/UI | 7 | 2 | - |
| Funktional | 5 | 4 | 1 |
| Code-Qualitaet | 6 | 4 | 2 |
| Dokumentation | 4 | 3 | - |
| Produktion | 6 | 3 | - |

---

## Epic 1: Foundation (Sprint 1-2)
> **Ziel:** Stabiles Fundament, damit alles andere darauf aufbauen kann.

### 1.1 Projekt-Setup & Hygiene
- [ ] `.gitignore` erstellen (logs, state, __pycache__, .venv, .env)
- [ ] `pyproject.toml` oder `setup.py` fuer sauberes Packaging
- [ ] Version pinning in `requirements.txt` (exakte Versionen)
- [ ] Dependency-Check beim Start (Tesseract installiert? Poppler da?)

### 1.2 Structured Logging
- [ ] Python `logging` statt `print()` ueberall einfuehren
- [ ] Log-Level: ERROR, WARN, INFO, DEBUG
- [ ] Log-Output sowohl Terminal als auch Datei
- [ ] Log-Rotation (max 10 Dateien, je 5MB)
- [ ] Dashboard: Logs lesen und filtern koennen

### 1.3 Error Handling Fix
- [ ] Alle `except Exception: pass` ersetzen durch spezifische Exceptions + Logging
- [ ] reader.py: OCR-Fehler loggen statt verschlucken
- [ ] classifier.py: Sprach-Erkennung Fehler loggen
- [ ] organizer.py: Dateisystem-Fehler abfangen (Permissions, Disk voll)
- [ ] main.py: Graceful exit mit Fehlerbericht

### 1.4 Config Validation
- [ ] Schema-Validierung beim Laden (required keys pruefen)
- [ ] Defaults fuer fehlende Sektionen
- [ ] Pfad-Validierung (existiert? beschreibbar?)
- [ ] Environment-Variable Override (z.B. `DOCSORTER_INBOX`)
- [ ] Dashboard: Validierung vor dem Speichern (rote Felder bei Fehler)

### 1.5 State Management Hardening
- [ ] File-Locking fuer `_state.json` (fcntl/msvcrt)
- [ ] Atomic writes (temp file + rename)
- [ ] State-Backup vor jedem Run
- [ ] State-Recovery wenn korrupt

---

## Epic 2: Dashboard Crisp (Sprint 2-3)
> **Ziel:** Dashboard wird das primaere Interface. Poliert, intuitiv, vollstaendig.

### 2.1 Live Updates & Refresh
- [ ] Overview: Auto-Refresh alle 10s (ui.timer) statt manueller Button
- [ ] Terminal: Buttons disabled waehrend Job laeuft
- [ ] Terminal: "Stop Job" Button (subprocess.kill)
- [ ] Terminal: Fortschrittsanzeige (X von Y Dateien)
- [ ] File Browser: Auto-Refresh nach Job-Ende

### 2.2 Navigation & Layout Polish
- [ ] Aktive Seite in Sidebar hervorheben (current route marker)
- [ ] Breadcrumbs auf jeder Seite
- [ ] Dark Mode Toggle im Header
- [ ] Responsive Design testen und fixen
- [ ] Favicon (Dokument-Icon)
- [ ] Footer mit Version und Status

### 2.3 Config Editor Upgrade
- [ ] Feld-Validierung live (rote Rahmen bei Fehler)
- [ ] Keywords als visuelle Chips statt Komma-Text
- [ ] "Aenderungen verwerfen" Button (Reset auf letzte gespeicherte)
- [ ] Diff-Anzeige vor dem Speichern ("Was hat sich geaendert?")
- [ ] Bestaetigungs-Dialog bei destruktiven Aenderungen (Loeschen)
- [ ] Taxonomy-Vorschau: "So wuerde eine Datei heissen: rechnung_GASAG_deutschland_16.03.26.pdf"

### 2.4 File Browser Upgrade
- [ ] Deep-Navigation im Archiv (Klick in Unterordner)
- [ ] Suche/Filter in Dateilisten
- [ ] "Im Finder oeffnen" Button pro Datei/Ordner
- [ ] Datei-Vorschau (Text-Auszug fuer PDFs/DOCX)
- [ ] Pagination fuer grosse Ordner (>100 Dateien)
- [ ] Drag & Drop: Dateien in Inbox hochladen

### 2.5 Review-Management
- [ ] Review-Dateien mit Klassifikation anzeigen
- [ ] "Manuell klassifizieren" Dialog (Dokumentenart, Kunde, Land waehlen)
- [ ] "In Archiv verschieben" mit korrigierter Klassifikation
- [ ] Bulk-Aktionen (alle markieren, alle verschieben)
- [ ] Review-Statistiken auf Overview-Seite

### 2.6 Dashboard Logs & History
- [ ] Verarbeitungs-Historie Seite (alle bisherigen Runs)
- [ ] Pro Run: Dateien, Ergebnis, Fehler, Dauer
- [ ] Log-Viewer mit Filter (nach Datum, Status, Kunde)
- [ ] Export als CSV/Excel

---

## Epic 3: Onboarding & Client-Setup (Sprint 3-4)
> **Ziel:** Neuer Kunde kann in 15 Minuten produktiv sein.

### 3.1 First-Run Wizard
- [ ] Dashboard erkennt "erste Nutzung" (keine state.json vorhanden)
- [ ] Schritt 1: Willkommen + Erklaerung was Doc-Sorter macht
- [ ] Schritt 2: Pfade konfigurieren (Inbox, Archiv, Logs) mit Ordner-Picker
- [ ] Schritt 3: Erste Kunden anlegen (Name + Aliases)
- [ ] Schritt 4: Dokumentenarten pruefen/anpassen
- [ ] Schritt 5: Test-Datei in Inbox legen und Dry Run starten
- [ ] Schritt 6: Ergebnis pruefen und bestaetigen

### 3.2 Prerequisites Check
- [ ] Beim Start: Python-Version pruefen (>=3.10)
- [ ] Tesseract installiert? Welche Sprachen verfuegbar?
- [ ] Poppler installiert? (fuer PDF-zu-Bild)
- [ ] Disk Space pruefen
- [ ] Dashboard: Status-Seite mit System-Info

### 3.3 Client-spezifische Config Templates
- [ ] "Branchen-Templates" fuer Config:
  - Rechtsanwalt (Vertraege, Schriftsaetze, Gutachten, Korrespondenz)
  - Steuerberater (Rechnungen, Belege, Steuerbescheide, Jahresabschluss)
  - Handwerker (Angebote, Auftraege, Rechnungen, Lieferscheine)
  - Allgemein (Standard wie jetzt)
- [ ] Template-Auswahl im First-Run Wizard
- [ ] "Config exportieren" und "Config importieren" fuer Client-Backup

### 3.4 Dokumentation
- [ ] README komplett ueberarbeiten:
  - Installation Windows/Mac/Linux
  - Troubleshooting-Sektion
  - FAQ
  - Screenshots vom Dashboard
- [ ] In-App Hilfe-Tooltips auf jeder Seite
- [ ] Video/GIF: "Erste Schritte in 5 Minuten"
- [ ] Changelog fuehren

### 3.5 Client Deployment Package
- [ ] Installations-Script (`install.sh` / `install.bat`)
- [ ] Automatisch: venv erstellen, dependencies installieren, Tesseract pruefen
- [ ] Desktop-Shortcut erstellen (Dashboard starten)
- [ ] Auto-Start Option (Dashboard beim Login starten)

---

## Epic 4: Intelligenz & Klassifikation (Sprint 4-6)
> **Ziel:** Bessere Erkennung, weniger Review-Dateien, mehr Automatisierung.

### 4.1 Verbesserte Klassifikation
- [ ] Confidence Score (0.0-1.0) statt binaer unsicher/sicher
- [ ] Gewichtete Keywords (Titel-Keywords > Body-Keywords)
- [ ] Kontext-basierte Erkennung (z.B. "Rechnung" nach "Nr." = staerker)
- [ ] Regex-Patterns fuer Rechnungsnummern, IBAN, Steuernummern
- [ ] Mehrere Treffer bei Dokumentenart: Ranking statt erster Treffer

### 4.2 Kunden-Erkennung verbessern
- [ ] IBAN/Bankdaten als Kunden-Identifier
- [ ] Steuer-ID Matching
- [ ] Adress-Parsing (Strasse, PLZ, Ort)
- [ ] "Neuen Kunden vorschlagen" wenn unbekannt (statt "unbekannt")
- [ ] Dashboard: "Diesen Kunden merken" One-Click im Review

### 4.3 Watch Folder / Auto-Processing
- [ ] Filesystem Watcher (watchdog library)
- [ ] Neue Datei in Inbox -> automatisch verarbeiten
- [ ] Konfigurierbar: Sofort oder gebatchted (alle X Minuten)
- [ ] Dashboard: Watcher Status anzeigen (aktiv/inaktiv)
- [ ] Dashboard: Watcher starten/stoppen

### 4.4 Datum-Erkennung verbessern
- [ ] Monatsname-Parsing ("Januar 2026", "March 15, 2026")
- [ ] Relative Datumsangaben ("letzten Monat")
- [ ] Mehrere Daten pro Dokument: Rechnungsdatum vs. Faelligkeitsdatum
- [ ] Dashboard: Datum manuell korrigieren im Review

### 4.5 OCR Optimierung
- [ ] OCR-Qualitaetsbewertung (Confidence Score pro Seite)
- [ ] Vorverarbeitung: Kontrast erhoehen, Deskew, Denoising
- [ ] Cache: OCR-Ergebnisse cachen (Hash -> Text)
- [ ] Fortschritt: "Seite X von Y wird gelesen"

---

## Epic 5: Analyse & Reporting (Sprint 6-8)
> **Ziel:** Daten nicht nur sortieren, sondern auswerten. Ausbaustufe 2.

### 5.1 Statistik-Dashboard
- [ ] Zeitreihen: Dokumente pro Tag/Woche/Monat (Chart)
- [ ] Verteilung nach Dokumentenart (Pie Chart)
- [ ] Verteilung nach Kunde (Bar Chart)
- [ ] Top-Kunden nach Dokumentenanzahl
- [ ] Trend: Mehr/weniger Rechnungen als Vormonat?

### 5.2 Duplikat-Erkennung
- [ ] Inhaltsbasierter Vergleich (Text-Similarity)
- [ ] Exakte Duplikate (SHA-256 Match)
- [ ] Near-Duplikate (80%+ Text-Uebereinstimmung)
- [ ] Dashboard: Duplikate anzeigen und zusammenfuehren

### 5.3 Volltextsuche
- [ ] SQLite FTS5 Index ueber alle extrahierten Texte
- [ ] Dashboard: Suchfeld "Finde Dokument mit Text..."
- [ ] Ergebnisse mit Highlighting
- [ ] Filter kombinierbar mit Kunde/Typ/Datum

### 5.4 Export & Reporting
- [ ] Monatlicher Report als PDF generieren
- [ ] CSV-Export aller Klassifikationen
- [ ] API-Endpoint fuer externe Systeme
- [ ] Webhook bei neuer Verarbeitung

---

## Epic 6: Produktion & Sicherheit (Sprint 8-10)
> **Ziel:** Enterprise-ready. Sicher, stabil, monitorbar.

### 6.1 Authentifizierung
- [ ] Login-Seite fuer Dashboard (lokaler User/Passwort)
- [ ] Session-Management
- [ ] Audit-Log: Wer hat wann was geaendert

### 6.2 Backup & Recovery
- [ ] Automatische State-Backups (taeglich)
- [ ] Config-Versionierung (Aenderungshistorie)
- [ ] Disaster Recovery: Archiv aus Logs rekonstruieren
- [ ] Export/Import der gesamten Konfiguration

### 6.3 Performance
- [ ] File-Count Caching (nicht bei jedem Seitenaufruf zaehlen)
- [ ] Lazy Loading im Archiv-Browser
- [ ] OCR Worker Pool (parallel verarbeiten)
- [ ] Batch-Progress mit ETA

### 6.4 Monitoring
- [ ] Health-Check Endpoint (`/api/health`)
- [ ] Metriken: Dateien/Stunde, OCR-Dauer, Fehlerrate
- [ ] Alerting bei Fehlern (optional Email/Webhook)
- [ ] Dashboard: System-Status Seite

### 6.5 Tests
- [ ] Unit Tests: classifier.py (alle Erkennungs-Funktionen)
- [ ] Unit Tests: organizer.py (Dateinamen, Ordnerstruktur)
- [ ] Unit Tests: config.py (Laden, Speichern, Validierung)
- [ ] Integration Tests: End-to-End Pipeline
- [ ] Test-Fixtures: Beispiel-PDFs, DOCXs, Bilder
- [ ] CI/CD: Tests bei jedem Commit (GitHub Actions)

---

## Epic 7: Advanced Intelligence (Sprint 10+)
> **Ziel:** Ausbaustufe 3-5 aus dem urspruenglichen Scope.

### 7.1 LLM-Integration (Optional)
- [ ] Lokales LLM fuer Dokumenten-Zusammenfassung
- [ ] Intelligente Klassifikation bei unbekannten Dokumenten
- [ ] Automatische Keyword-Extraktion fuer neue Dokumentenarten

### 7.2 Knowledge Graph
- [ ] Beziehungen zwischen Dokumenten erkennen (Vertrag -> Rechnung -> Mahnung)
- [ ] Kundenakte: Alle Dokumente eines Kunden verlinkt
- [ ] Timeline-Ansicht pro Kunde

### 7.3 Prognose & Decision Intelligence
- [ ] Zahlungsmuster erkennen (Rechnung -> wann bezahlt?)
- [ ] Fristen-Monitoring (Vertragsende, Kuendigungsfristen)
- [ ] Anomalie-Erkennung (ungewoehnliche Rechnungsbetraege)

---

## Priorisierte Reihenfolge

```
JETZT (Quick Wins, 1-2 Tage)
  -> .gitignore
  -> Error Handling Fixes
  -> Dashboard: Active Page Marker
  -> Dashboard: Buttons disabled waehrend Job
  -> Dashboard: Auto-Refresh Overview

NAECHSTE WOCHE (Epic 1 + 2 Kern)
  -> Structured Logging
  -> Config Validation
  -> State Locking
  -> Review-Management im Dashboard
  -> First-Run Wizard Basis

MONAT 1 (Epic 2 + 3)
  -> Dashboard komplett poliert
  -> Client Onboarding Package
  -> Dokumentation
  -> Watch Folder

MONAT 2-3 (Epic 4 + 5)
  -> Verbesserte Klassifikation
  -> Statistik-Dashboard
  -> Duplikat-Erkennung
  -> Volltextsuche

MONAT 3+ (Epic 6 + 7)
  -> Tests & CI/CD
  -> Authentifizierung
  -> LLM-Integration
  -> Knowledge Graph
```

---

## Metriken fuer Erfolg

| Metrik | Jetzt (MVP) | Ziel (v1.0) | Ziel (v2.0) |
|--------|-------------|-------------|-------------|
| Korrekte Klassifikation | ~70% | >90% | >95% |
| Review-Rate | ~30% | <10% | <5% |
| Onboarding-Zeit | 30+ min | 15 min | 5 min |
| Dashboard-Seiten | 4 | 7 | 10+ |
| Test-Abdeckung | 0% | 60% | 80% |
| Dateiformate | 8 | 12 | 15+ |
| Max Dateien/Run | 100 | 1000 | 10000+ |
