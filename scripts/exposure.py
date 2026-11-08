"""Packaging scope for assets that are not part of the installed package.

The exclusion list is packaging scope, not scientific judgement. Every entry
names an asset kept out of the installed package, generated documentation, the
capability index, the query service and the capability matrix.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCLUSIONS = ROOT / "catalog" / "review" / "excluded_from_package.json"
EXCLUSION_SCHEMA = "scirel.excluded-from-package"


def excluded_asset_ids(path: Path | None = None, *, read_bytes=None) -> frozenset[str]:
    """Return excluded asset ids, optionally parsing already captured bytes."""
    path = DEFAULT_EXCLUSIONS if path is None else Path(path)
    payload = json.loads(path.read_bytes() if read_bytes is None else read_bytes(path))
    if not isinstance(payload, dict) or payload.get("schema") != EXCLUSION_SCHEMA:
        raise ValueError(f"invalid package exclusion schema: {path}")
    ids = payload.get("ids")
    if not isinstance(ids, list):
        raise ValueError(f"invalid package exclusion ids: {path}")
    for asset in ids:
        if not isinstance(asset, str) or not asset.strip():
            raise ValueError(f"invalid package exclusion id: {asset}")
    return frozenset(ids)


def exposed_documents(documents: list[dict], *, exclusions_path: Path | None = None) -> list[dict]:
    """Filter contract documents to the exposed capability list."""
    excluded = excluded_asset_ids(exclusions_path)
    return [document for document in documents if document["asset_id"] not in excluded]
