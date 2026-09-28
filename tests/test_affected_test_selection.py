import json
from pathlib import Path
import runpy
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ROOT / "scripts" / "select_affected_tests.py"


def select(*paths):
    command = [sys.executable, str(SELECTOR), "--format", "json"]
    for path in paths:
        command.extend(("--changed-path", path))
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_operator_change_selects_only_its_contract_and_dependent_graphs():
    result = select("src/scirel/field/poloidal_field_magnitude.py")

    assert result["full_suite_required"] is False
    assert "tests/operator_contracts/test_poloidal_field_magnitude.py" in result["test_paths"]
    assert (
        "tests/graph_contracts/free_boundary_anisotropic_picard/"
        "test_graph_free_boundary_anisotropic_picard.py"
    ) in result["test_paths"]
    assert "tests/operator_contracts/test_dense_axisymmetric_green.py" not in result["test_paths"]


def test_anisotropic_feedback_change_selects_free_boundary_graph():
    result = select("src/scirel/equilibrium/anisotropic_picard_feedback.py")

    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_anisotropic_picard_feedback.py",
        "tests/graph_contracts/free_boundary_anisotropic_picard/test_graph_free_boundary_anisotropic_picard.py",
    } <= set(result["test_paths"])


def test_anisotropic_current_change_selects_free_boundary_graph():
    result = select("src/scirel/equilibrium/anisotropic_toroidal_current.py")

    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_anisotropic_toroidal_current.py",
        "tests/graph_contracts/free_boundary_anisotropic_picard/test_graph_free_boundary_anisotropic_picard.py",
    } <= set(result["test_paths"])


def test_force_balance_change_selects_both_picard_graphs_and_current_wrapper():
    result = select("src/scirel/equilibrium/anisotropic_force_balance.py")

    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_anisotropic_force_balance.py",
        "tests/operator_contracts/test_anisotropic_toroidal_current.py",
        "tests/graph_contracts/axisymmetric_anisotropic_picard/test_graph_axisymmetric_anisotropic_picard.py",
        "tests/graph_contracts/free_boundary_anisotropic_picard/test_graph_free_boundary_anisotropic_picard.py",
    } <= set(result["test_paths"])


def test_picard_residual_change_selects_free_boundary_graph():
    result = select("src/scirel/diagnostics/picard_flux_residual.py")

    assert result["full_suite_required"] is False
    assert "tests/operator_contracts/test_picard_flux_residual.py" in result["test_paths"]
    assert (
        "tests/graph_contracts/free_boundary_anisotropic_picard/"
        "test_graph_free_boundary_anisotropic_picard.py"
    ) in result["test_paths"]


def test_cylindrical_quadrature_change_selects_distribution_handoff():
    result = select("src/scirel/kinetic/cylindrical_velocity_quadrature.py")

    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_cylindrical_velocity_quadrature.py",
        "tests/operator_contracts/test_cross_mesh_distribution.py",
    } <= set(result["test_paths"])


def test_nested_task_graph_dependents_are_selected_transitively():
    result = select("src/scirel/closures/reduced_hall_drift.py")

    assert {
        "scirel.equilibrium.reduced_hall_anisotropic_picard."
        "solve_reduced_hall_anisotropic_picard",
        "scirel.equilibrium.kinetic_mirror_hall_equilibrium."
        "solve_kinetic_mirror_hall_equilibrium",
    } <= set(result["affected_assets"])
    assert (
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py"
        in result["test_paths"]
    )


def test_task_graph_change_does_not_select_unrelated_graphs():
    result = select("src/scirel/field/multi_coil_vacuum_field.py")

    assert result["test_paths"] == [
        "tests/graph_contracts/multi_coil_vacuum_field/"
        "test_graph_multi_coil_vacuum_field.py",
    ]


def test_package_export_change_checks_public_surface_and_asset_examples():
    result = select("src/scirel/field/__init__.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == [
        "tests/test_asset_documentation.py",
        "tests/test_public_surface.py",
    ]


def test_collision_package_export_change_checks_momentum_namespace_contract():
    result = select("src/scirel/collisions/__init__.py")

    assert result["full_suite_required"] is False
    assert "tests/operator_contracts/test_momentum_scales.py" in result["test_paths"]


