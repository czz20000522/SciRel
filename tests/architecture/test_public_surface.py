import importlib
import json
from pathlib import Path
from types import ModuleType

import numpy as np

import scirel

CATALOG_ROOT = Path(__file__).resolve().parents[2] / "catalog" / "examples"

from scirel.kinetic.plasma_dispersion import evaluate_plasma_dispersion
from scirel.kinetic.bessel_gamma import evaluate_bessel_gamma
from scirel.kinetic.kinetic_dispersion_sum_n import evaluate_kinetic_dispersion_sum
from scirel.kinetic.species_equilibrium_scales import derive_species_equilibrium_scales
from scirel.kinetic.thermal_speed_scale import compute_thermal_speed_m_s
from scirel.kinetic.generation_density_reduction import reduce_generation_density
from scirel.kinetic.incoming_boundary_flux_normalization import normalize_incoming_neutral_boundary
from scirel.kinetic.spatial_source_shape_normalization import normalize_spatial_source_shape
from scirel.field.poloidal_field_magnitude import compute_poloidal_field_magnitude
from scirel.field.rectangular_coil_filaments import discretize_rectangular_coil
from scirel.field.circular_filament_green import circular_filament_green_response
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux
from scirel.equilibrium.isotropic_pressure_flux import solve_isotropic_pressure_flux
from scirel.collisions.relativistic_maxwellian_bessel import (
    BesselBackendEvaluationError,
    InvalidBesselArgumentError,
)
from scirel.dielectric.cold_plasma_tensor import (
    ColdPlasmaOverflowError,
    ColdPlasmaResonanceError,
)


def _documented_public_bindings() -> list[dict[str, str | None]]:
    """Every Python binding declared by the formal asset contracts."""
    bindings: list[dict[str, str | None]] = []
    for path in sorted(CATALOG_ROOT.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        api = document["public_api"]["python"]
        bindings.append(
            {
                "document": path.name,
                "module": api["module"],
                "symbol": api["symbol"],
                "canonical_module": api.get("canonical_module"),
                "canonical_symbol": api.get("canonical_symbol"),
            }
        )
    assert bindings, "catalog/examples must declare the public surface"
    return bindings


def test_all_documented_public_callables_are_importable_and_callable():
    bindings = _documented_public_bindings()
    documented_domains = set()
    for binding in bindings:
        document = str(binding["document"])
        implementation = importlib.import_module(str(binding["module"]))
        symbol = str(binding["symbol"])
        assert callable(getattr(implementation, symbol)), (
            f"{document}: {binding['module']}.{symbol} is not callable"
        )
        documented_domains.add(str(binding["module"]).split(".")[1])
        canonical_module = binding["canonical_module"]
        if canonical_module is not None:
            facade = importlib.import_module(str(canonical_module))
            canonical_symbol = str(binding["canonical_symbol"])
            assert callable(getattr(facade, canonical_symbol)), (
                f"{document}: {canonical_module}.{canonical_symbol} is not callable"
            )
    # Domain discovery must expose every documented domain; a domain that the
    # root namespace cannot resolve is a public-surface failure.
    for domain in sorted(documented_domains):
        assert domain in scirel.__all__
        assert isinstance(getattr(scirel, domain), ModuleType)
    # The two rejection classes are classes rather than callables, so they are
    # asserted as the ValueError subclasses the relation promises to raise.
    assert issubclass(InvalidBesselArgumentError, ValueError)
    assert issubclass(BesselBackendEvaluationError, ValueError)
    assert issubclass(ColdPlasmaResonanceError, ValueError)
    assert issubclass(ColdPlasmaOverflowError, ValueError)


def test_algebra_grid_exports_keep_domain_callables():
    from scirel import geometry, physics
    from scirel.geometry.face_to_cell import face_to_cell
    from scirel.physics import coulomb_logs, dilution

    assert geometry.face_to_cell is face_to_cell
    assert "face_to_cell" in geometry.__all__
    expected = {
        "calculate_stored_thermal_energy": physics.calculate_stored_thermal_energy,
        "calculate_main_ion_dilution_factor": dilution.calculate_main_ion_dilution_factor,
        "calculate_log_lambda_ee": coulomb_logs.calculate_log_lambda_ee,
        "calculate_log_lambda_ei": coulomb_logs.calculate_log_lambda_ei,
        "calculate_log_lambda_ii": coulomb_logs.calculate_log_lambda_ii,
    }
    assert set(physics.__all__) == set(expected)
    assert all(getattr(physics, name) is function for name, function in expected.items())


def test_root_namespace_supports_normal_python_imports():
    namespace = {}
    exec("from scirel import *", namespace)
    from types import ModuleType

    assert all(isinstance(namespace[name], ModuleType) for name in scirel.__all__)
    assert "poloidal_field_from_flux" not in namespace


def test_plasma_dispersion_is_exported_from_the_kinetic_domain():
    assert scirel.kinetic.evaluate_plasma_dispersion is evaluate_plasma_dispersion
    assert "evaluate_plasma_dispersion" in scirel.kinetic.__all__


def test_bessel_gamma_is_exported_from_the_kinetic_domain():
    assert scirel.kinetic.evaluate_bessel_gamma is evaluate_bessel_gamma
    assert "evaluate_bessel_gamma" in scirel.kinetic.__all__


def test_kinetic_dispersion_sum_is_exported_from_the_kinetic_domain():
    assert scirel.kinetic.evaluate_kinetic_dispersion_sum is evaluate_kinetic_dispersion_sum
    assert "evaluate_kinetic_dispersion_sum" in scirel.kinetic.__all__


def test_species_equilibrium_scales_is_exported_from_the_kinetic_domain():
    assert scirel.kinetic.derive_species_equilibrium_scales is derive_species_equilibrium_scales
    assert "derive_species_equilibrium_scales" in scirel.kinetic.__all__


def test_neutral_scale_and_density_are_exported_from_the_kinetic_domain():
    for name, function in (
        ("compute_thermal_speed_m_s", compute_thermal_speed_m_s),
        ("reduce_generation_density", reduce_generation_density),
    ):
        assert getattr(scirel.kinetic, name) is function
        assert name in scirel.kinetic.__all__


def test_neutral_normalizations_are_exported_from_the_kinetic_domain():
    for name, function in (
        ("normalize_incoming_neutral_boundary", normalize_incoming_neutral_boundary),
        ("normalize_spatial_source_shape", normalize_spatial_source_shape),
    ):
        assert getattr(scirel.kinetic, name) is function
        assert name in scirel.kinetic.__all__


def test_poloidal_field_and_magnitude_smoke():
    r, z = np.meshgrid(np.linspace(0.0, 0.4, 5), np.linspace(-0.2, 0.2, 5))
    field = poloidal_field_from_flux(r, z, 0.5 * r**2)
    assert field["B"].shape == r.shape
    magnitude = compute_poloidal_field_magnitude(field["B_R"], field["B_Z"])
    np.testing.assert_allclose(magnitude["B"], field["B"])


def test_poloidal_field_magnitude_handles_large_finite_components():
    result = compute_poloidal_field_magnitude([[1.0e308]], [[1.0e308]])
    assert np.isfinite(result["B"]).all()
    np.testing.assert_allclose(result["B"], [[np.sqrt(2.0) * 1.0e308]])


def test_simple_geometry_and_green_smoke():
    coil = discretize_rectangular_coil(0.3, 0.0, 2, 2, 0.02, 0.02)
    assert coil.shape == (4, 2)
    weighted_coil = np.column_stack((coil, np.ones(coil.shape[0])))
    response = circular_filament_green_response(weighted_coil, coil + np.array([0.0, 0.03]))
    assert response["gpsi"].shape == (4,)


def test_pressure_flux_picard_zero_green_smoke():
    r, z = np.meshgrid(np.linspace(0.1, 0.4, 5), np.linspace(-0.2, 0.2, 5))
    result = solve_isotropic_pressure_flux(
        {
            "r_grid": r,
            "z_grid": z,
            "psi_vac": 0.5 * r**2,
            "g_psi": np.zeros((r.size, r.size)),
            "pressure_of_radius": lambda radius: np.maximum(
                0.4 - np.asarray(radius, dtype=float), 0.0
            ),
            "tol": 1.0e-12,
            "maxiter": 2,
            "relax": 0.0,
        }
    )
    assert result["converged"] and result["psi"].shape == r.shape
    assert result["closure_residual"] <= 1.0e-12
