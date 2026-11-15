"""Representability of the pure-imaginary Weideman branch."""

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


@pytest.mark.parametrize("imaginary_part", [-27.0])
def test_pure_imaginary_values_outside_documented_range_fail_closed(imaginary_part):
    with np.errstate(invalid="ignore"), pytest.raises(ValueError, match="finite"):
        evaluate_plasma_dispersion_weideman(1j * imaginary_part)


@pytest.mark.parametrize("imaginary_part", [27.0, 40.0])
def test_positive_axis_is_not_limited_by_intermediate_exponential_overflow(imaginary_part):
    # The old +27 rejection assertion described exp(y*y)*erfc(y) overflow,
    # not an unrepresentable w or Z. Independent integral tests protect values.
    result = evaluate_plasma_dispersion_weideman(1j * imaginary_part)
    assert result["method"].item() == "erfc"
    assert result["all_purely_imaginary"] is True
    assert np.isfinite(result["w"]).all()
    assert np.isfinite(result["Z"]).all()
