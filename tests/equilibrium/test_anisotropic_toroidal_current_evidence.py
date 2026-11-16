"""Independent evidence for the gyrotropic toroidal-current split.

Asset: ``scirel.equilibrium.anisotropic-toroidal-current``.

The maintained tests exercise manufactured fixtures whose expected currents were
taken from the same force-balance operator, so the *split* and the *current* are
verified only against themselves.

The independent basis here is the continuum perpendicular-current relation.  For
an isotropic pressure the gyrotropic tensor is ``P = p I`` and the force balance
``div(P) = J x B`` gives the toroidal projection

``J_phi = (B_Z dR p - B_R dZ p) / (B_R^2 + B_Z^2)``,

which is ``(B x grad p)_phi / |B|^2``.  With a constant field and a pressure that
is linear or quadratic in R and linear in Z the discrete three-point stencils of
the implementation are *exact* (the interior rule and the one-sided quadratic
end rule both reproduce quadratics), so the discrete current must equal this
analytic expression to rounding.

Statements, each of which a wrong implementation cannot pass:

1. **Axial constant field.**  With ``B_R = 0``, ``B_Z`` constant and a quadratic
   radial pressure, ``J_phi = (dR p)/B_Z``.  Only ``p_perp`` may enter an
   isotropic comparison, so a swapped or doubled component shows up here.
2. **Oblique constant field.**  With both components nonzero and a pressure
   linear in R and Z, ``J_phi = (B_Z dR p - B_R dZ p)/|B|^2``.  This decides the
   cross term's sign and the ``|B|^2`` denominator.
3. **The split adds up.**  ``j_phi == gradp_term + anisotropy_curvature_term``
   within two roundings of a single subtraction and addition.
4. **Equal pressures leave nothing to the curvature term.**  For
   ``p_parallel == p_perp`` the anisotropic term is exactly zero and the total
   current is bitwise the comparison current, because both evaluations receive
   identical arguments.
5. **Degenerate states.**  A uniform pressure gives exactly zero current and the
   ``R = 0`` axis column is exactly zero.

Budgets, fixed before the comparison was run:

* statements 1 and 2 use ``_CURRENT_BUDGET = 64 eps`` relative, the envelope of
  one exact stencil difference, a two-term product difference, one division by
  ``|B|^2`` and the hypot evaluation.  The analytic side is evaluated at 40
  digits and contributes nothing;
* statements 3 to 5 are bitwise or exact-zero equalities.

Failure channels (contract ``failure_semantics``):

* ``invalid_input`` -- wrong rank, mismatched shapes, nonfinite entries, a
  non-rectilinear grid, fewer than three points on either axis, a negative first
  radius, non-increasing axes and negative pressures all raise ``ValueError``
  from the bound force-balance evaluation;
* ``runtime_failure`` -- declared as "dependency and arithmetic failures
  propagate" with no finite-output guarantee, so the executable assertion is
  that non-finite *input* is refused instead of producing a silent ``nan``
  current; the propagation of an arithmetic failure is recorded as
  not-guarded;
* ``nonconvergence`` -- not applicable; the assertion is that the mapping has
  exactly the five declared keys and no status field;
* ``partial_results`` -- no mapping exists if either evaluation fails, and
  ``force_diagnostics`` is a plain dict on success.
"""

from __future__ import annotations

import math

import mpmath
import numpy as np
import pytest

from scirel.equilibrium import compute_anisotropic_toroidal_current

mpmath.mp.dps = 40

_EPS = math.ulp(1.0)
_CURRENT_BUDGET = 64 * _EPS


def _grid(points_r=7, points_z=5):
    r_axis = np.linspace(0.25, 1.75, points_r)
    z_axis = np.linspace(-0.6, 0.6, points_z)
    return np.meshgrid(r_axis, z_axis)


def test_axial_constant_field_reproduces_the_perpendicular_current():
    r_grid, z_grid = _grid()
    b_r = np.zeros_like(r_grid)
    b_z = np.full_like(r_grid, 2.0)
    # Quadratic radial pressure: the three-point stencils are exact for it.
    pressure = 3.0 + 0.5 * r_grid + 0.25 * r_grid**2
    result = compute_anisotropic_toroidal_current(r_grid, z_grid, b_r, b_z, pressure, pressure)
    for node in range(r_grid.size):
        radius = mpmath.mpf(float(r_grid.ravel()[node]))
        expected = (mpmath.mpf("0.5") + mpmath.mpf("0.5") * radius) / mpmath.mpf("2.0")
        observed = float(result["j_phi"].ravel()[node])
        assert abs(mpmath.mpf(observed) - expected) <= _CURRENT_BUDGET * abs(expected), (
            node,
            observed,
            float(expected),
        )
    # The anisotropic term is exactly zero for equal pressures.
    assert np.all(result["anisotropy_curvature_term"] == 0.0)


def test_oblique_constant_field_reproduces_the_cross_product_relation():
    r_grid, z_grid = _grid()
    b_r = np.full_like(r_grid, 0.5)
    b_z = np.full_like(r_grid, -1.5)
    # Linear in R and in Z, so every stencil is exact.
    pressure = 2.0 + 0.75 * r_grid - 0.4 * z_grid
    result = compute_anisotropic_toroidal_current(r_grid, z_grid, b_r, b_z, pressure, pressure)
    b_squared = mpmath.mpf("0.5") ** 2 + mpmath.mpf("-1.5") ** 2
    expected = (
        mpmath.mpf("-1.5") * mpmath.mpf("0.75") - mpmath.mpf("0.5") * mpmath.mpf("-0.4")
    ) / b_squared
    for observed in result["j_phi"].ravel():
        assert abs(mpmath.mpf(float(observed)) - expected) <= _CURRENT_BUDGET * abs(expected)


