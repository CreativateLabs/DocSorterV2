"""Design-System & Theme: Tailwind-orientierte Design Tokens und Komponenten-Helper.

Alle Komponenten nutzen native NiceGUI-Elemente (KEIN ui.html fuer Icons!).
"""

from __future__ import annotations

from nicegui import ui


def enable_scroll() -> None:
    """Scrolling fuer klassische Seiten aktivieren."""
    ui.add_head_html(
        "<style>"
        "html, body { overflow-y: auto !important; height: auto !important; }"
        ".q-layout { min-height: 100vh !important; }"
        ".q-page-container { overflow-y: visible !important; }"
        ".q-page { overflow-y: visible !important; min-height: auto !important; }"
        "</style>"
    )


# ---------------------------------------------------------------------------
# Design Tokens
# ---------------------------------------------------------------------------

COLORS = {
    "primary": "#00d4ff",
    "primary_light": "rgba(0,212,255,0.15)",
    "primary_dark": "#0098cc",
    "success": "#00e87d",
    "success_light": "rgba(0,232,125,0.12)",
    "warning": "#ff9f0a",
    "warning_light": "rgba(255,159,10,0.12)",
    "error": "#ff3366",
    "error_light": "rgba(255,51,102,0.12)",
}

# SharePoint-inspirierte Kategorie-Farben (aus RTF Design)
CATEGORY_COLORS: dict[str, str] = {
    "rechnung":  "#3b82f6",   # bright blue
    "vertrag":   "#22c55e",   # green
    "angebot":   "#f97316",   # orange
    "mahnung":   "#ef4444",   # red
    "brief":     "#a855f7",   # purple
    "bericht":   "#06b6d4",   # cyan
    "protokoll": "#14b8a6",   # teal
    "sonstiges": "#64748b",   # gray
}

# Icon-Hintergrund Farben (futuristisch)
_ICON_BG = {
    "blue":   ("background:rgba(0,212,255,0.12);color:#00d4ff", "background:rgba(0,212,255,0.15);color:#00d4ff"),
    "green":  ("background:rgba(0,232,125,0.12);color:#00e87d", "background:rgba(0,232,125,0.15);color:#00e87d"),
    "amber":  ("background:rgba(255,159,10,0.12);color:#ff9f0a", "background:rgba(255,159,10,0.15);color:#ff9f0a"),
    "red":    ("background:rgba(255,51,102,0.12);color:#ff3366", "background:rgba(255,51,102,0.15);color:#ff3366"),
    "purple": ("background:rgba(124,58,237,0.12);color:#a78bfa", "background:rgba(124,58,237,0.15);color:#a78bfa"),
    "cyan":   ("background:rgba(0,212,255,0.10);color:#00d4ff", "background:rgba(0,212,255,0.15);color:#00d4ff"),
}

# Badge-Farben: (bg, text)
_BADGE_COLORS = {
    "success": ("rgba(0,232,125,0.15)", "#00e87d"),
    "warning": ("rgba(255,159,10,0.15)", "#ff9f0a"),
    "error":   ("rgba(255,51,102,0.15)", "#ff3366"),
    "info":    ("rgba(0,212,255,0.15)", "#00d4ff"),
    "neutral": ("rgba(148,163,184,0.12)", "#94a3b8"),
}

# Callout-Farben: (bg, border, text)
_CALLOUT_COLORS = {
    "info":    ("rgba(0,212,255,0.06)", "#00d4ff", "#93c5fd"),
    "warning": ("rgba(255,159,10,0.06)", "#ff9f0a", "#fbbf24"),
    "success": ("rgba(0,232,125,0.06)", "#00e87d", "#6ee7b7"),
    "error":   ("rgba(255,51,102,0.06)", "#ff3366", "#fca5a5"),
}

_CALLOUT_ICONS = {
    "info": "info",
    "warning": "warning",
    "success": "check_circle",
    "error": "error",
}


# ---------------------------------------------------------------------------
# Custom CSS (no Material Icons in HTML - alle via NiceGUI ui.icon())
# ---------------------------------------------------------------------------

_CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --ds-bg:           #050d1a;
    --ds-surface:      #0a1628;
    --ds-surface-2:    #0f1d35;
    --ds-surface-3:    #162544;
    --ds-border:       rgba(0,212,255,0.12);
    --ds-border-glow:  rgba(0,212,255,0.35);
    --ds-primary:      #00d4ff;
    --ds-primary-dark: #0098cc;
    --ds-primary-glow: rgba(0,212,255,0.25);
    --ds-secondary:    #7c3aed;
    --ds-secondary-glow: rgba(124,58,237,0.25);
    --ds-success:      #00e87d;
    --ds-success-glow: rgba(0,232,125,0.2);
    --ds-warning:      #ff9f0a;
    --ds-error:        #ff3366;
    --ds-text:         #e2e8f0;
    --ds-text-2:       #94a3b8;
    --ds-text-3:       #475569;
    --ds-radius:       12px;
    --ds-radius-sm:    8px;
    --ds-radius-xs:    6px;
    --ds-shadow:       0 4px 24px rgba(0,0,0,0.4);
    --ds-shadow-md:    0 8px 40px rgba(0,0,0,0.5);
    --ds-glow:         0 0 20px var(--ds-primary-glow);
    --ds-glow-md:      0 0 40px var(--ds-primary-glow);
    --ds-transition:   all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    --ds-glass:        rgba(10,22,40,0.75);
    --ds-glass-border: 1px solid rgba(0,212,255,0.15);
}

