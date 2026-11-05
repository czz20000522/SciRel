"""D2 corrections: independent properties, never relaxed D1 tolerances."""

import numpy as np
import pytest

from scirel.kinetic.spectral_evolution import (
    initialize_plasma_state,
    assemble_spectral_matrix,
    solve_temporal_spectrum,
    evaluate_spectral_dispersion,
)


def test_collision_is_dissipative_and_momentum_conserving():
    data = [[-1, 1, 4, 0, 0, 0, 0, 0, 0, 0], [1, 4, 4, 0, 0, 0, 0, 0, 0, 0]]
    state = initialize_plasma_state(data, cfg={"nuei": 0.2})
    result = assemble_spectral_matrix(state, 0, 0)
    block = result["M"][np.ix_([3, 7], [3, 7])].real
    np.testing.assert_allclose(block @ np.ones(2), 0, atol=1e-15)
    np.testing.assert_allclose(state["rhos0"] @ block, 0, atol=1e-15)
    assert np.linalg.eigvals(block).real.max() <= 1e-15
    assert np.array([1.0, -1.0]) @ (state["rhos0"] * (block @ [1.0, -1.0])) < 0


def test_reinitialization_replaces_all_species_and_zero_field_diagnostics():
    prior = initialize_plasma_state()
    state = initialize_plasma_state(
        [[0, 2, 3, 0, 0, 0, 0.2, 0.2, 0, 0]], prior=prior, cfg={"B0": 0}
    )
    assert state["s"] == 1
    assert state["qs"].shape == (1,)
    assert state["Q0"] == 0
    assert state["betasz"] is None and state["betasp"] is None
    np.testing.assert_array_equal(state["vA"], [0.0])
    np.testing.assert_array_equal(state["Deltas"], [0.0])


def test_gradient_denominator_linearization():
    state = initialize_plasma_state([[0, 2, 3, 0, 0, 0, 0.4, 0.6, 0.1, 0.2]])
    result = assemble_spectral_matrix(state, 0, 0)
    np.testing.assert_allclose(
        result["M"][[1, 2], 0], [0.6**2 * 0.1 / 3, 0.6**2 * 0.2 / 3], rtol=2e-15, atol=0
    )


@pytest.mark.parametrize("value", [0, -1, np.nan, np.inf])
def test_invalid_mass_and_density_fail_closed(value):
    for col in [1, 2]:
        data = np.array([[0.0, 1, 1, 0, 0, 0, 0, 0, 0, 0]])
        data[0, col] = value
        with pytest.raises(ValueError):
            initialize_plasma_state(data)


@pytest.mark.parametrize("speed", [1.0, 1.1])
def test_relativistic_boundary_rejected(speed):
    state = initialize_plasma_state([[0, 1, 1, speed, 0, 0, 0, 0, 0, 0]])
    with pytest.raises(ValueError, match="subluminal"):
        assemble_spectral_matrix(state, 0.1, 0, rel=1)


def test_vectors_do_not_change_spectrum_path_and_residuals():
    state = initialize_plasma_state()
    matrix = assemble_spectral_matrix(state, 0.2, 0.3, rel=1)
    values = solve_temporal_spectrum(matrix["M"], matrix["A"])
    vectors = solve_temporal_spectrum(matrix["M"], matrix["A"], vectors=True)
    np.testing.assert_array_equal(values["w1"], vectors["w1"])
    residual = matrix["M"] @ vectors["X1"] + 1j * (matrix["A"] @ vectors["X1"]) * vectors["w1"]
    assert np.max(np.abs(residual)) < 1e-12


def test_active_component_residual_mask_keeps_errors_fail_closed():
    from scirel.kinetic.spectral_evolution import _residuals

    M = np.array([[1.0e-14, 0.0], [1.0, 0.0]])
    A = np.array([[0.0, 0.0], [1.0, 0.0]])
    values = np.array([0.75, 0.0])
    vectors = np.eye(2)

    errors, worst = _residuals(M, A, values, vectors)
    np.testing.assert_allclose(errors[0], 0.25 / 1.75, rtol=1e-15, atol=0.0)
    np.testing.assert_allclose(worst, 0.25 / 1.75, rtol=1e-15, atol=0.0)

    nonfinite_vectors = np.array([[1.0, 0.0], [np.nan, 1.0]])
    with pytest.raises(ArithmeticError, match="nonfinite"):
        _residuals(M, A, values, nonfinite_vectors)


@pytest.mark.parametrize("method", [0, 1, 5, 99])
def test_single_point_selectors(method):
    result = evaluate_spectral_dispersion(method=method)
    assert result["ww1"].shape == (1, 14)
    assert result["method"] == method
    assert result["graphics"]["axes_count"] == 0


def test_si_arity_and_local_five_outputs_are_defined():
    result = evaluate_spectral_dispersion(unit="si", method=1, output_count=17)
    assert len(result) == 17
    assert np.size(result[4]) == 1
    matrix = assemble_spectral_matrix(initialize_plasma_state(), 0.1, 0)
    out = solve_temporal_spectrum(matrix["M"], matrix["A"], output_count=5)
    assert len(out) == 5 and out[4].shape == (14, 14)


def test_plot_one_and_high_species_without_index_failure(tmp_path):
    for s in [1, 17]:
        data = np.tile([0, 1, 1, 0, 0, 0, 0, 0, 0, 0], (s, 1))
        out = evaluate_spectral_dispersion(
            data, method=2, k_grid=[0, 0.1], plot_path=tmp_path / f"s{s}.png"
        )
        assert out["plot_png"] == b""
        assert out["graphics"]["axes_count"] == 2


def test_explicit_collision_categories_survive_graph_state():
    state = initialize_plasma_state(cfg={"collision_classes": ["heavy", "light"]})
    result = assemble_spectral_matrix(state, 0.1, 0)
    np.testing.assert_array_equal(result["state"]["collision_classes"], ["heavy", "light"])


def test_collision_flux_underflow_cannot_hide_asymmetry():
    rows = [[0, 1, 1e-300, 0, 0, 0, 0, 0, 0, 0]] * 2
    with pytest.raises(ValueError, match="numeric domain"):
        initialize_plasma_state(rows, cfg={"collision_rates": [[0, 1e-100], [2e-100, 0]]})


def test_legacy_collision_flux_underflow_fails_at_initialization():
    rows = [[0, 1e-100, 1e-100, 0, 0, 0, 0, 0, 0, 0]] * 2
    with pytest.raises(ValueError, match="numeric domain"):
        initialize_plasma_state(rows, cfg={"nuee": 1e-200})
