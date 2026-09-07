import unittest
import numpy as np

from scirel.geometry.flux_surface_profile import evaluate_flux_surface_profile


class FluxSurfaceProfileTest(unittest.TestCase):
    def test_sort_unique_and_endpoint_extension(self):
        result = evaluate_flux_surface_profile(psi_samples=[2.0, 0.0, 1.0, 1.0], values=[4.0, 0.0, 2.0, 3.0], target=[-1.0, 0.5, 3.0])
        np.testing.assert_allclose(result["values"], [0.0, 1.0, 4.0])
        np.testing.assert_allclose(result["psi"], [0.0, 1.0, 2.0])

    def test_rejects_nonfinite(self):
        with self.assertRaises(ValueError):
            evaluate_flux_surface_profile(psi_samples=[0.0, 1.0], values=[0.0, float("nan")], target=[0.5])


def test_reviewed_relation_example():
    from scirel.geometry.flux_surface_profile import evaluate_flux_surface_profile
    import numpy as np

    result = evaluate_flux_surface_profile(
        psi_samples=[2.0, 0.0, 1.0, 1.0],
        values=[4.0, 0.0, 2.0, 3.0],
        target=[-1.0, 0.5, 3.0],
        left=-7.0,
        right=9.0,
    )
    np.testing.assert_allclose(result["values"], [-7.0, 1.0, 9.0])
    np.testing.assert_allclose(result["psi"], [0.0, 1.0, 2.0])
    np.testing.assert_allclose(result["profile_values"], [0.0, 2.0, 4.0])
