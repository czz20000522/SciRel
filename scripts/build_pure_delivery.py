"""Export one public snapshot for private MCP/Python integration; never deploy."""
from __future__ import annotations

import argparse
import ast
import importlib
from html.parser import HTMLParser
from html import escape
import json
import posixpath
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import tempfile
from urllib.parse import parse_qs, urlsplit
from urllib.parse import unquote
import zipfile

from check_wheel_exposure import inspect_wheel
from query import encode, sha
from solving_skill import html_links, load_solving_skill, markdown_links
from scirel_docs import Documentation, build_capability_index, documentation_input_digests

ROOT = Path(__file__).resolve().parents[1]


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return ''.join(x if isinstance(x, str) else x.text() for x in self.children)


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node(); self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs); self.stack[-1].children.append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                       'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for position in range(len(self.stack) - 1, 0, -1):
            if self.stack[position].tag == tag:
                del self.stack[position:]; break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def article(self):
        def walk(node):
            if node.tag == 'article' and 'bd-article' in node.attrs.get('class', '').split():
                return node
            for child in node.children:
                if isinstance(child, Node):
                    result = walk(child)
                    if result is not None:
                        return result
            return None
        result = walk(self.root)
        if result is None:
            raise ValueError('rendered document has no article')
        return result


def markdown(html, *, source_path, target_path, language):
    """Project the existing rendered article, preserving code bytes and prose."""
    parser = ArticleParser(); parser.feed(html)
    protected = {}

    def link(href):
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or href.startswith('#'):
            return href
        if parsed.path == '/api/reader':
            return ''
        if parsed.path == '/api/asset':
            asset = parse_qs(parsed.query).get('id', [''])[0]
            destination = 'catalog/contracts/' + asset + '.json'
        elif parsed.path.startswith('/chapters/'):
            destination = 'docs/' + language + '/assets/' + parsed.path.lstrip('/')
        else:
            absolute = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), parsed.path))
            if '/reference/generated/' in absolute:
                destination = 'docs/' + language + '/api/' + Path(absolute).stem + '.md'
            elif '/user-guide/' in absolute or '/tutorials/' in absolute:
                if Path(absolute).stem in {'index', 'capability-matrix'}:
                    return ''
                destination = 'docs/' + language + '/tutorials/' + Path(absolute).stem + '.md'
            elif '/_images/' in absolute:
                destination = 'docs/' + language + '/assets/' + absolute.split('/_images/', 1)[1]
            elif '/_static/examples/' in absolute:
                destination = 'docs/' + language + '/assets/examples/' + absolute.split('/_static/examples/', 1)[1]
            else:
                # Non-reading navigation remains plain text, never a false local link.
                return ''
        return posixpath.relpath(destination, posixpath.dirname(target_path)) + (
            '#' + parsed.fragment if parsed.fragment else '')

    def render(node):
        if isinstance(node, str):
            return node
        tag, attrs = node.tag, node.attrs
        classes = attrs.get('class', '').split()
        if tag in {'script', 'style', 'button'} or 'headerlink' in classes:
            return ''
        if tag == 'math':
            formula = attrs.get('aria-label')
            if not formula:
                # Authored MathML need not have LaTeX source. Preserve its full
                # operator tree; never flatten roots/fractions/powers to text.
                def mathml(value):
                    if isinstance(value, str):
                        return escape(value)
                    attributes = ''.join(' ' + key + '="' + escape(val or '', quote=True) + '"'
                                         for key, val in value.attrs.items())
                    return '<' + value.tag + attributes + '>' + ''.join(
                        mathml(child) for child in value.children) + '</' + value.tag + '>'
                return '\n\n' + mathml(node) + '\n\n'
            return ('\n\n$$\n' + formula + '\n$$\n\n' if attrs.get('display') == 'block'
                    else '$' + formula + '$')
        if tag == 'pre':
            body = node.text().rstrip('\n')
            fence = '````' if '```' in body else '```'
            marker = 'SCIREL_LITERAL_' + str(len(protected)) + '_' + sha(body.encode())
            protected[marker] = fence + '\n' + body + '\n' + fence
            return '\n\n' + marker + '\n\n'
        if tag == 'code':
            return '`' + node.text() + '`'
        children = ''.join(render(child) for child in node.children)
        if tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            return '\n\n' + '#' * int(tag[1]) + ' ' + children.strip() + '\n\n'
        if tag == 'p' and 'rubric' in classes:
            return '\n\n## ' + children.strip() + '\n\n'
        if tag in {'p', 'div', 'section', 'dl', 'dd', 'table', 'tr'}:
            return '\n\n' + children.strip() + '\n\n'
        if tag == 'dt':
            return '\n\n**' + children.strip() + '**\n\n'
        if tag in {'strong', 'b'}:
            return '**' + children + '**'
        if tag in {'em', 'i'} and 'sig-param' not in classes:
            return '*' + children + '*'
        if tag == 'li':
            return '\n- ' + children.strip().replace('\n\n', '\n  ') + '\n'
        if tag in {'td', 'th'}:
            return children.strip() + ' | '
        if tag == 'a':
            destination = link(attrs.get('href', ''))
            return '[' + children + '](' + destination + ')' if destination else children
        if tag == 'img':
            destination = link(attrs.get('src', ''))
            return '![' + attrs.get('alt', '') + '](' + destination + ')' if destination else attrs.get('alt', '')
        if tag == 'br':
            return '\n'
        if 'classifier' in classes:
            return ': ' + children
        return children

    import re
    # Normalize outside protected literal nodes; code/output whitespace is data.
    rendered = render(parser.article()).strip()
    rendered = re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+', '\n\n', rendered)
    for marker, literal in protected.items():
        rendered = rendered.replace(marker, literal)
    return rendered + '\n'


