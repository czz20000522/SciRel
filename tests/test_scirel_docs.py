"""Human and Agent documentation share immutable canonical records."""
import json
from pathlib import Path
import sys
import subprocess
import shutil
import threading
import tomllib
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from scirel_docs import Documentation, build, project_version, server
from _document_fixtures import copy_example_closure, example_document_sources


@pytest.fixture(scope='session')
def built_snapshot(tmp_path_factory):
    output = tmp_path_factory.mktemp('sphinx') / 'docs'
    documents = copy_example_closure(tmp_path_factory.mktemp('reader-inputs') / 'documents')
    build(documents, output)
    return output


@pytest.fixture
def snapshot(tmp_path, built_snapshot):
    return Path(shutil.copytree(built_snapshot, tmp_path / 'docs'))


def test_queries_are_bounded_and_exact_records_unchanged(snapshot):
    docs = Documentation(snapshot)
    p = docs.search('Pleiades', limit=2)
    assert p['total'] > 2 and len(p['items']) == 2 and p['next_offset'] == 2
    assert not any('search_text' in x for x in p['items'])
    assert docs.search('pleiades')['total'] == p['total']
    assert docs.search('unfindable-xyz')['items'] == []
    asset = p['items'][0]['asset_id']
    original = json.loads(example_document_sources()[asset].read_text())
    assert docs.asset(asset)['document'] == original
    assert docs.search(kind='task_graph', domain='equilibrium')['total'] > 0
    assert docs.search('中文未找到', offset=999)['next_offset'] is None
    code = 'from scirel_docs import Documentation; import sys; Documentation(sys.argv[1]).search(); assert not any(n == "scirel" or n.startswith("scirel.") for n in sys.modules)'
    subprocess.run([sys.executable, '-c', code, str(snapshot)], cwd=ROOT/'scripts', check=True)


def test_document_builder_reads_the_project_version_from_pyproject():
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    assert project_version() == project['project']['version']


@pytest.mark.parametrize('url', ['/api/search?limit=0', '/api/search?limit=101',
                                 '/api/search?offset=-1', '/api/search?offset=x',
                                 '/api/search?q=a&q=b', '/api/search?unknown=x',
                                 '/api/search?kind=other'])
def test_invalid_queries_fail_closed(snapshot, url):
    with pytest.raises(ValueError):
        Documentation(snapshot).handle(url)


def test_snapshot_tampering_and_path_escape(snapshot, tmp_path):
    docs = Documentation(snapshot)
    with pytest.raises(ValueError, match='expected digest'):
        Documentation(snapshot, '0'*64)
    asset = docs.index[0]['asset_id']
    (snapshot / 'records' / f'{asset}.json').write_text('{}')
    with pytest.raises(ValueError, match='bytes changed'):
        docs.asset(asset)
    with pytest.raises(KeyError):
        docs.asset('../../manifest')
    (snapshot / 'index.json').write_text('[]')
    with pytest.raises(ValueError, match='bytes changed'):
        docs.search()


def test_http_matches_cli_core_and_does_not_serve_source(snapshot):
    docs = Documentation(snapshot)
    http = server(docs, 0)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{http.server_port}'
    try:
        with urlopen(base + '/api/search?q=Pleiades&limit=2') as r:
            assert json.load(r) == docs.search('Pleiades', limit=2)
        with urlopen(base + '/') as r:
            assert 'SciRel 中文文档' in r.read().decode()
        with pytest.raises(HTTPError) as e:
            urlopen(base + '/../../pyproject.toml')
        assert e.value.code == 404
        with pytest.raises(HTTPError) as e:
            urlopen(base + '/api/search?limit=abc')
        assert e.value.code == 400
    finally:
        http.shutdown(); http.server_close(); thread.join()


