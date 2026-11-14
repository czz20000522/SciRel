"""Distinguish invalid inputs from overflow produced by a theta step."""

import numpy as np
import pytest

from scirel.fvm import CellVariable, theta_step


@pytest.mark.parametrize("policy", ("warn", "ignore", "raise"))
@pytest.mark.parametrize("theta", (0.5, 1.0))
@pytest.mark.parametrize("part", ("implicit-matrix", "right-hand-side"))
def test_finite_step_overflow_raises_the_computation_error(policy, theta, part):
    variable = CellVariable([0.0, 0.0], [0.0, 1.0, 2.0])
    inputs = {"d_new": [4.0, 4.0, 4.0]} if part == "implicit-matrix" else {"source_new": [4.0, 4.0]}
    with np.errstate(over=policy, invalid=policy):
        with pytest.raises(FloatingPointError):
            theta_step(variable, variable, 1e308, theta=theta, **inputs)
    np.testing.assert_array_equal(variable.value, [0.0, 0.0])


@pytest.mark.parametrize("policy", ("warn", "ignore", "raise"))
def test_explicit_step_keeps_its_existing_overflow_classification(policy):
    variable = CellVariable([0.0, 0.0], [0.0, 1.0, 2.0])
    with np.errstate(over=policy, invalid=policy):
        with pytest.raises(FloatingPointError):
            theta_step(variable, variable, 1e308, theta=0.0, source_old=[4.0, 4.0])


@pytest.mark.parametrize("part", ("d_new", "source_new"))
def test_nonfinite_input_is_still_an_input_error(part):
    variable = CellVariable([0.0, 0.0], [0.0, 1.0, 2.0])
    values = [np.inf] * (3 if part == "d_new" else 2)
    with pytest.raises(ValueError):
        theta_step(variable, variable, 1.0, **{part: values})
