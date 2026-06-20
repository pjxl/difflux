from __future__ import annotations

import math

_FILLED = "█"
_TRACK = "░"


def churn_bar(value: int, max_value: int, width: int = 8) -> str:
    """A fixed-width horizontal bar whose fill length encodes magnitude.

    Length (not glyph height) is what makes the bar scannable down a column, so
    each cluster's churn is drawn as filled cells over a light track, scaled to
    the largest cluster in the current session.

    Scaling is perceptual (square-root): when one cluster dominates, a linear
    scale flattens every other cluster to a single cell. The sqrt curve keeps
    mid-range clusters distinguishable while preserving ordering.
    """
    if width <= 0:
        return ""
    if max_value <= 0 or value <= 0:
        return _TRACK * width
    frac = min(math.sqrt(value) / math.sqrt(max_value), 1.0)
    filled = max(1, round(frac * width))
    return _FILLED * filled + _TRACK * (width - filled)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def meta_label(hunks: int, files: int, added: int, removed: int) -> str:
    """The per-cluster counts row, shared by the TUI and plain-text renderers."""
    return f"{_plural(hunks, 'hunk')} · {_plural(files, 'file')} · +{added} -{removed}"