def test_cross_section_change_selects_both_collision_matrix_dependents():
    result = select("src/scirel/collisions/hydrogen_h2_elastic_cross_section.py")

    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_atomic_hydrogen_collision_matrices.py",
        "tests/operator_contracts/test_molecular_hydrogen_collision_matrices.py",
    } <= set(result["test_paths"])


def test_atomic_cx_rate_change_selects_its_direct_tests():
    result = select("src/scirel/collisions/atomic_hydrogen_charge_exchange_rate.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.collisions.atomic_hydrogen_charge_exchange_rate.evaluate_atomic_hydrogen_charge_exchange_rate"
    ]
    assert {
        "tests/operator_contracts/test_atomic_hydrogen_charge_exchange_rate.py",
        "tests/operator_contracts/test_atomic_hydrogen_charge_exchange_rate_l1.py",
    } <= set(result["test_paths"])


def test_molecular_cx_rate_change_selects_its_direct_tests():
    result = select("src/scirel/collisions/hydrogen2_charge_exchange_rate.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.collisions.hydrogen2_charge_exchange_rate.evaluate_hydrogen2_charge_exchange_rate"
    ]
    assert {
        "tests/operator_contracts/test_hydrogen2_charge_exchange_rate.py",
        "tests/operator_contracts/test_hydrogen2_charge_exchange_rate_l1.py",
    } <= set(result["test_paths"])


def test_janev_ionization_rate_change_selects_its_direct_tests():
    result = select("src/scirel/collisions/janev_electron_impact_ionization_rate.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.collisions.janev_electron_impact_ionization_rate.evaluate_janev_electron_impact_ionization_rate"
    ]
    assert {
        "tests/operator_contracts/test_janev_electron_impact_ionization_rate.py",
        "tests/operator_contracts/test_janev_electron_impact_ionization_rate_l1.py",
    } <= set(result["test_paths"])


def test_atomic_h1s_recombination_change_selects_its_direct_tests():
    result = select("src/scirel/collisions/atomic_hydrogen_1s_radiative_recombination_rate.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.collisions.atomic_hydrogen_1s_radiative_recombination_rate.evaluate_atomic_hydrogen_1s_radiative_recombination_rate"
    ]
    assert {
        "tests/operator_contracts/test_atomic_hydrogen_1s_radiative_recombination_rate.py",
        "tests/operator_contracts/test_atomic_hydrogen_1s_radiative_recombination_rate_l1.py",
    } <= set(result["test_paths"])


def test_alpha_change_selects_omega_dependent_and_direct_replay():
    result = select("src/scirel/kinetic/atomic_alpha_contraction.py")

    assert result["full_suite_required"] is False
    assert "scirel.collisions.atomic_hydrogen_omega_frequencies.assemble_atomic_hydrogen_omega_frequencies" in result["affected_assets"]
    assert {
        "tests/operator_contracts/test_atomic_hydrogen_omega_frequencies.py",
        "tests/operator_contracts/test_omega_frequencies_l1.py",
    } <= set(result["test_paths"])


def test_terminal_flux_change_selects_its_two_direct_tests():
    result = select("src/scirel/kinetic/terminal_flux_velocity_reduction.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.kinetic.terminal_flux_velocity_reduction.reduce_terminal_molecular_flux_velocity"
    ]
    assert {
        "tests/operator_contracts/test_terminal_molecular_flux_velocity.py",
        "tests/operator_contracts/test_terminal_molecular_flux_velocity_l1.py",
    } <= set(result["test_paths"])


def test_terminal_pressure_change_selects_its_two_direct_tests():
    result = select("src/scirel/kinetic/terminal_pressure_temperature_reduction.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.kinetic.terminal_pressure_temperature_reduction.reduce_terminal_molecular_pressure_temperature"
    ]
    assert {
        "tests/operator_contracts/test_terminal_molecular_pressure_temperature.py",
        "tests/operator_contracts/test_terminal_molecular_pressure_temperature_l1.py",
    } <= set(result["test_paths"])


def test_terminal_heat_flux_change_selects_its_two_direct_tests():
    result = select("src/scirel/kinetic/terminal_heat_flux_reduction.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.kinetic.terminal_heat_flux_reduction.reduce_terminal_molecular_heat_flux"
    ]
    assert {
        "tests/operator_contracts/test_terminal_molecular_heat_flux.py",
        "tests/operator_contracts/test_terminal_molecular_heat_flux_l1.py",
    } <= set(result["test_paths"])


