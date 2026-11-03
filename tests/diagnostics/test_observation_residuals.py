from scirel.diagnostics.observation_residuals import reduce_observation_residuals


def test_flux_first_residual():
    result = reduce_observation_residuals(
        predicted={'flux_loops': [3.0], 'thomson': {'p_perp': [5.0]}},
        observations={'flux_loops': {'values': [1.0], 'sigma': [2.0]}, 'thomson': {'p_perp': {'values': [3.0], 'sigma': [1.0]}}},
    )
    assert result['residual_vector'].tolist() == [1.0, 2.0]
    assert result['chi2'] == 5.0


def test_reviewed_relation_example():
    from scirel.diagnostics.observation_residuals import reduce_observation_residuals
    import numpy as np

    predicted = {"flux_loops": [3.0], "thomson": {"p_perp": [5.0]}}
    observations = {
        "flux_loops": {"values": [1.0], "sigma": [2.0]},
        "thomson": {"p_perp": {"values": [3.0], "sigma": [1.0]}},
    }
    result = reduce_observation_residuals(predicted=predicted, observations=observations)
    np.testing.assert_allclose(result["residual_vector"], [1.0, 2.0])
    assert result["chi2"] == 5.0

    observations["flux_loops"]["sigma"] = [4.0]
    scaled = reduce_observation_residuals(predicted=predicted, observations=observations)
    np.testing.assert_allclose(scaled["residual_vector"], [0.5, 2.0])
    assert scaled["chi2"] == 4.25


def test_review_gate_rejects_missing_matching_prediction_as_a_contract_error():
    import pytest

    with pytest.raises(ValueError, match="usable signal"):
        reduce_observation_residuals(
            predicted={},
            observations={"thomson": {"p_perp": {"values": [1.0], "sigma": [1.0]}}},
        )


def test_review_gate_rejects_invalid_residual_channel_domains():
    import numpy as np
    import pytest

    base_observation = {"flux_loops": {"values": [1.0, 2.0], "sigma": [1.0, 1.0]}}
    with pytest.raises(ValueError, match="exact same shape"):
        reduce_observation_residuals(
            predicted={"flux_loops": [1.0]}, observations=base_observation
        )
    with pytest.raises(ValueError, match="sigma must be positive"):
        reduce_observation_residuals(
            predicted={"flux_loops": [1.0, 2.0]},
            observations={"flux_loops": {"values": [1.0, 2.0], "sigma": [1.0, 0.0]}},
        )
    with pytest.raises(ValueError, match="must be finite"):
        reduce_observation_residuals(
            predicted={"flux_loops": [np.nan, 2.0]}, observations=base_observation
        )
