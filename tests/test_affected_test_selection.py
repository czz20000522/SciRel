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
        encoding="utf-8",
        errors="replace",
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
    assert "tests/test_admitted_integrations.py" in result["test_paths"]


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
        "tests/test_admitted_integrations.py",
    ]


def test_package_export_change_checks_public_surface_and_asset_examples():
    result = select("src/scirel/field/__init__.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == [
        "tests/test_asset_documentation.py",
        "tests/test_public_surface.py",
    ]


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
    assert {
        "tests/graph_contracts/frank_egedal_pressure_closure/test_graph_frank_egedal_pressure_closure.py",
        "tests/operator_contracts/test_frank_egedal_hot_ion_moments.py",
        "tests/operator_contracts/test_frank_egedal_pressure_state.py",
        "tests/operator_contracts/test_frank_egedal_radial_envelope.py",
        "tests/operator_contracts/test_frank_egedal_source_projection.py",
        "tests/operator_contracts/test_loss_cone_spectrum.py",
    } <= set(result["test_paths"])


def test_documentation_change_needs_no_scientific_tests():
    result = select("docs/architecture.md")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == []
    assert result["test_paths"] == []


def test_asset_schema_change_selects_contract_tests():
    result = select("contracts/scientific-asset-document.schema.json")
    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_asset_documentation.py"]


def test_exact_document_change_selects_asset_and_reverse_graph_tests():
    result = select("catalog/examples/scirel.field.circular-filament-green.json")

    assert result["full_suite_required"] is False
    assert result["reasons"][0]["classification"] == "asset_document_and_reverse_dependencies"
    assert set(result["affected_assets"]) == {
        "scirel.field.circular_filament_green.circular_filament_green_response",
        "scirel.field.multi_coil_vacuum_field.solve_multi_coil_vacuum_field",
    }
    assert result["test_paths"] == [
        "tests/graph_contracts/multi_coil_vacuum_field/test_graph_multi_coil_vacuum_field.py",
        "tests/operator_contracts/test_circular_filament_green.py",
        "tests/test_asset_documentation.py",
    ]


def test_unmapped_exact_document_change_fails_closed():
    result = select("catalog/examples/scirel.field.unmapped.json")

    assert result["full_suite_required"] is True
    assert result["test_paths"] == ["tests"]
    assert result["reasons"][0]["classification"] == "unmapped_asset_document"


def test_release_environment_helper_change_selects_only_its_contract_test():
    result = select("scripts/check_helpers.ps1")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_release_environment.py"]


def test_release_finalizer_selects_catalog_and_legacy_gate_tests():
    result = select("scripts/finalize_release.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == [
        "tests/test_legacy_release_gate.py",
        "tests/test_release_finalization.py",
    ]


def test_review_scope_report_selects_only_its_contract_test():
    result = select("scripts/review_scope.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_review_scope.py"]


def test_review_version_freeze_selects_only_its_contract_test():
    result = select("scripts/freeze_review_version.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_review_version_freeze.py"]


def test_wire_fixture_builder_selects_only_wire_smoke_test():
    result = select("scripts/build_l1_wire_fixture.py")

    assert result["full_suite_required"] is False
    assert result["test_paths"] == ["tests/test_l1_wire_smoke.py"]


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
        "tests/test_workflow_contracts.py",
        "tests/test_legacy_release_gate.py",
    }


def test_plugin_contract_change_selects_plugin_and_vertical_boundary():
    result = select("src/scirel_plugin/contract.py")

    assert result["full_suite_required"] is False
    assert result["reasons"][0]["classification"] == "plugin_source_contract"
    assert set(result["test_paths"]) == {
        "tests/plugin/test_codefusion_plugin_contract.py",
        "tests/plugin/test_http_listener.py",
        "tests/workflow/test_vertical_slice.py",
        "tests/test_legacy_release_gate.py",
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
        "tests/test_workflow_contracts.py",
        "tests/plugin/test_codefusion_plugin_contract.py",
        "tests/plugin/test_http_listener.py",
        "tests/test_legacy_release_gate.py",
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
        "tests/test_admitted_integrations.py",
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
        assert "tests/test_admitted_integrations.py" in result["test_paths"], operator


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


def test_current_asset_index_unions_legacy_samples_and_exact_documents():
    namespace = runpy.run_path(str(SELECTOR))
    assets = namespace["_load_assets"]()

    assert len(assets) == 81
    assert len({asset.public_callable for asset in assets}) == 81


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
        "tests/test_admitted_integrations.py",
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
        "tests/test_admitted_integrations.py",
    ]


def test_documented_asset_without_a_test_mapping_still_fails_closed():
    """A SciRel source change outside both indexes must not be silently skipped."""
    result = select("src/scirel/geometry/_undocumented_shared_module.py")

    assert result["full_suite_required"] is True
    assert result["test_paths"] == ["tests"]
    assert "without an asset/test mapping" in result["full_suite_reasons"][0]
