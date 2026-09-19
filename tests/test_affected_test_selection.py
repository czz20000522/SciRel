import json
from pathlib import Path
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
    assert len(result["test_paths"]) == 13


def test_documentation_change_needs_no_scientific_tests():
    result = select("docs/architecture.md")

    assert result["full_suite_required"] is False
    assert result["affected_assets"] == []
    assert result["test_paths"] == []


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