/* ======================================================
   FUTURISTIC DESIGN SYSTEM — Doc-Sorter
   Cyberpunk / Space / Neon aesthetic
   ====================================================== */

/* === Reset & Base === */
html, body {
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden;
    height: 100vh;
    width: 100vw !important;
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    background: var(--ds-bg) !important;
    color: var(--ds-text) !important;
}

/* Force dark mode always */
body { background: var(--ds-bg) !important; }

/* Subtle grid background */
body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
}

/* Scrollable pages */
.ds-scrollable-page,
body.ds-scrollable { overflow-y: auto !important; height: auto !important; }
.ds-page-scroll { overflow-y: auto; height: calc(100vh - 56px); width: 100%; }
.nicegui-content { padding: 0 !important; }
.q-page { padding: 0 !important; min-height: 0 !important; background: transparent !important; }
.q-layout { min-height: 0 !important; background: transparent !important; }
.q-page-container { padding-top: 0 !important; background: transparent !important; }

/* === Header === */
.q-header { height: 56px !important; min-height: 56px !important; max-height: 56px !important; }
.ds-header {
    background: rgba(5,9,26,0.95) !important;
    border-bottom: 1px solid rgba(0,212,255,0.2) !important;
    box-shadow: 0 1px 30px rgba(0,212,255,0.08) !important;
    backdrop-filter: blur(12px) !important;
    height: 56px !important; min-height: 56px !important; max-height: 56px !important;
}

/* === Sidebar (classic pages) === */
.ds-sidebar {
    background: var(--ds-surface) !important;
    border-right: 1px solid var(--ds-border) !important;
    padding-top: 8px !important;
}

/* === Nav Items === */
.ds-nav-link { text-decoration: none !important; }
.ds-nav-link:hover .ds-nav-row { background: rgba(0,212,255,0.06); }
.ds-nav-row {
    padding: 8px 16px;
    margin: 1px 8px;
    border-radius: 8px;
    transition: var(--ds-transition);
    border: 1px solid transparent;
}
.ds-nav-row.active {
    background: rgba(0,212,255,0.1) !important;
    border-color: rgba(0,212,255,0.25) !important;
}

/* === Page Title === */
.ds-page-title {
    font-size: 1.625rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.2;
    background: linear-gradient(135deg, #00d4ff 0%, #a78bfa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.ds-page-subtitle { font-size: 0.875rem; color: var(--ds-text-2); }

/* === Cards === */
.ds-card {
    border-radius: var(--ds-radius) !important;
    background: var(--ds-glass) !important;
    border: 1px solid var(--ds-border) !important;
    box-shadow: var(--ds-shadow), inset 0 1px 0 rgba(255,255,255,0.04) !important;
    transition: var(--ds-transition);
    padding: 20px !important;
    backdrop-filter: blur(12px) !important;
}
.ds-card:hover {
    border-color: rgba(0,212,255,0.3) !important;
    box-shadow: var(--ds-shadow), var(--ds-glow) !important;
}
.ds-card-flat {
    border-radius: var(--ds-radius) !important;
    background: rgba(10,22,40,0.6) !important;
    border: 1px solid var(--ds-border) !important;
    padding: 20px !important;
    box-shadow: none !important;
    transition: var(--ds-transition);
}
.ds-card-flat:hover { border-color: rgba(0,212,255,0.25) !important; }

/* === Stat Cards === */
.ds-stat-card {
    border-radius: var(--ds-radius) !important;
    background: var(--ds-glass) !important;
    border: 1px solid var(--ds-border) !important;
    box-shadow: var(--ds-shadow) !important;
    padding: 20px 24px !important;
    transition: var(--ds-transition);
    min-width: 0;
    backdrop-filter: blur(12px) !important;
    position: relative;
    overflow: hidden;
}
.ds-stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,212,255,0.4), transparent);
}
.ds-stat-card:hover {
    border-color: rgba(0,212,255,0.3) !important;
    box-shadow: var(--ds-shadow), var(--ds-glow) !important;
    transform: translateY(-2px);
}

