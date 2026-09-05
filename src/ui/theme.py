"""Zunara AI design system and shared navigation helpers."""
from __future__ import annotations

import html as _html
import streamlit as st

BRAND_NAME = "Zunara AI"
BRAND_TAGLINE = "Your adaptive learning companion"
ACCENT = "#D97706"
ACCENT_SOFT = "rgba(217, 119, 6, 0.08)"
ACCENT_BORDER = "rgba(217, 119, 6, 0.28)"
PRIMARY = "#0F766E"
PRIMARY_SOFT = "rgba(15, 118, 110, 0.08)"
PRIMARY_BORDER = "rgba(15, 118, 110, 0.16)"
PRIMARY_TINT = "#EBF6F4"
CTA_KEY = "zunara-next-cta"

_CSS = f"""
<style>
@media (prefers-reduced-motion: no-preference) {{
  @keyframes zunaraFadeUp {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}
  div[data-testid="stMain"] .block-container > div {{ animation:zunaraFadeUp 380ms ease-out both; }}
}}
div[data-testid="stMetric"] {{ background:#FFFFFF; border:1px solid rgba(16,24,40,0.06); border-radius:12px; padding:0.75rem 0.85rem; box-shadow:0 1px 2px rgba(16,24,40,0.05),0 1px 3px rgba(16,24,40,0.1); }}
div[data-testid="stMetricLabel"] {{ font-size:0.72rem !important; line-height:1.15 !important; }}
div[data-testid="stMetricValue"] {{ font-size:clamp(0.9rem, 1.8vw, 1.12rem) !important; line-height:1.2 !important; white-space:normal !important; overflow-wrap:anywhere !important; word-break:break-word !important; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:12px !important; box-shadow:0 1px 2px rgba(16,24,40,0.04),0 8px 20px -12px rgba(16,24,40,0.18); }}
.zunara-hero {{ padding:1.5rem 1.65rem; border-radius:16px; background:linear-gradient(135deg,{PRIMARY_SOFT},rgba(217,119,0,0.05)); border:1px solid {PRIMARY_BORDER}; margin-bottom:0.75rem; }}
.zunara-hero-eyebrow {{ text-transform:uppercase; letter-spacing:0.06em; font-size:0.72rem; font-weight:700; color:{PRIMARY}; margin-bottom:0.15rem; }}
.st-key-{CTA_KEY} {{ border-radius:16px !important; padding:1.1rem 1.35rem !important; background:linear-gradient(135deg,{ACCENT_SOFT},{PRIMARY_SOFT}) !important; border:1.5px solid {ACCENT_BORDER} !important; margin-bottom:0.5rem; }}
.zunara-cta-eyebrow {{ display:inline-flex; align-items:center; gap:0.35rem; text-transform:uppercase; letter-spacing:0.06em; font-size:0.72rem; font-weight:700; color:{ACCENT}; margin-bottom:0.3rem; }}
.zunara-avatar {{ display:inline-flex; align-items:center; justify-content:center; width:30px; height:30px; border-radius:50%; background:{PRIMARY}; color:white; font-weight:700; font-size:0.85rem; flex:none; }}
.zunara-progress-metric {{ box-sizing:border-box; width:100%; min-height:76px; padding:0.65rem 0.7rem; border:1px solid rgba(16,24,40,0.10); border-radius:12px; background:#FFFFFF; box-shadow:0 1px 2px rgba(16,24,40,0.05),0 4px 12px -8px rgba(16,24,40,0.18); overflow:hidden; }}
.zunara-progress-label {{ font-size:0.7rem; line-height:1.15; color:rgba(16,24,40,0.62); margin-bottom:0.28rem; font-weight:600; }}
.zunara-progress-metric .zunara-progress-value {{ font-size:0.92rem; font-weight:700; line-height:1.2; overflow-wrap:anywhere; word-break:break-word; }}
</style>
"""

def inject() -> None:
    st.html(_CSS)

def _initial(email: str | None) -> str:
    return _html.escape((email or "?").strip()[:1].upper() or "?")

def render_identity_sidebar(email: str | None, active_view: str, on_logout, role: str = "parent") -> None:
    with st.sidebar:
        st.markdown(f"### :material/psychology: {BRAND_NAME}")
        st.caption("Learner workspace" if role == "learner" else "Parent workspace")
        steps = [
            ("dashboard", "My Learning" if role == "learner" else "Dashboard", ":material/school:" if role == "learner" else ":material/dashboard:"),
            ("history", "History", ":material/history:"),
            ("settings", "Settings", ":material/settings:"),
        ]
        for key, label, icon in steps:
            if st.button(label, icon=icon, width="stretch", type="primary" if active_view == key else "secondary", key=f"nav_{role}_{key}"):
                st.session_state.view = key
                st.rerun()
        if active_view in {"session", "results"}:
            st.caption(f"Current: {active_view.title()}")
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f'<span class="zunara-avatar">{_initial(email)}</span>', unsafe_allow_html=True)
            st.caption(email or "")
        if st.button("Log out", icon=":material/logout:", width="stretch"):
            on_logout()

def hero(eyebrow: str, title: str, subtitle: str | None = None) -> None:
    parts = [f'<div class="zunara-hero"><div class="zunara-hero-eyebrow">{_html.escape(eyebrow)}</div>']
    parts.append(f"<h2 style='margin:0'>{_html.escape(title)}</h2>")
    if subtitle:
        parts.append(f"<p style='margin:0.3rem 0 0 0; opacity:0.8'>{_html.escape(subtitle)}</p>")
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

def cta_eyebrow(icon: str, text: str) -> None:
    st.markdown(f'<div class="zunara-cta-eyebrow">:material/{icon}: {_html.escape(text)}</div>', unsafe_allow_html=True)

def section_title(icon: str, title: str) -> None:
    st.markdown(f"### :material/{icon}: {title}")
