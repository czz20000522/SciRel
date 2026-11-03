"""Census callable domain exports that lack an exact SciRel document.

This is a development health check.  It reads the current source tree and the
current document set; it does not build a wheel, change release state, or infer
scientific fields for a missing document.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
from pathlib import Path
import sys
from typing import Any

from public_api_binding import implementation_module
from validate_asset_documents import AssetDocumentError, load_document_set


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "scirel.public-export-document-census"


def _document_keys(source_root: Path, document: dict[str, Any]) -> set[tuple[str, str]]:
    api = document["public_api"]["python"]
    implementation = implementation_module(source_root, api["module"], api["symbol"])
    keys = {
        (api["module"], api["symbol"]),
        (implementation, api["symbol"]),
    }
    if "canonical_module" in api:
        keys.add((api["canonical_module"], api["canonical_symbol"]))
    else:
        keys.add((implementation.rsplit(".", 1)[0], api["symbol"]))
    return keys


def census(
    source_root: Path = ROOT,
    documents_root: Path | None = None,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    source_path = str(source_root / "src")
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    documents_root = documents_root or source_root / "catalog" / "examples"

    document_bindings: set[tuple[str, str]] = set()
    canonical_bindings: dict[tuple[str, str], list[str]] = {}
    for document in load_document_set(documents_root):
        api = document["public_api"]["python"]
        implementation = implementation_module(source_root, api["module"], api["symbol"])
        canonical = (
            (api["canonical_module"], api["canonical_symbol"])
            if "canonical_module" in api
            else (implementation.rsplit(".", 1)[0], api["symbol"])
        )
        canonical_bindings.setdefault(canonical, []).append(document["asset_id"])
        document_bindings.update(_document_keys(source_root, document))

    exports: list[dict[str, str]] = []
    domains: list[str] = []
    for package_path in sorted((source_root / "src" / "scirel").iterdir()):
        if not package_path.is_dir() or package_path.name.startswith("_"):
            continue
        initializer = package_path / "__init__.py"
        if not initializer.is_file():
            continue
        domain = f"scirel.{package_path.name}"
        package = importlib.import_module(domain)
        domains.append(domain)
        names = getattr(package, "__all__", ())
        if not isinstance(names, (list, tuple)):
            continue
        for name in names:
            value = getattr(package, name, None)
            if not (
                inspect.isfunction(value)
                or inspect.isbuiltin(value)
                or inspect.ismethod(value)
            ):
                continue
            object_key = (
                getattr(value, "__module__", ""),
                getattr(value, "__name__", name),
            )
            exports.append(
                {
                    "module": domain,
                    "symbol": name,
                    "qualified_name": f"{domain}.{name}",
                    "kind": "callable",
                    "implementation": (
                        f"{object_key[0]}.{object_key[1]}"
                        if object_key[0]
                        else object_key[1]
                    ),
                }
            )

    missing = [
        item
        for item in exports
        if (
            (item["module"], item["symbol"]) not in document_bindings
            and tuple(item["implementation"].rsplit(".", 1)) not in document_bindings
        )
    ]
    duplicates = [
        {
            "module": module,
            "symbol": symbol,
            "asset_ids": sorted(asset_ids),
        }
        for (module, symbol), asset_ids in sorted(canonical_bindings.items())
        if len(asset_ids) > 1
    ]
    return {
        "schema": SCHEMA,
        "source_root": str(source_root),
        "documents_root": str(documents_root.resolve()),
        "domains": domains,
        "counts": {
            "domains": len(domains),
            "public_callables": len(exports),
            "documented_bindings": sum(
                1
                for item in exports
                if (item["module"], item["symbol"]) in document_bindings
            ),
            "missing": len(missing),
        },
        "missing": missing,
        "duplicate_document_bindings": duplicates,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--documents", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        report = census(args.source_root, args.documents)
    except AssetDocumentError as error:
        print(json.dumps({"schema": SCHEMA, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if report["missing"] or report["duplicate_document_bindings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
