"""Measured coefficient and eigenvalue diagnostics for the EM fluid spectrum."""

import numpy as np
from scirel.kinetic.fluid_spectrum import assemble_fluid_em, derive_fluid_case, solve_fluid_em


def assert_diag(d):
    assert d["harmonics"].shape == (1, 7)
    np.testing.assert_array_equal(d["harmonics"], np.arange(1, 8).reshape(1, -1))
    assert d["sum_residue_over_pole"].shape == (1, 7)
    assert d["sum_residue_over_pole_squared"].shape == (1, 7)
    np.testing.assert_array_equal(d["model_target"], np.zeros((1, 1), complex))


def test_assemble_exposes_only_measured_inverse_moments():
    state = derive_fluid_case("em", 2)
    out = assemble_fluid_em(state, 0.83 * state["wn"].item(), 8, 0)
    assert "cn_raw" not in out["poles"]
    assert "moment_normalization" not in out["poles"]
    assert_diag(out["poles"]["inverse_moment_diagnostics"])


def test_single_and_multi_solve_share_measured_diagnostics_and_eigenvalue_name():
    state = derive_fluid_case("em", 2)
    one = solve_fluid_em(2, 8, 0, [0.83 * state["wn"].item()])
    many = solve_fluid_em(2, 8, 0, np.array([0.37, 0.83, 1.43]) * state["wn"].item())
    for result in (one, many):
        assert_diag(result["inverse_moment_diagnostics"])
        assert "cn_raw" not in result and "moment_normalization" not in result
        assert "eigenvector_values" not in result["eigen_diagnostics"]
        assert "componentwise_backward_error" not in result["eigen_diagnostics"]
        assert "physical_state_scaled_backward_error" not in result["eigen_diagnostics"]
        assert "physical_gate_tolerance" not in result["eigen_diagnostics"]
        assert result["eigen_diagnostics"]["eigenpair_residuals_computed"].item() == 0
        assert result["eigen_diagnostics"]["eigenvalues"].shape == (40, 1)
    np.testing.assert_array_equal(
        one["inverse_moment_diagnostics"]["sum_residue_over_pole"],
        many["inverse_moment_diagnostics"]["sum_residue_over_pole"],
    )


def test_inverse_moment_diagnostics_follow_the_live_coefficient_table(monkeypatch):
    import scirel.kinetic.fluid_spectrum as module

    original = module.get_gamma_lpole_coefficients
    baseline = assemble_fluid_em(derive_fluid_case("em", 2), 1.0e11, 8, 0)["poles"][
        "inverse_moment_diagnostics"
    ]

    def perturbed(*, max_harmonic):
        tables = original(max_harmonic=max_harmonic)
        tables = {
            key: (value.copy() if isinstance(value, np.ndarray) else value)
            for key, value in tables.items()
        }
        tables["residues"] = {key: value.copy() for key, value in tables["residues"].items()}
        tables["residues"][4][0] += 1e-7 * (1 + 2j)
        return tables

    monkeypatch.setattr(module, "get_gamma_lpole_coefficients", perturbed)
    changed = assemble_fluid_em(derive_fluid_case("em", 2), 1.0e11, 8, 0)["poles"][
        "inverse_moment_diagnostics"
    ]
    pole = original(max_harmonic=7)["poles"][4][0]
    expected_delta = 1e-7 * (1 + 2j) / pole
    np.testing.assert_allclose(
        changed["sum_residue_over_pole"][0, 3] - baseline["sum_residue_over_pole"][0, 3],
        expected_delta,
    )
