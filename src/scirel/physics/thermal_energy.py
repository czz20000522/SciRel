"""Integrate three pressure profiles over explicit cell-volume weights."""

from __future__ import annotations
from fractions import Fraction
import numpy as np

from scirel._result import Result

__all__ = ["calculate_stored_thermal_energy"]


def _profile(value, name, n=None):
    """Validate one nonempty one-dimensional pressure or geometry profile."""
    a = np.asarray(value)
    if np.ma.isMaskedArray(value) or a.ndim != 1 or a.size == 0 or a.dtype.kind not in "iuf":
        raise ValueError(f"{name} must be a nonempty one-dimensional real array")
    if n is not None and a.size != n:
        raise ValueError("pressure profiles must have equal length")
    a = np.asarray(a, dtype=np.float64)
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be finite")
    return a


def calculate_stored_thermal_energy(p_el, p_ion, p_tot, vpr, drho_norm):
    """Return the three stored thermal energies in joules as a named result.

    Parameters
    ----------
    p_el : array_like, shape (N,)
        Electron pressure profile [Pa]. Finite and real; signed values are
        algebraically accepted.
    p_ion : array_like, shape (N,)
        Ion pressure profile [Pa], with the same length as ``p_el``.
    p_tot : array_like, shape (N,)
        Total pressure profile [Pa], with the same length as ``p_el``.
    vpr : array_like, shape (N,)
        Volume metric per normalized-radius unit [m^3]. Finite and strictly
        positive.
    drho_norm : array_like, shape (N,)
        Cell quadrature widths [dimensionless]. Finite and strictly positive.

    Returns
    -------
    W_el : float
        Field ``W_el`` of the returned ``scirel._result.Result`` mapping:
        electron stored thermal energy [J].
    W_ion : float
        Field ``W_ion`` of the returned result mapping: ion stored thermal
        energy [J].
    W_tot : float
        Field ``W_tot`` of the returned result mapping: total stored thermal
        energy [J].

    Raises
    ------
    ValueError
        If an input is malformed, non-real, non-finite, missing, not
        one-dimensional, unequal in length, or if a weight is nonpositive.
    FloatingPointError
        If a finite result is not representable as float64 or underflows to
        zero.

    See Also
    --------
    calculate_main_ion_dilution_factor : Evaluate a related local composition
        diagnostic.

    Notes
    -----
    Each pressure is integrated independently as

    .. math:: W = 1.5 * sum_i(p_i * vpr_i * drho_i).

    No closure between total, electron and ion pressure is imposed. The
    weighted sums use exact rational arithmetic on the converted binary64
    inputs and round only the final energies, preserving signed cancellation
    without intermediate product overflow or underflow. Physical stored
    thermal energy requires nonnegative thermal pressures.

    The precision budget is therefore one float64 rounding per returned
    component: each energy is the nearest float64 to the exact rational value of
    the stated sum, so the evidence tests compare against ``Fraction`` values
    with no tolerance at all. The two rejection boundaries are exact predicates
    on that same rational value — magnitude above float64 max before rounding,
    and a nonzero value that rounds to zero — and an exact zero is accepted
    rather than treated as underflow.

    The three energies are stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.physics import calculate_stored_thermal_energy
    >>> v=np.array([2.,3.]); d=np.array([.4,.6])
    >>> r=calculate_stored_thermal_energy([2,2],[3,3],[5,5],v,d)
    >>> assert isinstance(r, Result)
    >>> assert list(r) == ['W_el', 'W_ion', 'W_tot']
    >>> assert r.W_el is r['W_el']
    >>> assert np.allclose([r.W_el, r.W_ion, r.W_tot], (7.8, 11.7, 19.5))
    """
    v = _profile(vpr, "vpr")
    d = _profile(drho_norm, "drho_norm", v.size)
    if np.any(v <= 0) or np.any(d <= 0):
        raise ValueError("vpr and drho_norm must be strictly positive")
    pe = _profile(p_el, "p_el", v.size)
    pi = _profile(p_ion, "p_ion", v.size)
    pt = _profile(p_tot, "p_tot", v.size)
    # Finite binary64 values are dyadic rationals. Retaining their exact
    # products and sum makes cancellation independent of order and of the
    # platform's longdouble width. This is the same discrete relation, not
    # an added physical closure or a change to the accepted signed domain.
    weights = [Fraction(float(width)) * Fraction(float(jacobian)) for width, jacobian in zip(v, d)]
    energies = []
    for pressure in (pe, pi, pt):
        integral = sum(
            (Fraction(float(value)) * weight for value, weight in zip(pressure, weights)),
            Fraction(0),
        )
        energies.append(Fraction(3, 2) * integral)
    out = tuple(energies)
    if any(abs(x) > Fraction(float(np.finfo(np.float64).max)) for x in out):
        raise FloatingPointError("thermal energy is not representable as float64")
    result = tuple(float(x) for x in out)
    if any(x != 0 and y == 0 for x, y in zip(out, result)):
        raise FloatingPointError("thermal energy underflows float64")
    return Result(zip(("W_el", "W_ion", "W_tot"), result))
