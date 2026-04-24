# Scoping-Fragebogen: Dokumenten-Sortierungs-System

## A. Ausgangslage & Problemverstaendnis

### A1. Aktueller Zustand
- Wie viele Dokumente muessen insgesamt verarbeitet werden (grobe Schaetzung)?
  - [ ] unter 100
  - [ ] 100 - 500
  - [ ] 500 - 2.000
  - [ ] 2.000 - 10.000
  - [ ] ueber 10.000

- Wie viele neue Dokumente kommen pro Woche/Monat dazu?
  _______________

- Wo liegen die Dokumente aktuell?
  - [ ] Lokale Festplatte / Finder
  - [ ] Externe Festplatte / USB
  - [ ] OneDrive / SharePoint
  - [ ] Google Drive
  - [ ] E-Mail-Anhaenge
  - [ ] Scanner / physische Dokumente
  - [ ] Sonstiges: _______________

- Wie sieht die aktuelle Ordnerstruktur aus? (Beschreibung oder Screenshot)
  _______________

### A2. Schmerzpunkte
- Was genau funktioniert heute nicht gut?
  - [ ] Dateien haben unklare / unsinnige Namen
  - [ ] Keine einheitliche Ordnerstruktur
  - [ ] Dokumente werden nicht gefunden
  - [ ] Zu viel manuelle Arbeit beim Sortieren
  - [ ] Doppelte Dateien / Versionen unklar
  - [ ] Sonstiges: _______________

- Wie viel Zeit wird aktuell pro Woche fuer manuelles Sortieren/Suchen aufgewendet?
  _______________

---

## B. Dokumentenarten & Inhalte

### B1. Dateiformate
- Welche Dateitypen muessen verarbeitet werden?
  - [ ] PDF (Text-PDF)
  - [ ] PDF (Scans / Foto-PDF)
  - [ ] DOCX / Word
  - [ ] XLSX / Excel
  - [ ] TXT / Markdown
  - [ ] Bilder (JPG, PNG, TIFF)
  - [ ] E-Mails (.eml, .msg)
  - [ ] Sonstiges: _______________

### B2. Dokumentenkategorien
- Welche Arten von Dokumenten gibt es? (Bitte priorisieren: 1 = am haeufigsten)
  - [ ] Rechnungen (eingehend)
  - [ ] Rechnungen (ausgehend)
  - [ ] Vertraege
  - [ ] Angebote
  - [ ] Mahnungen / Inkasso
  - [ ] Briefe / Korrespondenz
  - [ ] Berichte / Reports
  - [ ] Personalunterlagen (HR)
  - [ ] Steuerunterlagen
  - [ ] Technische Dokumentation
  - [ ] Sonstiges: _______________

### B3. Sprachen
- In welchen Sprachen sind die Dokumente verfasst?
  - [ ] Deutsch
  - [ ] Englisch
  - [ ] Albanisch
  - [ ] Sonstiges: _______________

### B4. Vertraulichkeit
- Gibt es Dokumente mit besonderer Vertraulichkeit?
  - [ ] Ja, personenbezogene Daten (DSGVO-relevant)
  - [ ] Ja, Geschaeftsgeheimnisse / NDAs
  - [ ] Ja, Finanzdaten
  - [ ] Nein, alles unkritisch
- Duerfen Dokumenteninhalte an Cloud-Dienste (APIs) gesendet werden?
  - [ ] Nein, alles muss lokal bleiben
  - [ ] Ja, aber nur an europaeische Server
  - [ ] Ja, egal wo

---

## C. Gewuenschte Namens-Taxonomie & Ordnerstruktur

### C1. Dateinamen
- Gewuenschtes Namensschema (Beispiel bereits besprochen):
  `Projekt_Kunden-Name_Dokumentenart_DD.MM.YY`

- Welche Felder soll der Dateiname enthalten?
  - [ ] Projekt
  - [ ] Kunden-Name / Vertragspartner
  - [ ] Dokumentenart (Rechnung, Vertrag, etc.)
  - [ ] Datum
  - [ ] Rechnungsnummer / Aktenzeichen
  - [ ] Land
  - [ ] Sonstiges: _______________

- Gibt es bestehende Namenskonventionen die eingehalten werden muessen?
  _______________

### C2. Ordnerstruktur
- Gewuenschte Hierarchie (Beispiel bereits besprochen):
  `Projekt / Kunden-Name / Dokumentenart / Jahr /`

- Gibt es eine bestehende Zielstruktur die uebernommen werden soll?
  _______________

- Soll es einen "Review"-Ordner geben fuer unsichere Zuordnungen?
  - [ ] Ja
  - [ ] Nein

### C3. Kunden- / Projektliste
- Gibt es eine feste Liste von Projekten? Wenn ja, welche?
  _______________

- Gibt es eine feste Liste von Kunden / Vertragspartnern?
  _______________

- Sollen neue Kunden/Projekte automatisch erkannt oder manuell gepflegt werden?
  - [ ] Automatisch erkennen
  - [ ] Manuell pflegen (Whitelist)
  - [ ] Beides (automatisch + manuelle Korrektur)

---

## D. Technische Anforderungen

