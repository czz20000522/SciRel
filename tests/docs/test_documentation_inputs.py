"""Documentation snapshots bind build-time source bytes before rendering."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import scirel_docs as docs  # noqa: E402


@pytest.fixture
def source_tree(tmp_path, monkeypatch):
    root = tmp_path / 'source'
    files = {
        'tools/docs/manual/example.rst': b'Handwritten tutorial\n',
        'tools/docs/sphinx/conf.py': b'# Sphinx configuration\n',
        'tools/docs/zh/reader.json': b'{"records": []}\n',
        'pyproject.toml': b'[project]\nversion = "0.1.0"\n',
        'catalog/examples/scirel.test.example.json': b'{"asset_id":"scirel.test.example"}\n',
        **{'scripts/' + name: ('# synthetic input ' + name + '\n').encode()
           for name in docs.DOCUMENTATION_BUILD_SCRIPTS},
    }
    for relative, data in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    monkeypatch.setattr(docs, 'ROOT', root)
    return root, files


def test_input_digests_bind_exact_bytes_and_relocated_subset(source_tree, tmp_path):
    root, files = source_tree
    assert docs.documentation_input_digests() == {
        relative: docs.sha(data) for relative, data in sorted(files.items())}
    relocated = tmp_path / 'selected-contracts'
    relocated.mkdir()
    original = root / 'catalog/examples/scirel.test.example.json'
    (relocated / original.name).write_bytes(original.read_bytes())
    (root / 'catalog/examples/scirel.test.not-selected.json').write_bytes(b'{}')
    selected = docs.documentation_input_digests(relocated)
    assert selected['catalog/examples/scirel.test.example.json'] == docs.sha(original.read_bytes())
    assert 'catalog/examples/scirel.test.not-selected.json' not in selected
    assert not any(str(tmp_path) in key for key in selected)


def test_source_hashes_ignore_caches_but_track_added_manual_and_overrides(source_tree, tmp_path):
    root, _ = source_tree
    before = docs.documentation_input_digests()
    for relative in ('tools/docs/__pycache__/conf.cpython-314.pyc',
                     'tools/docs/.cache/scratch', 'tools/docs/.DS_Store'):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'cache')
    assert docs.documentation_input_digests() == before
    manual = root / 'tools/docs/manual/additional.rst'
    manual.write_bytes(b'Additional tutorial\n')
    assert docs.documentation_input_digests()['tools/docs/manual/additional.rst'] == docs.sha(manual.read_bytes())
    external_outline = tmp_path / 'custom-outline.json'
    external_reader = tmp_path / 'custom-reader.json'
    external_outline.write_bytes(b'{"chapters": []}')
    external_reader.write_bytes(b'{"records": []}')
    overridden = docs.documentation_input_digests(
        outline=external_outline, translation_paths=[external_reader])
    assert overridden['build-inputs/outline.json'] == docs.sha(external_outline.read_bytes())
    assert overridden['build-inputs/translations/0000.json'] == docs.sha(external_reader.read_bytes())


def test_required_build_source_missing_fails_closed(source_tree):
    root, _ = source_tree
    (root / 'scripts/capability_query.py').unlink()
    with pytest.raises(FileNotFoundError):
        docs.documentation_input_digests()


@pytest.mark.parametrize('change', ['modify_manual', 'add_manual', 'delete_manual',
                                   'modify_contract', 'modify_override'])
def test_input_mutation_during_render_aborts_before_output(source_tree, tmp_path, monkeypatch,
                                                         change):
    root, _ = source_tree
    # A stub renderer isolates the build's source-byte transaction boundary.
    # It does not claim successful Sphinx rendering or contract validation.
    document = {
        'asset_id': 'scirel.test.example', 'title': {'en': 'Example', 'zh': '示例'},
        'summary': 'Synthetic contract', 'taxonomy': [], 'aliases': [],
        'version': '0.1.0', 'public_api': {'python': {
            'module': 'scirel.test', 'symbol': 'example'}},
        'verification': {'evidence_ceiling': 'synthetic fixture', 'known_limitations': []},
    }
    monkeypatch.setattr(docs, 'load_document_set', lambda path: [document])
    monkeypatch.setattr(docs, 'held_asset_ids', lambda: frozenset())
    monkeypatch.setattr(docs, 'project_version', lambda: '0.1.0')
    monkeypatch.setattr(docs, 'handbook_document', lambda ids, outline: {'chapters': []})
    monkeypatch.setattr(docs, 'load_english_handbook', lambda root, book: book)
    monkeypatch.setattr(docs, 'english_guide_status', lambda *args: {})
    monkeypatch.setattr(docs, 'english_available_docs', lambda *args, **kwargs: set())
    monkeypatch.setattr(docs, 'english_translation_gaps', lambda records: [])
    monkeypatch.setattr(docs, 'capability_search_text', lambda *args, **kwargs: 'example')
    monkeypatch.setattr(docs, 'build_capability_index', lambda *args, **kwargs: {})
    monkeypatch.setattr(docs, 'build_matrix', lambda *args, **kwargs: {})
    monkeypatch.setattr(docs, 'render_markdown', lambda matrix: '# Synthetic matrix\n')
    outline = tmp_path / 'outline.json'
    outline.write_bytes(b'{"chapters": []}')

    def render(*args, **kwargs):
        manual = root / 'tools/docs/manual/example.rst'
        if change == 'modify_manual':
            manual.write_bytes(b'Mutated tutorial\n')
        elif change == 'add_manual':
            (manual.parent / 'new.rst').write_bytes(b'Added tutorial\n')
        elif change == 'delete_manual':
            manual.unlink()
        elif change == 'modify_contract':
            (root / 'catalog/examples/scirel.test.example.json').write_bytes(b'{}')
        else:
            outline.write_bytes(b'{"changed": true}')
        return {'web/index.html': b'<html>Synthetic render</html>'}

    monkeypatch.setattr(docs, 'render_site', render)
    output = tmp_path / 'output'
    with pytest.raises(ValueError, match='source inputs changed during build'):
        docs.build(root / 'catalog/examples', output, outline=outline,
                   source_revision='a' * 40, source_dirty=False, language='en')
    assert not output.exists()


def test_real_snapshot_records_build_time_inputs(snapshot):
    manifest = json.loads((snapshot / 'manifest.json').read_bytes())
    expected = docs.documentation_input_digests()
    assert manifest['source_inputs'] == expected
    assert manifest['source_inputs_sha256'] == docs.sha(docs.encode(expected))
    assert not any(key.startswith('catalog/review/') for key in expected)
    assert manifest['snapshot_sha256'] == docs.sha(docs.encode({
        key: value for key, value in manifest.items() if key != 'snapshot_sha256'}))
