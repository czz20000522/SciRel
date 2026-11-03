"""Pure-Python access to the packaged SI fluid example deck."""

from __future__ import annotations

from pathlib import Path

import numpy as np

_DECK = Path(__file__).resolve().parent / "_data" / "fluid_SI.in"


def fluid_deck():
    """Load the packaged SI fluid example deck without changing its units."""

    return np.loadtxt(_DECK, skiprows=1, ndmin=2)


__all__ = ["fluid_deck"]
