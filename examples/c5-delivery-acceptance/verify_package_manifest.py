"""Re-verify a delivered package against its own runtime.json, byte by byte.

The repository has a validator for the extraction kit and one for an installed wheel, but
none for the delivered package itself (see GAPS.md E1). This script fills that gap for one
narrow question only: do the bytes on disk still match the manifest the builder sealed.

It does not check scientific correctness, does not talk to the wheel's contents, and does
not replace validate_installed_wheel (which proves the wheel installs and imports).

Usage:
    python3 examples/c5-delivery-acceptance/verify_package_manifest.py \
        --package .runtime/c5/scirel-delivery-435cc9a1
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(package: Path) -> dict:
    runtime_json = package / "runtime.json"
    if not runtime_json.is_file():
        return {"status": "FAIL", "errors": [f"missing runtime.json in {package}"]}

    manifest = json.loads(runtime_json.read_text(encoding="utf-8"))
    errors: list[str] = []
    checked = 0
    for relative, entry in sorted(manifest.get("files", {}).items()):
        path = package / relative
        if not path.is_file():
            errors.append(f"missing: {relative}")
            continue
        if path.stat().st_size != entry["bytes"]:
            errors.append(f"size mismatch: {relative} ({path.stat().st_size} != {entry['bytes']})")
            continue
        if digest(path) != entry["sha256"]:
            errors.append(f"sha256 mismatch: {relative}")
            continue
        checked += 1

    on_disk = {
        path.relative_to(package).as_posix() for path in package.rglob("*") if path.is_file()
    }
    unsealed = sorted(on_disk - set(manifest.get("files", {})) - {"runtime.json"})
    for relative in unsealed:
        errors.append(f"present but not in manifest: {relative}")

    contracts = len(list((package / "catalog" / "contracts").glob("*.json")))
    if contracts != manifest.get("asset_count"):
        errors.append(
            f"contract count {contracts} != runtime.json asset_count {manifest.get('asset_count')}"
        )

    return {
        "schema": "scirel.c5-manifest-check",
        "package": str(package),
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "manifest_entries": len(manifest.get("files", {})),
        "entries_verified": checked,
        "files_on_disk_not_in_manifest": unsealed,
        "contracts": contracts,
        "asset_count": manifest.get("asset_count"),
        "snapshot_sha256": manifest.get("snapshot_sha256"),
        "source_revision": manifest.get("source_revision"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True, help="delivered package root")
    parser.add_argument("--output", type=Path, help="optional path for the JSON result")
    args = parser.parse_args()

    result = verify(args.package.resolve())
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
