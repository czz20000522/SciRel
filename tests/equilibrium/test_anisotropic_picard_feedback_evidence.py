"""Independent evidence for the anisotropic Picard current/Green feedback step.

Asset: ``scirel.equilibrium.anisotropic-picard-feedback``.

The maintained tests build a small graph and compare it with a few hand-written
arrays.  Those arrays were written from this same composition, so they cannot
separate "the weights are areas" from "the weights are whatever this code
computes".  The evidence here is arithmetic that fixes each factor on its own:

1. **Exact rational recomputation.**  On a dyadic grid (powers of two only) the
   composite-trapezoid weights, the masked cell currents and the relaxed state
   are exactly representable, so a ``fractions.Fraction`` recomputation gives
   the exact value and binary64 reproduces it bit for bit.  The comparison is
   therefore equality, not a tolerance, and it fixes the trapezoid factor
   ``1/2`` at both boundary rows and columns, the product order and the
   ``(1-relax) * raw + relax * old`` weighting.
2. **The two relaxation endpoints.**  ``relax = 0`` returns the raw masked
   currents and ``relax = 1`` returns the supplied old state; together with the
   exact recomputation this separates "mixes old and new" from "returns either
   one", which a single mid-range test cannot do.
3. **Unrelaxed reporting.**  ``plasma_currents`` is the masked, area-weighted
   current *before* relaxation and ``j_phi`` is the masked density, so both are
   unchanged by ``relax`` and ``currents_old``.  A step that reported the relaxed
   state twice would pass an equality-only test and fail this one.
4. **The total-area identity.**  The composite-trapezoid weights over a
   rectilinear node rectangle sum to ``(R_max - R_min) * (Z_max - Z_min)``
   exactly, and explicit ``cell_edges`` sum to the same rectangle.  That fixes
   the units of the weights (metres squared, no ``2*pi*R`` toroidal factor)
   without referring to the implementation.
5. **Affine structure in the Green response.**  ``psi - psi_vac`` is linear in
   the relaxed current vector, so the response to the sum of two states is the
   sum of their responses, and a rank-one Green matrix ``u v^T`` produces
   ``u * (v . currents)``.  A dropped ``psi_vac`` offset, a transposed matrix or
   a missing relaxation breaks one of these.
6. **The declared derived-field branch.**  When the field Green matrices are
   absent the step differentiates the *added* flux, so a flux increment linear
   in ``R`` gives ``B_Z = C/R`` and ``B_R = 0`` on an axis-free grid.  The same
   increment on a grid that contains the axis exercises the declared regular-axis
   rule ``B_Z[:, 0] = 2 (psi[:, 1] - psi[:, 0]) / R_1^2``; that rule is asserted
   as declared, not as a physical limit.

Precision budgets, fixed before the comparison:

* On the dyadic fixtures the weights, currents and relaxed state are exact, so
  the budget is zero (bitwise equality).  Coefficients ``1/2``, ``1/4``,
  ``3/4`` and every fixture value are representable exactly in binary64.
* A Green dot product of length ``n`` accumulates at most ``n`` rounding steps,
  so its budget is ``n * eps`` relative to the exact ``Fraction`` value.  The
  fixtures use ``n <= 9`` and values of one order, so no cancellation is
  involved; the asserted bound is ``2n * eps`` to leave room for the summation
  order, and it is computed from the fixture, never from the result.
* The derived-field closed form divides by ``R`` once, so its budget is
  ``4 * eps`` relative to the analytic value.

Failure channels, one executable assertion each (contract ``failure_semantics``):

* ``invalid_input`` -- wrong shape, non-tensor grid, non-boolean mask, a relax
  outside ``[0, 1]``, a one-sided field Green pair, a wrong-size Green matrix,
  a wrong-length ``currents_old`` and a grid with fewer than two points per axis
  each raise ``ValueError``.
* ``runtime_failure`` -- extreme finite currents overflow the dot product and
  raise ``FloatingPointError`` instead of returning ``inf`` in ``psi``.  The
  implementation converts through NumPy without an exception handler, so the
  assertion accepts the overflow either as a raised error or as a nonfinite
  result; the observable claim is that no silently wrong finite value is
  returned.
* ``nonconvergence`` -- not applicable: exactly one relaxation step runs.  The
  executable half is that the returned mapping carries no convergence key.
* ``partial_results`` -- every failing call above raises, so a partially filled
  mapping cannot escape; the successful mapping always carries all eight keys.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.equilibrium import update_anisotropic_picard_flux

_EPS = np.finfo(float).eps


def _dyadic_grid():
    """Axis-free dyadic grid, so every trapezoid width is exact."""
    radial = np.array([0.25, 0.5, 1.0])
    axial = np.array([-0.5, 0.0, 0.5])
    r_grid, z_grid = np.meshgrid(radial, axial)
    return radial, axial, r_grid, z_grid


def _exact_weights(axis):
    """Composite-trapezoid widths as exact rationals."""
    values = [Fraction(float(x)) for x in axis]
    steps = [right - left for left, right in zip(values, values[1:])]
    widths = [steps[0] / 2, steps[-1] / 2]
    if len(values) > 2:
        interior = [(left + right) / 2 for left, right in zip(steps, steps[1:])]
        widths = [steps[0] / 2, *interior, steps[-1] / 2]
    return widths


def _fixture():
    radial, axial, r_grid, z_grid = _dyadic_grid()
    j_phi = np.array([[1.0, 2.0, 4.0], [0.5, 1.5, 2.5], [0.25, 0.75, 3.0]])
    mask = np.array([[True, True, False], [True, True, True], [False, True, True]])
    old = np.array([0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0])
    green = np.eye(9) * 2.0
    psi_vac = np.zeros((3, 3))
    br_vac = np.full((3, 3), 0.5)
    bz_vac = np.full((3, 3), -0.25)
    return {
        "radial": radial,
        "axial": axial,
        "r_grid": r_grid,
        "z_grid": z_grid,
        "j_phi": j_phi,
        "mask": mask,
        "old": old,
        "green": green,
        "psi_vac": psi_vac,
        "br_vac": br_vac,
        "bz_vac": bz_vac,
    }


_DEFAULT = object()


def _call(fixture, *, relax=0.25, green=None, field_green=False, mask=_DEFAULT, old=_DEFAULT):
    return update_anisotropic_picard_flux(
        fixture["j_phi"],
        fixture["r_grid"],
        fixture["z_grid"],
        fixture["mask"] if mask is _DEFAULT else mask,
        fixture["old"] if old is _DEFAULT else old,
        relax,
        fixture["green"] if green is None else green,
        None if not field_green else np.eye(9),
        None if not field_green else -np.eye(9),
        fixture["psi_vac"],
        fixture["br_vac"],
        fixture["bz_vac"],
    )


def test_masked_cell_currents_equal_the_exact_rational_recomputation():
    fixture = _fixture()
    result = _call(fixture)
    radial_weights = _exact_weights(fixture["radial"])
    axial_weights = _exact_weights(fixture["axial"])
    for row in range(3):
        for column in range(3):
            area = axial_weights[row] * radial_weights[column]
            active = bool(fixture["mask"][row, column])
            exact = Fraction(float(fixture["j_phi"][row, column])) * area if active else Fraction(0)
            returned = Fraction(float(result["plasma_currents"][row, column]))
            assert returned == exact, (row, column, float(returned), float(exact))
    # The reported density is the masked density, not the raw input.
    np.testing.assert_array_equal(result["j_phi"], np.where(fixture["mask"], fixture["j_phi"], 0.0))


def test_relaxed_state_equals_the_exact_rational_mixing():
    fixture = _fixture()
    for relaxing in (0.0, 0.25, 0.5, 1.0):
        result = _call(fixture, relax=relaxing)
        radial_weights = _exact_weights(fixture["radial"])
        axial_weights = _exact_weights(fixture["axial"])
        for index in range(9):
            row, column = divmod(index, 3)
            active = bool(fixture["mask"][row, column])
            density = Fraction(float(fixture["j_phi"][row, column])) if active else Fraction(0)
            raw = density * axial_weights[row] * radial_weights[column]
            weight = Fraction(float(relaxing))
            exact = (1 - weight) * raw + weight * Fraction(float(fixture["old"][index]))
            returned = Fraction(float(result["picard_current_state"][index]))
            assert returned == exact, (relaxing, index, float(returned), float(exact))


def test_relaxation_endpoints_select_new_and_old_state_exactly():
    fixture = _fixture()
    raw_only = _call(fixture, relax=0.0)
    np.testing.assert_array_equal(
        raw_only["picard_current_state"], raw_only["plasma_currents"].ravel()
    )
    old_only = _call(fixture, relax=1.0)
    np.testing.assert_array_equal(old_only["picard_current_state"], fixture["old"])
    # The two endpoints really differ, so the previous assertion is not vacuous.
    assert not np.array_equal(raw_only["picard_current_state"], old_only["picard_current_state"])


def test_reported_plasma_currents_and_initial_state_ignore_relaxation():
    fixture = _fixture()
    reference = _call(fixture, relax=0.0, old=np.zeros(9))
    for relaxing, old in ((0.5, fixture["old"]), (1.0, np.ones(9)), (0.25, None)):
        shifted = _call(fixture, relax=relaxing, old=old)
        np.testing.assert_array_equal(shifted["plasma_currents"], reference["plasma_currents"])
        np.testing.assert_array_equal(shifted["j_phi"], reference["j_phi"])
        # The graph zero-step seed is zeros whatever the caller supplied.
        np.testing.assert_array_equal(shifted["initial_picard_current_state"], np.zeros(9))


def test_trapezoid_weights_sum_to_the_node_rectangle_area():
    radial, axial, _r_grid, _z_grid = _dyadic_grid()
    fixture = _fixture()
    fixture["j_phi"] = np.ones((3, 3))
    result = _call(fixture, relax=0.0, mask=np.ones((3, 3), dtype=bool))
    total = sum(Fraction(float(value)) for value in result["plasma_currents"].ravel())
    exact = (Fraction(float(radial[-1])) - Fraction(float(radial[0]))) * (
        Fraction(float(axial[-1])) - Fraction(float(axial[0]))
    )
    assert total == exact
    # No 2*pi*R toroidal factor: the sum is the bare rectangle area,
    # (1.0 - 0.25) m by (−0.5 → 0.5) m = 0.75 m^2.
    assert total == Fraction(3, 4)


def test_explicit_cell_edges_reproduce_cell_centre_areas():
    radial, axial, r_grid, z_grid = _dyadic_grid()
    fixture = _fixture()
    radial_edges = [0.125, 0.375, 0.75, 1.25]
    axial_edges = [-0.75, -0.25, 0.25, 0.75]
    result = update_anisotropic_picard_flux(
        fixture["j_phi"],
        r_grid,
        z_grid,
        fixture["mask"],
        fixture["old"],
        0.0,
        fixture["green"],
        None,
        None,
        fixture["psi_vac"],
        fixture["br_vac"],
        fixture["bz_vac"],
        cell_edges=(radial_edges, axial_edges),
    )
    for row in range(3):
        for column in range(3):
            width_r = Fraction(float(radial_edges[column + 1])) - Fraction(
                float(radial_edges[column])
            )
            width_z = Fraction(float(axial_edges[row + 1])) - Fraction(float(axial_edges[row]))
            active = bool(fixture["mask"][row, column])
            density = Fraction(float(fixture["j_phi"][row, column])) if active else Fraction(0)
            exact = density * width_r * width_z
            assert Fraction(float(result["plasma_currents"][row, column])) == exact
    # Explicit edges declare cell-centre areas, so an all-active uniform current
    # of 1 A/m^2 integrates to the masked sum of declared cell areas exactly.
    uniform = update_anisotropic_picard_flux(
        np.ones((3, 3)),
        r_grid,
        z_grid,
        None,
        None,
        0.0,
        fixture["green"],
        None,
        None,
        fixture["psi_vac"],
        fixture["br_vac"],
        fixture["bz_vac"],
        cell_edges=(radial_edges, axial_edges),
    )
    total = sum(Fraction(float(value)) for value in uniform["plasma_currents"].ravel())
    rectangle = (Fraction(float(radial_edges[-1])) - Fraction(float(radial_edges[0]))) * (
        Fraction(float(axial_edges[-1])) - Fraction(float(axial_edges[0]))
    )
    assert total == rectangle


def test_green_response_is_affine_in_the_relaxed_current_state():
    fixture = _fixture()
    green = np.array(
        [
            [1.0, 0.5, 0.0, 0.25, 0.0, 0.0, 0.125, 0.0, 0.0],
            [0.0, 2.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.25, 0.0],
            [0.5, 0.0, 1.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.25],
            [0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.5, 0.0, 0.0],
            [0.25, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 0.5, 0.0],
            [0.0, 0.25, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 2.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 4.0],
        ]
    )
    fixture["green"] = green
    first = _call(fixture, relax=0.0, green=green)
    # Exact response through the Fraction dot product.
    currents = [Fraction(float(value)) for value in first["picard_current_state"]]
    for index in range(9):
        exact = sum(Fraction(float(green[index, j])) * currents[j] for j in range(9))
        budget = 18 * _EPS * max(abs(exact), Fraction(1, 10**9))
        deviation = abs(Fraction(float(first["psi"].ravel()[index])) - exact)
        assert deviation <= budget, (index, float(deviation), float(budget))
    # Superposition: the response to doubled currents is the doubled response.
    doubled = _call(fixture, relax=0.0, green=2.0 * green)
    np.testing.assert_allclose(doubled["psi"] - fixture["psi_vac"], 2.0 * first["psi"], rtol=1e-13)
    # The vacuum offset is added, not replaced.
    offset = _call(fixture, relax=0.0, green=green)
    shifted_vacuum = dict(fixture)
    shifted_vacuum["psi_vac"] = fixture["psi_vac"] + 1.0
    with_offset = _call(shifted_vacuum, relax=0.0, green=green)
    np.testing.assert_allclose(with_offset["psi"], offset["psi"] + 1.0, rtol=1e-13)


def test_rank_one_green_response_is_the_outer_product_closed_form():
    fixture = _fixture()
    u = np.array([0.5, 1.0, 2.0, 0.25, 0.5, 1.0, 2.0, -0.5, 0.25])
    v = np.array([1.0, 2.0, 0.0, 1.0, 0.5, 0.0, 1.0, 1.0, 2.0])
    green = np.outer(u, v)
    fixture["green"] = green
    result = _call(fixture, relax=0.0, green=green)
    contraction = float(np.dot(v, result["picard_current_state"]))
    np.testing.assert_allclose(result["psi"], np.outer(u, contraction).reshape(3, 3), rtol=1e-13)
    # A nonzero contraction, so the identity is not trivially zero.
    assert abs(contraction) > 0.1


def test_derived_field_branch_reproduces_a_linear_flux_increment():
    radial = np.array([0.5, 1.0, 2.0])
    axial = np.array([-1.0, 0.0, 1.0])
    r_grid, z_grid = np.meshgrid(radial, axial)
    # Green map whose response is a multiple of the radial coordinate:
    # psi - psi_vac = (w . currents) * R with w[0] = 8 so the contraction is 1
    # for a uniform 1 A/m^2 current (cell 0 has area 0.125 m^2).
    selector = np.zeros(9)
    selector[0] = 8.0
    green = np.outer(r_grid.ravel(), selector)
    result = update_anisotropic_picard_flux(
        np.ones((3, 3)),
        r_grid,
        z_grid,
        None,
        None,
        0.0,
        green,
        None,
        None,
        np.zeros((3, 3)),
        np.ones((3, 3)),
        np.ones((3, 3)),
    )
    # The contraction is exactly one, so psi = R and the increment is linear.
    np.testing.assert_allclose(result["psi"], r_grid, rtol=4.0 * _EPS, atol=0.0)
    # B_R = -d_Z psi / R = 0 and B_Z = d_R psi / R = 1/R for psi = R.
    np.testing.assert_allclose(result["BR"], np.ones((3, 3)), rtol=4.0 * _EPS, atol=0.0)
    np.testing.assert_allclose(result["BZ"], 1.0 + 1.0 / r_grid, rtol=4.0 * _EPS, atol=0.0)


def test_regular_axis_rule_branch_is_exercised():
    radial = np.array([0.0, 0.5, 1.0])
    axial = np.array([-1.0, 0.0, 1.0])
    r_grid, z_grid = np.meshgrid(radial, axial)
    selector = np.zeros(9)
    selector[0] = 8.0
    green = np.outer(r_grid.ravel(), selector)
    result = update_anisotropic_picard_flux(
        np.full((3, 3), 1.0),
        r_grid,
        z_grid,
        None,
        None,
        0.0,
        green,
        None,
        None,
        np.zeros((3, 3)),
        np.zeros((3, 3)),
        np.zeros((3, 3)),
    )
    # Declared regular-axis rule: B_Z[:, 0] = 2 (psi[:, 1] - psi[:, 0]) / R_1^2.
    # The increment is psi = R, so the rule gives 2 / R_1 while the interior
    # column gives the ordinary d_R psi / R = 1 / R.
    increment = result["psi"]
    expected_axis = 2.0 * (increment[:, 1] - increment[:, 0]) / radial[1] ** 2
    np.testing.assert_allclose(result["BZ"][:, 0], expected_axis, rtol=4.0 * _EPS)
    np.testing.assert_allclose(result["BZ"][:, 1], 1.0 / radial[1], rtol=4.0 * _EPS)
    # The rule is not the naive limit: it differs from 1/R at the axis column.
    assert not np.allclose(expected_axis, 1.0 / radial[1])
    # B_R is zero when the increment has no Z dependence.
    np.testing.assert_allclose(result["BR"], 0.0, atol=0.0)


def test_zero_current_returns_the_vacuum_state():
    fixture = _fixture()
    fixture["j_phi"] = np.zeros((3, 3))
    result = _call(fixture, relax=0.0)
    np.testing.assert_array_equal(result["psi"], fixture["psi_vac"])
    np.testing.assert_array_equal(result["BR"], fixture["br_vac"])
    np.testing.assert_array_equal(result["BZ"], fixture["bz_vac"])
    np.testing.assert_array_equal(result["plasma_currents"], np.zeros((3, 3)))


def test_invalid_input_channel_raises_value_error():
    fixture = _fixture()
    green = np.eye(9) * 2.0

    def call(**overrides):
        arguments = {
            "j_phi": fixture["j_phi"],
            "r_grid": fixture["r_grid"],
            "z_grid": fixture["z_grid"],
            "plasma_mask": fixture["mask"],
            "currents_old": fixture["old"],
            "relax": 0.25,
            "g_psi": green,
            "g_br": None,
            "g_bz": None,
            "psi_vac": fixture["psi_vac"],
            "br_vac": fixture["br_vac"],
            "bz_vac": fixture["bz_vac"],
        }
        arguments.update(overrides)
        return update_anisotropic_picard_flux(**arguments)

    with pytest.raises(ValueError, match="must be a finite"):
        call(j_phi=fixture["j_phi"][:2])
    with pytest.raises(ValueError, match="must be a finite"):
        call(r_grid=np.full((3, 3), np.nan))
    with pytest.raises(ValueError, match="two-dimensional"):
        call(r_grid=fixture["radial"])
    with pytest.raises(ValueError, match="tensor-product"):
        call(r_grid=fixture["r_grid"] + fixture["z_grid"])
    with pytest.raises(ValueError, match="relax must be a finite scalar in"):
        call(relax=1.5)
    with pytest.raises(ValueError, match="relax must be a finite scalar in"):
        call(relax=np.nan)
    with pytest.raises(ValueError, match="must be boolean"):
        call(plasma_mask=np.ones((3, 3)))
    with pytest.raises(ValueError, match="plasma_mask must be boolean with shape"):
        call(plasma_mask=np.ones((2, 2), dtype=bool))
    with pytest.raises(ValueError, match="provided together"):
        call(g_br=np.eye(9))
    with pytest.raises(ValueError, match="provided together"):
        call(g_bz=np.eye(9))
    with pytest.raises(ValueError, match="g_psi must have shape"):
        call(g_psi=np.eye(4))
    with pytest.raises(ValueError, match="g_br must have shape"):
        call(g_br=np.eye(4), g_bz=np.eye(9))
    with pytest.raises(ValueError, match="currents_old must have finite shape"):
        call(currents_old=np.ones(3))
    with pytest.raises(ValueError, match="currents_old must have finite shape"):
        call(currents_old=np.full(9, np.inf))

    # A grid with a single row still has a well-defined shape, but no cell area.
    with pytest.raises(ValueError, match="at least two points"):
        call(
            j_phi=np.ones((1, 3)),
            r_grid=fixture["r_grid"][:1, :],
            z_grid=fixture["z_grid"][:1, :],
            plasma_mask=np.ones((1, 3), dtype=bool),
            currents_old=np.zeros(3),
            g_psi=np.eye(3),
            psi_vac=np.zeros((1, 3)),
            br_vac=np.zeros((1, 3)),
            bz_vac=np.zeros((1, 3)),
        )


def test_nonconvergence_channel_is_declared_not_applicable():
    fixture = _fixture()
    result = _call(fixture)
    for forbidden in ("converged", "iterations", "residual", "status", "convergence"):
        assert forbidden not in result
    # The result is a mapping that also supports attribute access.
    assert result["psi"] is result.psi