def seal_runtime(directory, metadata):
    files = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('delivery contains symlink: ' + str(path))
        if path.is_file() and path != directory / 'runtime.json':
            data = path.read_bytes()
            files[path.relative_to(directory).as_posix()] = {'sha256': sha(data), 'bytes': len(data)}
    identity = {**metadata, 'files': files}
    identity['snapshot_sha256'] = sha(encode(identity))
    (directory / 'runtime.json').write_bytes(encode(identity))
    return identity


def document_links(relative, data):
    """Read explicit resource links without interpreting examples or downloads."""
    import re
    suffix = Path(relative).suffix.lower()
    if suffix not in {'.html', '.md', '.svg', '.css'}:
        return []
    text = data.decode('utf-8')
    if suffix == '.md':
        return markdown_links(text)[0]

    def css_links(css):
        # Preserve quoted URL bytes while excluding actual CSS comments.
        css = re.sub(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|/\*[\s\S]*?\*/''',
                     lambda match: '' if match[0].startswith('/*') else match[0], css)
        urls = re.findall(r'''url\(\s*(?:"([^"]*)"|'([^']*)'|([^\s)]*))\s*\)''', css,
                          flags=re.IGNORECASE)
        return [next((value for value in group if value), '') for group in urls] + [
            match[1] for match in re.findall(r'''@import\s+(["'])(.*?)\1''', css,
                                            flags=re.IGNORECASE)]

    if suffix == '.css':
        return css_links(text)
    parser = ArticleParser(); parser.feed(text)
    links = html_links(text)[0]

    def walk(node):
        if not isinstance(node, Node):
            return
        if node.attrs.get('style'):
            links.extend(css_links(node.attrs['style']))
        if node.tag == 'style':
            links.extend(css_links(node.text()))
        for child in node.children:
            walk(child)

    walk(parser.root)
    return links


