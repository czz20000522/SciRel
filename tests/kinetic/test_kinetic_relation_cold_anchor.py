"""Independent evidence for the kinetic dielectric relation at the cold limit.

The primary anchor is **cross-asset and absolute**: in the cold limit the zero of the
kinetic determinant must sit at the plasma frequency recomputed from the published
relation ``omega_p**2 = sum n q**2/(eps0 m)`` by the B5 fluid reference helper
(``_cold_fluid_spectrum_reference.case_scales``), which is an independent mpmath
reimplementation and shares no code with this port.  Measured agreement is 1.1e-11
relative on ``omega/omega_n``.

Why not "the two internal methods agree": ``determinant_sum_n`` and
``determinant_ronnmark`` are two paths inside the same implementation.  They scale
together and change sign together, so their ratio survives both a ``scale`` and a
``negate`` mutation.  That agreement is still recorded below, but only as the
secondary statement it is.

Failure matrix, one assertion per channel:

* wrong mode location -> ``test_cold_limit_root_is_the_published_plasma_frequency``
* a sign flip of the determinant -> the **orientation** assertion (``det(lo) < 0``
  then ``det(hi) > 0``), not merely "the signs differ", which survives a negation
* a truncated harmonic sum passed off as converged ->
  ``test_two_methods_agree_and_the_harmonic_sum_is_saturated``
* a wrong declared graph shape -> ``test_declared_graph_structure``
* a silent zero ``kx_frac`` -> ``test_zero_kx_frac_is_rejected``
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

import _bessel_reference as bessel
import _cold_fluid_spectrum_reference as fluid

# Declared in the port's unit system: single species, q = m = n00 = T00 = B0 = 1.
COLD_KWARGS = dict(
    B0=1.0,
    qs=[1.0],
    ms=[1.0],
    ns_unit=[1.0],
    n00=1.0,
    T00=1.0,
    kz=1.0,
    kx_frac=1.0,
)
T_COLD = 1e-4


def _plasma_frequency_over_unit():
    """``omega_p / omega_n`` from the B5 helper, which recomputes both from first principles."""
    fluid.high_precision()
    scales = fluid.case_scales([1.0], [1.0], [1.0], [T_COLD], 1.0, 1.0, 1.0)
    total = mp.sqrt(sum(scales["wps2"]))
    return total / mp.mpf(float(scales["wcn"]))


def _determinant(omega_frac, method="ronnmark"):
    from scirel.kinetic.kinetic_dispersion_relation import evaluate_kinetic_dispersion_relation

    result = evaluate_kinetic_dispersion_relation(
        Ts_unit=[T_COLD], omega_frac=float(omega_frac), **COLD_KWARGS
    )
    return complex(np.asarray(result[f"determinant_{method}"]).ravel()[0])


def test_cold_limit_root_is_the_published_plasma_frequency():
    """The cold-limit zero of the kinetic determinant is the recomputed ``omega_p``.

    The bracket is placed by the anchor itself, and the orientation of the determinant
    across it is asserted explicitly (negative below, positive above).  Asserting only
    "the sign changes" would be blind to a negation of the whole determinant, because a
    negated function still changes sign.
    """
    bessel.high_precision()
    target = _plasma_frequency_over_unit()
    low = mp.mpf("0.95") * target
    high = mp.mpf("1.05") * target

    below = _determinant(low).real
    above = _determinant(high).real
    assert below < 0.0, f"determinant is not negative below the root: {below:.3e}"
    assert above > 0.0, f"determinant is not positive above the root: {above:.3e}"

    a, b = low, high
    for _ in range(60):
        middle = (a + b) / 2
        if _determinant(a).real < 0.0:
            a = middle
        else:
            b = middle
    root = (a + b) / 2
    relative = float(abs(root - target) / target)
    assert relative <= 1e-9, f"cold-limit root is off omega_p by {relative:.3e}"


def test_two_methods_agree_and_the_harmonic_sum_is_saturated():
    """The two internal methods agree to 5.5e-7, and raising ``lmx`` no longer changes it.

    This is a *secondary* statement and the contract says so: both quantities are
    returned by the same call, so the ratio is invariant under a common rescaling or
    negation of the determinants.  It is kept because it constrains the harmonic
    truncation, which the absolute anchor above does not.
    """
    from scirel.kinetic.kinetic_dispersion_relation import evaluate_kinetic_dispersion_relation

    differences = {}
    for lmx in (5, 12, 16):
        result = evaluate_kinetic_dispersion_relation(
            Ts_unit=[1.0], omega_frac=2.0, lmx=lmx, **COLD_KWARGS
        )
        sum_n = complex(np.asarray(result["determinant_sum_n"]).ravel()[0])
        ronnmark = complex(np.asarray(result["determinant_ronnmark"]).ravel()[0])
        differences[lmx] = abs(sum_n - ronnmark) / max(abs(sum_n), abs(ronnmark))

    # Measured 5.5e-7 at the default lmx = 5.
    assert differences[5] <= 1e-6
    # Saturation: raising lmx from 12 to 16 must not move the disagreement, which is
    # what "the harmonic sum has converged" means operationally.
    assert abs(differences[16] - differences[12]) <= 1e-9


def test_declared_graph_structure():
    """The returned graph carries the declared branch and ordering shapes."""
    from scirel.kinetic.kinetic_dispersion_relation import evaluate_kinetic_dispersion_relation

    result = evaluate_kinetic_dispersion_relation(
        Ts_unit=[1.0], omega_frac=2.0, **COLD_KWARGS
    )
    assert np.shape(result["graph_order"]) == (6,)
    assert np.shape(result["branches"]) == (8,)


def test_zero_kx_frac_is_rejected():
    """``kx_frac = 0`` is a parameter error, not a physical cold limit.

    The harmonic sum divides by the transverse wavenumber, so a zero ``kx_frac``
    raises ``FloatingPointError``.  Recording this as a contract statement keeps the
    next caller from reading that failure as "the cold limit is unreachable".
    """
    from scirel.kinetic.kinetic_dispersion_relation import evaluate_kinetic_dispersion_relation

    with pytest.raises(FloatingPointError):
        evaluate_kinetic_dispersion_relation(
            Ts_unit=[1.0], omega_frac=2.0, **{**COLD_KWARGS, "kx_frac": 0.0}
        )
