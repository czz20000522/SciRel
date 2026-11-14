"""Picard grid errors use the declared exceptions before indexing inputs."""

import numpy as np
import pytest

from scirel.equilibrium import solve_free_boundary_anisotropic_picard
from scirel.equilibrium.isotropic_picard_step import pressure_flux_picard_step


def _free_boundary_inputs():
    r_grid, z_grid = np.meshgrid([0.2, 0.4, 0.6], [-0.1, 0.0, 0.1])

    def closure(state):
        pressure = np.full_like(state["psi"], 2.0)
        return {
            "p_parallel": pressure,
            "p_perp": pressure.copy(),
            "density": None,
            "electron_temperature": None,
        }

    return {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "psi_vac": r_grid**2 / 2,
        "br_vac": np.zeros_like(r_grid),
        "bz_vac": np.ones_like(r_grid),
        "g_psi": np.zeros((r_grid.size, r_grid.size)),
        "params": {},
        "pressure_closure": closure,
        "tol": 1e-12,
        "maxiter": 1,
        "relax": 0.0,
    }


@pytest.mark.parametrize("shape", [(1, 2), (2, 1), (1, 1), (0, 2), (2, 0), (0, 0), (0, 1), (1, 0)])
def test_isotropic_rejects_too_small_grid_before_indexing(shape):
    r_grid, z_grid = np.meshgrid(np.arange(shape[1], dtype=float), np.arange(shape[0], dtype=float))
    with pytest.raises(ValueError, match="uniformly spaced tensor-product grids"):
        pressure_flux_picard_step(
            r_grid,
            z_grid,
            np.zeros(shape),
            np.zeros(shape),
            np.eye(r_grid.size),
            np.zeros(r_grid.size),
            1.0,
            None,
            0.0,
        )


@pytest.mark.parametrize("missing", [("r_grid",), ("z_grid",), ("r_grid", "z_grid")])
@pytest.mark.parametrize("keyword_call", [False, True], ids=["mapping", "keywords"])
def test_free_boundary_requires_grid_keys_before_indexing(missing, keyword_call):
    values = _free_boundary_inputs()
    for name in missing:
        del values[name]
    with pytest.raises(ValueError, match=f"{missing[0]} is required by composition.yaml"):
        if keyword_call:
            solve_free_boundary_anisotropic_picard(**values)
        else:
            solve_free_boundary_anisotropic_picard(values)


@pytest.mark.parametrize("shape", [(2, 2), (1, 3), (3, 1), (0, 3), (3, 0), (0, 0)])
def test_free_boundary_grid_validation_still_precedes_other_required_ports(shape):
    values = _free_boundary_inputs()
    values["r_grid"], values["z_grid"] = np.meshgrid(
        np.arange(shape[1], dtype=float), np.arange(shape[0], dtype=float)
    )
    del values["pressure_closure"]
    with pytest.raises(ValueError, match="equal-shape 2-D grids with at least 3 points per axis"):
        solve_free_boundary_anisotropic_picard(values)


@pytest.mark.parametrize(
    "missing",
    [
        "psi_vac",
        "br_vac",
        "bz_vac",
        "g_psi",
        "params",
        "tol",
        "maxiter",
        "relax",
        "pressure_closure",
    ],
)
def test_free_boundary_other_required_ports_keep_value_error(missing):
    values = _free_boundary_inputs()
    del values[missing]
    with pytest.raises(ValueError, match=missing):
        solve_free_boundary_anisotropic_picard(values)


@pytest.mark.parametrize("exception", [IndexError, KeyError])
def test_free_boundary_callback_programming_errors_propagate(exception):
    values = _free_boundary_inputs()

    def broken_closure(_state):
        raise exception("closure programming error")

    values["pressure_closure"] = broken_closure
    with pytest.raises(exception, match="closure programming error"):
        solve_free_boundary_anisotropic_picard(values)
