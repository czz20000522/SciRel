"""Evaluate the reference electron-density relation."""

from __future__ import annotations

import numpy as np

from scirel._result import Result


def compute_reference_electron_density(density_ref_m3, ion_charge_state):
    """Return the reference electron density as a named result.

    Parameters
    ----------
    density_ref_m3 : array_like, shape (...)
        Positive-ion reference number density in ``[m^-3]``.  Values must be
        finite and nonnegative; zero is valid.
    ion_charge_state : array_like, shape (...)
        Positive ion charge-state multiplier in ``[dimensionless]``.  Values
        must be finite and strictly positive; broadcast with
        ``density_ref_m3``.

    Returns
    -------
    electron_density_ref_m3 : numpy.ndarray
        Charge-state-weighted reference electron number density. [m^-3]
        Shape: common broadcast shape of both inputs, including scalar shape
        ``()``. The top-level return is a ``scirel._result.Result`` mapping;
        this field is available by key and by attribute access.

    Raises
    ------
    ValueError
        If either input is nonfinite or outside its declared domain, or the
        input shapes cannot be broadcast.
    TypeError
        If NumPy cannot convert an input to a numeric array.
    FloatingPointError
        If the validated finite inputs produce a nonfinite product.

    See Also
    --------
    scirel.closures.solve_mirror_quasineutral_closure
        Closure that consumes the reference-density leaf relation.

    Notes
    -----
    The relation is ``electron_density_ref_m3 = ion_charge_state *
    density_ref_m3``.  No multi-ion sum, potential solve, coordinate
    alignment or physical quasineutrality proof is performed.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.closures import compute_reference_electron_density
    >>> r = compute_reference_electron_density([1.0e18, 2.0e18], [1.0, 3.0])
    >>> np.testing.assert_allclose(r['electron_density_ref_m3'], [1.0e18, 6.0e18])
    >>> assert r['electron_density_ref_m3'].shape == (2,)
    """
    density, charge_state = np.broadcast_arrays(
        np.asarray(density_ref_m3, dtype=float), np.asarray(ion_charge_state, dtype=float)
    )
    if not np.all(np.isfinite(density)) or np.any(density < 0.0):
        raise ValueError("density_ref_m3 must be finite and nonnegative")
    if not np.all(np.isfinite(charge_state)) or np.any(charge_state <= 0.0):
        raise ValueError("ion_charge_state must be finite and positive")
    result = charge_state * density
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("electron reference density overflowed")
    return Result(electron_density_ref_m3=result)


__all__ = ["compute_reference_electron_density"]
