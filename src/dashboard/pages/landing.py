"""Landing Page: Startseite mit Login oder Registrierung."""

from __future__ import annotations

from nicegui import app, ui

from ..theme import inject_theme
from . import wizard

# ---------------------------------------------------------------------------
# SVG Illustration (Dokument / Ordner futuristisch)
# ---------------------------------------------------------------------------

_DOC_SVG = """
<svg viewBox="0 0 400 420" fill="none" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;height:auto;display:block">
  <defs>
    <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#00d4ff" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#7c3aed" stop-opacity="0.15"/>
    </linearGradient>
    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#00d4ff" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#0098cc" stop-opacity="0.9"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="glow-strong">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="doc-clip">
      <rect x="100" y="75" width="155" height="195" rx="10"/>
    </clipPath>
  </defs>

  <!-- Animated styles -->
  <style>
    @keyframes pulse-ring {
      0%,100% { opacity:0.15; r:160; }
      50%      { opacity:0.35; r:168; }
    }
    @keyframes float-arrow {
      0%,100% { transform: translateY(0px); }
      50%      { transform: translateY(-8px); }
    }
    @keyframes float-folder {
      0%,100% { transform: translateY(0px); }
      50%      { transform: translateY(6px); }
    }
    @keyframes float-check {
      0%,100% { transform: translateY(0px); }
      50%      { transform: translateY(-6px); }
    }
    @keyframes scan {
      0%   { transform: translateY(0px);   opacity:0.8; }
      80%  { transform: translateY(193px); opacity:0.8; }
      100% { transform: translateY(193px); opacity:0; }
    }
    @keyframes dot-orbit {
      from { transform: rotate(0deg)   translateX(130px) rotate(0deg); }
      to   { transform: rotate(360deg) translateX(130px) rotate(-360deg); }
    }
    @keyframes dot-orbit-rev {
      from { transform: rotate(0deg)   translateX(105px) rotate(0deg); }
      to   { transform: rotate(-360deg) translateX(105px) rotate(360deg); }
    }
    @keyframes blink-line {
      0%,100% { opacity:0.3; }
      50%      { opacity:0.7; }
    }
    @keyframes glow-border {
      0%,100% { stroke: rgba(0,212,255,0.45); }
      50%      { stroke: rgba(0,212,255,0.9); }
    }
    @keyframes badge-appear {
      0%,40% { opacity:0; transform:translateX(-6px); }
      60%,100%{ opacity:1; transform:translateX(0); }
    }
    .scan-line   { animation: scan 3.2s linear infinite; }
    .float-arrow { animation: float-arrow 3s ease-in-out infinite; }
    .float-folder{ animation: float-folder 4s ease-in-out infinite; }
    .float-check { animation: float-check 3.5s ease-in-out infinite; }
    .orbit-dot-1 { transform-origin:200px 210px; animation: dot-orbit 8s linear infinite; }
    .orbit-dot-2 { transform-origin:200px 210px; animation: dot-orbit 13s linear infinite 2s; }
    .orbit-dot-3 { transform-origin:200px 210px; animation: dot-orbit-rev 10s linear infinite 1s; }
    .orbit-dot-4 { transform-origin:200px 210px; animation: dot-orbit-rev 16s linear infinite 4s; }
    .blink-1     { animation: blink-line 2.4s ease-in-out infinite; }
    .blink-2     { animation: blink-line 2.4s ease-in-out infinite 0.8s; }
    .blink-3     { animation: blink-line 2.4s ease-in-out infinite 1.6s; }
    .doc-border  { animation: glow-border 2.5s ease-in-out infinite; }
    .badge-tag   { animation: badge-appear 4s ease-in-out infinite; }
    .badge-tag2  { animation: badge-appear 4s ease-in-out infinite 2s; }
    .pulse-ring  { animation: pulse-ring 3s ease-in-out infinite; }
  </style>

  <!-- Background glow ring (pulsing) -->
  <circle class="pulse-ring" cx="200" cy="210" r="160" fill="url(#g1)"/>
  <circle cx="200" cy="210" r="160" stroke="rgba(0,212,255,0.08)" stroke-width="1"/>

  <!-- Cross-hair lines -->
  <line x1="40" y1="210" x2="360" y2="210" stroke="rgba(0,212,255,0.05)" stroke-width="1"/>
  <line x1="200" y1="50"  x2="200" y2="370" stroke="rgba(0,212,255,0.05)" stroke-width="1"/>

  <!-- Orbiting dots -->
  <circle class="orbit-dot-1" cx="200" cy="80"  r="3.5" fill="#00d4ff" opacity="0.7"/>
  <circle class="orbit-dot-2" cx="330" cy="210" r="2.5" fill="#7c3aed" opacity="0.6"/>
  <circle class="orbit-dot-3" cx="200" cy="340" r="3"   fill="#00e87d" opacity="0.6"/>
  <circle class="orbit-dot-4" cx="90"  cy="180" r="2"   fill="#ff9f0a" opacity="0.5"/>

  <!-- Back document -->
  <rect x="130" y="100" width="155" height="195" rx="10"
        fill="rgba(10,22,40,0.9)" stroke="rgba(124,58,237,0.25)" stroke-width="1"/>

  <!-- Middle document -->
  <rect x="115" y="88" width="155" height="195" rx="10"
        fill="rgba(10,22,40,0.95)" stroke="rgba(0,212,255,0.18)" stroke-width="1"/>

  <!-- Front document -->
  <rect x="100" y="75" width="155" height="195" rx="10"
        fill="rgba(8,18,35,0.98)" stroke-width="1.5" filter="url(#glow)"
        class="doc-border"/>

  <!-- Top bar -->
  <rect x="100" y="75" width="155" height="36" rx="10" fill="url(#g2)" opacity="0.9"/>
  <rect x="100" y="97" width="155" height="14"          fill="url(#g2)" opacity="0.9"/>
  <rect x="137" y="88" width="70"  height="7"  rx="3"  fill="rgba(5,9,26,0.6)"/>

  <!-- Content lines (blinking) -->
  <rect class="blink-1" x="118" y="127" width="118" height="5" rx="2" fill="rgba(0,212,255,0.35)"/>
  <rect class="blink-2" x="118" y="140" width="100" height="4" rx="2" fill="rgba(148,163,184,0.22)"/>
  <rect class="blink-3" x="118" y="152" width="112" height="4" rx="2" fill="rgba(148,163,184,0.22)"/>
  <rect class="blink-1" x="118" y="164" width="85"  height="4" rx="2" fill="rgba(148,163,184,0.22)"/>

  <!-- Divider -->
  <line x1="118" y1="178" x2="236" y2="178" stroke="rgba(0,212,255,0.1)" stroke-width="1"/>

  <!-- Meta badges (animated appear) -->
  <rect class="badge-tag" x="118" y="188" width="40" height="14" rx="4"
        fill="rgba(0,212,255,0.1)" stroke="rgba(0,212,255,0.4)" stroke-width="0.8"/>
  <rect class="badge-tag2" x="165" y="188" width="50" height="14" rx="4"
        fill="rgba(124,58,237,0.1)" stroke="rgba(124,58,237,0.4)" stroke-width="0.8"/>

  <rect class="blink-2" x="118" y="210" width="90"  height="4" rx="2" fill="rgba(148,163,184,0.15)"/>
  <rect class="blink-3" x="118" y="222" width="75"  height="4" rx="2" fill="rgba(148,163,184,0.15)"/>
  <rect class="blink-1" x="118" y="234" width="105" height="4" rx="2" fill="rgba(148,163,184,0.15)"/>

  <!-- Confidence badges -->
  <rect x="118" y="250" width="50" height="10" rx="4"
        fill="rgba(0,232,125,0.15)" stroke="rgba(0,232,125,0.5)" stroke-width="0.8"/>
  <rect x="178" y="250" width="30" height="10" rx="4"
        fill="rgba(0,212,255,0.1)" stroke="rgba(0,212,255,0.3)" stroke-width="0.8"/>

  <!-- Animated scan line (clipped to doc) -->
  <g clip-path="url(#doc-clip)">
    <rect class="scan-line" x="100" y="75" width="155" height="3" rx="1"
          fill="rgba(0,212,255,0.7)" filter="url(#glow-strong)"/>
  </g>

  <!-- Floating icon: arrow (top right) -->
  <g class="float-arrow">
    <circle cx="310" cy="120" r="22" fill="rgba(0,212,255,0.08)"
            stroke="rgba(0,212,255,0.45)" stroke-width="1.5" filter="url(#glow)"/>
    <text x="298" y="127" font-size="16" fill="#00d4ff" font-weight="bold">→</text>
  </g>

  <!-- Floating icon: folder (bottom left) -->
  <g class="float-folder">
    <circle cx="72" cy="290" r="22" fill="rgba(124,58,237,0.08)"
            stroke="rgba(124,58,237,0.45)" stroke-width="1.5" filter="url(#glow)"/>
    <text x="60" y="297" font-size="14" fill="#a78bfa" font-weight="bold">▦</text>
  </g>

  <!-- Floating icon: check (bottom right) -->
  <g class="float-check">
    <circle cx="318" cy="290" r="18" fill="rgba(0,232,125,0.08)"
            stroke="rgba(0,232,125,0.5)" stroke-width="1.5" filter="url(#glow)"/>
    <text x="309" y="297" font-size="13" fill="#00e87d" font-weight="bold">✓</text>
  </g>
</svg>
"""


