# Doc-Sorter: Chat-Based Dashboard & NLP-to-File-Ops Evaluierung

> **Ziel:** Evaluierung eines Umbaus des Dashboards auf ein Chat-basiertes 3-Panel-Layout
> (orientiert an cNode MVP & SCIL Platform) mit einem NLP-to-File-Operations Agent
> (inspiriert von Scavenger AI's NLP-to-SQL Ansatz), der proaktiv Vorschlaege macht.

---

## 1. Vision

```
Heute:  Nutzer klickt Buttons -> System fuehrt aus -> Nutzer prueft Ergebnis
Morgen: Agent analysiert Inbox -> schlaegt Aktionen vor -> Nutzer bestaetigt nur
```

**Kernidee:** Der Agent ist NICHT nur ein Chatbot der auf Befehle wartet.
Er ist ein **proaktiver Assistent**, der:

1. **Analysiert** - Inbox scannen, Muster erkennen, Aenderungen bemerken
2. **Vorschlaegt** - "5 neue Rechnungen erkannt. Soll ich sie ins Archiv sortieren?"
3. **Bestaetigung einholt** - Nutzer sagt nur "Ja" oder korrigiert
4. **Ausfuehrt** - Dateien verschieben, umbenennen, klassifizieren
5. **Lernt** - Aus Korrekturen fuer zukuenftige Vorschlaege lernen

**Analogie zu Scavenger AI:**
- Scavenger: NLP -> SQL -> Datenbank -> Visualisierung
- Doc-Sorter: NLP -> File-Ops -> Dateisystem (lokal/Cloud) -> Bestaetigung

---

## 2. Referenz-Architektur Analyse

### 2.1 cNode MVP (3-Panel Workspace)

```
+------------------+------------------------+------------------+
|  Left Panel      |   Center Panel         |  Right Panel     |
|  (w-72)          |   (flex-1)             |  (w-80)          |
|                  |                        |                  |
|  Folder-Sidebar  |   Chat Interface       |  Decision Mirror |
|  - Projekte      |   - Message History    |  - Zusammenfassung|
|  - Decisions     |   - Intent Classifier  |  - Goals/Status  |
|  - Navigation    |   - Suggestion Chips   |  - Agent Activity|
|                  |   - Input Area         |                  |
+------------------+------------------------+------------------+
```

**Relevanz fuer Doc-Sorter:**
- 3-Panel-Layout ideal fuer Chat + Kontext
- Left Panel = Dateien/Ordner Navigation
- Center = Chat + proaktive Vorschlaege
- Right Panel = Aktuelle Aktion / Datei-Vorschau / Pipeline-Status

### 2.2 SCIL Platform (Chat-per-Page)

- Chat nur auf bestimmten Seiten (Diagnostik, Coaching)
- Settings/Config bleiben klassische Formulare
- Saubere Trennung: Chat wo sinnvoll, Formulare wo noetig

**Relevanz fuer Doc-Sorter:**
- NICHT jede Seite braucht Chat
- Settings/System bleiben klassische UI
- Chat nur dort wo es echten Mehrwert bietet

### 2.3 Scavenger AI (NLP-to-SQL, 3-Agent Architektur)

```
[Input Agent]          -> Semantic Layer aufbauen (Schema beschreiben)
[Analysis Agent]       -> NLP zu SQL/Python uebersetzen und ausfuehren
[Interpretation Agent] -> Ergebnisse als Visualisierung + Empfehlung zurueckgeben
```

**Adaptation fuer Doc-Sorter (NLP-to-File-Ops):**

```
[Indexing Agent]       -> File Semantic Layer aufbauen
                          (Ordnerstruktur, Dateitypen, Namenskonventionen,
                           Content-Embeddings, Cross-Backend Mapping)

[Operations Agent]     -> NLP zu File-Operationen uebersetzen
                          (find, move, rename, classify, search, delete)
                          Aber AUCH: proaktiv Muster erkennen und Vorschlaege generieren

[Presentation Agent]   -> Ergebnisse als Chat-Nachrichten + Vorschau darstellen
                          (Datei-Preview, Vorher/Nachher, Undo-Option)
```

---

## 3. Seiten-Evaluierung: Chat vs. Klassisch

### CHAT-BASIERT (Hoher Mehrwert)

| Seite | Jetzt | Chat-basiert | Beispiel-Interaktion |
|-------|-------|--------------|----------------------|
| **Terminal** | Buttons: Vorschau/Sortieren/Undo | Agent schlaegt Aktionen vor | *Agent: "5 neue PDFs in Inbox. 3 Rechnungen, 2 Vertraege erkannt. Sortieren?"* -> User: "Ja" |
| **Pruefung** | Manuelle Felder editieren | Agent schlaegt Korrekturen vor | *Agent: "Diese Datei sieht nach GASAG-Rechnung aus, nicht Vattenfall. Korrigieren?"* -> User: "Ja" |
| **Analyse** | Charts + Suchfeld | NL-Datenabfrage | *User: "Zeig mir alle GASAG-Rechnungen aus Q1"* -> Agent zeigt gefilterte Liste |

### HYBRID (Chat + Klassische UI)

| Seite | Jetzt | Hybrid-Ansatz | Warum Hybrid? |
|-------|-------|---------------|---------------|
| **Uebersicht** | Stat-Cards + Pipeline | Pipeline + proaktive Vorschlaege im Chat | Stats visuell besser, aber Agent kann Insights liefern |
| **Dateien** | Upload + Tabelle | Upload bleibt visuell, Chat fuer Suche/Aktionen | *User: "Finde alle PDFs groesser als 5MB"* |
| **Historie** | Tabelle + Filter | Tabelle bleibt, Chat fuer Abfragen | *User: "Was wurde gestern verarbeitet?"* |

### KLASSISCH BLEIBEN (Kein Chat-Mehrwert)

| Seite | Warum kein Chat? |
|-------|------------------|
| **Einstellungen** | 11 Tabs mit Formularen - Direkte Eingabe ist effizienter |
| **System** | Reine Statusanzeige - Keine Interaktion noetig |
| **Wizard** | Linearer Onboarding-Flow - Chat wuerde Struktur brechen |

---

## 4. Vorgeschlagenes 3-Panel Layout

### 4.1 Layout-Architektur

```
+--------------------+---------------------------+--------------------+
| LEFT PANEL (w-72)  |  CENTER PANEL (flex-1)    | RIGHT PANEL (w-80) |
|                    |                           |                    |
| [Doc-Sorter Logo]  |  [Chat Header]            | [Kontext-Panel]    |
|                    |                           |                    |
| --- NAVIGATION --- |  +---------------------+  | Tab: Vorschau      |
| > Uebersicht       |  | Agent: "5 neue PDFs |  | - Datei-Thumbnail  |
|   Chat             |  | in Inbox erkannt.   |  | - Metadaten        |
|   Analyse          |  | 3 Rechnungen,       |  | - Klassifikation   |
|                    |  | 2 Vertraege.        |  |                    |
| --- DATEIEN ---    |  | Sortieren?"         |  | Tab: Pipeline      |
| v Inbox (5)        |  |   [Ja] [Vorschau]   |  | - Inbox: 5         |
|   > rechnung.pdf   |  |   [Details]         |  | - Erkennung: ...   |
|   > vertrag.pdf    |  +---------------------+  | - Archiv: 127      |
|   > ...            |  | User: "Ja, aber     |  | - Pruefung: 2      |
| v Archiv (127)     |  | pruefe Vertraege"   |  |                    |
|   > Rechnungen/    |  +---------------------+  | Tab: Aktivitaet    |
|   > Vertraege/     |  | Agent: "OK. 3       |  | - 14:32 Sortiert   |
| v Pruefung (2)     |  | Rechnungen sortiert.|  | - 14:31 Erkannt    |
|                    |  | 2 Vertraege zur     |  | - 14:30 Gescannt   |
| --- QUICK ---      |  | Pruefung markiert." |  |                    |
| [Einstellungen]    |  +---------------------+  |                    |
| [System]           |  |                     |  |                    |
|                    |  | [Nachricht eingeben] |  |                    |
+--------------------+---------------------------+--------------------+
```

### 4.2 Panel-Beschreibung

**Left Panel: Navigation & Dateien**
- Logo + App-Name oben
- Navigations-Links (Uebersicht, Chat, Analyse)
- Dateibaum mit Inbox/Archiv/Pruefung (Live-Zaehler)
- Quick-Links: Einstellungen, System (klassische UI)
- Kollabierbar auf Mobile (Hamburger-Menu)

**Center Panel: Chat-Interface (Herzstuck)**
- **Proaktive Vorschlaege** des Agents (NICHT nur reaktiv!)
- Message-History mit verschiedenen Nachrichtentypen:
  - `agent_suggestion`: Vorschlag mit Bestaetigungs-Buttons
  - `agent_info`: Status-Update ("3 Dateien sortiert")
  - `agent_question`: Rueckfrage ("Meinst du GASAG oder E.ON?")
  - `user_command`: Nutzereingabe ("Sortiere alles")
  - `user_confirm`: Bestaetigung ("Ja")
  - `file_preview`: Datei-Vorschau inline
  - `operation_result`: Ergebnis mit Undo-Option
- Suggestion Chips: Schnellaktionen ("Inbox sortieren", "Pruefung oeffnen")
- Eingabefeld mit Auto-Resize

**Right Panel: Kontext & Vorschau**
- **Tab "Vorschau":** Aktuell ausgewaehlte Datei mit Thumbnail, Metadaten, Klassifikation
- **Tab "Pipeline":** Kompakte Pipeline-Visualisierung (Inbox->Erkennung->Archiv)
- **Tab "Aktivitaet":** Agent-Aktivitaetslog (was wurde wann gemacht)
- Kollabierbar (Toggle-Button)

### 4.3 Responsive Verhalten

```
Desktop (>1280px):  3-Panel nebeneinander
Tablet (768-1280):  Left Panel kollabiert, Center + Right
Mobile (<768px):    Single-Panel mit Bottom-Navigation
                    (wie cNode MVP: Overlay-Panels)
```

---

## 5. NLP-to-File-Operations Architecture

### 5.1 Kern-Analogie: Scavenger AI -> Doc-Sorter

```
Scavenger AI                         Doc-Sorter Agent
================================================== =========================================
Database Schema                  ->  File Semantic Layer
  - Tables, Columns                  - Ordnerstruktur, Dateitypen
  - Relationships                    - Namenskonventionen
  - KPI Definitions                  - Content-Embeddings
                                     - Cross-Backend Mapping

SQL Query                        ->  File Operation Command
  - SELECT ... WHERE ...             - find(criteria)
  - INSERT INTO ...                  - move(source, dest)
  - UPDATE ... SET ...               - rename(file, new_name)
  - JOIN ...                         - classify(file, category)

Query Execution                  ->  Operation Execution
  - Against single DB                - Against local FS
  - Returns result set               - Against SharePoint
                                     - Against Google Drive
                                     - Returns operation result

Result Visualization             ->  Chat Response
  - Charts, Tables                   - Datei-Vorschau
  - Text Summary                     - Vorher/Nachher
  - Recommendations                  - Undo-Option
```

### 5.2 Agent-Pipeline (Erweitert um Proaktivitaet)

```
                    +----------------------------+
                    |    FILE SEMANTIC LAYER      |
                    |  (Ordner, Typen, Regeln,    |
                    |   Embeddings, Konventionen) |
                    +----------------------------+
                               |
               +---------------+---------------+
               |                               |
      REAKTIVER PFAD                  PROAKTIVER PFAD
      (User fragt/befiehlt)           (Agent schlaegt vor)
               |                               |
    [User Input]                    [Filesystem Watcher]
         |                                |
    [Intent Detection]              [Aenderungs-Erkennung]
         |                           - Neue Dateien in Inbox
    [Schema Lookup]                  - Muster erkennen
         |                           - Anomalien entdecken
    [Op Plan Generation]                  |
         |                          [Analyse + Vorschlag]
    [Safety Check]                   - "5 neue PDFs erkannt"
         |                           - "3 sind Rechnungen"
    [User Confirmation]              - "Sortieren?"
         |                                |
    [Execution]                     [User Confirmation]
         |                                |
    [Result + Undo]                 [Execution]
                                         |
                                    [Result + Undo]
```

### 5.3 Proaktive Agent-Features (Kernunterschied zu reinem Chatbot)

**Der Agent wartet NICHT nur auf Befehle. Er:**

| Feature | Beschreibung | Beispiel |
|---------|-------------|----------|
| **Inbox-Monitoring** | Neue Dateien erkennen und klassifizieren | *"3 neue PDFs in Inbox. Wahrscheinlich Rechnungen von GASAG."* |
| **Batch-Vorschlaege** | Mehrere Dateien als Gruppe vorschlagen | *"Alle 5 Dateien sehen nach Rechnungen aus. Auf einmal sortieren?"* |
| **Anomalie-Erkennung** | Ungewoehnliche Dateien flaggen | *"Diese Datei hat keinen erkennbaren Dokumententyp. Manuell pruefen?"* |
| **Duplikat-Warnung** | Aehnliche Dateien finden | *"rechnung_2025.pdf scheint ein Duplikat von rechnung_jan.pdf zu sein."* |
| **Lern-Vorschlaege** | Aus Korrekturen lernen | *"Du hast 3x GASAG-Rechnungen manuell korrigiert. Soll ich die Regel anpassen?"* |
| **Zeitbasierte Aktionen** | Regelmaessige Aufgaben vorschlagen | *"Monatsende: 12 unverarbeitete Dateien. Soll ich den Monatslauf starten?"* |
| **Ordner-Vorschlaege** | Neue Ordner vorschlagen | *"Neuer Kunde 'SolarTech' erkannt. Ordner anlegen?"* |
| **Statistik-Insights** | Trends bemerken und berichten | *"Diese Woche 40% mehr Rechnungen als ueblich. Alles OK?"* |

### 5.4 File Semantic Layer (Kern-Innovation)

Analog zu Scavenger AI's proprietaerem Semantic Layer:

```yaml
file_semantic_layer:
  # Ordner-Taxonomie
  directories:
    inbox:
      path: "/Users/.../DocSorter/input"
      meaning: "Eingang fuer unverarbeitete Dokumente"
      backends: [local]
    archive:
      path: "/Users/.../DocSorter/output"
      meaning: "Sortierte und klassifizierte Dokumente"
      backends: [local]
      # Spaeter:
      # sharepoint: "https://company.sharepoint.com/docs/archive"
      # gdrive: "shared-drive-id/Archive"

  # Dateityp-Assoziationen
  file_types:
    "Rechnungen": [".pdf", ".xlsx"]
    "Vertraege": [".pdf", ".docx"]
    "Bilder": [".png", ".jpg", ".jpeg"]

  # Namenskonventionen
  naming_rules:
    pattern: "{datum}_{kunde}_{dokumentenart}_{original}"
    examples:
      - "2025-01-15_GASAG_Rechnung_Stromabrechnung.pdf"
      - "2025-02-20_Vodafone_Vertrag_Mobilfunk.pdf"

  # Kunden-Mapping (aus Config)
  entities:
    customers:
      "GASAG": { aliases: ["Gasag", "gasag AG"], keywords: ["Strom", "Gas"] }
      "Vodafone": { aliases: ["VF", "vodafone"], keywords: ["Mobilfunk", "Internet"] }

  # Content-Embeddings (auto-generiert)
  embeddings:
    model: "all-MiniLM-L6-v2"  # Oder OpenAI text-embedding-3-small
    indexed_files: 127
    last_update: "2025-03-16T14:30:00"
```

### 5.5 Operation-Typen (File-Ops DSL)

Analog zu SQL-Statements, aber fuer Datei-Operationen:

```json
{
  "operations": [
    {
      "action": "search",
      "criteria": {
        "content_semantic": "GASAG Rechnung Q1 2025",
        "file_types": ["pdf"],
        "date_range": { "after": "2025-01-01", "before": "2025-03-31" },
        "backends": ["local"]
      }
    },
    {
      "action": "classify",
      "target": "$search_results",
      "classification": {
        "doc_type": "Rechnung",
        "customer": "GASAG",
        "confidence": 0.92
      }
    },
    {
      "action": "move",
      "target": "$classified_results",
      "destination": "archive/Rechnungen/GASAG/2025-Q1/",
      "rename_pattern": "{datum}_{kunde}_Rechnung_{original}"
    }
  ],
  "requires_confirmation": true,
  "dry_run_first": true,
  "undo_available": true
}
```

---

## 6. Spaetere Erweiterung: Multi-Backend (Phase 2+)

### 6.1 Backend-Abstraction Layer

```
+------------------+
| Unified File API |  <-- Agent spricht nur mit dieser Schicht
+------------------+
    |    |    |    |
    v    v    v    v
 +----+ +----+ +----+ +----+
 |Local| |SP  | |GDr | |Drop|
 | FS  | |    | |ive | |box |
 +----+ +----+ +----+ +----+

Interface:
  search(query, filters) -> List[FileRef]
  move(source, dest)
  rename(file, new_name)
  copy(source, dest)
  classify(file, category)
  delete(file)  # nur mit doppelter Bestaetigung
  get_metadata(file) -> Metadata
  get_content(file) -> Content
  get_embedding(file) -> Vector
```

### 6.2 Backend-Prioritaet

```
Phase 1 (jetzt):   Lokales Dateisystem (Finder/Explorer)
Phase 2:           Google Drive Integration
Phase 3:           SharePoint / OneDrive
Phase 4:           Dropbox, Box, weitere
```

### 6.3 Cross-Backend Operationen

```
User: "Verschiebe alle Q4-Rechnungen von Google Drive ins lokale Archiv"

Agent-Plan:
  1. search(backends=["gdrive"], query="Q4 Rechnungen")  -> 8 Dateien
  2. download(source=gdrive_files, temp_dir)              -> Lokal zwischenspeichern
  3. classify(files, rules)                                -> Klassifizieren
  4. move(files, local_archive)                            -> Ins Archiv
  5. Optional: delete(gdrive_originals)                    -> Originale loeschen?

Agent: "8 Q4-Rechnungen auf Google Drive gefunden.
        Ins lokale Archiv verschieben?
        [ ] Originale auf Google Drive behalten
        [x] Originale auf Google Drive loeschen
        [Verschieben] [Abbrechen]"
```

---

## 7. Verwandte Projekte & Inspiration

### 7.1 Scavenger AI (Frankfurt, DE)

- **Was:** NLP-to-SQL fuer Business Intelligence
- **Architektur:** 3-Agent-System (Input, Analysis, Interpretation)
- **Kern-Innovation:** Proprietaerer Semantic Layer der Business-Begriffe auf DB-Schema mappt
- **Relevanz:** Gleicher Ansatz, aber SQL -> File-Ops

### 7.2 LSFS - LLM-based Semantic File System (ICLR 2025)

- **Was:** Akademisches Paper das LLM-basierte Dateisystem-APIs definiert
- **Architektur:** Macro-APIs (Retrieve, Change, Rollback, Link) + Micro-Syscalls
- **Kern-Innovation:** Dual-Index (traditioneller FS + Vector-DB mit Embeddings)
- **Open Source:** github.com/agiresearch/AIOS-LSFS
- **Relevanz:** Direkte Vorlage fuer die File-Ops Engine

### 7.3 Dust.tt - Synthetic Filesystems

- **Was:** Enterprise-Daten als Unix-aehnliche Dateisysteme fuer AI Agents
- **Kern-Insight:** Agents brauchen BEIDES: Navigation (Kontext aufbauen) + Search
- **Relevanz:** Cross-Backend Abstraktion (Slack, Notion, Drive -> Filesystem)

### 7.4 Perplexity Personal Computer (Maerz 2026)

- **Was:** 24/7 Agent auf dediziertem Mac Mini, steuert lokale Apps
- **Architektur:** NLP -> welche App oeffnen -> welche Dateien nutzen -> ausfuehren
- **Relevanz:** Vision von "NLP steuert lokales System" im Grossen

---

## 8. Technischer Umsetzungs-Stack

### 8.1 Empfohlener Stack

| Schicht | Technologie | Begruendung |
|---------|-------------|-------------|
| **Frontend** | NiceGUI (bestehend) | Kein Framework-Wechsel noetig; NiceGUI kann 3-Panel |
| **Chat UI** | NiceGUI `ui.chat_message()` + Custom Components | Native NiceGUI Chat-Elemente |
| **LLM** | Model-agnostisch via LiteLLM | OpenAI, Anthropic, Ollama (lokal) |
| **Embeddings** | `all-MiniLM-L6-v2` (lokal) oder OpenAI | Fuer Content-Suche |
| **Vector DB** | ChromaDB (lokal, lightweight) | Passt zu "lokal first" Ansatz |
| **File Indexing** | Custom Crawler + Apache Tika | PDF/Office Content Extraction |
| **Orchestration** | LangGraph oder custom Pipeline | Agentic Workflows mit Bestaetigung |
| **Watcher** | Bestehender Watchdog-basierter Watcher | Fuer proaktive Erkennung |
| **Undo-System** | SQLite-Log (wie AgentFS Ansatz) | Jede Operation reversibel |
| **Cloud APIs** | Google Drive API, MS Graph API | Fuer Phase 2+ |

### 8.2 NiceGUI 3-Panel mit Chat

NiceGUI unterstuetzt das 3-Panel-Layout nativ:

```python
# Konzept-Sketch (NICHT finaler Code)
with ui.header():
    # Header wie bisher

with ui.left_drawer():
    # Left Panel: Navigation + Dateibaum

with ui.column().classes("flex-1"):
    # Center: Chat-Interface
    with ui.scroll_area():
        # Message History
    with ui.row():
        # Input Area

with ui.right_drawer():
    # Right Panel: Kontext + Vorschau
```

---

## 9. Chat-Nachrichten-Typen

### 9.1 Message-Schema

```python
@dataclass
class ChatMessage:
    id: str
    role: Literal["agent", "user", "system"]
    type: Literal[
        "suggestion",      # Agent schlaegt Aktion vor (mit Buttons)
        "question",        # Agent fragt zurueck
        "info",            # Status-Update
        "result",          # Ergebnis einer Operation
        "error",           # Fehlermeldung
        "file_preview",    # Datei-Vorschau
        "text",            # Freier Text
        "insight",         # Proaktiver Insight/Analyse
    ]
    content: str
    actions: list[Action] | None = None  # Buttons fuer Bestaetigungen
    files: list[FileRef] | None = None   # Referenzierte Dateien
    undoable: bool = False               # Undo-Option verfuegbar?
    metadata: dict | None = None
```

### 9.2 Beispiel-Konversation (Proaktiver Agent)

```
SYSTEM: Agent beobachtet Inbox...

AGENT [suggestion]:
  "5 neue Dateien in der Inbox erkannt:
   - 3x Rechnungen (GASAG, Vodafone, Telekom)  [92-97% Sicherheit]
   - 1x Vertrag (Deutsche Bank)                  [88% Sicherheit]
   - 1x Unbekannt                                [34% Sicherheit]

   Vorschlag: 4 Dateien sortieren, 1 zur Pruefung markieren."
   [Alle sortieren] [Vorschau zuerst] [Details]

USER [confirm]: "Ja, sortieren"

AGENT [result]:
  "Erledigt!
   - 3 Rechnungen -> Archiv/Rechnungen/
   - 1 Vertrag -> Archiv/Vertraege/Deutsche_Bank/
   - 1 Datei -> Pruefung/
   [Rueckgaengig machen]"

--- 30 Minuten spaeter ---

AGENT [insight]:
  "Auffaellig: In den letzten 2 Wochen kamen 8 GASAG-Rechnungen.
   Normalerweise sind es 2 pro Monat. Alles in Ordnung?"
   [Ist OK] [Zeige mir die Dateien]

--- User fragt aktiv ---

USER [text]: "Zeig mir alle Vertraege die dieses Jahr auslaufen"

AGENT [result]:
  "3 Vertraege gefunden die 2025 auslaufen:
   1. Vodafone_Mobilfunk.pdf - Ablauf: 31.03.2025
   2. GASAG_Strom.pdf - Ablauf: 30.06.2025
   3. DeutscheBank_Konto.pdf - Ablauf: 31.12.2025"
   [Im Finder oeffnen] [Erinnerung setzen]
```

---

## 10. Seiten-Mapping: Alt -> Neu

### 10.1 Was aendert sich?

| Alte Seite | Neues Konzept | Aenderung |
|-----------|---------------|-----------|
| **Uebersicht** | -> Left Panel (Pipeline Stats) + Chat Home | Pipeline-Vis wandert in Right Panel |
| **Terminal** | -> Chat (Kern-Feature) | Buttons werden Chat-Aktionen |
| **Pruefung** | -> Chat (Proaktive Vorschlaege) | Agent schlaegt Korrekturen vor |
| **Analyse** | -> Chat (NL-Abfragen) + Right Panel (Charts) | "Zeig mir..." statt Tabs |
| **Dateien** | -> Left Panel (Dateibaum) + Chat (Upload/Suche) | Upload bleibt visuell |
| **Historie** | -> Chat ("Was wurde gestern verarbeitet?") | On-Demand statt eigene Seite |
| **Einstellungen** | -> Eigene Seite (BLEIBT klassisch) | Kein Chat noetig |
| **System** | -> Eigene Seite (BLEIBT klassisch) | Kein Chat noetig |
| **Wizard** | -> Eigene Seite (BLEIBT klassisch) | Linearer Flow |

### 10.2 Routing-Konzept

```
/                  -> 3-Panel Chat Layout (Home / Proaktive Vorschlaege)
/chat              -> 3-Panel Chat Layout (expliziter Chat-Modus)
/analytics         -> 3-Panel mit Analyse-Fokus im Right Panel
/config            -> Klassische Seite (Einstellungen)
/system            -> Klassische Seite (System-Status)
/wizard            -> Klassische Seite (Ersteinrichtung)
```

---

## 11. Implementierungs-Phasen

### Phase 1: Chat-Shell + Basic Agent (2-3 Wochen)

```
[ ] 3-Panel Layout in NiceGUI aufbauen
    - Left Panel: Vereinfachte Navigation + Dateibaum
    - Center: Chat-Interface mit Message-History
    - Right: Pipeline-Status + Datei-Vorschau
[ ] Chat-Message-Komponenten erstellen
    - suggestion, result, error, file_preview
    - Bestaetigungs-Buttons in Nachrichten
[ ] Basic Agent: Regelbasiert (kein LLM noetig)
    - Inbox scannen -> Dateien erkennen -> Vorschlag generieren
    - Bestehende Sorter-Engine als Backend nutzen
    - Ergebnisse als Chat-Nachricht darstellen
[ ] Suggestion Chips fuer Quick-Actions
```

### Phase 2: LLM-Agent + NLP (2-3 Wochen)

```
[ ] LLM-Integration (model-agnostisch via LiteLLM)
[ ] Intent Detection: NL -> File-Operations
    - "Sortiere die Inbox" -> dry_run + live_run
    - "Zeig mir alle Rechnungen" -> search + filter
    - "Was ist das fuer eine Datei?" -> classify + preview
[ ] File Semantic Layer aufbauen
    - Ordner-Taxonomie aus Config extrahieren
    - Namenskonventionen als Kontext
    - Kunden/Dokumentenarten als Entities
[ ] Proaktive Vorschlaege mit Bestaetigung
[ ] Undo-System (SQLite-Log)
```

### Phase 3: Content-Intelligence (2-3 Wochen)

```
[ ] Content-Embeddings (all-MiniLM-L6-v2 / ChromaDB)
[ ] Semantische Suche: "Finde Rechnungen ueber 500 Euro"
[ ] Duplikat-Erkennung (Embedding-Similarity)
[ ] Lern-Schleife: Aus Korrekturen Regeln verbessern
[ ] Anomalie-Erkennung (ungewoehnliche Dateien/Muster)
```

### Phase 4: Multi-Backend (3-4 Wochen)

```
[ ] Unified File API Abstraction
[ ] Google Drive Backend
[ ] SharePoint/OneDrive Backend
[ ] Cross-Backend Operationen
[ ] Backend-spezifische Berechtigungen
```

---

## 12. Risiken & Offene Fragen

| Risiko | Mitigation |
|--------|-----------|
| NiceGUI Chat-Performance bei vielen Nachrichten | Virtualisierte Scroll-Liste, Message-Limit |
| LLM-Latenz bei Echtzeit-Vorschlaegen | Regelbasierter Fallback fuer Standard-Operationen |
| False Positives bei proaktiven Vorschlaegen | Confidence-Threshold + "Nicht mehr vorschlagen" Option |
| Komplexitaet der Multi-Backend Abstraction | Phase 4, erst wenn lokal stabil laeuft |
| Datensicherheit bei Cloud-Backends | Verschluesselte Token-Speicherung, OAuth2 Flows |
| User-Akzeptanz: "Will ich ueberhaupt Chat?" | Hybrid: Chat + klassische Buttons parallel anbieten |

---

## 13. Entscheidungen die getroffen werden muessen

1. **LLM-Wahl:** OpenAI API vs. Anthropic vs. Ollama (lokal)?
   - Empfehlung: Model-agnostisch via LiteLLM, Default = Ollama fuer Privacy

2. **Phase 1 ohne LLM?** Regelbasierter Agent zuerst, LLM spaeter?
   - Empfehlung: Ja, Phase 1 regelbasiert -> schneller Mehrwert

3. **Right Panel immer sichtbar?** Oder nur bei Bedarf?
   - Empfehlung: Default offen auf Desktop, kollabierbar

4. **Chat-History persistent?** Oder pro Session?
   - Empfehlung: Persistent in SQLite, mit "Neuer Chat" Option

5. **Proaktivitaets-Level?** Wie oft soll der Agent von sich aus schreiben?
   - Empfehlung: Konfigurierbar (Ruhig / Normal / Proaktiv)