def test_terminal_energy_transfer_change_selects_its_two_direct_tests():
    result = select("src/scirel/kinetic/terminal_energy_transfer_reduction.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.kinetic.terminal_energy_transfer_reduction.reduce_terminal_molecular_energy_transfer"
    ]
    assert {
        "tests/operator_contracts/test_terminal_molecular_energy_transfer.py",
        "tests/operator_contracts/test_terminal_molecular_energy_transfer_l1.py",
    } <= set(result["test_paths"])


def test_terminal_ion_state_change_selects_its_two_direct_tests():
    result = select("src/scirel/kinetic/terminal_ion_state_reduction.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.kinetic.terminal_ion_state_reduction.reduce_terminal_molecular_ion_state"
    ]
    assert {
        "tests/operator_contracts/test_terminal_molecular_ion_state.py",
        "tests/operator_contracts/test_terminal_molecular_ion_state_l1.py",
    } <= set(result["test_paths"])


def test_terminal_conservation_change_selects_its_two_direct_tests():
    result = select("src/scirel/kinetic/terminal_conservation_diagnostic.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.kinetic.terminal_conservation_diagnostic.reduce_qh2_total_conservation_diagnostic"
    ]
    assert {
        "tests/operator_contracts/test_terminal_molecular_conservation.py",
        "tests/operator_contracts/test_terminal_molecular_conservation_l1.py",
    } <= set(result["test_paths"])


