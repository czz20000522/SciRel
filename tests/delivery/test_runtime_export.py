"""Exercise runtime export using synthetic documents and a metadata-only ZIP.

The fixture replaces scientific validation and documentation loading, while the
real exporter projects articles, preserves the skill tree, closes links, seals
runtime members and supplies the standalone CLI. No library wheel is built or
installed and no scientific calculation is performed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_pure_delivery as delivery  # noqa: E402
import exposure  # noqa: E402
from query import Consumer, encode, sha  # noqa: E402
import validate_installed_wheel  # noqa: E402

SOURCE = '0' * 40
ASSET = 'scirel.synthetic.alpha'
NOTICE = b'Synthetic fixture notice; no scientific validation.\n'


def _write(root, relative, data):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data if isinstance(data, bytes) else data.encode())


class _Documentation:
    def __init__(self, language, contract):
        self.ids = {ASSET}
        self.files = {
            'handbook.json': encode({'chapters': [{'id': 'synthetic'}]}),
            'records/' + ASSET + '.json': contract,
            'readers/' + ASSET + '.json': encode({'title': '合成示例'}),
            'web/index.html': (
                '<a href="reference/generated/' + ASSET + '.html">API</a>'
                '<a href="user-guide/synthetic.html">Tutorial</a>').encode(),
            'web/reference/generated/' + ASSET + '.html': (
                '<article class="bd-article"><h1>Synthetic API ' + language + '</h1>'
                '<p>Fixture only. <a href="/api/asset?id=' + ASSET + '">Contract</a> '
                '<a href="../../user-guide/synthetic.html#limits">Tutorial</a></p>'
                '<pre>print(0)\n</pre><p class="rubric">Actual output</p><pre>0\n</pre>'
                '<img src="../../_images/diagram.svg" alt="Synthetic diagram"></article>').encode(),
            'web/user-guide/synthetic.html': (
                '<article class="bd-article"><h1>Synthetic tutorial ' + language + '</h1>'
                '<p>Scope: synthetic scalar fixture. 合成示例。</p><pre>print(0)\n</pre>'
                '<p><a href="../reference/generated/' + ASSET + '.html">API</a></p>'
                '<p><a href="../tutorials/supplement.html">Further reading</a></p></article>').encode(),
            'web/tutorials/supplement.html': (
                '<article class="bd-article"><h1>Supplement ' + language + '</h1>'
                '<p>Keep every unvalidated assumption visible.</p></article>').encode(),
            'web/_images/diagram.svg': b'<svg xmlns="http://www.w3.org/2000/svg"/>\n',
        }
        self.manifest = {
            'source_revision': SOURCE, 'source_dirty': False,
            'reader_language': {'en': 'en-US', 'zh': 'zh-CN'}[language],
            'files': {relative: {} for relative in self.files},
        }

    def read(self, relative):
        return self.files[relative]

    def capability_index(self):
        record = {
            'asset_id': ASSET, 'symbol': 'alpha', 'capability': 'synthetic scalar',
            'capability_summary': 'Unvalidated synthetic fixture',
            'operation': 'evaluate', 'operation_direction': 'input to output',
            'model': 'synthetic algebraic fixture', 'geometry': 'scalar',
            'coordinates': 'none', 'boundary': 'unknown',
            'device_scope': 'unclassified', 'device_scope_source': 'unspecified',
            'aliases': ['synthetic', 'alpha'], 'taxonomy': [], 'title_zh': '合成示例',
        }
        return {'schema': 'scirel.capability-index', 'source_revision': SOURCE,
                'asset_count': 1, 'assets': [record],
                'search_text': {ASSET: 'synthetic scalar alpha 合成示例'}}


@pytest.fixture
def export_case(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    contract = encode({'asset_id': ASSET, 'notice': 'Synthetic fixture, not a science claim.',
                       'example': {'code': 'print(0)', 'output': '0'}})
    _write(source, 'catalog/examples/' + ASSET + '.json', contract)
    _write(source, 'licenses/NOTICE.txt', NOTICE)
    for name in ('query.py', 'capability_query.py', 'consumer_tools.py', 'serve_consumer_mcp.py'):
        _write(source, 'scripts/' + name, (ROOT / 'scripts' / name).read_bytes())
    _write(source, 'tools/docs/mcp-requirements.txt', 'mcp==2.3.0\nmcp-types==2.3.0\n')
    skill = source / 'skills/development/usage/scirel-solving'
    _write(skill, 'SKILL.md', '---\nname: scirel-solving\ndescription: Synthetic solving method.\n---\n'
           '# One method\n\n[Checks](references/checks.md)\n')
    _write(skill, 'references/checks.md', '# Checks\n\nKeep failures visible. '
           '[Helper](../scripts/delivery.py)\n')
    _write(skill, 'scripts/delivery.py', 'print("synthetic helper")\n')
    wheel = tmp_path / 'synthetic-0-py3-none-any.whl'
    with ZipFile(wheel, 'w') as archive:
        archive.writestr('synthetic-0.dist-info/METADATA',
                         'Metadata-Version: 2.4\nName: synthetic\nVersion: 0\n'
                         'Requires-Python: >=3.14,<3.15\nRequires-Dist: numpy==2.5.4\n\n')
        archive.writestr('synthetic-0.dist-info/licenses/licenses/NOTICE.txt', NOTICE)
    snapshots = {language: _Documentation(language, contract) for language in ('en', 'zh')}
    closure = {
        'schema': 'scirel.consumer-source-closure', 'source_revision': SOURCE,
        'asset_count': 1, 'source_signature_check': 'PASS',
        'natural_language_scientific_review': 'NOT_RUN',
        'generator_and_reading_inputs': {
            path.relative_to(source).as_posix(): sha(path.read_bytes())
            for path in source.rglob('*') if path.is_file()},
    }

    def git_check(command, *, cwd, text=False):
        assert cwd == source
        if command == ['git', 'rev-parse', 'HEAD']:
            return SOURCE + '\n' if text else (SOURCE + '\n').encode()
        assert command == ['git', 'status', '--porcelain']
        return '' if text else b''

    monkeypatch.setattr(delivery, 'ROOT', source)
    monkeypatch.setattr(delivery.subprocess, 'check_output', git_check)
    monkeypatch.setattr(delivery, 'Documentation', lambda root: snapshots[Path(root).name])
    monkeypatch.setattr(delivery, 'source_closure', lambda snapshots, revision: closure)
    monkeypatch.setattr(delivery, 'inspect_wheel', lambda path, **kwargs:
                        {'status': 'PASS', 'sha256': sha(path.read_bytes())})
    monkeypatch.setattr(validate_installed_wheel, '_catalog_wheel_closure',
                        lambda *args, **kwargs: ({'status': 'PASS'}, []))
    monkeypatch.setattr(exposure, 'held_asset_ids', lambda: set())
    return SimpleNamespace(source=source, skill=skill, wheel=wheel, contract=contract,
                           agent=tmp_path / 'agent', html=tmp_path / 'html', closure=closure)


def _export(case):
    return delivery.build(case.wheel, Path('en'), Path('zh'), case.agent, case.html)


def _cli(case, *arguments, expected_exit=0):
    # -S excludes site-packages, including every optional MCP/SDK dependency.
    pins = []
    if arguments[0] != 'describe':
        identity = json.loads((case.agent / 'runtime.json').read_bytes())
        pins = ['--expected-snapshot-sha256', identity['snapshot_sha256'],
                '--expected-wheel-sha256', identity['runtime']['wheel_sha256']]
    completed = subprocess.run(
        [sys.executable, '-S', '-B', str(case.agent / 'tools/query.py'),
         '--root', str(case.agent), *arguments, *pins], cwd=case.agent.parent,
        env={key: value for key, value in os.environ.items() if key != 'PYTHONPATH'},
        capture_output=True, text=True, check=False, timeout=20)
    assert completed.returncode == expected_exit, completed.stderr or completed.stdout
    assert not completed.stderr
    return json.loads(completed.stdout)


def test_export_supplies_a_closed_skill_tree_and_standalone_runtime(export_case):
    case = export_case
    result = _export(case)
    expected = {
        'README.md', 'runtime.json', 'runtime-requirements.txt', 'mcp-requirements.txt',
        'wheel/' + case.wheel.name,
        'tools/query.py', 'tools/capability_query.py', 'tools/consumer_tools.py', 'tools/server.py',
        'skills/scirel-solving/SKILL.md', 'skills/scirel-solving/references/checks.md',
        'skills/scirel-solving/scripts/delivery.py',
        'catalog/capability-index.json', 'catalog/tutorial-index.json',
        'catalog/contracts/' + ASSET + '.json',
        *{f'docs/{language}/{relative}' for language in ('en', 'zh') for relative in (
            'api/' + ASSET + '.md', 'tutorials/synthetic.md',
            'tutorials/supplement.md', 'assets/diagram.svg')},
    }
    actual = {path.relative_to(case.agent).as_posix()
              for path in case.agent.rglob('*') if path.is_file()}
    assert actual == expected
    expected_html = {'index.html', 'licenses/NOTICE.txt'} | {
        language + '/' + relative for language in ('en', 'zh') for relative in (
            'records/' + ASSET + '.json', 'readers/' + ASSET + '.json',
            'web/index.html', 'web/reference/generated/' + ASSET + '.html',
            'web/user-guide/synthetic.html', 'web/tutorials/supplement.html',
            'web/_images/diagram.svg')}
    assert {path.relative_to(case.html).as_posix()
            for path in case.html.rglob('*') if path.is_file()} == expected_html
    identity = json.loads((case.agent / 'runtime.json').read_bytes())
    assert result['agent'] == identity
    assert set(identity) == {'schema', 'source_revision', 'asset_count', 'runtime',
                             'retrieval', 'files', 'snapshot_sha256'}
    assert identity['schema'] == 'scirel.consumer-runtime'
    assert identity['source_revision'] == SOURCE and identity['asset_count'] == 1
    assert set(identity['files']) == expected - {'runtime.json'}
    assert identity['snapshot_sha256'] == sha(encode({
        key: value for key, value in identity.items() if key != 'snapshot_sha256'}))
    for relative, metadata in identity['files'].items():
        data = (case.agent / relative).read_bytes()
        assert metadata == {'sha256': sha(data), 'bytes': len(data)}
    for relative in ('SKILL.md', 'references/checks.md', 'scripts/delivery.py'):
        assert (case.agent / 'skills/scirel-solving' / relative).read_bytes() == (
            case.skill / relative).read_bytes()
    assert (case.agent / 'tools/query.py').read_bytes() == (case.source / 'scripts/query.py').read_bytes()
    assert (case.agent / 'catalog/contracts' / (ASSET + '.json')).read_bytes() == case.contract
    assert (case.agent / 'runtime-requirements.txt').read_text().splitlines()[-1] == 'numpy==2.5.4'
    assert (case.html / 'licenses/NOTICE.txt').read_bytes() == NOTICE
    with ZipFile(case.agent / 'wheel' / case.wheel.name) as wheel:
        assert wheel.read('synthetic-0.dist-info/licenses/licenses/NOTICE.txt') == NOTICE
    checks = result['checks']['source_closure']['local_links']
    assert all(item['status'] == 'PASS' and item['links_checked'] > 0 for item in checks.values())

    described = _cli(case, 'describe')
    assert described['asset_count'] == 1 and described['tutorial_count'] == 2
    assert described['snapshot_sha256'] == identity['snapshot_sha256']
    assert described['wheel_sha256'] == sha(case.wheel.read_bytes())
    browsed = _cli(case, 'browse', '--collection', 'tutorials', '--limit', '1')
    assert browsed['result']['total'] == 2
    assert browsed['result']['items'][0]['chapter_id'] == 'supplement'
    searched = _cli(case, 'search', '--q', 'synthetic', '--limit', '1')
    assert searched['result']['items'][0]['asset_id'] == ASSET
    selected = _cli(case, 'get', ASSET, '--language', 'zh')
    assert selected['document'] == json.loads(case.contract)
    assert 'print(0)' in selected['markdown'] and 'Synthetic API zh' in selected['markdown']
    passage = _cli(case, 'get_tutorial', 'synthetic', '--language', 'zh', '--limit-chars', '30')
    full_tutorial = (case.agent / 'docs/zh/tutorials/synthetic.md').read_text()
    assert passage['markdown'] == full_tutorial[:30] and passage['next_offset'] == 30
    assert Consumer(case.agent).verify()['files_verified'] == len(expected)

    _write(case.agent, 'catalog/contracts/' + ASSET + '.json', b'{"asset_id":"changed"}\n')
    rejected = _cli(case, 'get', ASSET, expected_exit=2)
    assert rejected['outcome'] == 'metadata_error' and 'changed' in rejected['error']


def test_export_rejects_a_skill_helper_changed_after_capture(export_case, monkeypatch):
    case = export_case
    original = delivery.markdown
    changed = False

    def project_and_mutate(*args, **kwargs):
        nonlocal changed
        result = original(*args, **kwargs)
        if not changed:
            (case.skill / 'scripts/delivery.py').write_text('print("changed after capture")\n')
            changed = True
        return result

    monkeypatch.setattr(delivery, 'markdown', project_and_mutate)
    with pytest.raises(ValueError, match='source input changed|solving source changed'):
        _export(case)
    assert changed
    assert not case.agent.exists() and not case.html.exists()
    assert not list(case.agent.parent.glob('.scirel-delivery-stage-*'))
