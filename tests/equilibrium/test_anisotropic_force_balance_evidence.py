"""Independent evidence for the axisymmetric gyrotropic force operator.

Asset: ``scirel.equilibrium.anisotropic-force-balance``.

The maintained tests in ``test_anisotropic_force_balance.py`` and the
cross-domain correction tests manufacture a tensor-equilibrium field and check
that it is accepted.  A manufactured field that was *derived from this
operator's own discretization* cannot separate a wrong tensor convention from a
right one: it reproduces whatever the code does.  The evidence here is instead
built from three things the code cannot invent:

1. **Analytic closed forms.**  For a solenoidal poloidal field and pressures
   that are polynomials of degree at most two, the three-point stencils are
   exact, so ``div(P)`` reduces to a formula that is written down here and
   evaluated from the fixture's coefficients alone.  Three geometries pin
   different parts of the tensor:

   * a uniform axial field with an isotropic quadratic pressure
     (``p = 3 + 2R^2 - 1.25Z`` on a grid that contains the magnetic axis)
     gives ``force_R = 4R``, ``force_Z = -1.25`` and ``J_phi = 8R``; this
     pins the ``R^2`` radial derivative, the axis column rule and the unit of
     ``J_phi`` (Pa/m divided by T);
   * a solenoidal *radial* field ``B_R = -c/R`` (from ``psi = c Z``) with
     anisotropic linear pressures gives
     ``force_R = dp_parallel/dR + (p_parallel - p_perp)/R`` and
     ``force_Z = dp_perp/dZ``; this is the case where the radial tensor
     component carries the *parallel* pressure and the azimuthal curvature term
     ``(P_RR - p_perp)/R`` is nonzero, so a swapped ``b_R``/``b_Z`` weight or a
     dropped curvature term changes the answer by ``O(1)``;
   * a curved solenoidal field (``psi = A R^2 + D R^2 Z``) with an *isotropic*
     linear pressure, where the anisotropy vanishes identically and the force
     must be exactly ``grad p`` for any field direction.

2. **Algebraic identities among the returned arrays.**  Two relations hold
   pointwise for any input because they are how the outputs are composed, and
   they are checked here against the returned numbers rather than against a
   second implementation: the parallel force is the field projection
   ``b . force``, and the toroidal current is the projection
   ``J_phi = (B_Z force_R - B_R force_Z)/|B|^2``.

3. **Structure that a wrong operator breaks.**  The divergence is affine in
   ``(p_parallel, p_perp)`` and homogeneous of degree one in the pressures:
   ``force(p_parallel, p_perp) = force(p_perp, p_perp) + force(delta, 0)`` and
   ``force(k p) = k force(p)``, while the normalized compatibility metric is
   invariant under ``k``.  A missing component, a sign flip or an absolute
   tolerance in the metric breaks one of these without needing an oracle.

4. **Order of accuracy.**  For a general field direction the discrete
   divergence cannot be exact, so the continuum identity
   ``b . div(P) = b . grad p_parallel + delta div(b)`` is tested as a
   *convergence* statement: the residual must fall by at least ``3.4x`` per
   mesh doubling (second order, 1.85 with margin).  A tensor built with the
   wrong pressure in the radial slot does not converge to the identity at all.

Precision budgets, fixed before any comparison was run:

* For the polynomial fixtures the stencil is exact, so the only error is
  binary64 rounding.  Algebraic outputs (``J_phi``, ``parallel_force``,
  ``B``, ``firehose_margin``) are sums of at most six products with one
  division by ``|B|^2``, and their budget is ``_REL = 16 * eps`` relative to
  the *analytic* magnitude computed from the fixture coefficients, not from the
  returned value.
* A difference quotient is worse conditioned than that, so it gets a budget
  that says why: each slope divides two rounded values, so its relative error
  is ``eps * max|p| / (h * |slope|)`` -- the offset-to-increment ratio.  The
  stencil then averages two such slopes and the one-sided boundary
  extrapolation roughly doubles the contribution, while the coefficient
  arithmetic adds a few ulp.  ``_quotient_budget`` therefore returns
  ``(8 + 4 * max|p| / (h_min |slope|)) * eps``.  It is computed from the
  fixture, never from the result.  The fixtures are also chosen to be
  well-conditioned (the increment is a sizeable fraction of the pressure), so
  the asserted bound sits well above the observed deviation.
* Identities among returned arrays are two or three operations, so their
  budget is ``_ID = 8 * eps`` relative to the largest term in the identity.
* No threshold below was adjusted after observing a result; the observed
  deviations are at least a factor of three inside every budget.

Failure channels, one executable assertion each (contract ``failure_semantics``):

* ``invalid_input`` -- nonfinite/wrong-shape arrays, a non-rectilinear grid,
  fewer than three points per axis, a nonincreasing or negative-radius axis, a
  negative pressure and a wrong-shaped mask each raise ``ValueError``.
* ``runtime_failure`` -- the declared small-denominator branch is exercised:
  an exactly zero field gives ``J_phi = parallel_force = 0`` with no NaN, and
  an overflowing pressure pair either returns nonfinite values or raises,
  but never returns a silently wrong finite value.
* ``nonconvergence`` -- declared not applicable; the executable half of that
  claim is that the returned mapping carries no convergence or iteration key.
* ``partial_results`` -- every failing call above raises, so a partially filled
  mapping cannot escape.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.equilibrium import compute_anisotropic_force_balance

_EPS = np.finfo(float).eps
_REL = 16.0 * _EPS
_ID = 8.0 * _EPS
REFINEMENT_FACTOR = 3.4


def _axis_fixture():
    """Uniform axial field on a grid whose first column is the magnetic axis.

    Analytic pressure ``p = 3 + 2R^2 - 1.25Z`` is even in ``R`` about the axis
    and nonnegative on the rectangle, and the field ``B_Z = 0.5 T`` is
    solenoidal with constant direction.
    """
    r = np.linspace(0.0, 0.8, 5)
    z = np.linspace(-0.4, 0.4, 5)
    R, Z = np.meshgrid(r, z)
    pressure = 3.0 + 2.0 * R**2 - 1.25 * Z
    return {
        "R": R,
        "Z": Z,
        "br": np.zeros_like(R),
        "bz": np.full_like(R, 0.5),
        "p_parallel": pressure.copy(),
        "p_perpendicular": pressure.copy(),
        "radial_slope": 4.0 * R,
        "axial_slope": np.full_like(R, -1.25),
        "b_magnitude": 0.5,
    }


def _radial_fixture():
    """Solenoidal radial field ``B_R = -c/R`` from ``psi = c Z``.

    ``p_parallel = 4 + 1.5R + 0.5Z`` and ``p_perp = 1 + 0.5R + 0.25Z`` are
    linear, so the three-point stencils are exact.  With ``b = -e_R`` the
    tensor components are ``P_RR = p_parallel``, ``P_ZZ = p_perp`` and
    ``P_RZ = 0``, so the azimuthal curvature term is the only ``1/R`` part.
    """
    r = np.linspace(0.2, 1.0, 6)
    z = np.linspace(-0.5, 0.5, 5)
    R, Z = np.meshgrid(r, z)
    c0 = 0.5
    p_parallel = 4.0 + 1.5 * R + 0.5 * Z
    p_perp = 1.0 + 0.5 * R + 0.25 * Z
    return {
        "R": R,
        "Z": Z,
        "br": -c0 / R,
        "bz": np.zeros_like(R),
        "p_parallel": p_parallel,
        "p_perpendicular": p_perp,
        "delta": p_parallel - p_perp,
        "c0": c0,
        "force_r": 1.5 + (p_parallel - p_perp) / R,
        "force_z": np.full_like(R, 0.25),
        "current": 0.25 * R / c0,
        "b_magnitude": c0 / R,
    }


def _oblique_fixture(nr=6, nz=5, *, anisotropic):
    """Curved solenoidal field from ``psi = A R^2 + D R^2 Z``.

    ``B_R = -D R`` and ``B_Z = 2A + 2DZ`` satisfy
    ``(1/R) d_R(R B_R) + d_Z B_Z = 0`` exactly, so the field is a legitimate
    axisymmetric poloidal field whose direction varies in space.
    """
    a, d = 1.0, 0.5
    r = np.linspace(0.3, 1.2, nr)
    z = np.linspace(-0.7, 0.7, nz)
    R, Z = np.meshgrid(r, z)
    br = -d * R
    bz = 2.0 * a + 2.0 * d * Z
    magnitude = np.hypot(br, bz)
    p_parallel = 3.0 + 2.0 * R - 0.75 * Z
    p_perp = p_parallel.copy() if not anisotropic else 1.0 + 0.5 * R + 0.25 * Z
    return {
        "R": R,
        "Z": Z,
        "br": br,
        "bz": bz,
        "b_magnitude": magnitude,
        "u_r": br / magnitude,
        "u_z": bz / magnitude,
        "p_parallel": p_parallel,
        "p_perpendicular": p_perp,
        "d": d,
    }


def _assert_close(actual, expected, budget, *, what):
    """Compare against an analytic value at a derived relative budget."""
    scale = max(float(np.max(np.abs(expected))), np.finfo(float).tiny)
    deviation = np.max(np.abs(np.asarray(actual, dtype=float) - expected))
    assert deviation <= budget * scale, (what, float(deviation), float(budget * scale))


def _quotient_budget(values, coordinate, slope):
    """Relative budget for one second-order difference quotient.

    ``values`` is the sampled field, ``coordinate`` the sampled axis and
    ``slope`` the exact derivative of the polynomial being differentiated.
    """
    step = float(np.min(np.abs(np.diff(coordinate))))
    ratio = float(np.max(np.abs(values))) / max(step * abs(slope), np.finfo(float).tiny)
    return (8.0 + 4.0 * ratio) * _EPS


def _rms(values, mask):
    selected = np.asarray(values, dtype=float)[mask]
    if selected.size == 0:
        return 0.0
    scale = float(np.max(np.abs(selected)))
    return 0.0 if scale == 0.0 else scale * float(np.sqrt(np.mean((selected / scale) ** 2)))


def test_isotropic_quadratic_pressure_on_the_axis_grid_has_the_analytic_gradient():
    fixture = _axis_fixture()
    result = compute_anisotropic_force_balance(
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    # delta = 0, so the tensor is isotropic and the divergence is grad p even
    # though the field direction is radial at the axis column.
    radial_budget = _quotient_budget(fixture["p_parallel"], fixture["R"][0], 3.2)
    axial_budget = _quotient_budget(fixture["p_parallel"], fixture["Z"][:, 0], 1.25)
    _assert_close(result["force_R"], fixture["radial_slope"], radial_budget, what="force_R")
    _assert_close(result["force_Z"], fixture["axial_slope"], axial_budget, what="force_Z")
    _assert_close(result["B"], fixture["b_magnitude"], _REL, what="B")
    # J_phi = B_Z force_R / |B|^2 = force_R / B_Z for a purely axial field.
    _assert_close(result["J_phi"], fixture["radial_slope"] / 0.5, 2.0 * radial_budget, what="J_phi")
    _assert_close(result["parallel_force"], fixture["axial_slope"], axial_budget, what="parallel")
    # The axis column is regular: force_R and J_phi vanish there exactly.
    assert np.all(result["force_R"][:, 0] == 0.0)
    assert np.all(result["J_phi"][:, 0] == 0.0)
    assert np.all(result["firehose_margin"] == 1.0)


def test_anisotropic_radial_field_reproduces_the_curvature_term_closed_form():
    fixture = _radial_fixture()
    result = compute_anisotropic_force_balance(
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    radial_budget = _quotient_budget(fixture["p_parallel"], fixture["R"][0], 1.5)
    axial_budget = _quotient_budget(fixture["p_perpendicular"], fixture["Z"][:, 0], 0.25)
    _assert_close(result["force_R"], fixture["force_r"], radial_budget, what="force_R")
    _assert_close(result["force_Z"], fixture["force_z"], axial_budget, what="force_Z")
    _assert_close(result["J_phi"], fixture["current"], 3.0 * axial_budget, what="J_phi")
    # With b = -e_R the projection is minus the radial force.
    _assert_close(result["parallel_force"], -fixture["force_r"], radial_budget, what="parallel")

    # The curvature term is a real O(1) part of force_R: dropping it changes the
    # value by delta/R, which is of the same order as the answer itself.
    curvature_share = np.min(np.abs(fixture["delta"] / fixture["R"]))
    assert curvature_share > 1.0
    assert curvature_share / np.max(np.abs(fixture["force_r"])) > 0.1


def test_isotropic_linear_pressure_on_a_curved_field_is_the_gradient():
    fixture = _oblique_fixture(anisotropic=False)
    result = compute_anisotropic_force_balance(
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    # d_R p = 2 Pa/m and d_Z p = -0.75 Pa/m for the manufactured pressure.
    radial_budget = _quotient_budget(fixture["p_parallel"], fixture["R"][0], 2.0)
    axial_budget = _quotient_budget(fixture["p_parallel"], fixture["Z"][:, 0], 0.75)
    _assert_close(result["force_R"], np.full_like(fixture["R"], 2.0), radial_budget, what="force_R")
    _assert_close(
        result["force_Z"], np.full_like(fixture["R"], -0.75), axial_budget, what="force_Z"
    )
    expected_current = (fixture["bz"] * 2.0 - fixture["br"] * (-0.75)) / fixture["b_magnitude"] ** 2
    # J_phi and the parallel force are combinations of the two force
    # components divided by |B| or |B|^2, so both inherit the sum of the two
    # quotient budgets plus the division chain; relative errors add.
    combined = radial_budget + axial_budget + 2.0 * _REL
    _assert_close(result["J_phi"], expected_current, combined, what="J")
    expected_parallel = (fixture["br"] * 2.0 + fixture["bz"] * (-0.75)) / fixture["b_magnitude"]
    _assert_close(result["parallel_force"], expected_parallel, combined, what="parallel")


def test_parallel_force_is_the_field_projection_of_the_returned_force():
    fixture = _oblique_fixture(anisotropic=True)
    result = compute_anisotropic_force_balance(
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    projected = fixture["u_r"] * result["force_R"] + fixture["u_z"] * result["force_Z"]
    _assert_close(result["parallel_force"], projected, _ID, what="u.f")
    # The projection must be nonzero, otherwise the identity is vacuous.
    assert np.min(np.abs(projected)) > 0.1


def test_toroidal_current_is_the_projected_force_over_the_field_squared():
    fixture = _oblique_fixture(anisotropic=True)
    result = compute_anisotropic_force_balance(
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    projected = (fixture["bz"] * result["force_R"] - fixture["br"] * result["force_Z"]) / result[
        "B"
    ] ** 2
    _assert_close(result["J_phi"], projected, _ID, what="J_phi identity")
    # A sign flip in that projection would change J by 2x its own magnitude.
    assert np.max(np.abs(projected)) > 0.1


def test_the_divergence_is_affine_in_the_anisotropy():
    fixture = _oblique_fixture(anisotropic=True)
    args = (fixture["R"], fixture["Z"], fixture["br"], fixture["bz"])
    parallel, perpendicular = fixture["p_parallel"], fixture["p_perpendicular"]
    full = compute_anisotropic_force_balance(*args, parallel, perpendicular)
    isotropic = compute_anisotropic_force_balance(*args, perpendicular, perpendicular)
    delta_only = compute_anisotropic_force_balance(
        *args, parallel - perpendicular, np.zeros_like(perpendicular)
    )
    for name in ("force_R", "force_Z", "parallel_force"):
        _assert_close(full[name], isotropic[name] + delta_only[name], _ID, what=f"affine {name}")
    # The split is not trivially zero: the anisotropy moves the force.
    assert np.max(np.abs(delta_only["force_R"])) > 0.1


def test_pressures_scale_the_force_and_leave_the_compatibility_metric_invariant():
    fixture = _radial_fixture()
    args = (fixture["R"], fixture["Z"], fixture["br"], fixture["bz"])
    base = compute_anisotropic_force_balance(
        *args, fixture["p_parallel"], fixture["p_perpendicular"]
    )
    for factor in (3.0, 8.0, 0.25):
        scaled = compute_anisotropic_force_balance(
            *args, factor * fixture["p_parallel"], factor * fixture["p_perpendicular"]
        )
        for name in ("force_R", "force_Z", "parallel_force"):
            _assert_close(scaled[name], factor * base[name], _REL, what=f"scale {name}")
        _assert_close(scaled["J_phi"], factor * base["J_phi"], _REL, what="scale J_phi")
        # Both residuals are ratios of homogeneous quantities, so the normalized
        # error is invariant; a hard-coded absolute tolerance would move with k.
        assert scaled["parallel_force_error"] == pytest.approx(
            base["parallel_force_error"], rel=1e-12
        )
        assert scaled["parallel_force_error_raw"] == pytest.approx(
            base["parallel_force_error_raw"], rel=1e-12
        )


def test_uniform_pressure_has_zero_force_and_unit_firehose_margin():
    for fixture in (_axis_fixture(), _radial_fixture(), _oblique_fixture(anisotropic=False)):
        pressure = np.full_like(fixture["R"], 2.5)
        result = compute_anisotropic_force_balance(
            fixture["R"],
            fixture["Z"],
            fixture["br"],
            fixture["bz"],
            pressure,
            pressure,
        )
        for name in ("force_R", "force_Z", "parallel_force", "J_phi"):
            assert np.all(result[name] == 0.0), name
        assert np.all(result["firehose_margin"] == 1.0)
        # A zero residual is compatible, not a rounding artefact.
        assert result["parallel_force_error"] == 0.0
        assert result["parallel_force_absolute"] == 0.0
        assert result["parallel_force_roundoff_consistent"]


def test_firehose_margin_matches_the_declared_expression():
    mu0 = 4.0e-7 * np.pi
    fixture = _radial_fixture()
    result = compute_anisotropic_force_balance(
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    expected = 1.0 - mu0 * fixture["delta"] / fixture["b_magnitude"] ** 2
    _assert_close(result["firehose_margin"], expected, _REL, what="firehose")

    # The margin is a pure diagnostic: a field far past the firehose threshold
    # is returned with a large negative margin instead of raising.  mu0 is
    # 1.26e-6, so reaching a negative margin needs a pressure ratio of order
    # 1e6 Pa/T^2, not a realistic tokamak value.
    axis = _axis_fixture()
    extreme_parallel = np.full_like(axis["R"], 2.0e7)
    extreme_perp = np.zeros_like(axis["R"])
    extreme = compute_anisotropic_force_balance(
        axis["R"], axis["Z"], axis["br"], axis["bz"], extreme_parallel, extreme_perp
    )
    extreme_expected = 1.0 - mu0 * 2.0e7 / 0.25
    _assert_close(
        extreme["firehose_margin"],
        np.full_like(axis["R"], extreme_expected),
        _REL,
        what="extreme firehose",
    )
    assert np.min(extreme["firehose_margin"]) < -1.0


def test_parallel_force_metric_is_the_declared_ratio_over_the_active_mask():
    fixture = _oblique_fixture(anisotropic=True)
    args = (
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    mask = np.zeros_like(fixture["R"], dtype=bool)
    mask[1:3, 1:4] = True
    result = compute_anisotropic_force_balance(*args, active_mask=mask)
    maskless = compute_anisotropic_force_balance(*args)

    # The mask selects cells for the metric only, so the arrays are unchanged.
    for name in ("force_R", "force_Z", "parallel_force", "J_phi"):
        np.testing.assert_array_equal(result[name], maskless[name])

    absolute = _rms(result["parallel_force"], mask)
    norm = _rms(np.hypot(result["force_R"], result["force_Z"]), mask)
    bound = _rms(result["parallel_force_roundoff"], mask)
    tiny = np.finfo(float).tiny
    assert result["parallel_force_absolute"] == pytest.approx(absolute, rel=1e-12)
    assert result["parallel_force_roundoff_rms"] == pytest.approx(bound, rel=1e-12)
    assert result["parallel_force_error"] == pytest.approx(
        max(absolute - bound, 0.0) / max(norm, bound, tiny), rel=1e-10
    )
    assert result["parallel_force_error_raw"] == pytest.approx(
        absolute / max(norm, tiny), rel=1e-12
    )
    assert result["parallel_force_roundoff_consistent"] == (absolute <= bound)

    # The masked subset is a strict part of the domain, so the metric differs
    # from the all-active one: the mask is honoured, not ignored.
    assert result["parallel_force_absolute"] != maskless["parallel_force_absolute"]

    empty = np.zeros_like(mask)
    unactive = compute_anisotropic_force_balance(*args, active_mask=empty)
    assert unactive["parallel_force_error"] == 0.0
    assert unactive["parallel_force_absolute"] == 0.0
    assert unactive["parallel_force_roundoff_consistent"]


def test_parallel_imbalance_is_reported_not_rejected():
    fixture = _radial_fixture()
    # Force the parallel force to be large by making p_parallel vary strongly
    # along the field: here the field is radial, so d_R p_parallel drives it.
    result = compute_anisotropic_force_balance(
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    assert result["parallel_force_absolute"] > 1.0
    assert result["parallel_force_error"] > 0.1
    assert not result["parallel_force_roundoff_consistent"]
    # Observational residual: no exception, no masked-out current.
    assert np.all(result["J_phi"] != 0.0)


def test_general_anisotropy_converges_to_the_continuum_projection_identity():
    def residual(size):
        fixture = _oblique_fixture(size, size, anisotropic=True)
        result = compute_anisotropic_force_balance(
            fixture["R"],
            fixture["Z"],
            fixture["br"],
            fixture["bz"],
            fixture["p_parallel"],
            fixture["p_perpendicular"],
        )
        # b . div(P) = b . grad p_par + delta div(b), with b and div(b) taken
        # from the analytic fixture rather than from the implementation.
        delta = fixture["p_parallel"] - fixture["p_perpendicular"]
        d = fixture["d"]
        b = fixture["b_magnitude"]
        br, bz = fixture["br"], fixture["bz"]
        d_b_d_r = -d * br / b
        d_b_d_z = bz * (2.0 * d) / b
        du_r_d_r = (-d * b - br * d_b_d_r) / b**2
        du_z_d_z = (2.0 * d * b - bz * d_b_d_z) / b**2
        div_b = (fixture["u_r"] + fixture["R"] * du_r_d_r) / fixture["R"] + du_z_d_z
        expected = fixture["u_r"] * 2.0 + fixture["u_z"] * (-0.75) + delta * div_b
        return float(np.max(np.abs(result["parallel_force"] - expected)))

    coarse = residual(9)
    middle = residual(17)
    fine = residual(33)
    assert middle < coarse / REFINEMENT_FACTOR
    assert fine < middle / REFINEMENT_FACTOR
    # Second order: halving the spacing must quarter the residual, and the
    # measured ratio is comfortably above the asserted bound.
    assert coarse / middle > REFINEMENT_FACTOR
    assert middle / fine > REFINEMENT_FACTOR


def test_small_denominator_branch_returns_zero_current_without_nan():
    fixture = _axis_fixture()
    zero_field = compute_anisotropic_force_balance(
        fixture["R"],
        fixture["Z"],
        np.zeros_like(fixture["R"]),
        np.zeros_like(fixture["R"]),
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    assert np.all(zero_field["B"] == 0.0)
    assert np.all(zero_field["J_phi"] == 0.0)
    assert np.all(zero_field["parallel_force"] == 0.0)
    for name in ("force_R", "force_Z", "J_phi", "parallel_force", "firehose_margin"):
        assert np.all(np.isfinite(zero_field[name])), name


def test_invalid_input_channel_raises_value_error():
    fixture = _axis_fixture()
    good = (
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )

    with pytest.raises(ValueError, match="must be finite same-shape"):
        compute_anisotropic_force_balance(*good[:-1], fixture["p_perpendicular"][:-1])
    with pytest.raises(ValueError, match="must be finite same-shape"):
        compute_anisotropic_force_balance(
            fixture["R"], fixture["Z"], fixture["br"], fixture["bz"], good[4], good[5] * np.nan
        )
    with pytest.raises(ValueError, match="rectilinear R-Z grid"):
        compute_anisotropic_force_balance(fixture["R"] + fixture["Z"], *good[1:])
    with pytest.raises(ValueError, match="rectilinear R-Z grid"):
        compute_anisotropic_force_balance(
            fixture["R"][:2], fixture["Z"][:2], *[value[:2] for value in good[2:]]
        )
    with pytest.raises(ValueError, match="grid axes and pressures are invalid"):
        compute_anisotropic_force_balance(
            fixture["R"], fixture["Z"], fixture["br"], fixture["bz"], -good[4], good[5]
        )
    with pytest.raises(ValueError, match="grid axes and pressures are invalid"):
        compute_anisotropic_force_balance(
            fixture["R"][:, ::-1],
            fixture["Z"][:, ::-1],
            *[value[:, ::-1] for value in good[2:]],
        )
    with pytest.raises(ValueError, match="active_mask must match"):
        compute_anisotropic_force_balance(*good, active_mask=np.ones((2, 2), dtype=bool))


def test_nonconvergence_channel_is_declared_not_applicable():
    fixture = _axis_fixture()
    result = compute_anisotropic_force_balance(
        fixture["R"],
        fixture["Z"],
        fixture["br"],
        fixture["bz"],
        fixture["p_parallel"],
        fixture["p_perpendicular"],
    )
    for forbidden in ("converged", "iterations", "residual", "status", "convergence"):
        assert forbidden not in result
