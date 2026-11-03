"""Exposure filtering for the human-review hold.

The hold is deliberately outside the contract schema: contracts remain the
scientific truth, while this module controls which admitted assets are exposed
by generated documentation, capability queries and the capability matrix.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOLD = ROOT / 'catalog' / 'review' / 'HOLD.json'


def held_asset_ids(path: Path | None = None, *, read_bytes=None) -> frozenset[str]:
    """Return withheld ids, optionally parsing an already captured byte set."""
    path = DEFAULT_HOLD if path is None else Path(path)
    if read_bytes is None and not path.exists():
        return frozenset()
    payload = json.loads(path.read_bytes() if read_bytes is None else read_bytes(path))
    if not isinstance(payload, dict) or payload.get('schema') != 'scirel.exposure-hold':
        raise ValueError(f'invalid exposure hold schema: {path}')
    assets = payload.get('assets')
    if not isinstance(assets, dict):
        raise ValueError(f'invalid exposure hold assets: {path}')
    for asset, record in assets.items():
        if not isinstance(asset, str) or not isinstance(record, dict):
            raise ValueError(f'invalid exposure hold record: {asset}')
        if record.get('status') not in ('human-review', 'rejected'):
            raise ValueError(f'invalid exposure hold status: {asset}')
        for key in ('reason', 'required_decision'):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f'missing {key}: {asset}')
    return frozenset(assets)


def exposed_documents(documents: list[dict], *, hold_path: Path | None = None) -> list[dict]:
    """Filter contract documents to the exposed capability list."""
    held = held_asset_ids(hold_path)
    return [document for document in documents if document['asset_id'] not in held]
