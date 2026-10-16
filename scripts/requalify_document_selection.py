"""Requalify one Git-owned asset selection for a successor package version.

The asset documents remain in their canonical ``catalog/examples`` tree.  This
tool only changes ``version.implementation_version`` after proving that the
selected document and its public implementation are unchanged from a baseline
Git ref.  Changed implementations are reported as blocked and stop a complete
requalification by default; callers must test those assets separately before
running an applying pass.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RECEIPT_SCHEMA = "scirel.document-requalification.v1"
SELECTION_SCHEMA = "scirel.selected-document-set.v1"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _resolve_ref(root: Path, ref: str) -> str:
    return _git(root, "rev-parse", f"{ref}^{{commit}}").decode().strip()


def _git_file(root: Path, revision: str, relative: str) -> bytes:
    return _git(root, "show", f"{revision}:{relative}")


def _module_candidates(document: dict[str, Any]) -> list[str]:
    module = document["public_api"]["python"]["module"]
    stem = f"src/{module.replace('.', '/')}"
    return [f"{stem}.py", f"{stem}/__init__.py"]


def _without_implementation_version(document: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(document)
    result["version"]["implementation_version"] = "<implementation-version>"
    return result


def _selection_rows(selection_path: Path) -> list[dict[str, Any]]:
    selection = _read_json(selection_path)
    if selection.get("schema") != SELECTION_SCHEMA:
        raise ValueError(f"selection has an invalid schema: {selection_path}")
    rows = selection.get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("selection records must be a non-empty array")
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"asset_id", "path", "sha256"}:
            raise ValueError("selection contains an invalid record")
    return rows


def requalify_selection(
    *,
    selection_path: Path,
    baseline_ref: str,
    old_version: str,
    new_version: str,
    root: Path = ROOT,
    output_selection: Path | None = None,
    output_receipt: Path | None = None,
    apply: bool = False,
    require_complete: bool = True,
) -> dict[str, Any]:
    if old_version == new_version:
        raise ValueError("old_version and new_version must differ")
    root = root.resolve()
    selection_path = selection_path.resolve()
    if not selection_path.is_relative_to(root):
        raise ValueError("selection must be inside the repository")
    rows = _selection_rows(selection_path)
    resolved_ref = _resolve_ref(root, baseline_ref)

    eligible: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []
    for row in rows:
        asset_id = row["asset_id"]
        relative = row["path"]
        document_path = (root / relative).resolve()
        if not document_path.is_relative_to(root) or not document_path.is_file():
            raise ValueError(f"selected document path is invalid: {relative}")
        current_bytes = document_path.read_bytes()
        if _sha256(current_bytes) != row["sha256"]:
            raise ValueError(f"selection digest differs from current document: {asset_id}")
        current = json.loads(current_bytes)
        if not isinstance(current, dict) or current.get("asset_id") != asset_id:
            raise ValueError(f"document asset ID differs from selection: {asset_id}")
        current_version = current.get("version", {}).get("implementation_version")
        if current_version != old_version:
            raise ValueError(
                f"document {asset_id} has version {current_version!r}, expected {old_version!r}"
            )

        baseline_bytes = _git_file(root, resolved_ref, relative)
        baseline = json.loads(baseline_bytes)
        if not isinstance(baseline, dict) or baseline.get("asset_id") != asset_id:
            raise ValueError(f"baseline document asset ID differs: {asset_id}")
        baseline_version = baseline.get("version", {}).get("implementation_version")
        if baseline_version != old_version:
            raise ValueError(
                f"baseline document {asset_id} has version {baseline_version!r}, "
                f"expected {old_version!r}"
            )

        reasons: list[str] = []
        if _without_implementation_version(current) != _without_implementation_version(baseline):
            reasons.append("document_contract_changed")
        module_relative = None
        baseline_module = None
        for candidate in _module_candidates(current):
            try:
                baseline_module = _git_file(root, resolved_ref, candidate)
            except ValueError:
                continue
            if (root / candidate).is_file():
                module_relative = candidate
                break
        if module_relative is None or baseline_module is None:
            reasons.append("public_module_missing_at_baseline")
            module_relative = _module_candidates(current)[0]
        elif (root / module_relative).read_bytes() != baseline_module:
            reasons.append("public_module_changed")

        item = {
            "asset_id": asset_id,
            "path": relative,
            "module": module_relative,
        }
        if reasons:
            blocked.append({**item, "reasons": ",".join(reasons)})
        else:
            eligible.append(item)

    if require_complete and blocked:
        raise ValueError(
            "complete requalification is blocked for "
            + ", ".join(item["asset_id"] for item in blocked)
        )
    if apply and not require_complete:
        raise ValueError("--apply requires complete requalification; remove --allow-partial")
    if apply and output_selection is None:
        raise ValueError("--apply requires --output-selection")

    changed_paths: list[str] = []
    if apply:
        for item in eligible:
            path = root / item["path"]
            text = path.read_text(encoding="utf-8")
            old_field = f'"implementation_version": "{old_version}"'
            new_field = f'"implementation_version": "{new_version}"'
            if text.count(old_field) != 1:
                raise ValueError(
                    f"cannot safely update implementation_version in {item['path']}"
                )
            updated = text.replace(old_field, new_field)
            json.loads(updated)
            path.write_text(updated, encoding="utf-8", newline="\n")
            changed_paths.append(item["path"])

    selection_out: str | None = None
    if apply and output_selection is not None:
        output_selection = output_selection.resolve()
        if not output_selection.is_relative_to(root):
            raise ValueError("output selection must be inside the repository")
        selected_rows = []
        for item in eligible:
            path = root / item["path"]
            selected_rows.append(
                {
                    "asset_id": item["asset_id"],
                    "path": item["path"],
                    "sha256": _sha256(path.read_bytes()),
                }
            )
        selection_value = {"schema": SELECTION_SCHEMA, "records": selected_rows}
        output_selection.parent.mkdir(parents=True, exist_ok=True)
        output_selection.write_text(
            json.dumps(selection_value, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        selection_out = str(output_selection.relative_to(root))

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "baseline_ref": baseline_ref,
        "baseline_revision": resolved_ref,
        "selection": str(selection_path.relative_to(root)),
        "old_version": old_version,
        "new_version": new_version,
        "mode": "apply" if apply else "dry_run",
        "require_complete": require_complete,
        "selected_count": len(rows),
        "eligible_count": len(eligible),
        "blocked_count": len(blocked),
        "eligible": eligible,
        "blocked": blocked,
        "changed_paths": changed_paths,
        "output_selection": selection_out,
    }
    if output_receipt is not None:
        output_receipt = output_receipt.resolve()
        output_receipt.parent.mkdir(parents=True, exist_ok=True)
        output_receipt.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--baseline-ref", required=True)
    parser.add_argument("--old-version", required=True)
    parser.add_argument("--new-version", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-selection", type=Path)
    parser.add_argument("--output-receipt", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="return eligible rows even when some selected assets are blocked",
    )
    args = parser.parse_args()
    try:
        receipt = requalify_selection(
            selection_path=args.selection,
            baseline_ref=args.baseline_ref,
            old_version=args.old_version,
            new_version=args.new_version,
            root=args.root,
            output_selection=args.output_selection,
            output_receipt=args.output_receipt,
            apply=args.apply,
            require_complete=not args.allow_partial,
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"document requalification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
