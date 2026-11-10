import pytest
import numpy as np
from scirel.mirror.frank_egedal_radial_envelope import evaluate_frank_egedal_radial_envelope


def test_rejects_invalid_explicit_reference_state():
    with pytest.raises(ValueError, match="finite radial profile"):
        evaluate_frank_egedal_radial_envelope(np.zeros((2, 2)), psi_axis=np.nan)


def test_rejects_legacy_mapping_call():
    with pytest.raises(TypeError):
        evaluate_frank_egedal_radial_envelope(np.zeros((2, 2)), {"psi_axis": 0.0})


def test_reviewed_relation_example():
    import numpy as np
    from scirel.mirror.frank_egedal_radial_envelope import evaluate_frank_egedal_radial_envelope

    psi = np.array([[-1.0, 0.0, 0.5], [1.0, 1.5, 2.0]])
    result = evaluate_frank_egedal_radial_envelope(psi, psi_axis=0.0, psi_edge=1.0, alpha=2.0)
    expected = np.array([[1.0, 1.0, 0.25], [0.0, 0.0, 0.0]])
    assert np.allclose(result, expected)
    assert result.shape == psi.shape

    linear = evaluate_frank_egedal_radial_envelope(psi, psi_axis=0.0, psi_edge=1.0, alpha=1.0)
    assert np.allclose(linear, [[1.0, 1.0, 0.5], [0.0, 0.0, 0.0]])
    assert result[0, 2] < linear[0, 2]  # alpha 改变必须影响区间内部，而不改变截断端点。

    # The admitted contract explicitly supports reverse flux orientation.
    np.testing.assert_allclose(
        evaluate_frank_egedal_radial_envelope(
            [[0.0, 0.5, 1.0]], psi_axis=1.0, psi_edge=0.0, alpha=1.0
        ),
        [[0.0, 0.5, 1.0]],
    )
    try:
        evaluate_frank_egedal_radial_envelope([[1.0, 1.0]], psi_axis=1.0, psi_edge=1.0)
    except ValueError as exc:
        assert "finite radial profile" in str(exc)
    else:
        raise AssertionError("退化磁通区间必须失败关闭")
