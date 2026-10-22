"""Portable product-byte and read-only consumer boundaries.

All catalog records, outputs, wheel bytes and 0/1 identity values in this file
are synthetic fixtures. These tests make no scientific or platform claim and
never build documentation, build/install a wheel, or run an MCP transport.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_pure_delivery as delivery  # noqa: E402
import consumer_tools  # noqa: E402
from query import Consumer, encode, sha  # noqa: E402

SOURCE = '0' * 40
ASSET = 'scirel.synthetic.alpha'
WHEEL_BYTES = b'Synthetic fixture only; this is not an installable wheel.\n'


def _write_snapshot(root: Path, *, count=2, summary_chars=0):
    root.mkdir()
    names = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'eta', 'theta', 'zeta'][:count]
    records, documents, files = [], {}, {'wheel/synthetic.whl': WHEEL_BYTES}
    for name in names:
        asset = 'scirel.synthetic.' + name
        record = {
            'asset_id': asset, 'symbol': name, 'capability': 'synthetic scalar',
            'capability_summary': 'Unvalidated fixture ' + 'x' * summary_chars,
            'operation': 'evaluate', 'operation_direction': 'input to output',
            'model': 'synthetic algebraic fixture', 'geometry': 'scalar',
            'coordinates': 'none', 'boundary': 'unknown',
            'device_scope': 'unclassified', 'aliases': ['synthetic', name],
            'title_zh': '合成示例',
        }
        records.append(record)
        documents[asset] = {
            'asset_id': asset, 'notice': 'Synthetic fixture; no scientific validation.',
            'inputs': [{'name': 'x', 'units': '1', 'shape': 'scalar'}],
            'outputs': [{'name': 'value', 'units': '1', 'shape': 'scalar'}],
            'example': {'code': 'print(0)', 'output': '0'},
        }
        files[f'catalog/contracts/{asset}.json'] = encode(documents[asset])
    files['catalog/capability-index.json'] = encode({
        'schema': 'scirel.capability-index', 'source_revision': SOURCE,
        'asset_count': len(records), 'assets': records,
        'search_text': {r['asset_id']: ' '.join((r['asset_id'], 'synthetic scalar',
                                              r['symbol'], '合成示例')) for r in records},
    })
    for relative, data in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    metadata = {
        'schema': 'scirel.consumer-runtime',
        'source_revision': SOURCE, 'asset_count': len(records),
        'runtime': {'wheel': 'synthetic.whl', 'wheel_sha256': sha(WHEEL_BYTES),
                    'requires_python': '>=3.14,<3.15',
                    'requires_dist': ['numpy', 'scipy', 'mpmath'],
                    'dependencies_bundled': False},
        'retrieval': {'backend': 'lexical-and', 'completeness': 'unknown',
                      'scientific_applicability': 'not_assessed',
                      'incomplete_status': 'retrieval_incomplete'},
    }
    manifest = delivery.seal_runtime(root, metadata)
    return root, manifest, documents


@pytest.fixture
def snapshot(tmp_path):
    return _write_snapshot(tmp_path / 'consumer')


def _pins(manifest):
    return {'expected_snapshot_sha256': manifest['snapshot_sha256'],
            'expected_wheel_sha256': manifest['runtime']['wheel_sha256']}


def _reseal(root):
    manifest = json.loads((root / 'runtime.json').read_bytes())
    return delivery.seal_runtime(root, {key: value for key, value in manifest.items()
                                if key not in {'files', 'snapshot_sha256'}})


def test_runtime_identity_binds_nested_product_members(tmp_path):
    root = tmp_path / 'sealed'
    (root / 'nested').mkdir(parents=True)
    (root / 'nested/runtime.json').write_bytes(b'{"synthetic":true}\n')
    manifest = delivery.seal_runtime(root, {'schema': 'synthetic.fixture'})
    assert manifest['files']['nested/runtime.json'] == {
        'sha256': sha(b'{"synthetic":true}\n'), 'bytes': len(b'{"synthetic":true}\n')}
    unsigned = {key: value for key, value in manifest.items() if key != 'snapshot_sha256'}
    assert manifest['snapshot_sha256'] == sha(encode(unsigned))



def test_export_archives_are_byte_stable_and_refuse_to_overwrite(snapshot, tmp_path):
    root, _, _ = snapshot
    first = delivery.archive(root, tmp_path / 'first.zip')
    second = delivery.archive(root, tmp_path / 'second.zip')
    assert first['sha256'] == second['sha256']
    assert first['bytes'] == second['bytes']
    with ZipFile(first['path']) as archive:
        assert set(archive.namelist()) == {
            path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
        assert archive.read('runtime.json') == (root / 'runtime.json').read_bytes()
    original = Path(first['path']).read_bytes()
    with pytest.raises(FileExistsError):
        delivery.archive(root, Path(first['path']))
    assert Path(first['path']).read_bytes() == original



def test_exact_snapshot_verifies_without_claiming_scientific_execution(snapshot):
    root, manifest, _ = snapshot
    result = Consumer(root).verify()
    assert result['outcome'] == 'ok'
    assert result['snapshot_sha256'] == manifest['snapshot_sha256']
    assert result['wheel_sha256'] == sha(WHEEL_BYTES)
    assert result['scientific_runtime_revalidated'] is False


@pytest.mark.parametrize('change', ['extra', 'missing', 'tamper', 'symlink'])
def test_verify_rejects_changed_or_unbound_product_members(snapshot, change, tmp_path):
    root, _, _ = snapshot
    member = root / f'catalog/contracts/{ASSET}.json'
    if change == 'extra':
        (root / 'extra.txt').write_text('Unbound')
    elif change == 'missing':
        member.unlink()
    elif change == 'tamper':
        member.write_text('Changed result')
    else:
        outside = tmp_path / 'outside.json'
        outside.write_bytes(member.read_bytes())
        member.unlink()
        member.symlink_to(outside)
    with pytest.raises((OSError, ValueError)):
        Consumer(root).verify()


@pytest.mark.parametrize('relative', ['../outside', '/outside', 'docs/../outside',
                                     'docs\\outside', 'C:/outside', './runtime.json'])
def test_member_read_rejects_unsafe_paths(snapshot, relative):
    root, _, _ = snapshot
    with pytest.raises(ValueError):
        Consumer(root).read(relative)


def test_runtime_identity_tamper_and_symlink_cannot_establish_a_snapshot(snapshot, tmp_path):
    root, _, _ = snapshot
    path = root / 'runtime.json'
    data = json.loads(path.read_bytes())
    data['asset_count'] += 1
    path.write_bytes(encode(data))
    with pytest.raises(ValueError):
        Consumer(root)
    outside = tmp_path / 'runtime-copy.json'
    outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ValueError):
        Consumer(root)


def test_mcp_registry_contains_only_read_only_product_tools():
    definitions = consumer_tools.tools()
    assert {item['name'] for item in definitions} == {
        'scirel_describe', 'scirel_browse', 'scirel_search', 'scirel_get'}
    assert all(item['annotations']['readOnlyHint'] is True and
               item['annotations']['destructiveHint'] is False for item in definitions)
    for item in definitions:
        if item['name'] != 'scirel_describe':
            assert {'expected_snapshot_sha256', 'expected_wheel_sha256'} <= set(item['inputSchema']['required'])


def test_describe_then_exact_get_bind_the_full_original_contract(snapshot):
    root, manifest, documents = snapshot
    describe = consumer_tools.call_tool(root, 'scirel_describe')
    assert describe['outcome'] == 'ok'
    assert describe['snapshot_sha256'] == manifest['snapshot_sha256']
    assert describe['wheel_sha256'] == sha(WHEEL_BYTES)
    assert describe['human_documentation'] == {'status': 'unconfigured', 'locator': 'asset_id'}
    args = {**_pins(manifest), 'asset_id': ASSET}
    original = dict(args)
    result = consumer_tools.call_tool(root, 'scirel_get', args)
    assert args == original
    assert result['outcome'] == 'ok'
    assert result['document'] == documents[ASSET]
    assert result['paths'] == {'contract': f'catalog/contracts/{ASSET}.json'}
    assert all(manifest['files'][path]['sha256'] == digest for path, digest in result['digests'].items())
    assert consumer_tools.call_tool(root, 'scirel_get', {
        **_pins(manifest), 'asset_id': 'scirel.synthetic.absent'})['outcome'] == 'unknown_asset'


def test_get_returns_a_complete_original_contract_larger_than_card_budget(snapshot):
    root, _, documents = snapshot
    original = {**documents[ASSET], 'detailed_evidence': {
        'unicode_text': '原始合同参数和适用范围' * 4000,
        'nested': [{'values': [0, 1.25, None, True], 'final': 'end-of-contract'}],
    }}
    path = f'catalog/contracts/{ASSET}.json'
    data = encode(original)
    assert len(data) > 65536
    (root / path).write_bytes(data)
    manifest = _reseal(root)
    result = consumer_tools.call_tool(root, 'scirel_get', {**_pins(manifest), 'asset_id': ASSET})
    assert result['outcome'] == 'ok'
    assert result['document'] == original
    assert len(json.dumps(result, ensure_ascii=False).encode()) > 65536
    assert result['digests'] == {path: sha(data)}


@pytest.mark.parametrize('field', ['expected_snapshot_sha256', 'expected_wheel_sha256'])
def test_read_rejects_a_different_selected_candidate(snapshot, field):
    root, manifest, _ = snapshot
    args = {**_pins(manifest), 'asset_id': ASSET, field: 'f' * 64}
    result = consumer_tools.call_tool(root, 'scirel_get', args)
    assert result['outcome'] == 'identity_mismatch'
    assert 'document' not in result


@pytest.mark.parametrize('name,args', [
    ('scirel_execute', {}), ('scirel_search', {}),
    ('scirel_get', {'asset_id': ASSET}),
    ('scirel_describe', {'unexpected': True}),
])
def test_dispatch_rejects_unknown_tools_arguments_and_missing_pins(snapshot, name, args):
    root, _, _ = snapshot
    assert consumer_tools.call_tool(root, name, args)['outcome'] == 'invalid_request'


@pytest.mark.parametrize('overrides', [
    {'limit': 0}, {'limit': 101}, {'limit': True}, {'offset': -1},
    {'max_bytes': 4095}, {'max_bytes': True}, {'q': ['synthetic']},
    {'expected_snapshot_sha256': 'x' * 64},
])
def test_query_rejects_invalid_bounds_types_and_pin_shape(snapshot, overrides):
    root, manifest, _ = snapshot
    result = consumer_tools.call_tool(root, 'scirel_search', {**_pins(manifest), **overrides})
    assert result['outcome'] == 'invalid_request'


def test_no_candidates_is_retrieval_evidence_not_a_metadata_failure(snapshot):
    root, manifest, _ = snapshot
    result = consumer_tools.call_tool(root, 'scirel_search', {
        **_pins(manifest), 'q': 'absent-unvalidated-token', 'limit': 1})
    assert result['outcome'] == 'no_candidates'
    assert result['result']['items'] == []
    assert result['result']['retrieval']['completeness'] == 'unknown'
    assert result['result']['retrieval']['scientific_applicability'] == 'not_assessed'


def test_bounded_cursor_pages_cover_the_selected_query_without_duplicates(snapshot):
    root, manifest, _ = snapshot
    args = {**_pins(manifest), 'limit': 1}
    page = consumer_tools.call_tool(root, 'scirel_browse', args)
    seen = [item['asset_id'] for item in page['result']['items']]
    assert page['next_cursor']
    second = consumer_tools.call_tool(root, 'scirel_browse', {**args, 'cursor': page['next_cursor']})
    seen.extend(item['asset_id'] for item in second['result']['items'])
    assert seen == sorted(Consumer(root).assets)
    assert second['next_cursor'] is None
    assert consumer_tools.call_tool(root, 'scirel_search', {
        **args, 'q': 'alpha', 'cursor': page['next_cursor']})['outcome'] == 'invalid_request'
    assert consumer_tools.call_tool(root, 'scirel_browse', {
        **args, 'offset': 0, 'cursor': page['next_cursor']})['outcome'] == 'invalid_request'


def test_candidate_cards_respect_byte_budget_and_resume_without_omissions(tmp_path):
    root, manifest, _ = _write_snapshot(tmp_path / 'large', count=8, summary_chars=800)
    args = {**_pins(manifest), 'limit': 8, 'max_bytes': 4096}
    seen, cursor, truncated = [], None, False
    for _ in range(8):
        page = consumer_tools.call_tool(root, 'scirel_browse',
                                        {**args, **({'cursor': cursor} if cursor else {})})
        assert page['outcome'] == 'match', page
        assert len(json.dumps(page, ensure_ascii=False).encode()) <= args['max_bytes']
        seen.extend(item['asset_id'] for item in page['result']['items'])
        truncated |= page['truncated']
        cursor = page['next_cursor']
        if cursor is None:
            break
    assert cursor is None and truncated
    assert seen == sorted(Consumer(root).assets)
    assert len(seen) == len(set(seen)) == 8


def test_one_oversized_card_returns_an_explicit_budget_error(tmp_path):
    root, manifest, _ = _write_snapshot(tmp_path / 'oversized', count=1, summary_chars=10000)
    result = consumer_tools.call_tool(root, 'scirel_browse', {
        **_pins(manifest), 'limit': 1, 'max_bytes': 4096})
    assert result['outcome'] == 'response_too_large'
    assert 'result' not in result


def test_corrupt_index_is_metadata_error_instead_of_no_candidates(snapshot):
    root, _, _ = snapshot
    path = root / 'catalog/capability-index.json'
    index = json.loads(path.read_bytes())
    index['assets'][0]['device_scope'] = 'invented-scope'
    path.write_bytes(encode(index))
    manifest = _reseal(root)
    result = consumer_tools.call_tool(root, 'scirel_search', {**_pins(manifest), 'q': 'alpha'})
    assert result['outcome'] == 'metadata_error'
    assert 'result' not in result


@pytest.mark.parametrize('replacement', [{'asset_id': 'scirel.synthetic.wrong'}, []])
def test_get_rejects_wrong_or_malformed_selected_contract_identity(snapshot, replacement):
    root, _, _ = snapshot
    (root / f'catalog/contracts/{ASSET}.json').write_bytes(encode(replacement))
    manifest = _reseal(root)
    result = consumer_tools.call_tool(root, 'scirel_get', {**_pins(manifest), 'asset_id': ASSET})
    assert result['outcome'] == 'metadata_error'
    assert 'document' not in result


@pytest.mark.parametrize('malformation', ['runtime_missing', 'not_object'])
def test_malformed_runtime_identity_returns_metadata_error_without_uncaught_exceptions(snapshot, malformation):
    root, _, _ = snapshot
    path = root / 'runtime.json'
    if malformation == 'not_object':
        path.write_bytes(encode([]))
    else:
        manifest = json.loads(path.read_bytes())
        del manifest['runtime']
        del manifest['snapshot_sha256']
        manifest['snapshot_sha256'] = sha(encode(manifest))
        path.write_bytes(encode(manifest))
    result = consumer_tools.call_tool(root, 'scirel_describe')
    assert result['outcome'] == 'metadata_error'
