"""Bounded replay against SHA-pinned saved KN1DPy matrix implementations.

The saved bundle is in re-review; these checks are historical comparisons, not
qualified L1 provenance or expert approval. They run only when the saved root
is available explicitly through SCIREL_KN1DPY_REVIEW_ROOT.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import (
    assemble_atomic_hydrogen_collision_matrices,
    assemble_molecular_hydrogen_collision_matrices,
)


SOURCES = [
    (
        "原子氢碰撞矩阵组装",
        "80fcd63681d255fbe6a2a0fc2e400d63143c9809099d1181bb30ef3266a956fe",
        assemble_atomic_hydrogen_collision_matrices,
    ),
    (
        "分子氢碰撞矩阵组装",
        "34358f11e3ee91fa6768c8cf89d22eb1a2edbe2707f9e58d0b91472bf1b50d06",
        assemble_molecular_hydrogen_collision_matrices,
    ),
]
CASES = [
    dict(vr=np.array([0.5, 1.0]), vx=np.array([-1.0, 1.0]),
         Vr2pidVr=np.array([1.7671458676442586, 3.141592653589793]),
         dVx=np.array([2.0, 2.0]), Tnorm=1.0, mu=1.0),
    dict(vr=np.array([0.4, 0.8, 1.5]), vx=np.array([-2.0, -1.0, 1.0, 2.0]),
         Vr2pidVr=np.array([1.1309733552923258, 3.0237829290801748, 6.597344572538567]),
         dVx=np.array([1.0, 1.5, 1.5, 1.0]), Tnorm=5.0, mu=2.0),
]


def _saved_function(package, expected_sha):
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set")
    source = Path(root) / "operators" / package / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected_sha
    spec = importlib.util.spec_from_file_location("kn1dpy_matrix_replay", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.scientific_operator


@pytest.mark.parametrize("package,expected_sha,assemble", SOURCES)
@pytest.mark.parametrize("case", CASES)
def test_saved_matrix_assembly_is_reproduced(package, expected_sha, assemble, case):
    saved = _saved_function(package, expected_sha)(**case)
    current = assemble(**case)
    assert current.keys() == saved.keys()
    for key in saved:
        np.testing.assert_allclose(current[key], saved[key], rtol=1e-12, atol=0.0)


@pytest.mark.parametrize("package,expected_sha,assemble", SOURCES)
def test_saved_reverse_radial_axis_is_rejected_here(package, expected_sha, assemble):
    saved_function = _saved_function(package, expected_sha)
    case = dict(CASES[0], vr=np.array([1.0, 0.5]))
    assert np.isfinite(saved_function(**case)["SIG_CX"]).all()
    with pytest.raises(ValueError, match="velocity-space carrier"):
        assemble(**case)


@pytest.mark.parametrize("package,expected_sha,assemble", SOURCES)
def test_saved_underflowed_normalization_is_rejected_here(package, expected_sha, assemble):
    saved_function = _saved_function(package, expected_sha)
    case = dict(CASES[0], Tnorm=np.nextafter(0.0, 1.0))
    assert saved_function(**case)["Vth2"][0] == 0.0
    with pytest.raises(ValueError, match="thermal normalization"):
        assemble(**case)
