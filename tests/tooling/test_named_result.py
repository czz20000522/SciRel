"""The named result keeps mapping behaviour and adds attribute access."""

import numpy as np
import pytest

from scirel._result import Result
from scirel.field import compute_poloidal_field_magnitude
from scirel.kinetic import evaluate_plasma_dispersion


def test_result_is_a_mapping_with_attributes():
    result = Result(a=1)
    assert isinstance(result, dict)
    assert result.a == result["a"] == 1
    assert "a" in dir(result)
    with pytest.raises(AttributeError):
        result.missing


@pytest.mark.parametrize(
    "call, field",
    [
        (lambda: compute_poloidal_field_magnitude([[3.0]], [[4.0]]), "B"),
        (lambda: evaluate_plasma_dispersion(0.5 + 0.1j), "Z"),
    ],
)
def test_converted_functions_return_the_same_values_by_key_and_attribute(call, field):
    result = call()
    assert isinstance(result, Result)
    np.testing.assert_array_equal(getattr(result, field), result[field])
