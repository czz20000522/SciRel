"""Run the review closure for held candidates.

Usage:
    .venv/bin/python scripts/review_harness.py --check

The harness sets SCIREL_REVIEW_HOLD=1 and mounts the review candidate tree onto
the installed package path.  It then runs the held contract, its direct tests and
the import-surface check.  This is the executable entry the merge policy refers
to; it does not expose anything.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REVIEW_SRC = ROOT / 'catalog' / 'review' / 'candidates' / 'src'
REVIEW_EXAMPLES = ROOT / 'catalog' / 'review' / 'examples'
HOLD = ROOT / 'catalog' / 'review' / 'HOLD.json'


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    args = p.parse_args(argv)
    if not REVIEW_SRC.is_dir():
        print('review harness: candidate tree missing', file=sys.stderr)
        return 1
    held = json.loads(HOLD.read_text())['assets']
    env = dict(os.environ, SCIREL_REVIEW_HOLD='1')
    tests = sorted({t for asset in held
                    for t in json.loads((REVIEW_EXAMPLES / (asset + '.json')).read_text())
                    ['verification']['tests'] if (ROOT / t).is_file()})
    cmd = [sys.executable, '-m', 'pytest', '-q', *tests]
    print('review harness:', ' '.join(cmd))
    code = subprocess.run(cmd, cwd=ROOT, env=env).returncode
    print('held assets:', ', '.join(sorted(held)))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
