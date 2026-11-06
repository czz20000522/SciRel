import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from scirel._result import Result
from scirel.equilibrium.pressure_flux_state import (
    build_pressure_flux_state,
    build_pressure_flux_state as scientific_function,
)


def _case(**overrides):
    r_grid, z_grid = np.meshgrid(
        np.linspace(0.2, 0.8, 4),
        np.array([-0.1, 0.0, 0.1]),
    )
    values = {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "psi": r_grid.copy(),
        "pressure_of_radius": lambda radius: max(0.8 - radius, 0.0),
    }
    values.update(overrides)
    return values


def test_builds_pressure_flux_state_from_exact_midplane():
    result = scientific_function(**_case())

    assert isinstance(result, Result)
    assert list(result) == [
        "pressure_derivative",
        "zero_currents",
        "psi_edge",
        "pressure_of_psi",
        "limiter_index",
    ]
    for key in result:
        assert getattr(result, key) is result[key]
    assert type(result.pressure_of_psi) is dict
    assert result["limiter_index"] == 3
    np.testing.assert_allclose(result["psi_edge"], 0.8)
    np.testing.assert_allclose(result["pressure_derivative"], -1.0)
    np.testing.assert_allclose(result["zero_currents"], 0.0)
    assert result["pressure_derivative"].shape == (12,)
    assert result["pressure_of_psi"]["extrapolation"] == "zeros"


def test_masked_cells_have_no_pressure_driven_derivative():
    mask = np.zeros((3, 4), dtype=bool)
    mask[1, 2] = True
    result = scientific_function(**_case(plasma_mask=mask))

    assert result["pressure_derivative"][6] == 0.0
    np.testing.assert_allclose(
        np.delete(result["pressure_derivative"], 6),
        -1.0,
    )


def test_requires_exact_midplane_and_zero_pressure_boundary():
    values = _case(z_grid=np.full((3, 4), 0.1))
    with pytest.raises(
        ValueError, match="z_grid must contain exactly one complete zero midplane row"
    ):
        scientific_function(**values)

    values = _case(pressure_of_radius=lambda radius: 1.0)
    with pytest.raises(ValueError, match="pressure boundary"):
        scientific_function(**values)


def test_reviewed_relation_example():
    import numpy as np

    r_grid, z_grid = np.meshgrid(np.linspace(0.2, 0.8, 4), [-0.1, 0.0, 0.1])
    mask = np.zeros_like(r_grid, dtype=bool)
    mask[1, 2] = True
    result = build_pressure_flux_state(
        r_grid,
        z_grid,
        r_grid.copy(),
        lambda radius: max(0.8 - radius, 0.0),
        plasma_mask=mask,
    )
    expected = np.full(r_grid.size, -1.0)
    expected[1 * r_grid.shape[1] + 2] = 0.0
    np.testing.assert_allclose(result["pressure_derivative"], expected)
    np.testing.assert_allclose(result["zero_currents"], 0.0)
    assert result["limiter_index"] == 3
    assert result["psi_edge"] == 0.8
    assert result["pressure_derivative"].shape == (r_grid.size,)
    assert result["pressure_of_psi"]["extrapolation"] == "zeros"
    np.testing.assert_allclose(result["pressure_of_psi"]["psi_samples"], r_grid[1])


def test_pressure_spline_defers_scipy_until_valid_fit() -> None:
    root = Path(__file__).resolve().parents[2]
    source = """
import sys
import numpy as np
from scirel.equilibrium._pressure_current import fit_pressure_spline

assert "scipy" not in sys.modules
try:
    fit_pressure_spline([0.0, 1.0, 1.0, 2.0], [0.0, 1.0, 2.0, 3.0])
except FloatingPointError as error:
    assert str(error) == (
        "midplane flux must be finite and strictly increasing with at least four points"
    )
else:
    raise AssertionError("invalid pressure spline input unexpectedly succeeded")
assert "scipy" not in sys.modules

fitted = fit_pressure_spline(
    np.array([0.0, 1.0, 2.0, 3.0]),
    np.array([0.0, 1.0, 4.0, 9.0]),
)
assert "scipy" in sys.modules
np.testing.assert_allclose(fitted(1.5), 2.25)
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(root / "src")
    result = subprocess.run(
        [sys.executable, "-c", source],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
