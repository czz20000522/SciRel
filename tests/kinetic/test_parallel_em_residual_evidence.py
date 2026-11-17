"""Independent evidence for the parallel Maxwellian electromagnetic residual.

Why this file exists
--------------------
``em1d_parallel_residual`` evaluates a closed expression built on the plasma dispersion function ``Z``.
Reading ``f`` next to its own ``scale`` cannot tell a correct sign, unit or branch from a wrong one, and
an implementation that is internally consistent can be uniformly wrong.  The anchors below are taken
outside the closed form:

1. **Direct velocity integral (Gauss-Hermite).**  The residual is the Gaussian velocity integral
   ``omega^2 - c2 k^2 - sum_s wps2_s (omega - k vds_s) * int F_s(v)/(omega - k v + pm wcs_s) dv``; this
   file evaluates that integral directly from ``roots_hermite`` nodes, never calling ``Z``, at three
   quadrature orders.  The quadrature is refined first (96 -> 160 -> 224 nodes) so that the comparison
   is not limited by the quadrature itself, then compared to the public residual.
2. **Exact symmetry identities, compared as complex numbers.**  Two transformations leave the integral
   invariant: ``(k, vds) -> (-k, -vds)`` and ``(pm, wcs) -> (-pm, -wcs)``.  Both are compared component by
   component in the complex plane -- not as magnitudes and not through the real part only -- so a sign
   error in either component is visible even when ``abs(f)`` happens to agree.
3. **Cold-limit reduction to the fluid determinant.**  As ``vtzs -> 0`` with fixed ``k``, the kinetic term
   tends to the cold-fluid susceptibility ``wps2 (omega - k vds)/(omega - k vds + pm wcs)``, so the
   residual must approach the cold electromagnetic determinant.  The test measures the *order* of that
   approach (halving ``vt`` must quarter the gap), not just its magnitude, which a wrongly normalized
   term cannot reproduce.

What this file deliberately does not claim
------------------------------------------
* It does not identify this residual with any external kinetic dielectric function (no comparison with a
  Bessel-sum or Z-function implementation from another code); the quadrature anchor is the Gaussian
  integral the model is defined by, not an independent kinetic solver.
* It establishes nothing about root existence, forward error of a solved root, or a condition estimate:
  the near-cancellation ``scale`` is a normalization.
* Sets the drift so the two symmetry identities are non-trivial; the identities are still exact
  bookkeeping facts about the model, so they constrain signs but do not by themselves prove the model's
  physics is right.  That role belongs to the velocity integral.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.special import roots_hermite

from scirel.kinetic.dispersion.parallel import em1d_parallel_residual

# Two species, distinct drifts, distinct signed cyclotron frequencies and a non-unit c2, so a sign or
# unit error in any single term is visible in the integral comparison.
STATE = dict(
    wps2=np.array([1.0, 2.0]),
    vds=np.array([0.2, -0.1]),
    vtzs=np.array([0.7, 1.1]),
    wcs=np.array([0.4, -0.7]),
    c2=9.0,
)
OMEGA = 2.1 + 0.8j
QUADRATURE = (96, 160, 224)
POINTS = [(-0.3, -1), (-0.3, 1), (0.3, -1), (0.3, 1)]


def _velocity_integral(state, omega, k, pm, nodes):
    """Evaluate the Gaussian velocity integral directly, without the plasma dispersion function."""
    abscissae, weights = roots_hermite(nodes)
    total = omega * omega - k * k * state["c2"]
    for wps2, vds, vtzs, wcs in zip(state["wps2"], state["vds"], state["vtzs"], state["wcs"]):
        denominator = omega - k * (vds + vtzs * abscissae) + pm * wcs
        total -= wps2 * (omega - k * vds) * np.sum(weights / np.sqrt(np.pi) / denominator)
    return total


def _cold_determinant(state, omega, k, pm):
    """Cold-fluid limit of the same residual: the ``vt -> 0`` reduction of the kinetic term."""
    total = omega * omega - k * k * state["c2"]
    for wps2, vds, wcs in zip(state["wps2"], state["vds"], state["wcs"]):
        total -= wps2 * (omega - k * vds) / (omega - k * vds + pm * wcs)
    return total


@pytest.mark.parametrize("k,pm", POINTS)
def test_public_residual_matches_the_direct_velocity_integral(k, pm):
    # Anchor 1.  First show the quadrature is converged, then that the closed form equals it.
    integrals = [_velocity_integral(STATE, OMEGA, k, pm, nodes) for nodes in QUADRATURE]
    reference = integrals[-1]
    for coarser in integrals[:-1]:
        assert abs(coarser - reference) / abs(reference) <= 1e-14, (k, pm, coarser, reference)

    f, scale = em1d_parallel_residual(STATE, OMEGA, k, pm=pm)
    assert abs(complex(f) - reference) / scale <= 1e-12, (k, pm, f, reference)


def test_wavevector_and_drift_reflection_is_an_exact_complex_identity():
    # Anchor 2a.  (k, vds) -> (-k, -vds) leaves every denominator unchanged; f must be bit-comparable,
    # component by component, not merely equal in magnitude.
    reflected = dict(STATE, vds=-STATE["vds"])
    for k, pm in POINTS:
        f, scale = em1d_parallel_residual(STATE, OMEGA, k, pm=pm)
        mirror, mirror_scale = em1d_parallel_residual(reflected, OMEGA, -k, pm=pm)
        tolerance = 1e-13 * max(abs(complex(f)), abs(complex(mirror)), 1.0)
        assert abs(complex(f).real - complex(mirror).real) <= tolerance, (k, pm, f, mirror)
        assert abs(complex(f).imag - complex(mirror).imag) <= tolerance, (k, pm, f, mirror)
        assert abs(abs(complex(f)) - abs(complex(mirror))) <= tolerance, (k, pm, f, mirror)
        assert abs(scale - mirror_scale) <= 1e-13 * max(scale, mirror_scale), (
            k,
            pm,
            scale,
            mirror_scale,
        )


def test_polarization_and_cyclotron_sign_is_an_exact_complex_identity():
    # Anchor 2b.  pm and wcs enter only through the combination (omega - k vd + pm wcs), so flipping both
    # is an exact identity; asserted in both components plus the magnitude and the scale.
    flipped = dict(STATE, wcs=-STATE["wcs"])
    for k, pm in POINTS:
        f, scale = em1d_parallel_residual(STATE, OMEGA, k, pm=pm)
        other, other_scale = em1d_parallel_residual(flipped, OMEGA, k, pm=-pm)
        tolerance = 1e-13 * max(abs(complex(f)), abs(complex(other)), 1.0)
        assert abs(complex(f).real - complex(other).real) <= tolerance, (k, pm, f, other)
        assert abs(complex(f).imag - complex(other).imag) <= tolerance, (k, pm, f, other)
        assert abs(abs(complex(f)) - abs(complex(other))) <= tolerance, (k, pm, f, other)
        assert abs(scale - other_scale) <= 1e-13 * max(scale, other_scale), (
            k,
            pm,
            scale,
            other_scale,
        )


def test_cold_limit_reduces_to_the_fluid_determinant_at_second_order():
    # Anchor 3.  Halving the thermal speed must quarter the gap to the cold-fluid determinant; the order
    # is the load-bearing part, because a mis-normalized kinetic term can still be small (but first
    # order) in vt at a single vt.
    cold_state = dict(STATE)
    gaps = []
    for vtzs in (1e-3, 5e-4, 2.5e-4, 1.25e-4):
        state = dict(cold_state, vtzs=np.array([vtzs, vtzs]))
        f, scale = em1d_parallel_residual(state, OMEGA, 0.3, pm=1)
        expected = _cold_determinant(state, OMEGA, 0.3, 1)
        gaps.append(abs(complex(f) - expected) / scale)

    assert gaps[-1] <= 1e-9, gaps
    for finer, coarser in zip(gaps[1:], gaps[:-1]):
        ratio = coarser / finer
        assert 3.5 <= ratio <= 4.5, (gaps, ratio)