### D1. Plattform
- Auf welchem System soll es laufen?
  - [ ] macOS (Finder-Integration wichtig)
  - [ ] Windows
  - [ ] Linux
  - [ ] Plattformunabhaengig

### D2. Ausfuehrung
- Wie soll das System gestartet werden?
  - [ ] Manuell per Terminal-Befehl
  - [ ] Automatisch im Hintergrund (Watch Folder)
  - [ ] Beides (manuell + Watch)
  - [ ] Spaeter als App mit GUI

### D3. Speicherort
- Wo soll das Archiv / die sortierten Dateien liegen?
  - [ ] Lokale Festplatte
  - [ ] Externe Festplatte / NAS
  - [ ] Cloud (OneDrive, Google Drive)
  - [ ] Kombination

### D4. AI / Intelligenz
- Wie soll die Dokumentenerkennung funktionieren?
  - [ ] Nur Regeln (schnell, keine AI noetig)
  - [ ] Lokales AI-Modell (Ollama, privat)
  - [ ] Cloud-AI (OpenAI, Claude API -- beste Qualitaet)
  - [ ] Hybrid (Regeln + AI-Fallback)

### D5. Integration
- Soll das System mit anderen Tools zusammenarbeiten?
  - [ ] Hazel (macOS Watch Folder)
  - [ ] DEVONthink (Archiv)
  - [ ] Microsoft 365 / OneDrive
  - [ ] E-Mail-System
  - [ ] Buchhaltungssoftware
  - [ ] Sonstiges: _______________

---

## E. Ausbaustufen & Zukunftsvision

### E1. Was ist fuer Phase 1 (MVP) am wichtigsten?
Bitte Top 3 markieren:
- [ ] Dokumente automatisch umbenennen
- [ ] Dokumente in Ordnerstruktur verschieben
- [ ] OCR fuer Scans
- [ ] Watch Folder (automatisch bei Datei-Drop)
- [ ] Undo / Rueckgaengig machen
- [ ] Logs / Nachvollziehbarkeit
- [ ] Review-Ordner fuer unsichere Zuordnungen

### E2. Was ist spaeter interessant?
- [ ] Dokumenten-Zusammenfassung (pro Datei)
- [ ] Volltext-Suche ueber alle Dokumente
- [ ] Fristenueberwachung (Vertraege, Kuendigungen)
- [ ] Kunden-Akte auf Knopfdruck
- [ ] Zahlungsmuster-Erkennung
- [ ] Duplikat-Erkennung
- [ ] Dashboard / Reporting
- [ ] Natural Language Queries ("Zeig mir alle Rechnungen von Kunde X")
- [ ] Wissensarchiv / Knowledge Graph
- [ ] Sonstiges: _______________

### E3. Wie viele Nutzer sollen das System verwenden?
  - [ ] 1 Person
  - [ ] 2-5 Personen
  - [ ] Team (5+)
  - [ ] Unternehmensweiter Einsatz

### E4. Gibt es einen Zeitrahmen?
- Wann soll ein erster funktionierender Prototyp stehen?
  _______________
- Wann soll die finale Loesung produktiv sein?
  _______________

---

## F. Budget & Rahmenbedingungen

### F1. Budget-Rahmen
- Gibt es ein Budget fuer:
  - Software-Lizenzen (Hazel, DEVONthink, etc.): _______________
  - Entwicklung (Custom Code): _______________
  - Laufende Kosten (API, Hosting, Wartung): _______________

### F2. Eigenleistung
- Was kann / will der Kunde selbst uebernehmen?
  - [ ] Testdokumente bereitstellen
  - [ ] Kunden-/Projektliste pflegen
  - [ ] Ordnerstruktur definieren
  - [ ] Feedback zu Erkennungsqualitaet geben
  - [ ] Technische Wartung spaeter selbst
  - [ ] Sonstiges: _______________

### F3. Bestehende Infrastruktur
- Welche Software / Tools sind bereits vorhanden?
  - [ ] Python installiert
  - [ ] Homebrew installiert
  - [ ] Ollama / lokales LLM
  - [ ] Adobe Acrobat (fuer OCR)
  - [ ] Microsoft 365 Lizenz
  - [ ] Sonstiges: _______________

---

## G. Testdaten

### G1. Koennen 10-20 echte Beispieldokumente bereitgestellt werden?
- [ ] Ja, sofort verfuegbar
- [ ] Ja, aber muessen erst gesammelt werden
- [ ] Nein, wir arbeiten mit Dummy-Daten

### G2. Idealerweise enthalten die Testdokumente:
- [ ] Mindestens 2 verschiedene Kunden
- [ ] Mindestens 3 verschiedene Dokumentenarten
- [ ] Mindestens 1 Scan-PDF (fuer OCR-Test)
- [ ] Mindestens 1 mehrsprachiges Dokument
- [ ] Mindestens 1 DOCX-Datei

---

## Naechste Schritte nach dem Fragebogen

1. Fragebogen auswerten
2. Scope & Aufwand schaetzen
3. MVP-Definition gemeinsam festlegen
4. Testdokumente erhalten
5. Prototyp bauen & testen
6. Feedback-Runde
7. Ausbaustufen planen
