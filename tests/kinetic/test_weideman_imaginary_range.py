"""Documented numerical range of the pure-imaginary Weideman branch."""

import numpy as np
import pytest

from scirel.kinetic import evaluate_plasma_dispersion_weideman


@pytest.mark.parametrize("imaginary_part", [-26.0, 26.0])
def test_pure_imaginary_values_inside_documented_range_are_finite(imaginary_part):
    result = evaluate_plasma_dispersion_weideman(1j * imaginary_part)

    assert result["method"].item() == "erfc"
    assert result["all_purely_imaginary"] is True
    assert np.isfinite(result["w"]).all()
    assert np.isfinite(result["Z"]).all()


@pytest.mark.parametrize("imaginary_part", [-27.0, 27.0])
def test_pure_imaginary_values_outside_documented_range_fail_closed(imaginary_part):
    with np.errstate(invalid="ignore"), pytest.raises(ValueError, match="finite"):
        evaluate_plasma_dispersion_weideman(1j * imaginary_part)
