"""Evaluate a clipped radial envelope for the Frank--Egedal pressure state."""

import numpy as np


def evaluate_frank_egedal_radial_envelope(psi, *, psi_axis=None, psi_edge=None, alpha=1.0):
    """Return the clipped source-order radial pressure envelope.

    Parameters
    ----------
    psi : array_like, shape (N_Z, N_R)
        Finite nonempty axisymmetric flux samples in one caller-selected
        flux convention.
    psi_axis : float or None, default=None
        Flux at the profile axis.  ``None`` selects ``min(psi)``.
    psi_edge : float or None, default=None
        Flux at the profile edge.  ``None`` selects ``max(psi)``.
    alpha : float, default=1.0
        Nonnegative dimensionless power-law exponent.

    Returns
    -------
    radial_envelope : numpy.ndarray
        Dimensionless array with the shape of ``psi``.  Values are clipped to
        the normalized interval before the power is applied.

    Raises
    ------
    ValueError
        If ``psi`` is not a finite nonempty two-dimensional grid, a reference
        flux or exponent is nonfinite, the exponent is negative, or the
        reference interval is smaller than ``1e-30``.

    See Also
    --------
    scirel.kinetic.assemble_frank_egedal_pressure
        Assemble pressure fields using a radial envelope.

    Notes
    -----
    The normalized coordinate is
    ``u = clip((psi - psi_axis) / (psi_edge - psi_axis), 0, 1)`` and the
    returned envelope is ``clip(1 - u, 0, inf) ** alpha``.  Reversing the two
    reference fluxes reverses the profile orientation.  The function does not
    infer physical axis, edge, units or pressure normalization.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import evaluate_frank_egedal_radial_envelope
    >>> psi = np.array([[-1.0, 0.0, 0.5], [1.0, 1.5, 2.0]])
    >>> evaluate_frank_egedal_radial_envelope(
    ...     psi, psi_axis=0.0, psi_edge=1.0, alpha=2.0
    ... )
    array([[1.  , 1.  , 0.25],
           [0.  , 0.  , 0.  ]])
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
