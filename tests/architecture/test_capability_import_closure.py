from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from measure_capability_runtime import (  # noqa: E402
    _binding_status,
    measure,
)
from validate_capability_runtime_closure import validate_receipt  # noqa: E402


def test_documented_field_capability_reports_import_closure() -> None:
    result = measure(ROOT, asset_id="scirel.field.poloidal-field-from-flux")

    assert result["status"] == "PASS"
    assert result["schema"] == "scirel.capability-runtime-closure"
    assert result["mode"] == "import"
    assert result["source"]["revision"]
    assert len(result["source"]["content_sha256"]) == 64
    assert result["source_after"] == result["source"]
    assert result["source"]["package_version"] == "0.0.0"
    assert result["child"]["isolated"] is True
    validate_receipt(result)
    assert result["target"]["module"] == "scirel.field"
    assert result["target"]["symbol"] == "poloidal_field_from_flux"
    assert "numpy" in result["external_import_roots"]
    assert "scipy" not in result["external_import_roots"]
    assert "scirel.field.poloidal_field_from_flux" in result["loaded_scirel_modules"]
    assert "scirel.equilibrium._anisotropic_numerics" not in result["loaded_scirel_modules"]


def test_documented_closure_capability_does_not_load_kinetic_private_helpers() -> None:
    result = measure(ROOT, asset_id="scirel.closures.boltzmann-quasineutrality")

    assert result["status"] == "PASS"
    assert "scirel._numerics" in result["loaded_scirel_modules"]
    assert "scirel.mirror._mirror_numerics" not in result["loaded_scirel_modules"]


def test_reduced_hall_closure_does_not_load_equilibrium_private_helpers() -> None:
    result = measure(ROOT, asset_id="scirel.closures.reduced-hall-drift")

    assert result["status"] == "PASS"
    assert "scirel._anisotropic_numerics" in result["loaded_scirel_modules"]
    assert "scirel.equilibrium._anisotropic_numerics" not in result["loaded_scirel_modules"]


def test_mirror_ambipolar_closure_loads_only_the_mirror_private_kernel() -> None:
    result = measure(ROOT, asset_id="scirel.mirror.mirror-ambipolar-potential")

    assert result["status"] == "PASS"
    assert "scirel.mirror._mirror_numerics" in result["loaded_scirel_modules"]
    assert not any(
        module.startswith("scirel.kinetic") for module in result["loaded_scirel_modules"]
    )


def test_direct_dispersion_capability_reports_implementation_path() -> None:
    result = measure(ROOT, asset_id="scirel.kinetic.rational-jpole-coefficients")

    assert result["status"] == "PASS"
    assert result["target"]["module"] == "scirel.kinetic.dispersion.rational"
    assert result["target"]["symbol"] == "jpole_coefficients"
    assert "numpy" in result["external_import_roots"]
    assert "mpmath" not in result["external_import_roots"]


def test_missing_asset_document_fails_closed() -> None:
    with pytest.raises(ValueError, match="catalog asset not found"):
        measure(ROOT, asset_id="scirel.missing.asset")


def test_missing_target_returns_a_child_failure() -> None:
    result = measure(ROOT, target="scirel.missing_module:missing_symbol")

    assert result["status"] == "FAIL"
    assert result["child_returncode"] != 0
    assert result["error"]["type"] == "ModuleNotFoundError"
    validate_receipt(result)


def test_probe_mode_runs_in_the_same_isolated_source_environment(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from scirel.field import poloidal_field_from_flux\n",
        encoding="utf-8",
    )

    result = measure(ROOT, probe=probe)

    assert result["status"] == "PASS"
    assert "numpy" in result["external_import_roots"]


def test_probe_mode_records_call_time_scientific_dependency(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from scirel.kinetic import evaluate_bessel_gamma\nevaluate_bessel_gamma(0, 0.0)\n",
        encoding="utf-8",
    )

    result = measure(ROOT, probe=probe)

    assert result["status"] == "PASS"
    assert result["mode"] == "probe"
    assert len(result["probe_sha256"]) == 64
    assert "numpy" in result["external_import_roots"]
    assert "scipy" in result["external_import_roots"]
    validate_receipt(result)


def test_probe_mode_records_high_precision_mpmath_dependency(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from scirel.kinetic.dispersion.rational import jpole_coefficients\n"
        "jpole_coefficients(J=2, I=2, precision=32)\n",
        encoding="utf-8",
    )

    result = measure(ROOT, probe=probe)

    assert result["status"] == "PASS"
    assert "numpy" in result["external_import_roots"]
    assert "mpmath" in result["external_import_roots"]


def test_runtime_receipt_rejects_wrong_revision_and_dirty_source() -> None:
    result = measure(ROOT, asset_id="scirel.field.poloidal-field-from-flux")
    with pytest.raises(ValueError, match="source revision differs"):
        validate_receipt(result, expected_revision="0" * 40)

    dirty = deepcopy(result)
    dirty["source"]["dirty"] = True
    dirty["source_after"]["dirty"] = True
    dirty["binding_status"] = "UNBOUND"
    dirty["binding_reasons"] = ["source tree is dirty"]
    with pytest.raises(ValueError, match="source tree is dirty"):
        validate_receipt(dirty, require_clean_source=True)
    with pytest.raises(ValueError, match="not BOUND"):
        validate_receipt(dirty, require_bound=True)


