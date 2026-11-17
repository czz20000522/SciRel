"""One contract shape, one field list.

The same document has two gates: `contracts/scientific-asset-document.schema.json`
(JSON Schema, used by the docs build and by contract readers) and
`scripts/validate_asset_documents.py` (the hand-written validator that runs in the
acceptance gate). They each declared `verification`'s allowed fields, and adding
`basis` to the schema alone left the validator rejecting it with
"unknown fields: basis" -- a field that exists in one truth and not the other.

This test pins the duplication down so it cannot drift silently: the validator's key
sets must equal the schema's declared properties. It does not remove the duplication;
it makes any divergence a red test instead of a field that half-exists.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "contracts" / "scientific-asset-document.schema.json"
sys.path.insert(0, str(ROOT / "scripts"))

import validate_asset_documents as validator  # noqa: E402


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_verification_keys_match_the_schema():
    declared = set(_schema()["properties"]["verification"]["properties"])
    assert validator.VERIFICATION_KEYS == declared, (
        "the validator and the JSON schema disagree about verification's fields: "
        f"validator-only={sorted(validator.VERIFICATION_KEYS - declared)}, "
        f"schema-only={sorted(declared - validator.VERIFICATION_KEYS)}"
    )


def test_verification_required_keys_are_a_subset_of_the_schema_required():
    """`basis` is optional today; the other four are required in both places."""
    schema_required = set(_schema()["properties"]["verification"]["required"])
    assert schema_required == {"scope", "tests", "evidence_ceiling", "known_limitations"}
    assert "basis" not in schema_required


def test_basis_kinds_match_the_schema_enum():
    declared = set(
        _schema()["properties"]["verification"]["properties"]["basis"]["properties"]["kind"]["enum"]
    )
    assert validator.VERIFICATION_BASIS_KINDS == declared, (
        f"validator-only={sorted(validator.VERIFICATION_BASIS_KINDS - declared)}, "
        f"schema-only={sorted(declared - validator.VERIFICATION_BASIS_KINDS)}"
    )
