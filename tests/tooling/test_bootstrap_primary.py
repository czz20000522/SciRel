"""Primary-paper coefficient anchors and independent pressure-differential assembly.

The fixture contains high-precision values from scalar paper expressions, using
polynomial Horner evaluation and 80/120-digit agreement. It never imports the
production formula to make its expected values. The six current cases instead
differentiate total pressure before applying the independent current relation.
These are bounded arithmetic checks, not NEO or experimental calibration.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from scirel.neoclassical import calculate_bootstrap_current, compute_bootstrap_coefficients


REFERENCE = json.loads(
    (
        Path(__file__).resolve().parents[1] / "fixtures/neoclassical/bootstrap_primary.json"
    ).read_text()
)


@pytest.mark.parametrize("method", ("redl", "sauter"))
def test_coefficients_follow_primary_paper_anchors(method):
    """Each fit must keep its own four coefficients, including corrected alpha."""
    inputs = np.asarray(REFERENCE["coefficient_inputs"], dtype=np.float64)
    expected = np.asarray(REFERENCE["coefficient_values"][method], dtype=np.float64)
    assert inputs.shape == expected.shape == (18, 4)
    result = compute_bootstrap_coefficients(*inputs.T, method=method)
    fields = REFERENCE["coefficient_fields"]
    assert list(result) == fields
    for index, field in enumerate(fields):
        observed = np.asarray(result[field])
        assert observed.shape == (18,) and np.all(np.isfinite(observed))
        target = expected[:, index]
        error = np.abs(observed - target) / np.maximum(1.0, np.abs(target))
        worst = int(np.argmax(error))
        assert np.all(error <= REFERENCE["acceptance_scaled"]), (
            f"{method} {field} must follow its primary-paper expression within the "
            f"fixed dimensionless arithmetic budget; input f,nue,Z,nui={inputs[worst]}, "
            f"observed={observed[worst]!r}, reference={target[worst]!r}, "
            f"scaled_error={error[worst]!r}"
        )


@pytest.mark.parametrize("case", REFERENCE["assembly"], ids=lambda case: case["name"])
def test_current_follows_pressure_differential_and_flux_convention(case):
    """Signed field, flux convention and explicit axis policy must stay distinct."""
    result = calculate_bootstrap_current(**case["inputs"])
    assert list(result) == ["j_parallel_bootstrap_face", "j_parallel_bootstrap"]
    for field, expected in (
        ("j_parallel_bootstrap_face", case["faces"]),
        ("j_parallel_bootstrap", case["cells"]),
    ):
        observed = np.asarray(result[field])
        target = np.asarray(expected, dtype=np.float64)
        assert observed.shape == target.shape and np.all(np.isfinite(observed))
        error = np.abs(observed - target) / np.maximum(1.0, np.abs(target))
        assert np.all(error <= REFERENCE["acceptance_scaled"]), (
            f"{case['name']} {field} must follow the independent total-pressure "
            "differential and stated total/per-radian flux convention; "
            f"maximum scaled error={np.max(error)!r}"
        )
    assert result.j_parallel_bootstrap_face[0] == 0.0, (
        "The declared rho=0 policy explicitly sets the first manufactured axis face to zero."
    )
