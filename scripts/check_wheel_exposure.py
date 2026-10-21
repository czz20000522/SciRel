"""Prove that reviewed/held modules and symbols are absent from the wheel."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DOCS = ROOT / 'catalog' / 'review' / 'examples'


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path)
    args = p.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, '-m', 'pip', 'wheel', '-q', '--no-deps',
                        '--no-build-isolation', '-w', tmp, str(ROOT)], check=True)
        wheels = list(Path(tmp).glob('*.whl'))
        if len(wheels) != 1:
            raise SystemExit('expected exactly one wheel')
        wheel = wheels[0]
        with zipfile.ZipFile(wheel) as z:
            names = z.namelist()
            sources = {n: z.read(n).decode('utf-8', 'replace')
                       for n in names if n.endswith('.py')}
    exposed_modules = set()
    for path in (ROOT / 'catalog' / 'examples').glob('*.json'):
        doc = json.loads(path.read_text())
        exposed_modules.add(doc['public_api']['python']['module'])
    held_modules = []
    shared_modules = []
    for path in REVIEW_DOCS.glob('*.json'):
        doc = json.loads(path.read_text())
        module = doc['public_api']['python']['module']
        (shared_modules if module in exposed_modules else held_modules).append(
            module.replace('.', '/') + '.py')
    held_symbols = []
    for path in REVIEW_DOCS.glob('*.json'):
        doc = json.loads(path.read_text())
        held_symbols.append(doc['public_api']['python']['symbol'])
    module_hits = sorted(m for m in held_modules if m in names)
    shared_hits = sorted(m for m in shared_modules if m in names)
    symbol_hits = {}
    for symbol in held_symbols:
        pattern = re.compile(r'^def ' + re.escape(symbol) + r'\b', re.M)
        hits = sorted(n for n, text in sources.items() if pattern.search(text))
        if hits:
            symbol_hits[symbol] = hits
    report = {
        'schema': 'scirel.wheel-exposure-proof',
        'wheel': wheel.name,
        'files': len(names),
        'held_modules_present': module_hits,
        'shared_modules_with_held_symbols_present': shared_hits,
        'held_symbol_definitions_present': symbol_hits,
        'candidate_paths_present': sorted(n for n in names if 'candidate' in n or 'catalog' in n),
    }
    text = json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n')
    return 1 if (module_hits or symbol_hits or report['candidate_paths_present']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
