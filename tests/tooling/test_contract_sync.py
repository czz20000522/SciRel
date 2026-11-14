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
    assert module.digest_error(record, "a" * 64, "zh_physics.json") is None


def test_an_extra_clause_is_reported_as_more_on_the_reader_side():
    module = _load()
    document, record = _contract_and_record(applicability__excluded=["丁", "戊", "己", "庚"])
    errors = module.clause_errors(document, record)
    assert len(errors) == 1
    assert "applicability.excluded" in errors[0]
    assert "3 clause" in errors[0] and "4 " in errors[0]
    assert "more on the reader side" in errors[0]
    assert module.digest_error(record, "a" * 64, "zh_physics.json") is None


def test_equal_counts_with_a_misspelt_key_are_still_rejected():
    module = _load()
    document, record = _contract_and_record()
    record["verification"]["known_limitation"] = ["误拼写的额外字段"]
    errors = module.clause_errors(document, record)
    assert len(errors) == 1
    assert "verification.known_limitation:" in errors[0]
    assert "clause count" not in errors[0]
    assert module.digest_error(record, "a" * 64, "zh_physics.json") is None


def test_a_stale_digest_is_reported_separately_from_clause_counts():
    module = _load()
    document, record = _contract_and_record()
    record["source_sha256"] = "b" * 64
    message = module.digest_error(record, "a" * 64, "zh_physics.json")
    assert message is not None
    assert "zh_physics.json" in message
    assert "source_sha256" in message
    assert "reader " + "b" * 64 + " vs contract " + "a" * 64 in message
    assert module.clause_errors(document, record) == []


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


@pytest.mark.parametrize(
    "section,key",
    [
        ("applicability", "preconditions"),
        ("applicability", "supported"),
        ("applicability", "excluded"),
        ("verification", "scope"),
        ("verification", "known_limitations"),
    ],
)
@pytest.mark.parametrize("delta", [-1, 1])
def test_each_translated_clause_list_has_its_own_count(section, key, delta):
    module = _load()
    document, record = _contract_and_record()
    expected = len(document[section][key])
    if delta < 0:
        record[section][key].pop()
    else:
        record[section][key].append("额外条款")
    errors = module.clause_errors(document, record)
    assert len(errors) == 1
    assert f"{section}.{key}" in errors[0]
    assert f"contract has {expected} clause(s)" in errors[0]
    assert f"reader record has {expected + delta} " in errors[0]


def test_contract_owns_clause_fields_and_evidence_tests_are_not_translated():
    module = _load()
    document, record = _contract_and_record()
    assert module.clause_errors(document, record) == []
    document["verification"]["additional_scope"] = ["contract-owned clause"]
    record["verification"]["additional_scope"] = []
    errors = module.clause_errors(document, record)
    assert len(errors) == 1
    assert "verification.additional_scope" in errors[0]
    record["verification"]["additional_scope"] = ["合同派生的条款"]
    assert module.clause_errors(document, record) == []


@pytest.mark.parametrize("value", [None, "丙", {"丙": "wrong type"}, 1])
def test_clause_values_must_be_lists_even_when_their_length_would_match(value):
    module = _load()
    document, record = _contract_and_record(applicability__supported=value)
    errors = module.clause_errors(document, record)
    assert len(errors) == 1
    assert "applicability.supported" in errors[0]
    assert "contract has 1 clause(s)" in errors[0]
    assert "expected a list" in errors[0]


def test_a_missing_empty_clause_field_cannot_silently_match_zero():
    module = _load()
    document, record = _contract_and_record()
    document["applicability"]["excluded"] = []
    record["applicability"].pop("excluded")
    errors = module.clause_errors(document, record)
    assert len(errors) == 1
    assert "applicability.excluded" in errors[0]
    assert "contract has 0 clause(s)" in errors[0]
    assert "no field" in errors[0]


@pytest.mark.parametrize("value", [None, [], "invalid"])
def test_invalid_reader_section_is_reported_without_crashing(value):
    module = _load()
    document, record = _contract_and_record()
    record["verification"] = value
    errors = module.clause_errors(document, record)
    assert errors == ["invalid reader section at verification: expected an object"]


@pytest.mark.parametrize("value", [None, 1, False, [], {}])
def test_invalid_digest_is_reported_without_crashing(value):
    module = _load()
    _, record = _contract_and_record()
    record["source_sha256"] = value
    message = module.digest_error(record, "a" * 64, "zh_physics.json")
    assert message is not None
    assert "zh_physics.json" in message and "source_sha256" in message


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


@pytest.mark.parametrize("change", ["fewer", "more", "digest", "key", "both"])
def test_check_reports_independent_reader_failures_with_asset_and_file(reader_case, change):
    record, check_record = reader_case
    if change in {"fewer", "both"}:
        record["verification"]["known_limitations"].pop()
    elif change == "more":
        record["verification"]["known_limitations"].append("额外条款")
    elif change == "key":
        record["verification"]["known_limitation"] = ["拼错字段"]
    if change in {"digest", "both"}:
        record["source_sha256"] = "0" * 64
    errors = check_record()
    assert len(errors) == (2 if change == "both" else 1)
    assert all("scirel.test.contract-sync: zh_test.json" in error for error in errors)
    assert sum("source_sha256" in error for error in errors) == int(change in {"digest", "both"})
    assert sum("clause count" in error for error in errors) == int(
        change in {"fewer", "more", "both"}
    )
    if change in {"fewer", "more", "both"}:
        count_error = next(error for error in errors if "clause count" in error)
        assert "verification.known_limitations" in count_error
        assert "contract has 1 clause(s)" in count_error
        assert f"reader record has {2 if change == 'more' else 0} " in count_error
    if change == "key":
        assert "verification.known_limitation:" in errors[0]


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
