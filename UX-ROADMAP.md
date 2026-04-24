# Doc-Sorter -- UX/UI Optimization Roadmap

## UX Audit Zusammenfassung

Umfassender Audit aller 10 Dashboard-Seiten nach Best Practices.
Ziel: **Maximale Intuitivitaet fuer nicht-technische Nutzer.**

| Kategorie | Status | Handlungsbedarf |
|-----------|--------|-----------------|
| Navigation | **Erledigt** | Sidebar-Gruppen mit Badges implementiert |
| Button-Konsistenz | **Erledigt** | 6 Button-Varianten via Design-System (ds-btn-*) |
| Spacing/Layout | **Erledigt** | Tailwind-orientiertes Grid-System mit theme.py |
| Accessibility | Mittel | ARIA Labels, Kontraste |
| Mobile | Mittel | Tabellen, Formulare responsive |
| Ladezeiten-Feedback | Mittel | Spinner fuer Terminal, Loading States |
| Fehlerbehandlung | **Erledigt** | Empty States, Callout-Komponenten |
| Onboarding | **Erledigt** | Crisp Cards, benutzerfreundliche Sprache |
| Leere Zustaende | **Erledigt** | Konsistente empty_state() Komponente |
| Typografie | **Erledigt** | Inter Font, Typ-Skala via CSS Variablen |
| Design-System | **Erledigt** | theme.py: CSS Variablen, Komponenten-Helper |
| Nicht-technische Sprache | **Erledigt** | Alle Begriffe eingedeutscht |
| Pipeline-Visualisierung | **Erledigt** | Inbox -> Erkennung -> Archiv / Pruefung |

---

## Epic UX-0: UI Design Overhaul (ABGESCHLOSSEN)
> **Ziel:** Tailwind-orientiertes Design-System mit Crisp Components.

### Umgesetzte Aenderungen

**Design-System (theme.py):**
- [x] CSS Variablen fuer Farben, Radien, Schatten, Transitions
- [x] Inter Font (Google Fonts)
- [x] 6 Button-Varianten: primary, success, danger, warning, secondary, ghost
- [x] Stat-Card Komponente mit farbigen Icons
- [x] Status-Badge Komponente (success/warning/error/info/neutral)
- [x] Callout-Box Komponente (info/warning/success/error)
- [x] Empty-State Komponente
- [x] Pipeline-Visualisierung Komponente
- [x] Dark Mode Support fuer alle Komponenten
- [x] Custom Scrollbar, Table, Tab Styles

**Layout:**
- [x] Gradient Header mit Branding
- [x] Gruppierte Sidebar: Arbeiten / Verwalten / Einstellungen
- [x] Badge-Zaehler fuer Inbox und Pruefung in Navigation
- [x] Crisp Nav-Items mit Hover/Active States

**Nicht-technische Sprache:**
- [x] "Dry Run" -> "Vorschau"
- [x] "Live Run" -> "Jetzt sortieren"
- [x] "Confidence" -> "Erkennungs-Sicherheit"
- [x] "OCR" -> "Texterkennung"
- [x] "LLM" -> "KI-Unterstuetzung"
- [x] "Watcher" -> "Automatische Verarbeitung"
- [x] "Config" -> "Einstellungen"
- [x] "Review" -> "Pruefung"
- [x] "Taxonomy" -> "Benennungsregeln"

**Alle Seiten ueberarbeitet:**
- [x] Uebersicht: Pipeline-Visual, Crisp Stat-Cards
- [x] Terminal: Dark Terminal, benutzerfreundliche Buttons
- [x] Einstellungen: 11 Tabs mit Callout-Erklaerungen
- [x] Dateien: Crisp Upload, bessere Tabellen
- [x] Pruefung: Status-Badges, cleane Cards
- [x] Historie: Moderne Tabelle, Filter
- [x] Analyse: Crisp Chart-Cards, Summary Stats
- [x] System: Status-Badges, Pfade-Check
- [x] Wizard: Benutzerfreundliche Anleitung

---

## Epic UX-1: Visual Consistency & Design System (Sprint 1)
> **Ziel:** Einheitliches Look & Feel. Jede Seite fuehlt sich gleich an.

