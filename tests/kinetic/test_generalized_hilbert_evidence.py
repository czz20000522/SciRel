"""What ``integration_mesh`` is, established by independent quadrature.

Asset: ``scirel.kinetic.generalized-hilbert``.

The open question was the meaning of ``integration_mesh``: quadrature nodes, cell
centres, or breakpoints.  The answer is fixed by an observation that does not
depend on reading the code twice: if the mesh were a set of interpolation nodes or
a sampled density table, a two-point mesh could not reproduce an analytic Cauchy
transform to machine precision.  It does.  The mesh is a list of **finite,
strictly increasing breakpoints** that partition the real axis into panels; each
panel is integrated adaptively, the two infinite tails are integrated separately,
and no value of the density at a mesh point is ever read.

Evidence sources:

1. **mpmath quadrature of the same integral.**  ``Z(z) = integral f(v)/(v - z) dv``
   evaluated at 40 digits with explicit contour breakpoints, for a Lorentzian and
   a Gaussian, compared with the public output on three very different meshes.
2. **The continuation identity.**  ``continuation=True`` must return the plain
   transform plus ``2*pi*i*f(z)`` in the lower half plane and the plain transform
   itself above it; that is checked as an identity against mpmath, not as an
   accuracy claim.
3. **The principal-value branch.**  On the real axis the transform is
   ``PV integral f(v)/(v - x) dv + i*pi*f(x)``; the reference evaluates the same
   expression by subtracting the singularity analytically, so the two routes
   differ in algorithm.

Budgets, fixed before the measurement: ``1e-12`` relative for the off-axis
transform (the implementation's own quadrature tolerance is ``1e-10`` absolute and
both sides are smooth there), ``1e-12`` relative for the continuation identity
(algebraic), and ``1e-9`` absolute for the real-axis principal value (the
subtracted integrand is ``0/0``-free but the adaptive tolerance is absolute).

A measured over-claim is recorded by its own test: the contract says the mesh must
resolve "all material features", yet a Gaussian of width 0.02 is reproduced to
4.5e-16 by a mesh with no breakpoint anywhere near its peak.  The requirement is a
hint for the caller, not a load-bearing condition of this implementation.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import evaluate_generalized_hilbert

mp.mp.dps = 40

LORENTZIAN = "1/(1+v**2)/pi"
GAUSSIAN = "exp(-v.^2)/sqrt(pi)"
NARROW = "exp(-(v/0.02).^2)/(sqrt(pi)*0.02)"

MESHES = {
    "two_point": [-20.0, 20.0],
    "odd": [-17.3, -3.1, 0.0, 2.7, 11.9],
    "fine": list(np.linspace(-20.0, 20.0, 41)),
}
CONTOUR = [-mp.inf, -10, -2, 0, 2, 10, mp.inf]


def _lorentzian(v):
    return 1 / (mp.pi * (1 + v**2))


def _gaussian(v):
    return mp.exp(-(v**2)) / mp.sqrt(mp.pi)


def _narrow(v):
    width = mp.mpf("0.02")
    return mp.exp(-((v / width) ** 2)) / (mp.sqrt(mp.pi) * width)


def _cauchy(density, z):
    z = mp.mpc(z)
    return mp.quad(lambda v: density(v) / (v - z), CONTOUR)


def test_two_point_and_fine_meshes_give_the_same_transform():
    """Evidence 1: the mesh is a breakpoint list, not a table of samples."""
    for expression, density in ((LORENTZIAN, _lorentzian), (GAUSSIAN, _gaussian)):
        for z in (0.4 - 0.7j, 1.3 + 0.9j):
            want = complex(_cauchy(density, z))
            for name, mesh in MESHES.items():
                got = complex(
                    evaluate_generalized_hilbert(
                        z, expression, integration_mesh=mesh, continuation=False
                    )["Z"]
                )
                assert abs(got - want) <= 1e-12 * abs(want), (expression, name, z, got, want)


def test_mesh_values_are_never_read_as_density_samples():
    """Evidence 1, sharper: a mesh point on a feature is not a sample point.

    Moving a breakpoint does not move the answer, which it would if the mesh
    carried density values.
    """
    z = 0.5 - 0.4j
    want = complex(_cauchy(_lorentzian, z))
    for mesh in ([-20.0, 20.0], [-7.0, 7.0], [-1.0, -0.5, 0.5, 1.0]):
        got = complex(
            evaluate_generalized_hilbert(z, LORENTZIAN, integration_mesh=mesh, continuation=False)[
                "Z"
            ]
        )
        assert abs(got - want) <= 1e-12 * abs(want), (mesh, got, want)


def test_continuation_adds_two_pi_i_f_only_below_the_axis():
    """Evidence 2: the identity that defines ``continuation``."""
    z_lower = 0.4 - 0.7j
    plain = complex(
        evaluate_generalized_hilbert(
            z_lower, LORENTZIAN, integration_mesh=MESHES["odd"], continuation=False
        )["Z"]
    )
    continued = complex(
        evaluate_generalized_hilbert(
            z_lower, LORENTZIAN, integration_mesh=MESHES["odd"], continuation=True
        )["Z"]
    )
    expected = plain + 2j * mp.pi * _lorentzian(mp.mpc(z_lower))
    assert abs(continued - complex(expected)) <= 1e-12 * abs(complex(expected))

    z_upper = 0.4 + 0.7j
    upper_plain = complex(
        evaluate_generalized_hilbert(
            z_upper, LORENTZIAN, integration_mesh=MESHES["odd"], continuation=False
        )["Z"]
    )
    upper_continued = complex(
        evaluate_generalized_hilbert(
            z_upper, LORENTZIAN, integration_mesh=MESHES["odd"], continuation=True
        )["Z"]
    )
    assert abs(upper_continued - upper_plain) <= 1e-12 * abs(upper_plain)


def test_real_axis_returns_the_principal_value_plus_i_pi_f():
    """Evidence 3: the on-axis branch, against the subtracted reference."""
    x = 0.7
    f_x = _lorentzian(mp.mpf(x))
    reference = (
        mp.quad(
            lambda v: (
                (_lorentzian(v) - f_x) / (v - mp.mpf(x)) if v != x else mp.diff(_lorentzian, x)
            ),
            CONTOUR,
        )
        + 1j * mp.pi * f_x
    )
    got = complex(
        evaluate_generalized_hilbert(
            x, LORENTZIAN, integration_mesh=MESHES["odd"], continuation=False
        )["Z"]
    )
    assert abs(got - complex(reference)) <= 1e-9, (got, complex(reference))


def test_a_narrow_neighbour_panel_reaches_the_removable_limit_branch():
    """The |offset| < 1e-7 replacement is reachable and correct.

    The contract requires only a finite, strictly increasing mesh with the material
    features resolved; it sets no minimum panel width.  Two panels of width 2e-9
    around the phase put Gauss-Kronrod interior nodes inside the 1e-7 window, so the
    integrand takes the removable limit f'(z) instead of the subtracted quotient.
    84 such nodes were counted with an instrumented copy on this exact input.

    The reference is the analytic removable limit evaluated at 40 digits, so this
    also checks that the replacement value is the right one and not merely finite.
    """
    x = 0.3
    mesh = [-8.0, x - 1e-9, x + 1e-9, 8.0]
    got = complex(
        evaluate_generalized_hilbert(x, LORENTZIAN, integration_mesh=mesh, continuation=False)["Z"]
    )
    f_x = _lorentzian(mp.mpf(x))
    reference = (
        mp.quad(
            lambda v: (
                (_lorentzian(v) - f_x) / (v - mp.mpf(x)) if v != x else mp.diff(_lorentzian, x)
            ),
            CONTOUR,
        )
        + 1j * mp.pi * f_x
    )
    assert abs(got - complex(reference)) <= 1e-12 * abs(complex(reference)), (
        got,
        complex(reference),
    )


def test_the_declared_feature_resolution_is_a_hint_not_a_condition():
    """A measured over-claim, recorded so no contract promises a rejection."""
    z = 0.3 - 0.2j
    want = complex(_cauchy(_narrow, z))
    unresolved = complex(
        evaluate_generalized_hilbert(z, NARROW, integration_mesh=[-40.0, 40.0], continuation=False)[
            "Z"
        ]
    )
    assert abs(unresolved - want) <= 1e-12 * abs(want), (unresolved, want)


def test_declared_mesh_and_expression_rejections_are_executable():
    """One assertion per declared rejection channel of this entry point."""
    z = 0.3 - 0.2j
    with pytest.raises(ValueError, match="finite increasing points"):
        evaluate_generalized_hilbert(z, LORENTZIAN, integration_mesh=[0.0, -0.0])
    with pytest.raises(ValueError, match="finite increasing points"):
        evaluate_generalized_hilbert(z, LORENTZIAN, integration_mesh=[0.0])
    with pytest.raises(ValueError, match="finite increasing points"):
        evaluate_generalized_hilbert(z, LORENTZIAN, integration_mesh=[-1.0, np.nan])
    with pytest.raises(ValueError):
        evaluate_generalized_hilbert(z, "__import__('os')", integration_mesh=[-20.0, 20.0])
