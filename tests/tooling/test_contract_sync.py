"""Regression tests for docstring/contract synchronization mechanics."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/development/scirel-acceptance/scripts/check_contract_sync.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_contract_sync", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_direct_parameter_is_required_even_when_var_keyword_is_documented():
    module = _load()

    def sampled(inputs=None, **kwargs):
        pass

    parameters = list(inspect.signature(sampled).parameters.values())
    parts = module.sections(
        """Parameters
----------
**kwargs
    Named inputs merged into ``inputs``.
"""
    )
    assert module._missing_direct_parameter_docs(parameters, parts) == ["inputs"]


def test_direct_parameter_is_accepted_when_documented():
    module = _load()

    def sampled(inputs=None, **kwargs):
        pass

    parameters = list(inspect.signature(sampled).parameters.values())
    parts = module.sections(
        """Parameters
----------
inputs : mapping, optional
    Input mapping.
**kwargs
    Named inputs merged into ``inputs``.
"""
    )
    assert module._missing_direct_parameter_docs(parameters, parts) == []


def test_exception_names_include_custom_failure_types():
    module = _load()
    assert module.ERROR.findall("ContinuationFailure") == ["ContinuationFailure"]


def _contract_and_record(**overrides):
    document = {
        "applicability": {
            "preconditions": ["a", "b"],
            "supported": ["c"],
            "excluded": ["d", "e", "f"],
        },
        "verification": {
            "scope": ["g", "h"],
            "known_limitations": ["i"],
            "tests": ["tests/test_example.py"],
            "evidence_ceiling": "Mechanical consistency only.",
        },
    }
    record = {
        "applicability": {
            "preconditions": ["甲", "乙"],
            "supported": ["丙"],
            "excluded": ["丁", "戊", "己"],
        },
        "verification": {
            "scope": ["庚", "辛"],
            "known_limitations": ["壬"],
            "evidence_ceiling": "仅检查机械一致性。",
        },
        "source_sha256": "a" * 64,
    }
    for path, value in overrides.items():
        section, key = path.split("__")
        record[section][key] = value
    return document, record


def test_a_dropped_clause_is_reported_with_both_counts():
    module = _load()
    document, record = _contract_and_record(verification__known_limitations=[])
    errors = module.clause_errors(document, record)
    assert len(errors) == 1
    assert "verification.known_limitations" in errors[0]
    assert "1 clause" in errors[0] and "0 " in errors[0]
    assert "fewer on the reader side" in errors[0]


def test_an_extra_clause_is_reported_as_more_on_the_reader_side():
    module = _load()
    document, record = _contract_and_record(applicability__excluded=["丁", "戊", "己", "庚"])
    errors = module.clause_errors(document, record)
    assert len(errors) == 1
    assert "applicability.excluded" in errors[0]
    assert "3 clause" in errors[0] and "4 " in errors[0]
    assert "more on the reader side" in errors[0]


def test_equal_counts_with_a_misspelt_key_are_still_rejected():
    module = _load()
    document, record = _contract_and_record()
    record["verification"]["known_limitation"] = ["误拼写的额外字段"]
    errors = module.clause_errors(document, record)
    assert len(errors) == 1
    assert "verification.known_limitation:" in errors[0]
    assert "clause count" not in errors[0]


def test_renamed_clause_key_reports_both_the_missing_and_unknown_fields():
    module = _load()
    document, record = _contract_and_record()
    record["verification"]["known_limitation"] = record["verification"].pop("known_limitations")
    errors = module.clause_errors(document, record)
    assert len(errors) == 2
    assert any("verification.known_limitation:" in error for error in errors)
    assert any(
        "verification.known_limitations:" in error and "no field" in error for error in errors
    )


@pytest.fixture
def reader_case(tmp_path, monkeypatch):
    module = _load()
    document, record = _contract_and_record()
    asset_id = "scirel.test.contract-sync"

    def sampled():
        """Return one.

        Returns
        -------
        result : int
            One.

        Raises
        ------
        ValueError
            No invalid inputs are accepted.

        See Also
        --------
        int

        Examples
        --------
        >>> 1
        1
        """
        return 1

    monkeypatch.setitem(sys.modules, "contract_sync_sample", SimpleNamespace(sampled=sampled))
    document.update(
        asset_id=asset_id,
        public_api={
            "python": {
                "module": "contract_sync_sample",
                "symbol": "sampled",
                "signature": "sampled()",
            }
        },
        inputs=[],
        outputs=[],
        failure_semantics={},
        example={"code": "1\n"},
    )
    contract_path = tmp_path / "catalog/examples" / f"{asset_id}.json"
    contract_path.parent.mkdir(parents=True)
    contract_bytes = json.dumps(document).encode()
    contract_path.write_bytes(contract_bytes)
    record.update(asset_id=asset_id, source_sha256=hashlib.sha256(contract_bytes).hexdigest())
    reader_path = tmp_path / "tools/docs/zh/zh_test.json"
    reader_path.parent.mkdir(parents=True)

    def check_record():
        reader_path.write_text(json.dumps({"records": [record]}), encoding="utf-8")
        return module.check({"asset_id": asset_id}, root=tmp_path)

    return record, check_record


def test_bound_reader_with_matching_clauses_has_no_sync_errors(reader_case):
    _, check_record = reader_case
    assert check_record() == []


@pytest.mark.parametrize("change", ["fewer", "more", "key"])
def test_check_reports_independent_reader_failures_with_asset_and_file(reader_case, change):
    record, check_record = reader_case
    if change == "fewer":
        record["verification"]["known_limitations"].pop()
    elif change == "more":
        record["verification"]["known_limitations"].append("额外条款")
    elif change == "key":
        record["verification"]["known_limitation"] = ["拼错字段"]
    errors = check_record()
    assert len(errors) == 1
    assert all("scirel.test.contract-sync: zh_test.json" in error for error in errors)
    assert sum("clause count" in error for error in errors) == int(change in {"fewer", "more"})
    if change in {"fewer", "more"}:
        count_error = next(error for error in errors if "clause count" in error)
        assert "verification.known_limitations" in count_error
        assert "contract has 1 clause(s)" in count_error
        assert f"reader record has {2 if change == 'more' else 0} " in count_error
    if change == "key":
        assert "verification.known_limitation:" in errors[0]


def _sample_docstring(raises, warns=None):
    """Build the sample docstring with the declaration sections a case needs."""
    body = f"Raises\n------\n{raises}\n"
    if warns:
        body += f"\nWarns\n-----\n{warns}\n"
    return (
        "Return one.\n"
        "\n"
        "Returns\n"
        "-------\n"
        "result : int\n"
        "    One.\n"
        "\n"
        f"{body}"
        "\n"
        "See Also\n"
        "--------\n"
        "int\n"
        "\n"
        "Examples\n"
        "--------\n"
        ">>> 1\n"
        "1\n"
    )


@pytest.fixture
def declaration_case(tmp_path, monkeypatch):
    """Build one asset whose docstring declares exactly the sections a test needs."""
    module = _load()
    asset_id = "scirel.test.declaration"

    def build(*, raises, warns=None, failure_semantics):
        document, record = _contract_and_record()
        document.update(
            asset_id=asset_id,
            public_api={
                "python": {
                    "module": "contract_sync_declaration",
                    "symbol": "sampled",
                    "signature": "sampled()",
                }
            },
            inputs=[],
            outputs=[],
            failure_semantics=failure_semantics,
            example={"code": "1\n"},
        )

        def sampled():
            return 1

        sampled.__doc__ = _sample_docstring(raises, warns)
        monkeypatch.setitem(
            sys.modules, "contract_sync_declaration", SimpleNamespace(sampled=sampled)
        )
        contract_path = tmp_path / "catalog/examples" / f"{asset_id}.json"
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_bytes = json.dumps(document).encode()
        contract_path.write_bytes(contract_bytes)
        record.update(asset_id=asset_id, source_sha256=hashlib.sha256(contract_bytes).hexdigest())
        reader_path = tmp_path / "tools/docs/zh/zh_test.json"
        reader_path.parent.mkdir(parents=True, exist_ok=True)
        reader_path.write_text(json.dumps({"records": [record]}), encoding="utf-8")
        return module.check({"asset_id": asset_id}, root=tmp_path)

    return build


def test_a_declared_warning_must_be_documented_under_warns(declaration_case):
    """A warning is not an exception: Raises cannot carry it.

    Reading only the Raises section used to make the check demand exactly that,
    so this pins the corrected rule from both sides.
    """
    warning = "ApplicabilityWarning\n    Outside the fitted range."
    errors = declaration_case(
        raises=f"ValueError\n    Invalid input.\n{warning}",
        failure_semantics={"runtime_failure": "Above the fitted range it warns."},
    )
    assert len(errors) == 1
    assert "ApplicabilityWarning is a warning and belongs under Warns" in errors[0]

    clean = declaration_case(
        raises="ValueError\n    Invalid input.",
        warns=warning,
        failure_semantics={"runtime_failure": "Above the fitted range it warns."},
    )
    assert clean == []


def test_a_warning_documented_only_under_warns_satisfies_failure_semantics(declaration_case):
    """The declared set is the union of both sections, so a warning in Warns counts."""
    errors = declaration_case(
        raises="ValueError\n    Invalid input.",
        warns="ApplicabilityWarning\n    Outside the fitted range.",
        failure_semantics={
            "invalid_input": "Raises ValueError.",
            "runtime_failure": "Emits ApplicabilityWarning above the fitted range.",
        },
    )
    assert errors == []


def test_an_exception_documented_under_warns_is_rejected(declaration_case):
    """The rule is symmetric: an exception belongs under Raises."""
    errors = declaration_case(
        raises="ValueError\n    Invalid input.",
        warns="ApplicabilityWarning\n    Outside the fitted range.\nTypeError\n    Wrong kind.",
        failure_semantics={"runtime_failure": "Emits ApplicabilityWarning."},
    )
    assert len(errors) == 1
    assert "TypeError is not a Warning subclass and belongs under Raises" in errors[0]


def test_a_declared_name_missing_from_both_sections_is_reported(declaration_case):
    """A name in neither section is still an unverified declaration."""
    errors = declaration_case(
        raises="ValueError\n    Invalid input.",
        failure_semantics={"runtime_failure": "Emits ApplicabilityWarning."},
    )
    assert len(errors) == 1
    assert "neither Raises nor Warns lists it" in errors[0]


@pytest.fixture
def catalog_case(tmp_path, monkeypatch):
    module = _load()
    catalog = tmp_path / "catalog/examples"
    catalog.mkdir(parents=True)
    asset_ids = ["scirel.test.first", "scirel.test.without-rules"]
    for asset_id in asset_ids:
        (catalog / f"{asset_id}.json").write_text(
            json.dumps({"asset_id": asset_id}), encoding="utf-8"
        )
    rules = tmp_path / "rules.json"
    rules.write_text(
        json.dumps({"schema": "scirel.contract-sync-rules", "assets": []}), encoding="utf-8"
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "RULES", rules, raising=False)
    visited = []

    def check(asset, **kwargs):
        visited.append(asset)
        return []

    monkeypatch.setattr(module, "check", check)
    return module, catalog, rules, asset_ids, visited


def test_default_checks_every_public_asset_without_requiring_rules(catalog_case, capsys):
    module, _, _, asset_ids, visited = catalog_case
    assert module.main([]) == 0
    assert [asset["asset_id"] for asset in visited] == asset_ids
    assert "2 assets, 0 problems" in capsys.readouterr().out


@pytest.mark.parametrize("selection", [["scirel.nonexistent.phase1-proof"], [""]])
def test_unknown_or_empty_explicit_selection_fails(catalog_case, capsys, selection):
    module, _, _, _, visited = catalog_case
    assert module.main(selection) == 1
    assert "unknown asset" in capsys.readouterr().out
    assert visited == []


def test_mixed_known_and_unknown_selection_cannot_hide_unknown_id(catalog_case, capsys):
    module, _, _, asset_ids, _ = catalog_case
    assert module.main([asset_ids[0], "scirel.nonexistent.phase1-proof"]) == 1
    assert "scirel.nonexistent.phase1-proof" in capsys.readouterr().out


def test_explicit_selection_checks_public_asset_without_rules(catalog_case):
    module, _, _, asset_ids, visited = catalog_case
    assert module.main([asset_ids[1]]) == 0
    assert visited == [{"asset_id": asset_ids[1]}]


@pytest.mark.parametrize("missing", [False, True])
def test_empty_or_missing_catalog_fails(catalog_case, capsys, missing):
    module, catalog, _, _, visited = catalog_case
    for path in catalog.iterdir():
        path.unlink()
    if missing:
        catalog.rmdir()
    assert module.main([]) == 1
    assert "catalog" in capsys.readouterr().out
    assert visited == []


@pytest.mark.parametrize("duplicate", [False, True])
def test_unknown_or_duplicate_rule_id_fails(catalog_case, capsys, duplicate):
    module, _, rules, asset_ids, visited = catalog_case
    row = {"asset_id": asset_ids[0], "forbidden_phrases": ["stale phrase"]}
    rows = [row, row] if duplicate else [dict(row, asset_id="scirel.nonexistent.rule")]
    rules.write_text(
        json.dumps({"schema": "scirel.contract-sync-rules", "assets": rows}),
        encoding="utf-8",
    )
    assert module.main([]) == 1
    assert ("duplicate rule" if duplicate else "unknown rule") in capsys.readouterr().out
    assert visited == []


def test_rules_are_options_and_do_not_select_the_checked_assets(catalog_case):
    module, _, rules, asset_ids, visited = catalog_case
    row = {"asset_id": asset_ids[0], "forbidden_phrases": ["stale phrase"]}
    rules.write_text(
        json.dumps({"schema": "scirel.contract-sync-rules", "assets": [row]}),
        encoding="utf-8",
    )
    assert module.main([]) == 0
    assert visited == [row, {"asset_id": asset_ids[1]}]


def test_real_checked_asset_failure_makes_main_red(reader_case, tmp_path, monkeypatch, capsys):
    record, check_record = reader_case
    record["verification"]["known_limitations"].pop()
    assert len(check_record()) == 1
    module = _load()
    rules = tmp_path / "rules.json"
    rules.write_text(
        json.dumps({"schema": "scirel.contract-sync-rules", "assets": []}), encoding="utf-8"
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "RULES", rules, raising=False)
    assert module.main([]) == 1
    output = capsys.readouterr().out
    assert "clause count mismatch at verification.known_limitations" in output
    assert "1 assets, 1 problems" in output


@pytest.mark.parametrize(
    "config",
    [
        [],
        {},
        {"schema": "wrong", "assets": []},
        {"schema": "scirel.contract-sync-rules", "assets": {}},
        {"schema": "scirel.contract-sync-rules", "assets": [], "unknown": []},
    ],
)
def test_invalid_rules_document_fails(catalog_case, capsys, config):
    module, _, rules, _, visited = catalog_case
    rules.write_text(json.dumps(config), encoding="utf-8")
    assert module.main([]) == 1
    assert "invalid contract sync rules" in capsys.readouterr().out
    assert visited == []


@pytest.mark.parametrize("phrases", [None, [], "stale", [""], [1], [False]])
def test_invalid_or_option_free_rule_fails(catalog_case, capsys, phrases):
    module, _, rules, asset_ids, visited = catalog_case
    rules.write_text(
        json.dumps(
            {
                "schema": "scirel.contract-sync-rules",
                "assets": [{"asset_id": asset_ids[0], "forbidden_phrases": phrases}],
            }
        ),
        encoding="utf-8",
    )
    assert module.main([]) == 1
    assert "invalid forbidden_phrases rule" in capsys.readouterr().out
    assert visited == []


@pytest.mark.parametrize("contents", ["{", '{"assets": [], "assets": []}'])
def test_malformed_or_duplicate_json_rules_keys_fail(catalog_case, capsys, contents):
    module, _, rules, _, visited = catalog_case
    rules.write_text(contents, encoding="utf-8")
    assert module.main([]) == 1
    assert "ERROR:" in capsys.readouterr().out
    assert visited == []


def test_explicit_rules_file_is_the_only_rules_source(catalog_case):
    module, _, rules, _, visited = catalog_case
    alternative = rules.with_name("alternative.json")
    rules.rename(alternative)
    assert module.main(["--rules", str(alternative)]) == 0
    assert len(visited) == 2
    visited.clear()
    assert module.main([]) == 1
    assert visited == []


def test_rule_ids_are_validated_even_outside_local_selection(catalog_case, capsys):
    module, _, rules, asset_ids, visited = catalog_case
    rules.write_text(
        json.dumps(
            {
                "schema": "scirel.contract-sync-rules",
                "assets": [{"asset_id": "unknown", "forbidden_phrases": ["stale"]}],
            }
        ),
        encoding="utf-8",
    )
    assert module.main([asset_ids[0]]) == 1
    assert "unknown rule" in capsys.readouterr().out
    assert visited == []


def test_contract_identity_must_match_its_catalog_filename(catalog_case, capsys):
    module, catalog, _, asset_ids, visited = catalog_case
    (catalog / f"{asset_ids[0]}.json").write_text(
        json.dumps({"asset_id": asset_ids[1]}), encoding="utf-8"
    )
    assert module.main([]) == 1
    assert "catalog asset_id must match filename" in capsys.readouterr().out
    assert visited == []


@pytest.mark.parametrize("where", ["contract", "reader record", "docstring"])
def test_real_stale_phrase_failure_makes_main_red(
    reader_case, tmp_path, monkeypatch, capsys, where
):
    _, check_record = reader_case
    assert check_record() == []
    asset_id = "scirel.test.contract-sync"
    phrase = {
        "contract": "Mechanical consistency only.",
        "reader record": "仅检查机械一致性。",
        "docstring": "Return one.",
    }[where]
    rules = tmp_path / "rules.json"
    rules.write_text(
        json.dumps(
            {
                "schema": "scirel.contract-sync-rules",
                "assets": [{"asset_id": asset_id, "forbidden_phrases": [phrase]}],
            }
        ),
        encoding="utf-8",
    )
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "RULES", rules)
    assert module.main([]) == 1
    output = capsys.readouterr().out
    assert f"stale phrase {phrase!r} in the {where}" in output
    assert "1 assets, 1 problems" in output
