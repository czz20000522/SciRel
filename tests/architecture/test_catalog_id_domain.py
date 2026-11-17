"""Pin the whole-catalog check that a contract ID names its module's domain.

`api-spec.md` requires ``scirel.<domain>.<name>`` to take ``<domain>`` from the
canonical module. `validate_extraction_package.py` enforces that for a candidate
package only, so 25 stale IDs survived in a catalog that was never re-extracted
as one batch. `scripts/check_catalog_id_domain.py` is the missing whole-catalog
check; these tests keep it green on the tracked catalog and red on a new
violation.

The domain comes from ``public_api.python.canonical_module`` (falling back to
``module``), which is the same source `capability_catalog.py`, `test_scope.py`
and `validate_extraction_package.py` use, so an asset cannot be owned by one
domain in the index and another in its ID.

Not covered here, deliberately: test directories do not follow the domain. The
repository keeps `tests/sampling/` and `tests/fieldline/` although both domains
have no source package, because nothing requires the names to agree —
`tests/architecture/_domain_imports.py` enumerates `src/scirel/` only, and
`scripts/test_scope.py` merely requires a directory for a domain a module uses,
falling back to the referencing test owners. `tests/scirel.inference.latin_hypercube_sampling/`
is an existing non-domain directory, so renaming a contract does not move tests.
"""

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_catalog_id_domain as checker  # noqa: E402


def _contract(asset_id, module, canonical_module):
    python = {"module": module, "canonical_module": canonical_module}
    return {"asset_id": asset_id, "public_api": {"python": python}}


def _write_repo(tmp_path, contracts, review=(), exceptions=None):
    """Build the smallest tree the checker reads: catalog/ plus contracts/."""
    examples = tmp_path / "catalog" / "examples"
    examples.mkdir(parents=True)
    for name, document in contracts.items():
        (examples / f"{name}.json").write_text(json.dumps(document), encoding="utf-8")
    review_root = tmp_path / "catalog" / "review" / "examples"
    review_root.mkdir(parents=True)
    for name, document in dict(review).items():
        (review_root / f"{name}.json").write_text(json.dumps(document), encoding="utf-8")
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    payload = exceptions if exceptions is not None else checker_default_exceptions()
    (contracts_dir / "catalog-domain-exceptions.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    return tmp_path


def checker_default_exceptions():
    return {
        "schema": checker.SCHEMA,
        "policy": "Empty by design: a mismatch is a stale ID, so it is renamed, not excused.",
        "exceptions": [],
    }


def test_checked_in_catalog_ids_name_their_module_domain():
    report = checker.check(ROOT)

    assert report["errors"] == []
    assert report["mismatches"] == []
    assert report["checked"] > 200
    assert checker.main(["--repo", str(ROOT)]) == 0


def test_a_stale_id_domain_fails_and_names_the_id_domains_and_module(tmp_path, capsys):
    repo = _write_repo(
        tmp_path,
        {
            "scirel.sampling.alpha": _contract(
                "scirel.sampling.alpha", "scirel.geometry", "scirel.geometry"
            )
        },
    )

    assert checker.main(["--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "scirel.sampling.alpha" in out
    assert "'sampling'" in out
    assert "'geometry'" in out
    assert "module scirel.geometry" in out


def test_the_canonical_module_decides_not_the_plain_module_field(tmp_path, capsys):
    """An ID that matches `module` but not `canonical_module` is still wrong."""
    repo = _write_repo(
        tmp_path,
        {
            "scirel.sampling.alpha": _contract(
                "scirel.sampling.alpha", "scirel.sampling.alpha", "scirel.geometry"
            )
        },
    )

    assert checker.main(["--repo", str(repo)]) == 1
    assert "module domain 'geometry'" in capsys.readouterr().out


def test_review_examples_are_checked_too(tmp_path, capsys):
    repo = _write_repo(
        tmp_path,
        {},
        review={
            "scirel.fieldline.alpha": _contract(
                "scirel.fieldline.alpha", "scirel.geometry", "scirel.geometry"
            )
        },
    )

    assert checker.main(["--repo", str(repo)]) == 1
    assert "scirel.fieldline.alpha" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("reason", "evidence"),
    [
        ("", "recorded in the tracking issue for this asset"),
        ("it is a deliberate cross-domain placement", ""),
        ("short", "short"),
    ],
)
def test_an_exception_without_a_reason_and_evidence_fails(tmp_path, capsys, reason, evidence):
    repo = _write_repo(
        tmp_path,
        {
            "scirel.sampling.alpha": _contract(
                "scirel.sampling.alpha", "scirel.geometry", "scirel.geometry"
            )
        },
        exceptions={
            "schema": checker.SCHEMA,
            "policy": "An exception needs a reason and evidence.",
            "exceptions": [
                {"asset_id": "scirel.sampling.alpha", "reason": reason, "evidence": evidence}
            ],
        },
    )

    assert checker.main(["--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "reason must say why" in out or "evidence must name where" in out


def test_a_recorded_exception_is_reported_rather_than_hidden(tmp_path, capsys):
    repo = _write_repo(
        tmp_path,
        {
            "scirel.sampling.alpha": _contract(
                "scirel.sampling.alpha", "scirel.geometry", "scirel.geometry"
            )
        },
        exceptions={
            "schema": checker.SCHEMA,
            "policy": "An exception needs a reason and evidence.",
            "exceptions": [
                {
                    "asset_id": "scirel.sampling.alpha",
                    "reason": "the reviewing maintainer keeps the family name for readers",
                    "evidence": "tickets/architecture/0001-family-name.md records the decision",
                }
            ],
        },
    )

    assert checker.main(["--repo", str(repo)]) == 0
    assert "excepted: scirel.sampling.alpha" in capsys.readouterr().out


def test_an_exception_that_matches_no_mismatch_fails(tmp_path, capsys):
    repo = _write_repo(
        tmp_path,
        {
            "scirel.geometry.alpha": _contract(
                "scirel.geometry.alpha", "scirel.geometry", "scirel.geometry"
            )
        },
        exceptions={
            "schema": checker.SCHEMA,
            "policy": "An exception needs a reason and evidence.",
            "exceptions": [
                {
                    "asset_id": "scirel.geometry.alpha",
                    "reason": "a stale allowance left behind after the ID was aligned",
                    "evidence": "tickets/architecture/0001-family-name.md records the decision",
                }
            ],
        },
    )

    assert checker.main(["--repo", str(repo)]) == 1
    assert "matches no current mismatch" in capsys.readouterr().out


def test_the_shipped_exception_list_is_empty_and_states_the_policy():
    document = json.loads((ROOT / checker.EXCEPTIONS).read_text(encoding="utf-8"))

    assert document["schema"] == checker.SCHEMA
    assert document["exceptions"] == []
    assert len(document["policy"]) > 100
    assert "stale" in document["policy"]
