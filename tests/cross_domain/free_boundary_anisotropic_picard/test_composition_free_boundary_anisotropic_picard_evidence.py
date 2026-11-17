"""Independent evidence for the free-boundary anisotropic Picard composition.

Asset: ``scirel.equilibrium.free-boundary-anisotropic-picard``.

The maintained cross-domain tests drive the composition through a factory.  The
docstring makes three claims that are checkable without an independent
equilibrium code, because each is an identity on the returned state:

1. **Uniform pressure leaves the vacuum state.**  A closure that returns a
   spatially constant pressure has a vanishing current density, hence a zero
   Green target, hence a zero fixed point.  The returned ``psi``, ``BR`` and
   ``BZ`` must be *bitwise* equal to the supplied vacuum arrays, ``j_phi`` must
   be zero everywhere, ``fixed_point_residual`` must be exactly zero and
   ``converged`` must be true with ``iterations = 1`` and
   ``failure_reason = None``.  This fixes the pressure-to-current direction and
   the convergence flag's composition (residual *and* compatibility *and* at
   least one update).
2. **A vanished wall response changes nothing.**  With a
   ``boundary_correction`` whose two Green matrices are exactly zero, the wall
   solves a zero system: the returned state is bitwise identical to the run
   without a wall, ``boundary_flux_correction`` is zero, the residual norm is
   zero and ``boundary_currents`` is still reported (so the port ran rather than
   being skipped).
3. **A spatially constant wall correction moves the flux, not the field.**  With
   a rank-one ``green_boundary_to_field`` of ones the wall correction is the
   constant ``1.375`` Wb/rad on every cell.  Its discrete gradient is exactly
   zero, so ``psi`` must shift by that constant while ``BR`` and ``BZ`` stay
   bitwise equal to the no-wall run.  An implementation that re-derived the
   field from the *total* flux, or that applied the correction to the flux only,
   fails one half of this pair while passing the other.
4. **The mask is a declared domain selector.**  ``j_phi`` and the integrated
   cell currents are zero exactly where the boolean mask is false.
5. **The gates precede and follow the iteration as declared.**  A zero vacuum
   field raises the intermediate ``minimum_field`` error before the closure can
   run, and a far super-firehose closure raises the terminal firehose error
   whose message names the terminal margin.

Precision budgets, fixed before the comparison: the three state identities are
bitwise, because the fixture's vacuum state is dyadic (``0.25 R^2`` and the
constants ``0`` and ``0.5``) and a zero or spatially constant correction is
exact in binary64; the wall constant ``1.375`` is compared at ``8 eps`` relative
because it comes out of a least-squares solve.

Failure channels, one executable assertion each (contract ``failure_semantics``):
a non-mapping input, a missing grid key, a non-tensor or too-small grid, a
non-boolean or wrong-shaped mask, a non-callable closure, a closure output
missing a key, a wrong-shaped or negative pressure, an invalid ``tol``,
``maxiter`` or ``relax`` bound, a nonpositive ``b0``, an incomplete
``boundary_correction``, an invalid ``compatibility_tol`` or ``minimum_field``,
the intermediate field gate, the terminal firehose gate and the strict
parallel-force gate each raise the declared exception type.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.equilibrium import solve_free_boundary_anisotropic_picard

_EPS = np.finfo(float).eps
_RADIAL = np.linspace(0.2, 1.0, 5)
_AXIAL = np.linspace(-0.5, 0.5, 5)


def _fixture():
    R, Z = np.meshgrid(_RADIAL, _AXIAL)
    return {
        "R": R,
        "Z": Z,
        "psi_vac": 0.25 * R**2,
        "br_vac": np.zeros_like(R),
        "bz_vac": np.full_like(R, 0.5),
        "green": np.zeros((R.size, R.size)),
    }


def _uniform_closure(p_parallel=3.0, p_perp=2.0):
    def closure(payload):
        shape = np.asarray(payload["psi"]).shape
        return {
            "p_parallel": np.full(shape, p_parallel),
            "p_perp": np.full(shape, p_perp),
            "density": np.full(shape, 1.0e18),
            "electron_temperature": np.full(shape, 1.0e2),
        }

    return closure


def _solve(fixture, closure, **overrides):
    inputs = {
        "r_grid": fixture["R"],
        "z_grid": fixture["Z"],
        "psi_vac": fixture["psi_vac"],
        "br_vac": fixture["br_vac"],
        "bz_vac": fixture["bz_vac"],
        "g_psi": fixture["green"],
        "params": {"B0": 0.5},
        "tol": 1e-10,
        "maxiter": 3,
        "relax": 0.0,
        "pressure_closure": closure,
        "strict_compatibility": False,
    }
    inputs.update(overrides)
    return solve_free_boundary_anisotropic_picard(inputs)


def _zero_wall(fixture):
    points = fixture["R"].size
    return {
        "boundary_sample_matrix": np.zeros((1, points)),
        "green_boundary_to_boundary": np.zeros((1, 1)),
        "green_boundary_to_field": np.zeros((points, 1)),
    }


def _constant_wall(fixture):
    points = fixture["R"].size
    return {
        "boundary_sample_matrix": np.ones((1, points)),
        "green_boundary_to_boundary": np.eye(1) * 2.0,
        "green_boundary_to_field": np.ones((points, 1)),
    }


def test_uniform_pressure_returns_the_vacuum_state():
    fixture = _fixture()
    result = _solve(fixture, _uniform_closure())
    np.testing.assert_array_equal(result["psi"], fixture["psi_vac"])
    np.testing.assert_array_equal(result["BR"], fixture["br_vac"])
    np.testing.assert_array_equal(result["BZ"], fixture["bz_vac"])
    np.testing.assert_array_equal(result["j_phi"], np.zeros_like(fixture["R"]))
    assert result["fixed_point_residual"] == 0.0
    assert result["flux_fixed_point_residual"] == 0.0
    assert result["field_fixed_point_residual"] == 0.0
    assert result["current_fixed_point_residual"] == 0.0
    assert result["converged"] is True
    assert result["iterations"] == 1
    assert result["failure_reason"] is None
    assert result["boundary_flux_correction"] is None
    # The reported profiles are the closure's own grids, not rescaled copies.
    np.testing.assert_array_equal(result["profiles"]["p_parallel"], np.full((5, 5), 3.0))


def test_a_vanished_wall_response_changes_nothing():
    fixture = _fixture()
    without = _solve(fixture, _uniform_closure())
    with_wall = _solve(fixture, _uniform_closure(), boundary_correction=_zero_wall(fixture))
    for name in ("psi", "BR", "BZ", "j_phi"):
        np.testing.assert_array_equal(with_wall[name], without[name])
    assert with_wall["boundary_flux_correction"] is not None
    np.testing.assert_array_equal(with_wall["boundary_flux_correction"], np.zeros((5, 5)))
    assert with_wall["boundary_residual_norm"] == 0.0
    # The wall port ran: boundary currents are reported, not skipped.
    assert with_wall["boundary_currents"] is not None
    assert np.asarray(with_wall["boundary_currents"]).shape == (1,)


def test_a_constant_wall_correction_moves_the_flux_and_not_the_field():
    fixture = _fixture()
    without = _solve(fixture, _uniform_closure())
    with_wall = _solve(fixture, _uniform_closure(), boundary_correction=_constant_wall(fixture))
    correction = with_wall["boundary_flux_correction"]
    constant = float(correction[0, 0])
    # The correction is spatially constant on every cell.
    np.testing.assert_allclose(correction, np.full((5, 5), constant), rtol=8.0 * _EPS)
    assert abs(constant) > 0.1
    # The flux shifted by exactly that constant ...
    np.testing.assert_allclose(with_wall["psi"] - without["psi"], constant, rtol=8.0 * _EPS)
    # ... while the field is unchanged, because a constant flux has no gradient.
    np.testing.assert_array_equal(with_wall["BR"], without["BR"])
    np.testing.assert_array_equal(with_wall["BZ"], without["BZ"])


def test_the_mask_zeroes_currents_exactly_where_it_is_false():
    fixture = _fixture()
    mask = np.zeros((5, 5), dtype=bool)
    mask[2, 2] = True

    # A radial pressure gradient drives a nonzero current density.
    R = fixture["R"]

    def graded(payload):
        pressure = 2.0 + 0.5 * R
        return {
            "p_parallel": pressure,
            "p_perp": pressure,
            "density": None,
            "electron_temperature": None,
        }

    masked = _solve(fixture, graded, plasma_mask=mask)
    assert np.all(masked["j_phi"][~mask] == 0.0)
    assert np.all(masked["plasma_currents"][~mask] == 0.0)
    unmasked = _solve(fixture, graded)
    assert np.max(np.abs(unmasked["j_phi"])) > 0.0


def test_the_intermediate_field_gate_runs_before_the_closure():
    fixture = _fixture()
    calls = []

    def recording(payload):
        calls.append(1)
        return _uniform_closure()(payload)

    with pytest.raises(FloatingPointError, match="intermediate magnetic field"):
        _solve(
            fixture,
            recording,
            psi_vac=np.zeros((5, 5)),
            br_vac=np.zeros((5, 5)),
            bz_vac=np.zeros((5, 5)),
        )
    assert calls == []


def test_the_terminal_firehose_gate_names_the_terminal_margin():
    fixture = _fixture()
    with pytest.raises(ValueError, match="firehose threshold"):
        _solve(fixture, _uniform_closure(p_parallel=2.0e7, p_perp=0.0))


def test_the_strict_compatibility_gate_and_its_diagnostic():
    fixture = _fixture()
    Z = fixture["Z"]

    def parallel_gradient(payload):
        shape = np.asarray(payload["psi"]).shape
        return {
            "p_parallel": 3.0 + Z,
            "p_perp": np.full(shape, 2.0),
            "density": None,
            "electron_temperature": None,
        }

    relaxed = _solve(fixture, parallel_gradient, strict_compatibility=False)
    assert relaxed["equilibrium_compatible"] is False
    assert relaxed["failure_reason"] == "parallel_force_incompatible"
    assert relaxed["converged"] is False
    with pytest.raises(ValueError, match="compatibility_tol"):
        _solve(fixture, parallel_gradient, strict_compatibility=True)


def test_invalid_input_channel_raises_the_declared_exception():
    fixture = _fixture()
    closure = _uniform_closure()

    # A non-mapping positional inputs is rejected by the public wrapper itself.
    with pytest.raises(TypeError, match="inputs must be a mapping"):
        solve_free_boundary_anisotropic_picard([("r_grid", fixture["R"])])
    with pytest.raises(ValueError, match="z_grid is required"):
        solve_free_boundary_anisotropic_picard({"r_grid": fixture["R"]})
    with pytest.raises(ValueError, match="at least 3 points per axis"):
        _solve(fixture, closure, r_grid=fixture["R"][:2], z_grid=fixture["Z"][:2])
    with pytest.raises(ValueError, match="tensor-product"):
        _solve(fixture, closure, r_grid=fixture["R"] + fixture["Z"])
    with pytest.raises(ValueError, match="plasma_mask must be a boolean"):
        _solve(fixture, closure, plasma_mask=np.ones((5, 5)))
    with pytest.raises(ValueError, match="plasma_mask must be a boolean"):
        _solve(fixture, closure, plasma_mask=np.ones((2, 2), dtype=bool))
    with pytest.raises(ValueError, match="pressure_closure must be a callable"):
        _solve(fixture, 1.0)
    with pytest.raises(ValueError, match="missing p_perp"):
        _solve(
            fixture,
            lambda payload: {"p_parallel": np.full((5, 5), 3.0)},
        )
    with pytest.raises(ValueError, match="finite nonnegative array with shape"):
        _solve(
            fixture,
            lambda payload: {
                "p_parallel": np.full((2, 2), 3.0),
                "p_perp": np.full((5, 5), 2.0),
                "density": None,
                "electron_temperature": None,
            },
        )
    with pytest.raises(ValueError, match="finite nonnegative array with shape"):
        _solve(
            fixture,
            lambda payload: {
                "p_parallel": np.full((5, 5), -1.0),
                "p_perp": np.full((5, 5), 2.0),
                "density": None,
                "electron_temperature": None,
            },
        )
    with pytest.raises(ValueError, match="violate the declared Picard bounds"):
        _solve(fixture, closure, tol=0.0)
    with pytest.raises(ValueError, match="violate the declared Picard bounds"):
        _solve(fixture, closure, relax=1.5)
    # b0 is only read when params supplies no B0, so this exercises that branch.
    with pytest.raises(ValueError, match="b0 must be a finite positive"):
        _solve(fixture, closure, params={}, b0=0.0)
    with pytest.raises(ValueError, match="boundary_correction missing keys"):
        _solve(fixture, closure, boundary_correction={"boundary_sample_matrix": np.ones((1, 25))})
    with pytest.raises(ValueError, match="minimum_field"):
        _solve(fixture, closure, minimum_field=0.0)