def copy_referenced_assets(directory, candidates, readings):
    """Copy only resources reached from projected API/tutorial reading paths.

    Relative resource paths retain their captured bytes. Markdown/HTML/SVG/CSS
    resources can declare further local dependencies; other downloads are
    opaque and never executed. Missing or escaping links fail the export.
    """
    directory = directory.resolve()
    pending = [(relative, (directory / relative).read_bytes()) for relative in readings]
    visited = set()
    while pending:
        relative, data = pending.pop()
        if relative in visited:
            continue
        visited.add(relative)
        for href in document_links(relative, data):
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = ((directory / unquote(parsed.path).lstrip('/')) if parsed.path.startswith('/')
                      else directory / posixpath.dirname(relative) / unquote(parsed.path)).resolve()
            if not target.is_relative_to(directory):
                raise ValueError('resource link escapes export: ' + relative + ' -> ' + href)
            destination = target.relative_to(directory).as_posix()
            if destination in candidates:
                captured = candidates[destination]
                if destination not in visited:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(captured)
                    pending.append((destination, captured))
            elif not target.is_file():
                raise ValueError('referenced resource is missing: ' + relative + ' -> ' + href)


def local_link_closure(directory):
    """Check local document/image targets; no network or scientific execution."""
    checked, errors = 0, []
    for path in directory.rglob('*'):
        if not path.is_file() or path.suffix not in {'.html', '.md'}:
            continue
        for href in document_links(path.name, path.read_bytes()):
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = ((directory / unquote(parsed.path).lstrip('/')) if parsed.path.startswith('/')
                      else path.parent / unquote(parsed.path)).resolve()
            checked += 1
            if not target.is_relative_to(directory.resolve()) or not target.is_file():
                errors.append({'document': path.relative_to(directory).as_posix(), 'target': href})
    if errors:
        raise ValueError('local document/image links do not close: ' + json.dumps(errors[:20]))
    return {'status': 'PASS', 'links_checked': checked, 'network_links_checked': False,
            'scientific_text_review': 'NOT_RUN'}


def archive(directory, target):
    if target.exists():
        raise FileExistsError(target)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(directory).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                output.writestr(info, path.read_bytes())
    return {'path': str(target), 'sha256': sha(target.read_bytes()), 'bytes': target.stat().st_size}


def tutorial_imports(text):
    """Derive scientific imports from authored Python blocks, without execution."""
    lines, imports = text.splitlines(), set()
    position = 0
    while position < len(lines):
        if lines[position].strip() != '.. code-block:: python':
            position += 1; continue
        position += 1
        while position < len(lines) and not lines[position].strip():
            position += 1
        block = []
        while position < len(lines) and (not lines[position].strip() or lines[position].startswith('   ')):
            block.append(lines[position]); position += 1
        try:
            tree = ast.parse(textwrap.dedent('\n'.join(block)))
        except SyntaxError as error:
            raise ValueError('authored Python tutorial block is not syntactically complete') from error
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('scirel'):
                imports.update((node.module, alias.name) for alias in node.names)
            elif isinstance(node, ast.Import):
                imports.update((alias.name, None) for alias in node.names if alias.name.startswith('scirel'))
    return sorted(imports, key=str)


