"""Build and query a version-bound development documentation snapshot.

This development tool does not import or execute scientific callables. It is not
an executable catalog release or a scientific wheel qualification.
"""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib
from urllib.parse import parse_qs, urlsplit

from validate_asset_documents import load_document_set
from build_scirel_sphinx import load_translations, render_site

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scirel.documentation-snapshot.v1'
NOTICE = ('开发文档 · 按每条资产的版本与证据范围使用。文档收录不代表人工批准、'
          '全项目通过或公开发行；此快照不是单一 wheel 的安装清单。')
STATIC_FILES = {
    'presentation.js': 'text/javascript; charset=utf-8',
    'code.css': 'text/css; charset=utf-8',
    'guide.css': 'text/css; charset=utf-8',
    'navigation.js': 'text/javascript; charset=utf-8',
    'handbook.js': 'text/javascript; charset=utf-8',
    'vendor/highlightjs/highlight.min.js': 'text/javascript; charset=utf-8',
    'vendor/highlightjs/LICENSE': 'text/plain; charset=utf-8',
    'vendor/highlightjs/provenance.json': 'application/json; charset=utf-8',
}


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def project_version(root=ROOT):
    try:
        metadata = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))
        version = metadata['project']['version']
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ValueError('pyproject.toml has no readable project.version') from error
    if not isinstance(version, str) or not version:
        raise ValueError('pyproject.toml project.version must be a non-empty string')
    return version


def handbook_document(asset_ids, outline=None):
    """Return the canonical navigation projected onto one exact document set.

    ``tools/docs/handbook.json`` is the only handbook source kept in the
    checkout.  A release or development snapshot may contain a strict subset
    of its assets (for example, when a platform-specific family is not in the
    selected wheel); the builder filters that subset in memory instead of
    requiring another versioned handbook file.  An explicitly supplied
    outline remains strict so tests and specialized callers can validate an
    exact, independently authored navigation document.
    """
    requested = set(asset_ids)
    source = outline or ROOT / 'tools/docs/handbook.json'
    book = json.loads(Path(source).read_bytes())
    if book.get('schema') != 'scirel.handbook.v1':
        raise ValueError('invalid handbook schema')
    seen, placements = set(), []
    canonical_assets = {
        asset
        for chapter in book['chapters']
        for topic in chapter['topics']
        for asset in topic['assets']
    }
    # The canonical handbook may contain a superset of one release's selected
    # documents, so validate its members against the repository catalog before
    # projecting a release subset.  Isolated callers/tests may provide only an
    # outline, in which case the requested set is the available contract.
    if outline is None:
        catalog = ROOT / 'catalog/examples'
        if catalog.is_dir():
            available_assets = {path.stem for path in catalog.glob('*.json')}
        else:
            available_assets = requested
        unknown_canonical = canonical_assets - available_assets
        if unknown_canonical:
            raise ValueError('handbook contains unknown assets: ' +
                             str(sorted(unknown_canonical)))
    unknown_requested = requested - canonical_assets
    if unknown_requested:
        raise ValueError('documents are outside canonical handbook: ' +
                         str(sorted(unknown_requested)))
    projected_chapters = []
    for chapter in book['chapters']:
        for node in [chapter, *chapter['topics']]:
            if not re.fullmatch(r'[a-z][a-z0-9-]*', node['id']) or node['id'] in seen:
                raise ValueError('invalid or duplicate handbook ID')
            seen.add(node['id'])
            if not node['title'].strip() or not node['introduction'].strip():
                raise ValueError('handbook nodes need a title and introduction')
        if not chapter['discipline'] or not chapter['topics']:
            raise ValueError('empty handbook chapter')
        projected_topics = []
        for topic in chapter['topics']:
            if not topic['assets']:
                raise ValueError('empty handbook topic')
            if topic.get('tutorial_id') not in (None, 'magnetostatics', 'kinetic-initial-value'):
                raise ValueError('handbook tutorial has no execution-backed renderer')
            topic_assets = list(topic['assets'])
            if outline is None:
                topic_assets = [asset for asset in topic_assets if asset in requested]
            if not topic_assets:
                continue
            projected = dict(topic)
            projected['assets'] = topic_assets
            # A tutorial is only valid when its complete topic remains in the
            # selected closure; otherwise it would advertise an incomplete
            # executable chapter.
            if outline is None and topic_assets != list(topic['assets']):
                projected.pop('tutorial_id', None)
            projected_topics.append(projected)
            placements.extend(topic_assets)
        if projected_topics:
            projected_chapter = dict(chapter)
            projected_chapter['topics'] = projected_topics
            projected_chapters.append(projected_chapter)
    if len(placements) != len(set(placements)):
        raise ValueError('duplicate handbook asset placement')
    if set(placements) != requested:
        raise ValueError('handbook coverage differs from exact documents: missing=' +
                         str(sorted(requested - set(placements))) + '; unknown=' +
                         str(sorted(set(placements) - requested)))
    book['chapters'] = projected_chapters
    return book


