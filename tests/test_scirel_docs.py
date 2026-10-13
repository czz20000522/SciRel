"""Human and Agent documentation share immutable canonical records."""
import json
from pathlib import Path
import sys
import subprocess
import threading
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from scirel_docs import Documentation, build, server


@pytest.fixture
def snapshot(tmp_path):
    output = tmp_path / 'docs'
    build(ROOT / 'catalog/examples', output)
    return output


def test_queries_are_bounded_and_exact_records_unchanged(snapshot):
    docs = Documentation(snapshot)
    p = docs.search('Pleiades', limit=2)
    assert p['total'] > 2 and len(p['items']) == 2 and p['next_offset'] == 2
    assert not any('search_text' in x for x in p['items'])
    assert docs.search('pleiades')['total'] == p['total']
    assert docs.search('unfindable-xyz')['items'] == []
    asset = p['items'][0]['asset_id']
    original = json.loads((ROOT / 'catalog/examples' / f'{asset}.json').read_text())
    assert docs.asset(asset)['document'] == original
    assert docs.search(kind='task_graph', domain='equilibrium')['total'] > 0
    assert docs.search('中文未找到', offset=999)['next_offset'] is None
    code = 'from scirel_docs import Documentation; import sys; Documentation(sys.argv[1]).search(); assert not any(n == "scirel" or n.startswith("scirel.") for n in sys.modules)'
    subprocess.run([sys.executable, '-c', code, str(snapshot)], cwd=ROOT/'scripts', check=True)


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
            assert '科学关系手册' in r.read().decode()
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
        build(ROOT / 'catalog/examples', snapshot)
    bad = tmp_path / 'bad'; bad.mkdir()
    (bad / 'fake.json').write_text('{"title":"invented"}')
    with pytest.raises(ValueError):
        build(bad, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()