def source_closure(snapshots, source):
    """Reject stale projections before exporting any product bytes.

    Tutorials receive exact reference/content bindings, never an inferred
    scientific-review approval. Their current semantic review remains NOT_RUN.
    """
    from build_scirel_sphinx import load_translations
    from exposure import held_asset_ids
    from validate_asset_documents import load_document_set, validate_runtime
    documents = load_document_set(ROOT / 'catalog/examples')
    documents = [doc for doc in documents if doc['asset_id'] not in held_asset_ids()]
    translations = load_translations(ROOT, ROOT / 'catalog/examples', documents,
                                     excluded_ids=held_asset_ids())
    ids = {doc['asset_id'] for doc in documents}
    current_inputs = documentation_input_digests()
    signatures = {}
    bindings = set()
    for document in documents:
        validate_runtime(document, source_root=ROOT)
        api = document['public_api']['python']
        signatures[document['asset_id']] = api
        bindings.add((api['module'], api['symbol']))
        if 'canonical_module' in api:
            bindings.add((api['canonical_module'], api['canonical_symbol']))
    for language, snapshot in snapshots.items():
        if (snapshot.manifest.get('source_inputs') != current_inputs or
                snapshot.manifest.get('source_inputs_sha256') != sha(encode(current_inputs))):
            raise ValueError('documentation build-time inputs are absent, stale or mixed')
        if snapshot.ids != ids:
            raise ValueError('snapshot omitted or added a public asset')
        record_ids = {Path(path).stem for path in snapshot.manifest['files']
                      if path.startswith('records/') and path.endswith('.json')}
        api_ids = {Path(path).stem for path in snapshot.manifest['files']
                   if path.startswith('web/reference/generated/') and path.endswith('.html')}
        if record_ids != ids or api_ids != ids:
            raise ValueError('snapshot has missing or stale extra contract/API pages')
        for asset in ids:
            if snapshot.read('records/' + asset + '.json') != (ROOT / 'catalog/examples' / (asset + '.json')).read_bytes():
                raise ValueError('snapshot contract bytes differ from source: ' + asset)
        expected = build_capability_index(documents, source_revision=source,
            translations=translations if language == 'zh' else None, language=language)
        if snapshot.capability_index() != expected:
            raise ValueError('snapshot discovery/API mapping differs from current contracts')
        if language == 'zh':
            for asset in ids:
                if json.loads(snapshot.read('readers/' + asset + '.json')) != translations[asset]:
                    raise ValueError('snapshot reader differs from current bound sidecar: ' + asset)
    tutorial_bindings = []
    import re
    for language, relative_root in [('zh', ROOT / 'tools/docs/manual'),
                                     ('en', ROOT / 'tools/docs/manual/en')]:
        for path in sorted(relative_root.glob('*.rst')):
            text = path.read_text()
            references = set(re.findall(r':doc:`[^`]*?(scirel\.[a-zA-Z0-9_.-]+)[^`]*`', text))
            unknown = references - ids
            excluded = bool(unknown & held_asset_ids())
            if unknown - held_asset_ids():
                raise ValueError('tutorial refers to unknown or renamed assets: ' + str(sorted(unknown)))
            imports = tutorial_imports(text)
            invalid_imports = [item for item in imports if item[1] is not None and item not in bindings]
            support_imports = []
            for item in list(invalid_imports):
                try:
                    module = importlib.import_module(item[0])
                    value = getattr(module, item[1])
                    if (item[1] in getattr(module, '__all__', ()) and isinstance(value, type)
                            and issubclass(value, BaseException)):
                        support_imports.append(item); invalid_imports.remove(item)
                except (ImportError, AttributeError):
                    pass
            if invalid_imports and not excluded:
                raise ValueError('tutorial imports unavailable/renamed scientific API: ' + str(invalid_imports))
            tutorial_bindings.append({'language': language, 'tutorial_id': path.stem,
                'source_sha256': sha(path.read_bytes()),
                'contracts': {asset: sha((ROOT / 'catalog/examples' / (asset + '.json')).read_bytes())
                              for asset in sorted(references & ids)},
                'public_imports': [list(item) for item in imports if item in bindings],
                'public_exception_imports': [list(item) for item in support_imports],
                'delivery_status': 'subset-placeholder' if excluded else 'authored',
                'review_status': 'NOT_RUN',
                'meaning': 'current byte/reference binding; never a scientific-review approval'})
    inputs = [ROOT / 'scripts' / name for name in (
        'build_pure_delivery.py', 'solving_skill.py', 'capability_query.py', 'query.py', 'consumer_tools.py',
        'serve_consumer_mcp.py', 'scirel_docs.py', 'build_scirel_sphinx.py',
        'build_capability_matrix.py', 'validate_asset_documents.py', 'public_api_binding.py',
        'check_wheel_exposure.py', 'exposure.py')]
    inputs += [ROOT / 'tools/docs' / name for name in (
        'PURE_CONSUMPTION.md', 'mcp-requirements.txt', 'handbook.json', 'handbook.en.json')]
    inputs += sorted((ROOT / 'tools/docs/zh').glob('*.json'))
    inputs += sorted((ROOT / 'tools/docs/manual').rglob('*.rst'))
    skill_inputs = load_solving_skill(ROOT / 'skills/development/usage/scirel-solving')
    inputs += [ROOT / 'skills/development/usage/scirel-solving' / name for name in skill_inputs]
    return {'schema': 'scirel.consumer-source-closure', 'source_revision': source,
            'asset_count': len(ids), 'public_api_mapping_sha256': sha(encode(signatures)),
            'source_signature_check': 'PASS',
            'generator_and_reading_inputs': {
                **{path.relative_to(ROOT).as_posix(): sha(path.read_bytes()) for path in inputs
                   if not path.is_relative_to(ROOT / 'skills/development/usage/scirel-solving')},
                **{'skills/development/usage/scirel-solving/' + name: sha(data)
                   for name, data in skill_inputs.items()}},
            'tutorial_bindings': tutorial_bindings,
            'natural_language_scientific_review': 'NOT_RUN'}


