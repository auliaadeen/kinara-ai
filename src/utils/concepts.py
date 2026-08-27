"""Concept-label normalization.

Gemini free-texts concept names per session ("Comparing Fractions" one time,
"fraction comparison" another). masteryMap/weakConcepts tracking only means
something if the same concept always maps to the same key, so every concept
string coming out of Gemini or user input is normalized before it touches
Learning Memory or Firestore.
"""
from __future__ import annotations

import re

_WS_RE = re.compile(r"[^a-z0-9]+")


def normalize_concept(raw: str) -> str:
    slug = _WS_RE.sub("_", raw.strip().lower()).strip("_")
    return slug or "general"
