from __future__ import annotations

import re


def _compact(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def extract_command(transcript: str, phrase: str = "hey anna") -> str | None:
    """Return the command text after the wake phrase, or None if the phrase is absent."""
    t = _compact(transcript)
    p = _compact(phrase)
    idx = t.find(p)
    if idx == -1:
        return None
    return t[idx + len(p) :].strip()