def consumer_index(full_index):
    """Project source discovery into the metadata used by both runtime callers."""
    fields = ('asset_id', 'symbol', 'capability', 'capability_summary', 'operation',
              'operation_direction', 'model', 'geometry', 'coordinates', 'boundary',
              'device_scope', 'device_scope_source', 'aliases', 'taxonomy', 'title_zh')
    index = {key: full_index[key] for key in ('schema', 'source_revision', 'asset_count')}
    index['assets'] = [{key: record[key] for key in fields} for record in full_index['assets']]
    index['search_text'] = full_index['search_text']
    index['derivation'] = 'Read-only projection of exact public contracts and bound Chinese reader; selected ports/evidence are in get.'
    return index


def _export(wheel, docs_en, docs_zh, output, html_output):
    if (output.resolve().is_relative_to(html_output.resolve()) or
            html_output.resolve().is_relative_to(output.resolve())):
        raise ValueError('agent and HTML outputs must be distinct non-overlapping directories')
    for target in (output, html_output):
        if target.exists():
            raise FileExistsError('refusing overwrite: ' + str(target))
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        raise ValueError('source must be clean before binding a delivery')
    snapshots = {'en': Documentation(docs_en), 'zh': Documentation(docs_zh)}
    for language, snapshot in snapshots.items():
        if snapshot.manifest['source_revision'] != source or snapshot.manifest['source_dirty']:
            raise ValueError('documentation source differs from clean delivery candidate: ' + language)
        expected_language = {'en': 'en-US', 'zh': 'zh-CN'}[language]
        if snapshot.manifest.get('reader_language') != expected_language:
            raise ValueError('documentation reader language differs from input role: ' + language)
    if snapshots['en'].ids != snapshots['zh'].ids:
        raise ValueError('bilingual public asset sets differ')
    from exposure import held_asset_ids
    public_ids = {path.stem for path in (ROOT / 'catalog/examples').glob('*.json')} - held_asset_ids()
    if snapshots['en'].ids != public_ids:
        raise ValueError('documentation must cover the exact complete exposed catalog')
    closure = source_closure(snapshots, source)
    from validate_installed_wheel import _catalog_wheel_closure
    catalog_wheel, errors = _catalog_wheel_closure(ROOT, wheel, expected_source_revision=source)
    if errors or catalog_wheel['status'] != 'PASS':
        raise ValueError('catalog/source/wheel closure failed: ' + str(errors))
    closure['catalog_wheel_closure'] = catalog_wheel
    proof = inspect_wheel(wheel, source_root=ROOT / 'src')
    if proof['status'] != 'PASS':
        raise ValueError('exact wheel inspection failed: ' + json.dumps(proof))
    wheel_bytes = wheel.read_bytes()
    if sha(wheel_bytes) != proof['sha256']:
        raise ValueError('wheel changed during inspection')
    import email
    with zipfile.ZipFile(wheel) as wheel_zip:
        metadata = email.message_from_bytes(wheel_zip.read(next(x for x in wheel_zip.namelist() if x.endswith('.dist-info/METADATA'))))
        for path in (ROOT / 'licenses').rglob('*'):
            if path.is_file():
                suffix = '/licenses/' + path.relative_to(ROOT).as_posix()
                matches = [name for name in wheel_zip.namelist() if name.endswith(suffix)]
                if len(matches) != 1 or wheel_zip.read(matches[0]) != path.read_bytes():
                    raise ValueError('wheel notice bytes differ from source: ' + path.relative_to(ROOT).as_posix())
    output.mkdir(parents=True); html_output.mkdir(parents=True)
    def put(relative, data):
        path = output / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
    put('wheel/' + wheel.name, wheel_bytes)
    skill_inputs = load_solving_skill(ROOT / 'skills/development/usage/scirel-solving')
    for relative, data in skill_inputs.items():
        put('skills/scirel-solving/' + relative, data)
    for source_name, name in [('capability_query.py', 'capability_query.py'),
                              ('query.py', 'query.py'),
                              ('consumer_tools.py', 'consumer_tools.py'),
                              ('serve_consumer_mcp.py', 'server.py')]:
        data = (ROOT / 'scripts' / source_name).read_bytes()
        if sha(data) != closure['generator_and_reading_inputs'].get('scripts/' + source_name):
            raise ValueError('runtime tool differs from its bound source: ' + source_name)
        put('tools/' + name, data)
    put('mcp-requirements.txt', (ROOT / 'tools/docs/mcp-requirements.txt').read_bytes())
    put('mcp-connections.json', encode({
        'stdio': {'command': 'python', 'args': ['tools/server.py', '--root', '.', '--transport', 'stdio']},
        'streamable_http': {'url': 'http://127.0.0.1:8765/mcp'}}))
    contracts = {}
    for asset in sorted(snapshots['en'].ids):
        data = snapshots['en'].read('records/' + asset + '.json')
        if data != snapshots['zh'].read('records/' + asset + '.json'):
            raise ValueError('bilingual contract bytes differ: ' + asset)
        if data != (ROOT / 'catalog/examples' / (asset + '.json')).read_bytes():
            raise ValueError('snapshot contract differs from source: ' + asset)
        contracts[asset] = sha(data)
        put('catalog/contracts/' + asset + '.json', data)
    put('catalog/capability-index.json', encode(consumer_index(snapshots['zh'].capability_index())))
    chapters = []
    asset_candidates, reading_paths = {}, []

    def candidate(relative, data):
        if (relative.startswith('/') or posixpath.normpath(relative) != relative or
                not (output / relative).resolve().is_relative_to(output.resolve())):
            raise ValueError('invalid projected resource path: ' + relative)
        if relative in asset_candidates and asset_candidates[relative] != data:
            raise ValueError('projected resource path has conflicting source bytes: ' + relative)
        asset_candidates[relative] = data

    for language, snapshot in snapshots.items():
        html_root = html_output / language; html_root.mkdir()
        for relative in snapshot.manifest['files']:
            if relative == 'web/_static/webpack-macros.html':
                # Theme build template, not a rendered page/runtime resource.
                continue
            data = snapshot.read(relative)
            if relative.startswith('web/') or relative.startswith(('records/', 'readers/', 'chapters/')) or relative in ('CAPABILITY_MATRIX.md', 'capability-matrix.json'):
                target = html_root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                html_data = data
                if relative.endswith('.html'):
                    text = data.decode()
                    import re
                    for endpoint, folder in [('asset', 'records'), ('reader', 'readers')]:
                        text = re.sub(r'/api/' + endpoint + r'\?id=([a-zA-Z0-9_.-]+)',
                            lambda match: posixpath.relpath(folder + '/' + match[1] + '.json',
                                posixpath.dirname(relative)), text)
                    text = re.sub(r'/api/chapter\?id=([a-zA-Z0-9_.-]+)',
                        lambda match: posixpath.relpath('chapters/' + match[1] + '/chapter.json',
                            posixpath.dirname(relative)), text)
                    text = re.sub(r'(?<=href=")/chapters/([^"?]+)',
                        lambda match: posixpath.relpath('chapters/' + match[1],
                            posixpath.dirname(relative)), text)
                    text = text.replace('href="/CAPABILITY_MATRIX.md"', 'href="' +
                                        posixpath.relpath('CAPABILITY_MATRIX.md', posixpath.dirname(relative)) + '"')
                    text = text.replace('href="/capability-matrix.json"', 'href="' +
                                        posixpath.relpath('capability-matrix.json', posixpath.dirname(relative)) + '"')
                    html_data = text.encode()
                target.write_bytes(html_data)
            if relative.startswith('web/_images/'):
                candidate('docs/' + language + '/assets/' + relative.removeprefix('web/_images/'), data)
            if relative.startswith('web/_static/examples/'):
                candidate('docs/' + language + '/assets/examples/' + relative.removeprefix('web/_static/examples/'), data)
            if relative.startswith('chapters/'):
                candidate('docs/' + language + '/assets/' + relative, data)
        for asset in sorted(snapshot.ids):
            relative = 'web/reference/generated/' + asset + '.html'
            destination = 'docs/' + language + '/api/' + asset + '.md'
            put(destination, markdown(snapshot.read(relative).decode(), source_path=relative,
                                      target_path=destination, language=language))
            reading_paths.append(destination)
        book = json.loads(snapshot.read('handbook.json'))
        for chapter in book['chapters']:
            chapter_id = chapter['id']
            relative = 'web/user-guide/' + chapter_id + '.html'
            destination = 'docs/' + language + '/tutorials/' + chapter_id + '.md'
            put(destination, markdown(snapshot.read(relative).decode(), source_path=relative,
                                      target_path=destination, language=language))
            reading_paths.append(destination)
            if language == 'en':
                chapters.append({'chapter_id': chapter_id, 'paths': {
                    lang: 'docs/' + lang + '/tutorials/' + chapter_id + '.md' for lang in ('en', 'zh')}})
        for relative in sorted(snapshot.manifest['files']):
            if relative.startswith('web/tutorials/') and relative.endswith('.html'):
                tutorial_id = Path(relative).stem
                destination = 'docs/' + language + '/tutorials/' + tutorial_id + '.md'
                put(destination, markdown(snapshot.read(relative).decode(), source_path=relative,
                                          target_path=destination, language=language))
                reading_paths.append(destination)
                if language == 'en':
                    if any(item['chapter_id'] == tutorial_id for item in chapters):
                        raise ValueError('tutorial ID collides with chapter ID: ' + tutorial_id)
                    chapters.append({'chapter_id': tutorial_id, 'paths': {
                        lang: 'docs/' + lang + '/tutorials/' + tutorial_id + '.md' for lang in ('en', 'zh')}})
    copy_referenced_assets(output, asset_candidates, reading_paths)
    put('catalog/tutorial-index.json', encode({'schema': 'scirel.tutorial-index', 'chapters': chapters}))
    # The Agent wheel already carries the checked notice bytes. The human site
    # is separate and therefore needs its own notices.
    for path in sorted((ROOT / 'licenses').rglob('*')):
        if path.is_file():
            html_notice = html_output / 'licenses' / path.relative_to(ROOT / 'licenses')
            html_notice.parent.mkdir(parents=True, exist_ok=True)
            html_notice.write_bytes(path.read_bytes())
    requirements = metadata.get_all('Requires-Dist', [])
    put('runtime-requirements.txt', '# Derived from the exact delivered wheel METADATA. Python ' + metadata['Requires-Python'] + '\n' + '\n'.join(requirements) + '\n')
    runtime = {'package_version': metadata['Version'], 'requires_python': metadata['Requires-Python'],
               'requires_dist': requirements, 'wheel': wheel.name, 'wheel_sha256': sha(wheel_bytes),
               'dependencies_bundled': False}
    for item in chapters:
        if any(not (output / relative).is_file() for relative in item['paths'].values()):
            raise ValueError('tutorial index has an old or missing reading path')
    (html_output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>SciRel</title><a href="en/web/index.html">English</a> · <a href="zh/web/index.html">中文</a>\n')
    closure['local_links'] = {'agent': local_link_closure(output), 'html': local_link_closure(html_output)}
    if (subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != source or
            subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)):
        raise ValueError('source changed during export')
    for relative, digest in closure['generator_and_reading_inputs'].items():
        if sha((ROOT / relative).read_bytes()) != digest:
            raise ValueError('generator/reading/skill source input changed during export: ' + relative)
    current_skill = load_solving_skill(ROOT / 'skills/development/usage/scirel-solving')
    if current_skill != skill_inputs:
        raise ValueError('solving source changed during export')
    for relative, data in skill_inputs.items():
        bound = closure['generator_and_reading_inputs'].get(
            'skills/development/usage/scirel-solving/' + relative)
        if bound != sha(data) or (output / 'skills/scirel-solving' / relative).read_bytes() != data:
            raise ValueError('exported solving input differs from its bound source: ' + relative)
    identity = seal_runtime(output, {'schema': 'scirel.consumer-runtime',
        'source_revision': source, 'asset_count': len(contracts), 'runtime': runtime,
        'retrieval': {'backend': 'lexical-and', 'ranking_method': 'weighted-lexical',
            'completeness': 'unknown', 'scientific_applicability': 'not_assessed',
            'incomplete_status': 'retrieval_incomplete'}})
    return {'agent': identity, 'checks': {'source_closure': closure, 'wheel_inspection': proof}}