def test_build_refuses_overwrite_and_invalid_documents(snapshot, tmp_path):
    with pytest.raises(FileExistsError):
        build(copy_example_closure(tmp_path / 'documents'), snapshot)
    bad = tmp_path / 'bad'; bad.mkdir()
    (bad / 'fake.json').write_text('{"title":"invented"}')
    with pytest.raises(ValueError):
        build(bad, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_chapter_http_cli_and_download_share_execution(snapshot):
    docs = Documentation(snapshot)
    chapter = docs.handle('/api/chapter?id=magnetostatics')['document']
    assert chapter['discipline'] == ['电磁学', '磁静力学']
    assert chapter['results']['all_checks_passed'] is True
    assert 0.00179 < chapter['results']['center_single_T'] < 0.00180
    assert all(x['id'] in docs.ids for x in chapter['assets'])
    assert 'circular_filament_green_response' in chapter['sections'][0]['code']
    assert docs.handle('/api/chapters')['items'][0]['id'] == chapter['id']
    cli = subprocess.check_output([sys.executable, str(ROOT/'scripts/scirel_docs.py'),
                                  'query', '--snapshot', str(snapshot), '--chapter', chapter['id']])
    assert json.loads(cli)['document'] == chapter
    with pytest.raises(KeyError):
        docs.chapter('../../source')
    (snapshot/'chapters/magnetostatics/chapter.json').write_text('{}')
    with pytest.raises(ValueError, match='bytes changed'):
        docs.chapter(chapter['id'])


def test_chapter_build_rejects_stale_execution(tmp_path, monkeypatch):
    import shutil
    import scirel_docs
    copy = tmp_path/'repo'
    shutil.copytree(ROOT/'tools/docs', copy/'tools/docs')
    # This test exercises the preserved historical checker fixture. Current
    # successor qualification is tested by the normal snapshot build above.
    (copy/'tools/docs/chapter-selection.json').unlink(missing_ok=True)
    binding = json.loads((copy/'tools/docs/magnetostatics/execution.json').read_text())
    for path in list(binding['files']) + list(binding['document_files']):
        target = copy/path
        target.parent.mkdir(parents=True, exist_ok=True)
        # The qualification record is historical evidence. Seed this checker
        # fixture with its bound committed bytes, not the changed successor.
        body = subprocess.check_output(['git', 'show', 'f669ee6c0f4b5d973d3f2c95666d970d48f42ac7:' + path], cwd=ROOT)
        import hashlib
        expected = (binding['files'] | binding['document_files'])[path]
        assert hashlib.sha256(body).hexdigest() == expected
        target.write_bytes(body)
    monkeypatch.setattr(scirel_docs, 'ROOT', copy)
    asset_ids = {x['id'] for x in json.loads((copy/'tools/docs/magnetostatics/chapter.json').read_text())['assets']}
    scirel_docs.chapter_files(asset_ids)
    path = copy/next(iter(binding['files']))
    path.write_text(path.read_text()+'\n# changed\n')
    with pytest.raises(ValueError, match='implementation changed'):
        scirel_docs.chapter_files(asset_ids)


def test_successor_chapter_selection_is_explicit_and_digest_bound(tmp_path, monkeypatch):
    import hashlib
    import scirel_docs
    root = tmp_path/'tools/docs'; root.mkdir(parents=True)
    successor = root/'magnetostatics-20261013'; successor.mkdir()
    execution = successor/'execution.json'; execution.write_text('{}')
    selection = {'schema': 'scirel.chapter-selection.v1', 'chapters': {
        'magnetostatics': {'directory': 'tools/docs/magnetostatics-20261013',
                          'execution_sha256': hashlib.sha256(execution.read_bytes()).hexdigest()}}}
    path = root/'chapter-selection.json'; path.write_text(json.dumps(selection))
    monkeypatch.setattr(scirel_docs, 'ROOT', tmp_path)
    assert scirel_docs.chapter_directory() == successor
    execution.write_text('{"changed":true}')
    with pytest.raises(ValueError, match='execution bytes changed'):
        scirel_docs.chapter_directory()
    selection['chapters']['magnetostatics']['directory'] = 'tools/docs/../../outside'
    path.write_text(json.dumps(selection))
    with pytest.raises(ValueError, match='selection path'):
        scirel_docs.chapter_directory()


def test_handbook_covers_exact_records_and_topic_queries_match(snapshot):
    docs = Documentation(snapshot)
    book = docs.handle('/api/handbook')['document']
    topics = [t for c in book['chapters'] for t in c['topics']]
    ids = [a for t in topics for a in t['assets']]
    assert len(ids) == len(set(ids)) == len(docs.ids)
    assert set(ids) == docs.ids
    for topic in topics:
        assert docs.handle('/api/topic?id=' + topic['id'])['document'] == topic
        result = docs.search(topic=topic['id'], limit=100)
        assert {x['asset_id'] for x in result['items']} == set(topic['assets'])
        for item in result['items']:
            assert item['public_api'] == docs.asset(item['asset_id'])['document']['public_api']
    cli = subprocess.check_output([sys.executable, str(ROOT/'scripts/scirel_docs.py'),
                                   'query', '--snapshot', str(snapshot), '--handbook'])
    assert json.loads(cli) == docs.handbook()
    cli = subprocess.check_output([sys.executable, str(ROOT/'scripts/scirel_docs.py'),
                                   'query', '--snapshot', str(snapshot), '--topic', topics[0]['id'], '--limit', '100'])
    assert json.loads(cli) == docs.search(topic=topics[0]['id'], limit=100)
    with pytest.raises(KeyError):
        docs.handle('/api/search?topic=unknown')
    with pytest.raises(KeyError):
        docs.handle('/api/topic?id=../../anything')
    (snapshot/'handbook.json').write_text('{}')
    with pytest.raises(ValueError, match='bytes changed'):
        docs.search(topic=topics[0]['id'])


def test_handbook_invalid_navigation_fails_closed(tmp_path, monkeypatch):
    import scirel_docs
    original = json.loads((ROOT/'tools/docs/handbook.json').read_text())
    ids = {a for c in original['chapters'] for t in c['topics'] for a in t['assets']}
    target = tmp_path/'tools/docs/handbook.json'; target.parent.mkdir(parents=True)
    monkeypatch.setattr(scirel_docs, 'ROOT', tmp_path)
    for mode in ['missing', 'unknown', 'duplicate', 'tutorial', 'duplicate_id']:
        book = json.loads(json.dumps(original)); topics = book['chapters'][0]['topics']
        if mode == 'missing': topics[0]['assets'].pop()
        if mode == 'unknown': topics[0]['assets'].append('unknown')
        if mode == 'duplicate': topics[0]['assets'].append(topics[0]['assets'][0])
        if mode == 'tutorial': topics[0]['tutorial_id'] = '../../not-executed'
        if mode == 'duplicate_id': topics[0]['id'] = book['chapters'][0]['id']
        target.write_text(json.dumps(book))
        with pytest.raises(ValueError):
            scirel_docs.handbook_document(ids)


def test_chinese_reader_http_cli_and_exact_source(snapshot):
    docs = Documentation(snapshot)
    asset = 'scirel.field.current-green-superposition'
    response = docs.reader(asset)
    assert response['document'] == docs.asset(asset)['document']
    assert docs.read(f'records/{asset}.json') == (ROOT/'catalog/examples'/f'{asset}.json').read_bytes()
    assert response['translation']['asset_id'] == asset
    assert any('\u4e00' <= c <= '\u9fff' for c in response['translation']['summary'])
    assert docs.search('线圈')['total'] > 0
    assert docs.handle('/api/reader?id=' + asset) == response
    cli = subprocess.check_output([sys.executable, str(ROOT/'scripts/scirel_docs.py'),
                                   'query', '--snapshot', str(snapshot), '--reader', asset])
    assert json.loads(cli) == response
    http = server(docs, 0)
    thread = threading.Thread(target=http.serve_forever, daemon=True); thread.start()
    try:
        with urlopen(f'http://127.0.0.1:{http.server_port}/api/reader?id=' + asset) as r:
            assert json.load(r) == response
        with urlopen(f'http://127.0.0.1:{http.server_port}/reference/generated/{asset}.html') as r:
            page = r.read().decode()
            assert 'pydata-sphinx-theme' in page and '参数' in page and '返回值' in page
            assert 'copybutton.js' in page
    finally:
        http.shutdown(); http.server_close(); thread.join()
    (snapshot/'readers'/f'{asset}.json').write_text('{}')
    with pytest.raises(ValueError, match='bytes changed'):
        docs.reader(asset)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'stale', 'port', 'clause'])
