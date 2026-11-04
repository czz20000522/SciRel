from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_l1_wire_smoke.py"
SPEC = importlib.util.spec_from_file_location("scirel_l1_wire_smoke", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

FIXTURE_SCRIPT = ROOT / "scripts" / "build_l1_wire_fixture.py"
FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "scirel_l1_wire_fixture", FIXTURE_SCRIPT
)
assert FIXTURE_SPEC is not None and FIXTURE_SPEC.loader is not None
FIXTURE_MODULE = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURE_MODULE)


def test_l1_wire_smoke_replays_import_and_check(tmp_path):
    source = tmp_path / "l1.json"
    source.write_text(
        '{"assets": [], "automated_checks": [{"name": "replay", "status": "passed"}]}',
        encoding="utf-8",
    )

    report = MODULE.run_smoke(source)

    assert report["schema"] == "scirel.l1-wire-smoke.dev"
    assert report["asset_count"] == 0
    assert report["next_action"] == "ready"
    assert report["gap_count"] == 0
    assert report["check_count"] == 1


def test_wire_fixture_keeps_importable_result_body_and_summary(tmp_path):
    source = tmp_path / "l1.json"
    source.write_text(
        '{"assets": [], "automated_checks": [{"name": "replay", "status": "passed"}]}',
        encoding="utf-8",
    )
    output_dir = tmp_path / "wire"

    summary = FIXTURE_MODULE.build_fixture(
        source,
        output_dir,
        artifact_ref="fixture://saved-l1/test",
    )

    response = json.loads(
        (output_dir / "04-automated-check-response.json").read_text(encoding="utf-8")
    )
    candidate_response = json.loads(
        (output_dir / "02-candidate-response.json").read_text(encoding="utf-8")
    )
    candidate_body = (output_dir / "02-candidate-body.json").read_bytes()
    result_body = (output_dir / "05-automated-check-result-body.json").read_bytes()
    saved_summary = json.loads(
        (output_dir / "summary.json").read_text(encoding="utf-8")
    )
    assert candidate_body == candidate_response["body"].encode("utf-8")
    assert FIXTURE_MODULE._digest(candidate_body) == candidate_response["body_digest"]
    assert result_body == response["body"].encode("utf-8")
    assert FIXTURE_MODULE._digest(result_body) == response["body_digest"]
    assert saved_summary == summary
    assert summary["next_action"] == "ready"


def test_imperfect_l1_wire_preserves_machine_repair_gaps_for_retry():
    source = ROOT / "tests" / "fixtures" / "l1" / "imperfect-inventory.json"

    report = MODULE.run_smoke(source)

    assert report["asset_count"] == 2
    assert report["next_action"] == "retry"
    assert report["gap_count"] == 2
    assert report["check_count"] == 2


def test_unautomated_l1_gaps_route_to_explicit_non_ready_actions():
    cases = (
        ("cycle-rework.json", "rework_requested"),
        ("scientific-evidence-gap.json", "needs_evidence"),
    )

    for filename, expected in cases:
        report = MODULE.run_smoke(ROOT / "tests" / "fixtures" / "l1" / filename)
        assert report["next_action"] == expected
        assert report["gap_count"] > 0
