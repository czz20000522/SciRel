"""Check admission records and their mechanically verifiable evidence bindings.

Historical reports are retained evidence, not proofs about today's candidate.
The current material identity and maintenance overlays never imply that a test
was run or that an unknown historical candidate was verified.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

from validate_asset_documents import resolve_test_reference

ROOT = Path(__file__).resolve().parents[1]
HOLD = ROOT / 'catalog' / 'review' / 'HOLD.json'
VERDICTS = ROOT / 'catalog' / 'review' / 'VERDICTS.json'
CATALOG = ROOT / 'catalog' / 'examples'
REVIEW_CATALOG = ROOT / 'catalog' / 'review' / 'examples'
ALLOWED = {'pass', 'pass-with-limits', 'human-review', 'blocked'}
CLAIM_FIELDS = {'verdict', 'oracle', 'residual_risk'}
IDENTITY_SCOPE = 'current-materials-only'


def _repo_file(relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError('path must be a nonempty string')
    path = Path(relative)
    resolved = (ROOT / path).resolve()
    if path.is_absolute() or '..' in path.parts or not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f'path must stay inside the repository: {relative}')
    if not resolved.is_file():
        raise ValueError(f'file is missing: {relative}')
    return resolved


def _git(*args: str) -> str:
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True,
                            text=True, timeout=10, check=False)
    if result.returncode:
        raise ValueError(f'git {" ".join(args)} failed: {result.stderr.strip()}')
    return result.stdout.strip()


def _revision(revision: str) -> None:
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('revision must be a full Git commit id')
    _git('cat-file', '-e', f'{revision}^{{commit}}')
    _git('merge-base', '--is-ancestor', revision, 'HEAD')


def _test_node(node: str) -> tuple[str, str]:
    if not isinstance(node, str) or node.count('::') != 1:
        raise ValueError('test must name a file::function node')
    path, name = node.split('::')
    if not path.startswith('tests/') or not name.startswith('test_'):
        raise ValueError(f'invalid test node: {node}')
    return path, name


def current_material_digest(verdicts: dict) -> str:
    """Identify current product bytes; this function never writes a binding.

    The fixed scope contains public and review implementations (including data),
    public and review contracts, and every contract-bound or overlay-named test.
    Contract selectors use the canonical opaque-selector resolver; only the
    resolved file bytes are bound. Collection is not part of this static gate.
    Registry/report bytes are bound separately, avoiding a registry self-hash.
    """
    materials: set[str] = set()
    for directory in (ROOT / 'src' / 'scirel',
                      ROOT / 'catalog' / 'review' / 'candidates' / 'src' / 'scirel'):
        for path in directory.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                materials.add(path.relative_to(ROOT).as_posix())
    for path in (*CATALOG.glob('*.json'), *REVIEW_CATALOG.glob('*.json')):
        materials.add(path.relative_to(ROOT).as_posix())
        document = json.loads(path.read_text(encoding='utf-8'))
        if document.get('asset_id') != path.stem:
            raise ValueError(f'contract asset_id differs from filename: {path.name}')
        tests = document.get('verification', {}).get('tests')
        if not isinstance(tests, list) or not tests:
            raise ValueError(f'contract has no bound tests: {path.name}')
        for test in tests:
            if not isinstance(test, str) or not test.startswith('tests/'):
                raise ValueError(f'invalid contract test path: {test!r}')
            resolved_test = resolve_test_reference(test, ROOT)
            materials.add(resolved_test.relative_to(ROOT.resolve()).as_posix())
    for record in verdicts['assets'].values():
        for node in record.get('current_review', {}).get('tests', []):
            materials.add(_test_node(node)[0])
    digest = hashlib.sha256()
    for relative in sorted(materials):
        path = _repo_file(relative)
        digest.update(relative.encode('utf-8') + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _report_bindings(verdicts: dict) -> tuple[dict, list[str]]:
    bindings = verdicts.get('report_bindings')
    if not isinstance(bindings, dict) or not bindings:
        return {}, ['report_bindings must be a nonempty object']
    reports, errors = {}, []
    for report, binding in bindings.items():
        try:
            if not isinstance(binding, dict):
                raise ValueError('report binding must be an object')
            path = _repo_file(report)
            if not (report.startswith('catalog/review/evidence/') or (
                    report.startswith('tests/') and path.suffix == '.py'
                    and binding.get('format') == 'test-source')):
                raise ValueError('report must be retained evidence or an explicitly bound test source')
            if binding.get('retained_sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError('retained report bytes differ from their binding')
            if binding.get('format') == 'csv':
                fields = binding.get('claim_fields')
                if not isinstance(fields, dict) or set(fields) != CLAIM_FIELDS:
                    raise ValueError('CSV binding must map verdict, oracle and residual_risk')
                if any(not isinstance(column, str) or not column for column in fields.values()):
                    raise ValueError('CSV claim column names must be nonempty strings')
                with path.open(encoding='utf-8', newline='') as stream:
                    reader = csv.reader(stream, strict=True)
                    header = next(reader, [])
                    if not header or any(not column for column in header) or len(set(header)) != len(header):
                        raise ValueError('CSV header must have unique nonempty column names')
                    if not {'asset_id', *fields.values()} <= set(header):
                        raise ValueError('CSV claim columns are missing')
                    rows = []
                    for values in reader:
                        if len(values) != len(header):
                            raise ValueError(f'CSV row ending at line {reader.line_num} has '
                                             f'{len(values)} fields; expected {len(header)}')
                        rows.append(dict(zip(header, values, strict=True)))
                    reports[report] = (binding, rows)
            elif (binding.get('format') in ('markdown', 'test-source')
                  and binding.get('claim_binding') == 'UNKNOWN'):
                reports[report] = (binding, None)
            else:
                raise ValueError('non-CSV claims must explicitly remain UNKNOWN')
        except (OSError, TypeError, ValueError, csv.Error) as exc:
            errors.append(f'{report}: {exc}')
    return reports, errors


def _evidence_errors(asset: str, record: dict, reports: dict) -> list[str]:
    errors = []
    evidence = record.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        return [f'{asset}: evidence must be a nonempty array']
    seen = set()
    for entry in evidence:
        report = entry.get('report') if isinstance(entry, dict) else None
        if isinstance(entry, dict) and (set(entry) - (CLAIM_FIELDS | {'report'})):
            errors.append(f'{asset}: unrecognized historical evidence fields')
        try:
            _repo_file(report)
        except (OSError, ValueError) as exc:
            errors.append(f'{asset}: evidence report {exc}')
            continue
        if report in seen:
            errors.append(f'{asset}: duplicate evidence report: {report}')
        seen.add(report)
        if report not in reports:
            errors.append(f'{asset}: evidence report has no valid binding: {report}')
            continue
        if not isinstance(entry.get('verdict'), str) or not entry['verdict'].strip():
            errors.append(f'{asset}: evidence verdict must be a nonempty claim')
        binding, rows = reports[report]
        if rows is not None:
            matching = [row for row in rows if row['asset_id'] == asset]
            if len(matching) != 1:
                errors.append(f'{asset}: evidence report must have exactly one asset row: {report}')
                continue
            for field, column in binding['claim_fields'].items():
                if not isinstance(entry.get(field), str) or entry[field] != matching[0][column]:
                    errors.append(f'{asset}: {field} claim differs from {report}:{column}')
    return errors


def _current_review_errors(asset: str, record: dict, held: set, public: set) -> list[str]:
    review = record.get('current_review')
    evidence = record.get('evidence', [])
    failures = [entry for entry in evidence if isinstance(entry, dict)
                and entry.get('verdict') in ('fail', 'blocked', 'human-review')]
    if review is None:
        return ([f'{asset}: exposed historical failure needs an explicit successor']
                if asset not in held and failures else [])
    errors = []
    try:
        if not isinstance(review, dict) or set(review) != {
                'claim', 'supersedes', 'fix_revision', 'tests', 'verification_status',
                'released_dependencies'}:
            raise ValueError('invalid current_review fields')
        if not isinstance(review['claim'], str) or not review['claim'].strip():
            raise ValueError('current_review claim must be nonempty')
        if review['verification_status'] != 'NOT_RUN':
            raise ValueError('gate only locates tests; verification_status must be NOT_RUN')
        _revision(review['fix_revision'])
        if not isinstance(review['tests'], list):
            raise ValueError('current_review tests must be an array')
        if asset not in held and not review['tests']:
            raise ValueError('exposed successor needs a locatable test; execution remains NOT_RUN')
        for node in review['tests']:
            relative, function = _test_node(node)
            tree = ast.parse(_repo_file(relative).read_text(encoding='utf-8'))
            if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and n.name == function for n in tree.body):
                raise ValueError(f'test node is missing: {node}')
        dependencies = review['released_dependencies']
        if not isinstance(dependencies, list) or any(
                dependency not in public or dependency in held for dependency in dependencies):
            raise ValueError('released dependency is not currently public')
        successors = review['supersedes']
        if not isinstance(successors, list) or not successors:
            raise ValueError('current_review must supersede a historical claim')
        targets = set()
        for target in successors:
            if not isinstance(target, dict) or set(target) != {'report', 'field', 'value'}:
                raise ValueError('supersedes must locate a historical report/field/value')
            if target['field'] not in CLAIM_FIELDS:
                raise ValueError('supersedes may only target historical evidence claims, never another overlay')
            matching = [entry for entry in evidence if isinstance(entry, dict)
                        and entry.get('report') == target['report']
                        and entry.get(target['field']) == target['value']]
            if len(matching) != 1:
                raise ValueError('supersedes has a dangling or ambiguous historical claim')
            key = (target['report'], target['field'])
            if key in targets:
                raise ValueError('duplicate supersedes target')
            targets.add(key)
        if asset not in held and any((entry['report'], 'verdict') not in targets for entry in failures):
            raise ValueError('historical failure has no explicit successor verdict')
    except (OSError, SyntaxError, TypeError, ValueError, subprocess.TimeoutExpired) as exc:
        errors.append(f'{asset}: {exc}')
    return errors


def check() -> list[str]:
    errors: list[str] = []
    try:
        hold = json.loads(HOLD.read_text(encoding='utf-8'))
        verdicts = json.loads(VERDICTS.read_text(encoding='utf-8'))
        if hold.get('schema') != 'scirel.exposure-hold' or not isinstance(hold.get('assets'), dict):
            return ['invalid hold schema/assets']
        if verdicts.get('schema') != 'scirel.audit-verdicts' or not isinstance(verdicts.get('assets'), dict):
            return ['invalid verdict schema/assets']
        if verdicts.get('historical_candidate_identity') != 'UNKNOWN':
            errors.append('historical_candidate_identity must remain explicitly UNKNOWN')
        candidate = verdicts.get('current_candidate')
        if not isinstance(candidate, dict) or set(candidate) != {'base_revision', 'material_sha256', 'identity_scope'}:
            errors.append('invalid current_candidate binding')
        else:
            try:
                _revision(candidate['base_revision'])
                if candidate['identity_scope'] != IDENTITY_SCOPE:
                    raise ValueError('current_candidate identity_scope must be current-materials-only')
                if candidate['material_sha256'] != current_material_digest(verdicts):
                    raise ValueError('current candidate material digest differs; no historical claim is rebound')
            except (OSError, TypeError, ValueError, subprocess.TimeoutExpired) as exc:
                errors.append(f'current_candidate: {exc}')
        reports, report_errors = _report_bindings(verdicts)
        errors.extend(report_errors)
        held = set(hold['assets'])
        entries = verdicts['assets']
        public = {path.stem for path in CATALOG.glob('*.json')}
        catalog = public | {path.stem for path in REVIEW_CATALOG.glob('*.json')}
        if set(entries) != catalog:
            errors.append(f'verdict coverage mismatch: missing={sorted(catalog-set(entries))[:5]} extra={sorted(set(entries)-catalog)[:5]}')
        for asset, record in entries.items():
            if not isinstance(record, dict):
                errors.append(f'{asset}: verdict record must be an object')
                continue
            if set(record) - {'status', 'evidence', 'reason', 'required_decision', 'current_review'}:
                errors.append(f'{asset}: unrecognized verdict fields')
            errors.extend(_evidence_errors(asset, record, reports))
            errors.extend(_current_review_errors(asset, record, held, public))
            status = record.get('status')
            if status not in ALLOWED:
                errors.append(f'{asset}: invalid status {status!r}')
            if asset in held and status != 'human-review':
                errors.append(f'{asset}: held asset must be human-review, got {status}')
            if asset not in held and status not in ('pass', 'pass-with-limits'):
                errors.append(f'{asset}: exposed asset has non-release verdict {status}')
        for asset in held - set(entries):
            errors.append(f'{asset}: held asset has no verdict')
    except (OSError, AttributeError, TypeError, ValueError) as exc:
        errors.append(f'invalid review data: {exc}')
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.parse_args(argv)
    errors = check()
    try:
        print(f'actual HEAD: {_git("rev-parse", "HEAD")}; working tree: '
              f'{"dirty" if _git("status", "--porcelain") else "clean"}')
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f'actual checkout identity: UNKNOWN ({exc})')
    try:
        data = json.loads(VERDICTS.read_text(encoding='utf-8'))
        evidence = [entry for record in data['assets'].values() for entry in record['evidence']]
        unknown = sum(data['report_bindings'][entry['report']]['format'] == 'markdown' for entry in evidence)
        sources = sum(data['report_bindings'][entry['report']]['format'] == 'test-source' for entry in evidence)
        if data.get('historical_candidate_identity') == 'UNKNOWN':
            print(f'historical candidate identity UNKNOWN: {len(evidence)}/{len(evidence)} evidence references')
        print(f'Markdown claim binding UNKNOWN: {unknown}/{len(evidence)}; '
              f'test-source claim binding UNKNOWN: {sources}/{len(evidence)}')
        print('current review test nodes: locatable only; execution NOT_RUN by this gate')
        print('contract test selectors: opaque; collection/execution NOT_RUN by this gate')
    except (OSError, KeyError, TypeError, ValueError, subprocess.TimeoutExpired):
        pass  # Invalid data are reported by check(); diagnostics never replace validation.
    if errors:
        for error in errors:
            print('ERROR:', error)
        return 1
    print('audit verdict gate: PASS (mechanical bindings only)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
