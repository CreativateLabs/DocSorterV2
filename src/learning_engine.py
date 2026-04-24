"""Doc-Sorter Lern-Engine: Eigenes, selbstlernendes Klassifikationssystem.

Das System lernt direkt aus den Bestätigungen und Korrekturen des Nutzers.
Jedes bestätigte oder korrigierte Dokument wird zum Trainingsbeispiel.
Mit der Zeit kennt die Engine die spezifischen Dokumente des Nutzers —
und kann eigenständig klassifizieren ohne externe KI.

Technischer Stack (alles lokal, kein Cloud-Zwang, kein Internet):
  sentence-transformers → Text in semantische Vektoren (DE/EN/SQ, ~275 MB, einmalig)
  scikit-learn          → Logistic Regression auf den Vektoren (trainiert in Sekunden)
  joblib / pickle       → Modell-Persistenz (< 5 MB)
  JSON                  → Trainings-Daten (wächst mit jedem Nutzer-Feedback)

Ablauf:
  1. Nutzer bestätigt/korrigiert Dokument im Review
       → add_example(text, label)
       → TrainingStore speichert Beispiel in training_data.json
  2. Alle RETRAIN_THRESHOLD neuen Beispiele → automatisch neu trainieren
  3. Nächste Klassifikation → predict(text) liefert Vorhersage + Konfidenz
  4. Je mehr Beispiele → desto besser und unabhängiger das System

Integration in die Klassifikations-Pipeline:
  Keyword-Classifier (immer)
    → Lern-Engine predict() — wenn Konfidenz > 0.70 → Ergebnis nutzen
    → LLM-Fallback (nur noch bei echter Unsicherheit)

Mindestanforderungen zum Trainieren:
  - ≥ MIN_EXAMPLES_PER_CLASS (2) Beispiele pro Dokumentenart
  - ≥ 2 verschiedene Dokumentenarten
  → Danach wächst die Genauigkeit mit jedem weiteren Beispiel

Alle Daten liegen in: <archiv-parent>/_learning_engine/
  training_data.json  — Alle Trainingsbeispiele (Text + Label)
  model.pkl           — Trainiertes Klassifikationsmodell
  embed_cache.pkl     — Embedding-Cache (vermeidet Doppel-Berechnungen)
  meta.json           — Metadaten (Status, Klassen, Timestamps)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pickle
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Konfiguration ────────────────────────────────────────────────────────────
_MIN_EXAMPLES_PER_CLASS = 2    # Mindest-Beispiele pro Klasse
_RETRAIN_THRESHOLD      = 10   # Neue Beispiele bis zum automatischen Retrain
_MAX_TEXT_LEN           = 2000 # Maximale Textlänge pro Trainingsbeispiel
_HIGH_CONFIDENCE        = 0.70 # Ab diesem Score gilt die Engine-Vorhersage als sicher
_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # 275 MB, DE/EN/SQ-fähig

# Globale Singletons (lazy geladen)
_embed_model_instance = None
_embed_model_tried    = False


# ============================================================================
# Datenklassen
# ============================================================================

@dataclass
class TrainingExample:
    """Ein einzelnes gelerntes Dokument."""
    text_preview: str          # Erste MAX_TEXT_LEN Zeichen des Dokuments
    label: str                 # Dokumentenart (z.B. "rechnung")
    source: str    = "review"  # Quelle: "review" | "auto" | "wizard"
    confidence: float = 1.0   # Vertrauen in das Label (1.0 = Nutzer bestätigt)
    added: str     = ""

    def __post_init__(self) -> None:
        if not self.added:
            self.added = datetime.now().isoformat()
        self.text_preview = self.text_preview[:_MAX_TEXT_LEN]


@dataclass
class LearningResult:
    """Ergebnis einer Lern-Engine-Klassifikation."""
    label: str             = "unbekannt"
    confidence: float      = 0.0
    available: bool        = False   # False: Modell noch nicht einsatzbereit
    trained_on: int        = 0       # Trainingsbeispiele beim letzten Training
    classes: list[str]     = field(default_factory=list)
    needs_more_data: bool  = False   # True: zu wenig Beispiele zum Trainieren
    is_confident: bool     = False   # True: confidence >= HIGH_CONFIDENCE


# ============================================================================
# Pfade
# ============================================================================

def _engine_dir() -> Path:
    """Verzeichnis für alle Lern-Engine-Dateien (neben dem Archiv)."""
    try:
        from .config import load_config
        cfg  = load_config()
        arch = cfg.get("paths", {}).get("archive", "")
        if arch:
            p = Path(arch).expanduser().parent / "_learning_engine"
            p.mkdir(parents=True, exist_ok=True)
            return p
    except Exception:
        pass
    p = Path.home() / ".doc-sorter" / "_learning_engine"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _training_data_path() -> Path: return _engine_dir() / "training_data.json"
def _model_path()         -> Path: return _engine_dir() / "model.pkl"
def _meta_path()          -> Path: return _engine_dir() / "meta.json"
def _embed_cache_path()   -> Path: return _engine_dir() / "embed_cache.pkl"


# ============================================================================
# Trainings-Daten
# ============================================================================

def _load_training_data() -> list[TrainingExample]:
    p = _training_data_path()
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return [TrainingExample(**ex) for ex in raw]
    except Exception as exc:
        logger.warning("TrainingData: Laden fehlgeschlagen: %s", exc)
        return []


def _save_training_data(examples: list[TrainingExample]) -> None:
    """Atomar schreiben — verhindert Datei-Korruption bei gleichzeitigen Schreibvorgängen."""
    import os, tempfile
    try:
        p = _training_data_path()
        content = json.dumps([asdict(ex) for ex in examples], ensure_ascii=False, indent=2)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, p)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as exc:
        logger.warning("TrainingData: Speichern fehlgeschlagen: %s", exc)


def _load_meta() -> dict[str, Any]:
    p = _meta_path()
    if not p.exists():
        return {
            "trained_on": 0, "total_examples": 0,
            "last_trained": "", "new_since_train": 0, "classes": [],
            "enabled": True,
        }
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # Rückwärtskompatibilität: enabled-Feld nachrüsten
        data.setdefault("enabled", True)
        return data
    except Exception:
        return {"trained_on": 0, "total_examples": 0, "last_trained": "", "new_since_train": 0, "classes": [], "enabled": True}


def _save_meta(meta: dict[str, Any]) -> None:
    """Atomar schreiben — verhindert Datei-Korruption bei gleichzeitigen Schreibvorgängen."""
    import os, tempfile
    try:
        p = _meta_path()
        content = json.dumps(meta, ensure_ascii=False, indent=2)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, p)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as exc:
        logger.warning("LearningMeta: Speichern fehlgeschlagen: %s", exc)


# ============================================================================
# Embedding-Cache
# ============================================================================

def _load_embed_cache() -> dict[str, list[float]]:
    p = _embed_cache_path()
    if not p.exists():
        return {}
    try:
        with p.open("rb") as f:
            return pickle.load(f)
    except Exception:
        return {}


def _save_embed_cache(cache: dict[str, list[float]]) -> None:
    p = _embed_cache_path()
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                pickle.dump(cache, f)
            os.replace(tmp_path, p)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise
    except Exception as exc:
        logger.warning("EmbedCache: Speichern fehlgeschlagen: %s", exc)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text[:_MAX_TEXT_LEN].encode("utf-8")).hexdigest()[:16]


# ============================================================================
# Embedding-Modell
# ============================================================================

def _get_embed_model():
    """Embedding-Modell laden (lazy init, gecacht, graceful fallback)."""
    global _embed_model_instance, _embed_model_tried
    if _embed_model_instance is not None:
        return _embed_model_instance
    if _embed_model_tried:
        return None
    _embed_model_tried = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        logger.info("Lade Embedding-Modell '%s' (einmalig ~275 MB) …", _EMBED_MODEL)
        _embed_model_instance = SentenceTransformer(_EMBED_MODEL)
        logger.info("Embedding-Modell bereit.")
        return _embed_model_instance
    except ImportError:
        logger.warning(
            "sentence-transformers nicht installiert. "
            "Lern-Engine deaktiviert. Installiere mit: pip install sentence-transformers scikit-learn"
        )
        return None
    except Exception as exc:
        logger.warning("Embedding-Modell konnte nicht geladen werden: %s", exc)
        return None


def _embed_texts(texts: list[str], cache: dict[str, list[float]]) -> list[list[float]] | None:
    """Texte in Vektoren umwandeln. Cache wird genutzt/aktualisiert."""
    model = _get_embed_model()
    if model is None:
        return None

    result_map: dict[int, list[float]] = {}
    to_embed: list[str] = []
    to_embed_idx: list[int] = []

    for i, text in enumerate(texts):
        h = _text_hash(text)
        if h in cache:
            result_map[i] = cache[h]
        else:
            to_embed.append(text[:_MAX_TEXT_LEN])
            to_embed_idx.append(i)

    if to_embed:
        try:
            new_embs = model.encode(to_embed, show_progress_bar=False).tolist()
            for idx, text, emb in zip(to_embed_idx, to_embed, new_embs):
                h = _text_hash(text)
                cache[h] = emb
                result_map[idx] = emb
        except Exception as exc:
            logger.warning("Embedding fehlgeschlagen: %s", exc)
            return None

    return [result_map[i] for i in range(len(texts))]


# ============================================================================
# Modell laden / speichern
# ============================================================================

def _load_model() -> dict | None:
    p = _model_path()
    if not p.exists():
        return None
    try:
        with p.open("rb") as f:
            return pickle.load(f)
    except Exception as exc:
        logger.warning("Modell-Laden fehlgeschlagen: %s", exc)
        return None


def _save_model(bundle: dict) -> None:
    try:
        with _model_path().open("wb") as f:
            pickle.dump(bundle, f)
    except Exception as exc:
        logger.warning("Modell-Speichern fehlgeschlagen: %s", exc)


# ============================================================================
# Training
# ============================================================================

def train(force: bool = False) -> dict[str, Any]:
    """Lern-Engine (neu) trainieren.

    Args:
        force: True → trainieren auch wenn RETRAIN_THRESHOLD noch nicht erreicht

    Returns dict mit:
        ok           — True wenn Training erfolgreich
        trained_on   — Anzahl genutzter Trainingsbeispiele
        classes      — Liste der gelernten Dokumentenarten
        reason       — Erklärung wenn ok=False
    """
    examples = _load_training_data()
    if not examples:
        return {"ok": False, "reason": "Keine Trainingsbeispiele vorhanden. Bestätige oder korrigiere zuerst Dokumente im Review."}

    meta = _load_meta()

    # Auto-Retrain-Schwelle prüfen (außer force=True)
    if not force:
        new_since = meta.get("new_since_train", 0)
        trained_on = meta.get("trained_on", 0)
        if trained_on > 0 and new_since < _RETRAIN_THRESHOLD:
            return {
                "ok": True,
                "reason": f"Retrain noch nicht nötig ({new_since}/{_RETRAIN_THRESHOLD} neue Beispiele).",
                "trained_on": trained_on,
                "classes": meta.get("classes", []),
            }

    # Klassen mit genug Beispielen filtern
    label_counts = Counter(ex.label for ex in examples)
    valid_labels  = {lbl for lbl, cnt in label_counts.items() if cnt >= _MIN_EXAMPLES_PER_CLASS}

    if len(valid_labels) < 2:
        missing = {
            lbl: max(0, _MIN_EXAMPLES_PER_CLASS - cnt)
            for lbl, cnt in label_counts.items()
        }
        return {
            "ok": False,
            "reason": (
                f"Noch nicht genug Trainingsbeispiele. "
                f"Benötigt: ≥{_MIN_EXAMPLES_PER_CLASS} Beispiele für mindestens 2 Dokumentenarten. "
                f"Fehlend: {missing}"
            ),
            "label_counts": dict(label_counts),
        }

    valid_examples = [ex for ex in examples if ex.label in valid_labels]
    texts  = [ex.text_preview for ex in valid_examples]
    labels = [ex.label for ex in valid_examples]

    # Embeddings berechnen
    embed_cache = _load_embed_cache()
    embeddings  = _embed_texts(texts, embed_cache)
    if embeddings is None:
        return {
            "ok": False,
            "reason": "Embedding-Modell nicht verfügbar. Installiere: pip install sentence-transformers",
        }
    _save_embed_cache(embed_cache)

    # Klassifikator trainieren
    try:
        import numpy as np
        from sklearn.linear_model     import LogisticRegression
        from sklearn.preprocessing    import LabelEncoder
        from sklearn.model_selection  import cross_val_score

        X = np.array(embeddings)
        le = LabelEncoder()
        y  = le.fit_transform(labels)

        clf = LogisticRegression(
            max_iter     = 1000,
            C            = 1.0,
            solver       = "lbfgs",
            multi_class  = "auto",
            class_weight = "balanced",   # Ausgleich bei ungleichen Klassengrößen
        )
        clf.fit(X, y)

        # Cross-Validation-Score (nur wenn genug Daten)
        cv_score = None
        if len(valid_examples) >= 10:
            try:
                scores   = cross_val_score(clf, X, y, cv=max(2, min(5, len(valid_examples) // 2)))
                cv_score = round(float(scores.mean()), 3)
            except Exception:
                pass

        bundle = {"clf": clf, "le": le, "embed_model_name": _EMBED_MODEL}
        _save_model(bundle)

        classes = list(le.classes_)
        new_meta: dict[str, Any] = {
            "trained_on":      len(valid_examples),
            "total_examples":  len(examples),
            "last_trained":    datetime.now().isoformat(),
            "new_since_train": 0,
            "classes":         classes,
            "label_counts":    dict(label_counts),
        }
        if cv_score is not None:
            new_meta["cv_accuracy"] = cv_score
        _save_meta(new_meta)

        logger.info(
            "Lern-Engine trainiert: %d Beispiele, %d Klassen: %s%s",
            len(valid_examples), len(classes), classes,
            f", CV-Accuracy: {cv_score:.1%}" if cv_score else "",
        )
        result: dict[str, Any] = {
            "ok": True, "trained_on": len(valid_examples), "classes": classes,
        }
        if cv_score is not None:
            result["cv_accuracy"] = cv_score
        return result

    except ImportError:
        return {
            "ok": False,
            "reason": "scikit-learn nicht installiert. Installiere: pip install scikit-learn",
        }
    except Exception as exc:
        logger.error("Training fehlgeschlagen: %s", exc, exc_info=True)
        return {"ok": False, "reason": str(exc)}


# ============================================================================
# Vorhersage
# ============================================================================

def predict(text: str) -> LearningResult:
    """Text mit dem trainierten Modell klassifizieren.

    Returns LearningResult.available=False wenn kein Modell vorhanden oder Engine pausiert.
    Returns LearningResult.is_confident=True wenn confidence >= HIGH_CONFIDENCE.
    """
    meta      = _load_meta()
    if not meta.get("enabled", True):
        return LearningResult(available=False, trained_on=meta.get("trained_on", 0))
    trained_on = meta.get("trained_on", 0)
    classes   = meta.get("classes", [])

    if trained_on == 0:
        return LearningResult(available=False, trained_on=0, needs_more_data=True)

    bundle = _load_model()
    if bundle is None:
        return LearningResult(available=False, trained_on=trained_on, classes=classes)

    embed_cache = _load_embed_cache()
    embeddings  = _embed_texts([text], embed_cache)
    if embeddings is None:
        return LearningResult(available=False, trained_on=trained_on, classes=classes)
    _save_embed_cache(embed_cache)

    try:
        import numpy as np

        clf = bundle["clf"]
        le  = bundle["le"]
        X   = np.array(embeddings)

        proba     = clf.predict_proba(X)[0]
        best_idx  = int(proba.argmax())
        best_lbl  = str(le.classes_[best_idx])
        conf      = float(proba[best_idx])

        return LearningResult(
            label         = best_lbl,
            confidence    = round(conf, 3),
            available     = True,
            trained_on    = trained_on,
            classes       = list(le.classes_),
            is_confident  = conf >= _HIGH_CONFIDENCE,
        )

    except Exception as exc:
        logger.warning("predict fehlgeschlagen: %s", exc)
        return LearningResult(available=False, trained_on=trained_on, classes=classes)


# ============================================================================
# Beispiel hinzufügen (öffentliche API)
# ============================================================================

def add_example(
    text: str,
    label: str,
    source: str     = "review",
    confidence: float = 1.0,
) -> bool:
    """Trainingsbeispiel hinzufügen und bei Bedarf automatisch neu trainieren.

    Args:
        text:       Dokumenttext (wird auf MAX_TEXT_LEN Zeichen begrenzt)
        label:      Korrekte Dokumentenart (z.B. "rechnung")
        source:     Quelle ("review" = Nutzer, "auto" = automatisch, "wizard" = Einrichtung)
        confidence: Zuverlässigkeit des Labels (1.0 = Nutzer hat bestätigt)

    Returns:
        True wenn erfolgreich hinzugefügt (False bei Duplikat oder ungültigen Eingaben)
    """
    if not text.strip() or not label or not label.strip() or label.strip() in ("unbekannt", ""):
        return False
    if not _load_meta().get("enabled", True):
        logger.debug("add_example übersprungen: Lern-Engine ist pausiert")
        return False

    try:
        examples = _load_training_data()

        # Duplikat-Check: gleicher Text + gleiche Klasse → überspringen
        text_h = _text_hash(text)
        for ex in examples:
            if _text_hash(ex.text_preview) == text_h and ex.label == label:
                logger.debug("Trainingsbeispiel übersprungen (Duplikat): label='%s'", label)
                return False

        new_ex = TrainingExample(
            text_preview=text, label=label, source=source, confidence=confidence
        )
        examples.append(new_ex)
        _save_training_data(examples)

        # Meta: Zähler erhöhen
        meta = _load_meta()
        meta["new_since_train"] = meta.get("new_since_train", 0) + 1
        meta["total_examples"]  = len(examples)
        _save_meta(meta)

        logger.info(
            "Trainingsbeispiel hinzugefügt: label='%s' source='%s' (gesamt: %d, neu: %d/%d)",
            label, source, len(examples), meta["new_since_train"], _RETRAIN_THRESHOLD,
        )

        # Auto-Retrain wenn Schwelle erreicht
        if meta["new_since_train"] >= _RETRAIN_THRESHOLD:
            logger.info("Auto-Retrain wird ausgelöst …")
            result = train(force=True)
            if result.get("ok"):
                logger.info("Auto-Retrain erfolgreich: %d Beispiele, Klassen: %s",
                            result.get("trained_on", 0), result.get("classes", []))
            else:
                logger.warning("Auto-Retrain fehlgeschlagen: %s", result.get("reason"))

        return True

    except Exception as exc:
        logger.warning("add_example fehlgeschlagen: %s", exc)
        return False


# ============================================================================
# Status-Abfrage (für UI und System-Seite)
# ============================================================================

def get_status() -> dict[str, Any]:
    """Vollständigen Status der Lern-Engine abfragen.

    Für System-Seite und Einstellungen.
    """
    meta     = _load_meta()
    examples = _load_training_data()

    # Abhängigkeiten prüfen
    try:
        import sentence_transformers  # noqa: F401
        embed_ok = True
    except ImportError:
        embed_ok = False

    try:
        import sklearn  # noqa: F401
        sklearn_ok = True
    except ImportError:
        sklearn_ok = False

    model_ok    = _model_path().exists()
    new_since   = meta.get("new_since_train", 0)
    trained_on  = meta.get("trained_on", 0)
    last_trained = meta.get("last_trained", "")

    # Lesbares Datum
    last_trained_fmt = ""
    if last_trained:
        try:
            dt = datetime.fromisoformat(last_trained)
            last_trained_fmt = dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            last_trained_fmt = last_trained

    # Klassen-Verteilung für aktuelle Trainingsdaten
    label_counts = Counter(ex.label for ex in examples)

    enabled = meta.get("enabled", True)

    return {
        # Einsatzbereit?
        "available":          model_ok and embed_ok and sklearn_ok and trained_on > 0 and enabled,
        "enabled":            enabled,
        # Trainings-Status
        "trained_on":         trained_on,
        "total_examples":     len(examples),
        "new_since_train":    new_since,
        "retrain_threshold":  _RETRAIN_THRESHOLD,
        "retrain_progress":   min(new_since, _RETRAIN_THRESHOLD),
        "last_trained":       last_trained,
        "last_trained_fmt":   last_trained_fmt,
        "cv_accuracy":        meta.get("cv_accuracy"),
        # Klassen
        "classes":            meta.get("classes", []),
        "label_counts":       dict(label_counts),
        # Abhängigkeiten
        "embed_installed":    embed_ok,
        "sklearn_installed":  sklearn_ok,
        "model_exists":       model_ok,
        # Konfiguration
        "high_confidence":    _HIGH_CONFIDENCE,
        "min_per_class":      _MIN_EXAMPLES_PER_CLASS,
        "embed_model":        _EMBED_MODEL,
        "engine_dir":         str(_engine_dir()),
    }


def is_available() -> bool:
    """Kurzprüfung: Ist die Engine trainiert und einsatzbereit?"""
    s = get_status()
    return bool(s["available"])


def is_enabled() -> bool:
    """Ist die Lern-Engine vom Nutzer aktiviert (nicht pausiert)?"""
    return bool(_load_meta().get("enabled", True))


def set_enabled(value: bool) -> None:
    """Lern-Engine an- oder abschalten ohne Daten oder Modell zu löschen.

    Deaktiviert:  add_example() und predict() tun nichts / geben unavailable zurück.
    Aktiviert:    Normalbetrieb wird sofort wieder aufgenommen.
    """
    meta = _load_meta()
    meta["enabled"] = value
    _save_meta(meta)
    logger.info("Lern-Engine: %s", "aktiviert" if value else "pausiert")


def install_hint() -> str:
    """Installationshinweis wenn Abhängigkeiten fehlen."""
    s = get_status()
    missing = []
    if not s["embed_installed"]:
        missing.append("sentence-transformers")
    if not s["sklearn_installed"]:
        missing.append("scikit-learn")
    if missing:
        return f"pip install {' '.join(missing)}"
    return ""