/* === Buttons === */
.ds-btn-primary {
    background: linear-gradient(135deg, #00d4ff, #0098cc) !important;
    color: #05091a !important;
    border-radius: var(--ds-radius-xs) !important;
    font-weight: 700 !important;
    font-size: 0.8125rem !important;
    text-transform: none !important;
    letter-spacing: 0.01em !important;
    padding: 6px 18px !important;
    box-shadow: 0 0 16px rgba(0,212,255,0.3) !important;
    transition: var(--ds-transition) !important;
}
.ds-btn-primary:hover {
    box-shadow: 0 0 28px rgba(0,212,255,0.5) !important;
    transform: translateY(-1px);
}
.ds-btn-success {
    background: linear-gradient(135deg, #00e87d, #00b361) !important;
    color: #05091a !important;
    border-radius: var(--ds-radius-xs) !important;
    font-weight: 700 !important; font-size: 0.8125rem !important;
    text-transform: none !important; letter-spacing: 0 !important;
    padding: 6px 18px !important;
    box-shadow: 0 0 16px rgba(0,232,125,0.25) !important;
}
.ds-btn-success:hover { box-shadow: 0 0 28px rgba(0,232,125,0.4) !important; }
.ds-btn-danger {
    background: linear-gradient(135deg, #ff3366, #cc0033) !important;
    color: white !important;
    border-radius: var(--ds-radius-xs) !important;
    font-weight: 700 !important; font-size: 0.8125rem !important;
    text-transform: none !important; letter-spacing: 0 !important;
    padding: 6px 18px !important;
    box-shadow: 0 0 16px rgba(255,51,102,0.25) !important;
}
.ds-btn-danger:hover { box-shadow: 0 0 28px rgba(255,51,102,0.4) !important; }
.ds-btn-warning {
    background: linear-gradient(135deg, #ff9f0a, #cc7a00) !important;
    color: #05091a !important;
    border-radius: var(--ds-radius-xs) !important;
    font-weight: 700 !important; font-size: 0.8125rem !important;
    text-transform: none !important; letter-spacing: 0 !important;
    padding: 6px 18px !important;
    box-shadow: 0 0 16px rgba(255,159,10,0.25) !important;
}
.ds-btn-secondary {
    background: transparent !important;
    color: var(--ds-primary) !important;
    border: 1px solid rgba(0,212,255,0.3) !important;
    border-radius: var(--ds-radius-xs) !important;
    font-weight: 600 !important; font-size: 0.8125rem !important;
    text-transform: none !important; letter-spacing: 0 !important;
    padding: 6px 18px !important;
    transition: var(--ds-transition) !important;
}
.ds-btn-secondary:hover {
    background: rgba(0,212,255,0.08) !important;
    border-color: var(--ds-primary) !important;
    box-shadow: 0 0 12px rgba(0,212,255,0.2) !important;
}
.ds-btn-ghost {
    background: transparent !important;
    color: var(--ds-text-2) !important;
    border: none !important;
    border-radius: var(--ds-radius-xs) !important;
    font-weight: 500 !important; font-size: 0.8125rem !important;
    text-transform: none !important; letter-spacing: 0 !important;
    padding: 6px 14px !important;
    transition: var(--ds-transition) !important;
}
.ds-btn-ghost:hover { background: rgba(0,212,255,0.06) !important; color: var(--ds-primary) !important; }

/* === Terminal === */
.ds-terminal {
    border-radius: var(--ds-radius) !important;
    background: rgba(3,6,15,0.95) !important;
    color: #00e87d !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 0.8125rem !important;
    line-height: 1.6 !important;
    border: 1px solid rgba(0,232,125,0.2) !important;
    box-shadow: 0 0 20px rgba(0,232,125,0.05) !important;
}

/* === Table === */
.ds-table .q-table__container {
    border-radius: var(--ds-radius) !important;
    border: 1px solid var(--ds-border) !important;
    background: var(--ds-glass) !important;
    overflow: hidden;
}
.ds-table th {
    font-size: 0.7rem !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.06em !important;
    color: var(--ds-primary) !important;
    background: rgba(0,212,255,0.05) !important;
    border-bottom: 1px solid var(--ds-border) !important;
}
.ds-table td { color: var(--ds-text) !important; border-color: var(--ds-border) !important; }

/* === Tabs === */
.ds-tabs .q-tab {
    text-transform: none !important; font-weight: 500 !important;
    font-size: 0.8125rem !important; letter-spacing: 0 !important;
    color: var(--ds-text-2) !important;
}
.ds-tabs .q-tab--active { font-weight: 700 !important; color: var(--ds-primary) !important; }
.ds-tabs .q-tabs__content { border-bottom: 1px solid var(--ds-border); }
.ds-tabs .q-tab-indicator { background: var(--ds-primary) !important; height: 2px !important; box-shadow: 0 0 8px var(--ds-primary); }

/* === Input === */
.ds-input .q-field__control {
    border-radius: var(--ds-radius-xs) !important;
    background: rgba(10,22,40,0.8) !important;
    border-color: var(--ds-border) !important;
    color: var(--ds-text) !important;
}
.ds-input .q-field__control:hover { border-color: rgba(0,212,255,0.3) !important; }
.ds-input .q-field__label { color: var(--ds-text-2) !important; }

/* === Expansion === */
.ds-expansion .q-expansion-item__container {
    border-radius: var(--ds-radius-sm) !important;
    border: 1px solid var(--ds-border) !important;
    background: rgba(10,22,40,0.5) !important;
    margin-bottom: 6px;
    transition: var(--ds-transition);
}
.ds-expansion .q-expansion-item__container:hover { border-color: rgba(0,212,255,0.25) !important; }

/* === Scrollbar === */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,212,255,0.3); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,212,255,0.6); }

/* === Animations === */
@keyframes ds-fade-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
@keyframes ds-glow-pulse { 0%,100% { box-shadow: 0 0 12px rgba(0,212,255,0.2); } 50% { box-shadow: 0 0 24px rgba(0,212,255,0.4); } }
@keyframes ds-scan { 0% { transform: translateY(-100%); } 100% { transform: translateY(100vh); } }
.ds-animate-in { animation: ds-fade-in 0.3s ease-out; }

/* === Chat Layout === */
.ds-right-drawer {
    background: var(--ds-surface) !important;
    border-left: 1px solid var(--ds-border) !important;
    padding: 0 !important;
}
.ds-chat-container {
    display: flex; flex-direction: column;
    height: 100%; width: 100%; min-height: 0;
    background: var(--ds-bg);
    overflow: hidden;
    position: relative;
    align-self: stretch;
}
.ds-chat-messages {
    flex: 1 1 0; min-height: 0;
    overflow-y: auto;
    padding: 20px 24px;
}

/* === Section Labels === */
.ds-section-label {
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(0,212,255,0.5);
    padding: 4px 16px 6px 16px;
}

/* === Nav Icons & Labels === */
.ds-nav-icon { font-size: 1.2rem; color: var(--ds-text-3); }
.ds-nav-icon-active { font-size: 1.2rem; color: var(--ds-primary); filter: drop-shadow(0 0 6px rgba(0,212,255,0.5)); }
.ds-nav-label { font-size: 0.85rem; font-weight: 500; color: var(--ds-text-2); flex: 1; }
.ds-nav-label-active { font-size: 0.85rem; font-weight: 700; color: var(--ds-primary); flex: 1; }

/* === File Count Badge === */
.ds-file-count-badge {
    font-size: 0.65rem; font-weight: 700;
    color: var(--ds-primary);
    background: rgba(0,212,255,0.12);
    padding: 1px 8px;
    border-radius: 99px;
    border: 1px solid rgba(0,212,255,0.2);
}
.ds-file-tree-label { font-size: 0.8rem; font-weight: 500; color: var(--ds-text-2); flex: 1; }

/* === Chat Messages === */
.ds-msg {
    max-width: 88%;
    border-radius: 14px;
    padding: 14px 18px;
    font-size: 0.875rem;
    line-height: 1.65;
    animation: ds-fade-in 0.25s ease-out;
}
.ds-msg-agent {
    background: rgba(10,22,40,0.8);
    border: 1px solid var(--ds-border);
    border-radius: 14px 14px 14px 4px;
    align-self: flex-start;
    backdrop-filter: blur(8px);
    color: var(--ds-text);
}
.ds-msg-user {
    background: linear-gradient(135deg, #00d4ff 0%, #0098cc 100%);
    color: #05091a;
    font-weight: 600;
    border-radius: 14px 14px 4px 14px;
    align-self: flex-end;
    box-shadow: 0 0 20px rgba(0,212,255,0.3);
}
.ds-msg-suggestion {
    background: rgba(0,212,255,0.05);
    border: 1px solid rgba(0,212,255,0.2);
    border-left: 3px solid var(--ds-primary);
    border-radius: 12px;
    color: var(--ds-text);
}
.ds-msg-result {
    background: rgba(0,232,125,0.05);
    border: 1px solid rgba(0,232,125,0.2);
    border-left: 3px solid var(--ds-success);
    border-radius: 12px;
    color: var(--ds-text);
}
.ds-msg-error {
    background: rgba(255,51,102,0.05);
    border: 1px solid rgba(255,51,102,0.2);
    border-left: 3px solid var(--ds-error);
    border-radius: 12px;
    color: var(--ds-text);
}
.ds-msg-welcome {
    background: linear-gradient(135deg, rgba(0,212,255,0.06) 0%, rgba(124,58,237,0.06) 100%);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 16px;
    text-align: center;
    color: var(--ds-text);
}
.ds-msg-question {
    background: rgba(255,159,10,0.05);
    border: 1px solid rgba(255,159,10,0.2);
    border-left: 3px solid var(--ds-warning);
    border-radius: 12px;
    color: var(--ds-text);
}
.ds-msg-chart {
    background: rgba(10,22,40,0.8);
    border: 1px solid var(--ds-border);
    border-radius: 14px 14px 14px 4px;
    padding: 8px 12px !important;
    color: var(--ds-text);
}
.ds-msg-system-info {
    background: rgba(71,85,105,0.08);
    border: 1px solid rgba(71,85,105,0.2);
    border-left: 3px solid #64748b;
    border-radius: 12px;
    color: var(--ds-text);
}
.ds-msg-history {
    background: rgba(124,58,237,0.05);
    border: 1px solid rgba(124,58,237,0.2);
    border-left: 3px solid #7c3aed;
    border-radius: 12px;
    color: var(--ds-text);
}
.ds-msg-file-list {
    background: rgba(10,22,40,0.8);
    border: 1px solid var(--ds-border);
    border-radius: 14px 14px 14px 4px;
    color: var(--ds-text);
}
.ds-msg-onboarding {
    background: linear-gradient(135deg, rgba(0,212,255,0.06) 0%, rgba(0,232,125,0.06) 100%);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 16px;
    color: var(--ds-text);
}

/* === Chat Input Area === */
.ds-chat-input-area {
    border-top: 1px solid var(--ds-border);
    background: rgba(5,9,26,0.9);
    padding: 12px 24px;
    flex-shrink: 0;
    width: 100%;
    backdrop-filter: blur(12px);
}

/* === Suggestion Chips === */
.ds-chip-row {
    gap: 8px; flex-wrap: wrap;
    padding: 8px 24px 12px 24px;
    max-height: 80px; overflow-y: auto;
    flex-shrink: 0;
    background: rgba(5,9,26,0.7);
}
.ds-suggestion-chip {
    background: rgba(0,212,255,0.06) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 99px !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: none !important;
    letter-spacing: 0.01em !important;
    padding: 4px 16px !important;
    color: var(--ds-primary) !important;
    cursor: pointer !important;
    transition: var(--ds-transition) !important;
}
.ds-suggestion-chip:hover {
    background: rgba(0,212,255,0.15) !important;
    border-color: var(--ds-primary) !important;
    box-shadow: 0 0 12px rgba(0,212,255,0.2) !important;
}

/* === Message Actions === */
.ds-msg-actions { gap: 8px; margin-top: 12px; flex-wrap: wrap; }

/* === Right Panel === */
.ds-right-section {
    padding: 16px 20px;
    border-bottom: 1px solid var(--ds-border);
}
.ds-right-section-title {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(0,212,255,0.5);
    margin-bottom: 12px;
}

/* === Pipeline === */
.ds-pipeline-mini { display: flex; align-items: center; gap: 8px; padding: 8px 0; }
.ds-pipeline-node-mini {
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    padding: 8px 12px; border-radius: 6px;
    border: 1px solid var(--ds-border);
    background: rgba(10,22,40,0.6);
    min-width: 60px;
}

/* === File Cards === */
.ds-file-card {
    border-radius: 10px !important;
    border: 1px solid var(--ds-border) !important;
    padding: 12px 16px !important;
    box-shadow: none !important;
    background: rgba(10,22,40,0.7) !important;
    transition: var(--ds-transition);
    color: var(--ds-text) !important;
}
.ds-file-card:hover {
    border-color: rgba(0,212,255,0.35) !important;
    box-shadow: 0 0 16px rgba(0,212,255,0.1) !important;
}
.ds-review-card {
    border-color: rgba(255,159,10,0.3) !important;
    background: rgba(255,159,10,0.05) !important;
}

/* === Upload Area === */
.ds-upload-area { padding: 12px 24px 0 24px; background: transparent; }
.ds-upload-area .q-uploader {
    border: 2px dashed rgba(0,212,255,0.25) !important;
    border-radius: 12px !important;
    background: rgba(0,212,255,0.03) !important;
}
.ds-upload-area .q-uploader:hover { border-color: rgba(0,212,255,0.5) !important; }

/* === Typing Indicator === */
@keyframes ds-typing { 0%, 60%, 100% { opacity: 0.2; } 30% { opacity: 1; } }
.ds-typing-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--ds-primary);
    display: inline-block;
    box-shadow: 0 0 6px var(--ds-primary);
}
.ds-typing-dot:nth-child(1) { animation: ds-typing 1.4s infinite 0s; }
.ds-typing-dot:nth-child(2) { animation: ds-typing 1.4s infinite 0.2s; }
.ds-typing-dot:nth-child(3) { animation: ds-typing 1.4s infinite 0.4s; }

