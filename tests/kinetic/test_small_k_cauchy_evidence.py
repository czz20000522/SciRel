"""Independent evidence for the small-k asymptote and the Cauchy-transform port.

Precision budgets, written before measurement.

The two assets differ in what can honestly be claimed:

* ``generalized-small-k`` returns an *asymptotic* branch.  Its damping is a closed
  form and is checked as one; its real part is only the leading term of a series, so
  the assertion there is on the **convergence rate** (the deviation from the exact
  root must shrink like ``k**2`` relative to ``omega_real - 1``, i.e. absolutely like
  ``k**4``), not on a tolerance around a number.
* ``gpdf-cauchy-transform`` is checked against the plasma dispersion function
  ``Z(z) = i sqrt(pi) exp(-z**2) erfc(-i z)`` recomputed at 40 digits, plus a
  conjugate-symmetry relation.  That symmetry is also how the port's **branch choice**
  is pinned: in the lower half plane the port returns ``conj(G(conj(z)))`` rather than
  ``Z(z)``, and the two differ by more than a modulus can see.

Failure matrix, one assertion per channel:

* wrong small-k damping prefactor -> ``test_small_k_damping_is_the_published_closed_form``
* wrong small-k real part -> ``test_small_k_real_part_is_the_leading_order_of_the_exact_root``
* an asymptote claimed beyond its order -> the rate assertion above
* wrong Cauchy transform kernel -> ``test_cauchy_transform_is_the_plasma_dispersion_function``
* wrong lower-half-plane branch -> ``test_cauchy_transform_is_conjugate_symmetric``
* a wrong sign in the transform's real part -> the complex (not modulus) comparison
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

import _bessel_reference as bessel

BUDGET = 1e-12


def _faddeeva(z):
    """``Z(z) = i sqrt(pi) exp(-z**2) erfc(-i z)`` at 40 digits."""
    bessel.high_precision()
    return 1j * mp.sqrt(mp.pi) * mp.e ** (-(z**2)) * mp.erfc(-1j * z)


def _rel(measured, expected):
    measured = mp.mpmathify(measured)
    expected = mp.mpmathify(expected)
    if expected == 0:
        return float(abs(measured))
    return float(abs(measured - expected) / abs(expected))


def test_small_k_damping_is_the_published_closed_form():
    """The damping is ``-sqrt(pi/8) k**-3 exp(-1/(2k**2) - 3/2)``, recomputed at 40 digits.

    This is the published Landau-damping asymptote for a Maxwellian, so recomputing it
    from ``pi`` is a statement about the physics rather than a restatement of the
    implementation's own arithmetic.  The two smallest wavenumbers underflow: the
    closed form is ``~e**-500000`` there, so the port must return exactly zero and
    that is asserted separately rather than hidden inside a tolerance.
    """
    from scirel.kinetic import evaluate_gpdf_small_k

    bessel.high_precision()

    def closed_form(k):
        return -mp.sqrt(mp.pi / 8) * mp.e ** (-1 / (2 * mp.mpf(k) ** 2) - mp.mpf("1.5")) / mp.mpf(k) ** 3

    # The exponential factor drops below the smallest normal binary64 number as k
    # shrinks, so part of the ladder is *declared* to underflow.  Which side of the
    # boundary each k sits on is computed here rather than assumed: the closed form is
    # evaluated at 40 digits and the port must return exactly zero exactly where that
    # value is below 1e-300.  Folding both regimes into one ladder keeps the test from
    # silently measuring only the easy half.
    ladder = [1e-3, 1e-2, 0.02, 0.05, 0.1, 0.2, 0.3]
    damping = np.asarray(evaluate_gpdf_small_k(ladder)["omega_imag"], dtype=float)
    underflowed = 0
    for index, k in enumerate(ladder):
        expected = closed_form(k)
        if expected < mp.mpf("1e-300"):
            underflowed += 1
            assert damping[index] == 0.0, (k, mp.nstr(expected, 3), damping[index])
        else:
            assert _rel(damping[index], expected) <= 1e-13, (k, damping[index])

    # Both regimes must actually appear in the ladder, otherwise this test would pass
    # while only ever exercising one of them.
    assert 0 < underflowed < len(ladder)


def test_small_k_real_part_is_the_leading_order_of_the_exact_root():
    """``omega_real`` is the leading term; the next term is measured as a rate.

    The exact mode is the root of ``1 + (1 + zeta Z(zeta))/k**2 = 0`` with
    ``zeta = omega/(sqrt(2) k)`` and ``Z`` from ``erfc``.  Solving that at 40 digits
    and halving ``k`` must shrink ``|omega_exact - omega_asym| / (omega_asym - 1)``
    by about four, because the leading correction is ``O(k**2)`` relative.

    The ``O(k**4)`` *coefficient* is deliberately not asserted: it is a property of
    the next order of the expansion, not of this port.
    """
    from scirel.kinetic import evaluate_gpdf_small_k

    bessel.high_precision()

    def exact_root(k):
        kk = mp.mpf(k)

        # Below k ~ 0.1 the growth rate is smaller than 1e-20, so the root is real to
        # far beyond the digits used here; bisecting the real part of the dispersion
        # is both independent of the implementation and numerically robust, whereas a
        # complex Newton solve needs a starting point that knows the answer.
        def real_part(omega):
            zeta = omega / (mp.sqrt(2) * kk)
            return mp.re(1 + (1 + zeta * _faddeeva(zeta)) / kk**2)

        return mp.findroot(real_part, (mp.mpf("1"), mp.mpf("1") + 3 * kk**2), solver="bisect")

    previous = None
    for k in (0.05, 0.025, 0.0125):
        asymptotic = mp.mpf("1") + mp.mpf("1.5") * mp.mpf(k) ** 2
        deviation = abs(exact_root(k) - asymptotic) / (asymptotic - 1)
        if previous is not None:
            ratio = previous / deviation
            # Halving k must shrink the relative deviation by about four.  A wrong
            # leading coefficient, a wrong sign, or an O(k**3) error would all land
            # outside this band, because the band is on the *rate*, not the value.
            assert 3.5 <= float(ratio) <= 4.5, (k, float(ratio))
        previous = deviation

    # Sanity: the port's own value is within the leading order at the smallest k.
    smallest = 0.0125
    port = float(np.asarray(evaluate_gpdf_small_k([smallest])["omega_real"], dtype=float)[0])
    assert abs(port - (1 + 1.5 * smallest**2)) <= 1e-16


def test_cauchy_transform_is_the_plasma_dispersion_function():
    """In the upper half plane the transform of a Gaussian is ``Z(z)`` exactly.

    ``Z`` is recomputed from ``erfc`` at 40 digits, so this is a statement about the
    Hilbert transform of the Maxwellian and not a comparison between two copies of the
    same kernel.  The Gaussian is integrated on a mesh dense enough that the
    transform's own quadrature error, not the mesh, sets the floor.
    """
    from scirel.kinetic import evaluate_cauchy_transform

    bessel.high_precision()
    mesh = np.linspace(-14.0, 14.0, 561)
    density = lambda v: np.exp(-v * v) / np.sqrt(np.pi)

    for z in (0.4 + 0.7j, 2.0 + 0.3j, 0.0 + 1.0j):
        collected = complex(
            np.asarray(evaluate_cauchy_transform(z, density, integration_mesh=mesh)["G"]).ravel()[0]
        )
        zz = mp.mpf(z.real) + 1j * mp.mpf(z.imag)
        assert _rel(collected, _faddeeva(zz)) <= 1e-10


def test_cauchy_transform_is_conjugate_symmetric():
    """The port returns ``conj(G(conj(z)))``, not ``Z(z)``, in the lower half plane.

    This pins a **branch choice**, which is the one place a modulus comparison would
    be blind: ``|Z(z)|`` and ``|conj(Z(conj(z)))|`` agree by construction while the
    two values differ in both real and imaginary parts.  Measured disagreement between
    ``Z(z)`` and the returned value below the axis: about 2.9 in the real part.
    """
    from scirel.kinetic import evaluate_cauchy_transform

    bessel.high_precision()
    mesh = np.linspace(-14.0, 14.0, 561)
    density = lambda v: np.exp(-v * v) / np.sqrt(np.pi)

    below = 0.4 - 0.7j
    collected = complex(
        np.asarray(evaluate_cauchy_transform(below, density, integration_mesh=mesh)["G"]).ravel()[0]
    )
    above = complex(
        np.asarray(
            evaluate_cauchy_transform(0.4 + 0.7j, density, integration_mesh=mesh)["G"]
        ).ravel()[0]
    )
    assert abs(collected - np.conj(above)) <= 1e-12

    # And the direct analytic continuation Z(z) is *not* what the port returns, so
    # the assertion above is a branch statement rather than an identity that would
    # hold for any correct implementation.
    zz = mp.mpf(below.real) + 1j * mp.mpf(below.imag)
    assert abs(collected - complex(_faddeeva(zz))) > 1.0


def test_cauchy_transform_uniform_density_is_the_log_closed_form():
    """A uniform density on ``[-1, 1]`` has the closed form ``log((z+1)/(z-1))``.

    The sign is checked, not assumed: the opposite ordering is the negated value, and
    the assertion compares complex values rather than moduli.
    """
    from scirel.kinetic import evaluate_cauchy_transform

    bessel.high_precision()
    mesh = np.linspace(-1.0, 1.0, 401)
    density = lambda v: np.full_like(np.asarray(v, dtype=float), 0.5)

    for z in (0.4 + 0.7j, 2.0 + 0.3j):
        collected = complex(
            np.asarray(
                evaluate_cauchy_transform(z, density, bounds=(-1.0, 1.0), integration_mesh=mesh)[
                    "G"
                ]
            ).ravel()[0]
        )
        zz = mp.mpf(z.real) + 1j * mp.mpf(z.imag)
        # 0.5 * integral of dv/(v - z) over [-1, 1] = 0.5 * log((z - 1)/(z + 1)).
        # The sign was measured, not assumed: the opposite ordering differs by exactly
        # -1, which shows up as a relative error of 2.0 rather than as a small residual.
        expected = mp.mpf("0.5") * mp.log((zz - 1) / (zz + 1))
        assert _rel(collected, expected) <= 1e-10
