"""Export a self-contained query runtime from the public catalog and exact wheel."""
from __future__ import annotations

import argparse
import email
import io
import json
from pathlib import Path
import tempfile
import zipfile

from capability_catalog import PublicCatalog
from check_wheel_exposure import inspect_wheel
from query import encode, sha
from solving_skill import load_solving_skill
from validate_asset_documents import resolve_test_reference, validate_runtime
from validate_installed_wheel import _catalog_wheel_closure

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_TOOLS = {
    'capability_query.py': 'capability_query.py', 'query.py': 'query.py',
    'consumer_tools.py': 'consumer_tools.py', 'serve_consumer_mcp.py': 'server.py',
}
BUILD_INPUTS = (
    'build_pure_delivery.py', 'capability_catalog.py', 'capability_query.py',
    'query.py', 'consumer_tools.py', 'serve_consumer_mcp.py', 'solving_skill.py',
    'validate_asset_documents.py', 'public_api_binding.py', 'check_wheel_exposure.py',
    'validate_installed_wheel.py', 'exposure.py',
)


def seal_runtime(directory, metadata):
    files = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('delivery contains symlink: ' + str(path))
        if path.is_file() and path != directory / 'runtime.json':
            data = path.read_bytes()
            files[path.relative_to(directory).as_posix()] = {'sha256': sha(data), 'bytes': len(data)}
    identity = {**metadata, 'files': files}
    identity['snapshot_sha256'] = sha(encode(identity))
    (directory / 'runtime.json').write_bytes(encode(identity))
    return identity



def archive(directory, target):
    if target.exists():
        raise FileExistsError(target)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(directory).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                output.writestr(info, path.read_bytes())
    return {'path': str(target), 'sha256': sha(target.read_bytes()), 'bytes': target.stat().st_size}



def consumer_index(full_index):
    """Project source discovery into the metadata used by both runtime callers."""
    fields = ('asset_id', 'symbol', 'capability', 'capability_summary', 'operation',
              'operation_direction', 'model', 'geometry', 'coordinates', 'boundary',
              'device_scope', 'device_scope_source', 'aliases', 'taxonomy', 'title_zh')
    index = {key: full_index[key] for key in ('schema', 'source_revision', 'asset_count')}
    index['assets'] = [{key: record[key] for key in fields} for record in full_index['assets']]
    index['search_text'] = full_index['search_text']
    index['derivation'] = 'Read-only projection of exact public contracts and bound Chinese reader; selected ports/evidence are in get.'
    return index