def chapter_directory():
    """Select one explicitly bound successor without rewriting old evidence."""
    selection_path = ROOT / 'tools/docs/chapter-selection.json'
    if not selection_path.exists():
        return ROOT / 'tools/docs/magnetostatics'
    selection = json.loads(selection_path.read_bytes())
    if set(selection) != {'schema', 'chapters'} or selection['schema'] != 'scirel.chapter-selection.v1':
        raise ValueError('invalid chapter selection schema')
    if set(selection['chapters']) != {'magnetostatics'}:
        raise ValueError('unsupported chapter selection IDs')
    item = selection['chapters']['magnetostatics']
    if set(item) != {'directory', 'execution_sha256'}:
        raise ValueError('invalid chapter selection binding')
    directory = item['directory']
    if not isinstance(directory, str) or not re.fullmatch(r'tools/docs/[a-z0-9][a-z0-9-]*', directory):
        raise ValueError('invalid chapter selection path')
    root = (ROOT / directory).resolve()
    if not root.is_relative_to((ROOT / 'tools/docs').resolve()) or not root.is_dir():
        raise ValueError('chapter selection path escapes documentation or is missing')
    digest = item['execution_sha256']
    if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('invalid chapter execution digest')
    if sha((root / 'execution.json').read_bytes()) != digest:
        raise ValueError('selected chapter execution bytes changed')
    return root


def chapter_files(asset_ids):
    """Bind executed examples to current implementation before publishing them."""
    root = chapter_directory()
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
    if chapter.get('id') != 'magnetostatics':
        raise ValueError('selected chapter ID differs from its route')
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


