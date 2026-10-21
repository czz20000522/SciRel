"""Validate the exposure/audit verdict gate.

This is deliberately outside the asset-document schema: contracts stay the
scientific truth; this registry records the admission state used by the
documentation, query and capability-matrix exposure filters.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLD = ROOT / 'catalog' / 'review' / 'HOLD.json'
VERDICTS = ROOT / 'catalog' / 'review' / 'VERDICTS.json'
CATALOG = ROOT / 'catalog' / 'examples'
REVIEW_CATALOG = ROOT / 'catalog' / 'review' / 'examples'
ALLOWED = {'pass', 'pass-with-limits', 'human-review', 'blocked'}


def check() -> list[str]:
    errors: list[str] = []
    hold = json.loads(HOLD.read_text(encoding='utf-8'))
    if hold.get('schema') != 'scirel.exposure-hold':
        errors.append('invalid hold schema')
    held = set(hold.get('assets', {}))
    verdicts = json.loads(VERDICTS.read_text(encoding='utf-8'))
    if verdicts.get('schema') != 'scirel.audit-verdicts':
        errors.append('invalid verdict schema')
    entries = verdicts.get('assets', {})
    catalog = {path.stem for path in CATALOG.glob('*.json')} | {
        path.stem for path in REVIEW_CATALOG.glob('*.json')}
    if set(entries) != catalog:
        errors.append(f'verdict coverage mismatch: missing={sorted(catalog-set(entries))[:5]} extra={sorted(set(entries)-catalog)[:5]}')
    for asset, record in entries.items():
        status = record.get('status')
        if status not in ALLOWED:
            errors.append(f'{asset}: invalid status {status!r}')
        if asset in held and status != 'human-review':
            errors.append(f'{asset}: held asset must be human-review, got {status}')
        if asset not in held and status not in ('pass', 'pass-with-limits'):
            errors.append(f'{asset}: exposed asset has non-release verdict {status}')
    for asset in held:
        if asset not in entries:
            errors.append(f'{asset}: held asset has no verdict')
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    errors = check()
    if errors:
        for error in errors:
            print('ERROR:', error)
        return 1
    print('audit verdict gate: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
