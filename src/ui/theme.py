"""Kinara AI design system (BATCH 1 — frontend/UI/UX only).

Presentation-only helpers: design tokens, global CSS, and small reusable
render functions shared by every screen in `src/ui/`. Nothing in this
module reads or writes Firestore, calls an AI provider, or computes
scores/mastery/recommendations — it only renders values it is given.

Colors/fonts/radius mirror `.streamlit/config.toml` (native Streamlit
theming); the CSS below only adds what config.toml cannot express —
motion, gradients, and hover depth for the hero/CTA panels and cards.

Structure (12px radius, layered neutral shadows, soft-tint/saturated-text
badge triads, filled-pill active nav state) is adapted from TailGrids
(github.com/TailGrids/tailgrids, MIT) with its blue/gray hue swapped for
Kinara's warm teal + amber — see docs/ prompt history for the "blend"
decision (structure from TailGrids, color from Kinara).
"""
from __future__ import annotations

import html as _html

import streamlit as st

BRAND_NAME = "Kinara AI"
BRAND_TAGLINE = "Your child's adaptive learning companion"

# Kept in sync by hand with .streamlit/config.toml [theme.light].
ACCENT = "#D97706"
ACCENT_SOFT = "rgba(217, 119, 6, 0.08)"
ACCENT_BORDER = "rgba(217, 119, 6, 0.28)"
PRIMARY = "#0F766E"
PRIMARY_SOFT = "rgba(15, 118, 110, 0.08)"
PRIMARY_BORDER = "rgba(15, 118, 110, 0.16)"
PRIMARY_TINT = "#EBF6F4"  # teal-50-ish — soft active/selected background

# TailGrids' neutral shadow recipe (rgba(16,24,40,x)) — kept as-is, it
# already reads as neutral rather than warm- or cool-tinted.
_SHADOW_SM = "0 1px 2px rgba(16,24,40,0.05), 0 1px 3px rgba(16,24,40,0.1)"
_SHADOW_MD = "0 1px 2px rgba(16,24,40,0.04), 0 8px 20px -12px rgba(16,24,40,0.18)"
_SHADOW_HOVER = "0 2px 4px rgba(16,24,40,0.06), 0 14px 26px -12px rgba(16,24,40,0.22)"

# Container `key=` used for the "Recommended Next" panel so it can be
# targeted by CSS (see theme.md: `st.container(key=...)` -> `.st-key-...`).
CTA_KEY = "kinara-next-cta"

_STEPS = [
    ("dashboard", "Dashboard"),
    ("session", "Learning session"),
    ("results", "Results"),
]

