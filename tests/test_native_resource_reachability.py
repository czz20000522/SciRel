from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_native_resource_reachability import audit  # noqa: E402


def test_native_reachability_audit_preserves_full_closure_and_marks_fluid_candidates() -> None:
    report = audit(ROOT)
    assert report["resource_count"] == 117
    fluid = report["groups"]["fluidbw-octave"]
    assert fluid["unreachable_candidates"] == [
        "_fluidbw_native/fD.m",
        "_fluidbw_native/fDtensor.m",
        "_fluidbw_native/fb_dispersion.m",
        "_fluidbw_native/fb_dispersion_observe.m",
    ]
    assert fluid["dynamic_entrypoints"] == [
        "_fluidbw_native/RASY.m",
        "_fluidbw_native/RINT.m",
        "_fluidbw_native/RTAY.m",
        "_fluidbw_native/RYLA.m",
    ]
    assert len(fluid["reachable_files"]) == 32
    assert fluid["public_python_entrypoints"] == [
        "evaluate_fluidbw_special",
        "derive_fluidbw_case",
        "evaluate_fluidbw_dispersion",
        "solve_fluidbw_bonk",
        "assemble_fluidbw_em",
        "solve_fluidbw_em",
        "render_fluidbw_materials",
    ]
    assert fluid["orphan_native_wrappers"] == fluid["unreachable_candidates"]
    assert fluid["dynamic_feval_targets"] == [
        "_fluidbw_native/Gamman.m",
        "_fluidbw_native/Gammapn.m",
        "_fluidbw_native/RASY.m",
        "_fluidbw_native/RINT.m",
        "_fluidbw_native/RTAY.m",
        "_fluidbw_native/RYLA.m",
        "_fluidbw_native/fD.m",
        "_fluidbw_native/fDR.m",
    ]
    assert report["groups"]["pdrk-current-fixtures"]["unreachable_candidates"] == []
    assert report["groups"]["pdrk-rational-legacy"]["unreachable_candidates"] == []


def test_native_reachability_audit_is_diagnostic_and_does_not_change_manifest() -> None:
    report = audit(ROOT)
    assert report["schema"] == "scirel.native-resource-reachability.v1"
    assert "_fluidbw_native/fb_r_harmonic.m" in report["groups"]["fluidbw-octave"]["reachable_files"]
    assert any("negative runtime test" in item for item in report["limitations"])


def test_native_reachability_audit_records_bounded_feval_dispatch() -> None:
    report = audit(ROOT)
    dynamic = report["dynamic_edges"]
    assert dynamic["_fluidbw_native/fb_dispersion.m"] == [
        "_fluidbw_native/fD.m",
        "_fluidbw_native/fDR.m",
    ]
    assert dynamic["_fluidbw_native/fb_dispersion_observe.m"] == [
        "_fluidbw_native/fD.m",
        "_fluidbw_native/fDR.m",
    ]
    assert dynamic["_fluidbw_native/fb_special.m"] == [
        "_fluidbw_native/Gamman.m",
        "_fluidbw_native/Gammapn.m",
        "_fluidbw_native/RASY.m",
        "_fluidbw_native/RINT.m",
        "_fluidbw_native/RTAY.m",
        "_fluidbw_native/RYLA.m",
    ]
