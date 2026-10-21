"""Read-only capability recall over the generated, snapshot-bound index.

The capability index is a build artifact projected from the asset contracts.
Reviewed ``discovery`` text wins when present; otherwise the view derives from
``title``/``identity``/``aliases``/``taxonomy``/ports/``verification``.  These
tests prove the projection is exact, ``device_scope`` filters only reviewed
discovery values (defaulting to ``unclassified``), unknown discovery keys are
ignored, and structured queries keep ``match`` / ``near_miss`` / ``gap``
explicit without introducing versioned schema fields.
"""
import json
from pathlib import Path
import subprocess
import sys
import threading
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from scirel_docs import (  # noqa: E402
    CAPABILITY_INDEX_SCHEMA,
    CAPABILITY_QUERY_SCHEMA,
    DEVICE_SCOPES,
    Documentation,
    build_capability_index,
    capability_record,
    encode,
    server,
    sha,
)
from validate_asset_documents import load_document_set  # noqa: E402


def _all_pages(docs, **filters):
    """Collect every page of one capability query (limit is capped at 100)."""
    items, offset = [], 0
    while True:
        page = docs.capabilities(**filters, offset=offset, limit=100)
        items.extend(page['items'])
        if page['next_offset'] is None:
            return page, items
        offset = page['next_offset']


def _write_minimal_snapshot(root, documents, source='0' * 40):
    """Write a Documentation-compatible snapshot without running Sphinx.

    This keeps discovery projection/filter tests independent of the contract
    schema landing first: the snapshot only carries the generated capability
    index, the exact contract records and the document index used for IDs.
    """
    index = build_capability_index(documents, source_revision=source)
    files = {'capabilities.json': encode(index)}
    lookup = []
    for document in documents:
        asset = document['asset_id']
        files['records/' + asset + '.json'] = encode(document)
        lookup.append({key: document[key] for key in
                       ('asset_id', 'title', 'summary', 'taxonomy', 'aliases', 'version')}
                      | {'public_api': document['public_api'], 'summary_zh': '',
                         'evidence_ceiling': document['verification']['evidence_ceiling'],
                         'known_limitations': document['verification']['known_limitations'],
                         'search_text': ''})
    files['index.json'] = encode(lookup)
    manifest = {
        'schema': 'scirel.documentation-snapshot',
        'source_commit': source, 'source_revision': source, 'source_dirty': False,
        'project_version': '0.1.0.dev11', 'documentation_version': '0.1.0.dev11',
        'asset_count': len(documents), 'notice': 'synthetic capability test snapshot',
        'reader_language': 'zh-CN', 'human_renderer': 'sphinx-pydata',
        'validation': {'schema_and_dependency_closure': True,
                       'scientific_runtime_revalidated': False},
        'files': {path: {'sha256': sha(data), 'bytes': len(data)}
                  for path, data in sorted(files.items())},
    }
    manifest['snapshot_sha256'] = sha(encode(manifest))
    root.mkdir(parents=True, exist_ok=True)
    for path, data in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (root / 'manifest.json').write_bytes(encode(manifest))
    return root


def _contract_copy(docs, asset_id):
    return json.loads(json.dumps(docs.asset(asset_id)['document']))


