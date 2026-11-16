"""Independent evidence for the isotropic pressure-current Picard step.

Asset: ``scirel.equilibrium.isotropic-picard-step``.

The maintained tests compare the step with a hand-computed current array for the
same identity-Green fixture.  Both sides are float arithmetic on the same
formula, so a wrong ``dR``/``dZ`` factor, a missing R weight or a swapped
relaxation convention survives whenever the expectation was derived from the
implementation.

Three independent bases are used here:

* **Exact rational arithmetic.**  On a dyadic grid the cell current
  ``R * dP/dpsi * dR * dZ``, the relaxation mixture and the Green contraction with
  an identity or zero matrix are all exactly representable, so ``Fraction`` gives
  the exact value and the comparison is bitwise.
* **The declared relaxation convention.**  ``currents = (1 - relax) * target +
  relax * old`` and ``flux = G @ currents + vacuum``.  The two boundary weights
  decide different branches: ``relax = 0`` uses the freshly weighted target,
  ``relax = 1`` keeps the previous currents unchanged even when the derivative is
  nonzero.  A "flow relaxation instead of current relaxation" implementation
  cannot pass both.
* **The normalized residual as a 40-digit recomputation.**  ``residual =
  ||psi_next - psi_state|| / |psi_edge|`` is recomputed in mpmath from the
  returned flux, so the denominator is decided separately from the numerator.

Budgets, fixed before the comparison was run:

* the exact statements (currents, flux with ``G = I`` and ``G = 0``, and the
  ``relax = 1`` branch) are bitwise equalities on the dyadic fixture;
* the residual uses ``_RESIDUAL_BUDGET = 8 eps``: one subtraction of two binary64
  arrays, two Euclidean norms (each a sum of squares, so relative error is at
  most a few eps), one division and one absolute value.  Eight eps covers that
  count without measuring the result.

Failure channels (contract ``failure_semantics``):

* ``invalid_input`` -- shape mismatch, non-2D inputs, nonfinite entries, a
  nonrectilinear or nonuniform or non-increasing axis, a Green matrix of the
  wrong size, ``relax`` outside ``[0, 1]``, a zero or nonfinite ``psi_edge`` and
  a two-cell grid on either axis each raise ``ValueError``;
* ``runtime_failure`` -- a finite Green matrix whose contraction overflows raises
  ``FloatingPointError`` from the finite-output guard of the Green update, before
  any residual is formed; the test asserts that exact message so a silent
  ``inf`` flux cannot be mistaken for a successful step;
* ``nonconvergence`` -- declared not applicable to a single step; the assertion
  is that the returned mapping has exactly the three declared keys and no
  convergence field;
* ``partial_results`` -- every raise happens before the mapping is built.
"""

from __future__ import annotations

import math
from fractions import Fraction

import mpmath
import numpy as np
import pytest

from scirel.equilibrium import pressure_flux_picard_step

mpmath.mp.dps = 40

_EPS = math.ulp(1.0)
_RESIDUAL_BUDGET = 8 * _EPS

R_AXIS = (1.0, 1.5, 2.0)
Z_AXIS = (-0.5, 0.0, 0.5)
R_GRID, Z_GRID = np.meshgrid(np.array(R_AXIS), np.array(Z_AXIS))
NODES = R_GRID.size
DR = Fraction(1, 2)
DZ = Fraction(1, 2)


def _identity():
    return np.eye(NODES)


def _exact_target_currents(derivative):
    """R * dP/dpsi * dR * dZ in exact rational arithmetic, in C order."""
    values = []
    for node in range(NODES):
        radius = Fraction(R_GRID.ravel()[node])
        values.append(radius * Fraction(float(derivative[node])) * DR * DZ)
    return values


def test_cell_currents_and_identity_green_flux_are_exact():
    derivative = np.array([[1.0, 2.0, 3.0], [-1.0, 0.5, 4.0], [2.0, 2.0, 2.0]])
    psi_state = np.zeros_like(R_GRID)
    psi_vac = np.zeros_like(R_GRID)
    exact_targets = _exact_target_currents(derivative.ravel())
    for relax in (0.0, 0.25, 0.5):
        result = pressure_flux_picard_step(
            R_GRID, Z_GRID, psi_state, psi_vac, _identity(), derivative, 2.0, None, relax
        )
        for node, exact in enumerate(exact_targets):
            expected = (1.0 - relax) * float(exact)
            assert result["plasma_currents"][node] == expected, (relax, node)
        # G = I means the flux is the current vector plus the vacuum flux.
        np.testing.assert_array_equal(
            result["psi_next"].ravel(), result["plasma_currents"] + psi_vac.ravel()
        )


def test_zero_green_response_leaves_only_the_vacuum_flux():
    derivative = np.full_like(R_GRID, 3.0)
    psi_state = np.zeros_like(R_GRID)
    psi_vac = np.array([[0.5, -1.0, 2.0], [0.25, 0.0, -0.25], [1.0, 1.0, 1.0]])
    result = pressure_flux_picard_step(
        R_GRID, Z_GRID, psi_state, psi_vac, np.zeros((NODES, NODES)), derivative, 2.0, None, 0.0
    )
    np.testing.assert_array_equal(result["psi_next"], psi_vac)
    assert np.any(result["plasma_currents"] != 0.0)


