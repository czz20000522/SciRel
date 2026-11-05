"""D2 regressions that intentionally fail against frozen D1 source behavior.

These tests are written before the corrected namespace exists.  They encode the
finite-domain contract selected for the SciRel successor, not source fidelity.
"""

import numpy as np
import pytest

from scirel.electromagnetism import ArbitraryPoints, Device, compute_greens
from scirel.geometry import PointsMesh


def test_origin_theta_is_rejected_as_undefined():
    mesh = PointsMesh([0.0, 1.0], [0.0, 0.0])
    with pytest.raises(ValueError, match="origin|undefined|polar"):
        _ = mesh.theta


def test_coincident_filament_is_rejected_not_zeroed():
    with pytest.raises(ValueError, match="coincident|singular"):
        compute_greens(np.array([[1.0, 0.0, 1.0]]), np.array([[1.0, 0.0]]))


def test_zero_sum_weights_are_rejected():
    cset = ArbitraryPoints([[1.0, 0.0], [1.1, 0.0]], weights=[1.0, -1.0])
    with pytest.raises(ValueError, match="zero|sum|weight"):
        cset.total_current = 3.0


def test_parent_cache_tracks_in_place_child_geometry_edit():
    mesh = PointsMesh([2.0], [0.0])
    child = ArbitraryPoints([[1.0, 0.0]], mesh=mesh)
    device = Device(mesh=mesh)
    device.coil = child
    old = device.psi().copy()
    child.translate([0.2, 0.0])
    expected = child.psi().copy()
    assert not np.allclose(expected, old)
    np.testing.assert_allclose(device.psi(), expected)