def test_snapshot_publishes_a_capability_index_bound_to_its_contracts(snapshot):
    docs = Documentation(snapshot)
    manifest = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8'))
    assert 'capabilities.json' in manifest['files']
    index = docs.capability_index()
    assert index['schema'] == CAPABILITY_INDEX_SCHEMA
    # Only the schema identity is recorded; no version labels are introduced.
    for absent in ('schema_version', 'query_version', 'index_version'):
        assert absent not in index
    assert index['source_revision'] == manifest['source_revision']
    assert index['asset_count'] == manifest['asset_count'] == len(docs.ids)
    assert {record['asset_id'] for record in index['assets']} == docs.ids
    assert set(index['search_text']) == docs.ids
    assert not any('search_text' in record for record in index['assets'])
    # The served index is exactly the projection of the served exact records.
    for record in index['assets']:
        document = docs.asset(record['asset_id'])['document']
        discovery = document.get('discovery', {})
        assert record == capability_record(document)
        if 'operation' in discovery and len(discovery['operation']) > 1:
            assert record['operation_direction'] == ' — '.join(discovery['operation'][1:])
        else:
            assert record['operation_direction'] == document['identity']['direction'].strip()
        assert record['coordinates'] == document['identity']['coordinates'].strip()
        assert record['aliases'] == document['aliases']
        assert record['taxonomy'] == document['taxonomy']
        if 'device_scope' in discovery:
            assert record['device_scope'] == discovery['device_scope']
            assert record['device_scope_source'] == 'discovery'
        else:
            assert record['device_scope'] == 'unclassified'
            assert record['device_scope_source'] == 'default-unclassified'
        assert record['contract_path'] == 'catalog/examples/' + record['asset_id'] + '.json'
        assert record['record_path'] == 'records/' + record['asset_id'] + '.json'
        assert record['docs_path'] == '/reference/generated/' + record['asset_id'] + '.html'
        assert [port['name'] for port in record['ports']['inputs']] == [
            port['name'] for port in document['inputs']]
        assert [port['units'] for port in record['ports']['outputs']] == [
            port['units'] for port in document['outputs']]
        assert record['evidence']['tests'] == document['verification']['tests']
        assert record['evidence']['status'] == (
            'bounded' if document['verification']['tests'] else 'unvalidated')


def test_capability_index_is_a_deterministic_contract_projection():
    documents = load_document_set(ROOT / 'catalog/examples')
    first = build_capability_index(documents, source_revision='0' * 40)
    second = build_capability_index(list(reversed(documents)), source_revision='0' * 40)
    assert first == second
    assert [record['asset_id'] for record in first['assets']] == sorted(
        record['asset_id'] for record in first['assets'])
    assert {record['device_scope'] for record in first['assets']} <= set(DEVICE_SCOPES)


def test_discovery_fields_are_consumed_and_unknown_keys_ignored():
    document = json.loads(json.dumps(next(iter(
        load_document_set(ROOT / 'catalog/examples')))))
    # The canonical contracts now carry reviewed discovery blocks; exercise the
    # derived fallback on a copy that removes it, then inject reviewed values.
    document.pop('discovery', None)
    fallback = capability_record(document)
    assert fallback['capability'] == document['title']['en'].strip()
    assert fallback['operation'] == document['identity']['relation'].strip()
    assert fallback['model'] == document['identity']['model'].strip()
    assert fallback['geometry'] == document['identity']['geometry'].strip()
    assert fallback['boundary'] == document['identity']['boundary'].strip()
    assert fallback['aliases'] == document['aliases']
    assert fallback['device_scope'] == 'unclassified'
    assert fallback['device_scope_source'] == 'default-unclassified'

    document['discovery'] = {
        'capability': ['Reviewed capability', 'Reviewed one-line summary'],
        'operation': ['Reviewed operation', 'inputs -> outputs'],
        'model': 'reviewed model level',
        'geometry': 'reviewed geometry',
        'boundary': 'reviewed boundary',
        'device_scope': 'device-parameterized',
        # Unknown keys are ignored, never projected.  In particular aliases are
        # not a discovery field: the top-level contract aliases stay the truth.
        'aliases': ['InjectedAlias'],
        'unknown_extra': {'nested': True},
    }
    reviewed = capability_record(document)
    assert reviewed['capability'] == 'Reviewed capability'
    assert reviewed['capability_summary'] == 'Reviewed one-line summary'
    assert reviewed['operation'] == 'Reviewed operation'
    assert reviewed['operation_direction'] == 'inputs -> outputs'
    assert reviewed['model'] == 'reviewed model level'
    assert reviewed['geometry'] == 'reviewed geometry'
    assert reviewed['boundary'] == 'reviewed boundary'
    assert reviewed['device_scope'] == 'device-parameterized'
    assert reviewed['device_scope_source'] == 'discovery'
    assert reviewed['aliases'] == document['aliases']
    assert 'unknown_extra' not in reviewed
    assert all('unknown_extra' not in json.dumps(value)
               for value in reviewed.values() if isinstance(value, str))

    for broken in ({'device_scope': 'device'},
                   {'device_scope': 'generic-ish'},
                   {'capability': 'not-a-list'},
                   {'capability': []},
                   {'operation': []},
                   {'model': ''}):
        document['discovery'] = broken
        with pytest.raises(ValueError):
            capability_record(document)
    document['discovery'] = ['not', 'an', 'object']
    with pytest.raises(ValueError, match='discovery must be an object'):
        capability_record(document)


