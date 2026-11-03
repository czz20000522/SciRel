"""Portable, standard-library-only capability retrieval over a bound JSON index.

The request/response JSON schemas below are the public query contract. Structured
text filters use literal, case-insensitive phrase containment in their named
fields; device_scope uses enum equality and taxonomy matches one complete
declared item (a missing taxonomy never acquires an inferred classification).
All supplied filters and whitespace-
separated q terms are AND conditions. Ranking is deterministic lexical evidence,
not semantic similarity, scientific applicability or composition correctness.
Index bytes and their delivery-manifest binding are verified by the caller.
"""
from __future__ import annotations

import re

CAPABILITY_INDEX_SCHEMA = 'scirel.capability-index'
CAPABILITY_QUERY_SCHEMA = 'scirel.capability-query-response'
CAPABILITY_REQUEST_SCHEMA = 'scirel.capability-query'
DEVICE_SCOPES = ('generic', 'device-parameterized', 'device-bound', 'unclassified')
FILTER_ORDER = ('capability', 'operation', 'model', 'geometry', 'boundary', 'taxonomy',
                'device_scope', 'alias', 'q')
_TEXT_FILTERS = tuple(name for name in FILTER_ORDER if name not in ('device_scope', 'q'))
_RECORD_TEXT = ('asset_id', 'capability', 'capability_summary', 'operation',
                'operation_direction', 'model', 'geometry', 'coordinates',
                'boundary', 'device_scope')
RETRIEVAL_CAVEAT = (
    'Literal lexical retrieval only: no semantic recall guarantee. Ranking does '
    'not establish scientific applicability or composition correctness; inspect '
    'the selected contracts for ports, units, model, geometry, boundary and evidence.'
)

REQUEST_SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': CAPABILITY_REQUEST_SCHEMA,
    'type': 'object', 'required': ['schema'], 'additionalProperties': False,
    'properties': {
        'schema': {'const': CAPABILITY_REQUEST_SCHEMA},
        **{name: {'type': 'string', 'maxLength': 1024, 'default': ''}
           for name in _TEXT_FILTERS},
        'device_scope': {'enum': ['', *DEVICE_SCOPES], 'default': ''},
        'q': {'type': 'string', 'maxLength': 512, 'default': ''},
        'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
        'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 20},
    },
}
RESPONSE_SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': CAPABILITY_QUERY_SCHEMA,
    'type': 'object',
    'required': ['schema', 'source_revision', 'query', 'tokens', 'retrieval',
                 'status', 'match_total', 'near_miss_total', 'total', 'offset',
                 'next_offset', 'items'],
    'properties': {
        'schema': {'const': CAPABILITY_QUERY_SCHEMA},
        'source_revision': {'type': 'string', 'pattern': '^[0-9a-f]{40}$'},
        'query': {'type': 'object', 'additionalProperties': False,
                  'required': [*FILTER_ORDER, 'offset', 'limit'],
                  'properties': {key: value for key, value in
                                 REQUEST_SCHEMA['properties'].items() if key != 'schema'}},
        'tokens': {'type': 'array', 'items': {'type': 'string'}, 'uniqueItems': True},
        'retrieval': {'type': 'object', 'required': [
                          'method', 'backend', 'completeness', 'scientific_applicability',
                          'outcome', 'caveat'],
                      'additionalProperties': False, 'properties': {
                          'method': {'type': 'string', 'minLength': 1},
                          'backend': {'type': 'string', 'minLength': 1},
                          'completeness': {'const': 'unknown'},
                          'scientific_applicability': {'const': 'not_assessed'},
                          'outcome': {'enum': ['match', 'near_miss', 'no_hit']},
                          'caveat': {'type': 'string', 'minLength': 1}}},
        'status': {'enum': ['match', 'near_miss', 'gap']},
        **{name: {'type': 'integer', 'minimum': 0}
           for name in ('match_total', 'near_miss_total', 'total', 'offset')},
        'next_offset': {'type': ['integer', 'null'], 'minimum': 0},
        'items': {'type': 'array', 'maxItems': 100, 'items': {
            'type': 'object', 'required': ['asset_id', 'status', 'matched_filters',
                                         'missed_filters', 'relevance'],
            'properties': {
                'asset_id': {'type': 'string', 'minLength': 1},
                'status': {'enum': ['match', 'near_miss']},
                **{key: {'type': 'array', 'uniqueItems': True,
                         'items': {'enum': list(FILTER_ORDER)}}
                   for key in ('matched_filters', 'missed_filters')},
                'relevance': {'type': 'object', 'additionalProperties': False,
                              'required': ['score', 'matched_terms', 'matched_fields'],
                              'properties': {
                                  'score': {'type': 'integer', 'minimum': 0},
                                  'matched_terms': {'type': 'array', 'uniqueItems': True,
                                                    'items': {'type': 'string'}},
                                  'matched_fields': {'type': 'object',
                                                     'additionalProperties': {
                                                         'type': 'array',
                                                         'items': {'type': 'string'}}}}},
            }}},
        'gap': {'type': 'object', 'required': ['reason', 'filters', 'q', 'caveat']},
    },
}


