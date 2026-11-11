"""Changed tools select their actual test consumers and unknown tools fail closed."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import test_scope  # noqa: E402


@pytest.mark.parametrize(
    "script",
    [
        "build_pure_delivery.py",
        "consumer_tools.py",
        "query.py",
        "solving_skill.py",
        "serve_consumer_mcp.py",
        "check_wheel_exposure.py",
    ],
)
def test_consumer_tools_select_the_delivery_tests(script):
    targets, _ = test_scope.classify(Path("scripts") / script)
    assert set(targets) == {"tests/delivery"}


@pytest.mark.parametrize(
    ("script", "owners"),
    [
        ("capability_query.py", {"docs", "tooling", "delivery"}),
        ("capability_catalog.py", {"docs", "delivery"}),
        ("scirel_docs.py", {"docs", "delivery"}),
        ("build_scirel_sphinx.py", {"docs", "delivery"}),
        ("build_capability_matrix.py", {"tooling", "docs", "delivery"}),
        ("validate_asset_documents.py", {"tooling", "architecture", "docs", "delivery"}),
        ("public_api_binding.py", {"tooling", "architecture", "docs", "delivery"}),
        ("mapping_interface_bindings.json", {"tooling", "architecture", "docs", "delivery"}),
        ("package_catalog_snapshot.py", {"tooling"}),
        ("build_catalog.py", {"tooling", "architecture"}),
        ("audit_public_export_documents.py", {"architecture"}),
        ("measure_capability_runtime.py", {"architecture"}),
        ("validate_capability_runtime_closure.py", {"architecture"}),
        ("validate_runtime_imports.py", {"architecture"}),
        ("dev.py", {"tooling", "architecture"}),
    ],
)
def test_shared_tools_select_direct_and_transitive_consumer_layers(script, owners):
    targets, _ = test_scope.classify(Path("scripts") / script)
    assert set(targets) == {"tests/" + owner for owner in owners}


@pytest.mark.parametrize(
    "path",
    [
        ".gitattributes",
        ".gitignore",
        ".githooks/pre-commit",
        ".github/workflows/check.yml",
        ".github/pull_request_template.md",
        ".python-version",
    ],
)
def test_development_infrastructure_selects_architecture_and_tooling(path):
    targets, notes = test_scope.classify(Path(path))
    assert targets == ["tests/tooling", "tests/architecture"]
    assert any("development infrastructure" in note for note in notes)


@pytest.mark.parametrize(
    "path", ["AGENTS.md", "ARCHITECTURE.md", "CONTRIBUTING.md", "README.md", "RULES.md"]
)
def test_maintainer_documents_select_architecture_and_docs(path):
    targets, notes = test_scope.classify(Path(path))
    assert targets == ["tests/architecture", "tests/docs"]
    assert any("maintainer-facing" in note for note in notes)


def test_external_truth_generator_selects_its_consumers_with_an_evidence_limit():
    targets, notes = test_scope.classify(Path("scripts/build_pleiades_truth.py"))
    assert targets == ["tests/cross_domain/multi_coil_vacuum_field"]
    assert any("does not execute the external source generator" in note for note in notes)


@pytest.mark.parametrize(
    "relative", ["SKILL.md", "references/result-checks.md", "scripts/delivery.py"]
)
def test_solving_source_changes_select_the_projection_consumer(relative):
    targets, notes = test_scope.classify(Path("skills/development/usage/scirel-solving") / relative)
    assert targets == ["tests/delivery"]
    assert any("scientific task acceptance is separate" in note for note in notes)


def test_current_script_inventory_has_an_explicit_bounded_scope():
    for script in sorted((ROOT / "scripts").glob("*.py")):
        targets, _ = test_scope.classify(script.relative_to(ROOT))
        assert targets, script.name
        assert "<full-suite>" not in targets, script.name
        assert all((ROOT / target.split("::")[0]).exists() for target in targets), script.name


@pytest.mark.parametrize(
    "unknown",
    [
        "scripts/new_tool.py",
        "scripts/subdirectory/capability_query.py",
        "unknown.input",
    ],
)
def test_unknown_path_fails_closed_even_with_a_resolved_path(unknown, capsys):
    assert test_scope.main(["--changed", "scripts/capability_query.py", unknown]) == 2
    output = capsys.readouterr().out
    assert "FAIL-CLOSED" in output
    assert "Resolved partial scope:" in output
    assert "tests/delivery tests/docs tests/tooling" in output
    assert (
        f"Full suite (required until the mapping is extended):\n  {sys.executable} -m pytest -q\n"
        in output
    )


def test_combined_script_scope_is_deterministic_and_deduplicated(capsys):
    assert (
        test_scope.main(
            ["--changed", "scripts/query.py", "scripts/capability_query.py", "scripts/query.py"]
        )
        == 0
    )
    assert capsys.readouterr().out.splitlines()[-1] == (
        f"  {sys.executable} -m pytest -q tests/delivery tests/docs tests/tooling"
    )


def test_global_configuration_requires_the_full_suite_even_with_bounded_paths(capsys):
    assert test_scope.main(["--changed", "tests/conftest.py", "scripts/capability_query.py"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == f"  {sys.executable} -m pytest -q"


def test_shared_scientific_fixture_selects_the_tests_that_load_it():
    # This selector probe does not load fixture bytes; keep it out of the
    # filename-reference scan that finds the actual scientific consumers.
    fixture = Path("tests/fixtures/inference") / ("anisotropic_" + "recovery.py")
    targets, _ = test_scope.classify(fixture)
    assert targets == ["tests/cross_domain"]


def test_shared_fixture_without_a_test_consumer_fails_closed(tmp_path, monkeypatch):
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    (fixture_root / "test_internal.py").write_text("# unused.dat belongs to fixture support only\n")
    monkeypatch.setattr(test_scope, "TESTS", tmp_path)
    with pytest.raises(test_scope.UnresolvedPath, match="shared fixture has no referencing tests"):
        test_scope.classify(Path("tests/fixtures/unused.dat"))


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("tests/_review_bindings.py", ["tests/cross_domain"]),
        ("tests/fs_links.py", ["tests/delivery", "tests/docs"]),
    ],
)
def test_shared_harness_selects_all_declared_consumers(path, expected):
    targets, _ = test_scope.classify(Path(path))
    assert targets == expected