def _export(wheel, output):
    """Capture, validate and write one runtime; scientific callables are not run."""
    if output.exists():
        raise FileExistsError('refusing overwrite: ' + str(output))
    source = PublicCatalog(ROOT)
    revision = source.identity['source_revision']
    if source.identity['source_dirty']:
        raise ValueError('source must be clean before binding a runtime')
    for name in BUILD_INPUTS:
        source._read('scripts/' + name)
    source._read('pyproject.toml')
    source._read('tools/docs/mcp-requirements.txt')
    mapping = ROOT / 'scripts/mapping_interface_bindings.json'
    if mapping.is_file():
        source._read('scripts/mapping_interface_bindings.json')
    for document in source.documents.values():
        for reference in document['verification']['tests']:
            path = resolve_test_reference(reference, ROOT)
            source._read(path.relative_to(ROOT).as_posix())
        validate_runtime(document, source_root=ROOT)
    skill_root = ROOT / 'skills/development/usage/scirel-solving'
    skill_inputs = load_solving_skill(skill_root)
    for relative, data in skill_inputs.items():
        key = 'skills/development/usage/scirel-solving/' + relative
        source.input_bytes[key] = data
        source.input_digests[key] = sha(data)

    wheel_bytes = wheel.read_bytes()
    proof = inspect_wheel(wheel, source_root=ROOT / 'src')
    if proof['status'] != 'PASS':
        raise ValueError('exact wheel inspection failed: ' + json.dumps(proof))
    if sha(wheel_bytes) != proof['sha256']:
        raise ValueError('wheel changed during inspection')
    catalog_wheel, errors = _catalog_wheel_closure(ROOT, wheel, expected_source_revision=revision)
    if errors or catalog_wheel['status'] != 'PASS':
        raise ValueError('catalog/source/wheel closure failed: ' + str(errors))
    notices = sorted(path for path in (ROOT / 'licenses').rglob('*') if path.is_file())
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
        members = archive.namelist()
        metadata = email.message_from_bytes(archive.read(next(
            name for name in members if name.endswith('.dist-info/METADATA'))))
        for name in members:
            if name.startswith('scirel/') and not name.endswith('/'):
                captured = source._read('src/' + name)
                if captured != archive.read(name):
                    raise ValueError('wheel package bytes differ from captured source: ' + name)
        for path in notices:
            relative = path.relative_to(ROOT).as_posix()
            captured = source._read(relative)
            suffix = '/licenses/' + relative
            matches = [name for name in members if name.endswith(suffix)]
            if len(matches) != 1 or archive.read(matches[0]) != captured:
                raise ValueError('wheel notice bytes differ from source: ' + relative)

    output.mkdir(parents=True)

    def put(relative, data):
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    put('wheel/' + wheel.name, wheel_bytes)
    for name, target in RUNTIME_TOOLS.items():
        put('tools/' + target, source.input_bytes['scripts/' + name])
    for relative, data in skill_inputs.items():
        put('skills/scirel-solving/' + relative, data)
    put('mcp-requirements.txt', source.input_bytes['tools/docs/mcp-requirements.txt'])
    put('mcp-connections.json', encode({
        'stdio': {'command': 'python', 'args': ['tools/server.py', '--root', '.', '--transport', 'stdio']},
        'streamable_http': {'url': 'http://127.0.0.1:8765/mcp'}}))
    for asset in sorted(source.documents):
        put('catalog/contracts/' + asset + '.json',
            source.input_bytes['catalog/examples/' + asset + '.json'])
    put('catalog/capability-index.json', encode(consumer_index(source.index)))
    requirements = metadata.get_all('Requires-Dist', [])
    put('runtime-requirements.txt', ('# Derived from the exact delivered wheel METADATA. Python '
        + metadata['Requires-Python'] + '\n' + '\n'.join(requirements) + '\n').encode())
    runtime = {'package_version': metadata['Version'], 'requires_python': metadata['Requires-Python'],
               'requires_dist': requirements, 'wheel': wheel.name, 'wheel_sha256': sha(wheel_bytes),
               'dependencies_bundled': False}
    source.verify_unchanged()
    if load_solving_skill(skill_root) != skill_inputs:
        raise ValueError('solving source changed during export')
    if sorted(path for path in (ROOT / 'licenses').rglob('*') if path.is_file()) != notices:
        raise ValueError('license source membership changed during export')
    if wheel.read_bytes() != wheel_bytes:
        raise ValueError('wheel changed during export')
    identity = seal_runtime(output, {'schema': 'scirel.consumer-runtime',
        'source_revision': revision, 'asset_count': len(source.documents), 'runtime': runtime,
        'retrieval': {'backend': 'lexical-and', 'ranking_method': 'weighted-lexical',
            'completeness': 'unknown', 'scientific_applicability': 'not_assessed',
            'incomplete_status': 'retrieval_incomplete'}})
    closure = {'schema': 'scirel.consumer-source-closure', 'source_revision': revision,
               'asset_count': len(source.documents), 'source_signature_check': 'PASS',
               'source_inputs': dict(sorted(source.input_digests.items())),
               'scientific_runtime_revalidated': False, 'catalog_wheel_closure': catalog_wheel}
    return {'agent': identity, 'checks': {'source_closure': closure, 'wheel_inspection': proof}}


def build(wheel, output):
    """Publish one complete runtime atomically, cleaning owned stages on failure."""
    wheel, output = Path(wheel), Path(output)
    if output.exists():
        raise FileExistsError('refusing overwrite: ' + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.scirel-runtime-stage-', dir=output.parent) as temp:
        stage = Path(temp) / 'runtime'
        result = _export(wheel, stage)
        stage.rename(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.wheel, args.output)
    print(json.dumps({'snapshot_sha256': result['agent']['snapshot_sha256'],
                      'checks': result['checks']}, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
