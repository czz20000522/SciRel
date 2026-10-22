"""Official MCP Client transport checks, enabled with SCIREL_MCP_PYTHON.

The optional interpreter must contain tools/docs/mcp-requirements.txt. SDK
dependencies do not enter the scientific library or the project's test venv.
The fixture is explicitly synthetic and tests transport/consumer behavior only.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from consumer_tools import tools  # noqa: E402

# Executed by the isolated SDK interpreter. Both transports use the real
# official Client in auto-negotiation mode, never a pinned/faked protocol.
CLIENT_PROBE = r'''
import asyncio
from importlib.metadata import version
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from mcp import Client, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
import httpx2

config = json.load(sys.stdin)
scripts = Path(config['scripts']).resolve()
root = Path(config['root']).resolve()

async def exercise(target):
    async with Client(target, read_timeout_seconds=10) as client:
        advertised = await client.list_tools()
        exact = [tool.model_dump(by_alias=True, exclude_none=True) for tool in advertised.tools]
        assert exact == config['registry'], (exact, config['registry'])
        assert len(exact) == 5
        assert all(tool['annotations']['readOnlyHint'] is True for tool in exact)
        discovery = client.session.discover_result
        assert discovery is not None, 'auto mode must perform real discovery'
        assert client.protocol_version in discovery.supported_versions
        results = {}

        async def call(label, name, args, outcome, is_error=False):
            response = await client.call_tool(name, args)
            assert response.is_error is is_error, (label, response)
            data = response.structured_content
            assert data['outcome'] == outcome, (label, data)
            assert json.loads(response.content[0].text) == data
            results[label] = data
            return data

        description = await call('describe', 'scirel_describe', {}, 'ok')
        pins = {'expected_snapshot_sha256': description['snapshot_sha256'],
                'expected_wheel_sha256': description['wheel_sha256']}
        first = await call('browse', 'scirel_browse', {**pins, 'limit': 1}, 'match')
        assert first['result']['items'][0]['asset_id'] == 'test.alpha'
        assert first['next_cursor']
        second = await call('browse_next', 'scirel_browse',
                            {**pins, 'limit': 1, 'cursor': first['next_cursor']}, 'match')
        assert second['result']['items'][0]['asset_id'] == 'test.beta'
        search = await call('search', 'scirel_search', {**pins, 'q': 'periodic flux', 'limit': 1}, 'match')
        assert search['result']['tokens'] == ['periodic', 'flux']
        assert search['result']['items'][0]['relevance']['matched_fields']
        assert search['result']['retrieval']['scientific_applicability'] == 'not_assessed'
        await call('no_candidates', 'scirel_search', {**pins, 'q': 'unfindable-xyz'}, 'no_candidates')
        near = await call('near_miss', 'scirel_search', {**pins, 'model': 'slab', 'boundary': 'open'}, 'near_miss')
        assert all(item['missed_filters'] for item in near['result']['items'])
        document = await call('get', 'scirel_get', {**pins, 'asset_id': 'test.alpha'}, 'ok')
        assert document['document']['asset_id'] == 'test.alpha'
        assert 'Synthetic API' in document['markdown']
        tutorial = await call('tutorial', 'scirel_get_tutorial',
                              {**pins, 'chapter_id': 'sample', 'limit_chars': 7}, 'ok')
        assert tutorial['markdown'] == 'Synthet' and tutorial['next_offset'] == 7
        await call('invalid', 'scirel_search', {**pins, 'limit': 0}, 'invalid_request', True)
        await call('missing_pin', 'scirel_search', {}, 'invalid_request', True)
        await call('wrong_pin', 'scirel_search', {**pins, 'expected_snapshot_sha256': '0' * 64}, 'identity_mismatch', True)
        await call('unknown_asset', 'scirel_get', {**pins, 'asset_id': 'test.absent'}, 'unknown_asset', True)
        index_path = root / 'catalog/capability-index.json'
        original = index_path.read_bytes()
        try:
            index_path.write_bytes(b'{}')
            await call('metadata_error', 'scirel_describe', {}, 'metadata_error', True)
        finally:
            index_path.write_bytes(original)
        assert not any(name == 'scirel' or name.startswith(('sphinx', 'numpy')) for name in sys.modules)
        return {'sdk_version': version('mcp'), 'protocol_version': client.protocol_version,
                'supported_versions': discovery.supported_versions,
                'server_info': client.server_info.model_dump() if client.server_info else None,
                'tools': exact, 'results': results}

server_args = [sys.executable, str(scripts / 'serve_consumer_mcp.py'), '--root', str(root)]

async def exercise_http(url):
    # Loopback verification must not inherit the host's external proxy route.
    async with httpx2.AsyncClient(trust_env=False,
                                  timeout=httpx2.Timeout(10.0, read=10.0)) as http_client:
        return await exercise(streamable_http_client(url, http_client=http_client))

if config['transport'] == 'stdio':
    target = StdioServerParameters(command=sys.executable, args=server_args[1:], cwd=root)
    output = asyncio.run(exercise(target))
else:
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    process = subprocess.Popen(server_args + ['--transport', 'streamable-http', '--host', '127.0.0.1',
                                              '--port', str(port)], stdout=subprocess.DEVNULL,
                               env={key: value for key, value in os.environ.items()
                                    if key != 'PYTHONDONTWRITEBYTECODE'})
    try:
        deadline = time.monotonic() + 10
        while True:
            if process.poll() is not None:
                raise RuntimeError('HTTP server exited before becoming ready')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('HTTP server did not become ready')
                time.sleep(0.05)
        output = asyncio.run(exercise_http('http://127.0.0.1:' + str(port) + '/mcp'))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
print(json.dumps(output, ensure_ascii=False, sort_keys=True))
'''


def _encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def sdk_python():
    configured = os.environ.get('SCIREL_MCP_PYTHON')
    if not configured:
        pytest.skip('NOT_RUN: set SCIREL_MCP_PYTHON to an isolated official MCP SDK interpreter')
    interpreter = Path(configured).absolute()
    assert interpreter.is_file(), 'SCIREL_MCP_PYTHON does not exist: ' + str(interpreter)
    return str(interpreter)


@pytest.fixture
def consumer_snapshot(tmp_path):
    root = tmp_path / 'consumer'
    records = [{
        'asset_id': 'test.' + suffix, 'capability': 'periodic flux integration',
        'capability_summary': 'synthetic retrieval fixture',
        'operation': 'field to flux', 'operation_direction': 'forward',
        'model': 'slab', 'geometry': 'Cartesian', 'coordinates': 'x, y',
        'boundary': 'periodic', 'device_scope': 'generic', 'aliases': ['周期通量'],
        'taxonomy': ['synthetic'],
    } for suffix in ('alpha', 'beta')]
    index = {'schema': 'scirel.capability-index', 'source_revision': 'a' * 40,
             'asset_count': len(records), 'assets': records,
             'search_text': {item['asset_id']: json.dumps(item, ensure_ascii=False).casefold()
                             for item in records}}
    files = {'catalog/capability-index.json': _encode(index),
             'catalog/tutorial-index.json': _encode({'chapters': [{
                 'chapter_id': 'sample', 'paths': {'en': 'docs/en/tutorials/sample.md',
                                                  'zh': 'docs/zh/tutorials/sample.md'}}]}),
             'docs/en/tutorials/sample.md': b'Synthetic tutorial with a bounded continuation.\n',
             'docs/zh/tutorials/sample.md': '合成教程，仅验证传输。\n'.encode()}
    for record in records:
        asset = record['asset_id']
        files['catalog/contracts/' + asset + '.json'] = _encode({'asset_id': asset})
        for language in ('en', 'zh'):
            files['docs/' + language + '/api/' + asset + '.md'] = b'# Synthetic API\n'
    manifest = {'schema': 'scirel.pure-consumption', 'source_revision': 'a' * 40,
                'asset_count': len(records), 'snapshot_id': 'c' * 64,
                'retrieval': {'backend': 'lexical-and', 'completeness': 'unknown'},
                'runtime': {'wheel_sha256': 'b' * 64},
                'files': {path: {'sha256': _sha(data), 'bytes': len(data)}
                          for path, data in files.items()}}
    manifest['manifest_sha256'] = _sha(_encode(manifest))
    files['manifest.json'] = _encode(manifest)
    for relative, data in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root


@pytest.mark.parametrize('transport', ['stdio', 'streamable-http'])
def test_official_client_negotiates_and_calls_exact_registry(sdk_python, consumer_snapshot,
                                                            tmp_path, transport):
    adapter = tmp_path / 'adapter'
    adapter.mkdir()
    for filename in ('serve_consumer_mcp.py', 'consumer_tools.py', 'pure_query.py',
                     'capability_query.py'):
        shutil.copyfile(ROOT / 'scripts' / filename, adapter / filename)
    config = {'scripts': str(adapter), 'root': str(consumer_snapshot),
              'transport': transport, 'registry': tools()}
    completed = subprocess.run([sdk_python, '-c', CLIENT_PROBE], input=json.dumps(config),
                               text=True, capture_output=True, timeout=40, cwd=tmp_path)
    assert completed.returncode == 0, completed.stderr
    evidence = json.loads(completed.stdout)
    assert evidence['sdk_version'] == '2.3.0'
    assert evidence['protocol_version'] in evidence['supported_versions']
    assert len(evidence['tools']) == 5
    assert not list(adapter.rglob('__pycache__'))
    # Save actual negotiated evidence alongside this project test's fixture.
    (tmp_path / ('mcp-' + transport + '-evidence.json')).write_text(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
