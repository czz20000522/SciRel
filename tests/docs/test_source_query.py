"""Public working-tree queries need neither a wheel nor a generated snapshot."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from fs_links import directory_link, file_link_or_reparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from capability_query import query_capabilities  # noqa: E402
import scirel_docs  # noqa: E402
import capability_catalog  # noqa: E402
from scirel_docs import SourceDocumentation, encode, sha  # noqa: E402

ASSET = 'scirel.physics.coulomb-ee'
HELD = 'scirel.test.withheld'


def git(root, *arguments):
    return subprocess.check_output(['git', *arguments], cwd=root, text=True,
                                   stderr=subprocess.PIPE, timeout=10).strip()


def commit(root):
    git(root, 'add', '.')
    git(root, '-c', 'user.name=Source query fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '-qm', 'Bind public source fixture')


@pytest.fixture
def source(tmp_path):
    root = tmp_path / 'source'
    contracts = root / 'catalog/examples'
    contracts.mkdir(parents=True)
    contract = (ROOT / 'catalog/examples' / (ASSET + '.json')).read_bytes()
    (contracts / (ASSET + '.json')).write_bytes(contract)
    # This deliberately unreadable held payload must never be parsed, even by get.
    (contracts / (HELD + '.json')).write_text('held payload is not public JSON')
    hold = root / 'catalog/review/HOLD.json'
    hold.parent.mkdir()
    hold.write_bytes(encode({'schema': 'scirel.exposure-hold', 'assets': {
        HELD: {'status': 'human-review', 'reason': 'withheld', 'required_decision': 'review'}}}))
    (hold.parent / 'SOURCE_PROVENANCE.md').write_text('private history, outside query inputs')
    reader = next(record for path in (ROOT / 'tools/docs/zh').glob('*.json')
                  for record in json.loads(path.read_bytes())['records'] if record['asset_id'] == ASSET)
    readers = root / 'tools/docs/zh'
    readers.mkdir(parents=True)
    (readers / 'reader.json').write_bytes(encode({
        'schema': 'scirel.reader-translation', 'language': 'zh-CN', 'records': [reader]}))
    git(root, 'init', '-q')
    commit(root)
    return root


def cli(source, *arguments):
    return subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/scirel_docs.py'),
                           'query', '--source-root', str(source), *arguments],
                          text=True, capture_output=True, timeout=20)


def test_source_describe_search_and_exact_get_reuse_the_public_projection(source, monkeypatch):
    read_bytes, read_text = Path.read_bytes, Path.read_text

    def public_only(path, original, *args, **kwargs):
        if (path == source / 'catalog/examples' / (HELD + '.json') or
                path.is_relative_to(source / 'catalog/review') and path.name != 'HOLD.json'):
            raise AssertionError('query read withheld payload or private review history')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_bytes', lambda path, *a, **kw: public_only(path, read_bytes, *a, **kw))
    monkeypatch.setattr(Path, 'read_text', lambda path, *a, **kw: public_only(path, read_text, *a, **kw))
    docs = SourceDocumentation(source)
    description = docs.describe()
    assert description['asset_count'] == 1
    assert description['source_revision'] == git(source, 'rev-parse', 'HEAD')
    assert description['source_dirty'] is False
    assert description['wheel_binding'] == 'not_bound'
    assert description['scientific_runtime_revalidated'] is False
    expected = query_capabilities(docs.index, {'schema': 'scirel.capability-query', 'q': 'coulomb', 'limit': 1})
    assert docs.capabilities(q='coulomb', limit=1)['result'] == expected
    assert all('record_path' not in item and 'docs_path' not in item for item in expected['items'])
    document = docs.asset(ASSET, reader=True)
    raw = (source / document['path']).read_bytes()
    assert document['document'] == json.loads(raw)
    assert document['sha256'] == document['translation']['source_sha256'] == sha(raw)
    assert docs.asset(HELD)['outcome'] == docs.asset('../review/SOURCE_PROVENANCE')['outcome'] == 'unknown_asset'
    assert set(docs.input_digests) == {
        'catalog/review/HOLD.json', 'catalog/examples/' + ASSET + '.json', 'tools/docs/zh/reader.json'}


def test_source_identity_binds_dirty_contract_reader_hold_and_head(source):
    initial = SourceDocumentation(source).describe()
    contract_path = source / 'catalog/examples' / (ASSET + '.json')
    document = json.loads(contract_path.read_bytes())
    document['summary'] += ' A changed public description.'
    contract_path.write_bytes(encode(document))
    reader_path = source / 'tools/docs/zh/reader.json'
    readers = json.loads(reader_path.read_bytes())
    readers['records'][0]['source_sha256'] = sha(contract_path.read_bytes())
    reader_path.write_bytes(encode(readers))
    changed = SourceDocumentation(source).describe()
    assert changed['source_revision'] == initial['source_revision']
    assert changed['source_dirty'] is True
    assert changed['source_inputs_sha256'] != initial['source_inputs_sha256']
    assert changed['source_identity_sha256'] != initial['source_identity_sha256']
    readers['records'][0]['summary'] += ' 阅读说明。'
    reader_path.write_bytes(encode(readers))
    reader_changed = SourceDocumentation(source).describe()
    assert reader_changed['source_inputs_sha256'] != changed['source_inputs_sha256']
    hold_path = source / 'catalog/review/HOLD.json'
    hold = json.loads(hold_path.read_bytes())
    hold['assets'][HELD]['status'] = 'rejected'
    hold_path.write_bytes(encode(hold))
    hold_changed = SourceDocumentation(source).describe()
    assert hold_changed['source_inputs_sha256'] != reader_changed['source_inputs_sha256']
    commit(source)
    committed = SourceDocumentation(source).describe()
    assert committed['source_dirty'] is False
    assert committed['source_revision'] != initial['source_revision']
    assert committed['source_inputs_sha256'] == hold_changed['source_inputs_sha256']
    with pytest.raises(ValueError, match='expected digest'):
        SourceDocumentation(source, initial['source_identity_sha256'])
    assert SourceDocumentation(source, committed['source_identity_sha256']).describe() == committed


def test_source_cli_runs_without_generated_inputs_or_scientific_imports(source):
    script = """
