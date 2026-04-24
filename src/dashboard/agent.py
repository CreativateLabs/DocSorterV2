"""Proaktiver Doc-Sorter Agent: Chat-First Dokumenten-Assistent.

Der Agent steuert ALLE Funktionen des 3-Panel Dashboards:
1. Scannt die Inbox und erkennt neue Dateien
2. Klassifiziert mit der bestehenden Engine
3. Generiert proaktive Vorschlaege als Chat-Messages
4. Fuehrt Aktionen nach Bestaetigung aus (mit Undo)
5. Zeigt Dateien, History, Analyse-Charts inline im Chat
6. Onboarding fuer neue Nutzer
7. Connector-Architektur fuer erweiterbare Dokumenten-Quellen

Phase 1: Regelbasiert (kein LLM).
Phase 2: LLM-Integration fuer NLP-Verstaendnis.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)

import re as _re
import random as _random

# ---------------------------------------------------------------------------
# Intent-Erkennung (Modul-Ebene)
# ---------------------------------------------------------------------------

_GREETING_STARTS = (
    # Deutsch
    "hallo", "hi", "hey", "moin", "servus", "guten morgen", "guten tag",
    "guten abend", "grüß gott", "grüss gott", "hallöchen", "hallochen",
    "tach", "nabend", "mahlzeit", "na ", "na!", "na,", "was geht",
    "was ist los", "long time", "guten", "morgen!", "tag!",
    # Umgangssprache / Slang Deutsch
    "ey ", "ey!", "ey,", "ey?",
    "oida", "oida!", "alter ", "alter!", "alter,",
    "digga", "digger", "digga!",
    "bruder", "bro ", "bro!", "brudi",
    "na alter", "na digga", "na bruder", "na bro",
    "jo jo", "jooo", "joo ", "naaa",
    "waddap", "waddup", "wass geht", "was geht alter", "was geht digga",
    "was los alter", "was los digga",
    # International
    "hej", "howdy", "yo ", "yo!", "salut", "ciao", "ola ", "ola!",
    "hello", "good morning", "good evening", "sup ", "sup!",
)

_THANKS_EXPLICIT = (
    "danke", "dankeschön", "dankeschoen", "vielen dank", "herzlichen dank",
    "danke schön", "danke sehr", "dankeschön sehr",
    "thx", "thanks", "thank you", "ty ", "ty!", "merci", "grazie",
    "gracias", "cheers", "appreciated",
)

_THANKS_POSITIVE = (
    # Deutsch
    "super", "toll", "top", "prima", "klasse", "wunderbar", "ausgezeichnet",
    "perfekt", "genial", "hammer", "krass", "spitze", "fantastisch",
    "großartig", "grossartig", "hervorragend", "sehr gut", "gut gemacht",
    "das war gut", "passt", "passt so", "alles klar", "läuft", "lauft",
    "sehr schön", "sehr schon", "schön", "nice one", "gut", "jut",
    # Umgangssprache / Slang Deutsch
    "safe", "sauber", "geil", "fett", "mega", "1a", "erste sahne",
    "auf drauf", "der hammer", "der kracher", "voll gut", "echt gut",
    "läuft bei dir", "lauft bei dir", "du bist gut", "du bist der beste",
    "lit", "fire", "drauf", "legitim", "legit", "ultra", "bombe",
    "geilo", "voll krass", "so geil", "echt krass", "wahnsinn",
    # Englisch
    "nice", "cool", "great", "awesome", "excellent", "perfect", "brilliant",
    "amazing", "fantastic", "wonderful", "bravo", "well done", "good job",
    "👍", "🙌", "💪",
)

_WELLBEING_WORDS = (
    # Hochdeutsch
    "wie geht es dir", "wie geht's", "wie geht es", "wie läuft es",
    "wie lauft es", "alles gut bei dir", "alles okay bei dir",
    "alles ok bei dir", "bist du ok", "bist du okay",
    # Umgangssprache Deutsch
    "was geht", "was geht ab", "was geht bei dir", "was is los",
    "was ist los", "was läuft", "was lauft", "was machst du",
    "wie läuft's", "wie lauft's", "wie steht's", "wie stehts",
    "wie so", "alles fit", "alles klar bei dir", "alles beim alten",
    "was geht so", "was geht bei euch", "na wie geht's", "na wie gehts",
    "na wie läuft", "na was geht", "und wie geht's", "und wie gehts",
    "läuft bei dir", "lauft bei dir", "alles paletti", "alles roger",
    # Slang / Jugendsprache
    "was geht alter", "was geht digga", "was geht bruder", "was geht bro",
    "alles safe", "alles mega", "alles fett", "alles geil",
    "was machst alter", "was machst digga", "ey was geht",
    "ey alles klar", "ey wie läuft", "ey wie lauft",
    "was geht ey", "wie läuft's alter", "wie lauft's alter",
    # Englisch / International
    "how are you", "how r u", "how you doing", "how are you doing",
    "how is it going", "how's it going", "hows it going",
    "what's up", "whats up", "sup?", "wassup", "how goes it",
    "you good", "you ok", "you okay", "all good",
)

_AFFIRMATION_WORDS = (
    # Deutsch
    "ja", "jo", "jop", "jup", "jap", "jawohl", "jaaa", "jaa",
    "klar", "klaro", "klar doch", "logisch", "natürlich", "natuerlich",
    "selbstverständlich", "selbstverstaendlich", "stimmt", "stimmt genau",
    "genau", "genau so", "richtig", "korrekt", "exakt", "exakt so",
    "auf jeden fall", "auf jedenfall", "definitiv", "absolut",
    "sicher", "sicher doch", "sicher!", "sicherlich", "okay", "ok",
    "alright", "roger", "verstanden", "einverstanden", "passt", "passt so",
    "mach das", "mach es", "machen", "bitte", "gerne", "gern",
    "yep", "jep",
    # Slang / Jugendsprache
    "safe", "logo", "ja logo", "na logo", "klar alter", "klar digga",
    "klar bro", "jo safe", "ja safe", "auf jeden", "auf jeden digga",
    "jo auf jeden", "mach ma", "machen wir", "geht klar", "geht",
    "geht klar alter", "geht klar digga", "auf", "fett", "krass ja",
    # Englisch
    "yes", "yeah", "yea", "yup", "sure", "of course", "absolutely",
    "correct", "exactly", "right", "affirmative", "indeed",
)

_NEGATION_WORDS = (
    # Deutsch
    "nein", "nee", "nö", "noe", "ne ", "ne!", "ne,", "neee",
    "nope", "nöp", "nop",
    "nicht", "nicht wirklich", "nicht nötig", "nicht noetig",
    "lass es", "lass mal", "lass gut sein", "lieber nicht",
    "auf keinen fall", "keinesfalls", "auf gar keinen fall",
    "niemals", "nie", "negativ", "falsch", "nix", "nichts",
    "stopp", "stop", "abbrechen", "abbruch", "cancel",
    # Englisch
    "no", "nah", "nope", "never", "negative", "not really",
    "no thanks", "no thank you", "not needed", "forget it",
)

_DATE_RE = _re.compile(
    r'\b\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}\b'
    r'|\b\d{4}[.\-/]\d{2}[.\-/]\d{2}\b'
    r'|\b(?:januar|februar|märz|maerz|april|mai|juni|juli|august|'
    r'september|oktober|november|dezember)\s+\d{4}\b'
    r'|\b(?:letzte[rn]?m?s?|vergangene[rn]?m?s?)\s+(?:woche|monat|jahr)\b'
    r'|\b(?:vor|seit)\s+\d+\s+(?:tagen?|wochen?|monaten?|jahren?)\b',
    flags=_re.IGNORECASE,
)


def _is_greeting(lower: str) -> bool:
    if len(lower) > 70:
        return False
    stripped = lower.strip("!?., ")
    return any(stripped == w.strip() or lower.startswith(w) for w in _GREETING_STARTS)


def _is_thanks(lower: str) -> bool:
    if len(lower) > 80:
        return False
    # Explizite Dankesworte immer
    if any(lower.startswith(w) or lower == w for w in _THANKS_EXPLICIT):
        return True
    # Positive Kurzantworten nur bei ≤ 4 Wörtern
    if len(lower.split()) <= 4:
        return any(w in lower for w in _THANKS_POSITIVE)
    return False


def _is_wellbeing(lower: str) -> bool:
    return any(w in lower for w in _WELLBEING_WORDS)


def _is_affirmation(lower: str) -> bool:
    if len(lower) > 60:
        return False
    stripped = lower.strip("!?., ")
    return any(stripped == w.strip() or lower.startswith(w) for w in _AFFIRMATION_WORDS)


def _is_negation(lower: str) -> bool:
    if len(lower) > 60:
        return False
    stripped = lower.strip("!?., ")
    return any(stripped == w.strip() or lower.startswith(w) for w in _NEGATION_WORDS)


_HELP_REQUEST_PHRASES = (
    # Kannst du helfen?
    "kannst du mir helfen", "kannst du helfen", "hilfst du mir",
    "kannst du mich unterstützen", "kannst du mich unterstuetzen",
    "bitte hilf mir", "hilf mir", "ich brauche hilfe", "brauche hilfe",
    "help me", "can you help", "could you help", "i need help",
    # Wie funktioniert das?
    "wie funktioniert", "wie funktionierst", "wie geht das", "wie geht es",
    "wie soll ich", "wie fange ich an", "wo fange ich an",
    "wie benutze ich", "wie nutze ich", "wie verwende ich",
    "wie arbeite ich", "wie bediene ich",
    # Was bist du?
    "was bist du", "wer bist du", "was machst du hier", "was ist das hier",
    "was ist das für", "was ist dieses", "was ist das programm",
    "was kann dieses", "was kann das programm", "was kann ich hier",
    "erkläre mir", "erklär mir", "erklaere mir", "erklaer mir",
    "beschreib mir", "sag mir wie",
    # Allgemein
    "anleitung", "tutorial", "einstieg", "quick start", "quickstart",
    "einführung", "einfuehrung", "onboarding",
    "what can you do", "what do you do", "what is this",
    "explain", "how does this work", "how do i use",
)


def _is_help_request(lower: str) -> bool:
    return any(p in lower for p in _HELP_REQUEST_PHRASES)


def _extract_date_filter(lower: str) -> str | None:
    """Erste Datumserwähnung aus Text extrahieren. None wenn keine."""
    m = _DATE_RE.search(lower)
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# Message Types
# ---------------------------------------------------------------------------

class MsgType(str, Enum):
    """Chat-Nachrichtentypen."""
    SUGGESTION = "suggestion"     # Agent schlaegt Aktion vor (mit Buttons)
    QUESTION = "question"         # Agent fragt zurueck
    INFO = "info"                 # Status-Update
    RESULT = "result"             # Ergebnis einer Operation
    ERROR = "error"               # Fehlermeldung
    FILE_PREVIEW = "file_preview" # Datei-Vorschau
    TEXT = "text"                 # Freier Text
    INSIGHT = "insight"           # Proaktiver Insight / Analyse
    WELCOME = "welcome"           # Willkommensnachricht
    # --- 3-Panel Chat-First Erweiterungen ---
    CHART = "chart"              # Inline-Chart (HighCharts config in metadata)
    TABLE = "table"              # Inline-Tabelle (rows/cols in metadata)
    FILE_LIST = "file_list"      # Dateiliste (Inbox/Archive/Review)
    ONBOARDING = "onboarding"    # Onboarding-Step
    CONNECTOR = "connector"      # Connector-Status
    SYSTEM_INFO = "system_info"  # System-Status
    HISTORY = "history"          # History-Eintraege


class MsgRole(str, Enum):
    AGENT = "agent"
    USER = "user"
    SYSTEM = "system"


@dataclass
class FileRef:
    """Referenz auf eine Datei mit Metadaten."""
    path: str
    name: str
    size_str: str
    doc_type: str = "unbekannt"
    customer: str = "unbekannt"
    country: str = "unbekannt"
    datum: str = ""           # DD.MM.YY
    datum_full: str = ""      # DD.MM.YYYY
    jahr: str = ""            # YYYY
    unsicher: bool = False
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)


@dataclass
class Action:
    """Eine Aktion die der User bestaetigen kann."""
    id: str
    label: str
    icon: str
    variant: str = "primary"   # primary, success, danger, ghost
    callback_key: str = ""     # Identifier fuer die Callback-Zuordnung


@dataclass
class ChatMessage:
    """Eine Nachricht im Chat."""
    id: str
    role: MsgRole
    type: MsgType
    content: str
    timestamp: str = ""
    actions: list[Action] = field(default_factory=list)
    files: list[FileRef] = field(default_factory=list)
    undoable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    artifact_id: str = ""  # Verknuepfung mit Right-Panel Artifact

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M")
        if not self.id:
            self.id = str(uuid4())[:8]


# ---------------------------------------------------------------------------
# Undo-Log
# ---------------------------------------------------------------------------

@dataclass
class UndoEntry:
    """Ein reversibler Schritt."""
    id: str
    description: str
    moves: list[tuple[str, str]]  # (source, destination) Paare
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class DocSorterAgent:
    """Proaktiver regelbasierter Agent fuer Dokumenten-Sortierung."""

    def __init__(self, username: str = "") -> None:
        self.username: str = username          # Eingeloggter User (fuer Pfad-Aufloesung)
        self.messages: list[ChatMessage] = []
        self.undo_stack: list[UndoEntry] = []
        self._pending_files: list[FileRef] = []
        self._on_message: Callable[[ChatMessage], None] | None = None
        self._initialized = False
        self._suppress_callback = False  # Batch-Emit: Callback unterdruecken
        self._lock = threading.Lock()  # Thread-Safety fuer messages-Liste
        self._dirty = False  # Flag fuer UI-Polling (Timer prueft periodisch)
        self._artifacts: list[dict[str, Any]] = []  # Right-Panel Artifacts
        self._onboarding_step: int = 0  # Onboarding-Fortschritt (0 = nicht aktiv)
        self._connectors: list = []  # Registrierte Connectors
        # Stats-Cache: Timer-Callbacks lesen nur den Cache (kein I/O)
        self._stats_cache: dict[str, Any] = {"inbox": 0, "review": 0, "processed": 0}
        self._stats_cache_time: float = 0.0
        self._init_connectors()

    def _cfg(self) -> dict:
        """Config laden und benutzerspezifische Pfade aus _state.json injizieren.

        Stellt sicher dass immer die Pfade des eingeloggten Users verwendet werden,
        unabhaengig davon was gerade in config.yaml steht.
        """
        from ..config import load_config
        cfg = load_config()
        if not self.username:
            return cfg
        try:
            import json as _json
            state_path = Path(__file__).resolve().parent.parent.parent / "_state.json"
            if not state_path.exists():
                return cfg
            state = _json.loads(state_path.read_text(encoding="utf-8"))
            # Pfade des eingeloggten Users einsetzen
            user_paths = state.get("user_dirs", {}).get(self.username)
            if user_paths:
                cfg.setdefault("paths", {}).update(user_paths)
            # Benutzerspezifische Klassifikations-Config
            user_config = state.get("user_config", {}).get(self.username, {})
            if user_config.get("document_types"):
                cfg["document_types"] = user_config["document_types"]
            if user_config.get("known_customers"):
                cfg["known_customers"] = user_config["known_customers"]
            if user_config.get("countries"):
                cfg["countries"] = user_config["countries"]
        except Exception:
            pass
        return cfg

    def _init_connectors(self) -> None:
        """Standard-Connectors registrieren."""
        try:
            from .connectors.local import LocalConnector
            self._connectors = [LocalConnector()]
        except Exception:
            self._connectors = []

    def get_connectors(self) -> list[dict[str, Any]]:
        """Connector-Status fuer UI."""
        return [c.get_status() for c in self._connectors]

    def _show_connectors(self) -> None:
        """Verfuegbare Connectors im Chat anzeigen."""
        connectors = self.get_connectors()

        parts = ["<strong>Dokumenten-Quellen:</strong><br>"]
        for c in connectors:
            status = "Verbunden" if c["connected"] else "Nicht verbunden"
            status_icon = "check_circle" if c["connected"] else "cancel"
            parts.append(
                f"• <strong>{c['name']}</strong> — {status}<br>"
                f"  {c.get('description', '')}"
            )

        parts.append("<br><br>Weitere Connectors (Google Drive, SharePoint, etc.) "
                     "koennen in zukuenftigen Versionen hinzugefuegt werden.")

        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.CONNECTOR,
            content="<br>".join(parts),
        ))

    def set_message_callback(self, cb: Callable[[ChatMessage], None]) -> None:
        """Callback fuer neue Nachrichten (UI-Update)."""
        self._on_message = cb

    # ---- Watcher ----

    def start_watcher(self) -> None:
        """Inbox-Watcher starten fuer proaktive Benachrichtigungen."""
        try:
            from ..config import load_config
            from ..watcher import start_watching, is_watching

            if is_watching():
                return

            cfg = self._cfg()

            def _on_new_file(file_path: Path) -> None:
                """Callback vom Watcher: Neue Datei erkannt."""
                logger.info("Watcher: Neue Datei erkannt: %s", file_path.name)
                # Scan triggern (beinhaltet Klassifikation + Vorschlag)
                self.scan_inbox()

            start_watching(
                cfg=cfg,
                callback=_on_new_file,
                poll_interval=5.0,
                debounce_seconds=2.0,
            )
            logger.info("Inbox-Watcher gestartet")
        except Exception as e:
            logger.warning("Watcher konnte nicht gestartet werden: %s", e)

    def shutdown(self) -> None:
        """Agent herunterfahren: Watcher stoppen."""
        try:
            from ..watcher import stop_watching
            stop_watching()
        except Exception:
            pass

    def _emit(self, msg: ChatMessage) -> None:
        """Nachricht hinzufuegen.

        Thread-safe: Kann aus ThreadPoolExecutor (run.io_bound) aufgerufen werden.
        Setzt _dirty-Flag fuer UI-Timer basierte Updates.
        Callback wird NIE direkt aufgerufen (wuerde aus Thread-Context crashen).
        """
        with self._lock:
            self.messages.append(msg)
            self._dirty = True

    # ---- Willkommen & Initialscann ----

    def initialize(self) -> None:
        """Agent starten mit Willkommensnachricht + Inbox-Scan + Watcher."""
        if self._initialized:
            return
        self._initialized = True

        self._emit(ChatMessage(
            id="welcome",
            role=MsgRole.AGENT,
            type=MsgType.WELCOME,
            content=(
                "Hallo! Ich bin dein Doc-Sorter Assistent. 👋<br><br>"
                "Du kannst einfach mit mir reden — ich verstehe natürliche Sprache:<br>"
                "• <strong>Suchen:</strong> 'Alle Rechnungen von GASAG'<br>"
                "• <strong>Inhalt lesen:</strong> 'Was steht in vertrag_coeo.pdf?'<br>"
                "• <strong>Timeline:</strong> 'Was wurde im März 2024 verarbeitet?'<br>"
                "• <strong>Grafiken:</strong> 'Zeig mir eine Grafik nach Dokumententyp'<br>"
                "• <strong>Statistiken:</strong> 'Wie viele Rechnungen gibt es?'<br><br>"
                "Oder klick einfach einen der Buttons unten."
            ),
            actions=[
                Action(id="scan", label="Inbox scannen", icon="search",
                       variant="primary", callback_key="rescan"),
                Action(id="stats", label="Statistiken", icon="analytics",
                       variant="secondary", callback_key="show_chart_timeline"),
                Action(id="help", label="Was kann ich?", icon="help_outline",
                       variant="ghost", callback_key="show_help_cmd"),
            ],
        ))

        # Sofort Inbox scannen
        self.scan_inbox()

        # Watcher starten fuer proaktive Erkennung
        self.start_watcher()

    # ---- File Upload ----

    def handle_file_upload(self, uploaded_paths: list[Path]) -> None:
        """Hochgeladene Dateien bestaetigen und Inbox neu scannen.

        Nutzt Batch-Emit: Callback wird waehrend der gesamten Operation
        unterdrueckt und erst am Ende einmal ausgeloest, um Race Conditions
        bei multiplen _refresh_chat() Aufrufen zu vermeiden.
        """
        self._suppress_callback = True
        try:
            names = [p.name for p in uploaded_paths]
            n = len(names)
            if n == 1:
                content = f"Datei <strong>{names[0]}</strong> in die Inbox hochgeladen."
            else:
                items = "".join(f"<br>• {name}" for name in names)
                content = f"<strong>{n} Dateien</strong> in die Inbox hochgeladen:{items}"

            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.INFO,
                content=content,
            ))

            # Sofort scannen (generiert weitere Messages)
            self.scan_inbox()
        finally:
            self._suppress_callback = False

        # Einmal finales UI-Update ausloesen
        if self._on_message and self.messages:
            self._on_message(self.messages[-1])

    # ---- Inbox scannen ----

    def scan_inbox(self) -> list[FileRef]:
        """Inbox scannen, klassifizieren, Vorschlag generieren."""
        try:
            from ..config import load_config, get_file_types
            from ..config import get_document_type_keywords, get_known_customers, get_country_keywords
            from ..reader import read_text
            from ..classifier import classify
            from ..config import get_ocr_languages

            cfg = self._cfg()
            inbox = Path(cfg["paths"]["inbox"])
            allowed = get_file_types(cfg)

            if not inbox.exists():
                self._emit(ChatMessage(
                    id="",
                    role=MsgRole.AGENT,
                    type=MsgType.INFO,
                    content="Inbox-Ordner existiert nicht. Bitte in den Einstellungen konfigurieren.",
                ))
                return []

            files = [
                f for f in inbox.rglob("*")
                if f.is_file() and not f.is_symlink() and f.suffix.lower() in allowed
            ]

            if not files:
                self._emit(ChatMessage(
                    id="",
                    role=MsgRole.AGENT,
                    type=MsgType.INFO,
                    content="Inbox ist leer. Sobald neue Dateien hinzukommen, analysiere ich sie automatisch.",
                ))
                return []

            # Dateien klassifizieren
            file_refs: list[FileRef] = []
            doc_kw = get_document_type_keywords(cfg)
            customers = get_known_customers(cfg)
            country_kw = get_country_keywords(cfg)
            ocr_langs = get_ocr_languages(cfg)
            ocr_cfg = cfg.get("ocr", {})

            for f in files:
                try:
                    text = read_text(
                        f,
                        ocr_languages=ocr_langs,
                        ocr_dpi=ocr_cfg.get("dpi", 200),
                        max_pages=ocr_cfg.get("max_pages", 5),
                    )
                    cls = classify(
                        text=text,
                        document_type_keywords=doc_kw,
                        known_customers=customers,
                        country_keywords=country_kw,
                    )

                    stat = f.stat()
                    size_kb = stat.st_size / 1024
                    size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"

                    file_refs.append(FileRef(
                        path=str(f),
                        name=f.name,
                        size_str=size_str,
                        doc_type=cls.dokumentenart,
                        customer=cls.kunde,
                        country=cls.land,
                        datum=cls.datum,
                        datum_full=cls.datum_full,
                        jahr=cls.jahr,
                        unsicher=cls.unsicher,
                        confidence=cls.confidence,
                        reasons=cls.unsicher_gruende,
                    ))
                except Exception as e:
                    logger.warning("Fehler bei %s: %s", f.name, e)
                    file_refs.append(FileRef(
                        path=str(f),
                        name=f.name,
                        size_str="?",
                        reasons=[f"Lesefehler: {e}"],
                    ))

            self._pending_files = file_refs
            self._generate_suggestion(file_refs)
            return file_refs

        except Exception as e:
            logger.error("Inbox-Scan fehlgeschlagen: %s", e)
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.ERROR,
                content=f"Fehler beim Inbox-Scan: {e}",
            ))
            return []

    def _generate_suggestion(self, files: list[FileRef]) -> None:
        """Vorschlag basierend auf gescannten Dateien generieren."""
        n = len(files)
        if n == 0:
            return

        # Dateien nach Typ gruppieren
        by_type: dict[str, list[FileRef]] = {}
        uncertain: list[FileRef] = []
        for f in files:
            if f.confidence < 0.4 or f.doc_type == "unbekannt":
                uncertain.append(f)
            else:
                by_type.setdefault(f.doc_type, []).append(f)

        # Zusammenfassung bauen
        parts: list[str] = []
        parts.append(f"<strong>{n} neue Datei{'en' if n > 1 else ''}</strong> in der Inbox erkannt:")
        parts.append("")

        for dtype, flist in sorted(by_type.items()):
            conf_avg = sum(f.confidence for f in flist) / len(flist)
            conf_str = f"{conf_avg:.0%}"
            customers = list({f.customer for f in flist if f.customer != "unbekannt"})
            customer_str = f" ({', '.join(customers)})" if customers else ""
            parts.append(f"• {len(flist)}x <strong>{dtype}</strong>{customer_str} — {conf_str} Sicherheit")

        if uncertain:
            parts.append(f"• {len(uncertain)}x unsicher — zur manuellen Pruefung")

        content = "<br>".join(parts)

        # Aktionen
        actions = []
        sure_count = sum(len(fl) for fl in by_type.values())

        if sure_count > 0:
            actions.append(Action(
                id="sort_all",
                label=f"Alle sortieren ({sure_count})",
                icon="auto_awesome",
                variant="success",
                callback_key="sort_sure",
            ))

        actions.append(Action(
            id="preview",
            label="Vorschau zuerst",
            icon="visibility",
            variant="primary",
            callback_key="preview",
        ))

        if uncertain:
            actions.append(Action(
                id="show_uncertain",
                label=f"Unsichere anzeigen ({len(uncertain)})",
                icon="help_outline",
                variant="secondary",
                callback_key="show_uncertain",
            ))

        self._emit(ChatMessage(
            id="",
            role=MsgRole.AGENT,
            type=MsgType.SUGGESTION,
            content=content,
            actions=actions,
            files=files,
        ))

    # ---- Aktionen ausfuehren ----

    def execute_action(self, callback_key: str) -> None:
        """Eine bestaetigte Aktion ausfuehren."""
        if callback_key == "sort_sure":
            self._sort_sure_files()
        elif callback_key == "preview":
            self._preview_files()
        elif callback_key == "show_uncertain":
            self._show_uncertain()
        elif callback_key == "sort_single":
            # metadata enthaelt file index
            pass
        elif callback_key == "rescan":
            self.scan_inbox()
        elif callback_key == "show_files_inbox":
            self._show_files("inbox")
        elif callback_key == "show_files_archive":
            self._show_files("archive")
        elif callback_key == "show_files_review":
            self._show_files("review")
        elif callback_key == "show_history":
            self._show_history()
        elif callback_key == "show_system":
            self._show_system_info()
        elif callback_key == "show_chart_timeline":
            self._show_chart("timeline")
        elif callback_key == "show_chart_doctype":
            self._show_chart("doctype_pie")
        elif callback_key == "show_chart_customer":
            self._show_chart("customer_bar")
        elif callback_key == "show_chart_confidence":
            self._show_chart("confidence")
        elif callback_key == "show_help_cmd":
            self._show_help()
        elif callback_key.startswith("onboard_"):
            self.handle_onboarding_action(callback_key)
        elif callback_key.startswith("add_expense_"):
            file_name = callback_key.replace("add_expense_", "")
            try:
                from ..assistant_store import add_invoice
                from ..invoice_extractor import extract_invoice_data
                from ..reader import read_text
                from ..config import load_config

                cfg = self._cfg()
                inv_data = {"amount": 0.0, "date": "", "vendor": file_name, "invoice_number": "", "category": "Rechnung"}

                # Datei im Archiv suchen und Text extrahieren
                archive = Path(cfg["paths"]["archive"])
                candidates = list(archive.rglob(file_name))
                if candidates:
                    try:
                        text = read_text(candidates[0])
                        inv_data = extract_invoice_data(text, file_name)
                    except Exception:
                        pass

                inv_id = add_invoice(
                    vendor=inv_data.get("vendor") or file_name,
                    amount=inv_data.get("amount", 0.0),
                    invoice_date=inv_data.get("date", ""),
                    category=inv_data.get("category", "Rechnung"),
                    invoice_number=inv_data.get("invoice_number", ""),
                    source_file=file_name,
                )
                amt = inv_data.get("amount", 0.0)
                vendor = inv_data.get("vendor", file_name)
                msg = (
                    f"Rechnung erfasst: <b>{vendor}</b> — "
                    f"<b>{amt:.2f} €</b> ({inv_data.get('category','')}, {inv_data.get('date','')})"
                    if amt > 0 else
                    f"Rechnung für <b>{file_name}</b> angelegt. "
                    f"Betrag konnte nicht automatisch erkannt werden — bitte im Assistenten ergänzen."
                )
                self._emit(ChatMessage(
                    id=str(uuid4())[:8], role=MsgRole.AGENT, type=MsgType.RESULT,
                    content=msg,
                ))
            except Exception as e:
                self._emit(ChatMessage(
                    id=str(uuid4())[:8], role=MsgRole.AGENT, type=MsgType.ERROR,
                    content=f"Fehler beim Anlegen der Rechnung: {e}",
                ))
        else:
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.ERROR,
                content=f"Unbekannte Aktion: {callback_key}",
            ))

    def _sort_sure_files(self) -> None:
        """Sichere Dateien automatisch sortieren."""
        try:
            from ..config import load_config
            from ..organizer import move_file
            from ..classifier import Classification
            from ..logger import LogManager, StateManager, file_hash
            from ..reader import read_text

            cfg = self._cfg()
            archive = Path(cfg["paths"]["archive"])
            logs_dir = Path(cfg["paths"]["logs"])
            state_path = archive / "_state.json"

            log_mgr = LogManager(logs_dir)
            state = StateManager(state_path)

            sure_files = [f for f in self._pending_files
                          if f.confidence >= 0.4 and f.doc_type != "unbekannt"]

            if not sure_files:
                self._emit(ChatMessage(
                    id="",
                    role=MsgRole.AGENT,
                    type=MsgType.INFO,
                    content="Keine sicheren Dateien zum Sortieren vorhanden.",
                ))
                return

            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.INFO,
                content=f"Sortiere {len(sure_files)} Dateien...",
            ))

            moved_files: list[tuple[str, str]] = []
            results: list[str] = []

            for fref in sure_files:
                source = Path(fref.path)
                if not source.exists():
                    results.append(f"• {fref.name} — uebersprungen (nicht mehr vorhanden)")
                    continue

                cls = Classification(
                    dokumentenart=fref.doc_type,
                    kunde=fref.customer,
                    land=fref.country,
                    datum=fref.datum,
                    datum_full=fref.datum_full,
                    jahr=fref.jahr,
                    unsicher=fref.unsicher,
                    unsicher_gruende=fref.reasons,
                    confidence=fref.confidence,
                )

                # Hash VOR dem Verschieben berechnen (Datei ist danach weg!)
                try:
                    sha = file_hash(source)
                except Exception:
                    sha = ""

                target, actually_moved = move_file(source, archive, cls, dry_run=False)
                if actually_moved:
                    moved_files.append((str(source), str(target)))
                    # Logging
                    try:
                        log_mgr.write_log(source, target, cls, sha, "")
                        state.mark_processed(sha, str(source), str(target), "")
                    except Exception:
                        pass
                    # Gehirn: Assistent befuellen
                    try:
                        from ..brain import process_classified_document
                        process_classified_document(
                            source_path=str(target),
                            doc_type=cls.dokumentenart,
                            customer=cls.kunde,
                            country=cls.land,
                            datum=cls.datum_full or cls.datum,
                            confidence=cls.confidence,
                        )
                    except Exception:
                        pass
                    results.append(f"• {fref.name} → <strong>{fref.doc_type}</strong>/{fref.customer}")
                else:
                    results.append(f"• {fref.name} — konnte nicht verschoben werden")

            # Undo-Eintrag
            undo_id = ""
            if moved_files:
                undo_entry = UndoEntry(
                    id=str(uuid4())[:8],
                    description=f"{len(moved_files)} Dateien sortiert",
                    moves=moved_files,
                )
                self.undo_stack.append(undo_entry)
                undo_id = undo_entry.id

            content_parts = [
                f"<strong>{len(moved_files)} von {len(sure_files)} Dateien sortiert:</strong>",
                "",
            ] + results

            uncertain = [f for f in self._pending_files
                         if f.confidence < 0.4 or f.doc_type == "unbekannt"]

            actions = []
            if undo_id:
                actions.append(Action(
                    id="undo",
                    label="Rueckgaengig",
                    icon="undo",
                    variant="ghost",
                    callback_key=f"undo_{undo_id}",
                ))
            if uncertain:
                actions.append(Action(
                    id="review",
                    label=f"{len(uncertain)} Unsichere pruefen",
                    icon="rate_review",
                    variant="secondary",
                    callback_key="show_uncertain",
                ))

            actions.append(Action(
                id="rescan",
                label="Inbox erneut scannen",
                icon="refresh",
                variant="ghost",
                callback_key="rescan",
            ))

            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.RESULT,
                content="<br>".join(content_parts),
                actions=actions,
                undoable=bool(moved_files),
            ))

            self._pending_files = uncertain

        except Exception as e:
            logger.error("Sortieren fehlgeschlagen: %s", e)
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.ERROR,
                content=f"Fehler beim Sortieren: {e}",
            ))

    def _preview_files(self) -> None:
        """Vorschau: Zeige was passieren wuerde ohne zu verschieben."""
        if not self._pending_files:
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.INFO,
                content="Keine Dateien in der Vorschau.",
            ))
            return

        parts = ["<strong>Vorschau — so wuerden die Dateien sortiert:</strong>", ""]

        for fref in self._pending_files:
            conf_pct = f"{fref.confidence:.0%}"
            if fref.doc_type == "unbekannt" or fref.confidence < 0.4:
                parts.append(
                    f"• {fref.name} → <strong>Pruefung</strong> "
                    f"({conf_pct} Sicherheit)"
                )
            else:
                target = f"{fref.doc_type}/{fref.country}/{fref.customer}/{fref.name}"
                parts.append(
                    f"• {fref.name} → <strong>{target}</strong> "
                    f"({conf_pct} Sicherheit)"
                )

        actions = [
            Action(
                id="sort_confirmed",
                label="Jetzt sortieren",
                icon="auto_awesome",
                variant="success",
                callback_key="sort_sure",
            ),
            Action(
                id="rescan",
                label="Erneut scannen",
                icon="refresh",
                variant="ghost",
                callback_key="rescan",
            ),
        ]

        self._emit(ChatMessage(
            id="",
            role=MsgRole.AGENT,
            type=MsgType.FILE_PREVIEW,
            content="<br>".join(parts),
            actions=actions,
            files=self._pending_files,
        ))

    def _show_uncertain(self) -> None:
        """Unsichere Dateien mit Inline-Review-Widgets anzeigen."""
        uncertain = [f for f in self._pending_files
                     if f.confidence < 0.4 or f.doc_type == "unbekannt"]

        if not uncertain:
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.INFO,
                content="Keine unsicheren Dateien vorhanden.",
            ))
            return

        n = len(uncertain)
        content = (
            f"<strong>{n} unsichere Datei{'en' if n > 1 else ''}</strong> gefunden. "
            f"Bitte korrigiere die Zuordnung oder sende sie zurueck in die Inbox:"
        )

        self._emit(ChatMessage(
            id="",
            role=MsgRole.AGENT,
            type=MsgType.QUESTION,
            content=content,
            files=uncertain,
            actions=[
                Action(
                    id="go_review_page",
                    label="Pruefung-Seite oeffnen",
                    icon="open_in_new",
                    variant="ghost",
                    callback_key="navigate_review",
                ),
            ],
        ))

    # ---- Review & Move ----

    def review_file(self, file_path: str, doc_type: str, customer: str, country: str) -> None:
        """Eine unsichere Datei korrigieren und ins Archiv verschieben."""
        try:
            from ..config import load_config
            from ..organizer import move_file
            from ..classifier import Classification

            cfg = self._cfg()
            archive = Path(cfg["paths"]["archive"])
            source = Path(file_path)

            if not source.exists():
                self._emit(ChatMessage(
                    id="",
                    role=MsgRole.AGENT,
                    type=MsgType.ERROR,
                    content=f"Datei nicht gefunden: {source.name}",
                ))
                return

            # Datum-Infos aus pending_files uebernehmen (sofern vorhanden)
            fref = next((f for f in self._pending_files if f.path == file_path), None)
            cls = Classification(
                dokumentenart=doc_type,
                kunde=customer,
                land=country,
                datum=fref.datum if fref else "",
                datum_full=fref.datum_full if fref else "",
                jahr=fref.jahr if fref else "",
                confidence=1.0,  # Manuell korrigiert
            )

            target, actually_moved = move_file(source, archive, cls, dry_run=False)

            if actually_moved:
                # Undo-Eintrag
                undo_entry = UndoEntry(
                    id=str(uuid4())[:8],
                    description=f"{source.name} manuell archiviert",
                    moves=[(str(source), str(target))],
                )
                self.undo_stack.append(undo_entry)

                # Aus pending entfernen
                self._pending_files = [
                    f for f in self._pending_files if f.path != file_path
                ]

                # Auch aus bestehenden QUESTION-Messages entfernen (Review-Widget aktualisieren)
                for msg in self.messages:
                    if msg.type == MsgType.QUESTION and msg.files:
                        msg.files = [f for f in msg.files if f.path != file_path]

                # Gehirn: Assistent befuellen (manuell korrigiert = Konfidenz 1.0)
                try:
                    from ..brain import process_classified_document
                    process_classified_document(
                        source_path=str(target),
                        doc_type=doc_type,
                        customer=customer,
                        country=country,
                        datum=cls.datum_full or cls.datum,
                        confidence=1.0,
                    )
                except Exception:
                    pass

                result_actions = [
                    Action(
                        id="undo",
                        label="Rueckgaengig",
                        icon="undo",
                        variant="ghost",
                        callback_key=f"undo_{undo_entry.id}",
                    ),
                ]
                self._emit(ChatMessage(
                    id="",
                    role=MsgRole.AGENT,
                    type=MsgType.RESULT,
                    content=f"<strong>{source.name}</strong> korrigiert und archiviert als "
                            f"<strong>{doc_type}</strong> / {customer} / {country}.",
                    actions=result_actions,
                ))

                # Rechnungslink: Ausgabe vorschlagen
                if doc_type and doc_type.lower() == "rechnung":
                    self._emit(ChatMessage(
                        id=str(uuid4())[:8],
                        role=MsgRole.AGENT,
                        type=MsgType.SUGGESTION,
                        content="Rechnung erkannt — Ausgabe automatisch erfassen?",
                        actions=[
                            Action(
                                id="add_expense",
                                label="Ausgabe erfassen",
                                icon="euro",
                                variant="success",
                                callback_key=f"add_expense_{source.name}",
                            ),
                        ],
                    ))
            else:
                self._emit(ChatMessage(
                    id="",
                    role=MsgRole.AGENT,
                    type=MsgType.ERROR,
                    content=f"Konnte {source.name} nicht verschieben.",
                ))

        except Exception as e:
            logger.error("Review fehlgeschlagen: %s", e)
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.ERROR,
                content=f"Fehler beim Korrigieren: {e}",
            ))

    def move_to_inbox(self, file_path: str) -> None:
        """Eine Datei zurueck in die Inbox verschieben."""
        try:
            from ..config import load_config

            cfg = self._cfg()
            inbox = Path(cfg["paths"]["inbox"])
            source = Path(file_path)

            if not source.exists():
                self._emit(ChatMessage(
                    id="",
                    role=MsgRole.AGENT,
                    type=MsgType.ERROR,
                    content=f"Datei nicht gefunden: {source.name}",
                ))
                return

            inbox.mkdir(parents=True, exist_ok=True)
            target = inbox / source.name
            shutil.move(str(source), str(target))

            # Aus pending entfernen
            self._pending_files = [
                f for f in self._pending_files if f.path != file_path
            ]

            # Auch aus bestehenden QUESTION-Messages entfernen
            for msg in self.messages:
                if msg.type == MsgType.QUESTION and msg.files:
                    msg.files = [f for f in msg.files if f.path != file_path]

            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.RESULT,
                content=f"<strong>{source.name}</strong> zurueck in die Inbox verschoben.",
                actions=[
                    Action(
                        id="rescan",
                        label="Inbox scannen",
                        icon="refresh",
                        variant="primary",
                        callback_key="rescan",
                    ),
                ],
            ))

        except Exception as e:
            logger.error("Move to inbox fehlgeschlagen: %s", e)
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.ERROR,
                content=f"Fehler: {e}",
            ))

    # ---- Undo ----

    def undo_last(self, undo_id: str = "") -> None:
        """Letzte Operation rueckgaengig machen."""
        if not self.undo_stack:
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.INFO,
                content="Nichts zum Rueckgaengig-Machen vorhanden.",
            ))
            return

        if undo_id:
            entry = next((e for e in self.undo_stack if e.id == undo_id), None)
            if not entry:
                self._emit(ChatMessage(
                    id="",
                    role=MsgRole.AGENT,
                    type=MsgType.ERROR,
                    content="Undo-Eintrag nicht gefunden.",
                ))
                return
            self.undo_stack.remove(entry)
        else:
            entry = self.undo_stack.pop()

        restored = 0
        for src_str, dest_str in entry.moves:
            dest = Path(dest_str)
            src = Path(src_str)
            if dest.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(dest), str(src))
                    restored += 1
                except OSError as e:
                    logger.warning("Undo fehlgeschlagen fuer %s: %s", dest, e)

        self._emit(ChatMessage(
            id="",
            role=MsgRole.AGENT,
            type=MsgType.RESULT,
            content=f"<strong>Rueckgaengig:</strong> {restored} von {len(entry.moves)} Dateien "
                    f"zurueck in die Inbox verschoben.",
            actions=[
                Action(
                    id="rescan",
                    label="Inbox scannen",
                    icon="refresh",
                    variant="primary",
                    callback_key="rescan",
                ),
            ],
        ))

    # ---- User-Nachrichten verarbeiten ----

    def handle_user_message(self, text: str) -> None:
        """Freitext vom User verarbeiten – konversationell + faktbasiert."""
        self._emit(ChatMessage(id="", role=MsgRole.USER, type=MsgType.TEXT, content=text))
        lower = text.lower().strip()

        # --- Konversation ---
        if _is_greeting(lower):
            self._handle_greeting(); return
        if _is_thanks(lower):
            self._handle_thanks(); return
        if _is_wellbeing(lower):
            self._handle_wellbeing(); return
        if _is_affirmation(lower):
            self._handle_affirmation(); return
        if _is_negation(lower):
            self._handle_negation(); return
        if _is_help_request(lower):
            self._handle_how_it_works(); return

        # --- Dokument-Inhalt lesen ---
        if any(p in lower for p in [
            "was steht in", "was steht da", "inhalt von", "zeig den inhalt",
            "lese die datei", "öffne die datei", "zeig mir die datei", "was ist in der",
        ]):
            self._handle_read_document(text); return

        # --- Archiv durchsuchen (mit Suchbegriffen) ---
        if any(p in lower for p in [
            "suche nach", "finde", "suche alle", "zeig alle", "zeige alle",
            "alle rechnungen", "alle verträge", "alle vertraege",
            "wo ist", "gibt es einen", "gibt es eine",
        ]):
            self._handle_archive_search(lower, text); return

        # --- Timeline (Datum erwähnt oder explizit) ---
        date_hint = _extract_date_filter(lower)
        if date_hint or any(p in lower for p in [
            "timeline", "zeitverlauf", "zeitstrahl", "wann wurde", "wann war",
            "was passierte", "was wurde", "zeig verlauf",
        ]):
            self._handle_timeline_query(lower, date_hint); return

        # --- Grafik / Chart ---
        if any(p in lower for p in [
            "als graph", "als grafik", "als diagramm", "als chart",
            "visualisier", "zeig grafik", "zeig diagramm", "zeig chart",
        ]):
            self._handle_chart_request(lower); return

        # --- Statistik-Fragen ---
        if any(p in lower for p in [
            "wie viele", "wieviele", "wie viel", "wie oft", "anzahl",
            "wie groß ist", "wie gross ist", "zähle", "zaehle",
        ]):
            self._handle_stats_query(lower); return

        # --- Bestehende Aktions-Intents ---
        if any(w in lower for w in ["scan", "prüf", "pruef", "neue datei", "neue dateien"]):
            self.scan_inbox(); return
        if any(w in lower for w in ["sortier", "verschieb", "jetzt sortier"]):
            self._sort_sure_files(); return
        if any(w in lower for w in ["vorschau", "preview"]):
            self._preview_files(); return
        if any(w in lower for w in ["rückg", "rueckg", "undo", "rückgängig", "rueckgaengig"]):
            self.undo_last(); return
        if any(w in lower for w in ["unsicher", "pruefung", "prüfung", "review"]):
            self._show_uncertain(); return
        if any(w in lower for w in ["chart", "diagramm", "grafik", "graph"]):
            self._handle_chart_request(lower); return
        if any(w in lower for w in ["analyse", "analytics", "statistik"]):
            self._show_analytics_summary(); return
        if any(w in lower for w in ["history", "historie", "verlauf", "log"]):
            self._handle_timeline_query(lower, None); return
        if any(w in lower for w in ["system", "health", "version"]):
            self._show_system_info(); return
        if any(w in lower for w in ["connector", "quelle", "verbindung", "sharepoint", "google drive"]):
            self._show_connectors(); return
        if any(w in lower for w in ["einstellung", "config", "setup", "konfigur"]):
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.INFO,
                content="Öffne die <strong>Einstellungen</strong> für erweiterte Konfiguration.",
                actions=[Action(id="cfg", label="Einstellungen öffnen", icon="tune",
                               variant="primary", callback_key="navigate_config")])); return
        if any(w in lower for w in ["hilfe", "help", "was kannst du", "kommandos", "befehle"]):
            self._show_help(); return
        if any(w in lower for w in ["status", "übersicht", "uebersicht"]):
            self._show_status(); return
        if "inbox" in lower:
            self._show_files("inbox"); return
        if "archiv" in lower:
            self._show_files("archive"); return

        # --- Fallback: intelligenter Hinweis ---
        self._handle_unknown(lower)

    # ---- Konversation ---

    def _handle_greeting(self) -> None:
        responses = [
            "Hallo! 👋 Wie kann ich dir helfen? Ich kann Dokumente suchen, Statistiken zeigen oder die Inbox scannen.",
            "Hi! Was kann ich heute für dich tun?",
            "Hey! Schreib mir einfach was du brauchst — ich kümmere mich darum.",
            "Ey, na! 👋 Was kann ich für dich tun?",
            "Jo, bin da! Was brauchst du?",
            "Na, alles klar? Sag mir einfach was ansteht! 😄",
            "Hey hey! Was geht? Ich bin startklar. 🚀",
        ]
        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.TEXT,
            content=_random.choice(responses),
            actions=[
                Action(id="scan", label="Inbox scannen", icon="search",
                       variant="primary", callback_key="rescan"),
                Action(id="stats", label="Statistiken", icon="analytics",
                       variant="secondary", callback_key="show_chart_timeline"),
                Action(id="help", label="Was kann ich?", icon="help_outline",
                       variant="ghost", callback_key="show_help_cmd"),
            ],
        ))

    def _handle_thanks(self) -> None:
        responses = [
            "Gerne! Noch etwas?",
            "Immer gerne! Falls du noch etwas brauchst — ich bin hier.",
            "Kein Problem! Was kann ich sonst noch für dich tun?",
            "Safe! Wenn du noch was brauchst — einfach sagen. 😄",
            "Jo, gerne! Was noch?",
            "Alles klar, kein Stress! Noch was?",
        ]
        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.TEXT,
            content=_random.choice(responses),
        ))

    def _handle_wellbeing(self) -> None:
        responses = [
            "Läuft! 😄 Ich bin ein Dokument-Bot — alles im grünen Bereich. Was kann ich für dich tun?",
            "Alles fit! 💪 Bereit für Dokumente, Suche oder Statistiken — was brauchst du?",
            "Bestens! 🤖 Dateien scannen, sortieren, suchen — ich bin startklar. Was geht?",
            "Danke der Nachfrage — läuft bei mir! Was kann ich für dich erledigen?",
            "Voll im Flow! Was steht an?",
            "Ey, alles safe hier! 😎 Dokumente sortieren, suchen, scannen — sag's mir!",
            "Jo, läuft mega! 💪 Was kann ich für dich tun?",
            "Alles geil, bin ready! Was geht?",
        ]
        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.TEXT,
            content=_random.choice(responses),
        ))

    def _handle_affirmation(self) -> None:
        responses = [
            "Alles klar! Was soll ich als nächstes tun?",
            "Super, auf gehts! Womit soll ich anfangen?",
            "Verstanden! Was kann ich für dich tun?",
            "Prima! Sag mir einfach was du brauchst.",
        ]
        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.TEXT,
            content=_random.choice(responses),
            actions=[
                Action(id="scan", label="Inbox scannen", icon="search",
                       variant="primary", callback_key="rescan"),
                Action(id="help", label="Was kann ich?", icon="help_outline",
                       variant="ghost", callback_key="show_help_cmd"),
            ],
        ))

    def _handle_negation(self) -> None:
        responses = [
            "Kein Problem! Sag mir einfach was du stattdessen brauchst.",
            "Alright, kein Stress. Was soll ich tun?",
            "Verstanden — was kann ich sonst für dich tun?",
            "Okay, kein Problem! Einfach schreiben wenn du etwas brauchst.",
        ]
        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.TEXT,
            content=_random.choice(responses),
        ))

    def _handle_how_it_works(self) -> None:
        """Erklärt den Archiv-Chat in einfachen Worten."""
        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.INFO,
            content=(
                "<strong>Ich bin der Archiv-Chat</strong> — dein Assistent für "
                "Dokumente. So funktioniere ich:<br><br>"
                "📥 <strong>Inbox scannen:</strong> Ich schaue in deinen Eingangsordner "
                "und erkenne automatisch was dort liegt — Rechnungen, Verträge, "
                "Angebote und mehr.<br><br>"
                "📂 <strong>Sortieren:</strong> Erkannte Dokumente sortiere ich nach "
                "Typ, Kunde und Land ins Archiv. Du bestätigst, ich erledige den Rest.<br><br>"
                "🔍 <strong>Fragen stellen:</strong> Du kannst mich fragen — "
                "<em>Wie viele Rechnungen gibt es?</em>, "
                "<em>Was wurde im März verarbeitet?</em> oder "
                "<em>Zeig mir eine Grafik nach Kunde</em>.<br><br>"
                "📖 <strong>Dateien lesen:</strong> Mit <em>Was steht in rechnung.pdf?</em> "
                "lese ich dir den Inhalt einer Datei aus dem Archiv vor.<br><br>"
                "Einfach drauflosschreiben — ich verstehe auch normale Sätze."
            ),
            actions=[
                Action(id="scan", label="Inbox scannen", icon="search",
                       variant="primary", callback_key="rescan"),
                Action(id="help", label="Alle Funktionen", icon="help_outline",
                       variant="ghost", callback_key="show_help_cmd"),
            ],
        ))

    # ---- Dokument-Inhalt lesen ----

    def _handle_read_document(self, text: str) -> None:
        """Dateiinhalt aus dem Archiv lesen und als Vorschau zeigen."""
        lower = text.lower()
        # Dateinamen oder Suchbegriff extrahieren
        quoted = _re.search(r'["\']([^"\']+)["\']', text)
        ext_match = _re.search(r'(\S+\.(?:pdf|docx|txt|png|jpg|tif|md))', text, _re.IGNORECASE)
        if quoted:
            keyword = quoted.group(1)
        elif ext_match:
            keyword = ext_match.group(1)
        else:
            # Stopwörter entfernen, Rest als Suchbegriff
            stopwords = {
                "was", "steht", "in", "der", "die", "das", "von", "inhalt",
                "zeig", "mir", "datei", "öffne", "lese", "dem", "einem",
                "einer", "eine", "ein", "ist", "sind", "auch",
            }
            words = [w for w in lower.split() if w not in stopwords and len(w) > 2]
            keyword = " ".join(words[:3]) if words else ""

        if not keyword:
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.TEXT,
                content="Welche Datei meinst du? Z.B.: <em>'Was steht in rechnung_gasag.pdf?'</em>",
            ))
            return

        try:
            from ..config import load_config, get_ocr_languages
            from ..reader import read_text

            cfg = self._cfg()
            search_dirs = [
                Path(cfg["paths"]["archive"]),
                Path(cfg["paths"]["inbox"]),
            ]

            kw = keyword.lower()
            found: list[Path] = []
            for d in search_dirs:
                if d.exists():
                    for f in d.rglob("*"):
                        if f.is_file() and kw in f.name.lower():
                            found.append(f)

            if not found:
                # Auch nach Inhalt in Ordnerpfad suchen
                for d in search_dirs:
                    if d.exists():
                        for f in d.rglob("*"):
                            if f.is_file() and kw in str(f.relative_to(d)).lower():
                                found.append(f)

            if not found:
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INFO,
                    content=f"Keine Datei mit '<strong>{keyword}</strong>' gefunden.",
                    actions=[
                        Action(id="arc", label="Archiv anzeigen", icon="folder_open",
                               variant="secondary", callback_key="show_files_archive"),
                    ],
                ))
                return

            f = found[0]
            try:
                raw = read_text(
                    f,
                    ocr_languages=get_ocr_languages(cfg),
                    ocr_dpi=cfg.get("ocr", {}).get("dpi", 200),
                    max_pages=2,
                )
                lines = [l.strip() for l in raw.splitlines() if l.strip()]
                preview = "\n".join(lines[:25])
                if len(preview) > 700:
                    preview = preview[:700] + "…"

                more_hint = (
                    f"<br><span style='font-size:0.72rem;color:var(--ds-text-2)'>"
                    f"… und {len(found) - 1} weitere Treffer</span>"
                    if len(found) > 1 else ""
                )
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.FILE_PREVIEW,
                    content=(
                        f"<strong>{f.name}</strong><br>"
                        f"<span style='font-size:0.72rem;color:var(--ds-text-2)'>"
                        f"{f.parent}</span><br><br>"
                        f"<pre style='font-size:0.78rem;white-space:pre-wrap;"
                        f"color:var(--ds-text);max-height:320px;overflow:auto'>"
                        f"{preview}</pre>{more_hint}"
                    ),
                ))
            except Exception as e:
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                    content=f"Datei gefunden aber konnte nicht gelesen werden: {e}",
                ))

        except Exception as e:
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                content=f"Fehler bei der Dateisuche: {e}",
            ))

    # ---- Archiv durchsuchen ----

    def _handle_archive_search(self, lower: str, original: str) -> None:
        """Archiv nach Typ/Kunde/Stichwort durchsuchen."""
        try:
            from ..config import load_config, get_document_type_keywords, get_known_customers
            cfg = self._cfg()
            archive = Path(cfg["paths"]["archive"])

            # Dokumentenart erkennen
            doc_kw = get_document_type_keywords(cfg)
            matched_type: str | None = None
            for dtype, keywords in doc_kw.items():
                if dtype.lower() in lower or any(kw.lower() in lower for kw in keywords):
                    matched_type = dtype
                    break

            # Kunde erkennen
            customers = get_known_customers(cfg)
            matched_customer: str | None = None
            for c in customers:
                aliases = [c["name"]] + c.get("aliases", [])
                if any(a.lower() in lower for a in aliases):
                    matched_customer = c["name"]
                    break

            if not matched_type and not matched_customer:
                # Generische Suche: Schlüsselwörter aus Nachricht
                stopwords = {
                    "suche", "finde", "nach", "alle", "zeig", "zeige", "gibt",
                    "wo", "ist", "sind", "ein", "eine", "der", "die", "das",
                    "von", "für", "fuer", "nach", "mit",
                }
                words = [w for w in lower.split() if w not in stopwords and len(w) > 2]
                keyword = " ".join(words[:3])
                if keyword:
                    # Fallback: Dateinamen-Suche
                    found: list[dict] = []
                    if archive.exists():
                        for f in archive.rglob("*"):
                            if f.is_file() and keyword in f.name.lower():
                                stat = f.stat()
                                found.append({
                                    "name": f.name,
                                    "path": str(f),
                                    "size": f"{stat.st_size / 1024:.0f} KB",
                                    "relative": str(f.relative_to(archive)),
                                    "suffix": f.suffix.lower(),
                                })
                    if found:
                        self._emit(ChatMessage(
                            id="", role=MsgRole.AGENT, type=MsgType.FILE_LIST,
                            content=f"<strong>{len(found)} Treffer</strong> für '<strong>{keyword}</strong>':",
                            metadata={"files": found[:30], "folder_label": keyword},
                        ))
                    else:
                        self._emit(ChatMessage(
                            id="", role=MsgRole.AGENT, type=MsgType.INFO,
                            content=f"Keine Treffer für '<strong>{keyword}</strong>' im Archiv.",
                            actions=[Action(id="arc", label="Archiv anzeigen", icon="folder_open",
                                           variant="secondary", callback_key="show_files_archive")],
                        ))
                else:
                    self._show_files("archive")
                return

            # Gefilterte Archiv-Suche
            if not archive.exists():
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INFO,
                    content="Archiv ist leer oder nicht gefunden.",
                ))
                return

            files_data: list[dict] = []
            for f in archive.rglob("*"):
                if not f.is_file():
                    continue
                rel = str(f.relative_to(archive)).lower()
                type_ok = not matched_type or matched_type.lower() in rel
                cust_ok = not matched_customer or matched_customer.lower() in rel
                if type_ok and cust_ok:
                    stat = f.stat()
                    files_data.append({
                        "name": f.name,
                        "path": str(f),
                        "size": f"{stat.st_size / 1024:.0f} KB",
                        "relative": str(f.relative_to(archive)),
                        "suffix": f.suffix.lower(),
                    })

            filter_parts = []
            if matched_type:
                filter_parts.append(f"Typ: <strong>{matched_type}</strong>")
            if matched_customer:
                filter_parts.append(f"Kunde: <strong>{matched_customer}</strong>")
            label = " · ".join(filter_parts)

            if not files_data:
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INFO,
                    content=f"Keine archivierten Dateien gefunden für {label}.",
                ))
                return

            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.FILE_LIST,
                content=f"<strong>{len(files_data)} Dateien</strong> gefunden — {label}:",
                metadata={"files": files_data[:30], "folder_label": " ".join(filter_parts)},
            ))

        except Exception as e:
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                content=f"Suche fehlgeschlagen: {e}",
            ))

    # ---- Timeline-Abfragen ----

    def _handle_timeline_query(self, lower: str, date_hint: str | None) -> None:
        """History nach Datum filtern oder Zeitverlaufs-Chart zeigen."""
        wants_chart = any(w in lower for w in ["chart", "graph", "grafik", "diagramm", "zeitstrahl"])

        if wants_chart and not date_hint:
            self._show_chart("timeline")
            return

        if date_hint:
            self._show_history_filtered(date_hint)
            if wants_chart:
                self._show_chart("timeline")
        else:
            # Allgemeiner Verlauf
            self._show_history()

    def _show_history_filtered(self, date_raw: str) -> None:
        """History auf eine Datumserwähnung filtern."""
        try:
            from ..config import load_config
            from ..logger import LogManager

            cfg = self._cfg()
            logs_dir = Path(cfg["paths"]["logs"])

            if not logs_dir.exists():
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INFO,
                    content="Noch keine History vorhanden.",
                ))
                return

            log_mgr = LogManager(logs_dir)
            all_logs = log_mgr.get_all_logs()

            # Filter: Datum-String in ISO-Timestamp suchen
            d = date_raw.lower().strip()
            filtered = [
                log for log in all_logs
                if d in log.get("timestamp", "").lower()[:10]
                or (len(d) >= 4 and d[:4] in log.get("timestamp", "")[:4])  # Jahr
                or d in log.get("timestamp", "").lower()
            ]

            if not filtered:
                # Wochentage / Monatsnamen auflösen
                month_map = {
                    "januar": "01", "februar": "02", "märz": "03", "maerz": "03",
                    "april": "04", "mai": "05", "juni": "06", "juli": "07",
                    "august": "08", "september": "09", "oktober": "10",
                    "november": "11", "dezember": "12",
                }
                for month, num in month_map.items():
                    if month in d:
                        filtered = [
                            log for log in all_logs
                            if f"-{num}-" in log.get("timestamp", "")
                        ]
                        break

            if not filtered:
                filtered = sorted(all_logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
                content = (
                    f"Keine Einträge für '<strong>{date_raw}</strong>' gefunden. "
                    f"Zeige die letzten Einträge:"
                )
            else:
                filtered = sorted(filtered, key=lambda x: x.get("timestamp", ""), reverse=True)
                content = f"<strong>{len(filtered)} Einträge</strong> für '<strong>{date_raw}</strong>':"

            entries = [
                {
                    "timestamp": log.get("timestamp", ""),
                    "source": Path(log.get("source", "")).name if log.get("source") else "?",
                    "target": Path(log.get("target", "")).name if log.get("target") else "?",
                    "doc_type": log.get("dokumentenart", "unbekannt"),
                    "customer": log.get("kunde", "unbekannt"),
                    "country": log.get("land", "unbekannt"),
                    "confidence": log.get("confidence", 0),
                }
                for log in filtered[:20]
            ]

            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.HISTORY,
                content=content,
                metadata={"entries": entries},
            ))

        except Exception as e:
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                content=f"Fehler beim Laden der History: {e}",
            ))

    # ---- Chart-Anfragen ----

    def _handle_chart_request(self, lower: str) -> None:
        """Natural-Language Chart-Auswahl."""
        if any(w in lower for w in ["typ", "art", "dokumentenart", "dokumententyp", "welche arten"]):
            self._show_chart("doctype_pie")
        elif any(w in lower for w in ["kunde", "kunden", "auftraggeber", "lieferant"]):
            self._show_chart("customer_bar")
        elif any(w in lower for w in ["sicherheit", "confidence", "genauigkeit", "treffsicher"]):
            self._show_chart("confidence")
        elif any(w in lower for w in ["monat", "zeitverlauf", "verlauf", "datum", "wann", "timeline"]):
            self._show_chart("timeline")
        else:
            # Alle Charts anbieten
            self._show_chart("timeline")
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.TEXT,
                content="Welche Grafik interessiert dich?",
                actions=[
                    Action(id="c1", label="Zeitverlauf", icon="timeline",
                           variant="primary", callback_key="show_chart_timeline"),
                    Action(id="c2", label="Nach Dokumententyp", icon="pie_chart",
                           variant="secondary", callback_key="show_chart_doctype"),
                    Action(id="c3", label="Nach Kunde", icon="bar_chart",
                           variant="secondary", callback_key="show_chart_customer"),
                    Action(id="c4", label="Erkennungs-Sicherheit", icon="speed",
                           variant="ghost", callback_key="show_chart_confidence"),
                ],
            ))

    # ---- Statistik-Fragen ----

    def _handle_stats_query(self, lower: str) -> None:
        """Faktbasierte Statistik-Antwort ohne Halluzination."""
        try:
            from ..config import load_config, get_document_type_keywords, get_known_customers
            from ..logger import LogManager

            cfg = self._cfg()
            logs_dir = Path(cfg["paths"]["logs"])

            doc_type_counts: dict[str, int] = {}
            customer_counts: dict[str, int] = {}

            if logs_dir.exists():
                log_mgr = LogManager(logs_dir)
                for log in log_mgr.get_all_logs():
                    dt = log.get("dokumentenart", "unbekannt")
                    ku = log.get("kunde", "unbekannt")
                    doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1
                    customer_counts[ku] = customer_counts.get(ku, 0) + 1

            total = sum(doc_type_counts.values())

            # Fragt der User nach einem bestimmten Typ?
            doc_kw = get_document_type_keywords(cfg)
            asked_type: str | None = None
            for dtype in doc_type_counts:
                if dtype.lower() in lower:
                    asked_type = dtype
                    break
            if not asked_type:
                for dtype, keywords in doc_kw.items():
                    if any(kw.lower() in lower for kw in keywords):
                        asked_type = dtype
                        break

            # Fragt der User nach einem bestimmten Kunden?
            customers = get_known_customers(cfg)
            asked_customer: str | None = None
            for c in customers:
                aliases = [c["name"]] + c.get("aliases", [])
                if any(a.lower() in lower for a in aliases):
                    asked_customer = c["name"]
                    break

            if asked_type:
                cnt = doc_type_counts.get(asked_type, 0)
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.TEXT,
                    content=f"Es gibt <strong>{cnt}</strong> archivierte Dokumente vom Typ "
                            f"<strong>{asked_type}</strong>.",
                    actions=[
                        Action(id="show", label=f"Alle {asked_type} anzeigen", icon="folder_open",
                               variant="secondary", callback_key="show_files_archive"),
                    ] if cnt > 0 else [],
                ))
            elif asked_customer:
                cnt = customer_counts.get(asked_customer, 0)
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.TEXT,
                    content=f"Von <strong>{asked_customer}</strong> gibt es "
                            f"<strong>{cnt}</strong> archivierte Dokumente.",
                ))
            else:
                # Allgemeine Übersicht
                if not total:
                    self._emit(ChatMessage(
                        id="", role=MsgRole.AGENT, type=MsgType.INFO,
                        content="Noch keine archivierten Dokumente. Sortiere Dateien um Statistiken zu sehen.",
                        actions=[Action(id="scan", label="Inbox scannen", icon="search",
                                       variant="primary", callback_key="rescan")],
                    ))
                    return

                parts = [f"<strong>Insgesamt {total} archivierte Dokumente:</strong>"]
                for dt, cnt in sorted(doc_type_counts.items(), key=lambda x: -x[1])[:6]:
                    parts.append(f"• {dt}: <strong>{cnt}</strong>")

                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INSIGHT,
                    content="<br>".join(parts),
                    actions=[
                        Action(id="chart", label="Als Diagramm", icon="pie_chart",
                               variant="secondary", callback_key="show_chart_doctype"),
                    ],
                ))

        except Exception as e:
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                content=f"Statistiken konnten nicht geladen werden: {e}",
            ))

    # ---- Fallback ----

    def _handle_unknown(self, lower: str) -> None:
        """Intelligenter Fallback basierend auf erkannten Schlüsselwörtern."""
        hint = ""
        if any(ext in lower for ext in [".pdf", ".docx", ".txt", ".png"]):
            hint = "<br>💡 Meinst du eine Datei? Probier: <em>'Was steht in [Dateiname]'</em>"
        elif _re.search(r'\d{4}', lower):
            hint = "<br>💡 Meinst du etwas mit einem Datum? Probier: <em>'Was wurde im Januar 2024 verarbeitet?'</em>"
        elif any(w in lower for w in ["wie", "wann", "was", "wer", "wo"]):
            hint = "<br>💡 Du kannst Fragen stellen wie: <em>'Wie viele Rechnungen gibt es?'</em>"

        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.TEXT,
            content=(
                "Das habe ich leider nicht verstanden. Ich kann dir helfen mit:<br><br>"
                "📄 <strong>Aktionen:</strong> 'Inbox scannen' · 'Sortieren' · 'Vorschau'<br>"
                "🔍 <strong>Suchen:</strong> 'Alle Rechnungen' · 'Finde Dokumente von GASAG'<br>"
                "📊 <strong>Statistiken:</strong> 'Wie viele Rechnungen?' · 'Zeig Grafik'<br>"
                "📅 <strong>Timeline:</strong> 'Was wurde am 15.03.2024 verarbeitet?'<br>"
                "📖 <strong>Inhalt:</strong> 'Was steht in rechnung_gasag.pdf?'"
                + hint
            ),
            actions=[
                Action(id="help", label="Alle Funktionen", icon="help_outline",
                       variant="ghost", callback_key="show_help_cmd"),
                Action(id="scan", label="Inbox scannen", icon="search",
                       variant="primary", callback_key="rescan"),
            ],
        ))

    def _show_help(self) -> None:
        """Hilfe anzeigen."""
        self._emit(ChatMessage(
            id="",
            role=MsgRole.AGENT,
            type=MsgType.INFO,
            content=(
                "<strong>Was ich für dich tun kann:</strong><br><br>"
                "🗣️ <strong>Konversation</strong> (einfach schreiben):<br>"
                "• 'Hallo' · 'Danke' · 'Wie geht es dir?'<br><br>"
                "📄 <strong>Dokumente verwalten:</strong><br>"
                "• <strong>Inbox scannen</strong> — Neue Dateien prüfen<br>"
                "• <strong>Sortieren</strong> — Erkannte Dateien archivieren<br>"
                "• <strong>Vorschau</strong> — Was würde passieren?<br>"
                "• <strong>Rückgängig</strong> — Letzte Sortierung rückgängig<br><br>"
                "🔍 <strong>Suchen &amp; Lesen:</strong><br>"
                "• 'Suche alle Rechnungen' — Archiv nach Typ filtern<br>"
                "• 'Alle Dokumente von GASAG' — Nach Kunde filtern<br>"
                "• 'Was steht in rechnung.pdf?' — Dateiinhalt lesen<br><br>"
                "📊 <strong>Statistiken &amp; Grafiken:</strong><br>"
                "• 'Wie viele Rechnungen gibt es?' — Faktbasierte Antwort<br>"
                "• 'Zeig Grafik nach Dokumententyp' — Kreisdiagramm<br>"
                "• 'Zeig Zeitverlauf als Chart' — Timeline-Grafik<br><br>"
                "📅 <strong>Timeline:</strong><br>"
                "• 'Was wurde am 15.03.2024 verarbeitet?'<br>"
                "• 'Zeig Verlauf vom letzten Monat'<br><br>"
                "📎 Dateien per Clip-Button hochladen — ich analysiere sie automatisch!"
            ),
        ))

    def _show_status(self) -> None:
        """Aktuellen Status anzeigen."""
        try:
            from ..config import load_config, get_file_types

            cfg = self._cfg()
            inbox = Path(cfg["paths"]["inbox"])
            archive = Path(cfg["paths"]["archive"])
            review = Path(cfg["paths"].get("review", str(archive / "_review")))
            allowed = get_file_types(cfg)

            inbox_count = sum(1 for f in inbox.rglob("*")
                              if f.is_file() and f.suffix.lower() in allowed) if inbox.exists() else 0
            review_count = sum(1 for f in review.rglob("*") if f.is_file()) if review.exists() else 0

            state_path = archive / "_state.json"
            processed = 0
            if state_path.exists():
                try:
                    data = json.loads(state_path.read_text(encoding="utf-8"))
                    processed = len(data.get("processed", {}))
                except Exception:
                    pass

            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.INFO,
                content=f"<strong>Status:</strong><br><br>"
                        f"📥 Inbox: <strong>{inbox_count}</strong> Dateien<br>"
                        f"📋 Pruefung: <strong>{review_count}</strong> Dateien<br>"
                        f"✅ Verarbeitet: <strong>{processed}</strong> gesamt",
                actions=[
                    Action(id="scan", label="Inbox scannen", icon="search",
                           variant="primary", callback_key="rescan"),
                ] if inbox_count > 0 else [],
            ))

        except Exception as e:
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.ERROR,
                content=f"Status konnte nicht geladen werden: {e}",
            ))

    # ---- Analytics Summary ----

    def _show_analytics_summary(self) -> None:
        """Kompakte Analyse-Zusammenfassung im Chat."""
        try:
            from ..config import load_config, get_file_types

            cfg = self._cfg()
            archive = Path(cfg["paths"]["archive"])
            logs_dir = Path(cfg["paths"]["logs"])

            # Stats aus State
            state_path = archive / "_state.json"
            processed = 0
            if state_path.exists():
                try:
                    data = json.loads(state_path.read_text(encoding="utf-8"))
                    processed = len(data.get("processed", {}))
                except Exception:
                    pass

            # Logs auswerten fuer Top-Typen und Top-Kunden
            doc_type_counts: dict[str, int] = {}
            customer_counts: dict[str, int] = {}

            if logs_dir.exists():
                for log_file in sorted(logs_dir.glob("*.json"), reverse=True)[:50]:
                    try:
                        log_data = json.loads(log_file.read_text(encoding="utf-8"))
                        entries = log_data if isinstance(log_data, list) else [log_data]
                        for entry in entries:
                            dt = entry.get("dokumentenart", "unbekannt")
                            ku = entry.get("kunde", "unbekannt")
                            doc_type_counts[dt] = doc_type_counts.get(dt, 0) + 1
                            customer_counts[ku] = customer_counts.get(ku, 0) + 1
                    except Exception:
                        continue

            # Top-3 bauen
            top_types = sorted(doc_type_counts.items(), key=lambda x: -x[1])[:3]
            top_customers = sorted(customer_counts.items(), key=lambda x: -x[1])[:3]

            parts = [f"<strong>Analyse-Zusammenfassung:</strong><br>"]
            parts.append(f"Insgesamt <strong>{processed}</strong> Dateien verarbeitet.<br>")

            if top_types:
                parts.append("<br><strong>Top Dokumentenarten:</strong>")
                for dtype, count in top_types:
                    parts.append(f"• {dtype}: <strong>{count}</strong>")

            if top_customers:
                parts.append("<br><strong>Top Kunden:</strong>")
                for customer, count in top_customers:
                    parts.append(f"• {customer}: <strong>{count}</strong>")

            if not top_types and not top_customers:
                parts.append("<br>Noch keine Log-Daten vorhanden. "
                             "Sortiere Dateien um Statistiken zu sehen.")

            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.INSIGHT,
                content="<br>".join(parts),
                actions=[
                    Action(
                        id="open_analytics",
                        label="Detaillierte Analyse",
                        icon="analytics",
                        variant="primary",
                        callback_key="navigate_analytics",
                    ),
                    Action(
                        id="rescan",
                        label="Inbox scannen",
                        icon="search",
                        variant="ghost",
                        callback_key="rescan",
                    ),
                ],
            ))

        except Exception as e:
            self._emit(ChatMessage(
                id="",
                role=MsgRole.AGENT,
                type=MsgType.ERROR,
                content=f"Analyse konnte nicht geladen werden: {e}",
            ))

    # ---- Onboarding ----

    def _needs_onboarding(self) -> bool:
        """Pruefen ob Ersteinrichtung noetig ist."""
        try:
            from ..config import load_config
            cfg = self._cfg()
            archive = Path(cfg["paths"]["archive"])
            state_path = archive / "_state.json"
            if not state_path.exists():
                return True
            import json as _json
            data = _json.loads(state_path.read_text(encoding="utf-8"))
            return len(data.get("processed", {})) == 0
        except Exception:
            return True

    def start_onboarding(self) -> None:
        """Onboarding im Chat starten (statt Wizard-Seite)."""
        self._onboarding_step = 1
        self._emit(ChatMessage(
            id="onboard_1", role=MsgRole.AGENT, type=MsgType.ONBOARDING,
            content="<strong>Willkommen bei Doc-Sorter!</strong><br><br>"
                    "Lass uns zusammen einrichten. Zuerst: "
                    "<strong>Welche Branche</strong> passt am besten?",
            actions=[
                Action(id="t_allg", label="Allgemein", icon="folder",
                       variant="primary", callback_key="onboard_template_allgemein"),
                Action(id="t_recht", label="Rechtsanwalt", icon="gavel",
                       variant="secondary", callback_key="onboard_template_rechtsanwalt"),
                Action(id="t_arch", label="Architektur", icon="architecture",
                       variant="secondary", callback_key="onboard_template_architektur"),
            ],
        ))

    def handle_onboarding_action(self, callback_key: str) -> None:
        """Onboarding-Aktion verarbeiten."""
        if callback_key.startswith("onboard_template_"):
            template_name = callback_key.replace("onboard_template_", "")
            self._apply_onboarding_template(template_name)
        elif callback_key == "onboard_lang_de":
            self._set_onboarding_lang(["deu"])
        elif callback_key == "onboard_lang_en":
            self._set_onboarding_lang(["eng"])
        elif callback_key == "onboard_lang_de_en":
            self._set_onboarding_lang(["deu", "eng"])
        elif callback_key == "onboard_finish":
            self._finish_onboarding()
        elif callback_key == "onboard_open_config":
            # Wird in chat.py behandelt (navigate)
            pass

    def _apply_onboarding_template(self, template_name: str) -> None:
        """Branchen-Template anwenden und naechsten Step zeigen."""
        try:
            from .pages.wizard import TEMPLATES
        except ImportError:
            TEMPLATES = {}

        template = TEMPLATES.get(template_name, TEMPLATES.get("allgemein", {}))
        label = template.get("label", template_name)

        # Template in Config schreiben
        try:
            from ..config import load_config_raw, save_config
            cfg = load_config_raw()
            if "document_types" in template:
                cfg["document_types"] = template["document_types"]
            save_config(cfg)
        except Exception as e:
            logger.warning("Template konnte nicht gespeichert werden: %s", e)

        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.RESULT,
            content=f"Template <strong>{label}</strong> aktiviert!",
        ))

        # Step 2: OCR-Sprache
        self._onboarding_step = 2
        self._emit(ChatMessage(
            id="onboard_2", role=MsgRole.AGENT, type=MsgType.ONBOARDING,
            content="Welche <strong>Sprachen</strong> sollen erkannt werden?",
            actions=[
                Action(id="l_de", label="Deutsch", icon="translate",
                       variant="primary", callback_key="onboard_lang_de"),
                Action(id="l_en", label="Englisch", icon="translate",
                       variant="secondary", callback_key="onboard_lang_en"),
                Action(id="l_de_en", label="Deutsch + Englisch", icon="translate",
                       variant="secondary", callback_key="onboard_lang_de_en"),
            ],
        ))

    def _set_onboarding_lang(self, langs: list[str]) -> None:
        """OCR-Sprache setzen und finalen Step zeigen."""
        try:
            from ..config import load_config_raw, save_config
            cfg = load_config_raw()
            cfg.setdefault("ocr", {})["languages"] = langs
            save_config(cfg)
        except Exception as e:
            logger.warning("Sprache konnte nicht gespeichert werden: %s", e)

        lang_str = " + ".join(l.upper() for l in langs)
        self._emit(ChatMessage(
            id="", role=MsgRole.AGENT, type=MsgType.RESULT,
            content=f"OCR-Sprache: <strong>{lang_str}</strong> eingestellt.",
        ))

        # Step 3: Fertig
        self._onboarding_step = 3
        self._emit(ChatMessage(
            id="onboard_3", role=MsgRole.AGENT, type=MsgType.ONBOARDING,
            content="<strong>Alles eingerichtet!</strong><br><br>"
                    "Lade jetzt deine ersten Dokumente hoch ueber den "
                    "Clip-Button, oder lass mich die Inbox scannen.",
            actions=[
                Action(id="fin", label="Inbox scannen", icon="search",
                       variant="primary", callback_key="onboard_finish"),
                Action(id="cfg", label="Erweiterte Einstellungen", icon="tune",
                       variant="ghost", callback_key="onboard_open_config"),
            ],
        ))

    def _finish_onboarding(self) -> None:
        """Onboarding abschliessen und normalen Betrieb starten."""
        self._onboarding_step = 0

        # State-Datei erstellen damit is_first_run() False zurueckgibt
        try:
            from ..config import load_config
            cfg = self._cfg()
            archive = Path(cfg["paths"]["archive"])
            archive.mkdir(parents=True, exist_ok=True)
            state_path = archive / "_state.json"
            if not state_path.exists():
                import os as _os, tempfile as _tmp
                _content = '{"processed": {}}'
                _fd, _tp = _tmp.mkstemp(dir=state_path.parent, suffix=".tmp")
                try:
                    with _os.fdopen(_fd, "w", encoding="utf-8") as _f:
                        _f.write(_content)
                    _os.replace(_tp, state_path)
                except Exception:
                    Path(_tp).unlink(missing_ok=True)
                    raise
        except Exception:
            pass

        # Normal-Betrieb: Inbox scannen
        self.scan_inbox()
        self.start_watcher()

    # ---- Artifact Tracking ----

    def _add_artifact(self, title: str, atype: str, data: dict) -> str:
        """Artifact hinzufuegen und ID zurueckgeben."""
        artifact_id = str(uuid4())[:8]
        self._artifacts.append({
            "id": artifact_id,
            "title": title,
            "type": atype,  # "chart", "table", "file_list", "history"
            "data": data,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        return artifact_id

    def get_artifacts(self) -> list[dict[str, Any]]:
        """Alle Artifacts fuer das Right Panel."""
        return list(self._artifacts)

    # ---- Files anzeigen ----

    def _show_files(self, folder: str = "inbox") -> None:
        """Dateien aus Inbox/Archive/Review als FILE_LIST Message."""
        try:
            from ..config import load_config, get_file_types

            cfg = self._cfg()
            archive = Path(cfg["paths"]["archive"])

            folder_map = {
                "inbox": Path(cfg["paths"]["inbox"]),
                "archive": archive,
                "review": Path(cfg["paths"].get("review", str(archive / "_review"))),
            }

            target_path = folder_map.get(folder, folder_map["inbox"])
            folder_label = {"inbox": "Inbox", "archive": "Archiv", "review": "Pruefung"}.get(folder, folder)

            if not target_path.exists():
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INFO,
                    content=f"{folder_label}-Ordner existiert nicht.",
                ))
                return

            allowed = get_file_types(cfg) if folder == "inbox" else None
            files_data = []

            for f in sorted(target_path.rglob("*")):
                if not f.is_file():
                    continue
                if allowed and f.suffix.lower() not in allowed:
                    continue
                stat = f.stat()
                size_kb = stat.st_size / 1024
                size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
                rel_path = f.relative_to(target_path)
                files_data.append({
                    "name": f.name,
                    "path": str(f),
                    "size": size_str,
                    "relative": str(rel_path),
                    "suffix": f.suffix.lower(),
                })

            if not files_data:
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INFO,
                    content=f"{folder_label} ist leer.",
                ))
                return

            content = f"<strong>{len(files_data)} Dateien</strong> in {folder_label}:"
            artifact_id = self._add_artifact(f"{folder_label} ({len(files_data)})", "file_list", {"files": files_data})

            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.FILE_LIST,
                content=content,
                metadata={"files": files_data, "folder": folder, "folder_label": folder_label},
                artifact_id=artifact_id,
            ))

        except Exception as e:
            logger.error("Dateien anzeigen fehlgeschlagen: %s", e)
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                content=f"Fehler beim Laden der Dateien: {e}",
            ))

    # ---- History anzeigen ----

    def _show_history(self, search: str = "") -> None:
        """History-Eintraege als HISTORY Message."""
        try:
            from ..config import load_config
            from ..logger import LogManager

            cfg = self._cfg()
            logs_dir = Path(cfg["paths"]["logs"])

            if not logs_dir.exists():
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INFO,
                    content="Noch keine History vorhanden. Sortiere Dateien um den Verlauf zu sehen.",
                ))
                return

            log_mgr = LogManager(logs_dir)
            all_logs = log_mgr.get_all_logs()

            if search:
                search_lower = search.lower()
                all_logs = [
                    l for l in all_logs
                    if search_lower in l.get("source", "").lower()
                    or search_lower in l.get("dokumentenart", "").lower()
                    or search_lower in l.get("kunde", "").lower()
                ]

            # Neueste zuerst, max 20
            all_logs = sorted(all_logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:20]

            if not all_logs:
                content = "Keine passenden History-Eintraege gefunden."
                if search:
                    content += f" (Suche: \"{search}\")"
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INFO,
                    content=content,
                ))
                return

            entries = []
            for log in all_logs:
                entries.append({
                    "timestamp": log.get("timestamp", ""),
                    "source": Path(log.get("source", "")).name if log.get("source") else "?",
                    "target": Path(log.get("target", "")).name if log.get("target") else "?",
                    "doc_type": log.get("dokumentenart", "unbekannt"),
                    "customer": log.get("kunde", "unbekannt"),
                    "country": log.get("land", "unbekannt"),
                    "confidence": log.get("confidence", 0),
                })

            n = len(entries)
            content = f"<strong>Letzte {n} Aktionen</strong>:"
            if search:
                content += f" (Suche: \"{search}\")"

            artifact_id = self._add_artifact(f"History ({n})", "history", {"entries": entries})

            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.HISTORY,
                content=content,
                metadata={"entries": entries},
                artifact_id=artifact_id,
            ))

        except Exception as e:
            logger.error("History anzeigen fehlgeschlagen: %s", e)
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                content=f"Fehler beim Laden der History: {e}",
            ))

    # ---- System-Info anzeigen ----

    def _show_system_info(self) -> None:
        """System-Status als SYSTEM_INFO Message."""
        import platform
        import sys

        try:
            from ..config import load_config
            from ..watcher import is_watching

            cfg = self._cfg()

            # OCR Check
            ocr_available = False
            try:
                import pytesseract
                pytesseract.get_tesseract_version()
                ocr_available = True
            except Exception:
                pass

            info = {
                "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "os": f"{platform.system()} {platform.release()}",
                "inbox": cfg["paths"]["inbox"],
                "archive": cfg["paths"]["archive"],
                "ocr": "Verfuegbar" if ocr_available else "Nicht installiert",
                "watcher": "Aktiv" if is_watching() else "Inaktiv",
                "file_types": ", ".join(cfg.get("file_types", [".pdf"])),
            }

            parts = [
                "<strong>System-Information:</strong><br>",
                f"Python: <strong>{info['python']}</strong><br>"
                f"Betriebssystem: <strong>{info['os']}</strong><br>"
                f"OCR (Tesseract): <strong>{info['ocr']}</strong><br>"
                f"Inbox-Watcher: <strong>{info['watcher']}</strong><br>",
                f"<br><strong>Pfade:</strong><br>"
                f"Inbox: <code>{info['inbox']}</code><br>"
                f"Archiv: <code>{info['archive']}</code><br>",
                f"<br>Dateitypen: {info['file_types']}",
            ]

            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.SYSTEM_INFO,
                content="".join(parts),
                metadata=info,
                actions=[
                    Action(id="config", label="Einstellungen oeffnen", icon="tune",
                           variant="secondary", callback_key="navigate_config"),
                ],
            ))

        except Exception as e:
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                content=f"System-Info konnte nicht geladen werden: {e}",
            ))

    # ---- Inline-Charts ----

    def _show_chart(self, chart_type: str = "timeline") -> None:
        """HighChart-Config als CHART Message in metadata."""
        try:
            from .chart_data import get_chart_config

            config = get_chart_config(chart_type)

            if config is None:
                self._emit(ChatMessage(
                    id="", role=MsgRole.AGENT, type=MsgType.INFO,
                    content="Noch keine Daten fuer Charts vorhanden. Sortiere Dateien um Statistiken zu sehen.",
                ))
                return

            title_map = {
                "timeline": "Dokumente pro Monat",
                "doctype_pie": "Nach Dokumentenart",
                "customer_bar": "Nach Kunde",
                "confidence": "Erkennungs-Sicherheit",
            }
            title = title_map.get(chart_type, chart_type)
            artifact_id = self._add_artifact(title, "chart", config)

            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.CHART,
                content=f"<strong>{title}</strong>",
                metadata={"highchart_config": config},
                artifact_id=artifact_id,
            ))

        except Exception as e:
            logger.error("Chart-Anzeige fehlgeschlagen: %s", e)
            self._emit(ChatMessage(
                id="", role=MsgRole.AGENT, type=MsgType.ERROR,
                content=f"Chart konnte nicht geladen werden: {e}",
            ))

    # ---- Stats fuer Sidebar ----

    def get_stats(self) -> dict[str, Any]:
        """Aktuelle Statistiken fuer das Right Panel."""
        try:
            from ..config import load_config, get_file_types

            cfg = self._cfg()
            inbox = Path(cfg["paths"]["inbox"])
            archive = Path(cfg["paths"]["archive"])
            review = Path(cfg["paths"].get("review", str(archive / "_review")))
            allowed = get_file_types(cfg)

            inbox_count = sum(1 for f in inbox.rglob("*")
                              if f.is_file() and f.suffix.lower() in allowed) if inbox.exists() else 0
            review_count = sum(1 for f in review.rglob("*") if f.is_file()) if review.exists() else 0

            state_path = archive / "_state.json"
            processed = 0
            if state_path.exists():
                try:
                    data = json.loads(state_path.read_text(encoding="utf-8"))
                    processed = len(data.get("processed", {}))
                except Exception:
                    pass

            return {
                "inbox": inbox_count,
                "review": review_count,
                "processed": processed,
            }
        except Exception:
            return {"inbox": 0, "review": 0, "processed": 0}

    def get_stats_cached(self) -> dict[str, Any]:
        """Cached Stats zurueckgeben (kein I/O). Sicher fuer Timer-Callbacks."""
        return dict(self._stats_cache)

    def refresh_stats(self) -> dict[str, Any]:
        """I/O-bound: Stats neu berechnen und Cache aktualisieren.

        Nur aus run.io_bound() oder ThreadPoolExecutor aufrufen.
        """
        stats = self.get_stats()
        self._stats_cache = stats
        self._stats_cache_time = time.time()
        return stats