def test_mcp_adapter_change_selects_only_its_boundary_tests():
    result = select("src/scirel_adapter/mcp.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == []
    assert result["test_paths"] == ["tests/test_thin_mcp_adapter.py"]
    assert result["reasons"][0]["classification"] == "source_engineering_contract"


def test_codefusion_consumer_contract_change_selects_its_contract_test():
    result = select("docs/integration/codefusion-consumer-contract.md")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == []
    assert result["test_paths"] == ["tests/test_codefusion_consumer_contract.py"]
    assert result["reasons"][0]["classification"] == "engineering_contract"


def test_shared_composition_change_selects_every_task_graph():
    result = select("src/scirel/_composition.py")

    graph_assets = [
        asset for asset in result["affected_assets"] if ".solve_" in asset or ".synthesize_" in asset
    ]
    assert len(graph_assets) == 11
    assert "tests/test_library_composition.py" in result["test_paths"]
    assert "tests/test_incremental_admissions.py" in result["test_paths"]
    assert len(result["test_paths"]) == 13


def test_documentation_change_needs_no_scientific_tests():
    result = select("docs/architecture.md")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == []
    assert result["test_paths"] == []


def test_outbound_evaluation_manifest_change_selects_manifest_contract_test():
    result = select(
        "docs/evaluations/outbound-progressive-projects/manifests/"
        "2026-09-25-p3-reactivation-claude.json"
    )

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == []
    assert result["test_paths"] == ["tests/test_outbound_evaluation_manifests.py"]


def test_outbound_evaluation_manifest_verifier_selects_manifest_contract_test():
    result = select("scripts/verify_outbound_evaluation_manifests.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == []
    assert result["test_paths"] == ["tests/test_outbound_evaluation_manifests.py"]


def test_asset_schema_and_example_changes_select_contract_tests():
    result = select(
        "contracts/scientific-asset-document.schema.json",
        "catalog/examples/scirel.field.circular-filament-green.json",
    )

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_asset_documentation.py"]


def test_release_environment_helper_change_selects_only_its_contract_test():
    result = select("scripts/check_helpers.ps1")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_release_environment.py"]


def test_release_finalizer_selects_only_its_contract_test():
    result = select("scripts/finalize_release.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_release_finalization.py"]


def test_wire_fixture_builder_selects_only_wire_smoke_test():
    result = select("scripts/build_l1_wire_fixture.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_l1_wire_smoke.py"]


def test_user_acceptance_change_selects_current_tasks():
    result = select("examples/user_acceptance.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_user_acceptance.py"]


def test_scirel_solving_skill_change_selects_workflow_method_contract():
    result = select("skills/usage/scirel-solving/SKILL.md")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_scientific_request_workflow_docs.py"]
    assert result["reasons"][0]["classification"] == "engineering_contract"


def test_extraction_skill_bundle_tools_select_their_contract_test():
    result = select(
        "scripts/build_extraction_skill_bundle.py",
        "scripts/install_extraction_skill_bundle.py",
        "skills/extraction/tests/test_extraction_skill_bundle.py",
    )

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == []
    assert result["test_paths"] == [
        "skills/extraction/tests/test_extraction_skill_bundle.py"
    ]
    assert {
        reason["classification"] for reason in result["reasons"]
    } == {"external_tooling"}


def test_capability_progress_validator_is_outside_library_checks():
    result = select(
        "skills/extraction/scientific-computation-asset-extraction/scripts/"
        "validate_capability_progress.py",
        "skills/extraction/scientific-computation-asset-extraction/scripts/"
        "test_validate_capability_progress.py",
    )

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == []
    assert result["test_paths"] == []
    assert {
        reason["classification"] for reason in result["reasons"]
    } == {"external_tooling"}


def test_historical_admission_builder_selects_its_provenance_test():
    result = select(
        "scripts/build_admitted_distribution.py",
        "provenance/admitted-assets.json",
        "provenance/tests/test_admitted_distribution_builder.py",
    )

    assert result["full_suite_required"] is False
    assert result["test_paths"] == [
        "provenance/tests/test_admitted_distribution_builder.py"
    ]
    assert {reason["classification"] for reason in result["reasons"]} == {
        "external_tooling"
    }


def test_review_item_schema_selects_workflow_and_plugin_contracts():
    result = select("contracts/review-item-dev.schema.json")

    assert result["full_suite_required"] is False
    assert "tests/test_workflow_contracts.py" in result["test_paths"]
    assert "tests/plugin/test_codefusion_plugin_contract.py" in result["test_paths"]


def test_unknown_script_still_fails_closed_to_the_full_suite():
    result = select("scripts/unknown_maintenance_tool.py")

    assert result["full_suite_required"] is True
    assert result["test_paths"] == ["tests"]
    assert result["reasons"][0]["classification"] == "unclassified_change"


def test_https_runner_selects_only_listener_test():
    result = select("scripts/run_scirel_https.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/plugin/test_http_listener.py"]


def test_workflow_source_change_selects_workflow_boundary_without_full_suite():
    result = select("src/scirel_workflow/workflow.py")

    assert result["full_suite_required"] is False
    assert result["reasons"][0]["classification"] == "workflow_source_contract"
    assert set(result["test_paths"]) == {
        "tests/workflow/test_workflow.py",
        "tests/workflow/test_vertical_slice.py",
        "tests/workflow/test_l1_inventory.py",
        "tests/workflow/test_l1_bundle.py",
        "tests/workflow/test_standardization_submission.py",
        "tests/test_workflow_contracts.py",
    }


def test_plugin_contract_change_selects_plugin_and_vertical_boundary():
    result = select("src/scirel_plugin/contract.py")

    assert result["full_suite_required"] is False
    assert result["reasons"][0]["classification"] == "plugin_source_contract"
    assert set(result["test_paths"]) == {
        "tests/plugin/test_codefusion_plugin_contract.py",
        "tests/plugin/test_http_listener.py",
        "tests/workflow/test_vertical_slice.py",
    }


def test_workflow_contract_change_selects_all_workflow_boundaries():
    result = select(
        "contracts/release-manifest-dev.schema.json",
        "contracts/review-ui-extension-dev.schema.json",
        "contracts/workflow-state-dev.schema.json",
    )

    assert result["full_suite_required"] is False
    assert {
        reason["classification"] for reason in result["reasons"]
    } == {"workflow_contract"}
    assert set(result["test_paths"]) == {
        "tests/workflow/test_workflow.py",
        "tests/workflow/test_vertical_slice.py",
        "tests/workflow/test_l1_inventory.py",
        "tests/workflow/test_l1_bundle.py",
        "tests/workflow/test_standardization_submission.py",
        "tests/test_workflow_contracts.py",
        "tests/plugin/test_codefusion_plugin_contract.py",
        "tests/plugin/test_http_listener.py",
    }


def test_l1_fixture_change_selects_wire_and_vertical_slice_tests():
    result = select("tests/fixtures/l1/imperfect-inventory.json")

    assert result["full_suite_required"] is False
    assert result["reasons"][0]["classification"] == "workflow_fixture"
    assert result["test_paths"] == [
        "tests/test_l1_wire_smoke.py",
        "tests/workflow/test_vertical_slice.py",
    ]


def test_unicode_graph_evidence_path_is_classified_without_git_quoting():
    result = select("tests/graph_contracts/轴对称多矩形线圈真空场/graph.py")

    assert result["full_suite_required"] is True
    assert result["reasons"][0]["classification"] == "shared_test_material"


def test_shared_test_conftest_fails_closed_to_the_full_suite():
    """The repository-wide test conftest has no bounded test mapping."""
    result = select("tests/conftest.py")

    assert result["full_suite_required"] is True
    assert result["test_paths"] == ["tests"]
    assert result["reasons"][0]["classification"] == "shared_test_material"


def test_unmapped_scirel_source_fails_closed_to_full_suite():
    result = select("src/scirel/_unknown_shared_module.py")

    assert result["full_suite_required"] is True
    assert result["test_paths"] == ["tests"]
    assert "without an asset/test mapping" in result["full_suite_reasons"][0]


def test_every_admitted_asset_has_a_direct_test_mapping():
    result = select(
        *[
            "src/" + item["public_callable"].rsplit(".", 1)[0].replace(".", "/") + ".py"
            for item in json.loads(
                (ROOT / "provenance/admitted-assets.json").read_text(encoding="utf-8")
            )["integrations"]
        ]
    )

    assert len(result["affected_assets"]) == 52
    assert result["full_suite_required"] is False


def test_documented_operator_selects_its_own_direct_test():
    result = select("src/scirel/geometry/complex_rectilinear_interpolation.py")

    assert result["full_suite_required"] is False
    assert result["reasons"][0]["classification"] == "asset_and_reverse_dependencies"
    assert result["test_paths"] == [
        "tests/operator_contracts/test_complex_rectilinear_interpolation.py",
    ]


def test_documented_u1_operators_reverse_select_the_task_graph_test():
    graph_asset = (
        "scirel.geometry.axisymmetric_equilibrium_grid_support."
        "solve_axisymmetric_equilibrium_grid_mapping"
    )
    cases = {
        "src/scirel/geometry/axisymmetric_grid_mapping.py": (
            "tests/operator_contracts/test_axisymmetric_grid_mapping.py",
            "scirel.geometry.axisymmetric_grid_mapping."
            "map_axisymmetric_equilibrium_to_cartesian_grid",
        ),
        "src/scirel/geometry/material_support.py": (
            "tests/operator_contracts/test_material_support.py",
            "scirel.geometry.material_support.classify_material_support",
        ),
    }
    for operator, (operator_test, operator_asset) in cases.items():
        result = select(operator)

        assert result["full_suite_required"] is False, operator
        assert set(result["affected_assets"]) == {graph_asset, operator_asset}, operator
        assert operator_test in result["test_paths"], operator
        assert (
            "tests/graph_contracts/axisymmetric_equilibrium_grid_support/"
            "test_graph_axisymmetric_equilibrium_grid_support.py"
        ) in result["test_paths"], operator


def test_catalog_asset_ids_drive_reverse_dependencies_without_import_inference():
    namespace = runpy.run_path(str(SELECTOR))
    assets = namespace["_load_catalog_assets"]()
    by_ref = {asset.asset_ref: asset for asset in assets}
    mapping = by_ref["scirel.geometry.axisymmetric-equilibrium-grid-mapping"]
    graph = by_ref["scirel.geometry.axisymmetric-equilibrium-grid-support"]

    assert mapping.asset_ref in graph.dependency_refs
    assert graph in namespace["_dependent_assets"]({mapping}, assets)


def test_legacy_graph_dependencies_are_canonicalized_to_documented_asset_ids(tmp_path):
    namespace = runpy.run_path(str(SELECTOR))
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    documented_callables = (
        "scirel.field.rectangular_coil_filaments.discretize_rectangular_coil",
        "scirel.field.current_green_superposition.superpose_current_green_field",
        "scirel.field.circular_filament_green.circular_filament_green_response",
    )
    for source in (ROOT / "catalog/examples").glob("*.json"):
        document = json.loads(source.read_text(encoding="utf-8"))
        public_callable = (
            f"{document['public_api']['python']['module']}."
            f"{document['public_api']['python']['symbol']}"
        )
        if public_callable in documented_callables:
            (catalog / source.name).write_text(
                json.dumps(document), encoding="utf-8"
            )
    namespace["_load_catalog_assets"].__globals__["CATALOG"] = catalog

    assets = namespace["_load_assets"]()
    by_callable = {asset.public_callable: asset for asset in assets}
    graph = by_callable[
        "scirel.field.multi_coil_vacuum_field.solve_multi_coil_vacuum_field"
    ]
    dependency = by_callable[documented_callables[0]]

    assert dependency.asset_ref.startswith("scirel.")
    assert dependency.asset_ref in graph.dependency_refs
    assert graph in namespace["_dependent_assets"]({dependency}, assets)


def test_documented_mirror_quasineutral_leaves_keep_legacy_graph_reverse_dependencies():
    cases = {
        "src/scirel/closures/quasineutral_reference_density.py":
            "tests/operator_contracts/test_quasineutral_reference_density.py",
        "src/scirel/closures/boltzmann_quasineutrality.py":
            "tests/operator_contracts/test_boltzmann_quasineutrality.py",
        "src/scirel/closures/quasineutral_potential.py":
            "tests/operator_contracts/test_quasineutral_potential.py",
        "src/scirel/kinetic/mirror_total_pressure.py":
            "tests/operator_contracts/test_mirror_total_pressure.py",
        "src/scirel/kinetic/mirror_constrained_moments.py":
            "tests/operator_contracts/test_mirror_constrained_moments.py",
    }
    graph_tests = {
        "tests/graph_contracts/mirror_quasineutral_closure/test_graph_mirror_quasineutral_closure.py",
        "tests/graph_contracts/grid_mirror_kinetic_closure/test_graph_grid_mirror_kinetic_closure.py",
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
    }
    for source, direct_test in cases.items():
        result = select(source)
        assert result["full_suite_required"] is False
        assert {direct_test, *graph_tests} <= set(result["test_paths"])


def test_documented_mirror_quasineutral_graph_keeps_outer_reverse_dependencies():
    result = select("src/scirel/closures/mirror_quasineutral_closure.py")
    assert result["full_suite_required"] is False
    assert {
        "tests/graph_contracts/mirror_quasineutral_closure/test_graph_mirror_quasineutral_closure.py",
        "tests/graph_contracts/grid_mirror_kinetic_closure/test_graph_grid_mirror_kinetic_closure.py",
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
    } <= set(result["test_paths"])


def test_documented_flux_profile_keeps_grid_graph_reverse_dependencies():
    result = select("src/scirel/geometry/flux_surface_profile.py")
    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_flux_surface_profile.py",
        "tests/graph_contracts/grid_mirror_kinetic_closure/test_graph_grid_mirror_kinetic_closure.py",
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
    } <= set(result["test_paths"])


def test_documented_ambipolar_potential_keeps_grid_graph_reverse_dependencies():
    result = select("src/scirel/closures/mirror_ambipolar_potential.py")
    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_mirror_ambipolar_potential.py",
        "tests/test_reviewed_failure_semantics.py",
        "tests/graph_contracts/grid_mirror_kinetic_closure/test_graph_grid_mirror_kinetic_closure.py",
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
    } <= set(result["test_paths"])


