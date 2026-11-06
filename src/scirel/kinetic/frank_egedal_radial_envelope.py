"""Evaluate a clipped radial envelope for the Frank--Egedal pressure state."""

import numpy as np


def evaluate_frank_egedal_radial_envelope(psi, *, psi_axis=None, psi_edge=None, alpha=1.0):
    """Evaluate a clipped power-law envelope on a normalized two-dimensional flux grid, with optional explicit reference fluxes and exponent.

    Parameters
    ----------
    psi : float64-convertible array-like, nonempty [N_Z,N_R]
        Axisymmetric flux grid whose elements are normalized between two reference levels. [same flux unit as psi_axis and psi_edge; historical source label Wb] Constraints: np.asarray(..., dtype=float) must produce a finite two-dimensional nonempty array.
    psi_axis : float or None, scalar or null
        Flux at the profile axis; None selects the grid minimum. [same as psi] Constraints: Finite after float conversion when supplied. Default: ``None``.
    psi_edge : float or None, scalar or null
        Flux at the profile edge; None selects the grid maximum. [same as psi] Constraints: Finite after float conversion when supplied; distinct from psi_axis by at least 1e-30 in absolute value. Default: ``None``.
    alpha : float, scalar
        Power-law exponent for the clipped envelope. [dimensionless] Constraints: Finite and nonnegative after float conversion. Default: ``1.0``.

    Returns
    -------
    radial_envelope : float64 ndarray, same [N_Z,N_R] shape as psi
        Direct array return of the clipped source-order radial multiplier, not a key in a result mapping. [dimensionless] Constraints: For successful finite arithmetic, values lie in [0,1]. An alpha of zero returns ones, even at u=1; there is no post-computation finite-output validation.

    Raises
    ------
    ValueError
        If ``psi``, a reference flux or the exponent is not finite, ``psi`` is
        not a nonempty two-dimensional grid, the exponent is negative, or the
        reference interval has magnitude below ``1e-30``.
    TypeError
        If numeric conversion of an input fails with a native TypeError.
    See Also
    --------
    scirel.kinetic.assemble_frank_egedal_pressure
        Assemble pressure fields using this radial envelope.
    Notes
    -----
    The normalized coordinate is ``u = clip((psi - psi_axis) / (psi_edge - psi_axis), 0, 1)`` and the envelope is ``clip(1-u, 0, inf)**alpha``. Reversing the reference fluxes reverses the profile orientation. ``alpha=0`` returns one everywhere, including the outer endpoint. The function infers no physical axis, edge, pressure normalization or profile validity, and it performs no general finite-output check after the power evaluation.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import evaluate_frank_egedal_radial_envelope
    >>> psi = np.array([[-1.0, 0.0, 0.5], [1.0, 1.5, 2.0]])
    >>> r = evaluate_frank_egedal_radial_envelope(
    ...     psi, psi_axis=0.0, psi_edge=1.0, alpha=2.0
    ... )
    >>> np.testing.assert_allclose(r, [[1.0, 1.0, 0.25], [0.0, 0.0, 0.0]])
    >>> assert r.shape == psi.shape

    """
    psi = np.asarray(psi, dtype=float)
    if psi.ndim != 2 or psi.size == 0 or not np.all(np.isfinite(psi)):
        raise ValueError("psi must be a finite two-dimensional [Z,R] grid")
    axis = float(np.nanmin(psi) if psi_axis is None else psi_axis)
    edge = float(np.nanmax(psi) if psi_edge is None else psi_edge)
    exponent = float(alpha)
    denominator = edge - axis
    if (
        not np.all(np.isfinite([exponent, axis, edge, denominator]))
        or exponent < 0.0
        or abs(denominator) < 1.0e-30
    ):
        raise ValueError("psi_edge and psi_axis must define a finite radial profile")
    normalized = np.clip((psi - axis) / denominator, 0.0, 1.0)
    return np.power(np.clip(1.0 - normalized, 0.0, None), exponent)


__all__ = ["evaluate_frank_egedal_radial_envelope"]
