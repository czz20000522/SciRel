"""The Chinese pairing sidecar names the drifted field and cannot be satisfied by a blob hash."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import zh_pairs  # noqa: E402

ASSET = "scirel.test.asset"
OTHER = "scirel.test.other"
SIDECAR = "tools/docs/zh-pairing.json"


def contract(asset: str = ASSET) -> dict:
    return {
        "schema": "scirel.asset-document",
        "asset_id": asset,
        "title": {"en": "Test asset", "zh": "测试资产"},
        "summary": "Sums a declared profile.",
        "identity": {
            "relation": "A declared sum",
            "definition": "S=sum(p*v).",
            "model": "Bounded arithmetic.",
            "geometry": "generic",
            "coordinates": "generic",
            "boundary": "Nonempty declared vectors.",
            "assumptions": ["Inputs are finite", "Weights are positive"],
        },
        "inputs": [{"name": "p", "description": "Pressure", "units": "Pa", "required": True}],
        "outputs": [{"name": "s", "description": "Sum", "units": "N", "required": True}],
        "applicability": {
            "preconditions": ["Declared"],
            "supported": ["Sums"],
            "excluded": ["Nothing"],
        },
        "failure_semantics": {
            "invalid_input": "ValueError for nonfinite input.",
            "runtime_failure": "Propagates.",
            "nonconvergence": "Not applicable.",
            "partial_results": "None.",
        },
        "family": {
            "name": "test-family",
            "default": "a",
            "default_reason": "declared",
            "methods": [{"name": "a", "model": "Declared method."}],
        },
        "example": {"description": "One case.", "code": "pass", "expected": "finite"},
        "verification": {"scope": ["Declared checks."], "tests": ["tests/x.py"]},
    }


def record(asset: str = ASSET) -> dict:
    return {
        "asset_id": asset,
        "source_sha256": "0" * 64,
        "summary": "对声明剖面求和。",
        "definition": "S=sum(p*v)。",
        "model": "有界算术。",
        "assumptions": ["输入有限", "权重为正"],
        "boundary": "非空声明向量。",
        "inputs": [{"name": "p", "description": "压力"}],
        "outputs": [{"name": "s", "description": "求和"}],
        "applicability": {"preconditions": ["已声明"], "supported": ["求和"], "excluded": ["无"]},
        "failure_semantics": {
            "invalid_input": "非有限输入抛 ValueError。",
            "runtime_failure": "继续传播。",
            "nonconvergence": "不适用。",
            "partial_results": "无。",
        },
        "family": {
            "name": "test-family",
            "default": "a",
            "default_reason": "已声明",
            "methods": [{"name": "a", "model": "已声明方法。"}],
        },
        "example": {"description": "一个用例。", "expected": "有限"},
        "verification": {"scope": ["已声明检查。"], "tests": ["tests/x.py"]},
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "catalog" / "examples").mkdir(parents=True)
    (tmp_path / "tools" / "docs" / "zh").mkdir(parents=True)
    for asset in (ASSET, OTHER):
        write_contract(tmp_path, contract(asset), asset)
    zh = {
        "schema": "scirel.reader-translation",
        "language": "zh-CN",
        "records": [record(ASSET), record(OTHER)],
    }
    (tmp_path / "tools" / "docs" / "zh" / "zh_test.json").write_text(
        json.dumps(zh, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return tmp_path


def read_zh(root: Path) -> dict:
    return json.loads((root / "tools" / "docs" / "zh" / "zh_test.json").read_text(encoding="utf-8"))


def write_zh(root: Path, document: dict) -> None:
    (root / "tools" / "docs" / "zh" / "zh_test.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def read_contract(root: Path, asset: str = ASSET) -> dict:
    return json.loads((root / "catalog" / "examples" / f"{asset}.json").read_text(encoding="utf-8"))


def write_contract(root: Path, document: dict, asset: str = ASSET) -> None:
    (root / "catalog" / "examples" / f"{asset}.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def sidecar(root: Path) -> dict:
    return json.loads((root / SIDECAR).read_text(encoding="utf-8"))


def write_sidecar(root: Path, document: dict) -> None:
    (root / SIDECAR).write_text(
        json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def entry(document: dict, asset: str = ASSET) -> dict:
    return next(item for item in document["records"] if item["asset_id"] == asset)


def run(root: Path, capsys, *args: str) -> tuple[int, str]:
    code = zh_pairs.main(["--repo", str(root), *args])
    return code, capsys.readouterr().out


def record_pairing(root: Path) -> None:
    assert zh_pairs.main(["--repo", str(root), "--write"]) == 0


def test_a_fresh_pair_passes(repo, capsys):
    record_pairing(repo)
    code, out = run(repo, capsys)
    assert code == 0, out
    assert "pair with their contracts" in out
    assert (repo / SIDECAR).is_file()


def test_a_contract_field_change_names_that_field(repo, capsys):
    record_pairing(repo)
    document = read_contract(repo)
    document["identity"]["definition"] = "S=sum(p*v)/2."
    write_contract(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "contract field 'definition' changed" in out
    assert ASSET in out


def test_a_translation_change_without_rerecording_is_rejected(repo, capsys):
    record_pairing(repo)
    document = read_zh(repo)
    document["records"][0]["summary"] = "对声明剖面求和（已修改）。"
    write_zh(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "Chinese text of field 'summary' changed" in out


def test_a_missing_sidecar_file_is_a_clear_failure(repo, capsys):
    code, out = run(repo, capsys)
    assert code == 1
    assert "file is missing" in out
    assert "run --write" in out


def test_an_asset_missing_from_the_sidecar_is_rejected(repo, capsys):
    """Removing an entry must not silently downgrade that asset to a weaker check."""
    record_pairing(repo)
    document = sidecar(repo)
    document["records"] = [item for item in document["records"] if item["asset_id"] != OTHER]
    write_sidecar(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert OTHER in out
    assert "no recorded pair" in out
    assert "not an unmigrated pass" in out


def test_an_in_record_block_does_not_rescue_a_missing_sidecar_entry(repo, capsys):
    record_pairing(repo)
    zh = read_zh(repo)
    for item in zh["records"]:
        item["pairing"] = {
            "schema": "scirel.zh-pairing",
            "version": 1,
            "sections": {"summary": {"en": "0" * 16, "zh": "1" * 16}},
        }
    write_zh(repo, zh)
    document = sidecar(repo)
    document["records"] = [item for item in document["records"] if item["asset_id"] != OTHER]
    write_sidecar(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "no recorded pair" in out


def test_a_contract_without_a_chinese_record_is_rejected(repo, capsys):
    record_pairing(repo)
    zh = read_zh(repo)
    zh["records"] = [item for item in zh["records"] if item["asset_id"] != OTHER]
    write_zh(repo, zh)
    code, out = run(repo, capsys)
    assert code == 1
    assert OTHER in out
    assert "has no Chinese record" in out


def test_changing_family_is_red_and_names_it(repo, capsys):
    record_pairing(repo)
    document = read_contract(repo)
    document["family"] = {
        "name": "changed-family",
        "default": "a",
        "default_reason": "changed",
        "methods": [{"name": "a", "model": "changed"}],
    }
    write_contract(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "field 'family'" in out


def test_a_title_that_stops_copying_the_contract_title_is_rejected(repo, capsys):
    record_pairing(repo)
    zh = read_zh(repo)
    zh["records"][0]["title"] = {"en": "Renamed", "zh": "改名了"}
    write_zh(repo, zh)
    code, out = run(repo, capsys)
    assert code == 1
    assert "field 'title' must copy the contract value exactly" in out


def test_a_drifted_asset_is_red_even_when_another_is_unmigrated(repo, capsys):
    record_pairing(repo)
    document = sidecar(repo)
    document["records"] = [item for item in document["records"] if item["asset_id"] != OTHER]
    write_sidecar(repo, document)
    readme = read_contract(repo)
    readme["identity"]["model"] = "Different arithmetic."
    write_contract(repo, readme)
    code, out = run(repo, capsys)
    assert code == 1
    assert "contract field 'model' changed" in out


def test_a_field_the_record_no_longer_translates_is_rejected(repo, capsys):
    record_pairing(repo)
    document = sidecar(repo)
    entry(document)["fields"]["geometry"] = {"en": "a" * 16, "zh": "b" * 16}
    write_sidecar(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "fields the record no longer translates" in out


def test_a_field_missing_from_the_sidecar_entry_is_rejected(repo, capsys):
    record_pairing(repo)
    document = sidecar(repo)
    del entry(document)["fields"]["verification"]
    write_sidecar(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "field 'verification' has no recorded hash" in out


def test_a_forged_hash_is_rejected(repo, capsys):
    record_pairing(repo)
    document = sidecar(repo)
    entry(document)["fields"]["model"]["en"] = "f" * 16
    write_sidecar(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "contract field 'model' changed" in out


def test_a_pair_without_a_chinese_record_is_rejected(repo, capsys):
    record_pairing(repo)
    document = sidecar(repo)
    document["records"].append(
        {"asset_id": "scirel.absent.asset", "fields": {"summary": {"en": "a" * 16, "zh": "b" * 16}}}
    )
    write_sidecar(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "has no Chinese record" in out


def test_a_duplicate_asset_in_the_sidecar_is_rejected(repo, capsys):
    record_pairing(repo)
    document = sidecar(repo)
    document["records"].append(dict(entry(document)))
    write_sidecar(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "duplicate asset_id" in out


def test_a_record_without_a_contract_is_rejected(repo, capsys):
    document = read_zh(repo)
    document["records"][0]["asset_id"] = "scirel.absent.asset"
    write_zh(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "no contract" in out


def test_the_sidecar_wins_over_an_in_record_block(repo, capsys):
    """A stale in-record block from the first format must not mask a correct sidecar."""
    document = read_zh(repo)
    for item in document["records"]:
        item["pairing"] = {
            "schema": "scirel.zh-pairing",
            "version": 1,
            "sections": {"summary": {"en": "0" * 16, "zh": "1" * 16}},
        }
    write_zh(repo, document)
    record_pairing(repo)
    code, out = run(repo, capsys)
    assert code == 0, out


def test_the_sidecar_is_not_masked_by_a_correct_in_record_block(repo, capsys):
    document = read_zh(repo)
    for item in document["records"]:
        item["pairing"] = {
            "schema": "scirel.zh-pairing",
            "version": 1,
            "sections": {"summary": {"en": "0" * 16, "zh": "1" * 16}},
        }
    write_zh(repo, document)
    record_pairing(repo)
    broken = sidecar(repo)
    entry(broken)["fields"]["summary"]["zh"] = "e" * 16
    write_sidecar(repo, broken)
    code, out = run(repo, capsys)
    assert code == 1
    assert "Chinese text of field 'summary' changed" in out


def test_the_sidecar_is_sorted_one_record_per_line_and_idempotent(repo):
    record_pairing(repo)
    text = (repo / SIDECAR).read_text(encoding="utf-8")
    body = [line for line in text.splitlines() if line.startswith("  {")]
    assert len(body) == 2
    assert body[0].count('"asset_id"') == 1
    assert ASSET in body[0] and OTHER in body[1]
    assert text.startswith('{\n "schema": "scirel.zh-pairing"')
    record_pairing(repo)
    assert (repo / SIDECAR).read_text(encoding="utf-8") == text


def test_write_refreshes_a_stale_pair(repo, capsys):
    record_pairing(repo)
    document = read_contract(repo)
    document["summary"] = "Sums a declared profile onto a grid."
    write_contract(repo, document)
    code, _out = run(repo, capsys)
    assert code == 1
    record_pairing(repo)
    code, out = run(repo, capsys)
    assert code == 0, out


def test_list_reports_the_drifted_fields(repo, capsys):
    record_pairing(repo)
    document = read_contract(repo)
    document["identity"]["model"] = "Different bounded arithmetic."
    write_contract(repo, document)
    code, out = run(repo, capsys, "--list")
    assert code == 1
    assert "drift:model" in out


def test_the_legacy_blob_check_would_have_missed_the_drift(repo, capsys):
    """Reverting to the whole-file hash must fail this suite, so it is asserted here.

    The old gate compared one `source_sha256` per record against the contract bytes.
    A field edit plus that one hash refresh leaves the old gate green; the per-field
    pair must still be red and name the field. If the implementation degraded back to
    the blob comparison, the second half of this test would fail.
    """
    record_pairing(repo)
    document = read_contract(repo)
    document["identity"]["definition"] = "S=sum(p*v)*k."
    write_contract(repo, document)
    zh = read_zh(repo)
    for item in zh["records"]:
        item["source_sha256"] = hashlib.sha256(
            (repo / "catalog" / "examples" / f"{item['asset_id']}.json").read_bytes()
        ).hexdigest()
    write_zh(repo, zh)

    legacy = [
        item["asset_id"]
        for item in zh["records"]
        if item["source_sha256"]
        != hashlib.sha256(
            (repo / "catalog" / "examples" / f"{item['asset_id']}.json").read_bytes()
        ).hexdigest()
    ]
    assert legacy == []  # the old whole-blob gate is satisfied

    code, out = run(repo, capsys)
    assert code == 1, out
    assert "contract field 'definition' changed" in out


def test_the_checked_in_records_pass_the_gate():
    """Run the gate on this repository, so a stale checked-in pair cannot pass the default suite.

    The other tests build temporary records; without this one the gate would only
    protect itself. `check_all.py` collects `tests/` and refuses deselection, so
    this assertion is what puts the pairing gate inside the acceptance run.
    """
    errors, _notes, state = zh_pairs.check(ROOT)
    assert errors == [], "\n".join(errors)
    offenders = {asset: status for asset, status in state.items() if status != "ok"}
    assert offenders == {}, offenders
    assert set(state) == set(zh_pairs.load_contracts(ROOT))


def test_the_cli_reports_a_missing_record_directory(tmp_path, capsys):
    code = zh_pairs.main(["--repo", str(tmp_path)])
    assert code == 2
    assert "no Chinese reader records" in capsys.readouterr().out
