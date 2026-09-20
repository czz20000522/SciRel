"""Shared fixtures for the U1 review unit.

The candidate package is loaded from the review unit's own ``src`` directory, so
the tests never import the frozen SciRel tree.  The retained read-only source
checkout is loaded by file path only, for the comparison tests, and those tests
skip loudly rather than passing silently when the checkout is unreachable.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pytest

UNIT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_SRC = UNIT_ROOT / "src"

_RETAINED_OPERATOR = "轴对称平衡到求解网格材料支撑映射"
_L1_CANDIDATES = (
    os.environ.get("SCIREL_L1_AORSA3D"),
    r"D:\Users\26569\Desktop\归档_项目\codefusion\最小闭环压测环境\aorsa3d",
    str(UNIT_ROOT / "build" / "l1" / "aorsa3d"),
)


def _retained_root():
    for raw in _L1_CANDIDATES:
        if not raw:
            continue
        candidate = Path(raw)
        if (candidate / "operators" / _RETAINED_OPERATOR).is_dir():
            return candidate
    return None


@pytest.fixture(scope="session")
def candidate():
    """Import the source candidate, or the installed wheel during release checks."""
    installed_runtime = os.environ.get("SCIREL_INSTALLED_RUNTIME") == "1"
    if not installed_runtime:
        sys.path.insert(0, str(CANDIDATE_SRC))
    import scirel
    from scirel.geometry import (  # noqa: F401
        classify_material_support,
        map_axisymmetric_equilibrium_to_cartesian_grid,
        solve_axisymmetric_equilibrium_grid_mapping,
    )
    from scirel.geometry import axisymmetric_grid_mapping, material_support

    module_root = Path(scirel.__file__).resolve()
    if installed_runtime:
        assert module_root.is_relative_to(Path(sys.prefix).resolve()), (
            "release tests must import the installed wheel"
        )
    else:
        assert module_root.is_relative_to(CANDIDATE_SRC.resolve()), (
            "the candidate package must not resolve to the frozen SciRel tree"
        )
    yield {
        "mapping": map_axisymmetric_equilibrium_to_cartesian_grid,
        "classification": classify_material_support,
        "graph": solve_axisymmetric_equilibrium_grid_mapping,
        "mapping_module": axisymmetric_grid_mapping,
        "classification_module": material_support,
    }
    if not installed_runtime:
        sys.path.remove(str(CANDIDATE_SRC))


@pytest.fixture(scope="session")
def retained():
    """Load the read-only retained operator by file path, or skip."""
    root = _retained_root()
    if root is None:
        pytest.skip("read-only L1 aorsa3d checkout not found; set SCIREL_L1_AORSA3D")
    path = root / "operators" / _RETAINED_OPERATOR / "scientific_operator.py"
    spec = importlib.util.spec_from_file_location("u1_retained_grid_mapping", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def equilibrium():
    """Build a synthetic axisymmetric equilibrium map.

    The map is deliberately non-separable: the poloidal flux carries an axial
    modulation and a reproducible perturbation, so a reconstruction that
    collapsed to a one-dimensional profile or that dropped one interpolation
    stage would not reproduce it.
    """

    def build(*, r_start=0.05, side="less_than", separatrix=0.4, r_size=21, z_size=21):
        r_axis = np.linspace(r_start, 1.0, r_size)
        z_axis = np.linspace(-0.5, 0.5, z_size)
        rr, zz = np.meshgrid(r_axis, z_axis, indexing="ij")
        rng = np.random.default_rng(20260920)
        return {
            "r_m": r_axis,
            "z_m": z_axis,
            "psi_wb_per_rad": 0.9 * rr
            + 0.1 * np.sin(2.0 * np.pi * zz)
            + 0.02 * rng.normal(size=rr.shape),
            "br_t": 0.3 * rr - 0.1 * zz**2,
            "bz_t": 1.0 - 0.4 * rr**2 + 0.05 * zz,
            "separatrix_flux_wb_per_rad": separatrix,
            "closed_flux_side": side,
        }

    return build


@pytest.fixture
def axes():
    """The standard solver grid and a matching all-false PEC mask."""

    def build(*, x=( -0.5, 0.5, 9), y=(-0.5, 0.5, 9), z=(-0.4, 0.4, 7)):
        x_axis = np.linspace(*x)
        y_axis = np.linspace(*y)
        z_axis = np.linspace(*z)
        pec = np.zeros((x_axis.size, y_axis.size, z_axis.size), dtype=bool)
        return x_axis, y_axis, z_axis, pec

    return build


def cylindrical_coordinates(x_axis, y_axis, z_axis):
    """Independent construction of the grid's radius and axial coordinate."""
    xx, yy, zz = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    return np.hypot(xx, yy), zz


@pytest.fixture
def cylindrical():
    """Expose the independent cylindrical-coordinate construction."""
    return cylindrical_coordinates
