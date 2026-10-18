"""Portable discovery preserves exact contracts while limiting context output."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'skills/development/usage/scientific-asset-navigation/scripts/query.py'
spec = importlib.util.spec_from_file_location('navigation_query', TOOL)
query = importlib.util.module_from_spec(spec)
spec.loader.exec_module(query)


def bind(root, files, count):
    manifest = dict(schema='scirel.documentation-snapshot.v1', asset_count=count,
                    files={})
    for path, obj in files.items():
        data = query.encode(obj)
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifest['files'][path] = dict(bytes=len(data), sha256=query.hashlib.sha256(data).hexdigest())
    manifest['snapshot_sha256'] = query.hashlib.sha256(query.encode(manifest)).hexdigest()
    (root / 'manifest.json').write_bytes(query.encode(manifest))


@pytest.fixture
def snapshot(tmp_path):
    ids = ['scirel.kinetic.kinetic-dispersion-relation',
           'scirel.kinetic.kinetic-dispersion-ronnmark',
           'scirel.kinetic.species-equilibrium-scales']
    docs = [json.loads((ROOT / 'catalog/examples' / (a + '.json')).read_text()) for a in ids]
    cards = [dict(asset_id=d['asset_id'], kind=d['kind'], title=d['title'],
                  summary_zh=d['summary'], public_api=d['public_api'],
                  search_text=json.dumps(d).lower()) for d in docs]
    book = dict(chapters=[dict(id='waves', title='Waves', topics=[
        dict(id='tensor', title='Tensor', introduction='Dielectric response', assets=ids[:2]),
        dict(id='scale', title='Scales', introduction='Species scales', assets=ids[2:])])])
    bind(tmp_path, {'index.json': cards, 'handbook.json': book,
                   **{'records/' + d['asset_id'] + '.json': d for d in docs}}, 3)
    return tmp_path


def test_routes_candidates_and_exact_contract_are_distinct(snapshot):
    catalog = query.Catalog(snapshot)
    assert catalog.routes()['items'] == [dict(id='waves', title='Waves', topic_count=2, asset_count=3)]
    assert {t['id'] for t in catalog.routes('waves')['items']} == {'tensor', 'scale'}
    first = catalog.search(topic='tensor', limit=1)
    assert first['total'] == 2 and first['next_offset'] == 1
    assert first['items'][0]['kind'] == 'task_graph'
    assert not {'document', 'search_text', 'version'} & first['items'][0].keys()
    second = catalog.search(topic='tensor', offset=1, limit=1)
    assert second['items'][0]['kind'] == 'operator' and second['next_offset'] is None
    asset = first['items'][0]['asset_id']
    original = json.loads((ROOT / 'catalog/examples' / (asset + '.json')).read_text())
    assert catalog.show(asset, 'full')['document'] == original
    call = catalog.show(asset)['document']
    for field in ['inputs', 'outputs', 'applicability', 'failure_semantics', 'verification', 'example', 'public_api']:
        assert call[field] == original[field]
    assert 'graph' not in call and call['graph_execution'] == original['graph']['execution']
    assert catalog.show(asset, 'graph')['graph'] == original['graph']


def test_zero_hits_and_partial_pages_do_not_assert_absence(snapshot):
    catalog = query.Catalog(snapshot)
    result = catalog.search('no-such-relation')
    assert result['total'] == 0 and result['indexed_assets'] == 3
    assert result['coverage'].startswith('bound documentation snapshot only')
    assert 'zero keyword hits do not establish a gap' in result['applicability']
    assert catalog.search(topic='tensor', kind='operator')['total'] == 1
    assert catalog.search(q='ronnmark')['total'] == 2
    for kwargs in [dict(), dict(q='x', limit=21), dict(q='x', offset=-1), dict(q='x'*513)]:
        with pytest.raises(ValueError):
            catalog.search(**kwargs)
    with pytest.raises(KeyError):
        catalog.search(topic='unknown')


def test_changed_bytes_and_wrong_identity_fail_closed(snapshot):
    with pytest.raises(ValueError, match='expected digest'):
        query.Catalog(snapshot, '0'*64)
    catalog = query.Catalog(snapshot)
    asset = next(iter(catalog.records))
    (snapshot / 'records' / (asset + '.json')).write_text('{}')
    with pytest.raises(ValueError, match='bytes changed'):
        catalog.show(asset)
    (snapshot / 'index.json').write_text('[]')
    with pytest.raises(ValueError, match='bytes changed'):
        query.Catalog(snapshot)


def test_incomplete_routes_fail_instead_of_hiding_assets(snapshot):
    files = {p.relative_to(snapshot).as_posix(): json.loads(p.read_text())
             for p in snapshot.rglob('*.json') if p.name != 'manifest.json'}
    files['handbook.json']['chapters'][0]['topics'].pop()
    bind(snapshot, files, 3)
    with pytest.raises(ValueError, match='route coverage'):
        query.Catalog(snapshot)


def test_cli_is_source_free_and_errors_are_not_empty_results(snapshot, tmp_path):
    # Python -I cannot resolve repository modules; only the shipped script is needed.
    result = subprocess.run([sys.executable, '-I', str(TOOL), '--snapshot', str(snapshot),
                             'search', '--topic', 'tensor', '--limit', '1'],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0 and len(json.loads(result.stdout)['items']) == 1
    result = subprocess.run([sys.executable, '-I', str(TOOL), '--snapshot', str(snapshot),
                             'show', '../manifest'], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)['outcome'] == 'catalog_unavailable_not_capability_absent'
    probe = subprocess.run(
        [
            sys.executable,
            '-I',
            '-c',
            '''
import runpy, sys
tool, snapshot = sys.argv[1:]
sys.argv = [tool, '--snapshot', snapshot, 'search', '--topic', 'tensor', '--limit', '1']
try:
    runpy.run_path(tool, run_name='__main__')
except SystemExit as error:
    assert error.code == 0
assert not any(name == 'scirel' or name.startswith('scirel.') for name in sys.modules)
''',
            str(TOOL),
            str(snapshot),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr


def test_renamed_delivery_locates_its_own_snapshot_from_unrelated_cwd(snapshot, tmp_path):
    root = tmp_path / 'assets'
    shipped = root / TOOL.relative_to(ROOT)
    shipped.parent.mkdir(parents=True)
    shutil.copy2(TOOL, shipped)
    manual = root / 'docs/manual'
    manual.mkdir(parents=True)
    for name in ['manifest.json', 'index.json', 'handbook.json']:
        shutil.copy2(snapshot / name, manual / name)
    shutil.copytree(snapshot / 'records', manual / 'records')
    cwd = tmp_path / 'unrelated'
    cwd.mkdir()
    result = subprocess.run([sys.executable, '-I', str(shipped), 'routes'],
                            cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['indexed_assets'] == 3


def test_cli_call_contract_fits_transport_without_losing_diagnostics(tmp_path):
    asset = 'scirel.kinetic.pdrf-dispersion-scan'
    doc = json.loads((ROOT / 'catalog/examples' / (asset + '.json')).read_text())
    book = {'chapters': [{'id': 'waves', 'title': 'Waves', 'topics': [
        {'id': 'scan', 'title': 'Scan', 'introduction': 'Spectrum', 'assets': [asset]}]}]}
    bind(tmp_path, {'index.json': [{'asset_id': asset}], 'handbook.json': book,
                    'records/' + asset + '.json': doc}, 1)
    result = subprocess.run([sys.executable, '-I', str(TOOL), '--snapshot', str(tmp_path),
                             'show', asset], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert len(result.stdout) < 24000  # actual consumer tool response character limit
    assert len(result.stdout.splitlines()) == 1
    actual = json.loads(result.stdout)['document']
    for field in ['inputs', 'outputs', 'failure_semantics', 'verification', 'applicability']:
        assert actual[field] == doc[field]
    assert actual['graph_execution'] == doc['graph']['execution']
