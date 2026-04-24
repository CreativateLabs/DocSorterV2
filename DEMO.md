# Doc-Sorter — Demo-Skript

**Ziel:** 10-Minuten-Demo die Wertversprechen in 5 Kern-Flows zeigt:
Erkennung → Umbenennung → Ablage → Review → Automatisierung.

**Zielgruppe:** Geschäftsführer/Inhaber mit ~27.000 Dokumenten im Chaos
(SharePoint/Outlook). Hauptwunsch: Ordnung, Sicherheit (lokal), automatische
Erkennung neuer Dokumente.

---

## Vorbereitung (am Tag der Demo)

**5 Minuten vorher:**

1. **Dashboard starten** und Browser-Tab auf `http://127.0.0.1:1991/` offen halten:
   ```bash
   cd ~/doc-sorter-mvp
   DOCSORTER_PORT=1991 .venv/bin/python dashboard.py
   ```

2. **Tray starten** (zweites Terminal):
   ```bash
   bash scripts/run-tray.sh
   ```
   Icon erscheint in der Menüleiste.

3. **Demo-Profil einrichten** (falls noch nicht):
   - Landing-Seite → Profil 3 (Freier Platz) → "Profil einrichten"
   - Wizard durchklicken (Benutzername, Pfade, Branchenvorlage)
   - Auf Config-Seite → Tab "Dokumentenarten" → **"Standard-Dokumentenarten
     einfügen"** klicken (11 Arten mit Keywords in 1 Klick)

4. **Test-Dokumente kopieren** in den Inbox-Ordner:
   ```bash
   # Eigene Test-Dokumente (privat-lokal, nicht im Repo):
   cp "$HOME/Documents/doc-sorter-testdata/set-1/"*.{pdf,docx} \
      "$(yq '.paths.inbox' config.yaml)/"
   ```
   (≈ 8 Dokumente: Bewerbungen, Angebote, Briefe gemischt)

   **Hinweis:** Persoenliche Testdaten bleiben in `~/Documents/doc-sorter-testdata/`
   — sie werden **nicht** ins Repo gepusht. Der Kunden-Datenordner
   (`~/Documents/DocSorter/`) enthaelt ausschliesslich `users/<mandant>/` mit
   inbox/output/logs.

5. **Browser-Tab arrangieren:** Dashboard + Finder-Fenster mit Inbox und
   Archiv-Ordner nebeneinander.

---

## Demo-Ablauf (10 Min)

### 1. Pitch (60s) — Das Problem

> *"Ihr habt 27.000 Dokumente verteilt in SharePoint, Outlook, Downloads-Ordner.
> Niemand findet mehr was. Verträge laufen aus ohne dass jemand reagiert.
> Rechnungen werden doppelt bezahlt. Doc-Sorter löst das — **lokal auf eurem
> Rechner, ohne Cloud-Zwang**."*

Zeige Landing-Seite: 3 Profile, animiertes Illustrations-SVG.

> *"Drei Mandanten, jeder eigenes Profil. Datenschutz-Trennung von Haus aus."*

### 2. Landing & Login (30s)

- Klick auf Profil (oder Taste **1**) → Passwort → Anmelden
- Oder: Tastenkürzel zeigen — "`1`, `2`, `3` für Profil, Enter zum Anmelden,
  Esc zum Abwählen"

### 3. Übersicht (90s) — "Ich sehe den Zustand meines Unternehmens"

Die Overview-Seite zeigt:
- **Pipeline-Visualisierung:** Inbox → Erkennung → Archiv / Prüfung
- **4 Stat-Cards:** Inbox (N), Zur Prüfung, Verarbeitet gesamt, Letzter Lauf
- **Proaktive Alerts:** "X Fristen & Erinnerungen" — überfällige Todos,
  Rechnungen mit nahem Zahlungsziel, Abos vor Verlängerung, Verträge mit
  Kündigungsfrist
- **Inbox-Quick-Action:** "N neue Dokumente in der Inbox → Zum Terminal"

> *"Die Dashboard-Startseite **zwingt Aufmerksamkeit auf das was Handlung
> erfordert**. Ohne Suche, ohne Klick."*

### 4. Verarbeitung (120s) — "Aus Chaos wird Struktur"

- Klick auf "Zum Terminal" → Terminal-Seite
- Erklärung: *"Vorschau zeigt was passieren würde — ohne etwas zu verschieben.
  Jetzt sortieren macht es echt. Rückgängig macht die letzte Aktion rückgängig."*
- **"Vorschau" klicken**
- StatusBox oben wird aktiv: Spinner "Vorschau läuft …"
- Fortschrittsbalken: "Verarbeite Datei 3 von 8"
- Log-Output live: Jede Datei mit erkanntem Typ, Kunde, Land, Datum, Confidence
- Ende: Grüner Erfolgs-Banner "Vorschau erfolgreich abgeschlossen"

> *"Die Vorschau hat **keine Datei angefasst** — ihr seht aber genau was
> passieren würde. Confidence-Score zeigt wie sicher das System ist."*

- Dann **"Jetzt sortieren"** → Log zeigt echte Moves → Finder aktualisieren
- Zum Finder wechseln: Archiv-Ordner zeigt die neue Struktur:
  ```
  archiv/rechnung/deutschland/GASAG/2026/
  archiv/vertrag/deutschland/Vattenfall/2025/
  archiv/bewerbung/unbekannt/unbekannt/2026/
  ```

