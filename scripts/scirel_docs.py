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

from packaging.version import InvalidVersion, Version

from validate_asset_documents import load_document_set
from exposure import held_asset_ids
from build_scirel_sphinx import (LANGUAGE_TAGS, english_available_docs,
                                english_guide_status, english_translation_gaps,
                                load_english_handbook, load_translations,
                                render_site)
from build_capability_matrix import build_matrix, render_markdown
from capability_query import (CAPABILITY_INDEX_SCHEMA, CAPABILITY_QUERY_SCHEMA,
                              CAPABILITY_REQUEST_SCHEMA, DEVICE_SCOPES, FILTER_ORDER,
                              query_capabilities, validate_capability_index)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scirel.documentation-snapshot'
NOTICE = ('开发文档 · 按每条资产的版本与证据范围使用。文档收录不代表人工批准、'
          '全项目通过或公开发行；此快照不是单一 wheel 的安装清单。')
NOTICE_EN = ('Development documentation · Use each asset according to its version and '
             'evidence scope. Inclusion does not imply human approval, project-wide '
             'acceptance or public release; this snapshot is not an installation '
             'manifest for a single wheel.')
LANGUAGES = tuple(LANGUAGE_TAGS)
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


DOCUMENTATION_BUILD_SCRIPTS = (
    'scirel_docs.py', 'build_scirel_sphinx.py', 'build_capability_matrix.py',
    'capability_query.py', 'validate_asset_documents.py', 'public_api_binding.py',
    'exposure.py',
)


def documentation_input_digests(documents=None, *, outline=None, translation_paths=None):
    """Hash exact source inputs, independent of a selected contract directory.

    Contract keys always use catalog/examples/<filename>; relocated/subset
    inputs therefore retain stable public identities. Only public docs sources
    and build code are included, never private review material. Explicit reader
    or outline overrides have stable keys without exposing their local paths.
    """
    documents = ROOT / 'catalog/examples' if documents is None else Path(documents)
    docs_root = ROOT / 'tools/docs'
    if not docs_root.is_dir() or not documents.is_dir():
        raise ValueError('documentation source directories are missing')
    digests = {}

    def include(key, path):
        if path.is_symlink():
            raise ValueError('documentation source input may not be a symlink: ' + key)
        digests[key] = sha(path.read_bytes())

    caches = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.cache', '_build'}
    for path in sorted(docs_root.rglob('*')):
        relative = path.relative_to(ROOT)
        if (set(relative.parts) & caches or path.suffix in {'.pyc', '.pyo'}
                or path.name == '.DS_Store'):
            continue
        if path.is_symlink():
            raise ValueError('documentation source input may not be a symlink: ' + relative.as_posix())
        if path.is_file():
            include(relative.as_posix(), path)
    for name in DOCUMENTATION_BUILD_SCRIPTS:
        include('scripts/' + name, ROOT / 'scripts' / name)
    include('pyproject.toml', ROOT / 'pyproject.toml')
    contracts = sorted(documents.glob('*.json'))
    if not contracts:
        raise ValueError('no documentation contract inputs')
    for path in contracts:
        include('catalog/examples/' + path.name, path)
    if outline is not None:
        include('build-inputs/outline.json', Path(outline))
    if translation_paths is not None:
        for number, path in enumerate(translation_paths):
            include('build-inputs/translations/' + str(number).zfill(4) + '.json', Path(path))
    return dict(sorted(digests.items()))


def project_version(root=ROOT):
    try:
        metadata = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))
        version = metadata['project']['version']
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ValueError('pyproject.toml has no readable project.version') from error
    if not isinstance(version, str) or not version:
        raise ValueError('pyproject.toml project.version must be a non-empty string')
    return version


