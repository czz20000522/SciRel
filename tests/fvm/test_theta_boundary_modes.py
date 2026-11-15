"""Theta validates its documented modes even when convection is absent."""

import numpy as np
import pytest

from scirel.fvm import CellVariable, theta_step


def _convection_inputs(presence):
    return {name: np.zeros(3) for name in presence}


@pytest.mark.parametrize("mode", ["dirichlet_mode", "neumann_mode"])
@pytest.mark.parametrize("invalid", ["wrong-mode", "", "GHOST"])
@pytest.mark.parametrize("theta", [0.0, 0.5, 1.0])
@pytest.mark.parametrize("presence", [(), ("v_old",), ("v_new",), ("v_old", "v_new")])
def test_invalid_mode_rejected_consistently_before_either_operator(mode, invalid, theta, presence):
    var = CellVariable([0.25, -0.5], [0.0, 0.25, 1.0])
    with pytest.raises(ValueError, match="invalid convection boundary mode"):
        theta_step(var, var, 0.1, theta=theta, **{mode: invalid}, **_convection_inputs(presence))
    np.testing.assert_array_equal(var.value, [0.25, -0.5])


@pytest.mark.parametrize("dirichlet", ["ghost", "direct", "semi-implicit"])
@pytest.mark.parametrize("neumann", ["ghost", "semi-implicit"])
@pytest.mark.parametrize("convection", [False, True])
def test_all_documented_modes_keep_the_same_diffusion_only_equation(dirichlet, neumann, convection):
    var = CellVariable(
        [0.0, 0.0],
        [0.0, 1.0, 2.0],
        left_face_constraint=1.0,
        right_face_constraint=1.0,
        left_face_grad_constraint=None,
        right_face_grad_constraint=None,
    )
    kwargs = _convection_inputs(("v_old", "v_new")) if convection else {}
    result = theta_step(
        var,
        var,
        1.0,
        d_new=np.ones(3),
        dirichlet_mode=dirichlet,
        neumann_mode=neumann,
        **kwargs,
    )
    # [[4,-1],[-1,4]] u=[2,2], independently of absent/zero convection.
    np.testing.assert_allclose(result.value, [2.0 / 3.0] * 2, rtol=2e-14, atol=2e-15)


@pytest.mark.parametrize("presence", [(), ("v_old",), ("v_new",), ("v_old", "v_new")])
def test_direct_is_not_a_neumann_mode_even_when_it_is_a_dirichlet_mode(presence):
    var = CellVariable([0.0, 0.0], [0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="invalid convection boundary mode"):
        theta_step(
            var,
            var,
            0.1,
            dirichlet_mode="direct",
            neumann_mode="direct",
            **_convection_inputs(presence),
        )