def test_runtime_receipt_enforces_expected_linux_python_gate() -> None:
    result = measure(ROOT, asset_id="scirel.field.poloidal-field-from-flux")
    with pytest.raises(ValueError, match="expected system"):
        validate_receipt(result, expected_system="NotThisHost")
    with pytest.raises(ValueError, match="expected Python line"):
        validate_receipt(result, expected_python_line="3.13")


def test_runtime_receipt_rejects_source_content_drift() -> None:
    result = measure(ROOT, asset_id="scirel.field.poloidal-field-from-flux")
    changed = deepcopy(result)
    changed["source_after"]["content_sha256"] = "0" * 64
    changed["binding_status"] = "BOUND"
    changed["binding_reasons"] = []
    with pytest.raises(ValueError, match="source identity changed"):
        validate_receipt(changed)


def test_binding_status_preserves_sorted_multiple_reasons() -> None:
    source = {
        "root": str(ROOT),
        "revision": None,
        "dirty": True,
        "package_version": "0+unknown",
        "content_sha256": "0" * 64,
    }
    status, reasons = _binding_status(
        source, {**source, "content_sha256": "1" * 64}, "a" * 64, "b" * 64
    )
    assert status == "UNBOUND"
    assert reasons == sorted(set(reasons))
    assert "probe identity changed during measurement" in reasons
    assert "source identity changed during measurement" in reasons


def test_unbound_probe_receipt_can_preserve_missing_postimage(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text("pass\n", encoding="utf-8")
    probe_result = measure(ROOT, probe=probe)
    changed = deepcopy(probe_result)
    changed["probe_sha256_after"] = None
    changed["binding_status"] = "UNBOUND"
    changed["binding_reasons"] = ["probe identity changed during measurement"]
    validate_receipt(changed)


def test_invalid_module_prefix_fails_closed() -> None:
    with pytest.raises(ValueError, match="SciRel module"):
        measure(ROOT, target="scirelnot.a")


def test_runtime_closure_contract_declares_the_receipt_schema() -> None:
    contract = json.loads(
        (ROOT / "contracts/capability-runtime-closure.schema.json").read_text(encoding="utf-8")
    )
    assert contract["properties"]["schema"]["const"] == ("scirel.capability-runtime-closure")
    assert "source" in contract["required"]
    assert "source_after" in contract["required"]
    assert "binding_status" in contract["required"]
    assert "binding_reasons" in contract["required"]
    assert "probe_sha256" in contract["required"]
    assert "content_sha256" in contract["properties"]["source"]["required"]
    result = measure(ROOT, asset_id="scirel.field.poloidal-field-from-flux")
    assert set(result) <= set(contract["properties"])
    assert set(contract["required"]) <= set(result)


def test_cli_preflight_failure_emits_a_complete_receipt(capsys: pytest.CaptureFixture[str]) -> None:
    from measure_capability_runtime import main

    assert main(["--root", str(ROOT), "--target", "scirelnot.a"]) == 1
    result = json.loads(capsys.readouterr().out)
    validate_receipt(result)
    assert result["status"] == "FAIL"
    assert result["binding_status"] == "UNBOUND"
    assert "measurement preflight failed" in result["binding_reasons"]
    assert result["child"]["executed"] is False


def test_cli_missing_probe_emits_an_unbound_complete_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from measure_capability_runtime import main

    missing = tmp_path / "missing-probe.py"
    assert main(["--root", str(ROOT), "--probe", str(missing)]) == 1
    result = json.loads(capsys.readouterr().out)
    validate_receipt(result)
    assert result["binding_status"] == "UNBOUND"
    assert "probe input unavailable" in result["binding_reasons"]
    assert result["child"]["executed"] is False


def test_cli_timeout_emits_an_unbound_complete_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from measure_capability_runtime import main

    probe = tmp_path / "sleep-probe.py"
    probe.write_text("import time\ntime.sleep(1)\n", encoding="utf-8")
    assert main(["--root", str(ROOT), "--probe", str(probe), "--timeout", "0.01"]) == 1
    result = json.loads(capsys.readouterr().out)
    validate_receipt(result)
    assert result["status"] == "FAIL"
    assert result["binding_status"] == "UNBOUND"
    assert "child did not emit a runtime measurement" in result["binding_reasons"]
    assert result["child"]["executed"] is False


def test_validator_rejects_bound_receipt_without_an_executed_isolated_child() -> None:
    result = measure(ROOT, asset_id="scirel.field.poloidal-field-from-flux")
    result["status"] = "FAIL"
    result["error"] = {"type": "ChildProcessError", "message": "no measurement"}
    result["child"]["executed"] = False
    result["child"]["isolated"] = False
    result["binding_status"] = "BOUND"
    result["binding_reasons"] = []
    result["source"]["dirty"] = False
    result["source_after"]["dirty"] = False

    with pytest.raises(ValueError, match="BOUND receipt child"):
        validate_receipt(result)
