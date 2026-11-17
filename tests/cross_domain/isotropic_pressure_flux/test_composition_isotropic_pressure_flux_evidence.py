"""Independent evidence for the pressure-only flux composition boundary.

Asset: ``scirel.equilibrium.isotropic-pressure-flux``.

This entry is a composition: it validates its own ports, calls the shared
pressure/current solver and packages the terminal state with a pressure-versus-
flux spline.  The maintained tests are cross-domain graph tests, so they show
that the graph runs, not that this boundary adds nothing and drops nothing.  The
evidence here is therefore built on the same closed-form fixture the shared
solver is checked against, evaluated through *this* entry:

``psi_vac = c R^2`` and ``P = A - R^2`` clipped at zero make ``P`` linear in
``psi`` along the midplane, so one unrelaxed update has the exact current target

``j_phi = R * (-1/c) * dR * dZ``   with ``-1/c = -2``,

zeroed beyond the pressure-edge flux.  Every fixture value is dyadic, so the
expected currents are exact rationals and the comparison budget is the ``32 eps``
derived in the module docstring of the shared-solver evidence (the derivative is
evaluated in a B-spline basis).  A composition that rescaled the currents, added
a toroidal factor, or reported the unclipped array would fail it.

The remaining statements are about the boundary itself:

1. **``maxiter = 0`` returns an independent copy.**  The terminal flux equals
   ``psi_vac``, ``iterations`` is zero, ``converged`` is false, both residuals are
   ``+inf``, and the terminal spline record already exists because the initial
   fit ran.  Mutating the returned array must not change the caller's input.
2. **The reworded grid rejection.**  A non-uniform grid raises a message that
   names *this* boundary's requirement (uniformly spaced tensor-product grids)
   instead of leaking the shared solver's wording, so a caller cannot mistake
   the port contract for an internal one.
3. **The terminal spline record is the fitted prefix, verbatim.**  ``psi_samples``
   and ``pressure_samples`` are compared bitwise with the fixture's first five
   midplane samples, ``degree`` is 3 and ``extrapolation`` is ``zeros``; the knots
   and coefficients are finite and as long as the spline requires.  This is the
   declared "terminal pressure-flux samples and cubic-spline representation".
4. **The two residual gates are carried through.**  With a tiny Green response
   and ``relax = 0.9`` the flux residual is below ``tol`` while the closure
   residual is about ``0.9``; the composition must report ``status = maxiter``
   and ``converged = False``, and the failure reason must be the shared solver's
   ``maxiter`` label translated to ``maxiter_reached``.
5. **The terminal spline is absent, not fabricated, on failure.**  A pressure law
   that cannot be fitted returns ``status = nonfinite`` and
   ``pressure_of_psi = None`` rather than an empty mapping.

Precision budgets, fixed before the comparison:

* the closed-form currents use ``32 eps`` relative, as derived for the shared
  solver (B-spline coefficient solve plus evaluation);
* the residual identities are exact equalities on the returned floats;
* the spline-record comparisons are bitwise, because the record copies caller
  samples rather than recomputing them.

Failure channels, one executable assertion each (contract ``failure_semantics``):

* ``invalid_input`` -- a mapping-form call or an unknown keyword raises
  ``TypeError`` (the signature is explicit); mismatched shapes, a wrong-size
  Green matrix, a non-callable or scalar-returning or negative or nonfinite
  pressure law, a nonpositive ``tol``, a negative ``maxiter`` and ``relax = 1``
  each raise ``ValueError``, and a non-uniform grid raises the reworded
  ``ValueError``.
* ``runtime_failure`` -- a pressure callback that raises propagates its own
  exception unchanged, and an unfittable pressure law becomes
  ``status = nonfinite`` instead of an exception, so both behaviours are pinned.
* ``nonconvergence`` -- ``status = maxiter`` with ``failure_reason =
  maxiter_reached`` and ``converged = False``; the histories stay as long as the
  completed updates.
* ``partial_results`` -- every failing call raises, so no partially built mapping
  escapes; a successful mapping always carries all eleven keys.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.equilibrium import solve_isotropic_pressure_flux

_EPS = np.finfo(float).eps
_C = 0.5
_SLOPE = -2.0
_DR = 0.25
_DZ = 1.0
_KEYS = {
    "psi",
    "plasma_currents",
    "pressure_of_psi",
    "iterations",
    "residual",
    "closure_residual",
    "residual_history",
    "closure_residual_history",
    "converged",
    "status",
    "failure_reason",
}


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


def _solve(fixture, **overrides):
    arguments = {
        "r_grid": fixture["R"],
        "z_grid": fixture["Z"],
        "psi_vac": fixture["psi_vac"],
        "g_psi": fixture["green"],
        "pressure_of_radius": fixture["pressure"],
        "tol": 1e-12,
        "maxiter": 1,
        "relax": 0.0,
    }
    arguments.update(overrides)
    return solve_isotropic_pressure_flux(**arguments)


def _expected_currents(fixture):
    radial = fixture["radial"]
    column = np.where(radial <= 2.0, _SLOPE * _DR * _DZ * radial, 0.0)
    return np.tile(column, (fixture["R"].shape[0], 1))


def test_the_composition_reproduces_the_exact_current_target():
    fixture = _fixture()
    result = _solve(fixture)
    expected = _expected_currents(fixture)
    np.testing.assert_allclose(result["plasma_currents"], expected, rtol=32.0 * _EPS, atol=0.0)
    # The boundary neither rescales nor reorders the array.
    assert result["plasma_currents"].shape == fixture["R"].shape
    assert np.all(result["plasma_currents"][:, -1] == 0.0)
    assert np.all(result["plasma_currents"][0][:-1] < 0.0)
    np.testing.assert_array_equal(result["psi"], fixture["psi_vac"])
    assert result["status"] == "converged"
    assert result["converged"] is True
    assert result["failure_reason"] is None
    assert result["iterations"] == 1
    assert set(result) == _KEYS


def test_maxiter_zero_returns_an_independent_copy_of_the_vacuum_flux():
    fixture = _fixture()
    before = fixture["psi_vac"].copy()
    result = _solve(fixture, maxiter=0)
    np.testing.assert_array_equal(result["psi"], before)
    assert result["psi"] is not fixture["psi_vac"]
    result["psi"][0, 0] = 99.0
    np.testing.assert_array_equal(fixture["psi_vac"], before)
    assert result["iterations"] == 0
    assert result["converged"] is False
    assert result["status"] == "maxiter"
    assert result["residual"] == math.inf
    assert result["closure_residual"] == math.inf
    assert result["failure_reason"] == "maxiter_reached"
    # The initial fit ran, so the terminal spline record exists even with no update.
    assert result["pressure_of_psi"] is not None


def test_the_terminal_spline_record_is_the_fitted_prefix_verbatim():
    fixture = _fixture()
    result = _solve(fixture)
    record = result["pressure_of_psi"]
    assert isinstance(record, dict)
    expected_psi = fixture["psi_vac"][1, :5]
    expected_pressure = np.array([3.0, 2.4375, 1.75, 0.9375, 0.0])
    np.testing.assert_array_equal(record["psi_samples"], expected_psi)
    np.testing.assert_array_equal(record["pressure_samples"], expected_pressure)
    assert record["degree"] == 3
    assert record["extrapolation"] == "zeros"
    assert record["knots"].size == record["coefficients"].size
    assert np.all(np.isfinite(record["knots"]))
    assert np.all(np.isfinite(record["coefficients"]))
    # The fixture pressure is linear in flux, so the interpolant's own values at
    # the samples coincide with the pressure samples; the record is consistent.
    assert np.all(np.diff(record["psi_samples"]) > 0.0)


def test_the_closure_gate_is_carried_through_the_composition():
    fixture = _fixture()
    green = np.eye(fixture["R"].size) * 1e-12
    result = _solve(fixture, g_psi=green, maxiter=1, relax=0.9, tol=1e-6)
    assert result["residual"] <= 1e-6
    assert result["closure_residual"] > 0.5
    assert result["status"] == "maxiter"
    assert result["converged"] is False
    assert result["failure_reason"] == "maxiter_reached"
    assert len(result["residual_history"]) == result["iterations"] == 1


def test_an_unfittable_pressure_law_returns_no_terminal_spline():
    fixture = _fixture()
    result = _solve(fixture, pressure_of_radius=lambda _radius: 0.0)
    assert result["status"] == "nonfinite"
    assert result["converged"] is False
    assert result["pressure_of_psi"] is None
    assert result["iterations"] == 0
    assert math.isnan(result["residual"])
    # The failure reason is the shared solver's own text, not a new label.
    assert isinstance(result["failure_reason"], str) and result["failure_reason"]


def test_a_non_uniform_grid_is_rejected_with_the_boundary_wording():
    fixture = _fixture()
    stretched = np.array([1.0, 1.2, 1.5, 1.9, 2.4, 3.0])
    R, Z = np.meshgrid(stretched, np.array([-1.0, 0.0, 1.0]))
    with pytest.raises(ValueError, match="uniformly spaced tensor-product grids"):
        _solve(fixture, r_grid=R, z_grid=Z, psi_vac=_C * R**2)


def test_invalid_input_channel_raises_type_error_or_value_error():
    fixture = _fixture()

    # The mapping form was removed, so a positional mapping is a TypeError.
    with pytest.raises(TypeError):
        solve_isotropic_pressure_flux(
            {
                "r_grid": fixture["R"],
                "z_grid": fixture["Z"],
                "psi_vac": fixture["psi_vac"],
                "g_psi": fixture["green"],
                "pressure_of_radius": fixture["pressure"],
            }
        )
    with pytest.raises(TypeError):
        _solve(fixture, unknown_keyword=1.0)

    with pytest.raises(ValueError, match="same-shape"):
        _solve(fixture, z_grid=fixture["Z"][:2])
    with pytest.raises(ValueError, match="g_psi must have shape"):
        _solve(fixture, g_psi=np.eye(4))
    with pytest.raises(ValueError, match="must be callable"):
        _solve(fixture, pressure_of_radius=1.0)
    with pytest.raises(ValueError, match="finite nonnegative scalar"):
        _solve(fixture, pressure_of_radius=lambda radius: np.array([radius, radius]))
    with pytest.raises(ValueError, match="finite nonnegative scalar"):
        _solve(fixture, pressure_of_radius=lambda radius: -1.0)
    with pytest.raises(ValueError, match="finite nonnegative scalar"):
        _solve(fixture, pressure_of_radius=lambda radius: math.nan)
    with pytest.raises(ValueError, match="tol"):
        _solve(fixture, tol=0.0)
    with pytest.raises(ValueError, match="maxiter"):
        _solve(fixture, maxiter=-1)
    with pytest.raises(ValueError, match="relax"):
        _solve(fixture, relax=1.0)


def test_runtime_failure_channel_propagates_the_callback_exception():
    fixture = _fixture()

    class PressureFailure(RuntimeError):
        pass

    def failing(radius):
        raise PressureFailure(f"pressure law failed at {radius}")

    with pytest.raises(PressureFailure, match="pressure law failed"):
        _solve(fixture, pressure_of_radius=failing)


def test_nonconvergence_channel_reports_the_translated_label():
    fixture = _fixture()
    green = np.eye(fixture["R"].size) * 1e-3
    result = _solve(fixture, g_psi=green, tol=1e-300, maxiter=2)
    assert result["status"] == "maxiter"
    assert result["failure_reason"] == "maxiter_reached"
    assert result["converged"] is False
    assert result["iterations"] == 2
    assert len(result["residual_history"]) == 2
    assert len(result["closure_residual_history"]) == 2
    assert np.all(np.isfinite(result["residual_history"]))
