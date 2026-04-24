"""Chart-Data: HighChart-Config Generatoren fuer Inline-Charts und Analytics.

Extrahiert die Chart-Logik aus analytics.py in wiederverwendbare Funktionen,
die sowohl von analytics.py als auch vom Chat-Agent genutzt werden.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_logs() -> list[dict[str, Any]]:
    """Log-Daten laden."""
    try:
        from ..config import load_config
        from ..logger import LogManager

        cfg = load_config()
        logs_dir = Path(cfg["paths"]["logs"])
        if not logs_dir.exists():
            return []
        log_mgr = LogManager(logs_dir)
        return log_mgr.get_all_logs()
    except Exception as e:
        logger.warning("Logs konnten nicht geladen werden: %s", e)
        return []


def get_timeline_chart_config(logs: list[dict] | None = None) -> dict | None:
    """HighChart JSON Config fuer Timeline (Dokumente pro Monat)."""
    if logs is None:
        logs = _load_logs()
    if not logs:
        return None

    monthly: Counter = Counter()
    for log in logs:
        ts = log.get("timestamp", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                key = dt.strftime("%Y-%m")
                monthly[key] += 1
            except (ValueError, TypeError):
                pass

    if not monthly:
        return None

    months = sorted(monthly.keys())
    counts = [monthly[m] for m in months]
    display_months = []
    for m in months:
        try:
            dt = datetime.strptime(m, "%Y-%m")
            display_months.append(dt.strftime("%b %Y"))
        except ValueError:
            display_months.append(m)

    return {
        "title": {"text": ""},
        "chart": {"type": "column", "height": 240, "backgroundColor": "transparent"},
        "xAxis": {"categories": display_months},
        "yAxis": {"title": {"text": "Anzahl"}, "allowDecimals": False},
        "series": [{"name": "Dokumente", "data": counts, "color": "#3B82F6"}],
        "credits": {"enabled": False},
        "legend": {"enabled": False},
    }


def get_doctype_chart_config(logs: list[dict] | None = None) -> dict | None:
    """HighChart JSON Config fuer Dokumentenart-Verteilung (Pie)."""
    if logs is None:
        logs = _load_logs()
    if not logs:
        return None

    types: Counter = Counter()
    for log in logs:
        cls = log.get("classification", {})
        art = cls.get("dokumentenart", "unbekannt")
        types[art] += 1

    if not types:
        return None

    data = [{"name": k, "y": v} for k, v in types.most_common(10)]

    return {
        "title": {"text": ""},
        "chart": {"type": "pie", "height": 240, "backgroundColor": "transparent"},
        "series": [{"name": "Dokumente", "data": data}],
        "plotOptions": {"pie": {"dataLabels": {"enabled": True, "format": "{point.name}: {point.y}"}}},
        "credits": {"enabled": False},
    }


def get_customer_chart_config(logs: list[dict] | None = None) -> dict | None:
    """HighChart JSON Config fuer Top-Kunden (Bar)."""
    if logs is None:
        logs = _load_logs()
    if not logs:
        return None

    customers: Counter = Counter()
    for log in logs:
        cls = log.get("classification", {})
        kunde = cls.get("kunde", "unbekannt")
        customers[kunde] += 1

    if not customers:
        return None

    top = customers.most_common(10)
    names = [k for k, v in top]
    counts = [v for k, v in top]

    return {
        "title": {"text": ""},
        "chart": {"type": "bar", "height": 240, "backgroundColor": "transparent"},
        "xAxis": {"categories": names},
        "yAxis": {"title": {"text": "Dokumente"}, "allowDecimals": False},
        "series": [{"name": "Dokumente", "data": counts, "color": "#10B981"}],
        "credits": {"enabled": False},
        "legend": {"enabled": False},
    }


def get_confidence_chart_config(logs: list[dict] | None = None) -> dict | None:
    """HighChart JSON Config fuer Confidence-Verteilung."""
    if logs is None:
        logs = _load_logs()
    if not logs:
        return None

    buckets = {"0-20%": 0, "20-40%": 0, "40-60%": 0, "60-80%": 0, "80-100%": 0}
    for log in logs:
        conf = log.get("classification", {}).get("confidence", 0)
        if conf < 0.2:
            buckets["0-20%"] += 1
        elif conf < 0.4:
            buckets["20-40%"] += 1
        elif conf < 0.6:
            buckets["40-60%"] += 1
        elif conf < 0.8:
            buckets["60-80%"] += 1
        else:
            buckets["80-100%"] += 1

    colors = ["#EF4444", "#F97316", "#EAB308", "#84CC16", "#22C55E"]

    return {
        "title": {"text": ""},
        "chart": {"type": "column", "height": 240, "backgroundColor": "transparent"},
        "xAxis": {"categories": list(buckets.keys())},
        "yAxis": {"title": {"text": "Anzahl"}, "allowDecimals": False},
        "series": [{"name": "Dokumente", "data": [
            {"y": v, "color": colors[i]} for i, v in enumerate(buckets.values())
        ]}],
        "credits": {"enabled": False},
        "legend": {"enabled": False},
    }


# --- Convenience: Chart-Type Dispatcher ---

_CHART_BUILDERS = {
    "timeline": get_timeline_chart_config,
    "doctype_pie": get_doctype_chart_config,
    "customer_bar": get_customer_chart_config,
    "confidence": get_confidence_chart_config,
}


def get_chart_config(chart_type: str, logs: list[dict] | None = None) -> dict | None:
    """Dispatcher: Chart-Config nach Typ holen.

    Args:
        chart_type: "timeline", "doctype_pie", "customer_bar", "confidence"
        logs: Optional vorgeladene Log-Daten

    Returns:
        HighChart Config dict, oder None wenn keine Daten
    """
    builder = _CHART_BUILDERS.get(chart_type)
    if builder is None:
        logger.warning("Unbekannter Chart-Typ: %s", chart_type)
        return None
    return builder(logs)


def get_all_chart_types() -> list[str]:
    """Alle verfuegbaren Chart-Typen."""
    return list(_CHART_BUILDERS.keys())