/* === Onboarding === */
.ds-onboarding-step { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ds-onboarding-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ds-text-3); flex-shrink: 0; }
.ds-onboarding-dot.active { background: var(--ds-primary); width: 10px; height: 10px; box-shadow: 0 0 8px var(--ds-primary); }
.ds-onboarding-dot.completed { background: var(--ds-success); box-shadow: 0 0 8px var(--ds-success); }

/* === Connector Cards === */
.ds-connector-card {
    border-radius: 10px !important;
    border: 1px solid var(--ds-border) !important;
    padding: 12px 16px !important;
    box-shadow: none !important;
    background: rgba(10,22,40,0.7) !important;
    transition: var(--ds-transition);
    color: var(--ds-text) !important;
}
.ds-connector-card:hover { border-color: rgba(0,212,255,0.3) !important; }
.ds-connector-connected { border-left: 3px solid var(--ds-success) !important; }
.ds-connector-available { border-left: 3px solid var(--ds-text-3) !important; }

/* === Artifact Cards === */
.ds-artifact-card {
    border-radius: 8px !important;
    border: 1px solid var(--ds-border) !important;
    padding: 10px 14px !important;
    box-shadow: none !important;
    background: rgba(10,22,40,0.7) !important;
    transition: var(--ds-transition);
    cursor: pointer; margin-bottom: 6px;
    color: var(--ds-text) !important;
}
.ds-artifact-card:hover { border-color: rgba(0,212,255,0.3) !important; box-shadow: 0 0 12px rgba(0,212,255,0.1) !important; }

