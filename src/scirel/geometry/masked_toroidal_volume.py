"""Compute a masked toroidal volume from an explicit finite R/Z grid."""

from __future__ import annotations

from math import pi

import numpy as np

__all__ = ["plasma_volume"]


def plasma_volume(
    R: np.ndarray,
    dR: float,
    dZ: float,
    core_mask: np.ndarray,
) -> float:
    """Masked finite-grid toroidal volume

    Parameters
    ----------
    R : real array
        Major-radius coordinate array for the finite R/Z grid. [m] Shape: ``array-like,
        conventionally [N_R,N_Z]``. Used as supplied by NumPy arithmetic; the implementation
        does not sort, validate finiteness or infer a mesh.

    dR : real scalar
        Uniform radial cell width. [m] Shape: ``scalar``. Used as supplied; zero, negative
        and non-finite values are not separately rejected.

    dZ : real scalar
        Uniform vertical cell width. [m] Shape: ``scalar``. Used as supplied; zero, negative
        and non-finite values are not separately rejected.

    core_mask : Boolean or numeric array
        Caller-supplied core or limiter mask, optionally carrying numeric cell weights.
        [dimensionless] Shape: ``broadcast-compatible with R``. Broadcasting follows NumPy.
        No implicit mask is constructed and values are not clipped to [0,1].

    Returns
    -------
    volume : Python float
        Summed toroidally revolved finite-grid volume. [m^3] Shape: ``scalar``. Finite, NaN
        or infinite according to the supplied arithmetic; no physical validity filter is
        applied.

    Raises
    ------
    ValueError
        Underlying array, spline, or interpolation validation errors propagate;
        the callable adds no input repair or fallback.

    See Also
    --------
    scirel.geometry : Geometry namespace

    Notes
    -----
    Form 2*pi*R*dR*dZ elementwise, multiply by core_mask using NumPy broadcasting, sum all
    elements and project the scalar to a Python float.

    **Coordinates.** R contains major-radius coordinates at the supplied grid locations; no
    coordinate transformation or mesh reconstruction is performed.

    **Boundary.** The caller-supplied mask defines the included region. Numeric mask values
    are weights, and values outside a Boolean interpretation are not clipped.

    **Preconditions.**

    * The caller supplies a finite-grid R/Z measure and a mask representing the region to
      include.
    * R, dR and dZ use one consistent length unit, and the caller accepts the discrete
      cell-sum approximation.

    **Limits.**

    * Equilibrium solving, limiter or separatrix construction, and topology inference.
    * Nonuniform-cell quadrature, mesh convergence estimation and geometric boundary
      correction.
    * A claim that the returned sum is a physically validated plasma volume for an arbitrary
      caller mask.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import plasma_volume
    >>> R = np.array([[1.0, 1.0], [2.0, 2.0]])
    >>> mask = np.array([[True, False], [True, False]])
    >>> volume = plasma_volume(R, dR=0.5, dZ=0.25, core_mask=mask)
    >>> np.testing.assert_allclose(volume, 2.0 * np.pi * (1.0 + 2.0) * 0.5 * 0.25)
    """
    volume_element = 2.0 * pi * R * dR * dZ
    volume_element *= core_mask
    return float(np.sum(volume_element))
