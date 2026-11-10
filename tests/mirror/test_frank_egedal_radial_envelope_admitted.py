import numpy as np
import pytest
from scirel.mirror.frank_egedal_radial_envelope import (
    evaluate_frank_egedal_radial_envelope as envelope,
)


def test_closed_form_and_input_ownership():
    x = np.array([[-2.0, 0.0, 0.25, 0.5, 0.75, 1.0, 3.0]])
    saved = x.copy()
    out = envelope(x, psi_axis=0.0, psi_edge=1.0, alpha=2.0)
    np.testing.assert_array_equal(out, [[1.0, 1.0, 0.5625, 0.25, 0.0625, 0.0, 0.0]])
    np.testing.assert_array_equal(x, saved)
    assert not np.shares_memory(x, out)


@pytest.mark.parametrize("scale,offset", [(4.0, 8.0), (-4.0, 8.0), (1e-12, 0.0)])
def test_affine_flux_relabelling_preserves_envelope(scale, offset):
    x = np.array([[-1.0, 0.0, 0.25, 0.5, 1.0, 2.0]])
    actual = envelope(scale * x + offset, psi_axis=offset, psi_edge=scale + offset, alpha=1.0)
    np.testing.assert_allclose(actual, [[1.0, 1.0, 0.75, 0.5, 0.0, 0.0]])


def test_zero_exponent_and_default_references():
    np.testing.assert_array_equal(
        envelope([[-1.0, 0.0, 1.0, 2.0]], alpha=0.0), [[1.0, 1.0, 1.0, 1.0]]
    )
    np.testing.assert_array_equal(envelope([[2.0, 3.0, 4.0]]), [[1.0, 0.5, 0.0]])


@pytest.mark.parametrize(
    "grid,kwargs",
    [
        ([], {}),
        ([[0.0, np.nan]], {}),
        ([[2.0, 2.0]], {}),
        ([[0.0, 1.0]], {"alpha": -1.0}),
        ([[0.0, 1.0]], {"alpha": np.inf}),
        ([[0.0, 1.0]], {"psi_axis": -1e308, "psi_edge": 1e308}),
        ([[0.0, 1.0]], {"psi_axis": 0.0, "psi_edge": 1e-31}),
    ],
)
def test_explicit_invalid_domain_is_rejected(grid, kwargs):
    with pytest.raises(ValueError):
        envelope(grid, **kwargs)
