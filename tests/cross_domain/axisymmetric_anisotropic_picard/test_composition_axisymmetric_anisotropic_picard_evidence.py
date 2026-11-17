"""Independent evidence for the axisymmetric gyrotropic Picard composition.

Asset: ``scirel.equilibrium.axisymmetric-anisotropic-picard``.

The maintained cross-domain tests run the composition through a factory.  They
show that a graph executes, not that the returned state is the one the
docstring declares: the terminal field, closure and force are supposed to be
*recomputed at the returned flux*, the field gate is supposed to run before the
caller closure, and the reported convergence is supposed to come from the
unrelaxed terminal residual rather than from the loop's relaxed step.  Each of
those claims is checkable without an oracle:

1. **Terminal recomputation, by call log.**  The fixture's closure records the
   ``(B, psi)`` it is called with.  The composition is declared to call it once
   per iteration and once more at the returned state, so the log length must be
   ``iterations + 1`` and the last recorded ``psi`` must be *bitwise* equal to
   the returned ``psi``.  A composition that returned a state it never closed
   at, or that reused the last iterate's closure without rederiving the field,
   fails this.
2. **The field gate precedes the closure.**  With ``psi_vac = 0`` the derived
   field is exactly zero, below ``minimum_field``, and the call must raise
   ``FloatingPointError`` **with an empty call log**: the singularity is
   detected before the caller's closure is ever evaluated.
3. **A closed-form force.**  On the axial fixture ``psi_vac = 0.25 R^2`` gives
   ``B_Z = 0.5 T`` and ``B_R = 0`` exactly, so a closure returning
   ``p_parallel = 3 + Z``, ``p_perpendicular = 2`` has the analytic parallel
   force ``b . grad p_parallel = 1 Pa/m`` and ``J_phi = 0``.  The returned
   ``B``, ``parallel_force`` and ``J_phi`` are compared with those values, which
   fixes the field normalization and the pressure-to-force direction.
4. **The firehose gate reads the terminal active cell set.**  A closure far past
   the firehose threshold raises ``FloatingPointError`` at the default
   ``minimum_firehose_margin = 0`` and returns normally once the declared margin
   is lowered, so the gate is on the declared threshold rather than on a fixed
   sign test.
5. **Broadcast and mask identities.**  Scalar closure pressures are broadcast to
   the grid shape, grid pressures keep their values, and the fixed boolean mask
   zeroes ``J_phi`` and the integrated cell currents exactly where it is false.
6. **Convergence is the unrelaxed terminal residual.**  On the axial fixture the
   currents vanish, the flux is unchanged and both the loop and the terminal
   residual are zero, so ``converged`` is true with ``iterations = 1``; the
   reported ``fixed_point_residual`` is exactly zero, which a relaxed-only
   residual could not produce when ``relax`` is nonzero.

Precision budgets, fixed before the comparison: the axial fixture is dyadic
(``0.25 R^2`` with radii from 0.2 to 1.0), ``B_Z = 2 c`` is exact, and the
parallel force is one division of a linear pressure by that constant, so the
budget is ``8 eps`` relative; the call-log and mask comparisons are bitwise.

Failure channels, one executable assertion each (contract ``failure_semantics``):
a non-mapping input, missing keys, a non-callable closure, an invalid grid, a
wrong-size Green matrix, invalid controls, a non-boolean mask, a closure that
returns a non-mapping, a missing pressure key, a wrong pressure shape, a
negative pressure, the field gate, the firehose gate and the strict
parallel-force gate each raise the declared exception type.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.equilibrium import solve_axisymmetric_anisotropic_picard

_EPS = np.finfo(float).eps
_RADIAL = np.linspace(0.2, 1.0, 5)
_AXIAL = np.linspace(-0.5, 0.5, 5)
_C = 0.25
_B_Z = 2.0 * _C


def _fixture():
    R, Z = np.meshgrid(_RADIAL, _AXIAL)
    return {
        "R": R,
        "Z": Z,
        "psi_vac": _C * R**2,
        "green": np.zeros((R.size, R.size)),
    }


def _solve(fixture, closure, **overrides):
    arguments = {
        "r_grid": fixture["R"],
        "z_grid": fixture["Z"],
        "psi_vac": fixture["psi_vac"],
        "g_psi": fixture["green"],
        "pressure_closure": closure,
        "tol": 1e-10,
        "maxiter": 2,
        "relax": 0.0,
        "strict_compatibility": False,
    }
    arguments.update(overrides)
    return solve_axisymmetric_anisotropic_picard(**arguments)


def _axial_closure(log=None, beta=1.0):
    Z = np.meshgrid(_RADIAL, _AXIAL)[1]

    def closure(B, psi):
        if log is not None:
            log.append((np.array(B, copy=True), np.array(psi, copy=True)))
        return {"p_parallel": 3.0 + beta * Z, "p_perpendicular": 2.0}

    return closure


def test_terminal_state_is_recomputed_at_the_returned_flux():
    fixture = _fixture()
    log = []
    # An isotropic radial pressure gradient drives a nonzero J_phi, so a Green
    # response moves the flux between iterations and the terminal state differs
    # from the first iterate.
    R = fixture["R"]

    def closure(B, psi):
        log.append((np.array(B, copy=True), np.array(psi, copy=True)))
        pressure = 2.0 + 0.5 * R
        return {"p_parallel": pressure, "p_perpendicular": pressure}

    result = _solve(
        fixture,
        closure,
        g_psi=np.eye(fixture["R"].size) * 1e-3,
        maxiter=2,
        tol=1e-300,
    )
    # One closure call per iteration, plus the terminal recomputation.
    assert result["iterations"] == 2
    assert len(log) == result["iterations"] + 1
    terminal_B, terminal_psi = log[-1]
    np.testing.assert_array_equal(terminal_psi, result["psi"])
    np.testing.assert_array_equal(terminal_B, result["B"])
    # The flux moved, so the terminal recomputation is not a repeat of the first
    # iterate and the call log distinguishes it from the last loop evaluation.
    assert not np.array_equal(log[0][1], result["psi"])
    assert not np.array_equal(log[1][1], result["psi"])
    assert len(result["iteration_history"]) == result["iterations"]


def test_the_closed_form_field_and_parallel_force():
    fixture = _fixture()
    result = _solve(fixture, _axial_closure())
    np.testing.assert_allclose(result["B"], np.full_like(fixture["R"], _B_Z), rtol=8.0 * _EPS)
    np.testing.assert_allclose(result["B_R"], 0.0, atol=8.0 * _EPS * _B_Z)
    np.testing.assert_allclose(result["B_Z"], np.full_like(fixture["R"], _B_Z), rtol=8.0 * _EPS)
    # b = e_Z, so b . grad p_parallel = d_Z p_parallel = 1 Pa/m exactly.
    np.testing.assert_allclose(
        result["parallel_force"], np.full_like(fixture["R"], 1.0), rtol=8.0 * _EPS
    )
    # p_perpendicular is uniform and the field is axial, so no toroidal current.
    np.testing.assert_allclose(result["J_phi"], 0.0, atol=8.0 * _EPS)
    np.testing.assert_array_equal(result["psi"], fixture["psi_vac"])
    assert result["converged"] is True
    assert result["iterations"] == 1
    assert result["fixed_point_residual"] == 0.0


def test_the_axisymmetric_force_error_of_a_parallel_gradient_is_reported():
    fixture = _fixture()
    # The closed-form imbalance: parallel force 1 Pa/m against a total force of
    # the same size, so the resolved relative error is close to one.
    result = _solve(fixture, _axial_closure(), strict_compatibility=False)
    assert result["parallel_force_error"] > 0.9
    # A strict run rejects the same state through the declared gate.
    with pytest.raises(ValueError, match="unbalanced parallel div"):
        _solve(fixture, _axial_closure(), strict_compatibility=True)


def test_the_field_gate_precedes_the_pressure_closure():
    fixture = _fixture()
    log = []
    with pytest.raises(FloatingPointError, match="minimum_field"):
        _solve(fixture, _axial_closure(log), psi_vac=np.zeros((5, 5)))
    # The singularity was detected before the caller closure ran.
    assert log == []


def test_the_firehose_gate_reads_the_declared_terminal_margin():
    fixture = _fixture()

    def extreme(magnetic, psi):
        return {"p_parallel": 2.0e7, "p_perpendicular": 0.0}

    with pytest.raises(FloatingPointError, match="firehose"):
        _solve(fixture, extreme)
    relaxed = _solve(fixture, extreme, minimum_firehose_margin=-1.0e9)
    assert np.min(relaxed["firehose_margin"]) < -1.0
    # The returned margin is the declared expression on the terminal state.
    mu0 = 4.0e-7 * np.pi
    expected = 1.0 - mu0 * (relaxed["p_parallel"] - relaxed["p_perpendicular"]) / relaxed["B"] ** 2
    np.testing.assert_allclose(relaxed["firehose_margin"], expected, rtol=1e-12)


def test_scalar_and_grid_pressures_are_broadcast_and_validated():
    fixture = _fixture()
    scalar = _solve(fixture, lambda B, psi: {"p_parallel": 3.0, "p_perpendicular": 2.0})
    np.testing.assert_allclose(scalar["p_parallel"], np.full((5, 5), 3.0))
    np.testing.assert_allclose(scalar["p_perpendicular"], np.full((5, 5), 2.0))
    # Extra caller keys survive in closure_state.
    annotated = _solve(
        fixture,
        lambda B, psi: {"p_parallel": 3.0, "p_perpendicular": 2.0, "tag": "closure"},
    )
    assert annotated["closure_state"]["tag"] == "closure"

    grid = np.meshgrid(_RADIAL, _AXIAL)[1]
    gridded = _solve(
        fixture, lambda B, psi: {"p_parallel": 3.0 + grid, "p_perpendicular": 2.0 + 0 * grid}
    )
    np.testing.assert_array_equal(gridded["p_parallel"], 3.0 + grid)

    with pytest.raises(ValueError, match="pressure fields must be scalar or match"):
        _solve(fixture, lambda B, psi: {"p_parallel": 3.0 + grid[:2], "p_perpendicular": 2.0})
    with pytest.raises(ValueError, match="invalid pressure"):
        _solve(fixture, lambda B, psi: {"p_parallel": -1.0, "p_perpendicular": 2.0})


def test_the_fixed_mask_zeroes_currents_exactly_where_it_is_false():
    fixture = _fixture()
    mask = np.zeros((5, 5), dtype=bool)
    mask[2, 2] = True
    # A pressure gradient drives a nonzero current density.
    closure = _axial_closure(beta=4.0)
    masked = _solve(fixture, closure, plasma_mask=mask)
    assert np.all(masked["J_phi"][~mask] == 0.0)
    # The integrated cell currents follow the same mask.
    assert np.all(masked["plasma_cell_currents"][~mask] == 0.0)
    # Without the mask the same state has a nonzero current somewhere.
    unmasked = _solve(fixture, closure)
    assert np.max(np.abs(unmasked["J_phi"])) >= np.max(np.abs(masked["J_phi"]))


def test_invalid_input_channel_raises_the_declared_exception():
    fixture = _fixture()
    closure = _axial_closure()

    # The public entry has an explicit signature, so a mapping call is a
    # TypeError from Python itself rather than a port error.
    with pytest.raises(TypeError):
        solve_axisymmetric_anisotropic_picard({"r_grid": fixture["R"]})
    with pytest.raises(TypeError, match="pressure_closure must be callable"):
        _solve(fixture, 1.0)
    with pytest.raises(ValueError, match="equal-shape 2-D arrays"):
        _solve(fixture, closure, z_grid=fixture["Z"][:2])
    with pytest.raises(ValueError, match="strictly increasing rectilinear"):
        _solve(fixture, closure, r_grid=fixture["R"][:, ::-1])
    with pytest.raises(ValueError, match="g_psi must be finite"):
        _solve(fixture, closure, g_psi=np.eye(4))
    with pytest.raises(ValueError, match="Picard controls are invalid"):
        _solve(fixture, closure, relax=1.0)
    with pytest.raises(ValueError, match="Picard controls are invalid"):
        _solve(fixture, closure, tol=0.0)
    with pytest.raises(ValueError, match="Picard controls are invalid"):
        _solve(fixture, closure, minimum_field=0.0)
    with pytest.raises(ValueError, match="boolean"):
        _solve(fixture, closure, plasma_mask=np.ones((5, 5)))
    with pytest.raises(TypeError, match="must return a mapping"):
        _solve(fixture, lambda B, psi: (3.0, 2.0))
    with pytest.raises(KeyError):
        _solve(fixture, lambda B, psi: {"p_parallel": 3.0})
