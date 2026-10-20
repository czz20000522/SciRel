import numpy as np
import pytest

from scirel.field.ideal_conductor_boundary import correct_ideal_conductor_boundary_flux, correct_ideal_conductor_boundary_flux as scientific_operator


def _inputs():
    return {
        "uncorrected_field_flux": np.array([3.0, -1.0, 2.0]),
        "boundary_sample_matrix": np.array([[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]]),
        "green_boundary_to_boundary": np.array([[2.0, 0.0], [0.0, 4.0]]),
        # S @ G_BF equals G_BB, so the field correction is physically
        # consistent with the sampled boundary response.
        "green_boundary_to_field": np.array([[2.0, 0.0], [-1.0, 3.0], [1.0, 5.0]]),
    }


# 验证：满秩墙 Green 矩阵时，采样边界磁通应由墙电流严格抵消。
def test_cancels_boundary_flux_and_reports_rank():
    result = scientific_operator(**_inputs())
    assert np.allclose(result["residual"], 0.0)
    assert result["residual_norm"] == pytest.approx(0.0)
    assert result["effective_rank"] == 2
    assert np.allclose(result["corrected_field_flux"], np.array([0.0, 0.125, -0.125]))
    assert np.allclose(_inputs()["boundary_sample_matrix"] @ result["corrected_field_flux"], 0.0)


# 验证：相对奇异值截断必须改变有效秩，而非法 rcond 必须 fail closed。
def test_honors_relative_svd_cutoff_and_rejects_invalid_cutoff():
    data = _inputs()
    data["green_boundary_to_boundary"] = np.diag([2.0, 1.0e-6])
    result = scientific_operator(**data, rcond=1.0e-4)
    assert result["effective_rank"] == 1
    with pytest.raises(ValueError):
        scientific_operator(**_inputs(), rcond=-1.0)


def test_consistent_flux_rescaling_preserves_boundary_currents():
    data = _inputs()
    per_radian = scientific_operator(**data)
    full_flux = scientific_operator(
        uncorrected_field_flux=2 * np.pi * data["uncorrected_field_flux"],
        boundary_sample_matrix=data["boundary_sample_matrix"],
        green_boundary_to_boundary=2 * np.pi * data["green_boundary_to_boundary"],
        green_boundary_to_field=2 * np.pi * data["green_boundary_to_field"],
    )
    np.testing.assert_allclose(full_flux["boundary_currents"], per_radian["boundary_currents"])
    for name in ("corrected_field_flux", "boundary_flux_correction", "field_flux_correction", "residual"):
        np.testing.assert_allclose(full_flux[name], 2 * np.pi * per_radian[name])


def test_reviewed_relation_example():
    import numpy as np
    from scirel.field.ideal_conductor_boundary import correct_ideal_conductor_boundary_flux

    field_flux = np.array([3.0, -1.0, 2.0])
    sample = np.array([[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]])
    g_boundary = np.array([[2.0, 0.0], [0.0, 4.0]])
    g_field = np.array([[2.0, 0.0], [-1.0, 3.0], [1.0, 5.0]])
    assert np.allclose(sample @ g_field, g_boundary)
    result = correct_ideal_conductor_boundary_flux(
        field_flux, sample, g_boundary, g_field
    )
    np.testing.assert_allclose(result["residual"], 0.0)
    np.testing.assert_allclose(sample @ result["corrected_field_flux"], result["residual"])
    np.testing.assert_allclose(result["corrected_field_flux"], [0.0, 0.125, -0.125])
    assert result["effective_rank"] == 2
    assert result["residual_norm"] == 0.0
