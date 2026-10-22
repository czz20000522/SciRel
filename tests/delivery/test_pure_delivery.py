"""Portable product-byte and read-only consumer boundaries.

All catalog records, outputs, wheel bytes and 0/1 identity values in this file
are synthetic fixtures. These tests make no scientific or platform claim and
never build documentation, build/install a wheel, or run an MCP transport.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_pure_delivery as delivery  # noqa: E402
from build_scirel_sphinx import guide_selection_complete  # noqa: E402
import consumer_tools  # noqa: E402
import exposure  # noqa: E402
import validate_asset_documents  # noqa: E402
from pure_query import Consumer, encode, sha  # noqa: E402

SOURCE = '0' * 40
SNAPSHOT_ID = '1' * 64
ASSET = 'scirel.synthetic.alpha'
WHEEL_BYTES = b'Synthetic fixture only; this is not an installable wheel.\n'
TUTORIAL = '# Synthetic tutorial\n\n合成示例，未作科学验证。\n\n```python\nprint(0)\n```\n\nOutput: 0\n'


def _write_snapshot(root: Path, *, count=2, summary_chars=0):
    root.mkdir()
    names = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'eta', 'theta', 'zeta'][:count]
    records, documents, files = [], {}, {
        'wheel/synthetic.whl': WHEEL_BYTES,
        'catalog/tutorial-index.json': encode({
            'schema': 'scirel.tutorial-index',
            'chapters': [{'chapter_id': 'synthetic', 'paths': {
                lang: f'docs/{lang}/tutorials/synthetic.md' for lang in ('en', 'zh')}}],
        }),
    }
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
        for lang in ('en', 'zh'):
            files[f'docs/{lang}/api/{asset}.md'] = (
                f'# {name}\n\nSynthetic fixture ({lang}); not a science claim.\n\n'
                '```python\nprint(0)\n```\n\n```text\n0\n```\n').encode()
    files['catalog/capability-index.json'] = encode({
        'schema': 'scirel.capability-index', 'source_revision': SOURCE,
        'asset_count': len(records), 'assets': records,
        'search_text': {r['asset_id']: ' '.join((r['asset_id'], 'synthetic scalar',
                                              r['symbol'], '合成示例')) for r in records},
    })
    for lang in ('en', 'zh'):
        files[f'docs/{lang}/tutorials/synthetic.md'] = TUTORIAL.encode()
    for relative, data in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    metadata = {
        'schema': 'scirel.pure-consumption', 'snapshot_id': SNAPSHOT_ID,
        'source_revision': SOURCE, 'asset_count': len(records),
        'runtime': {'wheel': 'synthetic.whl', 'wheel_sha256': sha(WHEEL_BYTES),
                    'requires_python': '>=3.14,<3.15',
                    'requires_dist': ['numpy', 'scipy', 'mpmath'],
                    'dependencies_bundled': False},
        'retrieval': {'backend': 'lexical-and', 'completeness': 'unknown',
                      'scientific_applicability': 'not_assessed',
                      'incomplete_status': 'retrieval_incomplete'},
    }
    manifest = delivery.seal(root, metadata)
    return root, manifest, documents


@pytest.fixture
def snapshot(tmp_path):
    return _write_snapshot(tmp_path / 'consumer')


def _pins(manifest):
    return {'expected_snapshot_sha256': manifest['manifest_sha256'],
            'expected_wheel_sha256': manifest['runtime']['wheel_sha256']}


def _reseal(root):
    manifest = json.loads((root / 'manifest.json').read_bytes())
    return delivery.seal(root, {key: value for key, value in manifest.items()
                                if key not in {'files', 'manifest_sha256'}})


def test_article_markdown_preserves_code_output_prose_and_product_links():
    code = 'values = [0.0, 1.0]\n\n\nprint("``` marker")\nprint(values)\n'
    output = '[0.0, 1.0]\n\n\nresidual = 0.0\n'
    article = f'''<header>outside navigation</header><article class="bd-article">
<h1>Exact quantities<a class="headerlink" href="#exact">¶</a></h1>
<p>Read the <strong>whole</strong> result &amp; keep <em>its scope</em>.</p>
<h2>Numerical example</h2><div class="highlight"><pre>{html.escape(code)}</pre></div>
<p class="rubric">Actual output</p><pre>{html.escape(output)}</pre>
<p><a href="/api/asset?id={ASSET}">contract</a>,
<a href="../../user-guide/synthetic.html#limits">tutorial</a>,
<a href="../../tutorials/supplement.html">supplement</a>,
<a href="../../user-guide/index.html">guide index</a>,
<a href="../../tutorials/index.html">tutorial index</a>,
<a href="scirel.synthetic.beta.html#units">neighbor</a>,
<a href="https://example.org/reference?q=1#part">reference</a>.</p>
<img src="../../_images/example.png" alt="synthetic curve">
<ul><li>First condition</li><li>Second condition</li></ul>
<script>hidden executable content</script></article>'''
    result = delivery.markdown(article,
        source_path=f'web/reference/generated/{ASSET}.html',
        target_path=f'docs/en/api/{ASSET}.md', language='en')

    assert '# Exact quantities' in result
    assert '## Numerical example' in result and '## Actual output' in result
    assert 'Read the **whole** result & keep *its scope*.' in result
    assert code.rstrip('\n') in result
    assert output.rstrip('\n') in result
    assert f'[contract](../../../catalog/contracts/{ASSET}.json)' in result
    assert '[tutorial](../tutorials/synthetic.md#limits)' in result
    assert '[supplement](../tutorials/supplement.md)' in result
    assert 'guide index' in result and '[guide index](' not in result
    assert 'tutorial index' in result and '[tutorial index](' not in result
    assert '[neighbor](scirel.synthetic.beta.md#units)' in result
    assert '[reference](https://example.org/reference?q=1#part)' in result
    assert '![synthetic curve](../assets/example.png)' in result
    assert 'First condition' in result and 'Second condition' in result
    assert 'outside navigation' not in result and 'hidden executable content' not in result


def test_markdown_requires_the_selected_article():
    with pytest.raises(ValueError):
        delivery.markdown('<html><p>Navigation only</p></html>',
                          source_path='web/index.html', target_path='docs/en/index.md', language='en')


@pytest.mark.parametrize('display', [False, True])
def test_mathml_preserves_bound_roots_fractions_subscripts_and_powers(display):
    formula = r'\sqrt{x_0^2 + \frac{a_1}{b_2}}'
    attributes = ' display="block"' if display else ''
    article = ('<article class="bd-article"><p>Before </p>'
               '<math aria-label="' + html.escape(formula, quote=True) + '"' + attributes + '>'
               '<msqrt><mrow><msup><msub><mi>x</mi><mn>0</mn></msub><mn>2</mn></msup>'
               '<mo>+</mo><mfrac><msub><mi>a</mi><mn>1</mn></msub>'
               '<msub><mi>b</mi><mn>2</mn></msub></mfrac></mrow></msqrt>'
               '</math><p>After</p></article>')
    result = delivery.markdown(article, source_path='web/user-guide/synthetic.html',
                               target_path='docs/en/tutorials/synthetic.md', language='en')
    expected = '$$\n' + formula + '\n$$' if display else '$' + formula + '$'
    assert expected in result
    assert 'Before' in result and 'After' in result


def test_mathml_without_exact_formula_fails_instead_of_flattening_science():
    article = ('<article class="bd-article"><math><mfrac><mi>a</mi><mi>b</mi>'
               '</mfrac></math></article>')
    with pytest.raises(ValueError):
        delivery.markdown(article, source_path='web/user-guide/synthetic.html',
                          target_path='docs/en/tutorials/synthetic.md', language='en')


def test_seal_binds_nested_manifests_as_product_members(tmp_path):
    root = tmp_path / 'sealed'
    (root / 'nested').mkdir(parents=True)
    (root / 'nested/manifest.json').write_bytes(b'{"synthetic":true}\n')
    manifest = delivery.seal(root, {'schema': 'synthetic.fixture'})
    assert manifest['files']['nested/manifest.json'] == {
        'sha256': sha(b'{"synthetic":true}\n'), 'bytes': len(b'{"synthetic":true}\n')}
    unsigned = {key: value for key, value in manifest.items() if key != 'manifest_sha256'}
    assert manifest['manifest_sha256'] == sha(encode(unsigned))


def test_local_link_closure_reads_actual_targets_and_rejects_a_missing_member(tmp_path):
    root = tmp_path / 'linked'
    root.mkdir()
    (root / 'contract.json').write_bytes(b'{"synthetic":true}\n')
    (root / 'image.png').write_bytes(b'Synthetic non-rendered image fixture\n')
    page = root / 'guide.md'
    page.write_text('[contract](contract.json#section)\n\n![fixture](image.png)\n\n'
                    '[external](https://example.org/not-fetched)\n\n'
                    '```text\n[literal data](does-not-exist)\n```\n')
    result = delivery.local_link_closure(root)
    assert result['status'] == 'PASS'
    assert result['network_links_checked'] is False
    assert result['scientific_text_review'] == 'NOT_RUN'
    page.write_text(page.read_text() + '\n[missing target](absent.md)\n')
    with pytest.raises(ValueError):
        delivery.local_link_closure(root)


def test_export_archives_are_byte_stable_and_refuse_to_overwrite(snapshot, tmp_path):
    root, _, _ = snapshot
    first = delivery.archive(root, tmp_path / 'first.zip')
    second = delivery.archive(root, tmp_path / 'second.zip')
    assert first['sha256'] == second['sha256']
    assert first['bytes'] == second['bytes']
    with ZipFile(first['path']) as archive:
        assert set(archive.namelist()) == {
            path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_file()}
        assert archive.read('manifest.json') == (root / 'manifest.json').read_bytes()
    original = Path(first['path']).read_bytes()
    with pytest.raises(FileExistsError):
        delivery.archive(root, Path(first['path']))
    assert Path(first['path']).read_bytes() == original


@pytest.mark.parametrize('existing', ['agent', 'html'])
def test_builder_preserves_existing_delivery_directories(tmp_path, existing):
    agent, site = tmp_path / 'agent', tmp_path / 'html'
    retained = agent if existing == 'agent' else site
    retained.mkdir()
    (retained / 'existing.txt').write_bytes(b'Keep exact bytes\n')
    with pytest.raises(FileExistsError):
        delivery.build(tmp_path / 'not-a-wheel', tmp_path / 'no-en-docs',
                       tmp_path / 'no-zh-docs', agent, site)
    assert (retained / 'existing.txt').read_bytes() == b'Keep exact bytes\n'


@pytest.mark.parametrize('failure', [
    'source_dirty', 'docs_source', 'docs_dirty', 'asset_sets',
    'swapped_languages', 'same_language', 'equal_subset', 'exposes_withheld',
])
def test_builder_requires_one_clean_bilingual_candidate_before_creating_outputs(tmp_path, monkeypatch, failure):
    source_root = tmp_path / 'source'
    catalog = source_root / 'catalog/examples'
    catalog.mkdir(parents=True)
    source_ids = {ASSET}
    if failure == 'equal_subset':
        source_ids.add('scirel.synthetic.beta')
    withheld = {'scirel.synthetic.withheld'}
    source_ids |= withheld
    for asset in source_ids:
        (catalog / (asset + '.json')).write_bytes(encode({'asset_id': asset}))

    def git(command, **kwargs):
        if command == ['git', 'rev-parse', 'HEAD']:
            return SOURCE
        assert command == ['git', 'status', '--porcelain']
        return b' M changed.py\n' if failure == 'source_dirty' else b''

    def docs(path):
        language = path.name
        manifest = {'source_revision': '1' * 40 if failure == 'docs_source' else SOURCE,
                    'source_dirty': failure == 'docs_dirty',
                    'reader_language': {'en': 'en-US', 'zh': 'zh-CN'}[language]}
        if failure == 'swapped_languages':
            manifest['reader_language'] = {'en': 'zh-CN', 'zh': 'en-US'}[language]
        elif failure == 'same_language':
            manifest['reader_language'] = 'en-US'
        ids = {ASSET} if failure != 'asset_sets' or language == 'en' else set()
        if failure == 'exposes_withheld':
            ids |= withheld
        return SimpleNamespace(manifest=manifest, ids=ids)

    monkeypatch.setattr(delivery, 'ROOT', source_root)
    monkeypatch.setattr(delivery.subprocess, 'check_output', git)
    monkeypatch.setattr(delivery, 'Documentation', docs)
    monkeypatch.setattr(exposure, 'held_asset_ids', lambda: withheld)
    monkeypatch.setattr(delivery, 'inspect_wheel',
                        lambda path: pytest.fail('invalid source/docs must fail before wheel inspection'))
    output, site = tmp_path / 'agent', tmp_path / 'html'
    with pytest.raises(ValueError):
        delivery.build(tmp_path / 'not-a-wheel', tmp_path / 'en', tmp_path / 'zh', output, site)
    assert not output.exists() and not site.exists()


@pytest.mark.parametrize('failure', [None, 'signature', 'sidecar', 'extra_api_page',
                                     'contract_bytes', 'source_inputs', 'tutorial_import'])
def test_source_closure_rejects_drift_in_runtime_reader_or_snapshot_members(tmp_path, monkeypatch, failure):
    source_root = tmp_path / 'source'
    catalog = source_root / 'catalog/examples'
    catalog.mkdir(parents=True)
    module_name = 'scirel_synthetic_consumer_runtime'

    def evaluate(x):
        return x

    module = ModuleType(module_name)
    module.__all__ = ['evaluate']
    module.evaluate = evaluate
    if failure == 'tutorial_import':
        module.__all__.append('unexposed')
        module.unexposed = evaluate
    monkeypatch.setitem(sys.modules, module_name, module)
    monkeypatch.syspath_prepend(str(source_root / 'src'))
    port = {'name': 'x', 'description': 'Synthetic input', 'units': '1',
            'shape': 'scalar', 'dtype': 'float', 'required': True, 'constraints': 'Synthetic only'}
    document = {
        'asset_id': ASSET, 'title': {'en': 'Synthetic scalar', 'zh': '合成示例'},
        'summary': 'Synthetic fixture; no scientific validation.', 'aliases': ['synthetic'],
        'taxonomy': ['synthetic'],
        'public_api': {'python': {'module': module_name, 'symbol': 'evaluate',
                                  'signature': 'evaluate(x, y)' if failure == 'signature' else 'evaluate(x)'}},
        'identity': {'relation': 'Synthetic relation', 'direction': 'input to output',
                     'definition': 'A fixture only', 'model': 'Synthetic algebra',
                     'geometry': 'scalar', 'coordinates': 'none', 'boundary': 'unknown',
                     'assumptions': []},
        'inputs': [port], 'outputs': [{**port, 'name': 'value'}],
        'applicability': {'preconditions': [], 'supported': [], 'excluded': []},
        'verification': {'scope': [], 'tests': [], 'evidence_ceiling': 'No science claim',
                         'known_limitations': []},
    }
    contract = encode(document)
    (catalog / (ASSET + '.json')).write_bytes(contract)
    translation = {
        'asset_id': ASSET, 'source_sha256': sha(contract),
        'summary': '合成示例', 'definition': '合成定义', 'model': '合成模型', 'boundary': '未知',
        'inputs': [{**port, 'description': '合成输入', 'dtype': '合成类型', 'constraints': '仅测试'}],
        'outputs': [{**port, 'name': 'value', 'description': '合成输出', 'dtype': '合成类型', 'constraints': '仅测试'}],
        'applicability': {'preconditions': [], 'supported': [], 'excluded': []},
        'verification': {'scope': [], 'known_limitations': [], 'evidence_ceiling': '未作科学验证'},
        'assumptions': [],
        'failure_semantics': {key: '合成边界' for key in
                              ('invalid_input', 'runtime_failure', 'nonconvergence', 'partial_results')},
        'example': {'description': '合成示例', 'expected': '不作科学断言'},
    }
    reader_dir = source_root / 'tools/docs/zh'
    reader_dir.mkdir(parents=True)
    (reader_dir / 'synthetic.json').write_bytes(encode({
        'schema': 'scirel.reader-translation', 'language': 'zh-CN', 'records': [translation]}))
    # These are explicit synthetic source inputs for hashing, not copied product
    # code or a documentation build. The actual index/reader/runtime gates below
    # still execute against their real implementations.
    source_inputs = [
        'scripts/' + name for name in (
            'build_pure_delivery.py', 'capability_query.py', 'pure_query.py', 'consumer_tools.py',
            'serve_consumer_mcp.py', 'scirel_docs.py', 'build_scirel_sphinx.py',
            'build_capability_matrix.py', 'validate_asset_documents.py', 'public_api_binding.py',
            'check_wheel_exposure.py', 'exposure.py')]
    source_inputs += ['tools/docs/' + name for name in (
        'PURE_CONSUMPTION.md', 'mcp-requirements.txt', 'handbook.json', 'handbook.en.json')]
    source_inputs.append('skills/development/usage/scirel-solving/SKILL.md')
    for relative in source_inputs:
        path = source_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'Synthetic source binding input; not executable product code.\n')
    if failure == 'tutorial_import':
        tutorial = source_root / 'tools/docs/manual/synthetic.rst'
        tutorial.parent.mkdir(parents=True)
        tutorial.write_text('Synthetic only\n==============\n\n.. code-block:: python\n\n'
                            '   from ' + module_name + ' import unexposed\n')
    current_inputs = {'catalog/examples/' + ASSET + '.json': sha(contract),
                      'tools/docs/zh/synthetic.json': sha((reader_dir / 'synthetic.json').read_bytes())}
    monkeypatch.setattr(delivery, 'ROOT', source_root)
    monkeypatch.setattr(delivery, 'documentation_input_digests', lambda: dict(current_inputs))
    monkeypatch.setattr(exposure, 'held_asset_ids', lambda: frozenset())
    monkeypatch.setattr(validate_asset_documents, 'load_document_set', lambda path: [document])
    snapshots = {}
    for language in ('en', 'zh'):
        index = delivery.build_capability_index([document], source_revision=SOURCE,
                    translations={ASSET: translation} if language == 'zh' else None, language=language)
        members = {
            'records/' + ASSET + '.json': contract,
            'web/reference/generated/' + ASSET + '.html': b'<article class="bd-article">Synthetic only</article>',
        }
        if language == 'zh':
            reader = {**translation, 'summary': '过时的合成文本'} if failure == 'sidecar' else translation
            members['readers/' + ASSET + '.json'] = encode(reader)
        if failure == 'extra_api_page':
            members['web/reference/generated/scirel.synthetic.stale.html'] = b'Stale fixture'
        if failure == 'contract_bytes':
            members['records/' + ASSET + '.json'] = encode({**document, 'summary': 'Stale contract bytes'})
        bound_inputs = dict(current_inputs)
        if failure == 'source_inputs' and language == 'zh':
            bound_inputs['tools/docs/zh/synthetic.json'] = 'f' * 64
        manifest = {'files': members, 'source_inputs': bound_inputs,
                    'source_inputs_sha256': sha(encode(bound_inputs))}
        snapshots[language] = SimpleNamespace(ids={ASSET}, manifest=manifest,
                                              read=members.__getitem__, capability_index=lambda value=index: value)
    if failure is None:
        result = delivery.source_closure(snapshots, SOURCE)
        assert result['asset_count'] == 1
        assert result['source_signature_check'] == 'PASS'
        assert result['natural_language_scientific_review'] == 'NOT_RUN'
        assert result['generator_and_reading_inputs']
    else:
        with pytest.raises(ValueError):
            delivery.source_closure(snapshots, SOURCE)


def test_tutorial_imports_are_derived_from_actual_python_blocks_and_ast_names():
    text = '''Prose mentioning from scirel.prose import ignored.

.. code-block:: python

   from scirel.synthetic import evaluate as local_name
   import scirel.synthetic as scientific
   import numpy as np
   note = "from scirel.string import ignored"
   # from scirel.comment import ignored

End of block.
'''
    assert set(delivery.tutorial_imports(text)) == {
        ('scirel.synthetic', 'evaluate'), ('scirel.synthetic', None)}


def test_shared_guide_selection_rejects_missing_document_in_each_language():
    available = {'user-guide/index', 'reference/generated/' + ASSET}
    for prose in ('See', '参阅'):
        valid = prose + ' :doc:`../reference/generated/' + ASSET + '`.'
        missing = valid + '\n' + prose + ' :doc:`/reference/generated/scirel.synthetic.absent`.'
        assert guide_selection_complete(valid, 'synthetic', available) is True
        assert guide_selection_complete(missing, 'synthetic', available) is False


def test_exact_snapshot_verifies_without_claiming_scientific_execution(snapshot):
    root, manifest, _ = snapshot
    result = Consumer(root).verify()
    assert result['outcome'] == 'ok'
    assert result['snapshot_sha256'] == manifest['manifest_sha256']
    assert result['wheel_sha256'] == sha(WHEEL_BYTES)
    assert result['scientific_runtime_revalidated'] is False


@pytest.mark.parametrize('change', ['extra', 'missing', 'tamper', 'symlink'])
def test_verify_rejects_changed_or_unbound_product_members(snapshot, change, tmp_path):
    root, _, _ = snapshot
    member = root / f'docs/en/api/{ASSET}.md'
    if change == 'extra':
        (root / 'extra.txt').write_text('Unbound')
    elif change == 'missing':
        member.unlink()
    elif change == 'tamper':
        member.write_text('Changed result')
    else:
        outside = tmp_path / 'outside.md'
        outside.write_bytes(member.read_bytes())
        member.unlink()
        member.symlink_to(outside)
    with pytest.raises((OSError, ValueError)):
        Consumer(root).verify()


@pytest.mark.parametrize('relative', ['../outside', '/outside', 'docs/../outside',
                                     'docs\\outside', 'C:/outside', './manifest.json'])
def test_member_read_rejects_unsafe_paths(snapshot, relative):
    root, _, _ = snapshot
    with pytest.raises(ValueError):
        Consumer(root).read(relative)


def test_manifest_tamper_and_symlink_cannot_establish_a_snapshot(snapshot, tmp_path):
    root, _, _ = snapshot
    path = root / 'manifest.json'
    data = json.loads(path.read_bytes())
    data['asset_count'] += 1
    path.write_bytes(encode(data))
    with pytest.raises(ValueError):
        Consumer(root)
    outside = tmp_path / 'manifest-copy.json'
    outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(ValueError):
        Consumer(root)


def test_mcp_registry_contains_only_read_only_product_tools():
    definitions = consumer_tools.tools()
    assert {item['name'] for item in definitions} == {
        'scirel_describe', 'scirel_browse', 'scirel_search', 'scirel_get', 'scirel_get_tutorial'}
    assert all(item['annotations']['readOnlyHint'] is True and
               item['annotations']['destructiveHint'] is False for item in definitions)
    for item in definitions:
        if item['name'] != 'scirel_describe':
            assert {'expected_snapshot_sha256', 'expected_wheel_sha256'} <= set(item['inputSchema']['required'])


def test_describe_then_exact_get_bind_the_full_contract_and_language(snapshot):
    root, manifest, documents = snapshot
    describe = consumer_tools.call_tool(root, 'scirel_describe')
    assert describe['outcome'] == 'ok'
    assert describe['snapshot_sha256'] == manifest['manifest_sha256']
    assert describe['wheel_sha256'] == sha(WHEEL_BYTES)
    args = {**_pins(manifest), 'asset_id': ASSET, 'language': 'zh'}
    original = dict(args)
    result = consumer_tools.call_tool(root, 'scirel_get', args)
    assert args == original
    assert result['outcome'] == 'ok'
    assert result['document'] == documents[ASSET]
    assert result['markdown'] == (root / f'docs/zh/api/{ASSET}.md').read_text()
    assert all(manifest['files'][path]['sha256'] == digest for path, digest in result['digests'].items())
    assert consumer_tools.call_tool(root, 'scirel_get', {
        **_pins(manifest), 'asset_id': 'scirel.synthetic.absent'})['outcome'] == 'unknown_asset'


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
    ('scirel_get_tutorial', {'chapter_id': 'synthetic'}),
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


def test_tutorial_discovery_uses_the_same_identity_budget_and_collection_bound_cursor(snapshot):
    root, _, _ = snapshot
    index_path = root / 'catalog/tutorial-index.json'
    index = json.loads(index_path.read_bytes())
    index['chapters'].append({'chapter_id': 'another', 'paths': {
        lang: f'docs/{lang}/tutorials/another.md' for lang in ('en', 'zh')}})
    for lang in ('en', 'zh'):
        (root / f'docs/{lang}/tutorials/another.md').write_text('# Another synthetic fixture\n')
    index_path.write_bytes(encode(index))
    manifest = _reseal(root)
    args = {**_pins(manifest), 'collection': 'tutorials', 'limit': 1, 'max_bytes': 4096}
    first = consumer_tools.call_tool(root, 'scirel_browse', args)
    assert first['outcome'] == 'match' and first['collection'] == 'tutorials'
    assert len(json.dumps(first, ensure_ascii=False).encode()) <= args['max_bytes']
    second = consumer_tools.call_tool(root, 'scirel_browse', {**args, 'cursor': first['next_cursor']})
    assert [item['chapter_id'] for page in (first, second) for item in page['result']['items']] == ['another', 'synthetic']
    assert second['next_cursor'] is None
    assert consumer_tools.call_tool(root, 'scirel_browse', {
        **args, 'collection': 'capabilities', 'cursor': first['next_cursor']})['outcome'] == 'invalid_request'


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


def test_tutorial_pages_reconstruct_exact_unicode_and_reject_invalid_budget(snapshot):
    root, manifest, _ = snapshot
    args = {**_pins(manifest), 'chapter_id': 'synthetic', 'language': 'zh', 'limit_chars': 7}
    parts, offset, expected_digest = [], 0, sha(TUTORIAL.encode())
    while True:
        page = consumer_tools.call_tool(root, 'scirel_get_tutorial', {**args, 'offset': offset})
        assert page['outcome'] == 'ok'
        assert page['sha256'] == expected_digest
        assert page['total_chars'] == len(TUTORIAL)
        assert len(page['markdown']) <= 7
        parts.append(page['markdown'])
        offset = page['next_offset']
        if offset is None:
            break
    assert ''.join(parts) == TUTORIAL
    assert consumer_tools.call_tool(root, 'scirel_get_tutorial', {
        **args, 'limit_chars': 20001})['outcome'] == 'invalid_request'
    assert consumer_tools.call_tool(root, 'scirel_get_tutorial', {
        **args, 'chapter_id': 'absent'})['outcome'] == 'unknown_tutorial'


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
def test_malformed_manifest_returns_metadata_error_without_uncaught_exceptions(snapshot, malformation):
    root, _, _ = snapshot
    path = root / 'manifest.json'
    if malformation == 'not_object':
        path.write_bytes(encode([]))
    else:
        manifest = json.loads(path.read_bytes())
        del manifest['runtime']
        del manifest['manifest_sha256']
        manifest['manifest_sha256'] = sha(encode(manifest))
        path.write_bytes(encode(manifest))
    result = consumer_tools.call_tool(root, 'scirel_describe')
    assert result['outcome'] == 'metadata_error'
