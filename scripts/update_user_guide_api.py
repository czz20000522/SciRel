"""Refresh documentation from a bound wheel/catalog without importing science."""
import argparse
import ast
import email
import hashlib
import json
from pathlib import Path
import zipfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True, help='release.json')
    parser.add_argument('--guide', type=Path, default=Path('docs/user-guide'))
    args = parser.parse_args()
    binding = json.loads((args.guide / 'binding.json').read_text())
    topics = json.loads((args.guide / 'api-topics.json').read_text())
    raw = args.wheel.read_bytes()
    if sha(raw) != binding['wheel_sha256']:
        raise ValueError('Wheel differs from the separately supplied version binding')
    catalog_raw = args.catalog.read_bytes()
    if sha(catalog_raw) != binding['catalog_sha256']:
        raise ValueError('Catalog differs from the separately supplied version binding')
    catalog = json.loads(catalog_raw)
    if catalog['release_version'] != binding['package_version']:
        raise ValueError('Catalog version mismatch')
    records = {}
    for part in catalog['partitions']:
        file = (args.catalog.parent / part['path']).resolve()
        if not file.is_relative_to(args.catalog.parent.resolve()):
            raise ValueError('Catalog path escapes its root')
        data = file.read_bytes()
        if sha(data) != part['sha256'].removeprefix('sha256:') or len(data) != part['bytes']:
            raise ValueError('Catalog partition integrity mismatch')
        if part['path'].startswith('records/'):
            document = json.loads(data)
            api = document['public_api']['python']
            if document['version']['implementation_version'] != binding['package_version']:
                raise ValueError('Exact record version mismatch')
            records[api['module'] + '.' + api['symbol']] = (document, part)
    apis = []
    with zipfile.ZipFile(args.wheel) as wheel:
        metadata = [n for n in wheel.namelist() if n.endswith('.dist-info/METADATA')]
        if len(metadata) != 1:
            raise ValueError('Ambiguous wheel metadata')
        if email.message_from_bytes(wheel.read(metadata[0]))['Version'] != binding['package_version']:
            raise ValueError('Wheel version mismatch')
        for member in sorted(n for n in wheel.namelist() if n.startswith('scirel/') and n.endswith('.py')):
            tree = ast.parse(wheel.read(member).decode('utf-8'))
            exports = next((ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == '_EXPORTS' for t in n.targets)), None)
            if exports is None:
                continue
            module = member[:-3].replace('/', '.')
            for symbol, implementation_module in exports.items():
                identity = module + '.' + symbol
                if identity not in topics:
                    raise ValueError(f'Assign a reviewed physical topic/title before importing {identity}')
                implementation = wheel.read('scirel/_vendor/tokagrad/' + implementation_module + '.py')
                node = next(n for n in ast.parse(implementation.decode('utf-8')).body
                            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == symbol)
                entry = {'id': identity, 'module': module, 'symbol': symbol, **topics[identity],
                         'kind': 'class' if isinstance(node, ast.ClassDef) else 'function',
                         'implementation_member_sha256': sha(implementation),
                         'status': 'bound-detailed-compatibility-contract' if identity in records else 'compatibility-reference-limited',
                         'notes': ['Exact development wheel interface; source behavior is not independent scientific qualification.']}
                if isinstance(node, ast.FunctionDef):
                    entry['signature'] = symbol + '(' + ast.unparse(node.args) + ')' + (
                        ' -> ' + ast.unparse(node.returns) if node.returns else '')
                else:
                    fields = [{'name': n.target.id, 'annotation': ast.unparse(n.annotation),
                               'default_source': ast.unparse(n.value) if n.value is not None else None}
                              for n in node.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)]
                    entry['fields'] = fields
                    entry['signature'] = symbol + '(' + ', '.join(
                        f['name'] + ': ' + f['annotation'] + (' = ' + f['default_source'] if f['default_source'] is not None else '')
                        for f in fields) + ')'
                    entry['methods'] = [{'name': n.name, 'signature': n.name + '(' + ast.unparse(n.args) + ')'}
                                        for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]
                entry['source_docstring'] = ast.get_docstring(node) or None
                if identity in records:
                    document, part = records[identity]
                    keys = ['asset_id', 'schema', 'title', 'summary', 'identity', 'inputs', 'outputs', 'applicability',
                            'failure_semantics', 'public_api', 'example', 'verification', 'version', 'provenance']
                    entry['contract_projection'] = {k: document[k] for k in keys if k in document}
                    entry['contract_projection']['projection_note'] = 'Generated selected fields from the bound canonical record; not a separately authored scientific contract.'
                    entry['canonical_catalog_record'] = {'path': part['path'], 'sha256': part['sha256'].removeprefix('sha256:')}
                apis.append(entry)
    if len(apis) != binding['public_entries'] or len({a['module'] for a in apis}) != binding['public_modules']:
        raise ValueError('API count differs from version binding')
    if len(records) != binding['detailed_contracts']:
        raise ValueError('Contract count differs from version binding')
    snapshot = {'schema': 'scirel.user-guide-api-snapshot.v1', 'binding': binding,
                'derivation': 'Read-only AST extraction of the exact wheel and selected fields of seven canonical records. Do not edit generated API/contract fields manually.',
                'apis': apis}
    (args.guide / 'api-snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'public_entries': len(apis), 'detailed_contracts': len(records), 'science_imported': False}))


if __name__ == '__main__':
    main()
