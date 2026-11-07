"""Direct contracts for neutral elastic and total-loss frequency leaves."""

import numpy as np
import pytest

from scirel.kinetic import (
    assemble_neutral_total_collision_frequency,
    sum_elastic_frequency_channels,
)


def test_elastic_channels_preserve_order_and_zero_channel():
    channels = [np.array([1.0e16, 0.0]), np.array([-1.0e16, 2.0]), np.array([1.0, 3.0])]
    result = sum_elastic_frequency_channels(channels)
    np.testing.assert_array_equal(
        result["elastic_frequency_m_inv"], (channels[0] + channels[1]) + channels[2]
    )


def test_elastic_channels_reject_count_shape_and_nonfinite_total():
    with pytest.raises(ValueError, match="exactly three"):
        sum_elastic_frequency_channels([np.ones(2), np.ones(2)])
    with pytest.raises(ValueError, match="shape"):
        sum_elastic_frequency_channels([np.ones(2), np.ones(3), np.ones(2)])
    with pytest.raises(ValueError, match="finite"):
        sum_elastic_frequency_channels([np.array([1.0e308])] * 3)


@pytest.mark.parametrize("bad", [[True], ["1"], [1.0 + 0j]])
def test_elastic_channels_reject_implicit_real_conversion(bad):
    with pytest.raises(ValueError, match="frequency_profiles_m_inv"):
        sum_elastic_frequency_channels([bad, [1.0], [1.0]])


def test_total_loss_preserves_wall_and_cx_branches():
    result = assemble_neutral_total_collision_frequency(
        [1.0, 2.0], [-1.0, 1.0], [3.0, 4.0], [5.0, 6.0], [2.0, 0.0], np.ones((2, 2, 2))
    )
    np.testing.assert_array_equal(result[:, :, 0], [[10.0, 10.0], [11.0, 11.0]])
    np.testing.assert_array_equal(result[:, :, 1], [[11.0, 11.0], [11.0, 11.0]])
    disabled = assemble_neutral_total_collision_frequency(
        [1.0], [1.0], [3.0], [5.0], [2.0], ["not used"], charge_exchange_enabled=False
    )
    np.testing.assert_array_equal(disabled, [[[9.0]]])


def test_exact_zero_diameter_is_wall_off_sentinel_not_divergence():
    """Exact zero is the declared wall-off branch; near-zero keeps the D -> 0+ divergence."""
    vr = [1.0, 2.0]
    vx = [-1.0, 1.0]
    cx = np.ones((2, 2, 3))
    result = assemble_neutral_total_collision_frequency(
        vr, vx, np.zeros(3), np.zeros(3), [1.0, 0.0, 1.0], cx
    )
    # wall = 2 * u_r / D is applied only where D > 0; zero cells contribute no wall term.
    # The wall term broadcasts over vx: result[vr_i, vx_j, k] = 2*vr_i/D_k + 1.
    np.testing.assert_array_equal(result[:, :, 0], np.array([[3.0, 3.0], [5.0, 5.0]]))
    np.testing.assert_array_equal(result[:, :, 1], np.full((2, 2), 1.0))
    np.testing.assert_array_equal(result[:, :, 2], np.array([[3.0, 3.0], [5.0, 5.0]]))


def test_near_zero_diameter_keeps_formula_not_sentinel():
    """D -> 0+ grows without bound; only exact zero selects the wall-off branch."""
    tiny = np.finfo(float).tiny
    result = assemble_neutral_total_collision_frequency(
        [1.0], [1.0], [0.0], [0.0], [tiny], charge_exchange_enabled=False
    )
    np.testing.assert_allclose(result[0, 0, 0], 2.0 / tiny, rtol=2e-16)


def test_exact_zero_diameter_is_not_the_positive_limit():
    """The sentinel is a policy branch, not a numerical approximation of the limit."""
    exact = assemble_neutral_total_collision_frequency(
        [1.0], [1.0], [0.0], [0.0], [0.0], charge_exchange_enabled=False
    )
    assert exact[0, 0, 0] == 0.0
    assert np.isfinite(exact).all()


def test_total_loss_requires_enabled_cx_and_finite_result():
    with pytest.raises(ValueError, match="charge exchange"):
        assemble_neutral_total_collision_frequency([1.0], [1.0], [1.0], [1.0], [0.0])
    with pytest.raises(ValueError, match="finite"):
        assemble_neutral_total_collision_frequency(
            [1.0e308], [1.0], [0.0], [0.0], [1.0e-308], charge_exchange_enabled=False
        )


@pytest.mark.parametrize("bad", [[True], ["1"], [1.0 + 0j]])
def test_total_loss_rejects_implicit_real_conversion(bad):
    with pytest.raises(ValueError, match="vr"):
        assemble_neutral_total_collision_frequency(
            bad, [1.0], [1.0], [1.0], [1.0], charge_exchange_enabled=False
        )


def test_total_loss_requires_boolean_branch_selector():
    with pytest.raises(ValueError, match="charge_exchange_enabled"):
        assemble_neutral_total_collision_frequency(
            [1.0], [1.0], [1.0], [1.0], [1.0], charge_exchange_enabled=1
        )