def build(documents: Path, output: Path, outline: Path | None = None,
          translation_paths: list[Path] | None = None,
          *, source_revision: str | None = None,
          source_dirty: bool | None = None):
    docs = load_document_set(documents)
    if output.exists():
        raise FileExistsError('output already exists; build a new snapshot')
    source = source_revision
    if source is None:
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if not isinstance(source, str) or not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('source_revision must be a full Git commit id')
    dirty = source_dirty
    if dirty is None:
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
    translations = load_translations(ROOT, documents, docs, translation_paths=translation_paths)
    book = handbook_document({d['asset_id'] for d in docs}, outline)
    files = {}
    index = []
    for doc in docs:
        asset = doc['asset_id']
        files[f'records/{asset}.json'] = (documents / (asset + '.json')).read_bytes()
        files[f'readers/{asset}.json'] = encode(translations[asset])
        summary = {k: doc[k] for k in ('asset_id', 'kind', 'title', 'summary', 'taxonomy', 'aliases', 'version')}
        summary['public_api'] = doc['public_api']
        summary['summary_zh'] = translations[asset]['summary']
        summary['evidence_ceiling'] = doc['verification']['evidence_ceiling']
        summary['known_limitations'] = doc['verification']['known_limitations']
        summary['license_status'] = doc['provenance']['license_status']
        # Lexical retrieval of existing scientific text, never generated semantics.
        summary['search_text'] = json.dumps([doc, translations[asset]], ensure_ascii=False).lower()
        index.append(summary)
    files['index.json'] = encode(index)
    files['index.html'] = (ROOT / 'tools/docs/index.html').read_bytes()
    files['handbook.html'] = (ROOT / 'tools/docs/handbook.html').read_bytes()
    files['handbook.json'] = encode(book)
    for path in STATIC_FILES:
        files['static/' + path] = (ROOT / 'tools/docs' / path).read_bytes()
    files.update(chapter_files({d['asset_id'] for d in docs}))
    chapter = json.loads(files['chapters/magnetostatics/chapter.json'])
    files.update(render_site(
        ROOT, docs, book, translations, chapter,
        figure_files={name: files['chapters/magnetostatics/' + name]
                      for name in ('single.svg', 'pair.svg', 'rectangle.svg')},
    ))
    manifest = {'schema': SCHEMA, 'source_commit': source, 'source_revision': source,
                'source_dirty': dirty,
                'project_version': project_version(),
                'asset_count': len(docs), 'notice': NOTICE,
                'reader_language': 'zh-CN', 'human_renderer': 'sphinx-pydata',
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
        source_commit = self.manifest.get('source_commit')
        source_revision = self.manifest.get('source_revision', source_commit)
        if not isinstance(source_commit, str) or not re.fullmatch(r'[0-9a-f]{40}', source_commit):
            raise ValueError('invalid documentation source_commit')
        if source_revision != source_commit:
            raise ValueError('documentation source_revision differs from source_commit')
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
                'source_commit': self.manifest['source_commit'],
                'source_revision': self.manifest.get('source_revision', self.manifest['source_commit']),
                'notice': NOTICE, **items}

    def search(self, q='', kind='', domain='', offset=0, limit=20, topic=''):
        if len(q) > 512 or offset < 0 or not 1 <= limit <= 100:
            raise ValueError('q <= 512 characters, offset >= 0, limit 1..100 required')
        if kind not in ('', 'operator', 'task_graph'):
            raise ValueError('kind must be operator or task_graph')
        # Read the bound index again so mutation after startup also fails closed.
        index = json.loads(self.read('index.json'))
        topic_ids = set(self.topic(topic)['document']['assets']) if topic else self.ids
        terms = q.lower().split()
        matches = [x for x in index if x['asset_id'] in topic_ids and (not kind or x['kind'] == kind)
                   and (not domain or domain in x['taxonomy'])
                   and all(t in x['search_text'] for t in terms)]
        page = [{k: v for k, v in x.items() if k != 'search_text'} for x in matches[offset:offset+limit]]
        return self.envelope(items=page, total=len(matches), offset=offset,
                             next_offset=offset+limit if offset+limit < len(matches) else None)

    def asset(self, asset_id):
        if asset_id not in self.ids:
            raise KeyError('unknown asset_id')
        return self.envelope(document=json.loads(self.read(f'records/{asset_id}.json')))

    def reader(self, asset_id):
        result = self.asset(asset_id)
        result['translation'] = json.loads(self.read(f'readers/{asset_id}.json'))
        if result['translation']['source_sha256'] != sha(self.read(f'records/{asset_id}.json')):
            raise ValueError('Chinese reader is not bound to the served exact document')
        return result

    def chapter(self, chapter_id):
        if chapter_id != 'magnetostatics':
            raise KeyError('unknown chapter')
        return self.envelope(document=json.loads(self.read('chapters/magnetostatics/chapter.json')))

    def handbook(self):
        return self.envelope(document=json.loads(self.read('handbook.json')))

    def topic(self, topic_id):
        for chapter in self.handbook()['document']['chapters']:
            for topic in chapter['topics']:
                if topic['id'] == topic_id:
                    return self.envelope(document=topic, chapter_id=chapter['id'],
                                         discipline=[*chapter['discipline'], chapter['title']])
        raise KeyError('unknown handbook topic')

    def handle(self, url):
        parsed = urlsplit(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        if any(len(v) != 1 for v in params.values()):
            raise ValueError('duplicate query parameter')
        p = {k: v[0] for k, v in params.items()}
        if parsed.path == '/api/search':
            if set(p) - {'q', 'kind', 'domain', 'offset', 'limit', 'topic'}:
                raise ValueError('unknown search parameter')
            for key in ('offset', 'limit'):
                if key in p:
                    p[key] = int(p[key])
            return self.search(**p)
        if parsed.path == '/api/asset' and set(p) == {'id'}:
            return self.asset(p['id'])
        if parsed.path == '/api/reader' and set(p) == {'id'}:
            return self.reader(p['id'])
        if parsed.path == '/api/chapter' and set(p) == {'id'}:
            return self.chapter(p['id'])
        if parsed.path == '/api/handbook' and not p:
            return self.handbook()
        if parsed.path == '/api/topic' and set(p) == {'id'}:
            return self.topic(p['id'])
        if parsed.path == '/api/chapters' and not p:
            c = self.chapter('magnetostatics')['document']
            return self.envelope(items=[{k: c[k] for k in ('id', 'title', 'discipline', 'introduction')}])
        if parsed.path == '/api' and not p:
            return self.envelope(endpoints={'search': '/api/search?q=&kind=&domain=&offset=0&limit=20',
                                            'asset': '/api/asset?id=scirel.…',
                                            'reader': '/api/reader?id=scirel.…',
                                            'manifest': '/api/manifest',
                                            'chapters': '/api/chapters',
                                            'chapter': '/api/chapter?id=magnetostatics'},
                                 handbook='/api/handbook', topic='/api/topic?id=…',
                                 topic_search='/api/search?topic=…&q=&offset=0&limit=20',
                                 operations='read-only; no callable execution',
                                 discovery='lexical AND search, lowercase, whitespace separated; exact domain/kind filters')
        if parsed.path == '/api/manifest' and not p:
            return self.manifest
        raise KeyError('unknown endpoint')


def server(docs, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                path = urlsplit(self.path).path
                page = {'/': 'index.html', '/reference': 'reference/index.html',
                        '/tutorials/magnetostatics': 'tutorials/magnetostatics.html'}.get(path, path.lstrip('/'))
                if 'web/' + page in docs.manifest['files']:
                    data = docs.read('web/' + page)
                    content_type = mimetypes.guess_type(page)[0] or 'application/octet-stream'
                    if content_type.startswith('text/'):
                        content_type += '; charset=utf-8'
                elif self.path in ('/', '/index.html'):
                    data, content_type = docs.read('handbook.html'), 'text/html; charset=utf-8'
                elif self.path == '/tutorials/magnetostatics':
                    data, content_type = docs.read('chapter.html'), 'text/html; charset=utf-8'
                elif urlsplit(self.path).path == '/reference':
                    data, content_type = docs.read('index.html'), 'text/html; charset=utf-8'
                elif self.path.startswith('/static/') and self.path[8:] in STATIC_FILES:
                    data, content_type = docs.read(self.path[1:]), STATIC_FILES[self.path[8:]]
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
    b = subs.add_parser('build'); b.add_argument('--documents', type=Path, default=ROOT/'catalog/examples'); b.add_argument('--output', type=Path, required=True); b.add_argument('--outline', type=Path); b.add_argument('--translations', type=Path, action='append', help='Explicit complete reader bundle(s) for the selected document set; repeatable'); b.add_argument('--source-revision', help='explicit full Git commit id for an archived source tree'); b.add_argument('--source-dirty', action='store_true', help='mark an explicitly bound source tree as dirty')
    for name in ('query', 'serve'):
        sub = subs.add_parser(name); sub.add_argument('--snapshot', type=Path, required=True); sub.add_argument('--expected-digest')
        if name == 'query':
            sub.add_argument('--q', default=''); sub.add_argument('--kind', default=''); sub.add_argument('--domain', default=''); sub.add_argument('--offset', type=int, default=0); sub.add_argument('--limit', type=int, default=20); sub.add_argument('--asset'); sub.add_argument('--reader'); sub.add_argument('--chapter'); sub.add_argument('--handbook', action='store_true'); sub.add_argument('--topic', default='')
        else:
            sub.add_argument('--port', type=int, default=8765)
    a = parser.parse_args()
    if a.command == 'build':
        bound_dirty = True if a.source_dirty else (False if a.source_revision else None)
        result = build(a.documents, a.output, a.outline, a.translations,
                       source_revision=a.source_revision,
                       source_dirty=bound_dirty)
        print(json.dumps({k:v for k,v in result.items() if k != 'files'}, ensure_ascii=False)); return
    docs = Documentation(a.snapshot, a.expected_digest)
    if a.command == 'query':
        result = docs.reader(a.reader) if a.reader else (docs.handbook() if a.handbook else (docs.chapter(a.chapter) if a.chapter else (docs.asset(a.asset) if a.asset else docs.search(a.q, a.kind, a.domain, a.offset, a.limit, a.topic))))
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
