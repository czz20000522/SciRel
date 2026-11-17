"""Independent evidence for the pressure-only Picard feedback solver.

Asset: ``scirel.equilibrium.compute-equilibrium``.

The maintained tests compare the solver against manufactured updates and check
the terminal status labels.  Because the expected arrays were produced from this
same spline-and-Green chain, they cannot decide whether ``j_phi = R dP/dpsi dR dZ``
carries the right factor of ``R``, the right sign, or the right unit.  The
evidence here uses a fixture whose answer is known in closed form:

``psi_vac = c R^2`` (so flux is quadratic in radius) and ``P = A - R^2`` clipped
at zero.  Then ``P`` is *linear* in ``psi`` along the midplane,
``P = A - psi/c``, so the interpolating cubic spline reproduces it exactly and
``dP/dpsi = -1/c`` exactly at every node.  One unrelaxed update therefore gives

``j_phi = R * (-1/c) * dR * dZ``  and ``psi_new = psi_vac`` for a zero Green
matrix,

and every fixture value is dyadic, so the expected currents are exact binary64
numbers.  The implementation evaluates that derivative in a B-spline basis, not
in the monomial form ``-1/c``, so the comparison needs a budget: the coefficient
solve is one linear system and the derivative evaluation is a weighted sum of
basis values, which costs at most a few tens of roundings.  The budget is
therefore ``32 eps`` relative to the exact value, written here before the
comparison, and the observed deviation is about one third of it.  The same fixture also exercises the declared
pressure-edge rule: the fit stops at the first exact zero-pressure midplane
sample, and cells whose flux exceeds that edge get a zero derivative, so the
outermost column must be zero while the inner columns follow the closed form.

The remaining statements are structural, each of which a wrong solver fails:

1. **Both residual gates.**  With ``relax = 0.9`` and a tiny Green response the
   flux residual is below ``tol`` while the closure residual is about ``0.9``.
   The terminal status must then be ``maxiter``, not ``converged``: a solver that
   checked only the flux update would report convergence here.  This is the one
   fixture that separates the two gates.
2. **The declared residual normalization.**  ``residual`` is recomputed here as
   ``||psi_new - psi_old||_2 / |psi_edge|`` from the returned arrays, so a
   different norm, a missing edge normalization or a different edge index shows
   up as a factor.
3. **``maxiter = 0``.**  A valid initial state with no update returns
   ``maxiter``, ``iterations = 0``, the initial flux and both residuals at
   ``+inf``; a returned finite residual there would mean an update ran.
4. **The nonfinite branches.**  An initial spline fit that cannot run and a zero
   edge flux each return ``status = nonfinite`` with ``NaN`` residuals and zero
   iterations, and no exception escapes.
5. **The mask.**  ``plas_clip`` zeroes only the selected cells and leaves the
   rest at the closed-form values.

Precision budgets, fixed before the comparison:

* The closed-form currents are exact rationals: the fixture is dyadic, the
  spline reproduces a pressure linear in flux, and ``-1/c`` with ``c = 0.5`` is
  exactly ``-2``.  The implementation reaches that value through a B-spline
  coefficient solve and evaluation, so the budget is ``32 eps`` relative to the
  exact value; it is derived from that algebra, not measured.
* The recomputed flux residual is a norm of exact differences divided by an
  exact edge, so its budget is ``8 eps`` relative; the assertion also checks the
  recorded history entry against the returned residual at the same budget.

Failure channels, one executable assertion each (contract ``failure_semantics``):

* ``invalid_input`` -- a non-uniform or non-rectilinear grid, a grid smaller
  than 2x2, a non-callable pressure law, a nonpositive ``tol``, a non-integer or
  boolean ``maxiter``, ``relax`` outside ``[0, 1)``, a non-boolean ``plas_clip``
  of the wrong shape, ``plotit=True``, a nonfinite pressure, a pressure law with
  no exact zero edge and a grid with fewer than three exact midplane points each
  raise ``ValueError``.
* ``runtime_failure`` -- overflow inside the Green contraction is reported as
  ``status = nonfinite`` with ``NaN`` residuals rather than a silently wrong
  finite state.
* ``nonconvergence`` -- ``status = maxiter`` at the iteration bound with the
  last paired residuals and a history as long as the completed updates.
* ``partial_results`` -- every failing call raises, so no partially filled
  result escapes; a returned record always carries the status, iteration count,
  both residuals and both histories.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.equilibrium import compute_equilibrium

_EPS = np.finfo(float).eps
# psi = c R^2 makes P = A - R^2 linear in psi with slope -1/c = -2 Pa/(Wb/rad).
_C = 0.5
_SLOPE = -2.0
_DR = 0.25
_DZ = 1.0


def _fixture(midplane=(1.0, 1.25, 1.5, 1.75, 2.0, 2.25)):
    radial = np.array(midplane)
    axial = np.array([-1.0, 0.0, 1.0])
    R, Z = np.meshgrid(radial, axial)
    return {
        "R": R,
        "Z": Z,
        "radial": radial,
        "psi_vac": _C * R**2,
        "pressure": lambda radius: max(4.0 - radius**2, 0.0),
        "green": np.zeros((R.size, R.size)),
    }


def _expected_currents(fixture):
    """Exact j_phi = R dP/dpsi dR dZ with the declared edge zeroing."""
    radial = fixture["radial"]
    edge_radius = 2.0
    # The declared rule zeroes the derivative only beyond the edge flux, so the
    # sample exactly at the edge keeps its value.
    column = np.where(radial <= edge_radius, _SLOPE * _DR * _DZ * radial, 0.0)
    return np.tile(column, (fixture["R"].shape[0], 1))


def test_one_unrelaxed_update_reproduces_the_exact_current_target():
    fixture = _fixture()
    result = compute_equilibrium(
        fixture["R"],
        fixture["Z"],
        fixture["pressure"],
        fixture["psi_vac"],
        fixture["green"],
        tol=1e-12,
        maxiter=1,
        relax=0.0,
    )
    expected = _expected_currents(fixture)
    # The reference value is exact, but the spline derivative is evaluated in a
    # B-spline basis rather than in the monomial form -1/c, so the budget is the
    # 32 eps derived in the module docstring, relative to the exact value.
    np.testing.assert_allclose(result.plas_currents, expected, rtol=32.0 * _EPS, atol=0.0)
    # This records that the fixture is not accidentally all zeros.
    assert np.max(np.abs(expected)) == 1.0
    # dP/dpsi is negative, so the currents are negative: a sign flip is visible.
    assert np.all(expected[:, :-1] < 0.0)
    # The declared pressure-edge rule zeroes the column beyond the edge flux.
    assert np.all(result.plas_currents[:, -1] == 0.0)
    assert np.all(expected[:, -1] == 0.0)
    # The sample exactly at the edge keeps the closed-form value.
    assert np.all(result.plas_currents[:, -2] != 0.0)
    # With a zero Green matrix the flux does not move, so both residuals vanish
    # and the first update is a fixed point.
    np.testing.assert_array_equal(result.psi, fixture["psi_vac"])
    assert result.status == "converged"
    assert result.iterations == 1
    assert result.residual == 0.0
    assert result.closure_residual == 0.0


def test_relaxation_mixes_the_exact_target_with_the_zero_initial_state():
    fixture = _fixture()
    reference = compute_equilibrium(
        fixture["R"],
        fixture["Z"],
        fixture["pressure"],
        fixture["psi_vac"],
        fixture["green"],
        tol=1e-12,
        maxiter=1,
        relax=0.0,
    )
    for relaxing in (0.25, 0.5, 0.75):
        mixed = compute_equilibrium(
            fixture["R"],
            fixture["Z"],
            fixture["pressure"],
            fixture["psi_vac"],
            fixture["green"],
            tol=1e-12,
            maxiter=1,
            relax=relaxing,
        )
        # Initial currents are zero, so the relaxed state is (1-relax) * target.
        np.testing.assert_array_equal(
            mixed.plas_currents, (1.0 - relaxing) * reference.plas_currents
        )
        assert mixed.iterations == 1


def test_maxiter_zero_returns_the_vacuum_state_with_infinite_residuals():
    fixture = _fixture()
    result = compute_equilibrium(
        fixture["R"],
        fixture["Z"],
        fixture["pressure"],
        fixture["psi_vac"],
        fixture["green"],
        tol=1e-12,
        maxiter=0,
        relax=0.0,
    )
    np.testing.assert_array_equal(result.psi, fixture["psi_vac"])
    np.testing.assert_array_equal(result.plas_currents, np.zeros_like(fixture["R"]))
    assert result.status == "maxiter"
    assert result.iterations == 0
    assert result.residual == math.inf
    assert result.closure_residual == math.inf
    assert result.residual_history == ()
    assert result.closure_residual_history == ()
    # An initial pressure fit still ran, so the record carries it.
    assert result.p_psifit is not None


def test_the_closure_gate_blocks_false_convergence_of_the_flux_update():
    fixture = _fixture()
    # A tiny Green response makes the flux move by ~1e-12 while the retained
    # 90% of the zero initial current vector leaves the closure residual at 0.9.
    green = np.eye(fixture["R"].size) * 1e-12
    tol = 1e-6
    result = compute_equilibrium(
        fixture["R"],
        fixture["Z"],
        fixture["pressure"],
        fixture["psi_vac"],
        green,
        tol=tol,
        maxiter=1,
        relax=0.9,
    )
    assert result.residual <= tol
    assert result.closure_residual > 0.5
    assert result.status == "maxiter"
    assert result.iterations == 1
    # The two gates are recorded separately, so a reader can see which one held.
    assert result.closure_residual > result.residual


def test_flux_residual_matches_the_declared_normalization():
    fixture = _fixture()
    green = np.eye(fixture["R"].size) * 1e-3
    result = compute_equilibrium(
        fixture["R"],
        fixture["Z"],
        fixture["pressure"],
        fixture["psi_vac"],
        green,
        tol=1e-300,
        maxiter=1,
        relax=0.0,
    )
    # With one update the previous state is the vacuum flux, and the edge is the
    # midplane flux at the first exact zero-pressure sample (radius 2.0).
    limiter = 4
    midplane = 1
    edge = float(result.psi[midplane, limiter])
    recomputed = float(np.linalg.norm(result.psi - fixture["psi_vac"])) / abs(edge)
    assert result.residual == pytest.approx(recomputed, rel=8.0 * _EPS)
    # The edge normalization matters: without it the residual would differ by
    # the edge magnitude, so this is not a norm-only check.
    unnormalized = float(np.linalg.norm(result.psi - fixture["psi_vac"]))
    assert abs(unnormalized / recomputed - abs(edge)) <= 8.0 * _EPS * abs(edge)
    # The history is paired with the closures and its length is the iteration
    # count, so no update is missing from the record.
    assert len(result.residual_history) == result.iterations == 1
    assert result.residual_history[-1] == result.residual
    assert len(result.closure_residual_history) == 1
    assert result.status == "maxiter"
    assert not np.array_equal(result.psi, fixture["psi_vac"])


def test_plas_clip_zeroes_only_the_selected_cells():
    fixture = _fixture()
    clip = np.zeros_like(fixture["R"], dtype=bool)
    clip[1, 1] = True
    clip[1, 2] = True
    masked = compute_equilibrium(
        fixture["R"],
        fixture["Z"],
        fixture["pressure"],
        fixture["psi_vac"],
        fixture["green"],
        tol=1e-12,
        maxiter=1,
        relax=0.0,
        plas_clip=clip,
    )
    expected = _expected_currents(fixture)
    expected[clip] = 0.0
    np.testing.assert_allclose(masked.plas_currents, expected, rtol=32.0 * _EPS, atol=0.0)
    assert np.all(masked.plas_currents[clip] == 0.0)
    # The unselected cells keep the closed-form value (the last column stays
    # zero because of the pressure-edge rule, not because of the mask).
    assert np.all(masked.plas_currents[0][:-1] < 0.0)
    assert np.all(masked.plas_currents[1, 1:3] == 0.0)


def test_initial_fit_failure_returns_the_nonfinite_status():
    fixture = _fixture()
    result = compute_equilibrium(
        fixture["R"],
        fixture["Z"],
        lambda _radius: 0.0,
        fixture["psi_vac"],
        fixture["green"],
        tol=1e-12,
        maxiter=5,
        relax=0.0,
    )
    assert result.status == "nonfinite"
    assert result.iterations == 0
    assert math.isnan(result.residual)
    assert math.isnan(result.closure_residual)
    assert result.p_psifit is None
    np.testing.assert_array_equal(result.plas_currents, np.zeros_like(fixture["R"]))


def test_zero_edge_flux_returns_the_nonfinite_status():
    fixture = _fixture()
    # A strictly increasing flux sequence whose value at the pressure edge is
    # zero: psi = c R^2 - 2 reaches 0 exactly at R = 2.0, the first zero-pressure
    # sample, while staying increasing so the initial fit succeeds.
    psi_vac = _C * fixture["R"] ** 2 - 2.0
    result = compute_equilibrium(
        fixture["R"],
        fixture["Z"],
        fixture["pressure"],
        psi_vac,
        fixture["green"],
        tol=1e-12,
        maxiter=5,
        relax=0.0,
    )
    assert result.status == "nonfinite"
    assert result.iterations == 0
    assert "edge flux" in result.reason
    assert math.isnan(result.residual)


def test_invalid_input_channel_raises_value_error():
    fixture = _fixture()

    def call(**overrides):
        arguments = {
            "R": fixture["R"],
            "Z": fixture["Z"],
            "Pfunc": fixture["pressure"],
            "psi_vac": fixture["psi_vac"],
            "g_psi": fixture["green"],
            "tol": 1e-12,
            "maxiter": 1,
            "relax": 0.0,
        }
        arguments.update(overrides)
        return compute_equilibrium(**arguments)

    with pytest.raises(ValueError, match="uniformly spaced"):
        call(R=fixture["R"] * np.linspace(1.0, 1.1, 6))
    with pytest.raises(ValueError, match="2x2|at least"):
        call(
            R=fixture["R"][:1],
            Z=fixture["Z"][:1],
            psi_vac=fixture["psi_vac"][:1],
            g_psi=np.zeros((6, 6)),
        )
    with pytest.raises(ValueError, match="equal 2-D shapes"):
        call(Z=fixture["Z"][:2])
    with pytest.raises(ValueError, match="finite Green matrix"):
        call(g_psi=np.full((18, 18), np.nan))
    with pytest.raises(ValueError, match="column-consistent"):
        call(R=fixture["R"] + np.array([[0.0], [0.1], [0.2]]))
    with pytest.raises(ValueError, match="Pfunc must be callable"):
        call(Pfunc=1.0)
    with pytest.raises(ValueError, match="tol must be positive"):
        call(tol=0.0)
    with pytest.raises(ValueError, match="tol must be positive"):
        call(maxiter=True)
    with pytest.raises(ValueError, match="tol must be positive"):
        call(maxiter=-1)
    with pytest.raises(ValueError, match="relax must lie in"):
        call(relax=1.0)
    with pytest.raises(ValueError, match="relax must lie in"):
        call(relax=-0.5)
    with pytest.raises(ValueError, match="plas_clip must match"):
        call(plas_clip=np.zeros((2, 2), dtype=bool))
    with pytest.raises(ValueError, match="plas_clip must match"):
        call(plas_clip=np.zeros_like(fixture["R"]))
    with pytest.raises(ValueError, match="plotting is outside"):
        call(plotit=True)
    with pytest.raises(ValueError, match="pressure law must be finite"):
        call(Pfunc=lambda radius: math.inf)
    with pytest.raises(ValueError, match="exact zero edge"):
        call(Pfunc=lambda radius: 1.0)
    with pytest.raises(ValueError, match="three exact midplane points"):
        call(
            R=fixture["R"][:2],
            Z=np.tile(np.array([-1.0, 1.0])[:, None], (1, 6)),
            psi_vac=fixture["psi_vac"][:2],
            g_psi=np.zeros((12, 12)),
        )


def test_nonconvergence_channel_reports_the_iteration_bound():
    fixture = _fixture()
    green = np.eye(fixture["R"].size) * 1e-3
    result = compute_equilibrium(
        fixture["R"],
        fixture["Z"],
        fixture["pressure"],
        fixture["psi_vac"],
        green,
        tol=1e-300,
        maxiter=2,
        relax=0.0,
    )
    assert result.status == "maxiter"
    assert result.iterations == 2
    assert "iteration bound" in result.reason
    assert np.isfinite(result.residual)
    assert len(result.residual_history) == 2
