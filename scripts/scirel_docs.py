"""Build and query a version-bound development documentation snapshot.

This development tool does not import or execute scientific callables. It is not
an executable catalog release or a scientific wheel qualification.
"""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import parse_qs, urlsplit

from validate_asset_documents import load_document_set

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scirel.documentation-snapshot.v1'
NOTICE = ('开发文档 · 按每条资产的版本与证据范围使用。文档收录不代表人工批准、'
          '全项目通过或公开发行；此快照不是单一 wheel 的安装清单。')


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def chapter_files(asset_ids):
    """Bind executed examples to current implementation before publishing them."""
    root = ROOT / 'tools/docs/magnetostatics'
    execution = json.loads((root/'execution.json').read_bytes())
    for path, digest in execution['files'].items():
        if sha((ROOT/path).read_bytes()) != digest:
            raise ValueError('chapter implementation changed; rerun examples: ' + path)
    for name in ('example', 'results'):
        suffix = '.py' if name == 'example' else '.json'
        if sha((root/(name+suffix)).read_bytes()) != execution[name+'_sha256']:
            raise ValueError('chapter execution binding changed: ' + name)
    for name, digest in execution['figure_files'].items():
        if sha((root/name).read_bytes()) != digest:
            raise ValueError('chapter figure binding changed: ' + name)
    for path, digest in execution['document_files'].items():
        if sha((ROOT/path).read_bytes()) != digest:
            raise ValueError('chapter contract changed; review examples: ' + path)
    chapter = json.loads((root/'chapter.json').read_bytes())
    if any(x['id'] not in asset_ids for x in chapter['assets']):
        raise ValueError('chapter references a missing exact document')
    results = json.loads((root/'results.json').read_bytes())
    if not results.get('all_checks_passed') or execution['exit_code'] != 0:
        raise ValueError('chapter examples have not passed')
    script = (root/'example.py').read_text()
    sections = {}
    for block in script.split('# %% ')[1:]:
        name, code = block.split('\n', 1)
        sections[name] = code.split('output = dict(')[0].strip()
    for section in chapter['sections']:
        section['code'] = sections[section.pop('code_section')]
    chapter.update(results=results, execution=execution)
    prefix = 'chapters/magnetostatics/'
    files = {prefix+'chapter.json': encode(chapter),
             'chapter.html': (ROOT/'tools/docs/chapter.html').read_bytes()}
    for name in ('example.py', 'results.json', 'single.svg', 'pair.svg', 'rectangle.svg'):
        files[prefix+name] = (root/name).read_bytes()
    return files


def build(documents: Path, output: Path):
    docs = load_document_set(documents)
    if output.exists():
        raise FileExistsError('output already exists; build a new snapshot')
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
    files = {}
    index = []
    for doc in docs:
        asset = doc['asset_id']
        files[f'records/{asset}.json'] = encode(doc)
        summary = {k: doc[k] for k in ('asset_id', 'kind', 'title', 'summary', 'taxonomy', 'aliases', 'version')}
        summary['public_api'] = doc['public_api']
        summary['evidence_ceiling'] = doc['verification']['evidence_ceiling']
        summary['known_limitations'] = doc['verification']['known_limitations']
        summary['license_status'] = doc['provenance']['license_status']
        # Lexical retrieval of existing scientific text, never generated semantics.
        summary['search_text'] = json.dumps(doc, ensure_ascii=False).lower()
        index.append(summary)
    files['index.json'] = encode(index)
    files['index.html'] = (ROOT / 'tools/docs/index.html').read_bytes()
    files['static/presentation.js'] = (ROOT / 'tools/docs/presentation.js').read_bytes()
    files.update(chapter_files({d['asset_id'] for d in docs}))
    manifest = {'schema': SCHEMA, 'source_commit': source, 'source_dirty': dirty,
                'asset_count': len(docs), 'notice': NOTICE,
                'validation': {'schema_and_dependency_closure': True,
                               'scientific_runtime_revalidated': False},
                'files': {p: {'sha256': sha(b), 'bytes': len(b)} for p, b in sorted(files.items())}}
    manifest['snapshot_sha256'] = sha(encode(manifest))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / 'snapshot'
        stage.mkdir()
        for path, data in files.items():
            target = stage / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (stage / 'manifest.json').write_bytes(encode(manifest))
        stage.rename(output)
    return manifest


