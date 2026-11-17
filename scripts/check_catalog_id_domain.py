"""Check that every contract ID names the domain whose module defines the function.

The rule (`skills/development/scirel-code-style/references/api-spec.md`, "One
truth"): a contract ID ``scirel.<domain>.<name>`` must name the domain whose
module defines the function, so ``<domain>`` equals the canonical module's
domain. The domain source is ``public_api.python.canonical_module``, falling
back to ``module`` for the contracts that predate the canonical field; that is
the same choice ``scripts/capability_catalog.py``, ``scripts/test_scope.py`` and
``scripts/validate_extraction_package.py`` already make, so the index, the test
scope and this check cannot disagree about which domain owns an asset.

``validate_extraction_package.py`` enforces the rule for a candidate package
only, which is why 25 stale IDs survived in the catalog: a candidate check says
nothing about contracts that were never re-extracted. This script closes that
gap. It reads every contract in ``catalog/examples/`` and
``catalog/review/examples/`` and fails on an ID whose domain differs from its
module's domain.

A deliberate cross-domain placement, if one ever exists, is recorded in
``contracts/catalog-domain-exceptions.json`` with a reason and evidence. The
list ships empty because every mismatch found so far was a stale ID rather than
an intended exception, and an entry missing its reason or evidence is a failure,
so the file cannot quietly become a skip list. An entry that no longer matches a
current mismatch is also a failure: an exception that outlives its case hides
the next one.

The check never imports scirel and never writes, so it can run before the
package is installed. Exit code 0 means every ID is aligned; 1 means at least
one ID, exception file or exception entry is wrong.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "scirel.catalog-domain-exceptions"
CONTRACT_ROOT = Path("catalog/examples")
REVIEW_ROOT = Path("catalog/review/examples")
EXCEPTIONS = Path("contracts/catalog-domain-exceptions.json")
REASON_MIN = 20
EVIDENCE_MIN = 20


def _load_exceptions(path: Path) -> tuple[dict[str, dict], list[str]]:
    """Return the recorded exceptions keyed by asset id, and any structural errors."""
    if not path.is_file():
        return {}, [f"{path}: exception file is missing"]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, [f"{path}: unreadable exception file ({exc})"]
    errors: list[str] = []
    if document.get("schema") != SCHEMA:
        errors.append(f"{path}: schema must be {SCHEMA!r}, got {document.get('schema')!r}")
    policy = str(document.get("policy") or "").strip()
    if not policy:
        errors.append(f"{path}: needs a nonempty policy stating how an exception is justified")
    raw = document.get("exceptions")
    if not isinstance(raw, list):
        errors.append(f"{path}: exceptions must be a list")
        return {}, errors
    recorded: dict[str, dict] = {}
    for position, entry in enumerate(raw):
        where = f"{path}: exceptions[{position}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be an object")
            continue
        asset_id = str(entry.get("asset_id") or "").strip()
        if not asset_id:
            errors.append(f"{where}: needs asset_id")
            continue
        if asset_id in recorded:
            errors.append(f"{where}: duplicate entry for {asset_id}")
            continue
        reason = str(entry.get("reason") or "").strip()
        evidence = str(entry.get("evidence") or "").strip()
        if len(reason) < REASON_MIN:
            errors.append(f"{where}: reason must say why the ID stays across domains")
        if len(evidence) < EVIDENCE_MIN:
            errors.append(f"{where}: evidence must name where the exception is established")
        recorded[asset_id] = {
            "reason": reason,
            "evidence": evidence,
            "asset_id": asset_id,
        }
    return recorded, errors


def _domain(value: str) -> str:
    """Second dotted segment: the domain of an asset ID or of a module path."""
    parts = value.split(".")
    return parts[1] if len(parts) >= 2 else ""


def _contract_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for directory in (CONTRACT_ROOT, REVIEW_ROOT):
        base = root / directory
        if base.is_dir():
            files.extend(sorted(base.glob("*.json")))
    return files


def check(root: Path, exceptions_path: Path | None = None) -> dict:
    """Return the catalog ID domain report for ``root``; never raises on content."""
    exceptions_file = exceptions_path or (root / EXCEPTIONS)
    exceptions, errors = _load_exceptions(exceptions_file)
    checked = 0
    mismatches: list[dict] = []
    excepted: list[dict] = []
    for path in _contract_files(root):
        where = path.relative_to(root)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{where}: unreadable contract ({exc})")
            continue
        asset_id = document.get("asset_id")
        api = (document.get("public_api") or {}).get("python") or {}
        module = api.get("canonical_module") or api.get("module")
        if not isinstance(asset_id, str) or not isinstance(module, str):
            errors.append(f"{where}: needs asset_id and public_api.python.module")
            continue
        if not module.startswith("scirel."):
            errors.append(f"{where}: {asset_id} declares a non-SciRel module {module!r}")
            continue
        checked += 1
        id_domain = _domain(asset_id)
        module_domain = _domain(module)
        if id_domain == module_domain:
            continue
        record = {
            "asset_id": asset_id,
            "id_domain": id_domain,
            "module_domain": module_domain,
            "module": module,
            "path": str(where),
        }
        if asset_id in exceptions:
            record["reason"] = exceptions[asset_id]["reason"]
            excepted.append(record)
            continue
        mismatches.append(record)
    stale = sorted(set(exceptions) - {item["asset_id"] for item in excepted})
    for asset_id in stale:
        errors.append(
            f"{exceptions_file}: exception for {asset_id} matches no current mismatch; "
            "drop it instead of carrying a stale allowance"
        )
    return {
        "schema": "scirel.catalog-id-domain-report",
        "checked": checked,
        "mismatches": mismatches,
        "excepted": excepted,
        "stale_exceptions": stale,
        "errors": errors,
    }


def _format(report: dict) -> list[str]:
    lines: list[str] = []
    for item in report["mismatches"]:
        lines.append(
            f"{item['path']}: {item['asset_id']}: ID domain {item['id_domain']!r} != "
            f"module domain {item['module_domain']!r} (module {item['module']})"
        )
    for item in report["excepted"]:
        lines.append(f"excepted: {item['asset_id']} ({item['module']})")
    lines.extend(report["errors"])
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo",
        default=".",
        help="repository root that owns catalog/ and contracts/ (default: current directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the machine-readable report instead of the summary",
    )
    args = parser.parse_args(argv)

    report = check(Path(args.repo).resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for line in _format(report):
            print(line)
        print(
            f"catalog ID domain: {report['checked']} assets, "
            f"{len(report['excepted'])} exceptions, {len(report['mismatches'])} mismatches, "
            f"{len(report['errors'])} errors"
        )
    return 0 if not report["mismatches"] and not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
