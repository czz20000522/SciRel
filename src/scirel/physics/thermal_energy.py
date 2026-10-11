# Derived from TORAX: Copyright 2024 DeepMind Technologies Limited.
# Licensed under Apache-2.0; retained license: licenses/torax/LICENSE.
"""Discrete stored thermal-energy relation from TORAX pressure profiles.

Source: TORAX f21a878998abd74e6812f57d8bb8891641fecfc6,
torax/_src/physics/formulas.py:calculate_stored_thermal_energy. CellVariable
and Geometry adapters are replaced by explicit vector ports; neither KN1D
energy-transfer rates nor equilibrium pressure closures are absorbed.
"""
from __future__ import annotations
from fractions import Fraction
import numpy as np


def _profile(value, name, n=None):
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
    """Return ``(W_el, W_ion, W_tot)`` in joules.

    Inputs are pressure cell profiles in pascals and the same positive
    ``vpr * drho_norm`` cell-volume weights used by TORAX. Each pressure is
    integrated independently as ``1.5 * sum(p * vpr * drho_norm)``; the
    function does not impose a closure between total, electron and ion
    pressure. Signed finite values preserve TORAX's algebraic behavior;
    physical stored thermal energy requires nonnegative thermal pressures.
    All vectors are nonempty equal-length 1D real inputs (including integer
    and float32/64), converted to float64, with no broadcasting or defaults. A
    The weighted sums use exact rational arithmetic on the converted binary64
    inputs and round only the final energies. This retains small residuals of
    signed cancellation and avoids intermediate product overflow/underflow.
    A nonfinite or unrepresentable result raises ``ValueError`` or
    ``FloatingPointError`` respectively.
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
    weights = [Fraction(float(x)) * Fraction(float(y)) for x, y in zip(v, d)]
    out = tuple(Fraction(3, 2) * sum(
        (Fraction(float(x)) * w for x, w in zip(p, weights)), Fraction(0)
    ) for p in (pe, pi, pt))
    if any(abs(x) > Fraction(float(np.finfo(np.float64).max)) for x in out):
        raise FloatingPointError("thermal energy is not representable as float64")
    result = tuple(float(x) for x in out)
    if any(x != 0 and y == 0 for x, y in zip(out, result)):
        raise FloatingPointError("thermal energy underflows float64")
    return result
