"""Exercise the real result helper with hand-computable saved data.

These checks establish statement/data consistency, not physical model validity.
No substitute helper, scientific solver, wheel or transport is involved.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/development/usage/scirel-solving/scripts/delivery.py"


@pytest.fixture(scope="module")
def delivery():
    spec = importlib.util.spec_from_file_location("real_result_delivery", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def case(tmp_path):
    data = tmp_path / "measurements.csv"
    data.write_text("x_s,value\n0,-8\n1,2\n2,4\n3,6\n", encoding="utf-8")
    # Different order and values: comparison must join coordinates, not zip rows.
    reference = tmp_path / "reference.csv"
    reference.write_text("x_s,value\n3,8\n1,2\n0,-10\n2,4\n", encoding="utf-8")
    spec = {
        "schema": "scirel.result-delivery",
        "tables": {
            "measured": {
                "path": data.name,
                "units": {"x_s": "s", "value": "T"},
                "coordinates": ["x_s"],
                "expected_rows": 4,
            }
        },
        "claims": [{"op": "range", "table": "measured", "column": "value"}],
    }
    return SimpleNamespace(
        root=tmp_path,
        data=data,
        reference=reference,
        spec=spec,
        spec_path=tmp_path / "result-spec.json",
        out=tmp_path / "checked",
    )


def _save(case):
    case.spec_path.write_text(json.dumps(case.spec, ensure_ascii=False), encoding="utf-8")
    return case.spec_path


def _relative(case, **options):
    case.spec["claims"] = [
        {"op": "relative_deviation", "table": "measured", "column": "value", "at": {"x_s": 1}}
    ]
    case.spec["claims"][0].update(options)


def _compare(case, **options):
    case.spec["tables"]["reference"] = {
        "path": case.reference.name,
        "units": {"x_s": "s", "value": "T"},
        "coordinates": ["x_s"],
        "expected_rows": 4,
    }
    case.spec["claims"] = [
        {
            "op": "compare",
            "table": "measured",
            "column": "value",
            "reference": "reference",
            "keys": ["x_s"],
            "atol": 1,
            "rtol": 0.125,
        }
    ]
    case.spec["claims"][0].update(options)


def _cli(case, command, *options):
    # The test runner is launched through dev.py; inherit its interpreter and
    # runtime locations when exercising the actual standalone CLI entry point.
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPT),
            command,
            str(case.spec_path),
            "--out",
            str(case.out),
            *map(str, options),
        ],
        cwd=case.root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=False,
    )


def test_four_claims_build_and_replay_saved_data(delivery, case):
    _compare(case)
    comparison = case.spec["claims"][0]
    case.spec["claims"] = [
        {"op": "range", "table": "measured", "column": "value"},
        {"op": "threshold", "table": "measured", "column": "value", "relation": ">=", "value": 4},
        {"op": "relative_deviation", "table": "measured", "column": "value", "at": {"x_s": 1}},
        comparison,
    ]
    result = delivery.build(_save(case), case.out)
    assert result["status"] == "CONSISTENT"
    assert len(result["claims"]) == 4
    bounded, threshold, deviation, compared = result["claims"]
    assert (bounded["min"], bounded["max"], bounded["max_abs"]) == (-8, 6, 8)
    assert (threshold["relation"], threshold["threshold"], threshold["count"]) == (">=", 4, 2)
    assert deviation["reference"] == 2
    assert deviation["max_relative_deviation"] == 5
    assert deviation["sample_coordinates"] == {"x_s": 1}
    assert deviation["extrema"] == [{"x_s": 0}]
    assert compared["passed"] is True
    assert compared["max_absolute_error"] == 2
    assert compared["same_bytes"] is False
    assert all(c["rows"] == 4 and c["unit"] == "T" for c in result["claims"])
    assert result["tables"]["measured"]["coordinates"] == {"x_s": [0, 1, 2, 3]}
    assert result["tables"]["measured"]["units"] == {"x_s": "s", "value": "T"}
    assert result["spec_sha256"] == hashlib.sha256(case.spec_path.read_bytes()).hexdigest()
    assert (
        result["tables"]["measured"]["sha256"] == hashlib.sha256(case.data.read_bytes()).hexdigest()
    )
    assert json.loads((case.out / "checks.json").read_bytes()) == result
    answer = (case.out / "ANSWER.md").read_text(encoding="utf-8")
    assert "最小值 -8，最大值 6，最大绝对值 8" in answer
    assert "数据行为 2/4" in answer
    assert "最大绝对偏差为 500%" in answer
    assert "最大绝对差 2 T，通过" in answer
    assert "单位按输入声明；仅覆盖这些保存数据" in answer
    assert "不证明算法或物理模型独立" in answer
    assert (case.out / "REPORT.md").read_text(encoding="utf-8") == "# 数值结果与检查\n\n" + answer
    assert set(result["artifact_sha256"]) == {"ANSWER.md", "REPORT.md"}
    for name, checksum in result["artifact_sha256"].items():
        assert hashlib.sha256((case.out / name).read_bytes()).hexdigest() == checksum
    assert delivery.verify(case.spec_path, case.out, case.out / "ANSWER.md") == result


@pytest.mark.parametrize("relation,count", [(">", 1), (">=", 2), ("<", 2), ("<=", 3)])
def test_threshold_equality_boundary(delivery, case, relation, count):
    case.spec["claims"] = [
        {
            "op": "threshold",
            "table": "measured",
            "column": "value",
            "relation": relation,
            "value": 4,
        }
    ]
    result, _ = delivery.evaluate(_save(case), case.out)
    assert result["claims"][0]["count"] == count
    assert result["status"] == "CONSISTENT"


def test_zero_threshold_count_is_not_a_failed_comparison(delivery, case):
    case.spec["claims"] = [
        {"op": "threshold", "table": "measured", "column": "value", "relation": ">", "value": 6}
    ]
    result, artifacts = delivery.evaluate(_save(case), case.out)
    assert result["claims"][0]["count"] == 0
    assert result["status"] == "CONSISTENT"
    assert "0/4；没有满足该条件的数据行" in artifacts["ANSWER.md"].decode()


@pytest.mark.parametrize("rtol,passed", [(0.125, True), (0.0625, False)])
def test_comparison_uses_reference_magnitude_and_inclusive_tolerance(delivery, case, rtol, passed):
    # At x=3: |6-8| = 2; 1 + (1/8)*|8| = 2 exactly.
    # Using |actual|, dropping atol, or zipping the reordered rows must fail.
    _compare(case, rtol=rtol)
    result = delivery.build(_save(case), case.out)
    assert result["claims"][0]["passed"] is passed
    assert result["claims"][0]["max_absolute_error"] == 2
    assert result["status"] == ("CONSISTENT" if passed else "CHECK_FAILED")
    assert delivery.verify(case.spec_path, case.out) == result
    answer = (case.out / "ANSWER.md").read_text(encoding="utf-8")
    assert ("最大绝对差 2 T，通过" if passed else "最大绝对差 2 T，未通过") in answer
    if not passed:
        assert "有数据比较未通过" in answer
        assert "已核对下列数值陈述与保存数据一致" not in answer


def test_identical_tables_are_marked_as_same_bytes(delivery, case):
    _compare(case, atol=0, rtol=0)
    case.reference.write_bytes(case.data.read_bytes())
    result, artifacts = delivery.evaluate(_save(case), case.out)
    assert result["claims"][0]["passed"] is True
    assert result["claims"][0]["same_bytes"] is True
    assert result["claims"][0]["max_absolute_error"] == 0
    assert "两表字节相同" in artifacts["ANSWER.md"].decode()
    assert "不证明算法或物理模型独立" in artifacts["ANSWER.md"].decode()


@pytest.mark.parametrize(
    "rtol,code,status", [(0.125, 0, "CONSISTENT"), (0.0625, 3, "CHECK_FAILED")]
)
def test_real_cli_build_verify_exit_codes(case, rtol, code, status):
    _compare(case, rtol=rtol)
    _save(case)
    built = _cli(case, "build")
    assert built.returncode == code, (built.stdout, built.stderr)
    assert json.loads(built.stdout)["status"] == status
    replay = _cli(case, "verify", "--answer", case.out / "ANSWER.md")
    assert replay.returncode == code, (replay.stdout, replay.stderr)
    response = json.loads(replay.stdout)
    assert response["status"] == status
    assert response["answer_text"] == (case.out / "ANSWER.md").read_text(encoding="utf-8")


def test_cli_invalid_input_returns_two_without_a_report(case):
    case.data.write_text("x_s,value\n0,NaN\n", encoding="utf-8")
    _save(case)
    result = _cli(case, "build")
    assert result.returncode == 2, (result.stdout, result.stderr)
    response = json.loads(result.stdout)
    assert response["status"] == "INVALID"
    assert "nonfinite measurement" in response["error"]
    assert not case.out.exists()


@pytest.mark.parametrize(
    "csv,error",
    [
        ("x_s,value,value\n0,1,2\n", "duplicate/missing CSV headers"),
        ("", "duplicate/missing CSV headers"),
        ("x_s,other\n0,2\n", "declared column absent"),
        ("x_s,value\n", "empty/ragged CSV"),
        ("x_s,value\n0\n", "empty/ragged CSV"),
        ("x_s,value\n0,1,2\n", "empty/ragged CSV"),
        ("x_s,value\n0,\n", "could not convert string to float"),
    ],
    ids=[
        "duplicate-header",
        "no-header",
        "missing-column",
        "no-rows",
        "short-row",
        "long-row",
        "empty-value",
    ],
)
def test_invalid_csv_is_rejected_before_writing(delivery, case, csv, error):
    case.data.write_text(csv, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        delivery.build(_save(case), case.out)
    assert not case.out.exists()


@pytest.mark.parametrize("token", ["True", "False", "NaN", "inf", "-inf", "1e999"])
@pytest.mark.parametrize("column", ["x_s", "value"])
def test_csv_boolean_and_nonfinite_measurements_rejected(delivery, case, token, column):
    row = f"{token},2" if column == "x_s" else f"0,{token}"
    case.data.write_text("x_s,value\n" + row + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        delivery.build(_save(case), case.out)
    assert not case.out.exists()


@pytest.mark.parametrize("bad", [True, False, "NaN", "inf", "-inf"])
@pytest.mark.parametrize(
    "location",
    ["threshold", "reference-coordinate", "coordinate-atol", "atol", "rtol", "group-coordinate"],
)
def test_spec_boolean_and_nonfinite_numbers_rejected(delivery, case, bad, location):
    if location == "threshold":
        case.spec["claims"] = [
            {
                "op": "threshold",
                "table": "measured",
                "column": "value",
                "relation": ">",
                "value": bad,
            }
        ]
    elif location in {"reference-coordinate", "coordinate-atol"}:
        _relative(case)
        case.spec["claims"][0][
            "at" if location == "reference-coordinate" else "coordinate_atol"
        ] = {"x_s": bad} if location == "reference-coordinate" else bad
    elif location in {"atol", "rtol"}:
        _compare(case, **{location: bad})
    else:
        case.spec["tables"]["measured"]["expected_groups"] = {
            "columns": ["x_s"],
            "values": [[bad]],
            "rows_each": 4,
        }
    with pytest.raises(ValueError, match="boolean is not a measurement|nonfinite measurement"):
        delivery.build(_save(case), case.out)
    assert not case.out.exists()


@pytest.mark.parametrize("column,unit", [("value", "1"), ("value", "kg*m/s^2"), ("value", "T")])
def test_declared_scientific_units_are_preserved(delivery, case, column, unit):
    case.spec["tables"]["measured"]["units"][column] = unit
    result, artifacts = delivery.evaluate(_save(case), case.out)
    assert result["claims"][0]["unit"] == unit
    assert result["claims"][0]["min"] == -8
    assert f"value（{unit}，全部 4 行）" in artifacts["ANSWER.md"].decode()


@pytest.mark.parametrize("unit", ["", "特斯拉", "T\nextra claim", "<script>", 1, True])
def test_invalid_unit_declarations_rejected(delivery, case, unit):
    case.spec["tables"]["measured"]["units"]["value"] = unit
    with pytest.raises(ValueError, match="unit must be a short scientific unit expression"):
        delivery.build(_save(case), case.out)


@pytest.mark.parametrize(
    "change",
    ["no-units", "undeclared-measurement", "undeclared-coordinate", "duplicate-coordinate"],
)
def test_every_used_column_needs_a_unit_and_valid_coordinates(delivery, case, change):
    declaration = case.spec["tables"]["measured"]
    if change == "no-units":
        declaration["units"] = {}
    elif change == "undeclared-measurement":
        del declaration["units"]["value"]
    elif change == "undeclared-coordinate":
        declaration["coordinates"] = ["other"]
    else:
        declaration["coordinates"] = ["x_s", "x_s"]
    with pytest.raises((ValueError, KeyError)):
        delivery.build(_save(case), case.out)
    assert not case.out.exists()


def test_unused_extra_csv_column_is_allowed(delivery, case):
    case.data.write_text("x_s,value,note\n0,-8,a\n1,2,b\n2,4,c\n3,6,d\n", encoding="utf-8")
    result, _ = delivery.evaluate(_save(case), case.out)
    assert result["claims"][0]["min"] == -8
    assert result["tables"]["measured"]["rows"] == 4


@pytest.mark.parametrize("expected", [3, 5])
def test_row_coverage_must_equal_declared_count(delivery, case, expected):
    case.spec["tables"]["measured"]["expected_rows"] = expected
    with pytest.raises(ValueError, match="coverage: row count mismatch"):
        delivery.build(_save(case), case.out)


@pytest.mark.parametrize(
    "change",
    [
        "valid",
        "missing-group",
        "extra-group",
        "wrong-multiplicity",
        "duplicate-expected",
        "wrong-width",
        "non-coordinate",
    ],
)
def test_coordinate_groups_require_exact_set_and_multiplicity(delivery, case, change):
    case.data.write_text("x_s,group_id,value\n0,0,-8\n1,0,2\n0,1,4\n1,1,6\n", encoding="utf-8")
    table = case.spec["tables"]["measured"]
    table["units"]["group_id"] = "1"
    table["coordinates"] = ["x_s", "group_id"]
    groups = {"columns": ["group_id"], "values": [[0], [1]], "rows_each": 2}
    table["expected_groups"] = groups
    error = "coverage: group mismatch"
    if change == "missing-group":
        groups["values"] = [[0]]
    elif change == "extra-group":
        groups["values"].append([2])
    elif change == "wrong-multiplicity":
        groups["rows_each"] = 1
    elif change == "duplicate-expected":
        groups["values"] = [[0], [0]]
        error = "invalid expected groups"
    elif change == "wrong-width":
        groups["values"] = [[0, 1], [1, 1]]
        error = "invalid expected groups"
    elif change == "non-coordinate":
        groups["columns"] = ["value"]
        error = "group keys must be coordinates"
    if change == "valid":
        result = delivery.build(_save(case), case.out)
        assert result["tables"]["measured"]["rows"] == 4
        assert result["tables"]["measured"]["coordinates"] == {"x_s": [0, 1], "group_id": [0, 1]}
    else:
        with pytest.raises(ValueError, match=error):
            delivery.build(_save(case), case.out)


@pytest.mark.parametrize(
    "at,tolerance,error",
    [
        ({}, 0, "invalid reference coordinates"),
        ({"value": 2}, 0, "invalid reference coordinates"),
        ({"x_s": 1}, -0.1, "invalid reference coordinates"),
        ({"x_s": 1.125}, 0, "reference coordinate must identify exactly one saved row"),
        ({"x_s": 1}, 1, "reference coordinate must identify exactly one saved row"),
    ],
)
def test_relative_reference_must_select_exactly_one_coordinate(
    delivery, case, at, tolerance, error
):
    _relative(case, at=at, coordinate_atol=tolerance)
    with pytest.raises(ValueError, match=error):
        delivery.build(_save(case), case.out)


def test_reference_coordinate_tolerance_reports_actual_sample(delivery, case):
    _relative(case, at={"x_s": 1.125}, coordinate_atol=0.125)
    result, artifacts = delivery.evaluate(_save(case), case.out)
    claim = result["claims"][0]
    assert claim["at"] == {"x_s": 1.125}
    assert claim["sample_coordinates"] == {"x_s": 1}
    assert claim["reference"] == 2
    assert claim["max_relative_deviation"] == 5
    assert "参考值为 2 T" in artifacts["ANSWER.md"].decode()


def test_relative_reference_rejects_duplicate_matching_rows(delivery, case):
    _relative(case)
    case.data.write_text("x_s,value\n0,-8\n1,2\n1,4\n3,6\n", encoding="utf-8")
    with pytest.raises(
        ValueError, match="reference coordinate must identify exactly one saved row"
    ):
        delivery.build(_save(case), case.out)


def test_zero_relative_reference_rejected(delivery, case):
    _relative(case, at={"x_s": 1})
    case.data.write_text("x_s,value\n0,-8\n1,0\n2,4\n3,6\n", encoding="utf-8")
    with pytest.raises(ValueError, match="relative deviation undefined for zero reference"):
        delivery.build(_save(case), case.out)


def test_negative_reference_and_tied_extrema_are_reported(delivery, case):
    _relative(case, at={"x_s": 0})
    case.data.write_text("x_s,value\n0,-2\n1,2\n2,-6\n3,-2\n", encoding="utf-8")
    result, _ = delivery.evaluate(_save(case), case.out)
    claim = result["claims"][0]
    assert claim["reference"] == -2
    assert claim["max_relative_deviation"] == 2
    assert claim["extrema"] == [{"x_s": 1}, {"x_s": 2}]


@pytest.mark.parametrize("field", ["atol", "rtol"])
def test_negative_comparison_tolerances_rejected(delivery, case, field):
    _compare(case, **{field: -0.125})
    with pytest.raises(ValueError, match="negative tolerance"):
        delivery.build(_save(case), case.out)


@pytest.mark.parametrize("column", ["x_s", "value"])
def test_comparison_rejects_unit_mismatch_without_conversion(delivery, case, column):
    _compare(case)
    case.spec["tables"]["reference"]["units"][column] = "ms" if column == "x_s" else "mT"
    with pytest.raises(ValueError, match="comparison unit mismatch"):
        delivery.build(_save(case), case.out)


@pytest.mark.parametrize(
    "side,rows",
    [
        ("measured", "0,-8\n1,2\n1,4\n3,6\n"),
        ("reference", "0,-8\n1,2\n1,4\n3,6\n"),
        ("reference", "0,-8\n1,2\n2,4\n4,6\n"),
        ("reference", "0,-8\n1,2\n2,4\n"),
    ],
)
def test_comparison_requires_complete_unique_keys(delivery, case, side, rows):
    _compare(case)
    # Let comparison itself establish coverage, without the optional row guard.
    del case.spec["tables"][side]["expected_rows"]
    path = case.data if side == "measured" else case.reference
    path.write_text("x_s,value\n" + rows, encoding="utf-8")
    with pytest.raises(
        ValueError, match="coverage: comparison keys must match uniquely and completely"
    ):
        delivery.build(_save(case), case.out)


@pytest.mark.parametrize("keys", [[], ["value"], ["x_s", "x_s"]])
def test_comparison_keys_must_be_unique_declared_coordinates(delivery, case, keys):
    _compare(case, keys=keys)
    with pytest.raises(ValueError, match="comparison needs coordinate keys"):
        delivery.build(_save(case), case.out)


def test_comparison_keys_must_also_be_reference_coordinates(delivery, case):
    _compare(case)
    case.spec["tables"]["reference"]["coordinates"] = []
    with pytest.raises(ValueError, match="reference coordinate mismatch"):
        delivery.build(_save(case), case.out)


def test_original_multiline_premise_is_quoted_and_bound(delivery, case):
    source = case.root / "request.txt"
    quote = "只核对保存的数据。\n不推断模型适用性。"
    source.write_bytes(("用户要求：\n" + quote + "\n").encode("utf-8"))
    case.spec["premises"] = [{"path": source.name, "quote": quote}]
    result, artifacts = delivery.evaluate(_save(case), case.out)
    assert result["premises"] == [
        {"quote": quote, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    ]
    assert "> 只核对保存的数据。\n> 不推断模型适用性。" in artifacts["ANSWER.md"].decode()


@pytest.mark.parametrize("quote", ["未提供的工程验收条件", "", "   ", True])
def test_unprovided_premise_is_rejected(delivery, case, quote):
    (case.root / "request.txt").write_text("只核对保存的数据。\n", encoding="utf-8")
    case.spec["premises"] = [{"path": "request.txt", "quote": quote}]
    with pytest.raises(ValueError, match="unprovided premise"):
        delivery.build(_save(case), case.out)


@pytest.mark.parametrize(
    "target", ["data", "spec", "checks", "answer", "report", "premise", "missing-report"]
)
def test_replay_rejects_changed_inputs_records_and_artifacts(delivery, case, target):
    premise = case.root / "request.txt"
    premise.write_text("只核对保存的数据。\n", encoding="utf-8")
    case.spec["premises"] = [{"path": premise.name, "quote": "只核对保存的数据。"}]
    delivery.build(_save(case), case.out)
    if target == "data":
        # Reordering leaves range and coverage unchanged: source bytes are bound.
        case.data.write_text("x_s,value\n3,6\n2,4\n1,2\n0,-8\n", encoding="utf-8")
    elif target == "spec":
        case.spec_path.write_bytes(case.spec_path.read_bytes() + b"\n")
    elif target == "checks":
        path = case.out / "checks.json"
        record = json.loads(path.read_bytes())
        record["claims"][0]["max"] = 600
        path.write_text(json.dumps(record), encoding="utf-8")
    elif target == "premise":
        premise.write_text("只核对保存的数据。\n新增条件。\n", encoding="utf-8")
    elif target == "missing-report":
        (case.out / "REPORT.md").unlink()
    else:
        path = case.out / ("ANSWER.md" if target == "answer" else "REPORT.md")
        path.write_bytes(path.read_bytes() + "\n额外结论：模型已获验证。\n".encode())
    protected = {p.name: p.read_bytes() for p in case.out.iterdir()}
    with pytest.raises((ValueError, OSError)):
        delivery.verify(case.spec_path, case.out)
    assert {p.name: p.read_bytes() for p in case.out.iterdir()} == protected
    replay = _cli(case, "verify")
    assert replay.returncode == 2, (replay.stdout, replay.stderr)
    assert json.loads(replay.stdout)["status"] == "INVALID"


def test_external_answer_allows_terminal_newline_but_rejects_changed_claims(delivery, case):
    delivery.build(_save(case), case.out)
    answer = case.out / "ANSWER.md"
    draft = case.root / "draft.md"
    body = answer.read_text(encoding="utf-8")
    draft.write_text(body.rstrip("\n"), encoding="utf-8")
    assert delivery.verify(case.spec_path, case.out, draft)["status"] == "CONSISTENT"
    draft.write_text(body.replace("最小值 -8", "最小值 -80"), encoding="utf-8")
    with pytest.raises(ValueError, match="answer contains unverified edits or claims"):
        delivery.verify(case.spec_path, case.out, draft)
    replay = _cli(case, "verify", "--answer", draft)
    assert replay.returncode == 2, (replay.stdout, replay.stderr)
    assert "answer contains unverified edits or claims" in json.loads(replay.stdout)["error"]


@pytest.mark.parametrize(
    "source,filename",
    [
        ("table", "ANSWER.md"),
        ("table", "REPORT.md"),
        ("table", "checks.json"),
        ("premise", "ANSWER.md"),
        ("premise", "REPORT.md"),
        ("premise", "checks.json"),
        ("spec", "checks.json"),
    ],
)
def test_output_cannot_overwrite_declared_inputs(delivery, case, source, filename):
    case.out.mkdir()
    collision = case.out / filename
    if source == "table":
        collision.write_bytes(case.data.read_bytes())
        case.spec["tables"]["measured"]["path"] = f"checked/{filename}"
    elif source == "premise":
        collision.write_text("只核对保存的数据。", encoding="utf-8")
        case.spec["premises"] = [{"path": f"checked/{filename}", "quote": "只核对保存的数据。"}]
    else:
        case.spec_path = collision
        case.spec["tables"]["measured"]["path"] = "../measurements.csv"
    _save(case)
    before = {p: p.read_bytes() for p in case.root.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="output would overwrite input"):
        delivery.build(case.spec_path, case.out)
    assert {p: p.read_bytes() for p in case.root.rglob("*") if p.is_file()} == before
    built = _cli(case, "build")
    assert built.returncode == 2, (built.stdout, built.stderr)
    assert "output would overwrite input" in json.loads(built.stdout)["error"]
    assert {p: p.read_bytes() for p in case.root.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize(
    "change",
    [
        "schema",
        "unsupported-op",
        "free-claim",
        "unknown-table",
        "unknown-column",
        "bad-relation",
        "no-claims",
        "no-tables",
    ],
)
def test_bad_specification_does_not_generate_a_report(delivery, case, change):
    claim = case.spec["claims"][0]
    if change == "schema":
        case.spec["schema"] = "unrecognized"
    elif change == "unsupported-op":
        claim["op"] = "certify_physics"
    elif change == "free-claim":
        claim["verified_conclusion"] = "model is valid"
    elif change == "unknown-table":
        claim["table"] = "absent"
    elif change == "unknown-column":
        claim["column"] = "absent"
    elif change == "bad-relation":
        claim.update(op="threshold", relation="==", value=2)
    elif change == "no-claims":
        case.spec["claims"] = []
    else:
        case.spec["tables"] = {}
    _save(case)
    result = _cli(case, "build")
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert json.loads(result.stdout)["status"] == "INVALID"
    assert not case.out.exists()


def test_overflow_in_derived_deviation_cannot_become_a_report(delivery, case):
    _relative(case, at={"x_s": 0})
    case.data.write_text("x_s,value\n0,1e-300\n1,1e300\n2,2\n3,3\n", encoding="utf-8")
    with pytest.raises(ValueError):
        delivery.build(_save(case), case.out)
    assert not case.out.exists()
