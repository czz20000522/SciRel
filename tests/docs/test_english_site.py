"""English documentation skeleton.

The English site is a language parameter over the same documentation builder:
API pages project the English contract fields, navigation and guide pages are
explicit identifier-only skeletons, search uses English contract text, and no
Chinese reader layer is bound.  Chinese-site tests remain in
``test_scirel_docs.py``; this file proves the English build path without
translating contracts or guides.
"""
import json
import re
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scirel_docs import Documentation, LANGUAGES, build  # noqa: E402
from build_scirel_sphinx import english_translation_gaps  # noqa: E402
from _document_fixtures import copy_example_closure, example_document_sources  # noqa: E402

CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]')
CLEAN_ASSET = 'scirel.field.poloidal-field-magnitude'


def test_language_selector_is_explicit_and_fails_closed(tmp_path):
    assert LANGUAGES == ('zh', 'en')
    with pytest.raises(ValueError, match='language must be one of'):
        build(tmp_path / 'documents', tmp_path / 'docs', language='fr')
    documents = copy_example_closure(tmp_path / 'documents')
    with pytest.raises(ValueError, match='does not consume Chinese reader bundles'):
        build(documents, tmp_path / 'docs', translation_paths=[Path('bundle.json')],
              language='en')


def test_english_snapshot_manifest_and_renderer(english_snapshot):
    docs = Documentation(english_snapshot)
    manifest = docs.manifest
    assert manifest['reader_language'] == 'en-US'
    assert manifest['notice'].startswith('Development documentation')
    assert not any(path.startswith('readers/') for path in manifest['files'])
    # The Chinese legacy single-page reader is not part of the English skeleton.
    assert not {'index.html', 'handbook.html', 'chapter.html'} & set(manifest['files'])
    assert 'web/index.html' in manifest['files']
    renderer = json.loads(docs.read('renderer.json'))
    assert renderer['language'] == 'en-US'
    assert 'jieba' not in renderer
    assert renderer['warnings_as_errors'] is True
    assert renderer['source_documents'] == len(docs.ids)


def test_english_api_page_is_contract_derived(english_snapshot):
    docs = Documentation(english_snapshot)
    page = docs.read('web/reference/generated/' + CLEAN_ASSET + '.html').decode()
    assert not CJK.search(page), 'clean English contract must render without CJK'
    for label in ('Parameters', 'Returns', 'Exceptions and failure behavior', 'Description',
                  'Applicability', 'Related functions', 'Example',
                  'Verification and limitations', 'Read the exact contract JSON'):
        assert label in page
    for chinese in ('参数', '返回值', '异常与失败行为', '适用范围', '验证与限制'):
        assert chinese not in page
    record = json.loads(docs.read('records/' + CLEAN_ASSET + '.json'))
    text = ' '.join(re.sub(r'<[^>]+>', ' ', page).split())
    assert record['title']['en'] in text
    compact = re.sub(r'\s+', '', text)
    assert record['public_api']['python']['signature'].replace(' ', '') in compact
    assert record['example']['code'].splitlines()[0] in text


def test_english_navigation_and_guide_are_identifier_skeletons(english_snapshot):
    docs = Documentation(english_snapshot)
    book = docs.handbook()['document']
    assert book['title'] == 'SciRel scientific handbook'
    assert book['chapters']
    for chapter in book['chapters']:
        assert chapter['title'] == chapter['id']
        assert not CJK.search(chapter['introduction'])
        assert chapter['topics']
        for topic in chapter['topics']:
            assert topic['title'] == topic['id']
            assert not CJK.search(topic['introduction'])
            assert 'tutorial_id' not in topic
    guide = docs.read('web/user-guide/electromagnetism.html').decode()
    assert 'not authored yet' in guide
    assert not CJK.search(guide)
    reference = docs.read('web/reference/electromagnetism.html').decode()
    assert 'Functions' in reference and 'Model and conditions' in reference


def test_english_search_uses_english_contract_text(english_snapshot):
    docs = Documentation(english_snapshot)
    result = docs.search('magnetic', limit=5)
    assert result['total'] > 0
    assert all('search_text' not in item for item in result['items'])
    entry = next(item for item in docs.index if item['asset_id'] == CLEAN_ASSET)
    assert 'summary_zh' not in entry
    assert not CJK.search(entry['search_text'])
    capability = docs.capability_index()
    assert not CJK.search(capability['search_text'][CLEAN_ASSET])


def test_english_snapshot_records_translation_gaps(english_snapshot):
    docs = Documentation(english_snapshot)
    gaps = docs.manifest.get('translation_gaps')
    assert isinstance(gaps, dict)
    assert set(gaps) <= docs.ids
    assert CLEAN_ASSET not in gaps
    for asset, paths in gaps.items():
        assert paths and all(path != 'title.zh' for path in paths)
        assert all(not CJK.search(str(path)) for path in paths)
    records = [json.loads(docs.read('records/' + asset + '.json')) for asset in docs.ids]
    # The manifest gap map is exactly the contract-derived projection; it is
    # recorded, never repaired by the builder.
    assert gaps == english_translation_gaps(records)


def test_english_translation_gap_scan_ignores_title_zh():
    document = {
        'asset_id': 'scirel.demo.asset',
        'title': {'en': 'English title', 'zh': '中文标题'},
        'identity': {'definition': '中文定义', 'model': 'English model'},
    }
    assert english_translation_gaps([document]) == {
        'scirel.demo.asset': ['identity.definition'],
    }


def test_english_build_cli_accepts_language(tmp_path):
    sources = example_document_sources()
    subset = ['scirel.field.current-green-superposition', CLEAN_ASSET]
    documents = tmp_path / 'documents'
    documents.mkdir(parents=True)
    for asset in subset:
        (documents / (asset + '.json')).write_bytes(sources[asset].read_bytes())
    output = tmp_path / 'docs-en'
    subprocess.run(
        [sys.executable, str(ROOT / 'scripts/scirel_docs.py'), 'build',
         '--language', 'en', '--documents', str(documents), '--output', str(output)],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['reader_language'] == 'en-US'
    assert manifest['asset_count'] == len(subset)
    assert 'web/index.html' in manifest['files']