/* === Chart Container === */
.ds-chart-container {
    border-radius: 10px !important;
    border: 1px solid var(--ds-border);
    background: rgba(10,22,40,0.8);
    margin-top: 8px; overflow: hidden;
}

/* === Chat Table === */
.ds-chat-table .q-table__container { border-radius: 8px !important; border: 1px solid var(--ds-border) !important; margin-top: 8px; background: rgba(10,22,40,0.8); }
.ds-chat-table th { font-size: 0.7rem !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.06em !important; color: var(--ds-primary) !important; background: rgba(0,212,255,0.05) !important; padding: 6px 10px !important; }
.ds-chat-table td { font-size: 0.8rem !important; padding: 6px 10px !important; color: var(--ds-text) !important; border-color: var(--ds-border) !important; }

/* === File List Items === */
.ds-file-list-item {
    display: flex; align-items: center; gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid var(--ds-border);
    cursor: pointer; transition: var(--ds-transition);
    color: var(--ds-text);
}
.ds-file-list-item:last-child { border-bottom: none; }
.ds-file-list-item:hover { background: rgba(0,212,255,0.05); border-radius: 6px; padding-left: 8px; }

/* === Quick Actions === */
.ds-quick-action {
    background: transparent !important;
    border: 1px solid var(--ds-border) !important;
    border-radius: 8px !important;
    font-size: 0.75rem !important; font-weight: 500 !important;
    text-transform: none !important; letter-spacing: 0 !important;
    padding: 6px 12px !important;
    color: var(--ds-text-2) !important;
    cursor: pointer !important; width: 100%;
    justify-content: flex-start !important;
    transition: var(--ds-transition) !important;
}
.ds-quick-action:hover {
    background: rgba(0,212,255,0.08) !important;
    border-color: rgba(0,212,255,0.3) !important;
    color: var(--ds-primary) !important;
}

/* === Right Toggle === */
.ds-right-toggle {
    position: fixed; right: 0; top: 50%; transform: translateY(-50%);
    z-index: 100;
    background: var(--ds-surface);
    border: 1px solid var(--ds-border);
    border-right: none; border-radius: 8px 0 0 8px;
    padding: 8px 4px; cursor: pointer; transition: var(--ds-transition);
}
.ds-right-toggle:hover { background: rgba(0,212,255,0.1); border-color: rgba(0,212,255,0.3); }