def test_documented_grid_mirror_graph_keeps_outer_reverse_dependency():
    result = select("src/scirel/kinetic/grid_mirror_kinetic_closure.py")
    assert result["full_suite_required"] is False
    assert {
        "tests/graph_contracts/grid_mirror_kinetic_closure/test_graph_grid_mirror_kinetic_closure.py",
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
    } <= set(result["test_paths"])


def test_documented_poloidal_flux_field_keeps_hall_graph_reverse_dependencies():
    result = select("src/scirel/field/poloidal_field_from_flux.py")
    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_poloidal_field_from_flux.py",
        "tests/graph_contracts/reduced_hall_anisotropic_picard/test_graph_reduced_hall_anisotropic_picard.py",
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
    } <= set(result["test_paths"])


def test_documented_picard_update_keeps_hall_graph_reverse_dependencies():
    result = select("src/scirel/equilibrium/axisymmetric_picard_update.py")
    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_axisymmetric_picard_update.py",
        "tests/graph_contracts/reduced_hall_anisotropic_picard/test_graph_reduced_hall_anisotropic_picard.py",
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
    } <= set(result["test_paths"])


def test_documented_reduced_hall_drift_keeps_graph_reverse_dependencies():
    result = select("src/scirel/closures/reduced_hall_drift.py")
    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_reduced_hall_drift.py",
        "tests/graph_contracts/reduced_hall_anisotropic_picard/test_graph_reduced_hall_anisotropic_picard.py",
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
    } <= set(result["test_paths"])


