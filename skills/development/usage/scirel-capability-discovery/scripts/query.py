"""Query the public SciRel runtime with Python's standard library.

Run ``describe`` first, then pass the returned snapshot and wheel hashes to
subsequent commands. CLI and MCP calls use the same read-only dispatcher.
CLI JSON is encoded as UTF-8 on stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys

sys.dont_write_bytecode = True

from capability_query import (FILTER_ORDER, REQUEST_SCHEMA, RESPONSE_SCHEMA,
                              query_capabilities, validate_capability_index)

RUNTIME_SCHEMA = 'scirel.consumer-runtime'
RESPONSE = 'scirel.consumer-response'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _is_link_or_reparse(path):
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return (stat.S_ISLNK(metadata.st_mode) or
            bool(getattr(metadata, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT))


class Consumer:
    def __init__(self, root):
        root = Path(root).absolute()
        if any(_is_link_or_reparse(path) for path in [root, *root.parents]):
            raise ValueError('runtime root may not use a link or reparse point')
        self.root = root.resolve()
        path = self.root / 'runtime.json'
        if _is_link_or_reparse(path):
            raise ValueError('runtime identity may not use a link or reparse point')
        self.identity = json.loads(path.read_bytes())
        if not isinstance(self.identity, dict):
            raise ValueError('runtime identity must be an object')
        if (not isinstance(self.identity.get('snapshot_sha256'), str) or
                not re.fullmatch(r'[0-9a-f]{64}', self.identity['snapshot_sha256']) or
                not isinstance(self.identity.get('source_revision'), str) or
                not re.fullmatch(r'[0-9a-f]{40}', self.identity['source_revision']) or
                type(self.identity.get('asset_count')) is not int or self.identity['asset_count'] < 0 or
                not isinstance(self.identity.get('runtime'), dict) or
                not isinstance(self.identity['runtime'].get('wheel_sha256'), str) or
                not re.fullmatch(r'[0-9a-f]{64}', self.identity['runtime']['wheel_sha256']) or
                not isinstance(self.identity.get('retrieval'), dict) or
                not isinstance(self.identity.get('files'), dict)):
            raise ValueError('invalid runtime identity/runtime/files fields')
        for relative, member in self.identity['files'].items():
            if (not isinstance(relative, str) or not isinstance(member, dict) or
                    not isinstance(member.get('sha256'), str) or
                    not re.fullmatch(r'[0-9a-f]{64}', member['sha256']) or
                    type(member.get('bytes')) is not int or member['bytes'] < 0):
                raise ValueError('invalid runtime member metadata')
        unsigned = {k: v for k, v in self.identity.items() if k != 'snapshot_sha256'}
        if (self.identity.get('schema') != RUNTIME_SCHEMA or
                sha(encode(unsigned)) != self.identity['snapshot_sha256']):
            raise ValueError('invalid runtime identity')
        self.index = json.loads(self.read('catalog/capability-index.json'))
        validate_capability_index(self.index,
                                 expected_source_revision=self.identity['source_revision'])
        if self.index['asset_count'] != self.identity['asset_count']:
            raise ValueError('runtime/index count differs')
        self.assets = {x['asset_id']: x for x in self.index['assets']}

    def read(self, relative):
        if (not isinstance(relative, str) or '\\' in relative or ':' in relative or
                PurePosixPath(relative).as_posix() != relative or
                any(p in {'.', '..'} for p in relative.split('/'))):
            raise ValueError('invalid member path')
        path = self.root / relative
        if (any(_is_link_or_reparse(p) for p in [path, *path.parents]) or
                not path.resolve().is_relative_to(self.root)):
            raise ValueError('member path escapes root or uses a link or reparse point')
        expected = self.identity['files'].get(relative)
        if not expected:
            raise ValueError('member is not runtime-bound: ' + relative)
        data = path.read_bytes()
        if len(data) != expected['bytes'] or sha(data) != expected['sha256']:
            raise ValueError('member bytes changed: ' + relative)
        return data

    def envelope(self, command, **values):
        return dict(schema=RESPONSE, command=command,
                    snapshot_sha256=self.identity['snapshot_sha256'],
                    wheel_sha256=self.identity['runtime']['wheel_sha256'],
                    source_revision=self.identity['source_revision'], **values)

    def describe(self):
        return self.envelope('describe', outcome='ok', asset_count=len(self.assets),
                             commands=['describe', 'browse', 'search', 'get'],
                             filters=list(FILTER_ORDER), default_limit=5, maximum_limit=100,
                             retrieval=self.identity['retrieval'],
                             runtime=self.identity['runtime'],
                             human_documentation={'status': 'unconfigured',
                                                  'locator': 'asset_id'},
                             schemas={'request': REQUEST_SCHEMA, 'response': RESPONSE_SCHEMA})

    def query(self, command, **filters):
        result = query_capabilities(self.index, {'schema': 'scirel.capability-query', **filters},
                                    ranked=command == 'search')
        outcome = 'no_candidates' if result['status'] == 'gap' else result['status']
        return self.envelope(command, outcome=outcome, result=result,
                             retrieval=self.identity['retrieval'])

    def get(self, asset):
        if asset not in self.assets:
            return self.envelope('get', outcome='unknown_asset', asset_id=asset)
        contract = 'catalog/contracts/' + asset + '.json'
        document = json.loads(self.read(contract))
        if not isinstance(document, dict) or document.get('asset_id') != asset:
            raise ValueError('contract asset identity differs')
        return self.envelope('get', outcome='ok', asset_id=asset,
                             document=document, paths={'contract': contract},
                             digests={contract: self.identity['files'][contract]['sha256']})

    def verify(self):
        for relative in self.identity['files']:
            self.read(relative)
        actual = {p.relative_to(self.root).as_posix() for p in self.root.rglob('*')
                  if p.is_file()}
        if any(_is_link_or_reparse(p) for p in self.root.rglob('*')):
            raise ValueError('runtime contains a link or reparse point')
        if actual != set(self.identity['files']) | {'runtime.json'}:
            raise ValueError('runtime has missing or extra members')
        return self.envelope('verify', outcome='ok', files_verified=len(actual),
                             scientific_runtime_revalidated=False)


def main(argv=None):
    # The dispatcher imports Consumer from this module; importing it here keeps
    # the shared core independent of the CLI parser and optional MCP SDK.
    from consumer_tools import TOOL_PREFIX, call_tool, is_error_result, tools

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).absolute().parents[3])
    sub = parser.add_subparsers(dest='command', required=True)
    for tool in tools():
        command = tool['name'].removeprefix(TOOL_PREFIX)
        p = sub.add_parser(command, help=tool['description'])
        schema = tool['inputSchema']
        for field, definition in schema['properties'].items():
            options = {'default': argparse.SUPPRESS}
            if definition.get('type') == 'integer':
                options['type'] = int
            if 'enum' in definition:
                options['choices'] = definition['enum']
            if field == 'asset_id':
                p.add_argument(field, **options)
            else:
                p.add_argument('--' + field.replace('_', '-'), dest=field,
                               required=field in schema.get('required', []), **options)
    args = vars(parser.parse_args(argv))
    root, command = args.pop('root'), args.pop('command')
    result = call_tool(root, TOOL_PREFIX + command, args)
    # Pipe encoding is part of the JSON protocol, independent of the host
    # locale. In-memory text capture streams already accept Unicode strings.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 2 if is_error_result(result) else 0


if __name__ == '__main__':
    raise SystemExit(main())