def build() -> None:
    """Landing Page aufbauen."""
    ui.add_head_html(
        "<style>"
        "html, body { overflow: hidden !important; height: 100vh !important; }"
        ".q-page-container, .q-page { overflow: hidden !important; height: 100vh !important; }"
        "</style>"
    )

    # Full-viewport wrapper — kein Scrollen
    with ui.element("div").style(
        "height:100vh;width:100%;display:flex;flex-direction:column;"
        "background:var(--ds-bg);overflow:hidden"
    ):
        # Brand bar (top, centered)
        with ui.element("div").style(
            "width:100%;display:flex;flex-direction:column;align-items:center;"
            "padding:8px 24px 16px"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("description").style(
                    "font-size:2.5rem;color:var(--ds-primary);"
                    "filter:drop-shadow(0 0 12px rgba(0,212,255,0.5))"
                )
                ui.label("Doc-Sorter").style(
                    "font-size:2rem;font-weight:800;letter-spacing:-0.03em;"
                    "background:linear-gradient(135deg,#00d4ff,#a78bfa);"
                    "-webkit-background-clip:text;-webkit-text-fill-color:transparent"
                )
            ui.label("Dokumente automatisch erkennen, benennen und ins richtige Archiv sortieren — vollständig lokal.").style(
                "font-size:0.95rem;color:var(--ds-text-2);text-align:center;margin-top:6px"
            )

        # Accounts laden
        from .wizard import _read_state as _ws_read_state
        _accounts = list(_ws_read_state().get("accounts", {}).keys())
        _slot_colors = ["#00d4ff", "#a78bfa", "#00e87d"]
        _NUM_SLOTS = 3

        # Zustand: welcher Slot ist aktiv, welcher Slot ist ausgewählt
        selected = {"slot": None}   # None = kein Slot gewählt
        slot_tile_refs = {}         # slot_idx -> tile element
        slot_check_refs = {}        # slot_idx -> check element

        # Full-width 2-column body: LEFT = Slot-Picker, RIGHT = SVG
        with ui.element("div").style(
            "flex:1;display:flex;flex-wrap:wrap;width:100%;margin-top:-20px"
        ):

            # ---- Linke Hälfte: Slot-Picker ----
            with ui.element("div").style(
                "flex:1;min-width:340px;display:flex;flex-direction:column;"
                "align-items:center;justify-content:center;padding:24px 40px 40px;gap:24px"
            ):

                # ── Erster-Start-Hinweis (wenn alle Slots leer) ──────────────
                if not _accounts:
                    with ui.element("div").style(
                        "width:100%;max-width:460px;"
                        "border:1px solid rgba(0,212,255,0.2);border-radius:12px;"
                        "background:rgba(0,212,255,0.04);padding:12px 16px;"
                        "display:flex;align-items:center;gap:12px"
                    ):
                        ui.icon("info").style("color:#00d4ff;font-size:1.2rem;flex-shrink:0")
                        with ui.column().classes("gap-0"):
                            ui.label("Willkommen! Erstelle dein erstes Profil.").style(
                                "font-size:0.82rem;font-weight:700;color:#00d4ff"
                            )
                            ui.label("Klicke auf einen der drei Plätze unten, um loszulegen.").style(
                                "font-size:0.72rem;color:var(--ds-text-2)"
                            )

                # ── 3 Profil-Kacheln ─────────────────────────────────────────
                ui.label("Profil wählen").style(
                    "font-size:0.68rem;font-weight:700;color:var(--ds-text-3);"
                    "text-transform:uppercase;letter-spacing:0.08em;width:100%;max-width:460px"
                )
                with ui.element("div").style(
                    "display:flex;gap:14px;width:100%;max-width:460px"
                ):
                    for i in range(_NUM_SLOTS):
                        col = _slot_colors[i]
                        uname = _accounts[i] if i < len(_accounts) else None
                        is_filled = uname is not None

                        tile = ui.element("div").classes(f"ds-profile-slot ds-slot-{i}").style(
                            "border:1px solid rgba(255,255,255,0.1);"
                            "background:rgba(255,255,255,0.03);"
                            "border-radius:16px;padding:18px 10px;"
                            "cursor:pointer;flex:1;display:flex;"
                            "flex-direction:column;align-items:center;gap:10px;"
                            "transition:all 0.2s;position:relative"
                        )
                        slot_tile_refs[i] = tile

                        def _make_slot_click(idx=i, name=uname, filled=is_filled):
                            def _click():
                                selected["slot"] = idx
                                _apply_slot_styles()
                                if filled:
                                    # Passwort-Bereich zeigen
                                    pw_section.set_visibility(True)
                                    new_section.set_visibility(False)
                                    pw_input.set_value("")
                                    err_label.set_text("")
                                else:
                                    # Neu-anlegen-Bereich zeigen
                                    pw_section.set_visibility(False)
                                    new_section.set_visibility(True)
                            return _click

                        tile.on("click", _make_slot_click())

                        with tile:
                            # Profil-Nummer Badge
                            ui.label(f"Profil {i + 1}").style(
                                f"font-size:0.6rem;font-weight:700;color:{col};"
                                f"text-transform:uppercase;letter-spacing:0.08em;"
                                f"background:{col}15;padding:2px 8px;border-radius:99px;"
                                f"border:1px solid {col}30"
                            )

                            if is_filled:
                                # Avatar-Kreis mit Anfangsbuchstabe
                                with ui.element("div").style(
                                    f"width:52px;height:52px;border-radius:50%;"
                                    f"background:{col}20;border:2px solid {col}50;"
                                    f"display:flex;align-items:center;justify-content:center"
                                ):
                                    ui.label(uname[0].upper()).style(
                                        f"font-size:1.4rem;font-weight:800;color:{col}"
                                    )
                                ui.label(uname).style(
                                    "font-size:0.82rem;font-weight:600;"
                                    "color:var(--ds-text);text-align:center;"
                                    "word-break:break-all;max-width:90px"
                                )
                            else:
                                # Leerer Slot
                                with ui.element("div").style(
                                    f"width:52px;height:52px;border-radius:50%;"
                                    f"background:rgba(255,255,255,0.04);"
                                    f"border:2px dashed rgba(255,255,255,0.15);"
                                    f"display:flex;align-items:center;justify-content:center"
                                ):
                                    ui.icon("add").style(
                                        "font-size:1.4rem;color:rgba(255,255,255,0.25)"
                                    )
                                ui.label("Freier Platz").style(
                                    "font-size:0.72rem;color:rgba(255,255,255,0.3);"
                                    "text-align:center;font-style:italic"
                                )

                            # Häkchen (versteckt bis ausgewählt)
                            check = ui.element("div").style(
                                f"display:none;position:absolute;top:8px;right:8px;"
                                f"width:20px;height:20px;border-radius:50%;"
                                f"background:{col};align-items:center;justify-content:center"
                            )
                            slot_check_refs[i] = check
                            with check:
                                ui.icon("check").style(
                                    "font-size:0.75rem;color:#05091a"
                                )

                def _apply_slot_styles():
                    for idx, tile_el in slot_tile_refs.items():
                        col = _slot_colors[idx]
                        if idx == selected["slot"]:
                            tile_el.style(
                                f"border:2px solid {col};"
                                f"background:{col}12;"
                                f"box-shadow:0 0 20px {col}35;"
                                "border-radius:16px;padding:18px 10px;"
                                "cursor:pointer;flex:1;display:flex;"
                                "flex-direction:column;align-items:center;gap:10px;"
                                "transition:all 0.2s;position:relative"
                            )
                            slot_check_refs[idx].style(
                                f"display:flex;position:absolute;top:8px;right:8px;"
                                f"width:20px;height:20px;border-radius:50%;"
                                f"background:{col};align-items:center;justify-content:center"
                            )
                        else:
                            tile_el.style(
                                "border:1px solid rgba(255,255,255,0.1);"
                                "background:rgba(255,255,255,0.03);"
                                "box-shadow:none;"
                                "border-radius:16px;padding:18px 10px;"
                                "cursor:pointer;flex:1;display:flex;"
                                "flex-direction:column;align-items:center;gap:10px;"
                                "transition:all 0.2s;position:relative"
                            )
                            slot_check_refs[idx].style(
                                "display:none;position:absolute;top:8px;right:8px;"
                                "width:20px;height:20px;border-radius:50%;"
                                "align-items:center;justify-content:center"
                            )

                # ── Passwort-Bereich (gefüllter Slot) ────────────────────────
                pw_section = ui.element("div").style("width:100%;max-width:460px")
                pw_section.set_visibility(False)
                with pw_section:
                    with ui.column().classes("gap-3 w-full"):
                        pw_input = ui.input(
                            label="Passwort",
                            password=True,
                            password_toggle_button=True,
                            placeholder="Passwort eingeben…",
                        ).props("outlined dense dark").style("width:100%")

                        err_label = ui.label("").style(
                            "color:var(--ds-error);font-size:0.8rem;min-height:16px"
                        )

                        def do_login():
                            idx = selected["slot"]
                            if idx is None or idx >= len(_accounts):
                                return
                            u = _accounts[idx]
                            p = pw_input.value
                            if wizard.verify_login(u, p):
                                app.storage.user["logged_in"] = True
                                app.storage.user["username"] = u
                                ui.navigate.to("/")
                            else:
                                err_label.set_text("Falsches Passwort — bitte erneut versuchen.")
                                pw_input.set_value("")

                        pw_input.on("keydown.enter", do_login)

                        ui.button("Anmelden", on_click=do_login, icon="login").props(
                            "unelevated no-caps"
                        ).style(
                            "background:linear-gradient(135deg,#00d4ff,#0098cc);"
                            "color:#05091a;border-radius:10px;"
                            "font-weight:700;font-size:0.9rem;padding:10px;width:100%;"
                            "box-shadow:0 0 20px rgba(0,212,255,0.3)"
                        )

                # ── Neu-anlegen-Bereich (leerer Slot) ────────────────────────
                new_section = ui.element("div").style("width:100%;max-width:460px")
                new_section.set_visibility(False)
                with new_section:
                    with ui.column().classes("gap-3 w-full items-center"):
                        with ui.element("div").style(
                            "border:1px solid rgba(167,139,250,0.2);border-radius:12px;"
                            "background:rgba(167,139,250,0.05);padding:14px 18px;width:100%;max-width:460px"
                        ):
                            with ui.row().classes("items-center gap-2 mb-1"):
                                ui.icon("person_add").style("color:#a78bfa;font-size:1rem")
                                ui.label("Neues Profil anlegen").style(
                                    "font-size:0.88rem;font-weight:700;color:var(--ds-text)"
                                )
                            ui.label(
                                "Dieser Platz ist noch frei. In wenigen Schritten richtest du "
                                "Benutzername, Ordner und Branchenvorlage ein."
                            ).style("font-size:0.75rem;color:var(--ds-text-2);margin-bottom:10px;line-height:1.5")
                            ui.button(
                                "Profil einrichten →",
                                on_click=lambda: ui.navigate.to("/wizard"),
                                icon="rocket_launch",
                            ).props("unelevated no-caps").style(
                                "background:linear-gradient(135deg,#7c3aed,#a78bfa);"
                                "color:white;border-radius:10px;"
                                "font-weight:700;font-size:0.9rem;padding:10px 24px;width:100%;"
                                "box-shadow:0 0 20px rgba(124,58,237,0.3)"
                            )

            # ---- Right half: SVG illustration ----
            with ui.element("div").style(
                "flex:1;min-width:480px;width:50%;"
                "display:flex;align-items:center;justify-content:center;"
                "padding:16px 32px 32px;"
                "border-left:1px solid rgba(0,212,255,0.07)"
            ):
                with ui.element("div").style("width:100%;max-width:680px"):
                    ui.html(_DOC_SVG, sanitize=False)

        # Footer
        with ui.element("div").style("width:100%;text-align:center;padding:12px 0 20px"):
            with ui.row().classes("items-center justify-center gap-2 w-full"):
                ui.icon("lock").style("font-size:0.8rem;color:var(--ds-text-3)")
                ui.label("Alle Daten bleiben auf deinem Ger\u00e4t \u2014 keine Cloud, kein Tracking.").style(
                    "font-size:0.72rem;color:var(--ds-text-3)"
                )
            with ui.row().classes("items-center justify-center gap-3 w-full").style("margin-top:6px"):
                ui.label("Tastatur: 1/2/3 zur Profil-Auswahl, Enter zum Anmelden, Esc zum Abw\u00e4hlen").style(
                    "font-size:0.68rem;color:var(--ds-text-3);opacity:0.7"
                )

    # ── Keyboard-Shortcuts: 1, 2, 3 fuer Profil-Auswahl ──
    ui.add_head_html("""
    <script>
    (function(){
        document.addEventListener('keydown', function(ev){
            const tag = (ev.target && ev.target.tagName) || '';
            if (tag === 'INPUT' || tag === 'TEXTAREA' || ev.target.isContentEditable) return;
            if (ev.key === '1' || ev.key === '2' || ev.key === '3') {
                const idx = parseInt(ev.key, 10) - 1;
                const slot = document.querySelector('.ds-slot-' + idx);
                if (slot) { slot.click(); ev.preventDefault(); }
            }
        });
    })();
    </script>
    """)