_CSS = f"""
<style>
@media (prefers-reduced-motion: no-preference) {{
  @keyframes kinaraFadeUp {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  div[data-testid="stMain"] .block-container > div {{
    animation: kinaraFadeUp 380ms ease-out both;
  }}
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
    animation: kinaraFadeUp 360ms ease-out both;
  }}
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1) {{ animation-delay: 20ms; }}
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2) {{ animation-delay: 70ms; }}
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(3) {{ animation-delay: 120ms; }}
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(4) {{ animation-delay: 170ms; }}
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(5) {{ animation-delay: 220ms; }}
}}

div[data-testid="stMetric"] {{
  background: #FFFFFF;
  border: 1px solid rgba(16,24,40,0.06);
  border-radius: 12px;
  padding: 0.95rem 1.1rem;
  box-shadow: {_SHADOW_SM};
  transition: transform 160ms ease, box-shadow 160ms ease;
}}
div[data-testid="stMetric"]:hover {{
  transform: translateY(-2px);
  box-shadow: {_SHADOW_HOVER};
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
  border-radius: 12px !important;
  box-shadow: {_SHADOW_MD};
}}

.kinara-hero {{
  padding: 1.5rem 1.65rem;
  border-radius: 16px;
  background: linear-gradient(135deg, {PRIMARY_SOFT}, rgba(217,119,6,0.05));
  border: 1px solid {PRIMARY_BORDER};
  margin-bottom: 0.75rem;
}}
.kinara-hero-eyebrow {{
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 0.72rem;
  font-weight: 700;
  color: {PRIMARY};
  margin-bottom: 0.15rem;
}}

.st-key-{CTA_KEY} {{
  border-radius: 16px !important;
  padding: 1.1rem 1.35rem !important;
  background: linear-gradient(135deg, {ACCENT_SOFT}, {PRIMARY_SOFT}) !important;
  border: 1.5px solid {ACCENT_BORDER} !important;
  box-shadow: 0 1px 2px rgba(16,24,40,0.05), 0 10px 24px -16px rgba(217,119,6,0.45) !important;
  margin-bottom: 0.5rem;
}}
.kinara-cta-eyebrow {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 0.72rem;
  font-weight: 700;
  color: {ACCENT};
  margin-bottom: 0.3rem;
}}

.kinara-steps {{ margin: 0.2rem 0 1.1rem 0; display: flex; flex-direction: column; gap: 0.15rem; }}
.kinara-step {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  border-radius: 8px;
  font-size: 0.86rem;
  color: inherit;
  opacity: 0.6;
}}
.kinara-step-active {{
  opacity: 1;
  font-weight: 600;
  color: {PRIMARY};
  background: {PRIMARY_TINT};
}}
.kinara-step-dot {{
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor; flex: none;
}}

.kinara-avatar {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px; height: 30px;
  border-radius: 50%;
  background: {PRIMARY};
  color: white;
  font-weight: 700;
  font-size: 0.85rem;
  flex: none;
}}
</style>
"""


def inject() -> None:
    """Injects the shared stylesheet. Safe to call once per screen render."""
    st.html(_CSS)


def _initial(email: str | None) -> str:
    initial = (email or "?").strip()[:1].upper() or "?"
    return _html.escape(initial)


def render_identity_sidebar(email: str | None, active_view: str, on_logout) -> None:
    """Persistent branded sidebar shell shown across every screen.

    `active_view` is one of "dashboard" / "session" / "results" — the same
    values already used by src/app.py's router — rendered as a simple
    step indicator so the app feels like one coherent product rather than
    disconnected pages. `on_logout` is called with no args when the
    logout button is pressed; this function does not touch session_state
    or auth itself.
    """
    with st.sidebar:
        st.markdown(f"### :material/psychology: {BRAND_NAME}")
        st.caption(BRAND_TAGLINE)

        steps_html = ['<div class="kinara-steps">']
        for key, label in _STEPS:
            cls = "kinara-step kinara-step-active" if key == active_view else "kinara-step"
            steps_html.append(
                f'<div class="{cls}"><span class="kinara-step-dot"></span>'
                f'<span>{label}</span></div>'
            )
        steps_html.append("</div>")
        st.markdown("".join(steps_html), unsafe_allow_html=True)

        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f'<span class="kinara-avatar">{_initial(email)}</span>', unsafe_allow_html=True)
            st.caption(email or "")

        if st.button("Log out", icon=":material/logout:", width="stretch"):
            on_logout()


def hero(eyebrow: str, title: str, subtitle: str | None = None) -> None:
    """Warm gradient header panel used at the top of a screen.

    `title`/`subtitle` may contain user-supplied data (e.g. a child's
    name) — always HTML-escaped here before injection.
    """
    safe_title = _html.escape(title)
    parts = [f'<div class="kinara-hero"><div class="kinara-hero-eyebrow">{_html.escape(eyebrow)}</div>']
    parts.append(f"<h2 style='margin:0'>{safe_title}</h2>")
    if subtitle:
        parts.append(f"<p style='margin:0.3rem 0 0 0; opacity:0.8'>{_html.escape(subtitle)}</p>")
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def cta_eyebrow(icon: str, text: str) -> None:
    st.markdown(
        f'<div class="kinara-cta-eyebrow">:material/{icon}: {_html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def section_title(icon: str, title: str) -> None:
    st.markdown(f"### :material/{icon}: {title}")