def test_structured_queries_filter_on_contract_fields(snapshot):
    docs = Documentation(snapshot)
    records = docs.capability_index()['assets']
    record = next(item for item in records if item['aliases'])

    base = docs.capabilities(limit=2)
    assert base['schema'] == CAPABILITY_QUERY_SCHEMA
    for absent in ('query_version', 'index_schema', 'index_version',
                   'schema_version'):
        assert absent not in base
    assert base['status'] == 'match'
    assert base['total'] == len(docs.ids) == docs.manifest['asset_count']
    assert len(base['items']) == 2 and base['next_offset'] == 2
    assert base['snapshot_sha256'] == docs.manifest['snapshot_sha256']
    assert base['notice'] and '开发文档' in base['notice']
    assert base['query'] == {'capability': '', 'operation': '', 'model': '',
                             'geometry': '', 'device_scope': '', 'alias': '',
                             'q': '', 'offset': 0, 'limit': 2}
    assert not any('search_text' in item for item in base['items'])

    for field in ('capability', 'operation', 'model', 'geometry'):
        result = docs.capabilities(**{field: record[field]}, limit=100)
        ids = {item['asset_id'] for item in result['items']}
        assert record['asset_id'] in ids, field
        assert result['status'] == 'match'
        for item in result['items']:
            if item['asset_id'] == record['asset_id']:
                assert item['matched_filters'] == [field]
                assert item['missed_filters'] == []
                assert item['status'] == 'match'
                break

    alias = docs.capabilities(alias=record['aliases'][0], limit=100)
    assert record['asset_id'] in {item['asset_id'] for item in alias['items']}

    # Full-text recall covers the stable asset ID, the Chinese contract title
    # and the bound Chinese reader summary.
    for query in (record['asset_id'], record['title_zh'], 'basis'):
        result = docs.capabilities(q=query, limit=100)
        assert result['status'] == 'match'
        assert result['items']

    # Every supplied filter is an AND condition against the same asset.
    combined = docs.capabilities(capability=record['capability'],
                                 alias=record['aliases'][0], limit=100)
    hit = next(item for item in combined['items']
               if item['asset_id'] == record['asset_id'])
    assert hit['matched_filters'] == ['capability', 'alias']


def test_device_scope_filtering_defaults_to_unclassified(snapshot):
    docs = Documentation(snapshot)
    records = docs.capability_index()['assets']
    for record in records:
        assert record['device_scope'] in DEVICE_SCOPES
        document = docs.asset(record['asset_id'])['document']
        if 'device_scope' not in document.get('discovery', {}):
            assert record['device_scope'] == 'unclassified'
            assert record['device_scope_source'] == 'default-unclassified'
    for scope in DEVICE_SCOPES:
        expected = {record['asset_id'] for record in records
                    if record['device_scope'] == scope}
        page, items = _all_pages(docs, device_scope=scope)
        if expected:
            assert page['status'] == 'match'
            assert {item['asset_id'] for item in items} == expected
            assert all(item['device_scope'] == scope for item in items)
        else:
            assert page['status'] == 'gap' and items == []
    with pytest.raises(ValueError, match='device_scope must be one of'):
        docs.capabilities(device_scope='device')
    with pytest.raises(ValueError, match='device_scope must be one of'):
        docs.handle('/api/capabilities?device_scope=device')