/* === 3-Panel Layout === */
.ds-3panel {
    position: fixed;
    top: 56px; left: 0; right: 0; bottom: 0;
    display: flex;
    overflow: hidden;
}

.ds-left-panel {
    width: 260px; min-width: 260px; max-width: 260px; min-height: 0;
    background: rgba(5,9,26,0.95);
    border-right: 1px solid var(--ds-border);
    display: flex; flex-direction: column;
    overflow-y: auto; padding-top: 8px; flex-shrink: 0;
    backdrop-filter: blur(12px);
    transition: width 0.25s cubic-bezier(0.4,0,0.2,1),
                min-width 0.25s cubic-bezier(0.4,0,0.2,1),
                opacity 0.25s ease;
}
.ds-left-panel.ds-left-collapsed {
    width: 0 !important; min-width: 0 !important;
    overflow: hidden !important; opacity: 0;
    border-right: none !important;
}
.ds-center-panel { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.ds-right-panel {
    width: 320px; min-width: 320px; max-width: 320px; min-height: 0;
    background: rgba(5,9,26,0.95);
    border-left: 1px solid var(--ds-border);
    display: flex; flex-direction: column; overflow: hidden; flex-shrink: 0;
    backdrop-filter: blur(12px);
}

/* === Right Panel Tabs === */
.ds-right-tabs .q-tab { text-transform: none !important; font-weight: 500 !important; font-size: 0.75rem !important; letter-spacing: 0 !important; min-height: 40px !important; padding: 0 12px !important; color: var(--ds-text-2) !important; }
.ds-right-tabs .q-tab--active { font-weight: 700 !important; color: var(--ds-primary) !important; }
.ds-right-tabs .q-tab-panels { flex: 1 1 0; min-height: 0; overflow: hidden; }
.ds-right-tabs .q-tab-panel { height: 100%; overflow-y: auto; padding: 8px; }

/* === Chip === */
.ds-chip { border-radius: 6px !important; font-size: 0.75rem !important; font-weight: 600 !important; }

/* === Backdrop === */
.ds-backdrop {
    display: none; position: fixed; top: 56px; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.6); z-index: 199; transition: opacity 0.2s ease;
    backdrop-filter: blur(4px);
}
.ds-backdrop.active { display: block; }

/* === Quasar overrides for dark theme === */
.q-menu { background: var(--ds-surface) !important; border: 1px solid var(--ds-border) !important; box-shadow: var(--ds-shadow), var(--ds-glow) !important; }
.q-item { color: var(--ds-text) !important; }
.q-item:hover { background: rgba(0,212,255,0.08) !important; color: var(--ds-primary) !important; }
.q-separator { background: var(--ds-border) !important; }
.q-field__control { background: rgba(10,22,40,0.8) !important; }
.q-field__label, .q-field__native, .q-field__input { color: var(--ds-text) !important; }
.q-stepper { background: transparent !important; color: var(--ds-text) !important; }
.q-stepper__step-inner { color: var(--ds-text) !important; }
.q-expansion-item__toggle-icon { color: var(--ds-text-2) !important; }

/* === Slide-in Animations === */
@keyframes ds-slide-in-left { from { transform: translateX(-100%); } to { transform: translateX(0); } }
@keyframes ds-slide-in-right { from { transform: translateX(100%); } to { transform: translateX(0); } }

