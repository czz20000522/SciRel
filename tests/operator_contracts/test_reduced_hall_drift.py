import numpy as np
import pytest

from scirel.closures.reduced_hall_drift import _source_hypot, close_reduced_hall_drift, close_reduced_hall_drift as scientific_operator


M, E = 1.67262192595e-27, 1.602176634e-19


def _grid():
    r, z = np.linspace(0.0, .4, 9), np.linspace(-.5, .5, 11)
    R, Z = np.meshgrid(r, z)
    return R, Z, np.zeros_like(R), np.full_like(R, 2.0)


def _state(shape, pressure=20.0):
    return {'ion_density': np.full(shape, 1e18), 'electron_pressure': np.zeros(shape), 'electrostatic_potential': np.zeros(shape), 'ion_p_parallel': np.full(shape, pressure), 'ion_p_perpendicular': np.full(shape, pressure)}


def test_uniform_state_has_zero_hall_current_and_flows():
    R, Z, BR, BZ = _grid()
    result = scientific_operator(R, Z, BR, BZ, np.full_like(R, 20.0), np.full_like(R, 20.0), _state(R.shape), np.ones_like(R, dtype=bool), M, E)
    np.testing.assert_allclose(result['J_phi'], 0.0, atol=1e-12)
    np.testing.assert_allclose(result['ion_toroidal_velocity'], 0.0, atol=1e-12)
    assert result['generalized_ohm_error'] < 1e-12


def test_zero_hall_multiplier_keeps_pressure_current_and_no_inertia_runs_once():
    R, Z, BR, BZ = _grid()
    pressure = 20.0 + R
    result = scientific_operator(
        R, Z, BR, BZ, pressure, pressure, _state(R.shape),
        np.ones_like(R, dtype=bool), M, E,
        hall_multiplier=0.0, include_toroidal_inertia=False,
    )
    np.testing.assert_allclose(result['J_phi'][:, 1:], 0.5, atol=1e-12)
    np.testing.assert_allclose(result['ion_toroidal_velocity'], 0.0)
    assert result['inertia_converged'] and result['inertia_iterations'] == 1


def test_local_inertia_budget_exhaustion_returns_no_state():
    R, Z, BR, BZ = _grid()
    pressure = 20.0 + R
    with pytest.raises(RuntimeError, match='inertia iteration did not converge'):
        scientific_operator(
            R, Z, BR, BZ, pressure, pressure, _state(R.shape),
            np.ones_like(R, dtype=bool), M, E,
            inertia_max_iterations=1, inertia_tolerance=1e-30,
        )


def test_electron_gradient_drives_exact_generalized_ohm_drift():
    R, Z, BR, BZ = _grid()
    state = _state(R.shape, pressure=29.0)
    state['electron_pressure'] = 1.0 + R
    result = scientific_operator(R, Z, BR, BZ, np.full_like(R, 30.0), np.full_like(R, 30.0), state, np.ones_like(R, dtype=bool), M, E, include_toroidal_inertia=False, maximum_inertial_mach=10.0)
    assert np.max(np.abs(result['ion_toroidal_velocity'][:, 1:])) > 0.0
    assert result['generalized_ohm_error'] < 1e-12
    assert np.max(np.abs(result['momentum_residual_R'])) < 1e-12


def test_mask_excludes_axis_and_vacuum_cells():
    R, Z, BR, BZ = _grid()
    mask = np.zeros_like(R, dtype=bool)
    result = scientific_operator(R, Z, BR, BZ, np.full_like(R, 20.0), np.full_like(R, 20.0), _state(R.shape), mask, M, E)
    assert not np.any(result['hall_active_mask'])
    np.testing.assert_allclose(result['J_phi'], 0.0)


def test_source_hypot_preserves_finite_subnormal_and_large_results():
    result = _source_hypot(np.array([1.0e-308, 1.0e308]), np.array([1.0e-308, 1.0e308]))
    assert result[0] != 0.0
    assert np.isfinite(result[0]) and np.isfinite(result[1])
    np.testing.assert_array_equal(result, np.array([1.414213562373095e-308, 1.4142135623730951e308]))


def test_reviewed_relation_example():
    from scirel.closures.reduced_hall_drift import close_reduced_hall_drift
    import numpy as np

    m_i = 1.67262192595e-27
    q_i = 1.602176634e-19
    r = np.linspace(0.0, 0.4, 9)
    z = np.linspace(-0.5, 0.5, 11)
    R, Z = np.meshgrid(r, z)
    B_R = np.zeros_like(R)
    B_Z = np.full_like(R, 2.0)
    n_i = np.full_like(R, 1.0e18)
    state = {
        "ion_density": n_i,
        "electron_pressure": np.full_like(R, 3.0),
        "electrostatic_potential": 3.0 * R - 4.0 * Z,
        "ion_p_parallel": np.full_like(R, 29.0),
        "ion_p_perpendicular": np.full_like(R, 31.0),
        "electron_p_parallel": 2.0 + Z,
        "electron_p_perpendicular": 1.0 + R,
    }
    result = close_reduced_hall_drift(
        R, Z, B_R, B_Z, np.full_like(R, 30.0), np.full_like(R, 30.0),
        state, np.ones_like(R, dtype=bool), m_i, q_i,
        include_toroidal_inertia=False, maximum_inertial_mach=10.0,
    )
    charge_density = q_i * 1.0e18
    expected_velocity = (3.0 - 1.0 / charge_density) / 2.0
    np.testing.assert_allclose(result["J_phi"], 0.0, atol=1e-12)
    np.testing.assert_allclose(result["ion_toroidal_velocity"][:, 1:], expected_velocity, rtol=1e-12)
    np.testing.assert_allclose(result["electron_pressure_force_R"][:, 1:], 1.0, atol=1e-12)
    np.testing.assert_allclose(result["electron_pressure_force_R"][:, 0], 0.0, atol=1e-12)
    np.testing.assert_allclose(result["electron_pressure_force_Z"], 1.0, atol=1e-12)
    np.testing.assert_allclose(result["electric_field_R"], -3.0, atol=1e-12)
    np.testing.assert_allclose(result["electric_field_Z"], 4.0, atol=1e-12)
    np.testing.assert_allclose(result["hall_electric_field_R"][:, 1:], -1.0 / (q_i * 1.0e18), rtol=1e-12)
    np.testing.assert_allclose(result["ohm_residual_R"][:, 1:], 0.0, atol=1e-12)
    assert not np.any(result["hall_active_mask"][:, 0])


def test_review_gate_rejects_nonfinite_species_and_nonboolean_inertia_control():
    import pytest

    R, Z, BR, BZ = _grid()
    base = dict(
        r_grid=R, z_grid=Z, b_r=BR, b_z=BZ,
        p_parallel=np.full_like(R, 20.0), p_perpendicular=np.full_like(R, 20.0),
        closure_state=_state(R.shape), plasma_mask=np.ones_like(R, dtype=bool),
        ion_mass_kg=M, ion_charge_c=E,
    )
    with pytest.raises(ValueError, match="ion_mass_kg"):
        scientific_operator(**{**base, "ion_mass_kg": np.nan})
    with pytest.raises(ValueError, match="ion_charge_c"):
        scientific_operator(**{**base, "ion_charge_c": np.nan})
    with pytest.raises(ValueError, match="include_toroidal_inertia"):
        scientific_operator(**{**base, "include_toroidal_inertia": 1})
