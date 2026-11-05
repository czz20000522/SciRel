"""Composition wiring helpers stay private to their owning modules."""

import importlib

import pytest

COMPOSITION_MODULES = (
    "scirel.closures.mirror_quasineutral_closure",
    "scirel.diagnostics.equilibrium_synthesis_diagnostics",
    "scirel.equilibrium.axisymmetric_anisotropic_picard",
    "scirel.equilibrium.free_boundary_anisotropic_picard",
    "scirel.equilibrium.isotropic_pressure_flux",
    "scirel.equilibrium.kinetic_mirror_hall_equilibrium",
    "scirel.equilibrium.reduced_hall_anisotropic_picard",
    "scirel.field.multi_coil_vacuum_field",
    "scirel.geometry.axisymmetric_equilibrium_grid_support",
    "scirel.kinetic.frank_egedal_pressure_closure",
    "scirel.kinetic.grid_mirror_kinetic_closure",
)


@pytest.mark.parametrize("module_name", COMPOSITION_MODULES)
def test_composition_wiring_helper_is_private(module_name):
    module = importlib.import_module(module_name)

    assert callable(module._run_composition)
    assert not hasattr(module, "run_composition")
