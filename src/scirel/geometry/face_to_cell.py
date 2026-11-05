"""Midpoint mapping from a one-dimensional face grid to cell centers."""

from __future__ import annotations

import numpy as np

__all__ = ["face_to_cell"]


def face_to_cell(face):
    """Face to cell midpoint

    Parameters
    ----------
    face : real integer/float numeric one-dimensional array-like; converted to float64
        Face values [same as output] Shape: ``[n]``. finite numeric one-dimensional array,
        n>=2; nonempty, boolean/string/complex/masked values rejected

    Returns
    -------
    cell : float64 array
        Cell midpoint values [same as input] Shape: ``[n-1]``. finite; one fewer entry than
        face

    Raises
    ------
    ValueError
        Raises ValueError for boolean/string/complex/masked or empty input, non-finite values, malformed or incompatible shape;
    FloatingPointError
        Raises FloatingPointError if an accepted midpoint unexpectedly becomes nonfinite;

    See Also
    --------
    scirel.neoclassical.bootstrap_current : Consumer of face-to-cell averaging

    Notes
    -----
    Adjacent arithmetic midpoint; output has one fewer entry and same units. Sum first when
    representable, otherwise sum halved endpoints; no invented geometry or coordinate
    fallback.

    **Coordinates.** face index order; no coordinate values consumed

    **Boundary.** finite real one-dimensional face vector with at least two entries

    **Preconditions.**

    * finite real one-dimensional face vector with at least two entries

    **Limits.**

    * Whole-transport evolution, experimental calibration, and implicit coordinate
      reconstruction.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import face_to_cell
    >>> np.testing.assert_array_equal(face_to_cell([0.,2.,8.,10.]), [1.,5.,9.])
    """
    try:
        raw = np.asarray(face)
    except (TypeError, ValueError) as exc:
        raise ValueError("face must be a finite real one-dimensional array") from exc
    if raw.ndim != 1 or raw.size < 2 or raw.dtype.kind not in "iuf":
        raise ValueError("face must be a finite real one-dimensional array of at least two values")
    if np.ma.isMaskedArray(face) or any(
        isinstance(item, (bool, np.bool_)) for item in np.asarray(face, dtype=object).flat
    ):
        raise ValueError("face must be a finite real one-dimensional array of at least two values")
    values = raw.astype(np.float64, copy=False)
    if not np.isfinite(values).all():
        raise ValueError("face must contain only finite values")
    left, right = values[:-1], values[1:]
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        summed = left + right
        result = np.where(np.isfinite(summed), summed * 0.5, left * 0.5 + right * 0.5)
    if not np.isfinite(result).all():
        raise FloatingPointError("face midpoint is not representable")
    return result
