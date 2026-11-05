"""AUDIT-D5: collision contracts must not claim non-existent external tests.

The 11 collision contracts previously claimed an optional cross-implementation
comparison that "runs only when an external implementation root is configured".
No such test exists in this repository. The contracts now state that the
comparison is not maintained or replayed; this guard keeps that honest wording
from regressing back into an evidence claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "catalog" / "examples"
FORBIDDEN = (
    "external implementation root",
    "only when an external implementation root",
    "external comparison test compares",
    "comparison runs only when an external implementation",
)
ALLOWED_HONEST = (
    "not replayed",
    "outside this contract's evidence scope",
    "no environment-gated external-implementation comparison",
)


@pytest.mark.parametrize(
    "path", sorted(EXAMPLES.glob("scirel.collisions.*.json")), ids=lambda p: p.name
)
def test_collision_contracts_do_not_claim_a_missing_external_test(path):
    document = json.loads(path.read_text(encoding="utf-8"))
    fields = [
        json.dumps(document["verification"]["scope"], ensure_ascii=False),
        json.dumps(document["verification"]["known_limitations"], ensure_ascii=False),
        document["verification"]["evidence_ceiling"],
    ]
    text = " \n ".join(fields)
    for phrase in FORBIDDEN:
        assert phrase.lower() not in text.lower(), (path.name, phrase)
    if "external comparison" in text.lower():
        assert any(honest.lower() in text.lower() for honest in ALLOWED_HONEST), path.name