@media (max-width: 1279px) {
    .ds-right-panel { display: none; }
    .ds-right-panel.ds-panel-visible {
        display: flex; position: fixed; right: 0; top: 56px; bottom: 0; z-index: 200;
        box-shadow: -4px 0 40px rgba(0,0,0,0.5), var(--ds-glow);
        animation: ds-slide-in-right 0.25s ease-out;
    }
}
@media (max-width: 1023px) {
    .ds-left-panel { display: none; }
    .ds-left-panel.ds-panel-visible {
        display: flex; position: fixed; left: 0; top: 56px; bottom: 0; z-index: 200;
        box-shadow: 4px 0 40px rgba(0,0,0,0.5); animation: ds-slide-in-left 0.25s ease-out;
    }
    .ds-right-panel { display: none; }
    .ds-right-panel.ds-panel-visible {
        display: flex; position: fixed; right: 0; top: 56px; bottom: 0; z-index: 200;
        box-shadow: -4px 0 40px rgba(0,0,0,0.5); animation: ds-slide-in-right 0.25s ease-out;
    }
}
@media (max-width: 767px) {
    .ds-left-panel { display: none; width: 280px; min-width: 280px; max-width: 80vw; }
    .ds-left-panel.ds-panel-visible { display: flex; position: fixed; left: 0; top: 56px; bottom: 0; z-index: 200; animation: ds-slide-in-left 0.25s ease-out; }
    .ds-right-panel { display: none; width: 320px; min-width: 280px; max-width: 90vw; }
    .ds-right-panel.ds-panel-visible { display: flex; position: fixed; right: 0; top: 56px; bottom: 0; z-index: 200; animation: ds-slide-in-right 0.25s ease-out; }
    .ds-chat-messages { padding: 12px 16px; }
    .ds-chip-row { padding: 6px 16px 8px 16px; }
    .ds-chat-input-area { padding: 10px 16px; }
    .ds-msg { max-width: 95%; border-radius: 12px; padding: 10px 14px; }
}
</style>
"""


def inject_theme() -> None:
    """Design-System CSS in die Seite injizieren und Dark Mode erzwingen."""
    ui.add_head_html(_CUSTOM_CSS)
    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
    )
    # Force dark mode via Quasar
    ui.add_head_html(
        "<script>"
        "document.addEventListener('DOMContentLoaded',function(){"
        "  document.body.classList.add('body--dark');"
        "  document.documentElement.setAttribute('data-theme','dark');"
        "});"
        "</script>"
    )
    dark = ui.dark_mode()
    dark.enable()


# ---------------------------------------------------------------------------
# Komponenten-Helper (alle mit nativen NiceGUI-Elementen!)
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = "") -> None:
    """Seitentitel mit optionalem Untertitel."""
    with ui.column().classes("gap-1 mb-6 ds-animate-in"):
        ui.label(title).classes("ds-page-title")
        if subtitle:
            ui.label(subtitle).classes("ds-page-subtitle")


def stat_card(
    label: str,
    value: str | int,
    icon: str,
    color: str = "blue",
    suffix: str = "",
) -> ui.label:
    """Crisp Stat-Card. Gibt value-Label zurueck fuer Updates."""
    light_style, _ = _ICON_BG.get(color, _ICON_BG["blue"])
    with ui.card().classes("ds-stat-card flex-1"):
        with ui.row().classes("items-center gap-4 w-full"):
            # Icon-Box mit farbigem Hintergrund
            with ui.element("div").style(
                f"width:40px;height:40px;border-radius:10px;display:flex;"
                f"align-items:center;justify-content:center;{light_style}"
            ):
                ui.icon(icon).style("font-size:1.25rem")
            with ui.column().classes("gap-0 flex-1"):
                ui.label(label).style(
                    "font-size:0.8rem;font-weight:500;color:var(--ds-text-2);letter-spacing:0.01em"
                )
                v_label = ui.label(f"{value}{suffix}").style(
                    "font-size:1.75rem;font-weight:700;letter-spacing:-0.025em;line-height:1.2"
                )
    return v_label


def section_title(title: str, icon: str = "") -> None:
    """Abschnitts-Ueberschrift."""
    with ui.row().classes("items-center gap-2 mt-2 mb-3"):
        if icon:
            ui.icon(icon).style("font-size:1.2rem;color:var(--ds-primary)")
        ui.label(title).style(
            "font-size:1.05rem;font-weight:600;letter-spacing:-0.01em;color:var(--ds-text)"
        )


def section_divider() -> None:
    """Horizontaler Trennstrich."""
    ui.separator().classes("my-6")


def callout(text: str, variant: str = "info", icon: str = "") -> None:
    """Info/Warning/Success/Error Callout-Box mit nativem Icon."""
    bg, border, txt_color = _CALLOUT_COLORS.get(variant, _CALLOUT_COLORS["info"])
    ic = icon or _CALLOUT_ICONS.get(variant, "info")
    with ui.row().style(
        f"background:{bg};border-left:3px solid {border};border-radius:8px;"
        f"padding:14px 18px;gap:10px;align-items:flex-start;width:100%"
    ):
        ui.icon(ic).style(f"font-size:1.1rem;color:{border};margin-top:1px")
        ui.html(f'<span style="font-size:0.8125rem;color:{txt_color}">{text}</span>', sanitize=False)


def status_badge(text: str, variant: str = "neutral") -> None:
    """Kleiner Status-Badge."""
    bg, txt_color = _BADGE_COLORS.get(variant, _BADGE_COLORS["neutral"])
    ui.label(text).style(
        f"font-size:0.7rem;font-weight:600;padding:3px 10px;border-radius:99px;"
        f"background:{bg};color:{txt_color};display:inline-block;letter-spacing:0.01em"
    )


def empty_state(icon: str, title: str, text: str = "") -> None:
    """Leerer Zustand mit Icon, Titel und optionalem Text."""
    with ui.column().classes("w-full items-center ds-animate-in").style("padding:48px 24px"):
        ui.icon(icon).style("font-size:3.5rem;color:var(--ds-text-3);margin-bottom:12px")
        ui.label(title).style("font-size:1.125rem;font-weight:600;color:var(--ds-text)")
        if text:
            ui.label(text).style("font-size:0.875rem;color:var(--ds-text-2);text-align:center")


# ---------------------------------------------------------------------------
# Menschliche Fehlermeldungen
# ---------------------------------------------------------------------------

# Mapping h\u00e4ufiger Fehler auf verst\u00e4ndliche Erkl\u00e4rungen mit konkretem Tipp.
# Pr\u00fcfung erfolgt per Substring-Match (case-insensitive) gegen str(exc).
_ERROR_PATTERNS: list[tuple[str, str, str]] = [
    # (needle, titel, hinweis)
    ("permission denied",
     "Keine Berechtigung",
     "Pr\u00fcfe ob der Ordner beschreibbar ist. Unter macOS unter Systemeinstellungen \u203a Datenschutz \u203a Dateien & Ordner freigeben."),
    ("errno 13",
     "Keine Berechtigung",
     "Der Zielordner l\u00e4sst Schreiben nicht zu. Pr\u00fcfe die Rechte oder w\u00e4hle einen anderen Pfad."),
    ("errno 2", "Datei oder Ordner nicht gefunden",
     "Der angegebene Pfad existiert nicht mehr. Pr\u00fcfe die Einstellungen \u203a Pfade."),
    ("no such file or directory", "Datei oder Ordner nicht gefunden",
     "Der angegebene Pfad existiert nicht mehr. Pr\u00fcfe die Einstellungen \u203a Pfade."),
    ("errno 28", "Festplatte voll",
     "Gib Speicherplatz frei oder w\u00e4hle ein anderes Archiv-Ziel."),
    ("no space left", "Festplatte voll",
     "Gib Speicherplatz frei oder w\u00e4hle ein anderes Archiv-Ziel."),
    ("read-only file system", "Schreibschutz aktiv",
     "Das Ziel ist schreibgesch\u00fctzt. W\u00e4hle einen anderen Ordner."),
    ("connection refused", "Verbindung fehlgeschlagen",
     "Der Server antwortet nicht. Pr\u00fcfe Netzwerk oder Service-Status."),
    ("timeout", "Zeit\u00fcberschreitung",
     "Der Vorgang hat zu lange gedauert. Versuche es erneut oder pr\u00fcfe deine Verbindung."),
    ("ssl", "Sichere Verbindung fehlgeschlagen",
     "Pr\u00fcfe Uhrzeit/Datum und Netzwerk. Ggf. ist ein Proxy oder VPN im Weg."),
    ("authentication failed", "Anmeldung fehlgeschlagen",
     "Pr\u00fcfe Benutzername und Passwort / API-Key in den Einstellungen."),
    ("invalid api key", "API-Key ung\u00fcltig",
     "Der API-Key ist falsch oder abgelaufen. Aktualisiere ihn unter Einstellungen \u203a KI-Unterst\u00fctzung."),
    ("rate limit", "Zu viele Anfragen",
     "Der externe Dienst hat ein Limit erreicht. Warte kurz und versuche es erneut."),
    ("yaml", "Konfiguration fehlerhaft",
     "Die Einstellungen lassen sich nicht laden. Verwende \u201eStandard-Werte einf\u00fcgen\u201c oder pr\u00fcfe die Datei."),
    ("json", "Daten-Datei besch\u00e4digt",
     "Eine interne Daten-Datei hat ein Format-Problem. Ein Neustart l\u00e4dt sie neu."),
    ("tesseract", "OCR nicht verf\u00fcgbar",
     "Tesseract ist nicht installiert. Installiere es mit: brew install tesseract tesseract-lang"),
    ("poppler", "PDF-Konvertierung fehlt",
     "Poppler ist nicht installiert. Installiere es mit: brew install poppler"),
    ("module", "Fehlende Komponente",
     "Ein Python-Paket fehlt. Pr\u00fcfe System-Status \u203a Voraussetzungen."),
]


def friendly_error(exc: Exception | str) -> tuple[str, str]:
    """Verwandelt einen Fehler in (Titel, Tipp) auf Deutsch.

    Unbekannte Fehler werden mit generischem Text zur\u00fcckgegeben,
    die Original-Message bleibt im Tipp lesbar.
    """
    raw = str(exc).strip()
    low = raw.lower()
    for needle, title, hint in _ERROR_PATTERNS:
        if needle in low:
            return title, hint
    short = raw[:160] + ("\u2026" if len(raw) > 160 else "")
    return "Etwas ist schiefgelaufen", short or "Pr\u00fcfe die Logs unter System-Status f\u00fcr Details."


def notify_error(exc: Exception | str, prefix: str = "") -> None:
    """Zeigt einen Fehler als verst\u00e4ndliche Notification.

    Der Prefix wird dem Titel vorangestellt, z.B. "Speichern: ".
    """
    title, hint = friendly_error(exc)
    full = f"{prefix}{title} \u2014 {hint}" if prefix else f"{title} \u2014 {hint}"
    ui.notify(full, type="negative", position="top", multi_line=True, timeout=8000)


def pipeline_visual(
    inbox_count: int = 0,
    review_count: int = 0,
    archive_count: int = 0,
) -> None:
    """Pipeline-Visualisierung: Inbox -> Erkennung -> Archiv / Pruefung.
    Komplett mit nativen NiceGUI-Elementen."""

    def _node(ic: str, ic_color: str, count: int | None, label: str, active: bool) -> None:
        border = "rgba(0,212,255,0.5)" if active else "rgba(0,212,255,0.12)"
        bg = "rgba(0,212,255,0.08)" if active else "rgba(10,22,40,0.7)"
        glow = ";box-shadow:0 0 16px rgba(0,212,255,0.15)" if active else ""
        with ui.column().style(
            f"align-items:center;gap:6px;padding:12px 20px;border-radius:8px;"
            f"border:1px solid {border};background:{bg};min-width:100px{glow}"
        ):
            ui.icon(ic).style(f"font-size:1.3rem;color:{ic_color}")
            if count is not None:
                ui.label(str(count)).style("font-size:1.25rem;font-weight:700;color:var(--ds-text)")
            ui.label(label).style(
                "font-size:0.7rem;font-weight:500;color:var(--ds-text-2);"
                "text-transform:uppercase;letter-spacing:0.04em"
            )

    def _arrow() -> None:
        ui.icon("arrow_forward").style("font-size:1.5rem;color:var(--ds-text-3);padding:0 4px")

    with ui.row().classes("items-center justify-center flex-wrap gap-0 ds-animate-in").style("padding:16px 0"):
        _node("inbox", "#00d4ff", inbox_count, "Inbox", inbox_count > 0)
        _arrow()
        _node("auto_awesome", "#a78bfa", None, "Erkennung", False)
        _arrow()
        _node("archive", "#00e87d", archive_count, "Archiv", archive_count > 0)
        ui.icon("call_split").style("font-size:1.5rem;color:var(--ds-text-3);margin-left:8px")
        _node("rate_review", "#ff9f0a", review_count, "Pruefung", review_count > 0)