### 5. Review (120s) — "Das System lernt von mir"

Zurück zum Dashboard → Klick auf "Zur Prüfung" im Review-Reminder-Banner.

Die Review-Seite zeigt unsichere Dokumente. Für jedes:
- Datei-Name + Preview-Button
- Erkannte Dokumentenart, Kunde, Land (editierbar)
- Confidence-Badge (rot/gelb/grün)
- Keyword-Chips ("Erkannt durch: rechnung, gesamtbetrag")
- Buttons: **"Ins Archiv"** (= bestätigen/korrigieren) + **"Zurück in Inbox"**

> *"Jede Korrektur wird zum **Trainingsbeispiel für die eigene Lern-Engine**.
> Nach 10 Beispielen trainiert sie sich automatisch und wird mit der Zeit
> unabhängig von externer KI."*

**Batch-Demo:**
- Mehrere Checkboxen oben links anklicken
- **Sticky Bulk-Action-Bar erscheint** mit "N Dokumente ausgewählt"
- Buttons: "Alle markieren / Abwählen / Als korrekt ins Archiv / Zurück in Inbox"
- **"Als korrekt ins Archiv"** klicken — alle ausgewählten werden bestätigt
  und die Lern-Engine bekommt positives Feedback

### 6. Tray-App (60s) — "Es läuft einfach mit"

Mauszeiger in die Menüleiste:
- **"DS ✉5 ?2 !1"** — 5 in Inbox, 2 Prüfung, 1 Alert

Klick aufs Icon:
- Status-Zeile: "✓ Läuft auf Port 1991 · Inbox: 5 · Prüfung: 2 · Alerts: 1"
- Menü: Dashboard öffnen/stoppen, Vorschau, Jetzt sortieren, Beenden

> *"Der Tray ist immer da. Ihr seht auf einen Blick wie viele Dokumente
> Aufmerksamkeit brauchen — ohne das Dashboard offen zu haben."*

### 7. Einstellungen (60s) — "Ihr baut es weiter aus"

Dashboard → Einstellungen → Tab "Dokumentenarten":
- Zeigt die 11 Standard-Arten
- Klick auf "Rechnung" → Mehrsprachige Keywords (de/en/sq) als Chips
- Neue Dokumentenart anlegen: "gutachten" eintippen → Keywords werden
  automatisch aus dem integrierten Wörterbuch vorgeschlagen

Tab "Kunden": Zeigt leer — *"Hier trägt der Kunde selbst seine häufigsten
Geschäftspartner ein. Das System erkennt sie dann automatisch in Dokumenten."*

### 8. Abschluss (60s) — "Was das bedeutet"

> *"Wir haben jetzt:*
> - *8 Dokumente verarbeitet — 6 automatisch, 2 korrigiert*
> - *Die Lern-Engine hat 2 neue Beispiele dazugelernt*
> - *Ein Vertrag mit Kündigungsfrist wurde erkannt — der Alert erscheint
>   auf der Startseite bevor die Frist abläuft*
> - *Alles läuft **lokal**. Keine Daten gehen irgendwohin."*

*"Nächste Schritte für eure Einführung:*
1. *Wir installieren Doc-Sorter auf dem Rechner*
2. *Wir richten 3-5 Mandanten-Profile ein*
3. *Ihr fangt mit einem Subset an — 100 Dokumente*
4. *Wir schauen in 2 Wochen welche Korrekturen die Lern-Engine gelernt hat"*

---

## Demo-Tipps

- **Nicht hektisch durchklicken** — 10 Minuten sind lang genug für Ruhe.
- **Bei jeder Seite kurz innehalten** und die Struktur erklären (nicht nur
  den einen Button der jetzt geklickt wird).
- **Wenn etwas nicht funktioniert:** Sag ehrlich "das ist in Arbeit" und
  zeig stattdessen einen Screenshot aus dem Backlog.
- **Review-Queue offenlassen** falls Zeit — das ist der "Wow-Moment" wenn
  man sieht wie einfach die Korrektur ist.

---

## Backup-Szenarien

**Falls Dashboard nicht startet:** CLI-Demo
```bash
.venv/bin/python main.py --dry-run
```
Zeigt im Terminal denselben Klassifikations-Flow (weniger visuell, aber
funktioniert immer).

**Falls Tray nicht erscheint:** Stichwort *"optional, als Menüleisten-
Komfort — das Dashboard ist die Haupt-Oberfläche"*.

**Falls Test-Dokumente fehlen:** Neue PDFs aus dem Downloads-Ordner in die
Inbox kopieren und durchspielen.

---

## Checkliste vor der Demo

- [ ] `.venv` aktiviert, alle Dependencies installiert
- [ ] Dashboard startet ohne Fehler auf Port 1991
- [ ] Tray erscheint in Menüleiste
- [ ] Demo-Profil hat Dokumentenarten eingerichtet
- [ ] 8+ Testdokumente in Inbox
- [ ] Finder-Fenster zu Archiv-Ordner offen
- [ ] Kamera an, Mikrofon geprüft (falls Remote-Demo)
- [ ] Tests laufen grün (`pytest tests/`) — als Sicherheits-Check
