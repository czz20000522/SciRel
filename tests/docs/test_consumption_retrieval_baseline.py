"""Bounded lexical retrieval evidence from public contracts and bound zh prose.

This is a selected-query regression baseline, not an exhaustive recall metric or
a scientific composition test. Synthetic scale probes are kept separate.
Run directly with --output to regenerate the JSON evidence after a clean commit.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
import tracemalloc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from capability_query import query_capabilities  # noqa: E402
from scirel_docs import build_capability_index  # noqa: E402

FIELD = 'scirel.field.poloidal-field-from-flux'
CURRENT = 'scirel.equilibrium.anisotropic-toroidal-current'
CX_RATE = 'scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient'
LOSS = 'scirel.kinetic.neutral-total-collision-frequency'
THERMAL = 'scirel.physics.thermal-energy'
PROBES = [
    ('field_from_flux', {'q': 'poloidal field flux'}, FIELD, 'match'),
    ('pressure_current', {'q': 'gyrotropic toroidal current'}, CURRENT, 'match'),
    ('cx_rate', {'q': 'atomic-hydrogen charge-exchange Maxwellian'}, CX_RATE, 'match'),
    ('neutral_loss', {'q': 'neutral total-loss collision frequency'}, LOSS, 'match'),
    ('english_pressure_energy', {'q': 'stored thermal energy pressure'}, THERMAL, 'match'),
    ('chinese_density', {'q': '准中性 电子密度'},
     'scirel.closures.quasineutral-reference-density', 'match'),
    ('declared_alias', {'alias': 'cold Stix dielectric tensor'},
     'scirel.dielectric.cold-plasma-tensor', 'match'),
    ('chinese_reader_only', {'q': '总标量压强 储存热能'}, THERMAL, 'match'),
    ('wrong_boundary', {'capability': 'Axisymmetric poloidal field from flux',
                        'boundary': 'periodic wrap-around at both R boundaries'}, FIELD, 'near_miss'),
    ('no_lexical_candidate', {'q': 'gravitational wave chirp waveform'}, None, 'gap'),
]
GROUPS = [
    {'id': 'flux_to_pressure_current',
     'request': 'Recover the axisymmetric poloidal field from an R-Z flux grid, then evaluate the gyrotropic-pressure toroidal current projection.',
     'stages': ['field_from_flux', 'pressure_current'],
     'domains': ['field', 'equilibrium'],
     'composition_requirements': [
         'psi must be Wb/rad on the same increasing cylindrical R-Z axes.',
         'Connect B_R/B_Z in T to br/bz in T, preserving [Z,R] alignment; pressures must be Pa.',
         'The toroidal projection alone is not a complete equilibrium.'],
     'numerical_composition': 'NOT_RUN'},
    {'id': 'charge_exchange_to_total_loss',
     'request': 'Find an atomic-hydrogen charge-exchange rate and assemble a neutral total-loss collision-frequency field on the declared velocity/spatial grid.',
     'stages': ['cx_rate', 'neutral_loss'],
     'domains': ['collisions', 'kinetic'],
     'composition_requirements': [
         'The rate fit takes paired temperature and impact-energy samples in eV and returns m^3/s.',
         'An explicitly justified target number density and n*rate conversion are needed to obtain s^-1; no such glue is executed here.',
         'Align the frequency to (nvr,nvx,nx), supply the remaining loss terms and declare the charge-exchange enable flag.',
         'The logarithmic Maxwellian rate fit is not asserted equivalent to a velocity-mesh cross-section integral.'],
     'numerical_composition': 'NOT_RUN'},
]


def _encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _public_index():
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    documents, contract_hashes = [], {}
    for path in sorted((ROOT / 'catalog/examples').glob('*.json')):
        raw = path.read_bytes()
        document = json.loads(raw)
        documents.append(document)
        contract_hashes[document['asset_id']] = _sha(raw)
    translations = {}
    for path in sorted((ROOT / 'tools/docs/zh').glob('*.json')):
        for record in json.loads(path.read_bytes())['records']:
            asset = record['asset_id']
            if asset in contract_hashes:
                assert asset not in translations, 'duplicate public reader: ' + asset
                assert record['source_sha256'] == contract_hashes[asset], 'stale public reader: ' + asset
                translations[asset] = record
    assert set(translations) == set(contract_hashes)
    index = build_capability_index(documents, source_revision=source, translations=translations)
    # Match the delivered discovery-card shape: full ports/evidence remain in get.
    omitted = {'ports', 'evidence', 'public_api', 'contract_path', 'record_path',
               'docs_path', 'summary'}
    index['assets'] = [{key: value for key, value in record.items() if key not in omitted}
                       for record in index['assets']]
    return index, {doc['asset_id']: doc for doc in documents}, contract_hashes, translations


def _public_probes(index, contracts):
    results = []
    for name, filters, expected, status in PROBES:
        request = {'schema': 'scirel.capability-query', 'limit': 5, **filters}
        actual = query_capabilities(index, request)
        ids = [item['asset_id'] for item in actual['items']]
        assert len(ids) <= 5 and len(ids) == len(set(ids)), name
        assert actual['status'] == status, (name, actual)
        assert expected is None or expected in ids, (name, expected, ids)
        assert actual['retrieval']['completeness'] == 'unknown'
        assert actual['retrieval']['scientific_applicability'] == 'not_assessed'
        if name == 'wrong_boundary':
            selected = next(item for item in actual['items'] if item['asset_id'] == expected)
            assert 'boundary' in selected['missed_filters']
        results.append({'probe_id': name, 'request': request,
                        'expected_asset_ids': [expected] if expected else [],
                        'expected_core_status': status, 'actual_top5_asset_ids': ids,
                        'actual_core_status': actual['status'],
                        'retrieval_outcome': actual['retrieval']['outcome'],
                        'matched_missed_filters': [{key: item[key] for key in
                                                   ('asset_id', 'matched_filters', 'missed_filters')}
                                                  for item in actual['items']],
                        'result_json_bytes': len(_encode(actual)), 'passed': True})
    # These are public-contract compatibility observations, not executed graphs.
    def units(asset, side, port):
        return next(item['units'] for item in contracts[asset][side] if item['name'] == port)
    assert units(FIELD, 'outputs', 'B_R') == units(CURRENT, 'inputs', 'br') == 'T'
    assert units(FIELD, 'outputs', 'B_Z') == units(CURRENT, 'inputs', 'bz') == 'T'
    assert units(CX_RATE, 'outputs', 'rate_m3_s') == 'm^3/s'
    assert units(LOSS, 'inputs', 'charge_exchange_frequency_s_inv') == 's^-1'
    return results


def _synthetic_scale(size):
    def identifier(number):
        return 'synthetic.retrieval.' + str(number).zfill(5)
    records = [{
        'asset_id': identifier(number), 'capability': 'Synthetic density response',
        'capability_summary': 'No scientific capability; synthetic metadata only.',
        'operation': 'synthetic relation', 'operation_direction': 'synthetic output',
        'model': 'synthetic model', 'geometry': 'synthetic geometry',
        'coordinates': 'synthetic coordinates', 'boundary': 'synthetic boundary',
        'device_scope': 'unclassified', 'aliases': [], 'taxonomy': ['synthetic'],
    } for number in reversed(range(size))]
    index = {'schema': 'scirel.capability-index', 'source_revision': '0' * 40,
             'asset_count': size, 'assets': records,
             'search_text': {record['asset_id']: 'synthetic density response' for record in records}}
    request = {'schema': 'scirel.capability-query', 'q': 'density response', 'limit': 5}
    tracemalloc.start()
    started = perf_counter()
    try:
        result = query_capabilities(index, request)
        elapsed = perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert result['match_total'] == size and len(result['items']) == 5
    assert [item['asset_id'] for item in result['items']] == [identifier(i) for i in range(5)]
    pages = []
    for offset in (0, 5, size - 5):
        page = query_capabilities(index, {**request, 'offset': offset}, ranked=False)
        ids = [item['asset_id'] for item in page['items']]
        assert ids == [identifier(i) for i in range(offset, offset + 5)]
        assert page['total'] == size and len(ids) <= 5
        assert page['next_offset'] == (offset + 5 if offset + 5 < size else None)
        pages.append({'offset': offset, 'asset_ids': ids, 'next_offset': page['next_offset']})
    observed = [asset for page in pages for asset in page['asset_ids']]
    assert len(observed) == len(set(observed)) == 15
    return {'synthetic': True, 'asset_count': size, 'query': request,
            'query_seconds': elapsed, 'query_tracemalloc_peak_bytes': peak,
            'memory_scope': 'Incremental traced Python allocations during one query; excludes prebuilt index and process RSS.',
            'index_json_bytes': len(_encode(index)), 'result_json_bytes': len(_encode(result)),
            'returned': len(result['items']), 'match_total': result['match_total'],
            'pagination_coverage': 'First two pages and final page only; whole index not paged.',
            'pages': pages, 'passed': True}


def run_baseline():
    index, contracts, hashes, translations = _public_index()
    public = _public_probes(index, contracts)
    synthetic = [_synthetic_scale(size) for size in (1000, 5000, 10000)]
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    return {
        'schema': 'scirel.retrieval-baseline', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_revision': index['source_revision'], 'source_dirty': dirty,
        'public_asset_count': index['asset_count'],
        'public_contract_content_sha256': _sha(_encode(hashes)),
        'public_reader_content_sha256': _sha(_encode(translations)),
        'environment': {'python': sys.version, 'platform': platform.platform(),
                        'machine': platform.machine(), 'timing_clock': 'time.perf_counter',
                        'memory_instrument': 'tracemalloc'},
        'reproduce': '.venv/bin/python tests/docs/test_consumption_retrieval_baseline.py --output dist/famou-mcp-dev-20261022/retrieval-baseline.json',
        'denominators': {'public_probes': 10, 'positive_top5_probes_passed': 8,
                         'positive_top5_probes_total': 8, 'wrong_boundary_probes_passed': 1,
                         'wrong_boundary_probes_total': 1, 'no_hit_probes_passed': 1,
                         'no_hit_probes_total': 1, 'cross_domain_groups': 2,
                         'cross_domain_stages': 4, 'synthetic_scale_probes': 3},
        'cross_domain_groups': GROUPS, 'public_probes': public, 'synthetic_scale': synthetic,
        'limits': [
            'Only ten selected public lexical queries are checked; this is not semantic or exhaustive recall evaluation.',
            'Complex requests were manually decomposed into two stages; no automatic planner is evaluated.',
            'Top-5 retrieval and public port-unit observations do not establish numerical composition correctness; composition is NOT_RUN.',
            'No lexical hit means no retrieved candidate, not established scientific absence.',
            'The 1000/5000/10000 records are synthetic copies with synthetic IDs and no additional scientific coverage.',
            'Performance numbers describe this run with tracing overhead; no latency or process-memory performance gate is asserted.',
            'Synthetic browse checks cover three pages per size, not full-index traversal.',
        ],
    }


def test_public_retrieval_and_synthetic_scale():
    report = run_baseline()
    assert len(report['public_probes']) == 10
    assert len(report['synthetic_scale']) == 3
    if output := os.environ.get('SCIREL_RETRIEVAL_REPORT'):
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_encode(report))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run_baseline()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(_encode(report))
    print(json.dumps({'public_probes': 10, 'synthetic_scale_probes': 3,
                      'source_revision': report['source_revision'],
                      'source_dirty': report['source_dirty'], 'report': str(args.output)}))