def test_documented_reduced_hall_graph_keeps_outer_reverse_dependency():
    result = select("src/scirel/equilibrium/reduced_hall_anisotropic_picard.py")
    assert result["full_suite_required"] is False
    assert {
        "tests/graph_contracts/reduced_hall_anisotropic_picard/test_graph_reduced_hall_anisotropic_picard.py",
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
    } <= set(result["test_paths"])


def test_documented_outer_hall_graph_selects_its_direct_tests():
    result = select("src/scirel/equilibrium/kinetic_mirror_hall_equilibrium.py")
    assert result["full_suite_required"] is False
    assert result["test_paths"] == [
        "tests/framework_compositions/test_kinetic_mirror_hall_equilibrium.py",
        "tests/test_incremental_admissions.py",
    ]


def test_documented_dense_green_selects_its_direct_test():
    result = select("src/scirel/field/dense_axisymmetric_green.py")
    assert result["full_suite_required"] is False
    assert result["test_paths"] == [
        "tests/operator_contracts/test_dense_axisymmetric_green.py",
    ]


def test_documented_mirror_green_selects_its_direct_test():
    result = select("src/scirel/field/mirror_plasma_green.py")
    assert result["full_suite_required"] is False
    assert result["test_paths"] == [
        "tests/operator_contracts/test_mirror_plasma_green.py",
    ]


