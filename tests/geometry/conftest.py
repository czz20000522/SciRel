"""Fixtures for the geometry domain.

``equilibrium``, ``axes``, ``cylindrical_coordinates`` and ``cylindrical`` describe
the axisymmetric solver grid used by the geometry tests. They also remain
reachable from ``tests/cross_domain/axisymmetric_equilibrium_grid_support``
(and any future cross-domain consumer), so ``tests/conftest.py`` registers this
module as a root plugin. The plugin is the single definition site; the local
conftest discovery path reuses the same module.
"""

from __future__ import annotations

import numpy as np
import pytest


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

    def build(*, x=(-0.5, 0.5, 9), y=(-0.5, 0.5, 9), z=(-0.4, 0.4, 7)):
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