def test_reader_translation_cannot_drift_or_drop_contracts(tmp_path, change):
    from build_scirel_sphinx import load_translations
    from validate_asset_documents import load_document_set
    shutil.copytree(ROOT/'tools/docs/zh', tmp_path/'tools/docs/zh')
    path = next((tmp_path/'tools/docs/zh').glob('*.json'))
    data = json.loads(path.read_bytes()); first = data['records'][0]
    if change == 'missing': data['records'].pop()
    elif change == 'duplicate': data['records'].append(first)
    elif change == 'stale': first['source_sha256'] = '0'*64
    elif change == 'port': first['inputs'][0]['name'] = 'invented'
    elif change == 'clause': first['applicability']['supported'].append('invented')
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        documents = copy_example_closure(tmp_path / 'documents')
        load_translations(tmp_path, documents, load_document_set(documents))


def test_all_reference_pages_exist_and_use_bound_chinese_prose(snapshot):
    docs = Documentation(snapshot)
    for asset in docs.ids:
        page = docs.read('web/reference/generated/' + asset + '.html').decode()
        assert all(label in page for label in ['参数', '返回值', '说明', '示例', '验证与限制'])
        assert docs.reader(asset)['translation']['source_sha256'] in page
    assert b'copybutton.js' in docs.read('web/index.html')
    renderer = json.loads(docs.read('renderer.json'))
    assert renderer['source_documents'] == len(docs.ids)
    assert renderer['warnings_as_errors'] and not renderer['science_imports']
    graph = docs.read('web/reference/generated/scirel.equilibrium.free-boundary-anisotropic-picard.html').decode()
    assert 'href="scirel.field.poloidal-field-magnitude.html"' in graph
    wave = docs.read('web/reference/generated/scirel.kinetic.kinetic-dispersion-ronnmark.html').decode()
    assert '<math ' in wave and '<msub>' in wave and 'aria-label=' in wave