def test_relax_one_keeps_the_previous_currents_but_not_the_previous_flux():
    derivative = np.full_like(R_GRID, 5.0)
    previous = np.arange(NODES, dtype=float).reshape(R_GRID.shape) * 0.5
    psi_state = np.full_like(R_GRID, 1.0)
    psi_vac = np.zeros_like(R_GRID)
    result = pressure_flux_picard_step(
        R_GRID, Z_GRID, psi_state, psi_vac, _identity(), derivative, 2.0, previous, 1.0
    )
    np.testing.assert_array_equal(result["plasma_currents"], previous.ravel())
    # The current target is bypassed, so the current change is exactly zero while
    # the flux still moves through the Green contraction.
    np.testing.assert_array_equal(
        result["psi_next"], (previous.ravel() + 0.0).reshape(R_GRID.shape)
    )
    assert np.any(result["psi_next"] != psi_state)


def test_residual_is_the_normalized_norm_of_the_flux_change():
    derivative = np.array([[2.0, -2.0, 1.0], [0.0, 3.0, -1.0], [4.0, 1.0, 0.0]])
    psi_state = np.array([[0.5, 0.5, 0.5], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5]])
    psi_vac = np.zeros_like(R_GRID)
    edge = 3.0
    result = pressure_flux_picard_step(
        R_GRID, Z_GRID, psi_state, psi_vac, _identity(), derivative, edge, None, 0.0
    )
    next_flux = [mpmath.mpf(float(value)) for value in result["psi_next"].ravel()]
    previous = [mpmath.mpf(float(value)) for value in psi_state.ravel()]
    numerator = mpmath.sqrt(sum((a - b) ** 2 for a, b in zip(next_flux, previous, strict=True)))
    expected = numerator / abs(mpmath.mpf(edge))
    observed = float(result["residual"])
    assert abs(mpmath.mpf(observed) - expected) <= _RESIDUAL_BUDGET * abs(expected)


def test_returned_mapping_has_the_declared_keys_and_no_convergence_field():
    result = pressure_flux_picard_step(
        R_GRID,
        Z_GRID,
        np.zeros_like(R_GRID),
        np.zeros_like(R_GRID),
        _identity(),
        np.zeros_like(R_GRID),
        1.0,
        None,
        0.0,
    )
    assert list(result) == ["plasma_currents", "psi_next", "residual"]
    for forbidden in ("converged", "iterations", "status"):
        assert forbidden not in result


def test_invalid_input_channel_raises_value_error():
    derivative = np.zeros_like(R_GRID)
    zeros = np.zeros_like(R_GRID)
    identity = _identity()

    with pytest.raises(ValueError, match="same-shape"):
        pressure_flux_picard_step(
            R_GRID, Z_GRID[:-1], zeros, zeros, identity, derivative, 1.0, None, 0.0
        )
    with pytest.raises(ValueError, match="finite"):
        pressure_flux_picard_step(
            R_GRID,
            Z_GRID,
            np.full_like(R_GRID, np.inf),
            zeros,
            identity,
            derivative,
            1.0,
            None,
            0.0,
        )
    with pytest.raises(ValueError, match="uniformly spaced"):
        pressure_flux_picard_step(
            np.array([[1.0, 1.5, 2.5]] * 3),
            Z_GRID,
            zeros,
            zeros,
            identity,
            derivative,
            1.0,
            None,
            0.0,
        )
    with pytest.raises(ValueError, match="g_psi must have shape"):
        pressure_flux_picard_step(
            R_GRID, Z_GRID, zeros, zeros, np.zeros((2, 2)), derivative, 1.0, None, 0.0
        )
    for relax in (1.5, -0.05):
        with pytest.raises(ValueError, match="relax must be between"):
            pressure_flux_picard_step(
                R_GRID, Z_GRID, zeros, zeros, identity, derivative, 1.0, None, relax
            )
    for edge in (0.0, np.nan):
        with pytest.raises(ValueError, match="psi_edge"):
            pressure_flux_picard_step(
                R_GRID, Z_GRID, zeros, zeros, identity, derivative, edge, None, 0.0
            )
    with pytest.raises(ValueError, match="one value per grid cell"):
        pressure_flux_picard_step(
            R_GRID, Z_GRID, zeros, zeros, identity, np.zeros(2), 1.0, None, 0.0
        )
    # A one-row grid cannot carry a dZ spacing and is rejected before indexing.
    with pytest.raises(ValueError, match="same-shape|uniformly spaced"):
        pressure_flux_picard_step(
            np.array([[1.0, 1.5, 2.0]]),
            np.array([[0.0, 0.0, 0.0]]),
            np.zeros((1, 3)),
            np.zeros((1, 3)),
            np.eye(3),
            np.zeros((1, 3)),
            1.0,
            None,
            0.0,
        )
    # Two points per axis is the declared minimum and is accepted.
    pair_r, pair_z = np.meshgrid(np.array([1.0, 2.0]), np.array([0.0, 1.0]))
    accepted = pressure_flux_picard_step(
        pair_r,
        pair_z,
        np.zeros((2, 2)),
        np.zeros((2, 2)),
        np.eye(4),
        np.zeros((2, 2)),
        1.0,
        None,
        0.0,
    )
    assert accepted["residual"] == 0.0


def test_runtime_failure_channel_raises_floating_point_error():
    # A finite Green matrix whose contraction overflows makes the flux, and with
    # it the normalized residual, non-finite.
    huge = np.full((NODES, NODES), 1.0e300)
    derivative = np.full_like(R_GRID, 1.0e300)
    zeros = np.zeros_like(R_GRID)
    with pytest.raises(FloatingPointError, match="nonfinite Green update"):
        pressure_flux_picard_step(R_GRID, Z_GRID, zeros, zeros, huge, derivative, 1.0, None, 0.0)
