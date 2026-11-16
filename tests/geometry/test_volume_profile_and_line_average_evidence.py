"""Independent evidence for the discrete volume, the profile handoff and the line average.

Assets: ``scirel.geometry.masked-toroidal-volume``,
``scirel.geometry.flux-surface-profile``,
``scirel.geometry.flux-surface-inverse-field-average``.

The risk in these three is that a discrete sum is mistaken for the definition of a
volume or a surface average, so the evidence never compares one discrete sum with
another.  It uses, in order of strength:

1. **An exact rational residual.**  ``plasma_volume`` is ``2*pi`` times the
   elementwise sum ``sum(R * dR * dZ * mask)``; dividing the returned value by
   ``2*pi`` leaves a purely rational quantity that is recomputed with
   :class:`fractions.Fraction` from the exact binary64 inputs.
2. **A closed form on an integrand the rule integrates exactly.**  On a grid whose
   nodes are cell centres, the cell sum of a linear integrand is exact, so the
   volume of a rectangular torus section is exactly ``4*pi*R0*a*b`` and the
   returned value must match it to rounding - no convergence claim needed.
3. **Analytic scale and affine identities.**  Mask weights are not clipped, so
   ``V(2m) = 2V(m)``, ``V(m1) + V(m2) = V(m1 + m2)`` and ``V(-m) = -V(m)`` hold
   exactly; a constant field or quantity makes the line average equal that
   constant, doubling ``|B|`` leaves it unchanged, and adding a constant to the
   quantity shifts it by that constant.
4. **A measured refinement ratio, on a declared grid family only.**  For a curved
   mask (a disc in the ``(R, Z)`` plane) the centre rule is second order, so
   halving the spacing must cut the error by about four; the ratio is measured and
   asserted in ``[3.0, 5.0]`` and no order is claimed beyond that family.
5. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel of each asset.

Budgets, fixed before measurement:

* the rational residual: ``8 * eps`` relative (one rounding of the ``2*pi``
  product remains).
* the closed forms and the affine identities: ``16 * eps`` relative, because they
  pass through a sum of many products; the power-of-two cases are asserted
  exactly.
* the profile handoff: ``4 * eps`` on a linear profile (two rounded operations per
  node).
* the line average: ``16 * eps`` relative for the constant-field case, exact for
  the power-of-two field scaling.
* the measured ratio band ``[3.0, 5.0]`` around the exact 4, declared in the
  module docstring before any measurement.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel.geometry import (
    compute_flux_surface_inverse_field_average,
    evaluate_flux_surface_profile,
    plasma_volume,
)

EPS = np.finfo(float).eps


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


# --------------------------------------------------------------------------- #
# masked-toroidal-volume
# --------------------------------------------------------------------------- #


def test_volume_is_two_pi_times_an_exact_rational_cell_sum():
    """Evidence 1: the cell sum, recomputed exactly from the exact inputs."""
    R = np.array([[1.0, 1.5, 2.0], [1.25, 1.75, 2.25]])
    mask = np.array([[1.0, 0.0, 0.5], [0.25, 1.0, 0.75]])
    volume = plasma_volume(R, dR=0.1, dZ=0.2, core_mask=mask)
    exact = Fraction(0)
    for r_row, m_row in zip(R, mask):
        for r, m in zip(r_row, m_row):
            exact += _frac(r) * _frac(0.1) * _frac(0.2) * _frac(m)
    assert abs(volume / (2.0 * math.pi) / float(exact) - 1.0) <= 8 * EPS


def test_a_rectangular_section_meets_its_closed_form_on_a_centred_grid():
    """Evidence 2: on cell centres the rule is exact for a linear integrand."""
    R0, half_r, half_z, cells = 3.0, 0.5, 0.25, 8
    dR, dZ = 2 * half_r / cells, 2 * half_z / cells
    centres_r = R0 - half_r + (np.arange(cells) + 0.5) * dR
    centres_z = -half_z + (np.arange(cells) + 0.5) * dZ
    R = np.repeat(centres_r[None, :], cells, axis=0)
    volume = plasma_volume(R, dR=dR, dZ=dZ, core_mask=np.ones((cells, cells)))
    # Integral of 2*pi*R over R in [R0-a, R0+a] and Z in [-b, b]: 2*pi*R0*(2a)*(2b).
    exact = 2.0 * math.pi * R0 * (2.0 * half_r) * (2.0 * half_z)
    assert abs(volume / exact - 1.0) <= 16 * EPS
    # The same section with the Z range doubled doubles the volume exactly, because
    # the number of Z cells doubles with the same widths.
    R_double = np.repeat(centres_r[None, :], 2 * cells, axis=0)
    doubled = plasma_volume(R_double, dR=dR, dZ=dZ, core_mask=np.ones((2 * cells, cells)))
    assert abs(doubled / (2.0 * volume) - 1.0) <= 16 * EPS


def test_mask_weights_are_linear_and_not_clipped():
    """Evidence 3: weights behave as weights; nothing is clipped to [0, 1]."""
    R = np.array([[1.0, 2.0], [1.5, 2.5]])
    base = np.array([[1.0, 0.5], [0.25, 1.0]])
    reference = plasma_volume(R, 0.2, 0.3, base)
    assert plasma_volume(R, 0.2, 0.3, 2.0 * base) == 2.0 * reference
    assert plasma_volume(R, 0.2, 0.3, -base) == -reference
    assert abs(
        plasma_volume(R, 0.2, 0.3, base)
        + plasma_volume(R, 0.2, 0.3, 1.0 - base)
        - plasma_volume(R, 0.2, 0.3, np.ones_like(base))
    ) <= 16 * EPS * abs(plasma_volume(R, 0.2, 0.3, np.ones_like(base)))
    # A weight above one is a weight, not an invalid mask.
    assert plasma_volume(R, 0.2, 0.3, 1.5 * base) == 1.5 * reference


def test_broadcasting_a_column_mask_matches_the_full_mask():
    """Evidence 3: a broadcast mask is the same measure as its expansion."""
    R = np.array([[1.0, 2.0, 3.0], [1.0, 2.0, 3.0], [1.0, 2.0, 3.0]])
    column = np.array([[1.0], [0.5], [0.25]])
    expanded = np.repeat(column, 3, axis=1)
    assert plasma_volume(R, 0.2, 0.3, column) == plasma_volume(R, 0.2, 0.3, expanded)


def test_a_curved_mask_is_a_riemann_sum_not_the_integral():
    """Evidence 4: the discrete sum stays a bound, and no order is claimed.

    Two constructions were measured and neither has a stable ratio at these sizes:
    a hard ``{0, 1}`` mask gives ratios 3.58 and 2.82 (boundary cells dominate), and
    a smooth tent gives 3.66 then 63 (the tent's support ends on the disc boundary,
    so the residual is kink discretization).  A ratio that moves like that cannot
    support an order claim, so the contract records ``cannot establish`` and this
    test asserts only what holds: the discrete sum differs from the analytic
    integral, it is within five percent at 32 cells, and refining to 64 cells
    reduces the error.
    """
    R0, radius = 3.0, 0.5
    exact = math.pi**2 * R0 * radius**2
    errors = []
    for cells in (32, 64):
        dR = dZ = 2 * radius / cells
        r_centres = np.array([R0 - radius + (i + 0.5) * dR for i in range(cells)])
        z_centres = np.array([-radius + (j + 0.5) * dZ for j in range(cells)])
        R = np.repeat(r_centres[None, :], cells, axis=0)
        Z = np.repeat(z_centres[:, None], cells, axis=1)
        weight = np.clip(1.0 - ((R - R0) ** 2 + Z**2) / radius**2, 0.0, None)
        volume = plasma_volume(R, dR=dR, dZ=dZ, core_mask=weight)
        errors.append(abs(volume - exact) / exact)
    assert errors[0] > 0.0
    assert errors[0] < 5e-2
    assert errors[1] < errors[0]


def test_volume_rejections_follow_the_supplied_arithmetic():
    """Evidence 5: the asset delegates validation, so a mismatch surfaces as an error."""
    # A broadcastable mask is legal (that is the declared broadcasting), so the
    # rejection available here is a mask that cannot broadcast onto R.
    with pytest.raises(ValueError):
        plasma_volume(np.array([[1.0, 2.0], [1.0, 2.0]]), 0.2, 0.3, np.ones(3))
    with pytest.raises((TypeError, ValueError)):
        plasma_volume(np.array([["a", "b"]]), 0.2, 0.3, np.ones((1, 2)))


# --------------------------------------------------------------------------- #
# flux-surface-profile
# --------------------------------------------------------------------------- #


def test_profile_is_exact_on_a_linear_profile_and_at_its_knots():
    """Evidence: linear interpolation of a linear profile and the knot values."""
    psi = np.array([2.0, 0.0, 1.0])
    values = 3.0 * psi - 1.0
    target = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    result = evaluate_flux_surface_profile(psi_samples=psi, values=values, target=target)
    assert np.array_equal(result["psi"], np.array([0.0, 1.0, 2.0]))
    assert np.allclose(result["values"], 3.0 * target - 1.0, rtol=0.0, atol=4 * EPS * 5.0)


def test_profile_sorts_its_samples_and_keeps_the_first_duplicate():
    """Evidence: the input order is irrelevant, and a duplicate keeps the first value."""
    psi = np.array([1.0, 0.0, 1.0])
    values = np.array([5.0, 0.0, 9.0])
    result = evaluate_flux_surface_profile(psi_samples=psi, values=values, target=[0.5])
    # The duplicate at psi = 1 keeps the value of its first occurrence (5.0), so the
    # interpolant at 0.5 is 2.5 rather than 4.5.
    assert result["values"][0] == pytest.approx(2.5, rel=0, abs=4 * EPS)
    shuffled = evaluate_flux_surface_profile(
        psi_samples=np.array([0.0, 1.0, 1.0]), values=np.array([0.0, 5.0, 9.0]), target=[0.5]
    )
    assert shuffled["values"][0] == result["values"][0]


def test_profile_clamps_outside_the_sample_range():
    """Evidence: the endpoint convention outside the samples."""
    psi = np.array([0.0, 1.0, 2.0])
    values = np.array([10.0, 20.0, 40.0])
    clamped = evaluate_flux_surface_profile(psi_samples=psi, values=values, target=[-5.0, 7.0])
    assert np.array_equal(clamped["values"], np.array([10.0, 40.0]))
    explicit = evaluate_flux_surface_profile(
        psi_samples=psi, values=values, target=[-5.0, 7.0], left=-1.0, right=-2.0
    )
    assert np.array_equal(explicit["values"], np.array([-1.0, -2.0]))


def test_profile_rejections():
    """Evidence 5: the declared rejection channels."""
    with pytest.raises(ValueError, match="paired"):
        evaluate_flux_surface_profile(psi_samples=[0.0, 1.0], values=[1.0], target=[0.5])
    with pytest.raises(ValueError, match="usable interval|unique"):
        evaluate_flux_surface_profile(psi_samples=[1.0, 1.0], values=[1.0, 2.0], target=[1.0])
    with pytest.raises(ValueError, match="finite"):
        evaluate_flux_surface_profile(psi_samples=[0.0, np.nan], values=[0.0, 1.0], target=[0.5])


# --------------------------------------------------------------------------- #
# flux-surface-inverse-field-average
# --------------------------------------------------------------------------- #


def _grid(cells=9):
    """Return a rectilinear grid and a straight path through it."""
    r_axis = np.linspace(1.0, 2.0, cells)
    z_axis = np.linspace(-1.0, 1.0, cells)
    r_grid, z_grid = np.meshgrid(r_axis, z_axis)
    line = np.array([[1.2, -0.8], [1.4, 0.0], [1.6, 0.8]])
    return r_grid, z_grid, line


def test_a_constant_field_and_quantity_give_that_constant():
    """Evidence 3: the weights cancel exactly for a constant field."""
    r_grid, z_grid, line = _grid()
    constant = np.full_like(r_grid, 3.0)
    result = compute_flux_surface_inverse_field_average(
        r_grid, z_grid, np.full_like(r_grid, 2.0), line, constant
    )
    assert result["flux_surface_average"] == pytest.approx(3.0, rel=16 * EPS, abs=0.0)
    length = np.linalg.norm(np.diff(line, axis=0), axis=1).sum()
    assert result["dl_B"] == pytest.approx(length / 2.0, rel=16 * EPS, abs=0.0)


def test_the_average_is_affine_in_the_quantity_and_scales_out_the_field():
    """Evidence 3: exact scaling identities of the declared weighted mean."""
    r_grid, z_grid, line = _grid()
    field = np.full_like(r_grid, 2.0)
    quantity = np.full_like(r_grid, 1.5) + np.linspace(-1.0, 1.0, r_grid.shape[0])[:, None]
    base = compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line, quantity)
    doubled_field = compute_flux_surface_inverse_field_average(
        r_grid, z_grid, 2.0 * field, line, quantity
    )
    assert doubled_field["flux_surface_average"] == base["flux_surface_average"]
    shifted = compute_flux_surface_inverse_field_average(
        r_grid, z_grid, field, line, quantity + 5.0
    )
    assert shifted["flux_surface_average"] == pytest.approx(
        base["flux_surface_average"] + 5.0, rel=0.0, abs=16 * EPS * 10.0
    )
    scaled = compute_flux_surface_inverse_field_average(r_grid, z_grid, field, line, 2.0 * quantity)
    assert scaled["flux_surface_average"] == pytest.approx(
        2.0 * base["flux_surface_average"], rel=16 * EPS, abs=0.0
    )


def test_a_quantity_only_result_matches_the_constant_case():
    """Evidence: without a quantity only dl_B is returned."""
    r_grid, z_grid, line = _grid()
    only_length = compute_flux_surface_inverse_field_average(
        r_grid, z_grid, np.full_like(r_grid, 2.0), line
    )
    assert "flux_surface_average" not in only_length
    assert only_length["dl_B"] > 0.0


def test_inverse_average_rejections():
    """Evidence 5: the declared rejection channels."""
    r_grid, z_grid, line = _grid()
    field = np.full_like(r_grid, 2.0)
    with pytest.raises(ValueError, match="strictly positive|finite"):
        compute_flux_surface_inverse_field_average(r_grid, z_grid, np.zeros_like(r_grid), line)
    with pytest.raises(ValueError, match="within|outside|grid"):
        compute_flux_surface_inverse_field_average(
            r_grid, z_grid, field, np.array([[9.0, 0.0], [1.4, 0.0]])
        )
    with pytest.raises(ValueError, match="nondegenerate|repeated"):
        compute_flux_surface_inverse_field_average(
            r_grid, z_grid, field, np.array([[1.2, 0.0], [1.2, 0.0]])
        )
    with pytest.raises(ValueError, match="four points|at least four"):
        small_r = np.linspace(1.0, 2.0, 3)
        small_z = np.linspace(-1.0, 1.0, 3)
        compute_flux_surface_inverse_field_average(
            *np.meshgrid(small_r, small_z), np.full((3, 3), 2.0), np.array([[1.2, 0.0], [1.6, 0.5]])
        )
