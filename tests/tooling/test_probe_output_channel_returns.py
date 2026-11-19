"""The probe measures a completed call to the contract target, not an example local."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import probe_output_channel_returns as probe  # noqa: E402


def _catalog(root, documents):
    baseline = root / probe.BASELINE
    baseline.parent.mkdir(parents=True)
    baseline.write_text(json.dumps({"entries": [{"asset_id": a} for a in documents]}))
    directory = root / probe.CATALOG
    directory.mkdir(parents=True)
    for asset, document in documents.items():
        (directory / f"{asset}.json").write_text(json.dumps(document), encoding="utf-8")


def test_return_before_unpacking_indexing_or_discarding(tmp_path):
    expected = {
        "scirel.io.write-eqdsk": ("none", "NoneType"),
        "scirel.kinetic.vp-rk4-step": ("positional", "tuple"),
        "scirel.neutrals.elastic-regeneration-aggregation": ("positional", "ndarray"),
        "scirel.kinetic.relativistic-codrift-generalized-spectrum": ("mapping-like", "dict"),
    }
    _catalog(
        tmp_path,
        {a: json.loads((ROOT / probe.CATALOG / f"{a}.json").read_text()) for a in expected},
    )
    records = probe.probe(tmp_path)
    assert {a: (r["kind"], r["runtime_type"]) for a, r in records.items()} == expected


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        ("loads = dict\ninput_dict = loads(a=1)", "no completed"),
        ("from json import loads\nif False:\n    loads('{}')", "no completed"),
        ("from json import loads as f\nf('{}')\nf('42')", "inconsistent"),
        ("from json import loads\nloads('invalid')", "JSONDecodeError"),
        ("import json\njson.loads('{}')\nassert False, 'later failure'", "later failure"),
        ("raise SystemExit(0)", "SystemExit: 0"),
    ],
)
def test_unobserved_is_not_a_classification(tmp_path, code, reason):
    document = {
        "public_api": {"python": {"module": "json", "symbol": "loads"}},
        "example": {"code": code},
    }
    _catalog(tmp_path, {"example": document})
    report = tmp_path / "report.json"
    assert probe.main(["--root", str(tmp_path), "--json", str(report)]) == 2
    record = json.loads(report.read_text())["example"]
    assert record["kind"] == "no-candidate"
    assert record.get("runtime_type") is None
    assert reason in record["error"]
