"""Pure-Python access to the packaged SI fluid example deck."""

from __future__ import annotations

from pathlib import Path

import numpy as np

_DECK = Path(__file__).resolve().parent / "_data" / "fluid_SI.in"


def fluid_deck():
    r"""Load the packaged SI multifluid example deck.

    Returns
    -------
    deck : float64 ndarray
        Independent electron/proton SI deck copy. Shape: (2,10). Constraints: Literal
        table: density 8.7e6 m^-3 per species; the declared physical constants and sound
        speeds are used as given. Units: [C; kg; m^-3; m/s; m/s; m/s; m/s; m/s; m^-1;
        m^-1].

    Raises
    ------
    TypeError
        If arguments are supplied to the no-argument packaged-deck loader.

    See Also
    --------
    fluid_equilibrium_si
        Related kinetic amplitude or dispersion operator in the same workflow.
    fluid_equilibrium_relative_rates
        Related kinetic amplitude or dispersion operator in the same workflow.
    fluid_frequency_pencil
        Related kinetic amplitude or dispersion operator in the same workflow.
    fluid_solve_state
        Related kinetic amplitude or dispersion operator in the same workflow.
    scan_fluid_corrected
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The deck is read from the package-local fluid_SI.in resource. Every call parses
        a fresh NumPy array, so returned decks do not share mutable storage. Supported
        scope: Package-local input data; no checkout or network.

    Examples
    --------
    >>> from scirel.kinetic.dispersion.multifluid import fluid_deck
    >>> a, b = fluid_deck(), fluid_deck()
    >>> assert a.shape == (2, 10)
    >>> assert a is not b
    >>> assert a.dtype.name == "float64"
    >>> assert (a == b).all()
    """

    return np.loadtxt(_DECK, skiprows=1, ndmin=2)


__all__ = ["fluid_deck"]
