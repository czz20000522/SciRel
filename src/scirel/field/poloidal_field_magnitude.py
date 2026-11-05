"""Poloidal magnetic-field magnitude on a two-dimensional grid."""

import numpy as np

from scirel._result import Result


def compute_poloidal_field_magnitude(br, bz):
    """Return a floored poloidal magnitude and reference as a named result.

    The floor at ``1e-30`` is part of the public numerical contract.  The
    reference is the median computed by a difference-first interpolation so
    two very large neighboring values do not overflow when averaged.

    Parameters
    ----------
    br : real array-like, shape [N_Z,N_R]
        Radial poloidal magnetic-field component [T]. Finite, nonempty
        two-dimensional array with the same shape as ``bz``.
    bz : real array-like, shape [N_Z,N_R]
        Axial poloidal magnetic-field component [T]. Finite, nonempty
        two-dimensional array with the same shape as ``br``.

    Returns
    -------
    B : ndarray of float64, shape [N_Z,N_R]
        Field ``B`` of the returned ``scirel._result.Result`` mapping:
        pointwise floored poloidal-field magnitude [T].
    B0_default : float
        Field ``B0_default`` of the returned result mapping: median of the
        returned magnitude values for use as a caller-selected reference field
        [T].

    Raises
    ------
    ValueError
        If inputs are nonfinite, empty, not two-dimensional, have mismatched
        shapes, or produce an unrepresentable magnitude.

    See Also
    --------
    scirel.field.poloidal_field_from_flux : Poloidal components from flux.

    Notes
    -----
    The two fields are stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access. ``B0_default`` is descriptive and is
    not automatically applied as a normalization.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import compute_poloidal_field_magnitude
    >>> result = compute_poloidal_field_magnitude([[3.0, 0.0]], [[4.0, 0.0]])
    >>> assert isinstance(result, Result)
    >>> assert list(result) == ['B', 'B0_default']
    >>> assert result.B is result['B']
    >>> np.testing.assert_allclose(result['B'], [[5.0, 1.0e-30]])
    >>> assert result['B0_default'] == 2.5
    """
    radial, axial = np.asarray(br, dtype=float), np.asarray(bz, dtype=float)
    if radial.shape != axial.shape or radial.ndim != 2:
        raise ValueError("br and bz must be same-shape two-dimensional [Z,R] arrays")
    if not np.all(np.isfinite(radial)) or not np.all(np.isfinite(axial)):
        raise ValueError("br and bz must contain only finite values")
    if radial.size == 0:
        raise ValueError("br and bz must contain at least one grid point")
    with np.errstate(over="ignore"):
        magnitude = np.maximum(np.hypot(radial, axial), 1.0e-30)
    if not np.all(np.isfinite(magnitude)):
        raise ValueError("poloidal magnitude exceeds the finite floating-point range")
    lower = (magnitude.size - 1) // 2
    upper = magnitude.size // 2
    ordered = np.partition(magnitude.ravel(), (lower, upper))
    reference = ordered[lower] + 0.5 * (ordered[upper] - ordered[lower])
    return Result({"B": magnitude, "B0_default": float(reference)})


__all__ = ["compute_poloidal_field_magnitude"]