def test_the_two_terms_add_up_to_the_total_current():
    r_grid, z_grid = _grid()
    b_r = 0.3 * np.sin(z_grid)
    b_z = 1.2 + 0.1 * r_grid
    p_parallel = 1.0 + 0.2 * r_grid**2
    p_perp = 1.4 + 0.1 * r_grid
    result = compute_anisotropic_toroidal_current(r_grid, z_grid, b_r, b_z, p_parallel, p_perp)
    total = result["gradp_term"] + result["anisotropy_curvature_term"]
    scale = np.maximum(np.abs(result["j_phi"]), 1.0)
    assert np.all(np.abs(total - result["j_phi"]) <= 2 * _EPS * scale)


def test_equal_pressures_reduce_to_the_isotropic_comparison_bitwise():
    r_grid, z_grid = _grid()
    b_r = 0.2 + 0.05 * r_grid
    b_z = 0.9 - 0.03 * z_grid
    pressure = 2.5 + 0.4 * r_grid**2 - 0.1 * z_grid
    result = compute_anisotropic_toroidal_current(r_grid, z_grid, b_r, b_z, pressure, pressure)
    np.testing.assert_array_equal(result["j_phi"], result["gradp_term"])
    assert np.all(result["anisotropy_curvature_term"] == 0.0)
    np.testing.assert_array_equal(result["B"], np.hypot(b_r, b_z))
    assert type(result["force_diagnostics"]) is dict


def test_uniform_pressure_and_the_axis_column_are_exactly_zero():
    r_grid, z_grid = _grid()
    uniform = np.full_like(r_grid, 4.0)
    result = compute_anisotropic_toroidal_current(
        r_grid, z_grid, np.zeros_like(r_grid), np.ones_like(r_grid), uniform, uniform
    )
    assert np.all(result["j_phi"] == 0.0)

    # A grid that includes the magnetic axis: the R = 0 column is zero by the
    # declared regular-axis convention, including the anisotropic term.
    axis_r, axis_z = np.meshgrid(np.linspace(0.0, 1.0, 5), np.linspace(-0.4, 0.4, 5))
    axis_result = compute_anisotropic_toroidal_current(
        axis_r,
        axis_z,
        np.zeros_like(axis_r),
        np.ones_like(axis_r),
        2.0 + 0.5 * axis_r,
        1.0 + 0.25 * axis_r,
    )
    assert np.all(axis_result["j_phi"][:, 0] == 0.0)


def test_returned_mapping_has_the_declared_keys_and_no_convergence_field():
    r_grid, z_grid = _grid()
    zeros = np.zeros_like(r_grid)
    ones = np.ones_like(r_grid)
    result = compute_anisotropic_toroidal_current(r_grid, z_grid, zeros, ones, ones, ones)
    assert list(result) == [
        "j_phi",
        "gradp_term",
        "anisotropy_curvature_term",
        "B",
        "force_diagnostics",
    ]
    for forbidden in ("converged", "iterations", "status"):
        assert forbidden not in result


def test_invalid_input_channel_raises_value_error():
    r_grid, z_grid = _grid()
    zeros = np.zeros_like(r_grid)
    ones = np.ones_like(r_grid)

    with pytest.raises(ValueError, match="finite same-shape"):
        compute_anisotropic_toroidal_current(r_grid, z_grid[:-1], zeros, ones, ones, ones)
    with pytest.raises(ValueError, match="finite same-shape"):
        compute_anisotropic_toroidal_current(
            r_grid, z_grid, np.full_like(r_grid, np.nan), ones, ones, ones
        )
    with pytest.raises(ValueError, match="same-shape"):
        compute_anisotropic_toroidal_current(r_grid, z_grid, zeros, ones, ones[:-1], ones)
    twisted = r_grid + 0.05 * z_grid
    with pytest.raises(ValueError, match="rectilinear"):
        compute_anisotropic_toroidal_current(twisted, z_grid, zeros, ones, ones, ones)
    small_r, small_z = np.meshgrid(np.array([0.5, 1.0]), np.array([-0.5, 0.0, 0.5]))
    with pytest.raises(ValueError, match="at least 3 points"):
        compute_anisotropic_toroidal_current(
            small_r,
            small_z,
            np.zeros_like(small_r),
            np.ones_like(small_r),
            np.ones_like(small_r),
            np.ones_like(small_r),
        )
    negative_r, negative_z = np.meshgrid(np.array([-1.0, 0.0, 1.0]), np.array([-0.5, 0.0, 0.5]))
    with pytest.raises(ValueError, match="grid axes and pressures are invalid"):
        compute_anisotropic_toroidal_current(
            negative_r,
            negative_z,
            np.zeros_like(negative_r),
            np.ones_like(negative_r),
            np.ones_like(negative_r),
            np.ones_like(negative_r),
        )
    with pytest.raises(ValueError, match="grid axes and pressures are invalid"):
        compute_anisotropic_toroidal_current(r_grid, z_grid, zeros, ones, -ones, ones)
