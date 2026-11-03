"""Check that the review registry and the exposed catalog agree.

The gate is structural: every contract has one status, exposed assets carry a
releasable status, and held assets stay held. It proves no scientific claim and
needs nothing outside this repository. Human review decides the status.
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
EXPOSED_STATUSES = {'pass', 'pass-with-limits'}
HELD_STATUS = 'human-review'
RECORD_FIELDS = {'status', 'reason', 'required_decision'}


def _stems(directory: Path) -> set[str]:
    return {path.stem for path in directory.glob('*.json')}


def check() -> list[str]:
    try:
        hold = json.loads(HOLD.read_text(encoding='utf-8'))
        verdicts = json.loads(VERDICTS.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return [f'invalid review data: {exc}']
    if hold.get('schema') != 'scirel.exposure-hold' or not isinstance(hold.get('assets'), dict):
        return ['invalid hold schema/assets']
    if verdicts.get('schema') != 'scirel.audit-verdicts' or not isinstance(verdicts.get('assets'), dict):
        return ['invalid verdict schema/assets']

    errors: list[str] = []
    entries, held = verdicts['assets'], set(hold['assets'])
    public, review = _stems(CATALOG), _stems(REVIEW_CATALOG)
    catalog = public | review
    if missing := sorted(catalog - set(entries)):
        errors.append(f'contracts without a status: {missing}')
    if extra := sorted(set(entries) - catalog):
        errors.append(f'statuses without a contract: {extra}')
    if both := sorted(public & review):
        errors.append(f'contracts both exposed and in review: {both}')
    if not_held := sorted(review - held):
        errors.append(f'review contracts missing from HOLD.json: {not_held}')
    if exposed_hold := sorted(public & held):
        errors.append(f'held assets still exposed in catalog/examples: {exposed_hold}')
    for asset, record in entries.items():
        if not isinstance(record, dict) or set(record) - RECORD_FIELDS:
            errors.append(f'{asset}: record fields must be within {sorted(RECORD_FIELDS)}')
            continue
        status = record.get('status')
        if asset in held:
            if status != HELD_STATUS:
                errors.append(f'{asset}: held asset must be {HELD_STATUS}, got {status!r}')
            if not record.get('reason') or not record.get('required_decision'):
                errors.append(f'{asset}: held asset needs reason and required_decision')
        elif status not in EXPOSED_STATUSES:
            errors.append(f'{asset}: exposed asset has non-release status {status!r}')
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.parse_args(argv)
    errors = check()
    for error in errors:
        print('ERROR:', error)
    if errors:
        return 1
    print('review registry gate: PASS (structure only; no scientific claim)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