def validate_capability_index(index, *, expected_source_revision=None, expected_ids=None):
    """Validate the full or lightweight index shape, returning the same object.

    Both projections require only query fields in each asset. Detailed ports and
    evidence may remain in the selected full contract rather than this index.
    """
    if not isinstance(index, dict) or index.get('schema') != CAPABILITY_INDEX_SCHEMA:
        raise ValueError('invalid capability index schema')
    revision = index.get('source_revision')
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('invalid capability index source revision')
    if expected_source_revision is not None and revision != expected_source_revision:
        raise ValueError('capability index source revision differs from snapshot')
    assets = index.get('assets')
    if (not isinstance(assets, list) or type(index.get('asset_count')) is not int
            or index['asset_count'] != len(assets)):
        raise ValueError('invalid capability index count')
    ids = []
    for record in assets:
        if (not isinstance(record, dict)
                or any(not isinstance(record.get(key), str) for key in _RECORD_TEXT)
                or not record['asset_id']):
            raise ValueError('invalid capability index asset query fields')
        if record['device_scope'] not in DEVICE_SCOPES:
            raise ValueError('invalid capability index device_scope')
        aliases = record.get('aliases')
        if not isinstance(aliases, list) or any(not isinstance(value, str) for value in aliases):
            raise ValueError('invalid capability index aliases')
        taxonomy = record.get('taxonomy', [])
        if not isinstance(taxonomy, list) or any(not isinstance(value, str) for value in taxonomy):
            raise ValueError('invalid capability index taxonomy')
        for key in ('summary', 'title_zh', 'symbol'):
            if key in record and not isinstance(record[key], str):
                raise ValueError('invalid capability index ' + key)
        ids.append(record['asset_id'])
    if len(set(ids)) != len(ids) or (expected_ids is not None and set(ids) != set(expected_ids)):
        raise ValueError('capability index differs from the document set')
    recall = index.get('search_text')
    if (not isinstance(recall, dict) or set(recall) != set(ids)
            or any(not isinstance(value, str) for value in recall.values())):
        raise ValueError('capability index recall text differs from its assets')
    return index


def _request(request):
    if not isinstance(request, dict) or request.get('schema') != CAPABILITY_REQUEST_SCHEMA:
        raise ValueError('invalid capability query request schema')
    if set(request) - set(REQUEST_SCHEMA['properties']):
        raise ValueError('unknown capability query parameter')
    filters = {}
    for name in FILTER_ORDER:
        value = request.get(name, '')
        if not isinstance(value, str):
            raise ValueError(name + ' must be a string')
        maximum = 512 if name == 'q' else 1024
        if len(value) > maximum:
            raise ValueError(name + ' <= ' + str(maximum) + ' characters required')
        filters[name] = value if name == 'q' else value.strip()
    if filters['device_scope'] and filters['device_scope'] not in DEVICE_SCOPES:
        raise ValueError('device_scope must be one of: ' + ', '.join(DEVICE_SCOPES))
    offset, limit = request.get('offset', 0), request.get('limit', 20)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('offset >= 0 and limit 1..100 must be integers')
    return {**filters, 'offset': offset, 'limit': limit}


