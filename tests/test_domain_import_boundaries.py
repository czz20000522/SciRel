"""Regression checks for dependency-light scientific domain namespaces."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _run(source: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-c", source],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_heavy_domain_namespaces_do_not_import_numeric_backends() -> None:
    result = _run(
        """
import sys
import scirel.collisions
import scirel.configurations
import scirel.electromagnetism
assert "numpy" not in sys.modules
assert "scipy" not in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_all_domain_namespaces_are_dependency_light_until_an_export_is_used() -> None:
    result = _run(
        """
import sys
import scirel.diagnostics
import scirel.dielectric
import scirel.fvm
import scirel.fusion
import scirel.inference
import scirel.io
import scirel.neoclassical
import scirel.physics
import scirel.plasma
import scirel.source
assert "numpy" not in sys.modules
assert "scipy" not in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_geometry_sampling_core_export_does_not_import_scipy() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.geometry import locs_to_vals1D

assert "scipy" not in sys.modules
X, Y = np.meshgrid(np.array([0.0, 2.0]), np.array([0.0, 2.0]))
Q = np.array([[10, 20], [30, 40]])
assert locs_to_vals1D(X, Y, Q, [(1.0, 1.0)]) == [10]
assert "scipy" not in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_geometry_basis_core_export_does_not_import_scipy_special() -> None:
    result = _run(
        """
import sys
from scirel.geometry import build_basis

assert "scipy" not in sys.modules
try:
    build_basis("j0")
except NotImplementedError:
    pass
else:
    raise AssertionError("unimplemented special basis unexpectedly became available")
assert "scipy" not in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_geometry_complex_interpolation_defers_scipy_until_called() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.geometry import interpolate_complex_rectilinear_field

assert "scipy" not in sys.modules
axes = {"x_m": [0.0, 1.0], "y_m": [0.0, 1.0], "z_m": [0.0, 1.0]}
values = np.zeros((2, 2, 2), dtype=complex)
output = interpolate_complex_rectilinear_field(axes, values, np.array([[0.5, 0.5, 0.5]]))
assert output["valid_mask"].tolist() == [True]
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_geometry_arclength_export_defers_fieldline_scipy_backend() -> None:
    result = _run(
        """
import sys
from scirel.geometry import d_ds_arclength

assert "scipy" not in sys.modules
values = d_ds_arclength([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]], [0.0, 1.0, 4.0])
assert values.tolist() == [0.0, 2.0, 4.0]
assert "scipy" not in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_fluid_wavevector_export_defers_lapack_until_solve() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.kinetic import solve_fluid_wavevector_eigenproblem

assert "scipy" not in sys.modules
output = solve_fluid_wavevector_eigenproblem(matrix=np.array([[1.0 + 1.0j]]), kn=1.0)
assert output["returned_count"] == 1
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_pdrf_state_and_matrix_paths_defer_linalg_until_spectrum_solve() -> None:
    result = _run(
        """
import sys
from scirel.kinetic import (
    initialize_plasma_state,
    assemble_spectral_matrix,
    solve_temporal_spectrum,
)

assert "scipy" not in sys.modules
state = initialize_plasma_state()
assert "scipy" not in sys.modules
matrix = assemble_spectral_matrix(state, 0.1, 0.2)
assert "scipy" not in sys.modules
try:
    solve_temporal_spectrum(matrix["M"], matrix["A"], oldmethod=3)
except ValueError as error:
    assert str(error) == "oldmethod must be 1 or 2"
else:
    raise AssertionError("invalid PDRF spectrum method unexpectedly succeeded")
assert "scipy" not in sys.modules
output = solve_temporal_spectrum(matrix["M"], matrix["A"])
assert output["w1"].shape == (14,)
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_plasma_dispersion_defers_scipy_until_valid_call() -> None:
    result = _run(
        """
import sys
from scirel.kinetic import evaluate_plasma_dispersion
from scirel.kinetic.plasma_dispersion import evaluate_plasma_dispersion as direct

assert evaluate_plasma_dispersion is direct
assert "scipy" not in sys.modules
try:
    evaluate_plasma_dispersion([])
except ValueError as error:
    assert str(error) == "z must contain finite numeric values"
else:
    raise AssertionError("empty plasma-dispersion input unexpectedly succeeded")
assert "scipy" not in sys.modules
result = evaluate_plasma_dispersion(0j)
assert result["w"] == 1.0
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_scalar_mesh_interpolation_defers_scipy_until_valid_call() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.kinetic import interpolate_scalar_across_mesh
from scirel.kinetic.cross_mesh_scalar_interpolation import (
    interpolate_scalar_across_mesh as direct,
)

assert interpolate_scalar_across_mesh is direct
assert "scipy" not in sys.modules
try:
    interpolate_scalar_across_mesh([1.0], [0.0, 1.0], [0.5])
except ValueError as error:
    assert str(error) == "Number of elements in fa and Xa do not agree!"
else:
    raise AssertionError("invalid scalar-mesh input unexpectedly succeeded")
assert "scipy" not in sys.modules
output = interpolate_scalar_across_mesh(
    np.array([1.0, 3.0]), np.array([0.0, 1.0]), np.array([-1.0, 0.25, 2.0])
)
assert output.tolist() == [0.0, 1.5, 0.0]
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_generalized_dispersion_defers_backends_until_valid_call() -> None:
    result = _run(
        """
import sys
import scirel.kinetic.generalized_dispersion as generalized

assert "scipy" not in sys.modules
generalized.evaluate_gpdf_small_k(0.3)
assert "scipy" not in sys.modules
try:
    generalized.evaluate_generalized_dispersion([], 0)
except ValueError as error:
    assert str(error) == "z must be finite nonempty numeric values"
else:
    raise AssertionError("invalid generalized-dispersion input unexpectedly succeeded")
assert "scipy" not in sys.modules
generalized.evaluate_generalized_dispersion(1j, 0)
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_loss_cone_spectrum_defers_scipy_until_valid_call() -> None:
    result = _run(
        """
import sys
from scirel.kinetic import solve_loss_cone_spectrum
from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum as direct

assert solve_loss_cone_spectrum is direct
assert "scipy" not in sys.modules
try:
    solve_loss_cone_spectrum(0.0, 1)
except ValueError as error:
    assert str(error) == "xi_tp must be inside the open interval (0, 1)"
else:
    raise AssertionError("invalid loss-cone endpoint unexpectedly succeeded")
assert "scipy" not in sys.modules
result = solve_loss_cone_spectrum(0.6, 1, grid_points=16)
assert result["eigenfunctions"].shape == (16, 1)
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_bessel_gamma_defers_scipy_until_valid_call() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.kinetic import evaluate_bessel_gamma
from scirel.kinetic.bessel_gamma import evaluate_bessel_gamma as direct

assert evaluate_bessel_gamma is direct
assert "scipy" not in sys.modules
try:
    evaluate_bessel_gamma([], [])
except ValueError as error:
    assert str(error) == "n must contain finite numeric values"
else:
    raise AssertionError("invalid Bessel-Gamma input unexpectedly succeeded")
assert "scipy" not in sys.modules
result = evaluate_bessel_gamma(np.array([0]), np.array([0.0]))
assert result["Gamma_n"].tolist() == [1.0 + 0.0j]
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kinetic_spatial_source_shape_defers_scipy_until_valid_call() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.kinetic import normalize_spatial_source_shape
from scirel.kinetic.spatial_source_shape_normalization import (
    normalize_spatial_source_shape as direct,
)

assert normalize_spatial_source_shape is direct
assert "scipy" not in sys.modules
try:
    normalize_spatial_source_shape([0.0, 0.0], [0.0, 1.0])
except ValueError as error:
    assert str(error) == "source must have a positive spatial integral"
else:
    raise AssertionError("zero source profile unexpectedly succeeded")
assert "scipy" not in sys.modules
result = normalize_spatial_source_shape(np.array([1.0, 2.0]), np.array([0.0, 1.0]))
assert result["integral_source"] == 1.5
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_geometry_flux_surface_average_defers_scipy_until_called() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.geometry import compute_flux_surface_inverse_field_average

assert "scipy" not in sys.modules
r = np.linspace(0.0, 1.0, 4)
z = np.linspace(-1.0, 1.0, 4)
r_grid, z_grid = np.meshgrid(r, z)
output = compute_flux_surface_inverse_field_average(
    r_grid,
    z_grid,
    np.ones_like(r_grid),
    np.array([[0.0, 0.0], [1.0, 0.0]]),
)
assert output["dl_B"] > 0.0
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_electromagnetism_greens_defers_scipy_until_valid_numerical_call() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.electromagnetism.greens import compute_greens

assert "scipy" not in sys.modules
empty = compute_greens(np.empty((0, 3)), np.array([[0.3, 0.2]]))
assert all(value.shape == (1,) for value in empty)
assert "scipy" not in sys.modules
zero_weight = compute_greens(np.array([[1.0, 0.0, 0.0]]), np.array([[0.3, 0.2]]))
assert all(value.tolist() == [0.0] for value in zero_weight)
assert "scipy" not in sys.modules
try:
    compute_greens(np.array([[1.0, 0.0, 1.0]]), np.array([[1.0, 0.0]]))
except ValueError as error:
    assert str(error) == "target coincident with singular circular filament"
else:
    raise AssertionError("singular filament unexpectedly produced a value")
assert "scipy" not in sys.modules
compute_greens(np.array([[1.0, 0.0, 1.0]]), np.array([[0.3, 0.2]]))
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_electromagnetism_distributed_defers_scipy_until_numerical_call() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.electromagnetism.distributed import get_deltapsi

assert "scipy" not in sys.modules

class Dimension:
    size = 2

class Variable:
    dimensions = ("nzeqadim", "nreqadim")
    units = "A/cm^2"

    def __getitem__(self, key):
        return np.ones((2, 2))

class Dataset:
    dimensions = {"nzeqadim": Dimension(), "nreqadim": Dimension()}
    variables = {"curr_diamcurv_phi": Variable()}

get_deltapsi(Dataset(), np.array([[0.2, 1.0], [0.2, 1.0]]),
             np.array([[-0.5, -0.5], [0.5, 0.5]]))
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_closures_tabulated_pressure_defers_scipy_until_called() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.closures import evaluate_tabulated_pressure

assert "scipy" not in sys.modules
output = evaluate_tabulated_pressure(
    np.array([0.25, 0.75]),
    np.array([0.25, 0.75]),
    np.array([0.0, 0.5, 1.0]),
    np.array([1.0, 2.0, 3.0]),
)
assert output["is_isotropic"] is True
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_lazy_exports_preserve_identity_for_the_remaining_domains() -> None:
    result = _run(
        """
from scirel.dielectric import cold_plasma_dielectric_tensor
from scirel.dielectric.cold_plasma_tensor import cold_plasma_dielectric_tensor as direct_dielectric
from scirel.physics import calculate_log_lambda_ee
from scirel.physics.coulomb_logs import calculate_log_lambda_ee as direct_logs
from scirel.source import gaussian_profile
from scirel.source.gaussian import gaussian_profile as direct_gaussian
assert cold_plasma_dielectric_tensor is direct_dielectric
assert calculate_log_lambda_ee is direct_logs
assert gaussian_profile is direct_gaussian
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_collision_lazy_exports_keep_public_identity() -> None:
    result = _run(
        """
import scirel.collisions as package
from scirel.collisions import normalized_momentum
from scirel.collisions.momentum_scales import normalized_momentum as direct
assert package.normalized_momentum is direct
assert normalized_momentum is direct
assert all(name in dir(package) for name in package.__all__)
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_configuration_and_electromagnetism_lazy_exports_keep_public_identity() -> None:
    result = _run(
        """
from scirel.configurations import BRB
from scirel.configurations.brb import BRB as direct_brb
from scirel.electromagnetism import compute_greens
from scirel.electromagnetism.greens import compute_greens as direct_greens
assert BRB is direct_brb
assert compute_greens is direct_greens
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_field_child_modules_are_discoverable_and_lazy() -> None:
    result = _run(
        """
import sys
import scirel.field as field

assert {"coil_green_geometry", "complete_elliptic_integrals_approx"} <= set(dir(field))
assert not any(name.startswith("scirel.field.") for name in sys.modules)

child = field.coil_green_geometry
assert child.__name__ == "scirel.field.coil_green_geometry"
assert field.coil_green_geometry is child
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_domain_dirs_expose_only_public_contract_and_legal_lazy_names() -> None:
    result = _run(
        """
import importlib

import scirel


def check_namespace(package):
    public = set(package.__all__)
    lazy_modules = getattr(package, "_LAZY_MODULES", ())
    if hasattr(lazy_modules, "keys"):
        lazy_modules = set(lazy_modules)
    else:
        lazy_modules = set(lazy_modules)
    compatibility = set(getattr(package, "_COMPAT_EXPORTS", ()))
    names = set(dir(package))
    allowed = public | lazy_modules | compatibility
    assert public <= names, (package.__name__, sorted(public - names))
    assert compatibility <= names, (package.__name__, sorted(compatibility - names))
    assert names <= allowed, (package.__name__, sorted(names - allowed))
    assert not any(name.startswith("_") for name in names), package.__name__


for domain_name in scirel.__all__:
    check_namespace(importlib.import_module(f"scirel.{domain_name}"))

check_namespace(importlib.import_module("scirel.kinetic.dispersion"))
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr
