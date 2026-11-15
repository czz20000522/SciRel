"""The complete existing neutral transport cluster has one public owner."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_EXPORTS = {
    "compute_thermal_speed_m_s",
    "reduce_generation_density",
    "normalize_incoming_neutral_boundary",
    "normalize_spatial_source_shape",
    "make_cylindrical_velocity_quadrature",
    "build_shifted_maxwellian_seed",
    "reduce_axisymmetric_neutral_moments",
    "create_adaptive_neutral_velocity_mesh",
    "interpolate_scalar_across_mesh",
    "interp_distribution_across_mesh",
    "assemble_neutral_upwind_transport_coefficients",
    "propagate_neutral_generation",
    "assemble_neutral_boltzmann_rhs",
    "evaluate_neutral_generation_stopping",
    "update_neutral_generation_accumulation",
    "evaluate_neutral_outer_seed_convergence",
    "evaluate_outer_convergence",
    "sum_elastic_frequency_channels",
    "assemble_neutral_total_collision_frequency",
    "reduce_atomic_scattered_sources",
    "reduce_molecular_scattered_sources",
    "aggregate_elastic_regeneration_source",
    "assemble_simple_charge_exchange_source",
    "contract_atomic_hydrogen_alpha_frequencies",
    "contract_molecular_hydrogen_alpha_frequencies",
    "reduce_terminal_molecular_flux_velocity",
    "reduce_terminal_molecular_pressure_temperature",
    "reduce_terminal_molecular_heat_flux",
    "reduce_terminal_molecular_energy_transfer",
    "reduce_qh2_total_conservation_diagnostic",
    "reduce_terminal_molecular_ion_state",
    "compensate_velocity_slice",
    "build_compensated_shifted_maxwellian",
}


def test_neutrals_domain_is_lazy_without_importing_kinetic():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-c",
            """
import sys
sys.path.insert(0, sys.argv[1])
import scirel
assert "neutrals" in scirel.__all__
assert "scirel.neutrals" not in sys.modules
from scirel import neutrals
assert set(neutrals.__all__) <= set(dir(neutrals))
assert not any(name.startswith("scirel.neutrals.") for name in sys.modules)
assert "scirel.kinetic" not in sys.modules
assert not any(name in sys.modules for name in ("numpy", "scipy", "matplotlib"))
""",
            str(ROOT / "src"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_complete_neutral_cluster_has_no_kinetic_reexport_or_old_modules():
    from scirel import kinetic, neutrals

    assert set(neutrals.__all__) == EXPECTED_EXPORTS
    assert EXPECTED_EXPORTS.isdisjoint(kinetic.__all__)
    modules = set()
    for symbol in sorted(EXPECTED_EXPORTS):
        function = getattr(neutrals, symbol)
        assert function.__module__.startswith("scirel.neutrals.")
        module = importlib.import_module(function.__module__)
        assert getattr(module, symbol) is function
        assert getattr(neutrals, module.__name__.rsplit(".", 1)[1]) is module
        assert not hasattr(kinetic, symbol)
        old_module = function.__module__.replace("scirel.neutrals.", "scirel.kinetic.", 1)
        with pytest.raises(ModuleNotFoundError) as caught:
            importlib.import_module(old_module)
        assert caught.value.name == old_module
        modules.add(module.__name__)
    assert len(modules) == 32
    for symbol in ("derive_species_equilibrium_scales", "evaluate_h_saha_equilibrium_population"):
        assert getattr(kinetic, symbol).__module__.startswith("scirel.kinetic.")
        assert not hasattr(neutrals, symbol)


def test_all_neutral_obligations_and_both_compensations_are_bound():
    documents = [
        json.loads(path.read_text())
        for path in (ROOT / "catalog/examples").glob("scirel.neutrals.*.json")
    ]
    assert len(documents) == 33
    assert {doc["public_api"]["python"]["symbol"] for doc in documents} == EXPECTED_EXPORTS
    compensation = []
    for doc in documents:
        api = doc["public_api"]["python"]
        assert api["canonical_module"] == "scirel.neutrals"
        assert api["module"].startswith("scirel.neutrals.")
        assert "neutrals" in doc["taxonomy"]
        assert not (
            ROOT
            / "catalog/examples"
            / (doc["asset_id"].replace("scirel.neutrals.", "scirel.kinetic.", 1) + ".json")
        ).exists()
        if api["module"] == "scirel.neutrals.moment_compensation":
            compensation.append(api["symbol"])
    assert set(compensation) == {
        "compensate_velocity_slice",
        "build_compensated_shifted_maxwellian",
    }