def _validate_documentation_version(value, package_version):
    try:
        documentation = Version(value)
        package = Version(package_version)
    except InvalidVersion as error:
        raise ValueError('documentation_version must be a valid PEP 440 version') from error
    if len(documentation.release) < 2 or len(package.release) < 2:
        raise ValueError('documentation_version and project version need major/minor components')
    if (documentation.epoch, documentation.release[0], documentation.release[1]) != (
        package.epoch, package.release[0], package.release[1]
    ):
        raise ValueError('documentation_version must stay on the wheel major.minor release line')


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
    if book.get('schema') != 'scirel.handbook':
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
            review_catalog = ROOT / 'catalog/review/examples'
            if review_catalog.is_dir():
                available_assets |= {path.stem for path in review_catalog.glob('*.json')}
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
        raise ValueError('chapter selection is required; refusing historical fallback')
    selection = json.loads(selection_path.read_bytes())
    if set(selection) != {'schema', 'chapters'} or selection['schema'] != 'scirel.chapter-selection':
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


def chapter_files(asset_ids, *, expected_source_revision=None,
                  expected_project_version=None, expected_wheel_sha256=None):
    """Bind executed examples to current implementation before publishing them."""
    root = chapter_directory()
    execution = json.loads((root/'execution.json').read_bytes())
    if execution.get('schema') != 'scirel.chapter-execution':
        raise ValueError('selected chapter execution has an invalid schema')
    execution_source = execution.get('source_commit')
    if not isinstance(execution_source, str) or not re.fullmatch(r'[0-9a-f]{40}', execution_source):
        raise ValueError('selected chapter execution source commit is invalid')
    # The execution record is itself a Git-tracked file, so it cannot embed
    # the hash of the commit that contains its updated bytes.  Its
    # ``source_commit`` therefore identifies the implementation baseline used
    # for the run; the surrounding documentation snapshot remains bound to the
    # requested source revision.  The file and document digests below are the
    # compatibility proof between those two identities.
    if expected_project_version is not None and execution.get('wheel_version') != expected_project_version:
        raise ValueError('selected chapter execution wheel version differs from project version')
    if expected_wheel_sha256 is not None and execution.get('wheel_sha256') != expected_wheel_sha256:
        raise ValueError('selected chapter execution wheel digest differs from current release')
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


def _discovery(document):
    """Return the optional reviewed discovery block.

    Unknown keys inside the block are ignored: they are not projected and they
    never change the derived view.  A non-object block is a contract error.
    """
    discovery = document.get('discovery')
    if discovery is None:
        return {}
    if not isinstance(discovery, dict):
        raise ValueError('discovery must be an object: ' + document['asset_id'])
    return discovery


