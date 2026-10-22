"""Admission status, historical claims and current identity remain distinct."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import review_gate

ASSET = "scirel.test.asset"
REPORT = "catalog/review/evidence/report.csv"


def test_audit_verdict_gate_passes():
    assert review_gate.check() == []


def test_held_assets_are_not_exposed():
    hold = json.loads((ROOT / "catalog" / "review" / "HOLD.json").read_text())
    verdicts = json.loads((ROOT / "catalog" / "review" / "VERDICTS.json").read_text())
    for asset in hold["assets"]:
        assert verdicts["assets"][asset]["status"] == "human-review"


def _git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def _write(path, data):
    path.write_text(json.dumps(data))


def _retain_report(path, data):
    root = path.parents[2]
    data["report_bindings"][REPORT]["retained_sha256"] = hashlib.sha256(
        (root / REPORT).read_bytes()).hexdigest()
    _write(path, data)


def _review(data, field="verdict"):
    evidence = data["assets"][ASSET]["evidence"][0]
    review = {
        "claim": "A maintained correction supersedes this historical claim.",
        "supersedes": [{"report": REPORT, "field": field, "value": evidence[field]}],
        "fix_revision": data["current_candidate"]["base_revision"],
        "tests": ["tests/test_asset.py::test_relation"],
        "verification_status": "NOT_RUN",
        "released_dependencies": [],
    }
    data["assets"][ASSET]["current_review"] = review
    return review


@pytest.fixture
def verdict_fixture(tmp_path, monkeypatch):
    catalog = tmp_path / "catalog" / "examples"
    catalog.mkdir(parents=True)
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_asset.py").write_text("def test_relation():\n    assert 1 + 1 == 2\n")
    (catalog / f"{ASSET}.json").write_text(json.dumps({
        "asset_id": ASSET, "verification": {"tests": ["tests/test_asset.py"]}}))
    implementation = tmp_path / "src" / "scirel"
    implementation.mkdir(parents=True)
    (implementation / "asset.py").write_text("def relation():\n    return 2\n")
    review = tmp_path / "catalog" / "review"
    evidence = review / "evidence"
    evidence.mkdir(parents=True)
    hold = review / "HOLD.json"
    hold.write_text(json.dumps({"schema": "scirel.exposure-hold", "assets": {}}))
    report = tmp_path / REPORT
    report.write_text("asset_id,verdict,oracle,residual_risk\n"
                      f"{ASSET},pass-with-limits,analytic,bounded relation\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "-c", "user.name=Gate fixture", "-c", "user.email=fixture@example.invalid",
         "commit", "-qm", "Fixture candidate")
    revision = _git(tmp_path, "rev-parse", "HEAD")
    verdicts = review / "VERDICTS.json"
    data = {
        "schema": "scirel.audit-verdicts", "historical_candidate_identity": "UNKNOWN",
        "current_candidate": {"base_revision": revision,
                              "identity_scope": "current-materials-only", "material_sha256": ""},
        "report_bindings": {REPORT: {
            "format": "csv", "retained_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "claim_fields": {"verdict": "verdict", "oracle": "oracle", "residual_risk": "residual_risk"}}},
        "assets": {ASSET: {"status": "pass-with-limits", "evidence": [{
            "report": REPORT, "verdict": "pass-with-limits", "oracle": "analytic",
            "residual_risk": "bounded relation"}]}},
    }
    monkeypatch.setattr(review_gate, "ROOT", tmp_path)
    monkeypatch.setattr(review_gate, "HOLD", hold)
    monkeypatch.setattr(review_gate, "VERDICTS", verdicts)
    monkeypatch.setattr(review_gate, "CATALOG", catalog)
    monkeypatch.setattr(review_gate, "REVIEW_CATALOG", review / "examples")
    data["current_candidate"]["material_sha256"] = review_gate.current_material_digest(data)
    return verdicts, data


def test_gate_accepts_a_resolvable_evidence_reference(verdict_fixture):
    path, data = verdict_fixture
    _write(path, data)
    assert review_gate.check() == []


@pytest.mark.parametrize("report", [
    "catalog/review/missing.md",
    "catalog/review/evidence.md + missing.md",
    "../external-evidence.md",
    "/tmp/external-evidence.md",
    "",
    ["catalog/review/evidence.md"],
])
def test_gate_rejects_missing_or_invalid_evidence_paths(verdict_fixture, report):
    path, data = verdict_fixture
    data["assets"][ASSET]["evidence"][0]["report"] = report
    _write(path, data)
    assert any(ASSET in error and "evidence report" in error for error in review_gate.check())


def test_gate_rejects_a_verdict_without_evidence(verdict_fixture):
    path, data = verdict_fixture
    data["assets"][ASSET]["evidence"] = []
    _write(path, data)
    assert any("evidence must be a nonempty array" in error for error in review_gate.check())


def test_an_existing_unrelated_file_is_not_evidence(verdict_fixture):
    path, data = verdict_fixture
    (review_gate.ROOT / "RULES.md").write_text("This is not an audit report.")
    data["assets"][ASSET]["evidence"][0]["report"] = "RULES.md"
    _write(path, data)
    assert any("no valid binding" in error for error in review_gate.check())


@pytest.mark.parametrize("rows", [
    "scirel.some.other.asset,pass-with-limits,analytic,bounded relation\n",
    f"{ASSET},pass-with-limits,analytic,bounded relation\n" * 2,
])
def test_csv_requires_exactly_one_row_for_the_same_asset(verdict_fixture, rows):
    path, data = verdict_fixture
    (review_gate.ROOT / REPORT).write_text("asset_id,verdict,oracle,residual_risk\n" + rows)
    _retain_report(path, data)
    assert any("exactly one asset row" in error for error in review_gate.check())


@pytest.mark.parametrize("field", ["verdict", "oracle", "residual_risk"])
def test_csv_claims_must_match_retained_values(verdict_fixture, field):
    path, data = verdict_fixture
    data["assets"][ASSET]["evidence"][0][field] = "invented claim"
    _write(path, data)
    assert any(f"{field} claim differs" in error for error in review_gate.check())


def test_missing_claim_is_not_treated_as_a_matching_empty_value(verdict_fixture):
    path, data = verdict_fixture
    del data["assets"][ASSET]["evidence"][0]["oracle"]
    _write(path, data)
    assert any("oracle claim differs" in error for error in review_gate.check())


@pytest.mark.parametrize("content", [
    "asset_id,verdict,verdict,oracle,residual_risk\n"
    f"{ASSET},fail,pass-with-limits,analytic,bounded relation\n",
    "asset_id,verdict,oracle,residual_risk\n"
    f"{ASSET},pass-with-limits\n",
    "asset_id,verdict,oracle,residual_risk\n"
    f"{ASSET},pass-with-limits,analytic,bounded relation,discarded failure\n",
])
def test_malformed_csv_cannot_discard_a_claim(verdict_fixture, content):
    path, data = verdict_fixture
    (review_gate.ROOT / REPORT).write_text(content)
    if content.splitlines()[1].count(",") == 1:
        data["assets"][ASSET]["evidence"][0].update(oracle=None, residual_risk=None)
    _retain_report(path, data)
    assert any("CSV" in error for error in review_gate.check())


@pytest.mark.parametrize("reference", [
    "tests/test_asset.py::test_relation",
    "tests/test_asset.py::TestRelation::test_parameterized[case-1]",
])
def test_contract_test_selector_can_bind_the_resolved_file(verdict_fixture, reference):
    path, data = verdict_fixture
    contract = review_gate.CATALOG / f"{ASSET}.json"
    document = json.loads(contract.read_text())
    document["verification"]["tests"] = [reference]
    contract.write_text(json.dumps(document))
    data["current_candidate"]["material_sha256"] = review_gate.current_material_digest(data)
    _write(path, data)
    assert review_gate.check() == []


@pytest.mark.parametrize("reference", [
    "tests/test_asset.py::",
    "tests/test_asset.py::TestRelation::",
    "tests/test_asset.py::::test_relation",
])
def test_contract_empty_test_selectors_fail_closed(verdict_fixture, reference):
    path, data = verdict_fixture
    contract = review_gate.CATALOG / f"{ASSET}.json"
    document = json.loads(contract.read_text())
    document["verification"]["tests"] = [reference]
    contract.write_text(json.dumps(document))
    _write(path, data)
    assert any("invalid test reference" in error for error in review_gate.check())


@pytest.mark.parametrize("field", ["oracle", "residual_risk"])
def test_csv_claims_are_strings_even_when_the_retained_cell_is_empty(verdict_fixture, field):
    path, data = verdict_fixture
    entry = data["assets"][ASSET]["evidence"][0]
    entry[field] = None
    report = review_gate.ROOT / REPORT
    retained = report.read_text().replace("analytic" if field == "oracle" else "bounded relation", "")
    report.write_text(retained)
    _retain_report(path, data)
    assert any(f"{field} claim differs" in error for error in review_gate.check())


def test_changed_report_bytes_are_not_automatically_rebound(verdict_fixture):
    path, data = verdict_fixture
    _write(path, data)
    (review_gate.ROOT / REPORT).write_text("An unrelated replacement report.")
    before = path.read_bytes()
    assert any("retained report bytes differ" in error for error in review_gate.check())
    assert path.read_bytes() == before


@pytest.mark.parametrize("relative", [
    "src/scirel/asset.py", "catalog/examples/scirel.test.asset.json", "tests/test_asset.py",
])
def test_current_product_or_bound_test_drift_invalidates_candidate(verdict_fixture, relative):
    path, data = verdict_fixture
    _write(path, data)
    material = review_gate.ROOT / relative
    material.write_text(material.read_text() + "\n")
    assert any("current candidate material digest differs" in error for error in review_gate.check())


def test_new_review_candidate_code_is_part_of_the_fixed_scope(verdict_fixture):
    path, data = verdict_fixture
    _write(path, data)
    source = review_gate.ROOT / "catalog/review/candidates/src/scirel/candidate.py"
    source.parent.mkdir(parents=True)
    source.write_text("def candidate():\n    return 3\n")
    assert any("material digest differs" in error for error in review_gate.check())


@pytest.mark.parametrize("revision", ["0000000000000000000000000000000000000000", "HEAD"])
def test_candidate_base_must_be_an_actual_full_commit(verdict_fixture, revision):
    path, data = verdict_fixture
    data["current_candidate"]["base_revision"] = revision
    _write(path, data)
    assert any("current_candidate" in error for error in review_gate.check())


def test_candidate_base_must_be_an_ancestor_of_head(verdict_fixture):
    path, data = verdict_fixture
    root = review_gate.ROOT
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    unrelated = subprocess.check_output([
        "git", "-c", "user.name=Gate fixture", "-c", "user.email=fixture@example.invalid",
        "commit-tree", tree, "-m", "Unrelated root"], cwd=root, text=True).strip()
    data["current_candidate"]["base_revision"] = unrelated
    _write(path, data)
    assert any("current_candidate" in error for error in review_gate.check())


def test_historical_identity_cannot_be_filled_from_current_bytes(verdict_fixture):
    path, data = verdict_fixture
    data["historical_candidate_identity"] = data["current_candidate"]["material_sha256"]
    _write(path, data)
    assert any("historical_candidate_identity" in error for error in review_gate.check())


@pytest.mark.parametrize("field", ["candidate", "supersedes"])
def test_unrecognized_record_fields_cannot_bypass_the_canonical_overlay(verdict_fixture, field):
    path, data = verdict_fixture
    data["assets"][ASSET][field] = "invented identity or successor"
    _write(path, data)
    assert any("unrecognized verdict fields" in error for error in review_gate.check())


def test_a_current_overlay_can_supersede_a_locatable_historical_claim(verdict_fixture):
    path, data = verdict_fixture
    _review(data, "residual_risk")
    _write(path, data)
    assert review_gate.check() == []


@pytest.mark.parametrize("change", [
    {"report": "catalog/review/evidence/missing.csv"},
    {"value": "some other asset's finding"},
    {"field": "current_review"},
])
def test_supersession_cannot_dangle_cross_assets_or_cycle(verdict_fixture, change):
    path, data = verdict_fixture
    _review(data)["supersedes"][0].update(change)
    _write(path, data)
    assert any("supersedes" in error for error in review_gate.check())


def test_historical_failure_needs_an_explicit_successor_verdict(verdict_fixture):
    path, data = verdict_fixture
    report = review_gate.ROOT / REPORT
    report.write_text(report.read_text().replace("pass-with-limits", "fail"))
    data["assets"][ASSET]["evidence"][0]["verdict"] = "fail"
    _retain_report(path, data)
    assert any("historical failure needs" in error for error in review_gate.check())
    _review(data, "residual_risk")
    _write(path, data)
    assert any("no explicit successor verdict" in error for error in review_gate.check())
    _review(data, "verdict")
    _write(path, data)
    assert review_gate.check() == []


def test_a_missing_regression_is_not_a_locatable_successor(verdict_fixture):
    path, data = verdict_fixture
    _review(data)["tests"] = ["tests/test_asset.py::test_missing"]
    _write(path, data)
    assert any("test node is missing" in error for error in review_gate.check())


def test_an_exposed_successor_cannot_omit_its_regression_locator(verdict_fixture):
    path, data = verdict_fixture
    _review(data)["tests"] = []
    _write(path, data)
    assert any("exposed successor needs a locatable test" in error for error in review_gate.check())


def test_a_nested_function_is_not_a_collectable_module_test_node(verdict_fixture):
    path, data = verdict_fixture
    source = review_gate.ROOT / "tests/test_asset.py"
    source.write_text("def wrapper():\n    def test_nested():\n        pass\n")
    _review(data)["tests"] = ["tests/test_asset.py::test_nested"]
    data["current_candidate"]["material_sha256"] = review_gate.current_material_digest(data)
    _write(path, data)
    assert any("test node is missing" in error for error in review_gate.check())


def test_a_locatable_test_cannot_be_recorded_as_executed_by_the_gate(verdict_fixture):
    path, data = verdict_fixture
    _review(data)["verification_status"] = "PASS"
    _write(path, data)
    assert any("verification_status must be NOT_RUN" in error for error in review_gate.check())


def test_released_dependency_must_currently_be_public(verdict_fixture):
    path, data = verdict_fixture
    _review(data)["released_dependencies"] = ["scirel.unavailable.forward-solver"]
    _write(path, data)
    assert any("dependency is not currently public" in error for error in review_gate.check())


def test_markdown_claims_stay_unknown_and_cli_reports_actual_state(verdict_fixture, capsys):
    path, data = verdict_fixture
    report = "catalog/review/evidence/source-audit.md"
    source = review_gate.ROOT / report
    source.write_text("Historical audit text; exact candidate identity is unavailable.\n")
    data["assets"][ASSET]["evidence"] = [{"report": report, "verdict": "source-parity"}]
    data["report_bindings"] = {report: {"format": "markdown", "claim_binding": "UNKNOWN",
        "retained_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}}
    _write(path, data)
    assert review_gate.main(["--check"]) == 0
    output = capsys.readouterr().out
    assert data["current_candidate"]["base_revision"] in output
    assert "working tree: dirty" in output
    assert "identity UNKNOWN: 1/1" in output
    assert "claim binding UNKNOWN: 1/1" in output
    assert "execution NOT_RUN" in output
    data["report_bindings"][report]["claim_binding"] = "verified"
    _write(path, data)
    assert any("non-CSV claims must explicitly remain UNKNOWN" in error for error in review_gate.check())


def test_a_retained_test_source_is_explicitly_limited_to_unknown_claim_binding(verdict_fixture):
    path, data = verdict_fixture
    report = "tests/test_asset.py"
    source = review_gate.ROOT / report
    data["assets"][ASSET]["evidence"] = [{"report": report, "verdict": "bounded oracle"}]
    data["report_bindings"] = {report: {"format": "test-source", "claim_binding": "UNKNOWN",
        "retained_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}}
    _write(path, data)
    assert review_gate.check() == []