def test_synthetic_discovery_scope_filter_and_projection(snapshot):
    docs = Documentation(snapshot)
    # Pick contracts that already carry top-level aliases: aliases always come
    # from that field, never from a discovery block.
    aliased = [record['asset_id'] for record in docs.capability_index()['assets']
               if record['aliases']]
    generic = _contract_copy(docs, aliased[0])
    generic['discovery'] = {'device_scope': 'generic'}
    parameterized = _contract_copy(docs, aliased[1])
    parameterized['discovery'] = {
        'capability': ['Reviewed synthetic capability', 'one-line summary'],
        'operation': ['Reviewed synthetic operation', 'in -> out'],
        'model': 'reviewed synthetic model',
        'geometry': 'reviewed synthetic geometry',
        'boundary': 'reviewed synthetic boundary',
        'device_scope': 'device-parameterized',
    }
    fallback = _contract_copy(docs, aliased[2])
    fallback.pop('discovery', None)
    root = _write_minimal_snapshot(
        Path(snapshot).parent / 'synthetic-discovery',
        [generic, parameterized, fallback])
    synthetic = Documentation(root)

    assert synthetic.capabilities(
        device_scope='generic')['items'][0]['asset_id'] == generic['asset_id']
    result = synthetic.capabilities(device_scope='device-parameterized')
    assert [item['asset_id'] for item in result['items']] == [parameterized['asset_id']]
    item = result['items'][0]
    assert item['capability'] == 'Reviewed synthetic capability'
    assert item['operation'] == 'Reviewed synthetic operation'
    assert item['model'] == 'reviewed synthetic model'
    assert item['geometry'] == 'reviewed synthetic geometry'
    assert item['boundary'] == 'reviewed synthetic boundary'
    assert item['aliases'] == parameterized['aliases']
    assert item['matched_filters'] == ['device_scope']
    assert synthetic.capabilities(
        device_scope='unclassified')['items'][0]['asset_id'] == fallback['asset_id']
    assert synthetic.capabilities(device_scope='device-bound')['status'] == 'gap'

    combined = synthetic.capabilities(
        device_scope='device-parameterized',
        capability='Reviewed synthetic capability')
    assert [item['asset_id'] for item in combined['items']] == [parameterized['asset_id']]
    assert combined['items'][0]['matched_filters'] == ['capability', 'device_scope']
    assert synthetic.capabilities(
        alias=parameterized['aliases'][0])['items'][0]['asset_id'] == parameterized['asset_id']


def test_near_miss_and_gap_are_explicit(snapshot):
    docs = Documentation(snapshot)
    records = docs.capability_index()['assets']
    # A broad structured term yields many partial matches; use the most common
    # model token so the assertion does not depend on one asset's prose.
    tokens = {}
    for record in records:
        for token in record['model'].casefold().split():
            if len(token) >= 6:
                tokens[token] = tokens.get(token, 0) + 1
    token = max(tokens, key=lambda value: (tokens[value], value))
    near = docs.capabilities(capability='no-such-capability-xyz',
                             model=token, limit=5)
    assert near['status'] == 'near_miss'
    assert near['match_total'] == 0 and near['near_miss_total'] > 5
    assert near['items'] and len(near['items']) == 5
    assert all(item['status'] == 'near_miss' for item in near['items'])
    assert all('capability' in item['missed_filters'] for item in near['items'])
    assert all('model' in item['matched_filters'] for item in near['items'])
    counts = [len(item['matched_filters']) for item in near['items']]
    assert counts == sorted(counts, reverse=True)

    near_page, near_items = _all_pages(docs, capability='no-such-capability-xyz',
                                       model=token)
    assert near_page['status'] == 'near_miss'
    assert len(near_items) == near_page['near_miss_total'] > 5

    gap = docs.capabilities(capability='no-such-capability-xyz')
    assert gap['status'] == 'gap' and gap['items'] == [] and gap['total'] == 0
    assert gap['match_total'] == gap['near_miss_total'] == 0
    assert gap['gap']['reason'] == 'no asset matched every supplied filter'
    assert 'does not establish a scientific capability gap' in gap['gap']['caveat']
    assert gap['gap']['filters'] == {'capability': 'no-such-capability-xyz'}

    # A single full-text term miss is not classified as a structured near miss.
    assert docs.capabilities(q='unfindable-xyz-123')['status'] == 'gap'

    listing = docs.capabilities(limit=100)
    assert listing['status'] == 'match' and listing['near_miss_total'] == 0
    assert all(item['matched_filters'] == [] and item['missed_filters'] == []
               for item in listing['items'])


