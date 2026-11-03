"""Numerical failures become a status; programming errors stay visible."""

import numpy as np
import pytest

from scirel.equilibrium import equilibrium_state as module


def _call():
    radii = np.linspace(1.0, 5.0, 9)
    heights = np.linspace(-1.0, 1.0, 5)
    grid_r, grid_z = np.meshgrid(radii, heights)
    size = grid_r.size
    return module.compute_equilibrium(
        grid_r, grid_z, lambda radius: 5.0 - radius, grid_r * 1.0, np.zeros((size, size)), maxiter=1
    )


def test_programming_error_in_the_fit_is_not_reported_as_nonfinite(monkeypatch):
    def broken(*_):
        raise TypeError("a bug, not a numerical failure")

    monkeypatch.setattr(module, "fit_pressure_spline", broken)
    with pytest.raises(TypeError, match="a bug"):
        _call()


def test_numerical_failure_in_the_fit_is_still_reported_as_a_status(monkeypatch):
    def failing(*_):
        raise FloatingPointError("not finite")

    monkeypatch.setattr(module, "fit_pressure_spline", failing)
    assert _call().status == "nonfinite"
