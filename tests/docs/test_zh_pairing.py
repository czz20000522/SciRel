"""The Chinese pairing gate names the drifted field and cannot be satisfied by a blob hash."""

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


def contract() -> dict:
    return {
        "schema": "scirel.asset-document",
        "asset_id": ASSET,
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
        "example": {"description": "One case.", "code": "pass", "expected": "finite"},
        "verification": {"scope": ["Declared checks."], "tests": ["tests/x.py"]},
    }


def record() -> dict:
    return {
        "asset_id": ASSET,
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
        "example": {"description": "一个用例。", "expected": "有限"},
        "verification": {"scope": ["已声明检查。"], "tests": ["tests/x.py"]},
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "catalog" / "examples").mkdir(parents=True)
    (tmp_path / "tools" / "docs" / "zh").mkdir(parents=True)
    (tmp_path / "catalog" / "examples" / f"{ASSET}.json").write_text(
        json.dumps(contract(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    zh = {"schema": "scirel.reader-translation", "language": "zh-CN", "records": [record()]}
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


def read_contract(root: Path) -> dict:
    return json.loads((root / "catalog" / "examples" / f"{ASSET}.json").read_text(encoding="utf-8"))


def write_contract(root: Path, document: dict) -> None:
    (root / "catalog" / "examples" / f"{ASSET}.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


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


def test_a_missing_pairing_block_is_accepted_as_v1_and_annotated(repo, capsys):
    code, out = run(repo, capsys)
    assert code == 0, out
    assert "v1 record without a pairing block" in out
    code, out = run(repo, capsys, "--list")
    assert code == 0
    assert "v1" in out


def test_a_forged_hash_is_rejected(repo, capsys):
    record_pairing(repo)
    document = read_zh(repo)
    document["records"][0]["pairing"]["sections"]["model"]["en"] = "f" * 16
    write_zh(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "contract field 'model' changed" in out


def test_an_unknown_section_is_rejected(repo, capsys):
    record_pairing(repo)
    document = read_zh(repo)
    document["records"][0]["pairing"]["sections"]["geometry"] = {"en": "a" * 16, "zh": "b" * 16}
    write_zh(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "sections the record no longer translates" in out


def test_a_section_missing_from_the_pairing_block_is_rejected(repo, capsys):
    record_pairing(repo)
    document = read_zh(repo)
    del document["records"][0]["pairing"]["sections"]["verification"]
    write_zh(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "field 'verification' has no recorded hash" in out


def test_a_record_without_a_contract_is_rejected(repo, capsys):
    document = read_zh(repo)
    document["records"][0]["asset_id"] = "scirel.absent.asset"
    write_zh(repo, document)
    code, out = run(repo, capsys)
    assert code == 1
    assert "no contract" in out


def test_write_is_idempotent_and_keeps_the_existing_layout(repo, capsys):
    record_pairing(repo)
    once = (repo / "tools" / "docs" / "zh" / "zh_test.json").read_text(encoding="utf-8")
    record_pairing(repo)
    twice = (repo / "tools" / "docs" / "zh" / "zh_test.json").read_text(encoding="utf-8")
    assert once == twice
    assert once.startswith('{\n "schema"')  # the repository's one-space layout survives
    assert '"pairing"' in once


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
    zh["records"][0]["source_sha256"] = hashlib.sha256(
        (repo / "catalog" / "examples" / f"{ASSET}.json").read_bytes()
    ).hexdigest()
    write_zh(repo, zh)

    legacy = [
        record["asset_id"]
        for record in zh["records"]
        if record["source_sha256"]
        != hashlib.sha256(
            (repo / "catalog" / "examples" / f"{record['asset_id']}.json").read_bytes()
        ).hexdigest()
    ]
    assert legacy == []  # the old whole-blob gate is satisfied

    code, out = run(repo, capsys)
    assert code == 1, out
    assert "contract field 'definition' changed" in out


def test_the_cli_reports_a_missing_record_directory(tmp_path, capsys):
    code = zh_pairs.main(["--repo", str(tmp_path)])
    assert code == 2
    assert "no Chinese reader records" in capsys.readouterr().out
