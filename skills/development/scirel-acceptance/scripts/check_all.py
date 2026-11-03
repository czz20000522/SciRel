#!/usr/bin/env python3
"""Run the complete local acceptance: everything must pass for the tree to be green."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
VALIDATE_REPORT = 'skills/development/usage/scirel-solving/scripts/validate_report.py'
WHEEL = 'scirel-0.0.0-py3-none-any.whl'


def steps(output: Path) -> list[tuple[str, list[str]]]:
    python = [sys.executable, '-B']
    plan = [
        ('tests', [*python, '-m', 'pytest', '-q', '-p', 'no:cacheprovider']),
        ('review registry', [*python, 'scripts/review_gate.py', '--check']),
        ('contracts and examples', [*python, 'scripts/validate_asset_documents.py', 'catalog/examples',
                                    '--check-runtime', '--execute-examples']),
        ('documentation build', [*python, 'scripts/scirel_docs.py', 'build', '--output', str(output / 'docs')]),
    ]
    for report in sorted(ROOT.glob('examples/*/REPORT.md')):
        plan.append((f'report {report.parent.name}', [*python, VALIDATE_REPORT, str(report)]))
    if shutil.which('uv'):
        plan.append(('lockfile', ['uv', 'lock', '--check']))
        wheels = output / 'wheel'
        plan.append(('wheel build', ['uv', 'build', '--wheel', '--out-dir', str(wheels), '.']))
        plan.append(('wheel exposure', [*python, 'scripts/check_wheel_exposure.py', '--source-root', str(ROOT / 'src'),
                                        '--wheel', str(wheels / WHEEL)]))
    return plan


def main() -> int:
    failed = []
    with tempfile.TemporaryDirectory(prefix='scirel-check-') as temporary:
        for name, command in steps(Path(temporary)):
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            status = 'PASS' if completed.returncode == 0 else 'FAIL'
            print(f'{status}  {name}', flush=True)
            if completed.returncode:
                failed.append(name)
                print((completed.stdout + completed.stderr)[-4000:])
    for leftover in ('build', 'src/scirel.egg-info'):
        shutil.rmtree(ROOT / leftover, ignore_errors=True)
    print('ALL GREEN' if not failed else f'FAILED: {failed}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
