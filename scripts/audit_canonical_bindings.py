"""Census stable package-level API aliases for the current asset documents."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from public_api_binding import implementation_module


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_INTENTIONAL_EXCEPTIONS = {
    "scirel.kinetic.generalized-small-k",
}


def _is_intentional_exception(asset_id: str) -> bool:
    return asset_id.startswith("scirel.kinetic.pdrk-") or asset_id in EXPECTED_INTENTIONAL_EXCEPTIONS


def _check_binding(source_root: Path, api: dict[str, Any]) -> tuple[str, str, str]:
    """Resolve and verify one implementation/canonical binding.

    The implementation module is always the wheel/source authority.  An
    explicit canonical pair pins the stable package-level discovery alias;
    legacy documents keep the historical fallback to the implementation's
    parent package.  Both paths must resolve to the same object and the
    canonical symbol must be listed by the package facade.
    """
    implementation = implementation_module(source_root, api["module"], api["symbol"])
    implementation_namespace = importlib.import_module(implementation)
    implementation_value = getattr(implementation_namespace, api["symbol"], None)
    if not callable(implementation_value):
        raise TypeError(f"implementation callable unavailable: {implementation}.{api['symbol']}")

    if "canonical_module" in api:
        canonical_module = api["canonical_module"]
        canonical_symbol = api["canonical_symbol"]
    else:
        canonical_module = implementation.rsplit(".", 1)[0]
        canonical_symbol = api["symbol"]

    package = importlib.import_module(canonical_module)
    if not hasattr(package, "__path__"):
        raise TypeError(f"canonical module is not a package: {canonical_module}")
    exports = getattr(package, "__all__", ())
    if not isinstance(exports, (list, tuple)) or canonical_symbol not in exports:
        raise TypeError(
            f"canonical symbol is not listed in {canonical_module}.__all__: "
            f"{canonical_symbol}"
        )
    canonical_value = getattr(package, canonical_symbol, None)
    if canonical_value is not implementation_value:
        raise TypeError(
            f"canonical binding differs: {canonical_module}.{canonical_symbol} "
            f"!= {implementation}.{api['symbol']}"
        )
    return implementation, canonical_module, canonical_symbol


def census(source_root: Path = ROOT, documents_root: Path | None = None) -> dict[str, Any]:
    source_root = source_root.resolve()
    source_path = str(source_root / "src")
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    documents_root = documents_root or source_root / "catalog" / "examples"
    rows: list[dict[str, str]] = []
    counts = {"total": 0, "explicit": 0, "candidate": 0, "exception": 0}
    unexpected: list[dict[str, str]] = []

    for path in sorted(documents_root.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        asset_id = document["asset_id"]
        api = document["public_api"]["python"]
        counts["total"] += 1
        try:
            implementation, canonical_module, canonical_symbol = _check_binding(source_root, api)
            import_error = ""
        except Exception as error:  # pragma: no cover - reported as census data
            import_error = f"{type(error).__name__}: {error}"
            implementation = implementation_module(source_root, api["module"], api["symbol"])
            canonical_module = api.get("canonical_module", implementation.rsplit(".", 1)[0])
            canonical_symbol = api.get("canonical_symbol", api["symbol"])
            if "canonical_module" in api:
                status = "explicit_invalid"
                unexpected.append(
                    {
                        "asset_id": asset_id,
                        "implementation": implementation,
                        "canonical_module": canonical_module,
                        "canonical_symbol": canonical_symbol,
                        "error": import_error,
                    }
                )
                rows.append({"asset_id": asset_id, "status": status})
                continue
            candidate = False
        else:
            candidate = True

        if "canonical_module" in api:
            counts["explicit"] += 1
            rows.append({"asset_id": asset_id, "status": "explicit"})
            continue

        if candidate:
            counts["candidate"] += 1
            status = "candidate"
        elif _is_intentional_exception(asset_id):
            counts["exception"] += 1
            status = "exception"
        else:
            status = "unexpected_missing"
            unexpected.append(
                {
                    "asset_id": asset_id,
                    "implementation": implementation,
                    "canonical_module": canonical_module,
                    "canonical_symbol": canonical_symbol,
                    "error": import_error,
                }
            )
        rows.append({"asset_id": asset_id, "status": status})

    return {"counts": counts, "unexpected_missing": unexpected, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--documents", type=Path, default=None)
    args = parser.parse_args()
    print(json.dumps(census(args.source_root, args.documents), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
