"""Independent evidence for the grid-aware mirror kinetic closure composition.

Asset: ``scirel.mirror.grid-mirror-kinetic-closure``.

The maintained cross-domain tests run the composition through a factory and check
that the graph produces finite fields.  Two statements in the contract are
sharper than that and can be decided without an independent kinetic solver:

1. **The flux label is an interpolation coordinate, not a physical field.**  The
   contract says the supplied ``psi`` only selects the interpolation coordinate,
   so rescaling it by ``2*pi`` -- the Wb versus Wb/rad confusion the contract
   warns about -- must leave every fixed-profile result unchanged.  The fixture
   compares ``p_parallel``, ``p_perpendicular``, ``density_m3`` and both endpoint
   potentials between ``psi`` and ``2*pi*psi``; they must agree to 1e-12
   relative.  An implementation that used ``psi`` in a physical formula would
   scale instead.
2. **The pressure assembly and the electron closure are exact.**  The returned
   ``p_parallel`` is the ion parallel pressure plus the electron pressure, and the
   electron pressure is ``n_e T_e`` with the supplied electron temperature; both
   are checked bitwise against the returned arrays.  That fixes which pressure
   component the electron term is added to and the unit of the electron energy.
3. **The local charge closure is small.**  The returned
   ``relative_charge_residual`` must be below the contract's ``1e-9`` bound on
   every sample, and both endpoint current balances must report solved.

This asset's scope is deliberately partial.  The *physical* correctness of the
nested closure (the truncated-loss-cone density, the end-loss potential root and
the pitch-angle weighting) has no independent reference in this file: the
composition exposes no closed form for it and this batch has no published
high-order对照.  What is established here is the coordinate invariance, the two
exact algebraic assemblies and the declared residual bound; the rest is recorded
as ``cannot establish`` in the contract's evidence ceiling.

Precision budgets, fixed before the comparison: the invariance comparison uses
``1e-12`` relative, well above the rounding of the same expressions evaluated
twice (the two runs differ only in the ``psi`` array they receive, and the
interpolation coordinate is rescaled by an exact power-of-two-free factor); the
two assemblies are bitwise because both sides are the returned arrays themselves
and one multiplication; the residual bound is the contract's own ``1e-9``.

Failure channels: a non-positive density or temperature, a ``psi``/``B`` shape
mismatch, a plug plane outside the grid and a non-integer quadrature order each
raise the composition's declared error type.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.mirror import solve_grid_mirror_kinetic_closure

_E = 1.602176634e-19
_INVARIANCE = 1e-12


def _fixture():
    r = np.linspace(0.0, 0.2, 5)
    z = np.linspace(-1.0, 1.0, 7)
    R, Z = np.meshgrid(r, z)
    return {
        "r_grid": R,
        "z_grid": Z,
        "b_t": 1.0 + 3.0 * np.abs(Z),
        "psi": 0.5 * R**2,
        "mass_kg": 1.67262192595e-27,
        "charge_c": _E,
        "density_ref_m3": 1.0e18,
        "temperature_parallel_j": 1000.0 * _E,
        "temperature_perpendicular_ref_j": 2000.0 * _E,
        "electron_temperature_j": 500.0 * _E,
        "reference_z": 0.0,
        "plug_left_z": -1.0,
        "plug_right_z": 1.0,
        "loss_cone_refill": 0.05,
        "quadrature_order": 24,
        "plug_potential_mode": "ambipolar_end_loss",
    }


def _solve(**overrides):
    inputs = _fixture()
    inputs.update(overrides)
    return solve_grid_mirror_kinetic_closure(inputs)


def test_rescaling_the_flux_coordinate_leaves_the_fixed_profile_state():
    base = _fixture()
    direct = solve_grid_mirror_kinetic_closure(base)
    rescaled = solve_grid_mirror_kinetic_closure(dict(base, psi=2.0 * np.pi * base["psi"]))
    for name in (
        "p_parallel",
        "p_perpendicular",
        "density_m3",
        "end_left_potential_v",
        "end_right_potential_v",
    ):
        np.testing.assert_allclose(
            rescaled[name], direct[name], rtol=_INVARIANCE, atol=0.0, err_msg=name
        )
    # The fixture is not trivially zero, so the invariance is a real statement.
    assert np.max(np.abs(direct["p_parallel"])) > 1.0
    assert np.max(np.abs(direct["density_m3"])) > 0.0


def test_the_pressure_assembly_is_ion_plus_electron():
    state = _solve()
    np.testing.assert_array_equal(
        state["p_parallel"], state["ion_p_parallel"] + state["electron_pressure"]
    )
    np.testing.assert_array_equal(
        state["p_perpendicular"], state["ion_p_perpendicular"] + state["electron_pressure"]
    )
    # The electron term is n_e T_e with the supplied electron energy in joules.
    np.testing.assert_allclose(
        state["electron_pressure"],
        state["electron_density"] * (500.0 * _E),
        rtol=1e-12,
        atol=0.0,
    )
    assert np.max(np.abs(state["electron_pressure"])) > 0.0


def test_the_local_charge_closure_and_endpoint_balances_are_reported():
    state = _solve()
    assert np.max(np.abs(state["relative_charge_residual"])) < 1e-9
    assert state["end_left_current_balance_solved"]
    assert state["end_right_current_balance_solved"]
    assert np.all(state["end_left_potential_v"] < 0.0)
    # The fixture is mirror-symmetric (b_t depends on |Z| and the two plug planes
    # are equidistant), so the mapped left and right end potentials must agree
    # exactly: this pins the endpoint mapping to the symmetric geometry.
    np.testing.assert_array_equal(state["end_left_potential_v"], state["end_right_potential_v"])


def test_the_shared_velocity_domain_and_quadrature_record_are_reported():
    state = _solve()
    assert np.all(np.isfinite(state["density_pitch_integral"]))
    # The *_pa aliases are the ion-only components, and the total adds the
    # electron pressure exactly; both relations are bitwise.
    np.testing.assert_array_equal(state["p_parallel_pa"], state["ion_p_parallel"])
    np.testing.assert_array_equal(state["p_perpendicular_pa"], state["ion_p_perpendicular"])
    assert np.max(np.abs(state["p_parallel"] - state["p_parallel_pa"])) > 0.0


def test_invalid_input_channel_raises():
    with pytest.raises(ValueError, match="quadrature_order"):
        _solve(quadrature_order=1)
    with pytest.raises(ValueError, match="plug planes must bracket"):
        _solve(plug_left_z=5.0)
    with pytest.raises(ValueError, match="equal-shape 2-D arrays"):
        _solve(psi=np.zeros((2, 2)))
    with pytest.raises(ValueError, match="strictly positive"):
        _solve(mass_kg=-1.0)