def test_inline_scientific_math_and_code_do_not_execute_rest():
    from build_scirel_sphinx import plain
    value = plain(r'张量 $K_{ij}=\delta_{ij}$；调用 `evaluate`。')
    assert '<msub>' in value and ' ``evaluate`` ' in value
    assert '\\*' in plain('*未声明标记*')
    assert '\n' not in plain('\n.. include:: /etc/passwd')


def test_reference_domains_list_linked_functions_and_keep_sidebar_compact(snapshot):
    from bs4 import BeautifulSoup
    docs = Documentation(snapshot)
    book = json.loads((ROOT/'tools/docs/handbook.json').read_bytes())
    seen = set()
    for chapter in book['chapters']:
        page = BeautifulSoup(docs.read('web/reference/'+chapter['id']+'.html'), 'html.parser')
        rows = page.select('article table.scirel-api-summary tbody tr')
        expected = [asset for topic in chapter['topics'] for asset in topic['assets']]
        assert len(rows) == len(expected)
        for row, asset in zip(rows, expected, strict=True):
            seen.add(asset)
            cells = row.find_all('td')
            record = docs.asset(asset)['document']
            link = cells[0].find('a')
            assert link['href'] == 'generated/'+asset+'.html'
            assert link.get_text(strip=True) == record['public_api']['python']['symbol']
            assert len(cells[1].get_text(strip=True)) > 10
            assert ('（复合入口）' in cells[1].get_text()) == (record['kind'] == 'task_graph')
        sidebar = page.select_one('nav.bd-docs-nav')
        assert len(sidebar.select('a')) == len(book['chapters'])
        assert not sidebar.select('a[href*="generated/"]')
    assert seen == set(docs.ids)
    for asset in docs.ids:
        page = BeautifulSoup(docs.read('web/reference/generated/'+asset+'.html'), 'html.parser')
        sidebar = page.select_one('nav.bd-docs-nav')
        assert len(sidebar.select('a')) == len(book['chapters'])
        assert not sidebar.select('a[href*="generated/"]')


def test_explicit_reader_bundle_selects_exact_distribution_without_global_records(tmp_path):
    from build_scirel_sphinx import load_translations
    asset = "scirel.field.poloidal-field-magnitude"
    source = example_document_sources()[asset]
    documents = tmp_path / "documents"
    documents.mkdir()
    shutil.copy2(source, documents / (asset + ".json"))
    doc = json.loads(source.read_bytes())
    records = [record for file in (ROOT / "tools/docs/zh").glob("*.json")
               for record in json.loads(file.read_bytes())["records"] if record["asset_id"] == asset]
    assert len(records) == 1
    bundle = tmp_path / "selected-readers.json"
    bundle.write_text(json.dumps({"schema": "scirel.reader-translation.v1", "language": "zh-CN", "records": records}))
    # Default retains the strict complete global scope and rejects this subset.
    with pytest.raises(ValueError, match="coverage differs"):
        load_translations(ROOT, documents, [doc])
    selected = load_translations(ROOT, documents, [doc], translation_paths=[bundle])
    assert set(selected) == {asset}
    # Explicit selection still rejects missing, extra and stale records.
    for changed in [[], records + [records[0]], [dict(records[0], source_sha256="0"*64)]]:
        bundle.write_text(json.dumps({"schema": "scirel.reader-translation.v1", "language": "zh-CN", "records": changed}))
        with pytest.raises(ValueError):
            load_translations(ROOT, documents, [doc], translation_paths=[bundle])
