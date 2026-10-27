"""Standard-library CLI and official MCP Client transport checks.

Set SCIREL_MCP_PYTHON to an interpreter with tools/docs/mcp-requirements.txt. SDK
dependencies do not enter the scientific library or the project's test venv.
The fixture is explicitly synthetic and tests transport/consumer behavior only.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest
from fs_links import directory_link, file_link_or_reparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from consumer_tools import call_tool, tools  # noqa: E402
from query import Consumer  # noqa: E402
import serve_consumer_mcp as mcp_adapter  # noqa: E402

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
        assert len(exact) == 4
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
        contract = root / 'catalog/contracts/test.alpha.json'
        original_contract = contract.read_bytes()
        assert len(original_contract) > 65536
        assert document['document'] == json.loads(original_contract)
        assert document['paths'] == {'contract': 'catalog/contracts/test.alpha.json'}
        assert document['digests'] == {document['paths']['contract']: config['contract_sha256']}
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
    files = {'catalog/capability-index.json': _encode(index)}
    for record in records:
        asset = record['asset_id']
        files['catalog/contracts/' + asset + '.json'] = _encode({
            'asset_id': asset, 'notice': 'Synthetic fixture; no scientific validation.',
            'parameters': {'units': '1', 'nested': [0, None, True]},
            'original_text': '原始合同参数和适用范围' * 4000,
            'evidence': {'final': 'end-of-contract'},
        })
    identity = {'schema': 'scirel.consumer-runtime', 'source_revision': 'a' * 40,
                'asset_count': len(records),
                'retrieval': {'backend': 'lexical-and', 'completeness': 'unknown'},
                'runtime': {'wheel_sha256': 'b' * 64},
                'files': {path: {'sha256': _sha(data), 'bytes': len(data)}
                          for path, data in files.items()}}
    identity['snapshot_sha256'] = _sha(_encode(identity))
    files['runtime.json'] = _encode(identity)
    for relative, data in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root


@pytest.fixture
def registered_mcp_adapter(monkeypatch):
    """Exercise callback registration without claiming an official SDK run."""
    class Model(SimpleNamespace):
        @classmethod
        def model_validate(cls, value):
            return cls(**value)

    class Server:
        def __init__(self, name, *, instructions, on_list_tools, on_call_tool):
            self.name = name
            self.instructions = instructions
            self.on_list_tools = on_list_tools
            self.on_call_tool = on_call_tool

    async def run_sync(function, *args):
        return function(*args)

    anyio = ModuleType('anyio')
    anyio.to_thread = SimpleNamespace(run_sync=run_sync)
    mcp = ModuleType('mcp')
    server_module = ModuleType('mcp.server')
    server_module.Server = Server
    types_module = ModuleType('mcp.types')
    for name in ('CallToolResult', 'ListToolsResult', 'TextContent', 'Tool'):
        setattr(types_module, name, Model)
    for name, module in (('anyio', anyio), ('mcp', mcp),
                         ('mcp.server', server_module), ('mcp.types', types_module)):
        monkeypatch.setitem(sys.modules, name, module)
    return mcp_adapter


@pytest.mark.parametrize('linked_component', ['none', 'root', 'parent'])
def test_mcp_registered_callback_preserves_runtime_path_validation(
        registered_mcp_adapter, consumer_snapshot, tmp_path, linked_component):
    root = consumer_snapshot
    if linked_component != 'none':
        target = consumer_snapshot if linked_component == 'root' else consumer_snapshot.parent
        link = directory_link(tmp_path / 'linked-runtime', target)
        root = link if linked_component == 'root' else link / consumer_snapshot.name

    server = registered_mcp_adapter.create_server(root)
    advertised = asyncio.run(server.on_list_tools(None, None))
    assert [vars(tool) for tool in advertised.tools] == tools()
    response = asyncio.run(server.on_call_tool(
        None, SimpleNamespace(name='scirel_describe', arguments={})))

    assert response.structured_content == call_tool(root, 'scirel_describe')
    assert json.loads(response.content[0].text) == response.structured_content
    assert response.is_error is (linked_component != 'none')
    assert response.structured_content['outcome'] == (
        'ok' if linked_component == 'none' else 'metadata_error')
    if linked_component != 'none':
        assert ('link' in response.structured_content['error'] or
                'reparse' in response.structured_content['error'])


@pytest.mark.parametrize('transport', ['stdio', 'streamable-http'])
def test_official_client_negotiates_and_calls_exact_registry(sdk_python, consumer_snapshot,
                                                            tmp_path, transport):
    adapter = tmp_path / 'adapter'
    adapter.mkdir()
    for filename in ('serve_consumer_mcp.py', 'consumer_tools.py', 'query.py',
                     'capability_query.py'):
        shutil.copyfile(ROOT / 'scripts' / filename, adapter / filename)
    config = {'scripts': str(adapter), 'root': str(consumer_snapshot),
              'transport': transport, 'registry': tools(),
              'contract_sha256': _sha((consumer_snapshot / 'catalog/contracts/test.alpha.json').read_bytes())}
    completed = subprocess.run([sdk_python, '-c', CLIENT_PROBE], input=json.dumps(config),
                               text=True, capture_output=True, timeout=40, cwd=tmp_path)
    assert completed.returncode == 0, completed.stderr
    evidence = json.loads(completed.stdout)
    assert evidence['sdk_version'] == '2.3.0'
    assert evidence['protocol_version'] in evidence['supported_versions']
    assert len(evidence['tools']) == 4
    assert not list(adapter.rglob('__pycache__'))
    # Save actual negotiated evidence alongside this project test's fixture.
    (tmp_path / ('mcp-' + transport + '-evidence.json')).write_text(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


# -I -S gives this process only the standard library. The import guard also
# fails immediately if a future CLI change attempts an optional SDK or science
# import, even on hosts where those packages are otherwise installed.
CLI_DRIVER = r'''
import runpy
import sys
from pathlib import Path

class NoOptionalDependencies:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'mcp', 'mcp_types', 'numpy', 'scipy', 'scirel', 'sphinx'}:
            raise AssertionError('CLI attempted optional import: ' + fullname)

sys.meta_path.insert(0, NoOptionalDependencies())
sys.dont_write_bytecode = True
# Simulate a non-UTF-8 Windows pipe on every host. The CLI owns its wire encoding.
sys.stdout.reconfigure(encoding='cp1252')
entry = Path(sys.argv.pop(1)).absolute()
sys.path.insert(0, str(entry.parent))
sys.argv[0] = str(entry)
runpy.run_path(str(entry), run_name='__main__')
'''


def _cli(root, *arguments, entry=None, explicit_root=True):
    args = [sys.executable, '-I', '-S', '-c', CLI_DRIVER,
            str(entry or ROOT / 'scripts/query.py')]
    if explicit_root:
        args += ['--root', str(root)]
    completed = subprocess.run([*args, *arguments], capture_output=True,
                               timeout=15, cwd=root)
    # Read actual wire bytes and decode the JSON protocol independently of
    # both the parent process locale and the child's initial stdout encoding.
    return subprocess.CompletedProcess(completed.args, completed.returncode,
                                       completed.stdout.decode('utf-8'),
                                       completed.stderr.decode('utf-8'))


def _cli_pins(root):
    description = call_tool(root, 'scirel_describe')
    pins = {key: description[value] for key, value in (
        ('expected_snapshot_sha256', 'snapshot_sha256'),
        ('expected_wheel_sha256', 'wheel_sha256'))}
    flags = [part for key, value in pins.items()
             for part in ('--' + key.replace('_', '-'), value)]
    return pins, flags


@pytest.mark.parametrize('command,arguments,flags', [
    ('describe', {}, []),
    ('browse', {'limit': 1}, ['--limit', '1']),
    ('search', {'q': 'periodic flux', 'limit': 1},
     ['--q', 'periodic flux', '--limit', '1']),
    ('get', {'asset_id': 'test.alpha'}, ['test.alpha']),
])
def test_cli_without_sdk_uses_the_same_dispatch(consumer_snapshot, command, arguments, flags):
    pins, pin_flags = _cli_pins(consumer_snapshot) if command != 'describe' else ({}, [])
    completed = _cli(consumer_snapshot, command, *flags, *pin_flags)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == call_tool(
        consumer_snapshot, 'scirel_' + command, {**pins, **arguments})


def test_cli_without_sdk_returns_the_complete_large_original_contract(consumer_snapshot):
    _, flags = _cli_pins(consumer_snapshot)
    original = (consumer_snapshot / 'catalog/contracts/test.alpha.json').read_bytes()
    assert len(original) > 65536
    completed = _cli(consumer_snapshot, 'get', 'test.alpha', *flags)
    assert completed.returncode == 0, completed.stderr
    response = json.loads(completed.stdout)
    assert response['document'] == json.loads(original)
    assert len(completed.stdout.encode()) > 65536
    assert response['digests'] == {'catalog/contracts/test.alpha.json': _sha(original)}


def test_cli_without_sdk_can_continue_a_cursor(consumer_snapshot):
    _, flags = _cli_pins(consumer_snapshot)
    first = _cli(consumer_snapshot, 'browse', *flags, '--limit', '1')
    assert first.returncode == 0, first.stderr
    page = json.loads(first.stdout)
    second = _cli(consumer_snapshot, 'browse', *flags, '--limit', '1',
                  '--cursor', page['next_cursor'])
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)['result']['items'][0]['asset_id'] == 'test.beta'


def test_cli_utf8_wire_preserves_the_dispatcher_byte_budget(consumer_snapshot):
    pins, flags = _cli_pins(consumer_snapshot)
    completed = _cli(consumer_snapshot, 'browse', *flags, '--max-bytes', '4096')
    assert completed.returncode == 0, completed.stderr
    response = json.loads(completed.stdout)
    assert response == call_tool(consumer_snapshot, 'scirel_browse', {**pins, 'max_bytes': 4096})
    assert '周期通量' in completed.stdout
    assert len(completed.stdout.encode('utf-8')) <= 4096


@pytest.mark.parametrize('command,arguments,outcome', [
    ('search', ['--limit', '0'], 'invalid_request'),
    ('search', ['--expected-snapshot-sha256', '0' * 64], 'identity_mismatch'),
    ('search', ['--expected-wheel-sha256', '0' * 64], 'identity_mismatch'),
    ('browse', ['--cursor', 'invalid cursor'], 'invalid_request'),
    ('get', ['test.absent'], 'unknown_asset'),
])
def test_cli_without_sdk_returns_failure_exit_for_error_envelopes(
        consumer_snapshot, command, arguments, outcome):
    _, flags = _cli_pins(consumer_snapshot)
    completed = _cli(consumer_snapshot, command, *flags, *arguments)
    assert completed.returncode == 2, completed.stderr
    assert json.loads(completed.stdout)['outcome'] == outcome


def test_cli_requires_explicit_pins_after_discovery(consumer_snapshot):
    completed = _cli(consumer_snapshot, 'search', '--q', 'periodic')
    assert completed.returncode == 2
    assert '--expected-snapshot-sha256' in completed.stderr
    assert '--expected-wheel-sha256' in completed.stderr


@pytest.mark.parametrize('member', ['runtime.json', 'catalog/capability-index.json',
                                    'catalog/contracts/test.alpha.json'])
def test_cli_without_sdk_fails_closed_on_corrupt_runtime(consumer_snapshot, member):
    _, flags = _cli_pins(consumer_snapshot)
    (consumer_snapshot / member).write_bytes(b'{}')
    completed = _cli(consumer_snapshot, 'get', 'test.alpha', *flags)
    assert completed.returncode == 2, completed.stderr
    assert json.loads(completed.stdout)['outcome'] == 'metadata_error'


def test_exported_cli_resolves_its_runtime_root_without_sdk(consumer_snapshot):
    adapter = consumer_snapshot / 'tools'
    adapter.mkdir()
    for filename in ('query.py', 'consumer_tools.py', 'capability_query.py'):
        shutil.copyfile(ROOT / 'scripts' / filename, adapter / filename)
    completed = _cli(consumer_snapshot, 'describe', entry=adapter / 'query.py', explicit_root=False)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == call_tool(consumer_snapshot, 'scirel_describe')
    assert not list(adapter.rglob('__pycache__'))


def test_exported_cli_rejects_a_linked_default_runtime_root(consumer_snapshot, tmp_path):
    adapter = consumer_snapshot / 'tools'
    adapter.mkdir()
    for filename in ('query.py', 'consumer_tools.py', 'capability_query.py'):
        shutil.copyfile(ROOT / 'scripts' / filename, adapter / filename)
    linked_root = directory_link(tmp_path / 'linked-runtime', consumer_snapshot)

    completed = _cli(consumer_snapshot, 'describe', entry=linked_root / 'tools' / 'query.py',
                     explicit_root=False)

    assert completed.returncode == 2, completed.stderr
    response = json.loads(completed.stdout)
    assert response['outcome'] == 'metadata_error'
    assert 'link' in response['error'] or 'reparse' in response['error']


@pytest.mark.parametrize('linked_component', ['root', 'parent'])
def test_consumer_rejects_linked_runtime_roots_before_resolution(
        consumer_snapshot, tmp_path, linked_component):
    link = tmp_path / 'linked-runtime'
    if linked_component == 'root':
        directory_link(link, consumer_snapshot)
        root = link
    else:
        directory_link(link, consumer_snapshot.parent)
        root = link / consumer_snapshot.name
    with pytest.raises(ValueError, match='link|reparse'):
        Consumer(root)


def test_consumer_rejects_a_linked_catalog_directory(consumer_snapshot, tmp_path):
    catalog = consumer_snapshot / 'catalog'
    outside = tmp_path / 'catalog-data'
    catalog.rename(outside)
    directory_link(catalog, outside)
    with pytest.raises(ValueError, match='link|reparse'):
        Consumer(consumer_snapshot)


@pytest.mark.parametrize('relative', ['runtime.json', 'catalog/contracts/test.alpha.json'])
def test_consumer_rejects_file_links_or_reparse_points_before_reading(
        consumer_snapshot, tmp_path, relative):
    member = consumer_snapshot / relative
    outside = tmp_path / 'original-member.json'
    member.rename(outside)
    file_link_or_reparse(member, outside)
    with pytest.raises(ValueError, match='link|reparse'):
        consumer = Consumer(consumer_snapshot)
        consumer.get('test.alpha')


def test_consumer_verify_rejects_an_unbound_empty_directory_link(consumer_snapshot, tmp_path):
    outside = tmp_path / 'empty-directory'
    outside.mkdir()
    directory_link(consumer_snapshot / 'extra', outside)
    with pytest.raises(ValueError, match='link|reparse'):
        Consumer(consumer_snapshot).verify()
