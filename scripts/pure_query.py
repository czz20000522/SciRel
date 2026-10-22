"""Standard-library consumer adapter; distributed as tools/query.py."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

from capability_query import (FILTER_ORDER, REQUEST_SCHEMA, RESPONSE_SCHEMA,
                              query_capabilities, validate_capability_index)

MANIFEST_SCHEMA = 'scirel.pure-consumption'
RESPONSE = 'scirel.consumer-response'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Consumer:
    def __init__(self, root):
        self.root = Path(root).resolve()
        path = self.root / 'manifest.json'
        if path.is_symlink():
            raise ValueError('manifest may not be a symlink')
        self.manifest = json.loads(path.read_bytes())
        if not isinstance(self.manifest, dict):
            raise ValueError('manifest must be an object')
        if (any(not isinstance(self.manifest.get(key), str) or
                not re.fullmatch(r'[0-9a-f]{64}', self.manifest[key])
                for key in ('manifest_sha256', 'snapshot_id')) or
                not isinstance(self.manifest.get('source_revision'), str) or
                not re.fullmatch(r'[0-9a-f]{40}', self.manifest['source_revision']) or
                type(self.manifest.get('asset_count')) is not int or self.manifest['asset_count'] < 0 or
                not isinstance(self.manifest.get('runtime'), dict) or
                not isinstance(self.manifest['runtime'].get('wheel_sha256'), str) or
                not re.fullmatch(r'[0-9a-f]{64}', self.manifest['runtime']['wheel_sha256']) or
                not isinstance(self.manifest.get('retrieval'), dict) or
                not isinstance(self.manifest.get('files'), dict)):
            raise ValueError('invalid manifest identity/runtime/files fields')
        for relative, member in self.manifest['files'].items():
            if (not isinstance(relative, str) or not isinstance(member, dict) or
                    not isinstance(member.get('sha256'), str) or
                    not re.fullmatch(r'[0-9a-f]{64}', member['sha256']) or
                    type(member.get('bytes')) is not int or member['bytes'] < 0):
                raise ValueError('invalid manifest member metadata')
        unsigned = {k: v for k, v in self.manifest.items() if k != 'manifest_sha256'}
        if (self.manifest.get('schema') != MANIFEST_SCHEMA or
                sha(encode(unsigned)) != self.manifest.get('manifest_sha256')):
            raise ValueError('invalid manifest identity')
        self.index = json.loads(self.read('catalog/capability-index.json'))
        validate_capability_index(self.index,
                                 expected_source_revision=self.manifest['source_revision'])
        if self.index['asset_count'] != self.manifest['asset_count']:
            raise ValueError('manifest/index count differs')
        self.assets = {x['asset_id']: x for x in self.index['assets']}

    def read(self, relative):
        if (not isinstance(relative, str) or '\\' in relative or ':' in relative or
                PurePosixPath(relative).as_posix() != relative or
                any(p in {'.', '..'} for p in relative.split('/'))):
            raise ValueError('invalid member path')
        path = self.root / relative
        if (not path.resolve().is_relative_to(self.root) or
                any(p.is_symlink() for p in [path, *path.parents] if p != self.root.parent)):
            raise ValueError('member path escapes root or uses a symlink')
        expected = self.manifest['files'].get(relative)
        if not expected:
            raise ValueError('member is not manifest-bound: ' + relative)
        data = path.read_bytes()
        if len(data) != expected['bytes'] or sha(data) != expected['sha256']:
            raise ValueError('member bytes changed: ' + relative)
        return data

    def envelope(self, command, **values):
        return dict(schema=RESPONSE, command=command,
                    snapshot_id=self.manifest['snapshot_id'],
                    manifest_sha256=self.manifest['manifest_sha256'],
                    snapshot_sha256=self.manifest['manifest_sha256'],
                    wheel_sha256=self.manifest['runtime']['wheel_sha256'],
                    source_revision=self.manifest['source_revision'], **values)

    def describe(self):
        tutorials = json.loads(self.read('catalog/tutorial-index.json'))
        return self.envelope('describe', outcome='ok', asset_count=len(self.assets),
                             commands=['describe', 'browse', 'search', 'get', 'get_tutorial'],
                             filters=list(FILTER_ORDER), default_limit=5, maximum_limit=100,
                             retrieval=self.manifest['retrieval'],
                             runtime=self.manifest['runtime'],
                             collections=['capabilities', 'tutorials'],
                             tutorial_count=len(tutorials['chapters']),
                             schemas={'request': REQUEST_SCHEMA, 'response': RESPONSE_SCHEMA})

    def query(self, command, **filters):
        result = query_capabilities(self.index, {'schema': 'scirel.capability-query', **filters},
                                    ranked=command == 'search')
        outcome = 'no_candidates' if result['status'] == 'gap' else result['status']
        return self.envelope(command, outcome=outcome, result=result,
                             retrieval=self.manifest['retrieval'])

    def get(self, asset, language='en'):
        if asset not in self.assets:
            return self.envelope('get', outcome='unknown_asset', asset_id=asset)
        contract = 'catalog/contracts/' + asset + '.json'
        markdown = 'docs/' + language + '/api/' + asset + '.md'
        document = json.loads(self.read(contract))
        if not isinstance(document, dict) or document.get('asset_id') != asset:
            raise ValueError('contract asset identity differs')
        return self.envelope('get', outcome='ok', asset_id=asset,
                             document=document, markdown=self.read(markdown).decode(),
                             paths={'contract': contract, 'markdown': markdown},
                             digests={p: self.manifest['files'][p]['sha256']
                                      for p in [contract, markdown]})

    def verify(self):
        for relative in self.manifest['files']:
            self.read(relative)
        actual = {p.relative_to(self.root).as_posix() for p in self.root.rglob('*')
                  if p.is_file()}
        if any(p.is_symlink() for p in self.root.rglob('*')):
            raise ValueError('delivery contains symlinks')
        if actual != set(self.manifest['files']) | {'manifest.json'}:
            raise ValueError('delivery has missing or extra members')
        return self.envelope('verify', outcome='ok', files_verified=len(actual),
                             scientific_runtime_revalidated=False)

    def tutorial(self, chapter_id, language='en', offset=0, limit_chars=12000):
        if (type(offset) is not int or offset < 0 or type(limit_chars) is not int or
                not 1 <= limit_chars <= 20000):
            raise ValueError('offset >= 0 and limit_chars 1..20000 required')
        tutorials = json.loads(self.read('catalog/tutorial-index.json'))
        found = next((item for item in tutorials['chapters']
                      if item['chapter_id'] == chapter_id), None)
        if found is None:
            return self.envelope('get_tutorial', outcome='unknown_tutorial', chapter_id=chapter_id,
                                 available=[x['chapter_id'] for x in tutorials['chapters']])
        path = found['paths'][language]
        text = self.read(path).decode()
        end = min(len(text), offset + limit_chars)
        return self.envelope('get_tutorial', outcome='ok', chapter_id=chapter_id,
                             language=language, markdown=text[offset:end], total_chars=len(text),
                             offset=offset, next_offset=end if end < len(text) else None,
                             path=path, sha256=self.manifest['files'][path]['sha256'])

    def browse_tutorials(self, offset=0, limit=5):
        index = json.loads(self.read('catalog/tutorial-index.json'))
        cards = sorted(index['chapters'], key=lambda item: item['chapter_id'])
        selected = cards[offset:offset + limit]
        return self.envelope('browse', outcome='match', collection='tutorials', result={
            'schema': 'scirel.tutorial-browse-response', 'items': selected, 'total': len(cards),
            'offset': offset, 'next_offset': offset + limit if offset + limit < len(cards) else None})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('describe', 'verify'):
        sub.add_parser(name)
    for name in ('browse', 'search'):
        p = sub.add_parser(name)
        if name == 'search':
            p.add_argument('--q', default='')
        for field in FILTER_ORDER:
            if field != 'q':
                p.add_argument('--' + field.replace('_', '-'), default='')
        p.add_argument('--offset', type=int, default=0)
        p.add_argument('--limit', type=int, default=5)
    p = sub.add_parser('get'); p.add_argument('asset_id')
    p.add_argument('--language', choices=('en', 'zh'), default='en')
    args = vars(parser.parse_args(argv))
    root, command = args.pop('root'), args.pop('command')
    try:
        consumer = Consumer(root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'schema': RESPONSE, 'command': command,
                          'outcome': 'metadata_error', 'error': str(error)}))
        return 2
    try:
        if command in ('search', 'browse'):
            # Validate request separately so corrupt metadata is never called no_hit.
            try:
                result = consumer.query(command, **args)
            except ValueError as error:
                print(json.dumps(consumer.envelope(command, outcome='invalid_request', error=str(error))))
                return 2
        elif command == 'get':
            result = consumer.get(args['asset_id'], args['language'])
        else:
            result = getattr(consumer, command)()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps(consumer.envelope(command, outcome='metadata_error', error=str(error))))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
