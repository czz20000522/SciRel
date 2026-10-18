from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from measure_capability_runtime import (  # noqa: E402
    measure,
)


def test_documented_field_capability_reports_import_closure() -> None:
    result = measure(ROOT, asset_id="scirel.field.poloidal-field-from-flux")

    assert result["status"] == "PASS"
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
    assert "scirel.kinetic._mirror_numerics" not in result["loaded_scirel_modules"]


def test_direct_pdrk_capability_reports_implementation_path() -> None:
    result = measure(ROOT, asset_id="scirel.kinetic.pdrk-rational-jpole-coefficients")

    assert result["status"] == "PASS"
    assert result["target"]["module"] == "scirel.kinetic.pdrk.rational"
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
        "from scirel.kinetic import evaluate_bessel_gamma\n"
        "evaluate_bessel_gamma(0, 0.0)\n",
        encoding="utf-8",
    )

    result = measure(ROOT, probe=probe)

    assert result["status"] == "PASS"
    assert "numpy" in result["external_import_roots"]
    assert "scipy" in result["external_import_roots"]


def test_probe_mode_records_high_precision_mpmath_dependency(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from scirel.kinetic.pdrk.rational import jpole_coefficients\n"
        "jpole_coefficients(J=2, I=2, precision=32)\n",
        encoding="utf-8",
    )

    result = measure(ROOT, probe=probe)

    assert result["status"] == "PASS"
    assert "numpy" in result["external_import_roots"]
    assert "mpmath" in result["external_import_roots"]
