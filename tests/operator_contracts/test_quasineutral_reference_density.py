import numpy as np
import pytest

from scirel.closures.quasineutral_reference_density import compute_reference_electron_density, compute_reference_electron_density as scientific_operator


def test_reference_density_product_broadcasts_and_preserves_units():
    result = scientific_operator([1.0e18, 2.0e18], 2.0)
    np.testing.assert_allclose(result["electron_density_ref_m3"], [2.0e18, 4.0e18])


def test_zero_ion_density_is_valid():
    result = scientific_operator(0.0, 1.0)
    assert result["electron_density_ref_m3"].item() == 0.0


@pytest.mark.parametrize(
    "density, charge_state",
    [([-1.0], 1.0), ([np.inf], 1.0), ([1.0], 0.0), ([1.0], np.nan)],
)
def test_invalid_domain_fails_closed(density, charge_state):
    with pytest.raises((ValueError, FloatingPointError)):
        scientific_operator(density, charge_state)


def test_reviewed_relation_example():
    from scirel.closures.quasineutral_reference_density import compute_reference_electron_density
    import numpy as np

    result = compute_reference_electron_density(np.array([1.0e18, 2.0e18]), np.array([1.0, 3.0]))
    np.testing.assert_allclose(result["electron_density_ref_m3"], [1.0e18, 6.0e18])
    assert result["electron_density_ref_m3"].shape == (2,)
