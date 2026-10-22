"""Public retrieval behavior on the portable, lightweight capability index."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from capability_query import (  # noqa: E402
    CAPABILITY_INDEX_SCHEMA, CAPABILITY_REQUEST_SCHEMA, CAPABILITY_QUERY_SCHEMA,
    REQUEST_SCHEMA, RESPONSE_SCHEMA, query_capabilities, validate_capability_index,
)


def _record(asset_id, **changes):
    return {
        'asset_id': asset_id, 'capability': 'flux integration',
        'capability_summary': 'integrate a supplied field',
        'operation': 'field to flux', 'operation_direction': 'forward',
        'model': 'slab', 'geometry': 'Cartesian', 'coordinates': 'x, y',
        'boundary': 'periodic', 'device_scope': 'generic', 'aliases': [],
        'contract_path': 'catalog/' + asset_id + '.json', **changes,
    }


def _index(*records):
    return {'schema': CAPABILITY_INDEX_SCHEMA, 'source_revision': 'a' * 40,
            'asset_count': len(records), 'assets': list(records),
            'search_text': {item['asset_id']: json.dumps(item, ensure_ascii=False).casefold()
                            for item in records}}


def _query(index, **request):
    return query_capabilities(index, {'schema': CAPABILITY_REQUEST_SCHEMA, **request})


def test_portable_query_prefers_identity_over_incidental_text_and_bounds_pages():
    incidental = _record('a.incidental', summary='density response')
    identity = _record('z.identity', capability='density response', aliases=['密度响应'])
    index = _index(incidental, identity)
    first = _query(index, q='density density', limit=1)
    assert first['schema'] == CAPABILITY_QUERY_SCHEMA
    assert first['tokens'] == ['density']
    assert first['items'][0]['asset_id'] == identity['asset_id']
    evidence = first['items'][0]['relevance']
    assert evidence['matched_terms'] == ['density']
    assert evidence['matched_fields']['capability'] == ['density']
    assert first['next_offset'] == 1 and first['total'] == first['match_total'] == 2
    second = _query(index, q='density density', offset=first['next_offset'], limit=1)
    assert [item['asset_id'] for item in second['items']] == ['a.incidental']
    assert second['next_offset'] is None
    assert evidence['score'] > second['items'][0]['relevance']['score']
    # Input ordering never changes relevance or deterministic tie-breaking.
    assert _query(_index(identity, incidental), q='density density', limit=1) == first
    tied = _index(_record('b'), _record('a'))
    assert [item['asset_id'] for item in _query(tied)['items']] == ['a', 'b']


def test_filters_and_aliases_are_literal_and_boundary_near_misses_are_explicit():
    index = _index(_record('a', aliases=['周期磁通']),
                   _record('b', model='cylindrical', boundary='open'))
    match = _query(index, model='SLAB', boundary='periodic', alias='周期磁通', limit=1)
    assert match['status'] == 'match'
    assert match['items'][0]['matched_filters'] == ['model', 'boundary', 'alias']
    assert _query(index, q='周期磁通')['items'][0]['asset_id'] == 'a'
    near = _query(index, model='slab', boundary='open', limit=1)
    assert near['status'] == 'near_miss' and near['near_miss_total'] == 2
    assert near['items'][0]['matched_filters'] == ['model']
    assert near['items'][0]['missed_filters'] == ['boundary']
    assert near['retrieval']['outcome'] == 'near_miss'
    assert near['retrieval']['scientific_applicability'] == 'not_assessed'


def test_browse_order_is_asset_id_before_pagination_with_same_filters():
    index = _index(_record('z', capability='density response'),
                   _record('a', summary='density response'),
                   _record('b', capability='density response'))
    request = {'schema': CAPABILITY_REQUEST_SCHEMA, 'q': 'density', 'limit': 1}
    page = query_capabilities(index, request, ranked=False)
    assert page['items'][0]['asset_id'] == 'a' and page['next_offset'] == 1
    assert page['retrieval']['method'] == 'asset-id'
    page = query_capabilities(index, {**request, 'offset': 1}, ranked=False)
    assert page['items'][0]['asset_id'] == 'b' and page['next_offset'] == 2
    assert query_capabilities(index, request)['items'][0]['asset_id'] == 'b'


def test_taxonomy_filter_uses_exact_item_and_never_infers_missing_classification():
    index = _index(_record('declared', taxonomy=['plasma.transport']),
                   _record('missing', capability='plasma.transport'))
    result = _query(index, taxonomy='PLASMA.TRANSPORT')
    assert result['status'] == 'match'
    assert [item['asset_id'] for item in result['items']] == ['declared']
    assert result['items'][0]['matched_filters'] == ['taxonomy']
    assert _query(index, taxonomy='plasma')['status'] == 'gap'


def test_lexical_no_hit_is_not_a_scientific_absence_claim():
    result = _query(_index(_record('a')), q='flux nonexistent')
    assert result['status'] == 'gap' and result['items'] == []
    assert result['retrieval']['outcome'] == 'no_hit'
    assert result['retrieval']['backend'] == 'lexical-and'
    assert result['retrieval']['completeness'] == 'unknown'
    assert 'does not establish a scientific capability gap' in result['gap']['caveat']
    assert 'no semantic recall guarantee' in result['retrieval']['caveat']


@pytest.mark.parametrize('changes', [
    {'unknown': ''}, {'schema': 'other'}, {'limit': 0}, {'limit': 101},
    {'limit': True}, {'limit': 1.5}, {'offset': -1}, {'offset': '0'},
    {'offset': False}, {'q': None}, {'q': 'x' * 513}, {'model': 1},
    {'boundary': 'x' * 1025}, {'device_scope': 'device'},
])
def test_invalid_request_fails_closed(changes):
    with pytest.raises(ValueError):
        _query(_index(_record('a')), **changes)


def test_explicit_json_request_schema_and_lightweight_index_are_required():
    index = _index(_record('a'))
    assert validate_capability_index(index, expected_source_revision='a' * 40,
                                     expected_ids={'a'}) is index
    assert 'ports' not in index['assets'][0] and 'evidence' not in index['assets'][0]
    for request in ({}, [], None, {'schema': CAPABILITY_REQUEST_SCHEMA, 'top_k': 5}):
        with pytest.raises(ValueError):
            query_capabilities(index, request)
    assert REQUEST_SCHEMA['additionalProperties'] is False
    assert REQUEST_SCHEMA['properties']['limit']['maximum'] == 100
    assert RESPONSE_SCHEMA['properties']['items']['maxItems'] == 100


@pytest.mark.parametrize('fault', [
    'schema', 'revision', 'count', 'bool-count', 'duplicates', 'recall-ids',
    'recall-type', 'asset-field', 'aliases', 'scope',
])
def test_invalid_index_fails_closed(fault):
    index = deepcopy(_index(_record('a')))
    if fault == 'schema':
        index['schema'] = 'unknown'
    elif fault == 'revision':
        index['source_revision'] = 'a' * 39
    elif fault == 'count':
        index['asset_count'] += 1
    elif fault == 'bool-count':
        index['asset_count'] = True
    elif fault == 'duplicates':
        index['assets'] *= 2
        index['asset_count'] = 2
    elif fault == 'recall-ids':
        index['search_text'] = {'b': 'text'}
    elif fault == 'recall-type':
        index['search_text']['a'] = []
    elif fault == 'asset-field':
        index['assets'][0].pop('model')
    elif fault == 'aliases':
        index['assets'][0]['aliases'] = 'alias'
    elif fault == 'scope':
        index['assets'][0]['device_scope'] = 'inferred-generic'
    with pytest.raises(ValueError):
        _query(index)


def test_copied_core_runs_with_standard_library_outside_repository(tmp_path):
    copied = tmp_path / 'capability_query.py'
    shutil.copyfile(ROOT / 'scripts/capability_query.py', copied)
    payload = {'index': _index(_record('portable', aliases=['周期磁通'])),
               'request': {'schema': CAPABILITY_REQUEST_SCHEMA, 'q': '周期磁通', 'limit': 1}}
    code = '''import json, sys
sys.path.insert(0, sys.argv[1])
from capability_query import query_capabilities
payload = json.load(sys.stdin)
print(json.dumps(query_capabilities(payload['index'], payload['request'])))
assert not any(name.startswith(('sphinx', 'numpy', 'scirel_docs')) for name in sys.modules)
'''
    completed = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(tmp_path)],
                               cwd=tmp_path, input=json.dumps(payload), text=True,
                               capture_output=True, check=True, timeout=10)
    assert json.loads(completed.stdout) == query_capabilities(payload['index'], payload['request'])
