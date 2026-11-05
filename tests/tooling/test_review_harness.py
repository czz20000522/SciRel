"""Review tools keep candidate checks explicit, bounded and fail closed."""

import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import review_harness
import test_scope

ASSET = "scirel.inference.direct-anisotropic-inversion"
COMPOSITION = "tests/cross_domain/direct_anisotropic_inversion/test_composition_direct_anisotropic_inversion.py"
PHYSICAL = "tests/cross_domain/test_inference_physical_closure.py"
INDEPENDENT = "tests/cross_domain/test_anisotropic_inference_independent.py"


@pytest.fixture
def review_fixture(tmp_path, monkeypatch):
    review = tmp_path / "catalog" / "review"
    examples = review / "examples"
    examples.mkdir(parents=True)
    document = json.loads(
        (ROOT / "catalog" / "review" / "examples" / (ASSET + ".json")).read_text()
    )
    document["verification"]["tests"] = [COMPOSITION, PHYSICAL, INDEPENDENT]
    (examples / (ASSET + ".json")).write_text(json.dumps(document))
    (review / "HOLD.json").write_text(
        json.dumps(
            {"schema": "scirel.exposure-hold", "assets": {ASSET: {"status": "human-review"}}}
        )
    )
    candidate = (
        review / "candidates" / "src" / "scirel" / "inference" / "direct_anisotropic_inversion.py"
    )
    candidate.parent.mkdir(parents=True)
    candidate.write_text("# Candidate is checked in the separate runtime stage.\n")
    for reference in [*document["verification"]["tests"], review_harness.IMPORT_SURFACE_TEST]:
        path = tmp_path / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_bound_case(): pass\n")
    monkeypatch.setattr(review_harness, "ROOT", tmp_path)
    monkeypatch.setattr(test_scope, "ROOT", tmp_path)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(review_harness.subprocess, "run", run)
    return tmp_path, document, calls


def _write_contract(root, document):
    (root / "catalog" / "review" / "examples" / (ASSET + ".json")).write_text(json.dumps(document))


def test_harness_runs_contract_runtime_examples_and_explicit_test_closure(review_fixture):
    root, _, calls = review_fixture
    assert review_harness.main(["--check"]) == 0
    assert len(calls) == 2
    assert "-c" in calls[0][0]
    pytest_command, options = calls[1]
    assert pytest_command[:5] == [sys.executable, "-B", "-m", "pytest", "-q"]
    assert set(pytest_command[5:]) == {
        COMPOSITION,
        PHYSICAL,
        INDEPENDENT,
        review_harness.IMPORT_SURFACE_TEST,
    }
    assert options["env"]["SCIREL_REVIEW_HOLD"] == "1"
    assert "candidates" not in options["env"]["PYTHONPATH"]
    assert options["cwd"] == root
    assert options["timeout"] == review_harness.STAGE_TIMEOUT_SECONDS


def test_harness_rejects_a_missing_direct_test_before_running_any_stage(review_fixture):
    root, _, calls = review_fixture
    (root / PHYSICAL).unlink()
    assert review_harness.main(["--check"]) == 1
    assert calls == []


def test_harness_requires_the_default_import_surface_check(review_fixture):
    root, _, calls = review_fixture
    (root / review_harness.IMPORT_SURFACE_TEST).unlink()
    assert review_harness.main(["--check"]) == 1
    assert calls == []


def test_harness_rejects_an_empty_test_binding_instead_of_running_all_tests(review_fixture):
    root, document, calls = review_fixture
    document["verification"]["tests"] = []
    _write_contract(root, document)
    assert review_harness.main(["--check"]) == 1
    assert calls == []


def test_harness_preserves_pytest_node_selectors(review_fixture):
    root, document, calls = review_fixture
    selected = PHYSICAL + "::test_bound_case"
    document["verification"]["tests"] = [selected]
    _write_contract(root, document)
    assert review_harness.main(["--check"]) == 0
    assert selected in calls[1][0]


def test_harness_has_an_explicit_no_hold_no_test_result(review_fixture):
    root, _, calls = review_fixture
    (root / "catalog" / "review" / "HOLD.json").write_text(
        json.dumps({"schema": "scirel.exposure-hold", "assets": {}})
    )
    assert review_harness.main(["--check"]) == 0
    assert calls == []


def test_harness_stops_when_contract_stage_fails(review_fixture, monkeypatch):
    _, _, calls = review_fixture

    def fail(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(review_harness.subprocess, "run", fail)
    assert review_harness.main(["--check"]) == 7
    assert len(calls) == 1


def test_harness_fails_a_timed_out_stage(review_fixture, monkeypatch):
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(review_harness.subprocess, "run", timeout)
    assert review_harness.main(["--check"]) == 1


@pytest.mark.parametrize(
    "path",
    [
        "catalog/review/candidates/src/scirel/inference/direct_anisotropic_inversion.py",
        "catalog/review/examples/" + ASSET + ".json",
        "scripts/review_harness.py",
    ],
)
def test_candidate_and_harness_scopes_include_the_bound_direct_tests(review_fixture, path):
    targets, _ = test_scope.classify(Path(path))
    assert {COMPOSITION, PHYSICAL, INDEPENDENT, "tests/tooling", "tests/architecture"} <= set(
        targets
    )


def test_candidate_scope_fails_closed_for_a_missing_test(review_fixture):
    root, _, _ = review_fixture
    (root / PHYSICAL).unlink()
    with pytest.raises(test_scope.UnresolvedPath, match="declared test is missing"):
        test_scope.classify(Path("scripts/review_harness.py"))


def test_unbound_candidate_scope_fails_closed(review_fixture):
    with pytest.raises(test_scope.UnresolvedPath, match="no held contract binding"):
        test_scope.classify(Path("catalog/review/candidates/src/scirel/inference/unbound.py"))


def test_current_held_contract_binds_composition_and_physical_closure():
    document = json.loads(
        (ROOT / "catalog" / "review" / "examples" / (ASSET + ".json")).read_text()
    )
    assert {COMPOSITION, PHYSICAL, INDEPENDENT} <= set(document["verification"]["tests"])


def test_review_contract_executes_example_without_changing_public_exports(monkeypatch):
    import scirel.inference as inference

    document = json.loads(
        (ROOT / "catalog" / "review" / "examples" / (ASSET + ".json")).read_text()
    )
    document["example"]["code"] = "raise RuntimeError('held example was executed')"
    original = json.dumps(document, sort_keys=True)
    exports = list(inference.__all__)
    monkeypatch.setattr(review_harness, "load_review_documents", lambda root: [document])
    with pytest.raises(RuntimeError, match="held example was executed"):
        review_harness.check_contracts()
    assert json.dumps(document, sort_keys=True) == original
    assert inference.__all__ == exports
    assert "solve_direct_anisotropic_inversion" not in inference.__all__
    assert not hasattr(inference, "solve_direct_anisotropic_inversion")


def test_review_contract_rejects_a_different_canonical_callable(monkeypatch):
    import scirel.inference as inference

    document = json.loads(
        (ROOT / "catalog" / "review" / "examples" / (ASSET + ".json")).read_text()
    )
    document["public_api"]["python"].update(
        canonical_module="scirel.inference", canonical_symbol="solve_direct_anisotropic_inversion"
    )
    monkeypatch.setattr(review_harness, "load_review_documents", lambda root: [document])
    monkeypatch.setattr(
        inference, "solve_direct_anisotropic_inversion", lambda: None, raising=False
    )
    with pytest.raises(ValueError, match="canonical review binding differs"):
        review_harness.check_contracts()