import builtins, json, sys
sys.path.insert(0, sys.argv[1])
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'scirel', 'numpy', 'scipy', 'mpmath', 'sphinx'}:
        raise AssertionError('query imported scientific/build dependency: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from scirel_docs import SourceDocumentation
print(json.dumps(SourceDocumentation(sys.argv[2]).describe()))
"""
    result = subprocess.run([sys.executable, '-B', '-c', script, str(ROOT / 'scripts'), str(source)],
                            text=True, capture_output=True, timeout=20, check=True)
    assert json.loads(result.stdout)['asset_count'] == 1
    described = cli(source, '--describe')
    assert described.returncode == 0
    identity = json.loads(described.stdout)['source_identity_sha256']
    found = cli(source, '--q', 'coulomb', '--limit', '1', '--expected-digest', identity)
    assert found.returncode == 0
    assert json.loads(found.stdout)['result']['items'][0]['asset_id'] == ASSET
    exact = cli(source, '--reader', ASSET)
    assert json.loads(exact.stdout)['translation']['asset_id'] == ASSET
    held = cli(source, '--asset', HELD)
    assert json.loads(held.stdout)['outcome'] == 'unknown_asset'
    no_hit = json.loads(cli(source, '--q', 'nonexistent-science-term').stdout)
    assert no_hit['outcome'] == 'no_candidates'
    assert no_hit['result']['retrieval']['outcome'] == 'no_hit'
    invalid = cli(source, '--limit', '0')
    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)['outcome'] == 'invalid_request'
    mixed = cli(source, '--snapshot', str(source))
    assert mixed.returncode == 2
    assert 'not allowed with argument' in mixed.stderr


@pytest.mark.parametrize('fault', ['contract', 'reader', 'reader_list', 'reader_null_failure',
                                  'reader_null_section', 'hold', 'hold_list', 'missing_hold',
                                  'file_link_or_reparse'])
def test_corrupt_source_metadata_fails_instead_of_claiming_no_hit(source, fault, tmp_path):
    contract_path = source / 'catalog/examples' / (ASSET + '.json')
    if fault == 'contract':
        contract_path.write_text('{}')
    elif fault in ('reader', 'reader_list', 'reader_null_failure', 'reader_null_section'):
        reader_path = source / 'tools/docs/zh/reader.json'
        bundle = json.loads(reader_path.read_bytes())
        if fault == 'reader':
            bundle['records'][0]['source_sha256'] = '0' * 64
        elif fault == 'reader_list':
            bundle = []
        elif fault == 'reader_null_failure':
            bundle['records'][0]['failure_semantics']['invalid_input'] = None
        else:
            bundle['records'][0]['verification'] = None
        reader_path.write_bytes(encode(bundle))
    elif fault in ('hold', 'hold_list'):
        (source / 'catalog/review/HOLD.json').write_text('{}' if fault == 'hold' else '[]')
    elif fault == 'missing_hold':
        (source / 'catalog/review/HOLD.json').unlink()
    else:
        external = tmp_path / 'external.json'
        external.write_bytes(contract_path.read_bytes())
        contract_path.unlink()
        file_link_or_reparse(contract_path, external)
    result = cli(source, '--q', 'nonexistent-science-term')
    assert result.returncode == 2
    response = json.loads(result.stdout)
    assert response['outcome'] == 'metadata_error'
    assert 'result' not in response


def test_public_source_rejects_file_link_or_reparse_before_reading_it(source, tmp_path, monkeypatch):
    contract_path = source / 'catalog/examples' / (ASSET + '.json')
    external = tmp_path / 'external.json'
    external.write_bytes(contract_path.read_bytes())
    contract_path.unlink()
    file_link_or_reparse(contract_path, external)
    read_bytes = Path.read_bytes

    def refuse_link_read(path):
        if path == contract_path:
            raise AssertionError('public source opened a file link/reparse point')
        return read_bytes(path)

    monkeypatch.setattr(Path, 'read_bytes', refuse_link_read)
    with pytest.raises(ValueError, match='link|reparse'):
        SourceDocumentation(source)


def test_public_source_rejects_contracts_redirected_by_a_directory_link(source, tmp_path):
    contracts = source / 'catalog/examples'
    external = tmp_path / 'external-contracts'
    contracts.rename(external)
    directory_link(contracts, external)
    result = cli(source, '--q', 'nonexistent-science-term')
    assert result.returncode == 2
    response = json.loads(result.stdout)
    assert response['outcome'] == 'metadata_error'
    assert 'result' not in response


def test_hold_aba_cannot_expose_a_held_contract_under_bound_hold_bytes(source, monkeypatch):
    public = json.loads((source / 'catalog/examples' / (ASSET + '.json')).read_bytes())
    public['asset_id'] = HELD
    held_path = source / 'catalog/examples' / (HELD + '.json')
    held_path.write_bytes(encode(public))
    reader_path = source / 'tools/docs/zh/reader.json'
    bundle = json.loads(reader_path.read_bytes())
    held_reader = json.loads(json.dumps(bundle['records'][0]))
    held_reader.update(asset_id=HELD, source_sha256=sha(held_path.read_bytes()))
    bundle['records'].append(held_reader)
    reader_path.write_bytes(encode(bundle))
    commit(source)
    baseline = SourceDocumentation(source)
    original = capability_catalog.held_asset_ids

    def swap_during_hold_parse(path, **kwargs):
        before = path.read_bytes()
        temporary = json.loads(before)
        temporary['assets'] = {}
        path.write_bytes(encode(temporary))
        try:
            return original(path, **kwargs)
        finally:
            path.write_bytes(before)

    monkeypatch.setattr(capability_catalog, 'held_asset_ids', swap_during_hold_parse)
    queried = SourceDocumentation(source)
    assert queried.describe() == baseline.describe()
    assert queried.asset(HELD)['outcome'] == 'unknown_asset'


def test_reader_aba_cannot_return_unbound_text_under_the_same_source_identity(source, monkeypatch):
    baseline = SourceDocumentation(source)
    reader_path = source / 'tools/docs/zh/reader.json'
    original = capability_catalog.load_translations

    def swap_during_reader_parse(*args, **kwargs):
        before = reader_path.read_bytes()
        temporary = json.loads(before)
        temporary['records'][0]['summary'] = '未绑定的临时说明 B'
        reader_path.write_bytes(encode(temporary))
        try:
            return original(*args, **kwargs)
        finally:
            reader_path.write_bytes(before)

    monkeypatch.setattr(capability_catalog, 'load_translations', swap_during_reader_parse)
    queried = SourceDocumentation(source)
    assert queried.describe() == baseline.describe()
    assert queried.asset(ASSET, reader=True) == baseline.asset(ASSET, reader=True)


def test_reader_binding_checks_captured_contract_bytes_during_contract_aba(source, monkeypatch):
    contract_path = source / 'catalog/examples' / (ASSET + '.json')
    temporary = json.loads(contract_path.read_bytes())
    temporary['summary'] += ' Temporary contract B.'
    temporary_bytes = encode(temporary)
    reader_path = source / 'tools/docs/zh/reader.json'
    bundle = json.loads(reader_path.read_bytes())
    bundle['records'][0]['source_sha256'] = sha(temporary_bytes)
    reader_path.write_bytes(encode(bundle))
    original = capability_catalog.load_translations

    def swap_during_binding(*args, **kwargs):
        before = contract_path.read_bytes()
        contract_path.write_bytes(temporary_bytes)
        try:
            return original(*args, **kwargs)
        finally:
            contract_path.write_bytes(before)

    monkeypatch.setattr(capability_catalog, 'load_translations', swap_during_binding)
    with pytest.raises(ValueError, match='stale Chinese reader'):
        SourceDocumentation(source)