def build(wheel, docs_en, docs_zh, output, html_output):
    """Publish both complete projections, cleaning all owned stages on failure."""
    output, html_output = Path(output), Path(html_output)
    if (output.resolve().is_relative_to(html_output.resolve()) or
            html_output.resolve().is_relative_to(output.resolve())):
        raise ValueError('agent and HTML outputs must be distinct non-overlapping directories')
    for target in (output, html_output):
        if target.exists():
            raise FileExistsError('refusing overwrite: ' + str(target))
    output.parent.mkdir(parents=True, exist_ok=True)
    html_output.parent.mkdir(parents=True, exist_ok=True)
    published = []
    try:
        with tempfile.TemporaryDirectory(prefix='.scirel-delivery-stage-', dir=output.parent) as temp:
            stage = Path(temp)
            result = _export(wheel, docs_en, docs_zh, stage / 'agent', stage / 'html')
            (stage / 'agent').rename(output); published.append(output)
            (stage / 'html').rename(html_output); published.append(html_output)
        return result
    except BaseException:
        # Only these newly created task-owned paths can be rolled back.
        for target in published:
            shutil.rmtree(target)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('wheel', 'docs-en', 'docs-zh', 'output', 'html-output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = build(args.wheel, args.docs_en, args.docs_zh, args.output, args.html_output)
    print(json.dumps({'snapshot_sha256': result['agent']['snapshot_sha256'],
                      'checks': result['checks']}, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