### UX-1.1 Design Tokens definieren
- [ ] **Farb-Palette fixieren:**
  - Primary: Blue-500 (#3B82F6) - Aktionen, Links, aktive Nav
  - Success: Green-500 (#22C55E) - Erfolg, OK-Status
  - Warning: Amber-500 (#F59E0B) - Warnungen, unsicher
  - Error: Red-500 (#EF4444) - Fehler, destruktive Aktionen
  - Neutral Text: Gray-600 (body), Gray-500 (sekundaer), Gray-400 (tertiear)
  - Background: White / Gray-50 (Light), Gray-900 / Gray-800 (Dark)
- [ ] **Spacing-Skala:**
  - XS: 4px, SM: 8px, MD: 16px, LG: 24px, XL: 32px
  - Alle Gaps und Margins nur aus dieser Skala
- [ ] **Border-Radius:** Einheitlich rounded-lg (8px) fuer alle Karten
- [ ] **Schatten:** shadow-sm fuer Karten, shadow-md fuer Modale

### UX-1.2 Typografie-System
- [ ] **Skala definieren:**
  - H1 (Seitentitel): text-2xl font-bold (28px) -> nur 1x pro Seite
  - H2 (Abschnitt): text-lg font-semibold (20px)
  - H3 (Karten-Titel): text-base font-semibold (16px)
  - Body: text-sm (14px) -> Standard fuer alles
  - Caption/Help: text-xs text-gray-500 (12px) -> NICHT kleiner
  - Mono: font-mono text-sm -> fuer Pfade, Code, Hashes
- [ ] **Alle Seiten anpassen:** Konsistente Klassen ueberall

### UX-1.3 Button-System
- [ ] **4 Button-Varianten definieren:**
  - **Primary:** Blau, gefuellt -> Haupt-Aktion pro Seite (max 1)
  - **Secondary:** Grau, outline -> Alternative Aktionen
  - **Destructive:** Rot, gefuellt -> Loeschen, Verwerfen (mit Confirm-Dialog)
  - **Ghost:** Transparent, nur Text -> Tertieare Aktionen
- [ ] **Icon-Position:** Immer links vom Text
- [ ] **Groesse:** Alle Buttons gleich hoch (h-10)
- [ ] **Tooltips:** ALLE Buttons brauchen Tooltip bei hover

### UX-1.4 Karten-System
- [ ] **Standard-Karte:** p-4, rounded-lg, shadow-sm
- [ ] **Stat-Karte:** Wie Standard + Icon links, Wert gross, Label klein
- [ ] **Action-Karte:** Wie Standard + Buttons rechts unten
- [ ] **Info-Karte:** Farbiger linker Rand (blau=info, gelb=warnung, rot=fehler)

---

## Epic UX-2: Intuitive Navigation (Sprint 1-2)
> **Ziel:** Nutzer weiss immer wo er ist und kommt ueberall hin.

### UX-2.1 Sidebar verbessern
- [ ] **Gruppierung mit Trennlinien:**
  ```
  ARBEITEN
    Uebersicht
    Terminal
    Analyse
  --------
  VERWALTEN
    Dateien
    Review
    Historie
  --------
  EINSTELLUNGEN
    Konfiguration
    System
  ```
- [ ] **Badge-Zahlen:** Inbox (3), Review (5) direkt in der Navigation
- [ ] **Collapse/Expand** Gruppen merken (localStorage)
- [ ] **Wizard aus Nav entfernen** nach erster Einrichtung

### UX-2.2 Breadcrumbs
- [ ] Jede Seite zeigt Pfad: `Uebersicht > Analyse > Duplikate`
- [ ] Klickbar fuer Zurueck-Navigation
- [ ] Konsistentes Styling: text-sm text-gray-500

### UX-2.3 Kontextuelle Quick-Actions
- [ ] **Overview-Seite:** "Inbox hat 5 neue Dateien" -> Button direkt zum Terminal
- [ ] **Review-Badge:** Wenn >0 Dateien, Pulsierender Punkt in Nav
- [ ] **Leere Inbox:** "Dateien hochladen" Link direkt zur File-Browser-Upload-Sektion

### UX-2.4 Tastatur-Shortcuts
- [ ] `Ctrl+D` -> Dry Run starten
- [ ] `Ctrl+L` -> Live Run starten
- [ ] `Ctrl+K` -> Quick-Suche oeffnen (navigiert zu Seiten oder sucht Dateien)
- [ ] `/` -> Fokus auf Suchfeld (falls vorhanden)

---

## Epic UX-3: Feedback & Ladezeiten (Sprint 2)
> **Ziel:** Nutzer weiss immer was passiert. Kein "haengt die App?"

### UX-3.1 Loading States
- [ ] **Terminal:**
  - Spinner neben "Job laeuft..." waehrend Ausfuehrung
  - Fortschrittsbalken: "Datei 3 von 12 wird verarbeitet"
  - Geschaetzte Restzeit anzeigen
- [ ] **File Browser:**
  - Skeleton-Loading waehrend Ordner geladen wird
  - Upload-Fortschrittsbalken pro Datei
- [ ] **Config Editor:**
  - "Speichern..." Spinner im Button waehrend save_config()
  - Button wird kurz gruen nach erfolgreichem Speichern
- [ ] **Analytics:**
  - "Charts werden geladen..." Placeholder
  - Lazy Loading fuer grosse Datenmengen

### UX-3.2 Erfolgs-Feedback
- [ ] **Nach jedem Speichern:** Gruener Haken + Timestamp "Zuletzt gespeichert: 14:32"
- [ ] **Nach Job-Ende:**
  - Erfolg: Gruenes Banner "12 Dateien verarbeitet, 2 zur Review"
  - Fehler: Rotes Banner mit "Details anzeigen" Expand
- [ ] **Nach Datei-Upload:** Thumbnail/Icon + Name + Groesse + Haekchen
- [ ] **Nach Review-Aktion:** Animation: Karte gleitet raus, Counter aktualisiert

### UX-3.3 Fehler-Meldungen fuer Menschen
- [ ] **Statt:** `OSError: [Errno 13] Permission denied: '/path/to/file'`
- [ ] **Zeige:** "Die Datei konnte nicht verschoben werden. Pruefe ob der Zielordner beschreibbar ist."
- [ ] **Immer:** Konkreten naechsten Schritt vorschlagen
- [ ] **Optional:** "Details anzeigen" klappt technische Info aus
- [ ] **Mapping erstellen:** Die 10 haeufigsten Fehler -> menschliche Erklaerung

### UX-3.4 Unsaved Changes Warning
- [ ] Config-Editor: Punkt neben Tab-Name bei ungespeicherten Aenderungen
- [ ] Browser-Warning bei Seitenwechsel mit ungespeicherten Aenderungen
- [ ] "Speichern oder verwerfen?" Dialog

---

## Epic UX-4: Accessibility & Inclusive Design (Sprint 2-3)
> **Ziel:** Bedienbar fuer alle -- auch mit eingeschraenktem Sehen oder ohne Maus.

### UX-4.1 Farbkontrast
- [ ] Alle Text/Hintergrund-Kombinationen auf WCAG AA pruefen (min 4.5:1)
- [ ] Gray-500 auf White testen (aktuell grenzwertig: 4.6:1)
- [ ] Status-Badges: Weissen Text auf farbigem Hintergrund pruefen
- [ ] Dark Mode: Alle Farben separat pruefen

### UX-4.2 Screen Reader Support
- [ ] ARIA Labels fuer alle Icon-only Buttons
  - Loeschen-Button: `aria-label="Kunde entfernen"`
  - Refresh-Button: `aria-label="Seite aktualisieren"`
- [ ] Tabelle: Korrekte `role="table"` und Column-Headers
- [ ] Charts: Alt-Text mit Zusammenfassung der Daten
- [ ] Formular-Labels: Explizit mit `for` Attribut verbunden

### UX-4.3 Keyboard Navigation
- [ ] Focus-Ring sichtbar machen (outline-2 outline-blue-500)
- [ ] Tab-Reihenfolge logisch (links-nach-rechts, oben-nach-unten)
- [ ] Enter/Space auf allen klickbaren Elementen
- [ ] Escape schliesst Dialoge/Dropdowns

### UX-4.4 Responsive Design
- [ ] **Tabellen:** Horizontal scrollbar auf Mobile
- [ ] **Charts:** Mindestbreite definieren, darunter Tabellen-Fallback
- [ ] **Config-Tabs:** Scrollbare Tab-Leiste statt Zeilenumbruch
- [ ] **Wizard:** Full-Width auf Mobile, keine Min-Width Constraints
- [ ] **Test auf:** iPhone SE (375px), iPad (768px), Laptop (1280px)

---

## Epic UX-5: Nicht-Technische Nutzer (Sprint 3)
> **Ziel:** Jemand der "PDF in Ordner sortieren" will, versteht alles sofort.

### UX-5.1 Sprache vereinfachen
- [ ] **"Dry Run"** -> "Vorschau (ohne Dateien zu verschieben)"
- [ ] **"Live Run"** -> "Jetzt sortieren"
- [ ] **"Confidence"** -> "Erkennungs-Sicherheit"
- [ ] **"Taxonomy"** -> "Benennungsregeln"
- [ ] **"OCR"** -> "Texterkennung (fuer gescannte Dokumente)"
- [ ] **"LLM"** -> "KI-Unterstuetzung"
- [ ] **"Watcher"** -> "Automatische Verarbeitung"
- [ ] **"Config"** -> "Einstellungen"
- [ ] **Keine Abkuerzungen** in Benutzer-sichtbaren Texten

### UX-5.2 Hilfe-System
- [ ] **Kontext-Hilfe:** Info-Icon (?) neben jedem Abschnitt
  - Klick oeffnet Tooltip mit Erklaerung + Mini-Beispiel
- [ ] **Erste-Schritte-Banner:** Auf Overview, bis 3 Dateien verarbeitet wurden
  ```
  Willkommen! So geht's los:
  1. Lege Dokumente in die Inbox -> [Dateien hochladen]
  2. Starte eine Vorschau -> [Vorschau starten]
  3. Pruefe die Ergebnisse -> [Ergebnisse ansehen]
  ```
- [ ] **Tooltips ueberall:** Jeder Button, jedes Icon, jedes Feld hat Tooltip
- [ ] **Glossar-Seite:** Was ist Inbox? Archiv? Review? OCR?

### UX-5.3 Gebuehrenpflichtige Aktionen hervorheben
- [ ] **Vor "Jetzt sortieren":** Zusammenfassung:
  ```
  12 Dateien werden sortiert:
  - 8 Rechnungen
  - 3 Vertraege
  - 1 Unbekannt (geht zur Pruefung)
  Weiter? [Abbrechen] [Sortieren]
  ```
- [ ] **Vor Undo:** "Die letzte Aktion wird rueckgaengig gemacht. Die Datei wird zurueck in die Inbox verschoben."
- [ ] **Vor Config-Loeschen:** Bestaetigung mit rotem Rahmen

### UX-5.4 Visuelle Prozess-Erklaerung
- [ ] **Overview-Seite:** Pipeline-Visualisierung
  ```
  [Inbox: 5] -> [Erkennung] -> [Archiv: 127]
                      |
                      v
                  [Pruefung: 2]
  ```
- [ ] **Terminal:** Live-Status statt nur Text:
  - Aktuell verarbeitete Datei mit Thumbnail
  - Erkannter Typ, Kunde, Datum als Tags
  - Confidence als Farbbalken
- [ ] **Review:** Vorher/Nachher Vorschau:
  - Links: Alter Dateiname
  - Rechts: Neuer Dateiname + Zielordner

---

## Epic UX-6: Delight & Polish (Sprint 3-4)
> **Ziel:** Von "funktioniert" zu "macht Spass zu benutzen".

### UX-6.1 Micro-Animations
- [ ] **Sidebar:** Sanfter Slide-In/Out (300ms ease)
- [ ] **Karten:** Hover-Effekt (leichtes Anheben, Schatten verstaerken)
- [ ] **Statistik-Zahlen:** Count-Up Animation beim Laden
- [ ] **Review-Karten:** Slide-Out beim Verschieben
- [ ] **Upload:** Drag-Zone pulsiert beim Drarueber-Ziehen
- [ ] **Status-Wechsel:** Sanftes Farbueberblenden (Watcher start/stop)

### UX-6.2 Smart Defaults
- [ ] **Config-Editor:** Pfad-Vorschlaege basierend auf OS
  - macOS: `~/Documents/DocSorter/...`
  - Windows: `C:\Users\...\Documents\DocSorter\...`
  - Linux: `~/docsorter/...`
- [ ] **Kunden-Hinzufuegen:** Automatisch Alias = Name
- [ ] **Dokumentenarten:** Haeufigste Keywords vorschlagen (aus verarbeiteten Docs lernen)
- [ ] **Watcher-Intervall:** "Normal (5s)" / "Schnell (1s)" / "Energiesparend (30s)"

### UX-6.3 Dashboard-Personalisierung
- [ ] **Startseite waehlen:** Manche Nutzer wollen direkt den Terminal
- [ ] **Sidebar-Position:** Links oder rechts
- [ ] **Kompakt-Modus:** Kleinere Karten, mehr Informationsdichte
- [ ] **Farbschema:** 3-4 Themes (Blau, Gruen, Lila, Orange)

### UX-6.4 Erfolgs-Momente
- [ ] **Erster erfolgreicher Run:** Konfetti-Animation + "Geschafft!" Badge
- [ ] **100 Dateien sortiert:** Milestone-Benachrichtigung
- [ ] **Review-Queue leer:** Positives Feedback mit Haekchen-Animation
- [ ] **Watcher laeuft:** Subtiler Puls-Indikator im Header

---

## Priorisierte Reihenfolge

```
WOCHE 1 (High Impact, Low Effort)
  -> UX-1.3: Button-Konsistenz (1 Tag)
  -> UX-3.1: Loading Spinner im Terminal (0.5 Tag)
  -> UX-5.1: Technische Begriffe umbenennen (0.5 Tag)
  -> UX-3.3: Menschliche Fehlermeldungen (1 Tag)

WOCHE 2 (High Impact, Medium Effort)
  -> UX-2.1: Sidebar-Gruppierung + Badges (1 Tag)
  -> UX-3.2: Erfolgs-Feedback verbessern (1 Tag)
  -> UX-1.2: Typografie vereinheitlichen (0.5 Tag)
  -> UX-5.2: Hilfe-Tooltips (1 Tag)

WOCHE 3-4 (Medium Impact)
  -> UX-4.1-4.3: Accessibility (2 Tage)
  -> UX-4.4: Responsive Design (2 Tage)
  -> UX-5.3: Bestaetigungs-Dialoge (1 Tag)
  -> UX-2.2: Breadcrumbs (0.5 Tag)
  -> UX-1.1: Design Tokens dokumentieren (0.5 Tag)

MONAT 2 (Polish & Delight)
  -> UX-6.1: Micro-Animations (2 Tage)
  -> UX-5.4: Visuelle Prozess-Erklaerung (2 Tage)
  -> UX-6.2: Smart Defaults (1 Tag)
  -> UX-6.3: Personalisierung (2 Tage)
  -> UX-6.4: Erfolgs-Momente (1 Tag)
```

---

## Metriken fuer UX-Erfolg

| Metrik | Jetzt | Ziel |
|--------|-------|------|
| Seiten bis zur ersten Sortierung | 3 Klicks | 1 Klick |
| Zeit bis Nutzer Config versteht | ~10 Min | 2 Min |
| Unerklaerte Fehlermeldungen | ~50% | 0% |
| Tooltips pro Seite | ~2 | Jedes Element |
| Mobile-Nutzbarkeit | Eingeschraenkt | Vollstaendig |
| WCAG AA Konformitaet | ~60% | 100% |
| Nicht-technische Begriffe | ~40% | 100% |
| Loading-Feedback | Fehlt oft | Immer vorhanden |