def _field_text(record):
    return {
        'asset_id': record['asset_id'],
        'capability': record['capability'] + '\n' + record['capability_summary'],
        'operation': record['operation'] + '\n' + record['operation_direction'],
        'model': record['model'],
        'geometry': record['geometry'] + '\n' + record['coordinates'],
        'boundary': record['boundary'],
        'alias': '\n'.join(record['aliases']),
        'summary': record.get('summary', ''),
        'title_zh': record.get('title_zh', ''),
        'symbol': record.get('symbol', ''),
    }


def _relevance(text, haystack, terms, phrase):
    # Stable field weights favor capability identity over incidental reader prose.
    weights = {'asset_id': 12, 'symbol': 12, 'alias': 10, 'capability': 8,
               'title_zh': 8, 'operation': 5, 'model': 4, 'geometry': 4,
               'boundary': 3, 'summary': 2, 'recall': 1}
    fields = {**text, 'recall': haystack}
    evidence, score = {}, 0
    for name, value in fields.items():
        found = [term for term in terms if term in value]
        if found:
            evidence[name] = found
            score += weights[name] * len(found)
            if phrase and phrase == value.strip():
                score += weights[name] * 2
    return {'score': score, 'matched_terms': [term for term in terms if term in haystack],
            'matched_fields': evidence}


def query_capabilities(index, request, *, ranked=True):
    """Return one bounded JSON response; invalid requests/indexes fail closed."""
    if type(ranked) is not bool:
        raise ValueError('ranked must be a boolean')
    query = _request(request)
    validate_capability_index(index)
    terms = list(dict.fromkeys(query['q'].casefold().split()))
    phrase = ' '.join(terms)
    supplied = {name: query[name].casefold() for name in FILTER_ORDER
                if name != 'q' and query[name]}
    strict, partial = [], []
    for record in index['assets']:
        text = {name: value.casefold() for name, value in _field_text(record).items()}
        haystack = index['search_text'][record['asset_id']].casefold()
        matched, missed = [], []
        for name in FILTER_ORDER:
            if name == 'q':
                if terms:
                    (matched if all(term in haystack for term in terms) else missed).append(name)
            elif name in supplied:
                if name == 'device_scope':
                    hit = supplied[name] == record['device_scope']
                elif name == 'taxonomy':
                    hit = supplied[name] in [value.casefold() for value in record.get('taxonomy', [])]
                else:
                    hit = supplied[name] in text[name]
                (matched if hit else missed).append(name)
        relevance = _relevance(text, haystack, terms, phrase)
        entry = (record, matched, missed, relevance)
        if not missed:
            strict.append(entry)
        elif any(name != 'q' for name in matched):
            partial.append(entry)
    if strict:
        status, candidates = 'match', strict
    elif partial:
        status, candidates = 'near_miss', partial
    else:
        status, candidates = 'gap', []
    candidates.sort(key=(lambda item: (-len(item[1]), -item[3]['score'], item[0]['asset_id']))
                    if ranked else (lambda item: item[0]['asset_id']))
    offset, limit, total = query['offset'], query['limit'], len(candidates)
    items = [{**record, 'status': status, 'matched_filters': matched,
              'missed_filters': missed, 'relevance': relevance}
             for record, matched, missed, relevance in candidates[offset:offset + limit]]
    result = {
        'schema': CAPABILITY_QUERY_SCHEMA, 'source_revision': index['source_revision'],
        'query': query, 'tokens': terms,
        'retrieval': {'method': 'weighted-lexical' if ranked else 'asset-id',
                      'backend': 'lexical-and',
                      'completeness': 'unknown', 'scientific_applicability': 'not_assessed',
                      'outcome': 'no_hit' if status == 'gap' else status,
                      'caveat': RETRIEVAL_CAVEAT},
        'status': status, 'match_total': len(strict),
        'near_miss_total': len(partial) if status == 'near_miss' else 0,
        'total': total, 'offset': offset,
        'next_offset': offset + limit if offset + limit < total else None, 'items': items,
    }
    if status == 'gap':
        result['gap'] = {
            'reason': 'no asset matched every supplied filter',
            'filters': {name: value for name, value in query.items()
                        if name in FILTER_ORDER and name != 'q' and value},
            'q': query['q'],
            'caveat': ('A zero lexical hit does not establish a scientific capability '
                       'gap; applicability is decided by ports, units, model, '
                       'geometry, boundary and evidence.'),
        }
    return result