def test_documented_filament_vacuum_field_selects_its_direct_test():
    result = select("src/scirel/field/filament_vacuum_field.py")
    assert result["full_suite_required"] is False
    assert result["test_paths"] == [
        "tests/operator_contracts/test_filament_vacuum_field.py",
    ]


def test_documented_ideal_conductor_boundary_keeps_free_boundary_graph():
    result = select("src/scirel/field/ideal_conductor_boundary.py")
    assert result["full_suite_required"] is False
    assert {
        "tests/operator_contracts/test_ideal_conductor_boundary.py",
        "tests/graph_contracts/free_boundary_anisotropic_picard/test_graph_free_boundary_anisotropic_picard.py",
    } <= set(result["test_paths"])


def test_current_asset_index_unions_legacy_samples_and_exact_documents():
    namespace = runpy.run_path(str(SELECTOR))
    assets = namespace["_load_assets"]()

    assert len(assets) == 114
    assert len({asset.public_callable for asset in assets}) == 114


def test_catalog_asset_keeps_every_declared_direct_test(tmp_path):
    document = json.loads(
        (
            ROOT
            / "catalog/examples/scirel.geometry.complex-rectilinear-interpolation.json"
        ).read_text(encoding="utf-8")
    )
    declared_tests = (
        "tests/operator_contracts/test_complex_rectilinear_interpolation.py",
        "tests/test_public_surface.py",
    )
    document["verification"]["tests"] = list(declared_tests)
    (tmp_path / "asset.json").write_text(
        json.dumps(document), encoding="utf-8"
    )
    namespace = runpy.run_path(str(SELECTOR))
    namespace["_load_catalog_assets"].__globals__["CATALOG"] = tmp_path

    assets = namespace["_load_catalog_assets"]()

    assert assets[0].direct_tests == declared_tests


def test_documented_task_graph_selects_only_its_own_direct_test():
    result = select("src/scirel/geometry/axisymmetric_equilibrium_grid_support.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.geometry.axisymmetric_equilibrium_grid_support."
        "solve_axisymmetric_equilibrium_grid_mapping"
    ]
    assert result["test_paths"] == [
        "tests/graph_contracts/axisymmetric_equilibrium_grid_support/"
        "test_graph_axisymmetric_equilibrium_grid_support.py",
    ]


def test_documented_diagnostics_operator_selects_its_own_direct_test():
    result = select("src/scirel/diagnostics/species_absorption_fraction.py")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == [
        "scirel.diagnostics.species_absorption_fraction."
        "compute_species_absorption_fraction"
    ]
    assert result["test_paths"] == [
        "tests/operator_contracts/test_species_absorption_fraction.py",
    ]


def test_documented_asset_without_a_test_mapping_still_fails_closed():
    """A SciRel source change outside both indexes must not be silently skipped."""
    result = select("src/scirel/geometry/_undocumented_shared_module.py")

    assert result["full_suite_required"] is True
    assert result["test_paths"] == ["tests"]
    assert "without an asset/test mapping" in result["full_suite_reasons"][0]