@pytest.mark.parametrize('url', ['/api/capabilities?limit=0',
                                 '/api/capabilities?limit=101',
                                 '/api/capabilities?offset=-1',
                                 '/api/capabilities?offset=x',
                                 '/api/capabilities?device_scope=device',
                                 '/api/capabilities?capability=a&capability=b',
                                 '/api/capabilities?unknown=x'])
def test_invalid_capability_queries_fail_closed(snapshot, url):
    with pytest.raises(ValueError):
        Documentation(snapshot).handle(url)


def test_capability_http_cli_and_missing_index(snapshot):
    docs = Documentation(snapshot)
    record = next(item for item in docs.capability_index()['assets'] if item['aliases'])
    expected = docs.capabilities(limit=2)

    cli = subprocess.check_output([sys.executable, str(ROOT / 'scripts/scirel_docs.py'),
                                   'query', '--snapshot', str(snapshot),
                                   '--capabilities', '--limit', '2'])
    assert json.loads(cli) == expected
    cli = subprocess.check_output([sys.executable, str(ROOT / 'scripts/scirel_docs.py'),
                                   'query', '--snapshot', str(snapshot),
                                   '--capability', record['capability'],
                                   '--limit', '2'])
    assert json.loads(cli) == docs.capabilities(capability=record['capability'], limit=2)
    cli = subprocess.check_output([sys.executable, str(ROOT / 'scripts/scirel_docs.py'),
                                   'query', '--snapshot', str(snapshot),
                                   '--device-scope', record['device_scope'],
                                   '--limit', '2'])
    assert json.loads(cli) == docs.capabilities(
        device_scope=record['device_scope'], limit=2)

    http = server(docs, 0)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{http.server_port}'
    try:
        with urlopen(base + '/api/capabilities?limit=2') as response:
            assert json.load(response) == expected
        with urlopen(base + '/api/capabilities?alias=' + quote(record['aliases'][0])) as response:
            assert json.load(response) == docs.capabilities(alias=record['aliases'][0])
        with urlopen(base + '/api/capabilities?device_scope=' +
                     record['device_scope']) as response:
            assert json.load(response) == docs.capabilities(
                device_scope=record['device_scope'])
        endpoints = json.load(urlopen(base + '/api'))['endpoints']
        assert '/api/capabilities' in endpoints['capabilities']
        assert 'device_scope' in endpoints['capabilities']
        with pytest.raises(HTTPError) as error:
            urlopen(base + '/api/capabilities?limit=abc')
        assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + '/api/capabilities?device_scope=device')
        assert error.value.code == 400
    finally:
        http.shutdown()
        http.server_close()
        thread.join()

    # An older snapshot without the generated artifact stays readable for every
    # existing endpoint and fails closed only on the new capability endpoint.
    docs.manifest['files'].pop('capabilities.json')
    with pytest.raises(KeyError, match='no capability index'):
        docs.capabilities()


def test_capability_index_tampering_fails_closed(snapshot):
    docs = Documentation(snapshot)
    (snapshot / 'capabilities.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='bytes changed'):
        docs.capabilities()


def test_capability_index_schema_drift_fails_closed(snapshot, monkeypatch):
    docs = Documentation(snapshot)
    original = docs.read

    def drifted(relative):
        data = original(relative)
        if relative == 'capabilities.json':
            index = json.loads(data)
            index['schema'] = 'scirel.capability-index-v2'
            return json.dumps(index, ensure_ascii=False).encode()
        return data

    monkeypatch.setattr(docs, 'read', drifted)
    with pytest.raises(ValueError, match='schema'):
        docs.capabilities()
