"""SHA-gated historical Omega replay from the saved KN1DPy bundle.

The saved bundle is pending re-review, so these comparisons are bounded
development evidence rather than qualified L1 provenance or expert approval.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import (
    assemble_atomic_hydrogen_omega_frequencies,
    assemble_molecular_hydrogen_omega_frequencies,
)


SOURCES = [
    (
        "原子氢弹性散射频率聚合",
        "5b80ea51cf51490208c5e39d71ca5a56c9a4610943a703e066cbbfa4ea6d9038",
        "assemble_atomic_hydrogen_omega_frequencies",
        assemble_atomic_hydrogen_omega_frequencies,
    ),
    (
        "分子氢弹性碰撞频率聚合",
        "13b001078958fa6fd8a819e65340a3a4e22fbfb6a3dbb58e4451db92e81f78d9",
        "assemble_molecular_hydrogen_omega_frequencies",
        assemble_molecular_hydrogen_omega_frequencies,
    ),
]


def _saved_function(package, expected_sha, symbol):
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = Path(root) / "operators" / package / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected_sha
    spec = importlib.util.spec_from_file_location("kn1dpy_omega_replay", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, symbol)


def _arguments(moment_scale):
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 0.0, 2.0])
    f = np.array([[[0.4, 0.5], [0.7, 0.8], [0.9, 1.1]],
                  [[0.3, 0.6], [0.8, 0.9], [1.2, 1.3]]])
    common = [
        f, np.array([10.0, 12.0]),
        np.full_like(f, 0.2), np.full_like(f, 0.3),
        -np.full((6, 6), 0.1), np.array([1.0, 2.0]),
        np.array([1.0, 1.0, 1.0]), vr, vx, 1000.0,
        np.array([100.0, 120.0]), np.array([300.0, 200.0]),
        f * moment_scale, vr[:, None] ** 2 - 2.0 * vx[None, :] ** 2,
    ]
    return common


@pytest.mark.parametrize("package,expected_sha,symbol,assemble", SOURCES)
@pytest.mark.parametrize("moment_scale", [-0.5, 0.0, 0.5])
def test_saved_omega_branches_are_reproduced(package, expected_sha, symbol, assemble, moment_scale):
    arguments = _arguments(moment_scale)
    saved = _saved_function(package, expected_sha, symbol)(*arguments)
    current = assemble(*arguments)
    assert current.keys() == saved.keys()
    for key in saved:
        np.testing.assert_array_equal(current[key], saved[key])


@pytest.mark.parametrize("package,expected_sha,symbol,assemble", SOURCES)
def test_zero_denominator_is_a_documented_repair(package, expected_sha, symbol, assemble):
    arguments = _arguments(0.0)
    saved_function = _saved_function(package, expected_sha, symbol)
    f, density = arguments[:2]
    radial_weights, axial_widths, vx, vth = arguments[5], arguments[6], arguments[8], arguments[9]
    arguments[10] = np.array([
        vth * np.sum(radial_weights * (f[:, :, k] @ (vx * axial_widths))) / density[k]
        for k in range(density.size)
    ])
    with np.errstate(divide="ignore", invalid="ignore"):
        legacy = saved_function(*arguments, **_channel_flags(symbol, "first"))
    first_key = "Omega_H_P" if "atomic" in symbol else "Omega_H2_P"
    assert not np.all(np.isfinite(legacy[first_key]))
    with pytest.raises(ValueError, match="zero velocity difference"):
        assemble(*arguments, **_channel_flags(symbol, "first"))

    arguments = _arguments(0.0)
    arguments[0] = np.zeros_like(arguments[0])
    with np.errstate(divide="ignore", invalid="ignore"):
        legacy = saved_function(*arguments, **_channel_flags(symbol, "self"))
    self_key = "Omega_H_H" if "atomic" in symbol else "Omega_H2_H2"
    assert not np.all(np.isfinite(legacy[self_key]))
    with pytest.raises(ValueError, match="zero perpendicular moment"):
        assemble(*arguments, **_channel_flags(symbol, "self"))


def _channel_flags(symbol, enabled):
    flags = ("H_P_EL", "H_H2_EL", "H_H_EL") if "atomic" in symbol else (
        "H2_P_EL", "H2_H_EL", "H2_H2_EL"
    )
    return {flag: enabled == label for flag, label in zip(flags, ("first", "second", "self"))}