class Documentation:
    def __init__(self, root: Path, expected_digest=None):
        self.root = Path(root).resolve()
        self.manifest = json.loads((self.root / 'manifest.json').read_bytes())
        unsigned = {k: v for k, v in self.manifest.items() if k != 'snapshot_sha256'}
        digest = sha(encode(unsigned))
        if self.manifest.get('schema') != SCHEMA or digest != self.manifest.get('snapshot_sha256'):
            raise ValueError('invalid snapshot manifest')
        if expected_digest and expected_digest != digest:
            raise ValueError('snapshot differs from expected digest')
        for path in self.manifest['files']:
            self.read(path)
        self.index = json.loads(self.read('index.json'))
        self.ids = {x['asset_id'] for x in self.index}
        if len(self.ids) != len(self.index) or len(self.ids) != self.manifest['asset_count']:
            raise ValueError('invalid index count')

    def read(self, relative):
        if relative not in self.manifest['files']:
            raise KeyError('unknown document')
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError('snapshot path escapes root')
        data = target.read_bytes()
        expected = self.manifest['files'][relative]
        if len(data) != expected['bytes'] or sha(data) != expected['sha256']:
            raise ValueError('snapshot bytes changed; rebuild into a new directory')
        return data

    def envelope(self, **items):
        return {'schema': 'scirel.documentation-response.v1',
                'snapshot_sha256': self.manifest['snapshot_sha256'],
                'source_commit': self.manifest['source_commit'], 'notice': NOTICE, **items}

    def search(self, q='', kind='', domain='', offset=0, limit=20):
        if len(q) > 512 or offset < 0 or not 1 <= limit <= 100:
            raise ValueError('q <= 512 characters, offset >= 0, limit 1..100 required')
        if kind not in ('', 'operator', 'task_graph'):
            raise ValueError('kind must be operator or task_graph')
        # Read the bound index again so mutation after startup also fails closed.
        index = json.loads(self.read('index.json'))
        terms = q.lower().split()
        matches = [x for x in index if (not kind or x['kind'] == kind)
                   and (not domain or domain in x['taxonomy'])
                   and all(t in x['search_text'] for t in terms)]
        page = [{k: v for k, v in x.items() if k != 'search_text'} for x in matches[offset:offset+limit]]
        return self.envelope(items=page, total=len(matches), offset=offset,
                             next_offset=offset+limit if offset+limit < len(matches) else None)

    def asset(self, asset_id):
        if asset_id not in self.ids:
            raise KeyError('unknown asset_id')
        return self.envelope(document=json.loads(self.read(f'records/{asset_id}.json')))

    def chapter(self, chapter_id):
        if chapter_id != 'magnetostatics':
            raise KeyError('unknown chapter')
        return self.envelope(document=json.loads(self.read('chapters/magnetostatics/chapter.json')))

    def handle(self, url):
        parsed = urlsplit(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        if any(len(v) != 1 for v in params.values()):
            raise ValueError('duplicate query parameter')
        p = {k: v[0] for k, v in params.items()}
        if parsed.path == '/api/search':
            if set(p) - {'q', 'kind', 'domain', 'offset', 'limit'}:
                raise ValueError('unknown search parameter')
            for key in ('offset', 'limit'):
                if key in p:
                    p[key] = int(p[key])
            return self.search(**p)
        if parsed.path == '/api/asset' and set(p) == {'id'}:
            return self.asset(p['id'])
        if parsed.path == '/api/chapter' and set(p) == {'id'}:
            return self.chapter(p['id'])
        if parsed.path == '/api/chapters' and not p:
            c = self.chapter('magnetostatics')['document']
            return self.envelope(items=[{k: c[k] for k in ('id', 'title', 'discipline', 'introduction')}])
        if parsed.path == '/api' and not p:
            return self.envelope(endpoints={'search': '/api/search?q=&kind=&domain=&offset=0&limit=20',
                                            'asset': '/api/asset?id=scirel.…',
                                            'manifest': '/api/manifest',
                                            'chapters': '/api/chapters',
                                            'chapter': '/api/chapter?id=magnetostatics'},
                                 operations='read-only; no callable execution',
                                 discovery='lexical AND search, lowercase, whitespace separated; exact domain/kind filters')
        if parsed.path == '/api/manifest' and not p:
            return self.manifest
        raise KeyError('unknown endpoint')


def server(docs, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                if self.path in ('/', '/index.html'):
                    data, content_type = docs.read('chapter.html'), 'text/html; charset=utf-8'
                elif self.path == '/reference':
                    data, content_type = docs.read('index.html'), 'text/html; charset=utf-8'
                elif self.path == '/static/presentation.js':
                    data, content_type = docs.read('static/presentation.js'), 'text/javascript; charset=utf-8'
                elif self.path.startswith('/chapters/') and self.path[1:] in docs.manifest['files']:
                    suffix = Path(self.path).suffix
                    content_type = {'.svg': 'image/svg+xml', '.json': 'application/json; charset=utf-8', '.py': 'text/plain; charset=utf-8'}[suffix]
                    data = docs.read(self.path[1:])
                else:
                    data, content_type = encode(docs.handle(self.path)), 'application/json; charset=utf-8'
                status = 200
            except (KeyError, ValueError, OSError) as error:
                status = 404 if isinstance(error, KeyError) else 400
                data, content_type = encode({'error': str(error)}), 'application/json; charset=utf-8'
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    b = subs.add_parser('build'); b.add_argument('--documents', type=Path, default=ROOT/'catalog/examples'); b.add_argument('--output', type=Path, required=True)
    for name in ('query', 'serve'):
        sub = subs.add_parser(name); sub.add_argument('--snapshot', type=Path, required=True); sub.add_argument('--expected-digest')
        if name == 'query':
            sub.add_argument('--q', default=''); sub.add_argument('--kind', default=''); sub.add_argument('--domain', default=''); sub.add_argument('--offset', type=int, default=0); sub.add_argument('--limit', type=int, default=20); sub.add_argument('--asset'); sub.add_argument('--chapter')
        else:
            sub.add_argument('--port', type=int, default=8765)
    a = parser.parse_args()
    if a.command == 'build':
        result = build(a.documents, a.output)
        print(json.dumps({k:v for k,v in result.items() if k != 'files'}, ensure_ascii=False)); return
    docs = Documentation(a.snapshot, a.expected_digest)
    if a.command == 'query':
        result = docs.chapter(a.chapter) if a.chapter else (docs.asset(a.asset) if a.asset else docs.search(a.q, a.kind, a.domain, a.offset, a.limit))
        print(encode(result).decode()); return
    http = server(docs, a.port)
    print(f'SciRel documentation: http://127.0.0.1:{http.server_port}', flush=True)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()


if __name__ == '__main__':
    main()