def _discovery_text(discovery, field):
    """Return one reviewed nonempty discovery text list, or ``None``."""
    values = discovery.get(field)
    if values is None:
        return None
    if not isinstance(values, list) or not values or any(
            not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError('invalid discovery.' + field + ' list')
    return [value.strip() for value in values]


def _discovery_value(discovery, field, fallback):
    """Return one reviewed discovery string, or the contract-derived fallback."""
    value = discovery.get(field)
    if value is None:
        return fallback.strip()
    if not isinstance(value, str) or not value.strip():
        raise ValueError('invalid discovery.' + field)
    return value.strip()


def _device_scope(document, discovery):
    """Return ``(scope, source)``; absence always means ``unclassified``."""
    if 'device_scope' not in discovery:
        return 'unclassified', 'default-unclassified'
    scope = discovery['device_scope']
    if scope not in DEVICE_SCOPES:
        raise ValueError('invalid discovery.device_scope: ' + document['asset_id'])
    return scope, 'discovery'


def _capability_port(port):
    record = {
        'name': port['name'],
        'description': port['description'],
        'units': port['units'],
        'shape': port['shape'],
        'dtype': port['dtype'],
        'required': port.get('required', True),
        'constraints': port['constraints'],
    }
    if 'default' in port:
        record['default'] = port['default']
    return record


def capability_record(document):
    """Project one contract into the read-only capability view.

    Reviewed ``discovery`` text for capability/operation/model/geometry/
    boundary/device_scope wins when present; otherwise the view derives from
    ``title``/``identity``/``taxonomy``/ports/``verification``.  ``aliases``
    always come from the top-level contract field (single recall truth), and
    unknown discovery keys are ignored.  ``device_scope`` defaults to
    ``unclassified`` and is never inferred from a name.
    """
    asset = document['asset_id']
    identity = document['identity']
    verification = document['verification']
    tests = list(verification['tests'])
    discovery = _discovery(document)
    capability_terms = _discovery_text(discovery, 'capability')
    operation_terms = _discovery_text(discovery, 'operation')
    scope, scope_source = _device_scope(document, discovery)
    return {
        'asset_id': asset,
        'symbol': document['public_api']['python']['symbol'],
        'public_api': document['public_api'],
        'capability': (capability_terms[0] if capability_terms
                       else document['title']['en'].strip()),
        'capability_summary': (' — '.join(capability_terms[1:])
                               if capability_terms and len(capability_terms) > 1
                               else document['summary']),
        'summary': document['summary'],
        'title_zh': document['title']['zh'],
        'operation': (operation_terms[0] if operation_terms
                      else identity['relation'].strip()),
        'operation_direction': (' — '.join(operation_terms[1:])
                                if operation_terms and len(operation_terms) > 1
                                else identity['direction'].strip()),
        'model': _discovery_value(discovery, 'model', identity['model']),
        'geometry': _discovery_value(discovery, 'geometry', identity['geometry']),
        'coordinates': identity['coordinates'].strip(),
        'boundary': _discovery_value(discovery, 'boundary', identity['boundary']),
        'device_scope': scope,
        'device_scope_source': scope_source,
        'aliases': list(document.get('aliases', [])),
        'taxonomy': list(document.get('taxonomy', [])),
        'ports': {
            'inputs': [_capability_port(port) for port in document['inputs']],
            'outputs': [_capability_port(port) for port in document['outputs']],
        },
        'contract_path': 'catalog/examples/' + asset + '.json',
        'record_path': 'records/' + asset + '.json',
        'docs_path': '/reference/generated/' + asset + '.html',
        'evidence': {
            'status': 'bounded' if tests else 'unvalidated',
            'scope': list(verification['scope']),
            'tests': tests,
            'evidence_ceiling': verification['evidence_ceiling'],
            'known_limitations': list(verification['known_limitations']),
        },
    }


def capability_search_text(document, translation=None, *, language='zh'):
    """Lexical recall text from the contract plus its bound reader layer.

    The Chinese site also recalls the Chinese reader prose and the Chinese
    title. The English site uses the English contract fields only (it has no
    English reader layer), so Chinese queries do not match English pages.
    The reviewed discovery fields are included except ``aliases``: the
    top-level contract ``aliases`` list remains the only recall alias source,
    so a stray ``discovery.aliases`` key cannot become a second truth.
    """
    if language not in LANGUAGES:
        raise ValueError('language must be one of: ' + ', '.join(LANGUAGES))
    if language == 'en' and translation is not None:
        raise ValueError('English recall text does not consume a reader layer')
    identity = document['identity']
    discovery = document.get('discovery')
    reviewed = {}
    if isinstance(discovery, dict):
        reviewed = {field: discovery[field] for field in
                    ('capability', 'operation', 'model', 'geometry',
                     'boundary', 'device_scope')
                    if field in discovery}
    payload = [
        document['asset_id'],
        document['title']['en'],
        document['summary'],
        identity['relation'],
        identity['direction'],
        identity['definition'],
        identity['model'],
        identity['geometry'],
        identity['coordinates'],
        identity['boundary'],
        identity['assumptions'],
        reviewed,
        document.get('aliases', []),
        document.get('taxonomy', []),
        [port['name'] for port in document['inputs']],
        [port['name'] for port in document['outputs']],
        [port['units'] for port in document['inputs']],
        [port['units'] for port in document['outputs']],
        document['applicability'],
        document['verification'],
    ]
    if language == 'zh':
        payload.insert(2, document['title']['zh'])
    if translation is not None:
        payload.append([translation['summary'], translation['definition'],
                        translation['model'], translation['boundary']])
    return json.dumps(payload, ensure_ascii=False).lower()


def build_capability_index(documents, *, source_revision, translations=None, language='zh'):
    """Build the read-only capability index published inside a snapshot."""
    if language not in LANGUAGES:
        raise ValueError('language must be one of: ' + ', '.join(LANGUAGES))
    records = sorted((capability_record(document) for document in documents),
                     key=lambda item: item['asset_id'])
    ids = [record['asset_id'] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate capability index asset_id')
    if translations is not None and set(translations) != set(ids):
        raise ValueError('capability index translations differ from documents')
    search_text = {}
    for document in documents:
        asset = document['asset_id']
        search_text[asset] = capability_search_text(
            document, None if translations is None else translations[asset],
            language=language)
    return {
        'schema': CAPABILITY_INDEX_SCHEMA,
        'source_revision': source_revision,
        'asset_count': len(records),
        'derivation': {
            'capability': ('discovery.capability when present (first entry is the '
                           'name, remaining text is the summary); otherwise '
                           'title.en + summary'),
            'operation': ('discovery.operation when present; otherwise '
                          'identity.relation + identity.direction'),
            'model': 'discovery.model; otherwise identity.model',
            'geometry': ('discovery.geometry; otherwise identity.geometry; '
                         'identity.coordinates is always included'),
            'boundary': 'discovery.boundary; otherwise identity.boundary',
            'device_scope': ('discovery.device_scope when present; otherwise '
                             'unclassified, never inferred as generic'),
            'aliases': ('contract top-level aliases only; a discovery.aliases key '
                        'is ignored so aliases never become a second truth'),
            'ports': 'inputs + outputs',
            'evidence': ('verification.scope/tests/evidence_ceiling/'
                         'known_limitations; status is bounded when '
                         'verification.tests is non-empty, else unvalidated'),
            'paths': ('contract_path is repository-relative; record_path is the '
                      'served exact contract; docs_path is the snapshot web route'),
        },
        'assets': records,
        'search_text': search_text,
    }


def build(documents: Path, output: Path, outline: Path | None = None,
          translation_paths: list[Path] | None = None,
          *, source_revision: str | None = None,
          source_dirty: bool | None = None,
          documentation_version: str | None = None,
          language: str = 'zh'):
    if language not in LANGUAGES:
        raise ValueError('language must be one of: ' + ', '.join(LANGUAGES))
    if language == 'en' and translation_paths is not None:
        raise ValueError('English build does not consume Chinese reader bundles')
    source_inputs = documentation_input_digests(
        documents, outline=outline, translation_paths=translation_paths)
    docs = load_document_set(documents)
    held = held_asset_ids()
    docs = [document for document in docs if document['asset_id'] not in held]
    if not docs:
        raise ValueError('all documents are withheld by the exposure hold')
    if documentation_version is None:
        documentation_version = project_version()
    if not isinstance(documentation_version, str) or not documentation_version.strip():
        raise ValueError('documentation_version must be a non-empty version')
    _validate_documentation_version(documentation_version, project_version())
    if output.exists():
        raise FileExistsError('output already exists; build a new snapshot')
    bound_source = source_revision
    source = source_revision
    if source is None:
        source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if not isinstance(source, str) or not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('source_revision must be a full Git commit id')
    dirty = source_dirty
    if dirty is None:
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
    if language == 'zh':
        translations = load_translations(ROOT, documents, docs,
                                         translation_paths=translation_paths,
                                         excluded_ids=held)
    else:
        if translation_paths is not None:
            raise ValueError('English build does not consume Chinese reader bundles')
        translations = None
    book = handbook_document({d['asset_id'] for d in docs}, outline)
    english_guides = None
    if language == 'en':
        book = load_english_handbook(ROOT, book)
        english_guides = english_guide_status(
            ROOT, book['chapters'],
            english_available_docs(ROOT, book, {d['asset_id'] for d in docs}, matrix=True))
    files = {}
    index = []
    for doc in docs:
        asset = doc['asset_id']
        files[f'records/{asset}.json'] = (documents / (asset + '.json')).read_bytes()
        summary = {k: doc[k] for k in ('asset_id', 'title', 'summary', 'taxonomy', 'aliases', 'version')}
        summary['public_api'] = doc['public_api']
        summary['evidence_ceiling'] = doc['verification']['evidence_ceiling']
        summary['known_limitations'] = doc['verification']['known_limitations']
        if language == 'zh':
            files[f'readers/{asset}.json'] = encode(translations[asset])
            summary['summary_zh'] = translations[asset]['summary']
            # Lexical retrieval of existing scientific text, never generated semantics.
            summary['search_text'] = json.dumps([doc, translations[asset]], ensure_ascii=False).lower()
        else:
            summary['search_text'] = capability_search_text(doc, language='en')
        index.append(summary)
    files['index.json'] = encode(index)
    files['capabilities.json'] = encode(build_capability_index(
        docs, source_revision=source, translations=translations, language=language))
    if language == 'zh':
        files['index.html'] = (ROOT / 'tools/docs/index.html').read_bytes()
        files['handbook.html'] = (ROOT / 'tools/docs/handbook.html').read_bytes()
        for path in STATIC_FILES:
            files['static/' + path] = (ROOT / 'tools/docs' / path).read_bytes()
    files['handbook.json'] = encode(book)
    expected_wheel_sha256 = None
    if bound_source is not None:
        current_path = ROOT / 'release/CURRENT.json'
        if current_path.is_file():
            current = json.loads(current_path.read_bytes())
            if current.get('source_revision') == bound_source:
                expected_wheel_sha256 = (
                    current.get('wheel', {}).get('artifact', {}).get('sha256')
                )
    chapter = None
    figure_files = None
    if language == 'zh':
        files.update(chapter_files(
            {d['asset_id'] for d in docs},
            expected_source_revision=bound_source,
            expected_project_version=project_version(),
            expected_wheel_sha256=expected_wheel_sha256,
        ))
        chapter = json.loads(files['chapters/magnetostatics/chapter.json'])
        figure_files = {name: files['chapters/magnetostatics/' + name]
                        for name in ('single.svg', 'pair.svg', 'rectangle.svg')}
    matrix = build_matrix(docs, revision=source)
    files['capability-matrix.json'] = encode(matrix)
    files['CAPABILITY_MATRIX.md'] = render_markdown(matrix).encode('utf-8')
    files.update(render_site(
        ROOT, docs, book, translations, chapter,
        figure_files=figure_files, matrix=matrix, language=language,
        withheld_ids=held,
    ))
    if language == 'en':
        # The pydata theme ships a multilingual copybutton; its Chinese
        # locale would otherwise leak into an English page.
        copy_path = 'web/_static/copybutton.js'
        if copy_path in files:
            copy_text = files[copy_path].decode('utf-8')
            for source_text, english_text in (
                ("'复制'", "'Copy'"),
                ("'复制到剪贴板'", "'Copy to clipboard'"),
                ("'复制成功!'", "'Copied!'"),
                ("'复制失败'", "'Copy failed'"),
            ):
                copy_text = copy_text.replace(source_text, english_text)
            files[copy_path] = copy_text.encode('utf-8')
    try:
        final_inputs = documentation_input_digests(
            documents, outline=outline, translation_paths=translation_paths)
    except (OSError, ValueError) as error:
        raise ValueError('documentation source inputs changed during build') from error
    if final_inputs != source_inputs:
        raise ValueError('documentation source inputs changed during build')
    manifest = {'schema': SCHEMA, 'source_commit': source, 'source_revision': source,
                'source_dirty': dirty,
                'source_inputs': source_inputs,
                'source_inputs_sha256': sha(encode(source_inputs)),
                'project_version': project_version(),
                'documentation_version': documentation_version,
                'asset_count': len(docs),
                'notice': NOTICE if language == 'zh' else NOTICE_EN,
                'reader_language': LANGUAGE_TAGS[language],
                'human_renderer': 'sphinx-pydata',
                'validation': {'schema_and_dependency_closure': True,
                               'scientific_runtime_revalidated': False},
                'files': {p: {'sha256': sha(b), 'bytes': len(b)} for p, b in sorted(files.items())}}
    if language == 'en':
        manifest['translation_gaps'] = english_translation_gaps(docs)
        manifest['english_guides'] = english_guides
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

    def envelope(self, schema='scirel.documentation-response', **items):
        return {'schema': schema,
                'snapshot_sha256': self.manifest['snapshot_sha256'],
                'source_commit': self.manifest['source_commit'],
                'source_revision': self.manifest.get('source_revision', self.manifest['source_commit']),
                'documentation_version': self.manifest.get(
                    'documentation_version', self.manifest.get('project_version')
                ),
                'notice': self.manifest.get('notice', NOTICE), **items}

    def search(self, q='', domain='', offset=0, limit=20, topic=''):
        if len(q) > 512 or offset < 0 or not 1 <= limit <= 100:
            raise ValueError('q <= 512 characters, offset >= 0, limit 1..100 required')
        # Read the bound index again so mutation after startup also fails closed.
        index = json.loads(self.read('index.json'))
        topic_ids = set(self.topic(topic)['document']['assets']) if topic else self.ids
        terms = q.lower().split()
        matches = [x for x in index if x['asset_id'] in topic_ids
                   and (not domain or domain in x['taxonomy'])
                   and all(t in x['search_text'] for t in terms)]
        page = [{k: v for k, v in x.items() if k != 'search_text'} for x in matches[offset:offset+limit]]
        return self.envelope(items=page, total=len(matches), offset=offset,
                             next_offset=offset+limit if offset+limit < len(matches) else None)

    def capability_index(self):
        """Read and verify the frozen capability index bound to this snapshot."""
        if 'capabilities.json' not in self.manifest['files']:
            raise KeyError('snapshot has no capability index; rebuild the snapshot')
        index = json.loads(self.read('capabilities.json'))
        return validate_capability_index(
            index,
            expected_source_revision=self.manifest.get(
                'source_revision', self.manifest['source_commit']),
            expected_ids=self.ids,
        )

    def capabilities(self, capability='', operation='', model='', geometry='',
                     device_scope='', alias='', q='', offset=0, limit=20, boundary='',
                     taxonomy=''):
        """Bounded, lexically ranked retrieval using the portable query core.

        All supplied filters and q terms remain AND conditions; partial structured
        matches are explicitly near_miss. Ranking never proves applicability.
        """
        response = query_capabilities(self.capability_index(), {
            'schema': CAPABILITY_REQUEST_SCHEMA,
            'capability': capability, 'operation': operation, 'model': model,
            'geometry': geometry, 'boundary': boundary, 'taxonomy': taxonomy,
            'device_scope': device_scope,
            'alias': alias, 'q': q, 'offset': offset, 'limit': limit,
        })
        return self.envelope(**response)

    def asset(self, asset_id):
        if asset_id not in self.ids:
            raise KeyError('unknown asset_id')
        return self.envelope(document=json.loads(self.read(f'records/{asset_id}.json')))

    def reader(self, asset_id):
        if f'readers/{asset_id}.json' not in self.manifest['files']:
            raise KeyError('snapshot has no Chinese reader layer')
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
            if set(p) - {'q', 'domain', 'offset', 'limit', 'topic'}:
                raise ValueError('unknown search parameter')
            for key in ('offset', 'limit'):
                if key in p:
                    p[key] = int(p[key])
            return self.search(**p)
        if parsed.path == '/api/capabilities':
            if set(p) - (set(FILTER_ORDER) | {'offset', 'limit'}):
                raise ValueError('unknown capability query parameter')
            for key in ('offset', 'limit'):
                if key in p:
                    p[key] = int(p[key])
            return self.capabilities(**p)
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
            endpoints = {'search': '/api/search?q=&domain=&offset=0&limit=20',
                         'asset': '/api/asset?id=scirel.…',
                         'manifest': '/api/manifest'}
            if any(path.startswith('readers/') for path in self.manifest['files']):
                endpoints['reader'] = '/api/reader?id=scirel.…'
            if any(path.startswith('chapters/') for path in self.manifest['files']):
                endpoints['chapters'] = '/api/chapters'
                endpoints['chapter'] = '/api/chapter?id=magnetostatics'
            # Older snapshots have no generated capability index; do not
            # advertise an endpoint they cannot serve.
            if 'capabilities.json' in self.manifest['files']:
                endpoints['capabilities'] = ('/api/capabilities?capability=…&operation=…&'
                                             'model=…&geometry=…&boundary=…&taxonomy=…&device_scope=…&'
                                             'alias=…&q=…&offset=0&limit=20')
            return self.envelope(endpoints=endpoints,
                                 handbook='/api/handbook', topic='/api/topic?id=…',
                                 topic_search='/api/search?topic=…&q=&offset=0&limit=20',
                                 operations='read-only; no callable execution',
                                 discovery=('lexical AND search, lowercase, whitespace separated; '
                                            'exact domain filter; structured capability filters'))
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
    b = subs.add_parser('build'); b.add_argument('--documents', type=Path, default=ROOT/'catalog/examples'); b.add_argument('--output', type=Path, required=True); b.add_argument('--outline', type=Path); b.add_argument('--language', choices=LANGUAGES, default='zh', help='site language: zh projects the Chinese reader layer; en projects the English contract fields with a skeleton guide'); b.add_argument('--translations', type=Path, action='append', help='Explicit complete reader bundle(s) for the selected document set; repeatable'); b.add_argument('--source-revision', help='explicit full Git commit id for an archived source tree'); b.add_argument('--source-dirty', action='store_true', help='mark an explicitly bound source tree as dirty'); b.add_argument('--documentation-version', help='documentation editorial version on the compatible wheel release line')
    for name in ('query', 'serve'):
        sub = subs.add_parser(name); sub.add_argument('--snapshot', type=Path, required=True); sub.add_argument('--expected-digest')
        if name == 'query':
            sub.add_argument('--q', default=''); sub.add_argument('--domain', default=''); sub.add_argument('--offset', type=int, default=0); sub.add_argument('--limit', type=int, default=20); sub.add_argument('--asset'); sub.add_argument('--reader'); sub.add_argument('--chapter'); sub.add_argument('--handbook', action='store_true'); sub.add_argument('--topic', default='')
            sub.add_argument('--capabilities', action='store_true', help='query the generated capability index instead of document search')
            sub.add_argument('--capability', default=''); sub.add_argument('--operation', default=''); sub.add_argument('--model', default=''); sub.add_argument('--geometry', default=''); sub.add_argument('--boundary', default=''); sub.add_argument('--taxonomy', default=''); sub.add_argument('--device-scope', '--device_scope', dest='device_scope', default=''); sub.add_argument('--alias', default='')
        else:
            sub.add_argument('--port', type=int, default=8765)
    a = parser.parse_args()
    if a.command == 'build':
        bound_dirty = True if a.source_dirty else (False if a.source_revision else None)
        result = build(a.documents, a.output, a.outline, a.translations,
                       source_revision=a.source_revision,
                       source_dirty=bound_dirty,
                       documentation_version=a.documentation_version,
                       language=a.language)
        print(json.dumps({k:v for k,v in result.items() if k != 'files'}, ensure_ascii=False)); return
    docs = Documentation(a.snapshot, a.expected_digest)
    if a.command == 'query':
        capability_query = any((a.capabilities, a.capability, a.operation, a.model,
                                a.geometry, a.boundary, a.taxonomy, a.device_scope, a.alias))
        if a.reader:
            result = docs.reader(a.reader)
        elif a.handbook:
            result = docs.handbook()
        elif a.chapter:
            result = docs.chapter(a.chapter)
        elif a.asset:
            result = docs.asset(a.asset)
        elif capability_query:
            result = docs.capabilities(a.capability, a.operation, a.model, a.geometry,
                                       a.device_scope, a.alias, a.q, a.offset, a.limit, a.boundary, a.taxonomy)
        else:
            result = docs.search(a.q, a.domain, a.offset, a.limit, a.topic)
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
