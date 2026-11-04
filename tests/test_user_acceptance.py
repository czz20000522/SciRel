"""Exercise the maintained user tasks without a source-project checkout."""

from pathlib import Path
import runpy
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = runpy.run_path(str(ROOT / "examples" / "user_acceptance.py"))


def test_user_acceptance_tasks_create_their_declared_results(tmp_path):
    tasks = (
        ("green_field_synthesis", "green_field_synthesis.csv"),
        ("quasineutral_profile", "quasineutral_profile.json"),
        ("pressure_state_and_residual", "pressure_state_and_residual.json"),
        ("reusable_complex_field_profile", "reusable_complex_field_profile.json"),
        ("unbound_complex_field_profile", "unbound_complex_field_profile.json"),
        ("multi_coil_vacuum_followup", "multi_coil_vacuum_followup.json"),
    )
    for task, artifact in tasks:
        report = ACCEPTANCE[task](tmp_path)
        assert report["passed"] is True
        assert (tmp_path / artifact).is_file()


def test_reusable_complex_field_profile_records_reuse_bindings(tmp_path):
    report = ACCEPTANCE["reusable_complex_field_profile"](tmp_path)

    assert report["passed"] is True
    assert report["reused_intermediate"] is True
    assert report["sampling_asset_id"] == "scirel.geometry.complex-rectilinear-interpolation"
    assert report["metadata"]["source_axes_m"] == ["x_m", "y_m", "z_m"]
    assert report["metadata"]["coordinate_basis"] == "cartesian_m"
    assert report["metadata"]["support_mask_name"] == "support_mask"
    assert report["metadata"]["generation_plan_version"] == "acceptance.reusable_complex_field_profile.v1"
    assert report["metadata"]["intermediate_digest"].startswith("sha256:")
    assert report["metadata"]["axis_digest"].startswith("sha256:")
    assert report["metadata"]["support_mask_digest"].startswith("sha256:")
    with ACCEPTANCE["np"].load(
        tmp_path / "reusable_complex_field_intermediate.npz", allow_pickle=False
    ) as saved:
        assert saved["coordinate_basis"].item() == report["metadata"]["coordinate_basis"]
        assert saved["generation_plan_version"].item() == report["metadata"]["generation_plan_version"]
        assert saved["axis_digest"].item() == report["metadata"]["axis_digest"]
        assert saved["support_mask_digest"].item() == report["metadata"]["support_mask_digest"]
    assert report["rows"] == 3
    assert report["finite_rows"] == 1
    assert report["status_counts"] == {
        "sampled": 1,
        "stencil_touches_unsupported_cell": 1,
        "outside_grid_box": 1,
    }


def test_unbound_reusable_intermediate_is_not_treated_as_strong_reuse(tmp_path):
    report = ACCEPTANCE["unbound_complex_field_profile"](tmp_path)

    assert report["passed"] is True
    assert report["reused_intermediate"] is False
    assert report["evidence_ceiling"] == "insufficient_intermediate_bindings"
    assert report["missing_bindings"] == [
        "source_axes_m",
        "coordinate_basis",
        "support_mask_name",
        "generation_plan_version",
        "axis_digest",
        "support_mask_digest",
    ]
    assert report["status_counts"] == {
        "not_sampled": 1,
    }


def test_multi_coil_followup_preserves_initial_result_bytes(tmp_path):
    report = ACCEPTANCE["multi_coil_vacuum_followup"](tmp_path)

    assert report["passed"] is True
    assert report["initial_summary_sha256_before_followup"] == report[
        "initial_summary_sha256_after_followup"
    ]
    assert report["followup_rows"] == 2
    assert report["settings"] == ["balanced", "shifted", "reverse", "idle"]


def test_multi_coil_followup_rejects_duplicate_current_rows(tmp_path):
    report = ACCEPTANCE["multi_coil_vacuum_followup"](tmp_path)

    assert report["passed"] is True
    assert report["duplicate_current_row_rejected"] is True
    assert "duplicate setting/coil row" in report["duplicate_current_row_error"]


def test_verify_installation_rejects_installed_package_that_differs_from_wheel(
    tmp_path, monkeypatch
):
    prefix = tmp_path / "venv"
    package_root = prefix / "Lib" / "site-packages" / "scirel"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text(
        "# tampered installed package\n", encoding="utf-8"
    )
    wheel = tmp_path / "scirel-0.1.0.dev5-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("scirel/__init__.py", "# wheel package\n")

    class FakeDistribution:
        version = "0.1.0.dev5"

        def locate_file(self, member):
            if member == "scirel":
                return package_root
            return prefix / "Lib" / "site-packages" / member

        def read_text(self, name):
            if name == "direct_url.json":
                return "{}"
            return None

    monkeypatch.setattr(ACCEPTANCE["sys"], "prefix", str(prefix))
    monkeypatch.setattr(ACCEPTANCE["scirel"], "__file__", str(package_root / "__init__.py"))
    monkeypatch.setattr(
        ACCEPTANCE["importlib"].metadata,
        "distribution",
        lambda name: FakeDistribution(),
    )

    with pytest.raises(AssertionError, match="scirel/__init__.py"):
        ACCEPTANCE["verify_installation"](wheel)


def test_verify_installation_rejects_editable_distribution(tmp_path, monkeypatch):
    prefix = tmp_path / "venv"
    package_root = prefix / "Lib" / "site-packages" / "scirel"
    package_root.mkdir(parents=True)
    package_file = package_root / "__init__.py"
    package_file.write_text("# installed package\n", encoding="utf-8")
    wheel = tmp_path / "scirel-0.1.0.dev5-py3-none-any.whl"

    class FakeDistribution:
        version = "0.1.0.dev5"

        def locate_file(self, member):
            if member == "scirel":
                return package_root
            return prefix / "Lib" / "site-packages" / member

        def read_text(self, name):
            if name == "direct_url.json":
                return '{"dir_info": {"editable": true}}'
            return None

    monkeypatch.setattr(ACCEPTANCE["sys"], "prefix", str(prefix))
    monkeypatch.setattr(ACCEPTANCE["scirel"], "__file__", str(package_file))
    monkeypatch.setattr(
        ACCEPTANCE["importlib"].metadata,
        "distribution",
        lambda name: FakeDistribution(),
    )

    with pytest.raises(AssertionError):
        ACCEPTANCE["verify_installation"](wheel)
