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
    np.testing.assert_array_equal(result["elastic_frequency_m_inv"], (channels[0] + channels[1]) + channels[2])


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
