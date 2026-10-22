"""A hierarchical skill export is an unchanged, closed snapshot of its inputs."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import solving_skill  # noqa: E402


def _skill(root):
    (root / 'references').mkdir(parents=True)
    (root / 'scripts').mkdir()
    (root / 'SKILL.md').write_text('# Method\n\n[checks](references/checks.md#limits)\n')
    (root / 'references/checks.md').write_text(
        '# Limits\n\n[helper](../scripts/delivery.py)\n[more][detail]\n\n'
        '[detail]: more.md "Further checks"\n')
    (root / 'references/more.md').write_text('# More\n\n[back](checks.md)\n')
    (root / 'scripts/delivery.py').write_text('print("synthetic helper")\n')
    return root


def test_linked_hierarchy_and_helper_are_exported_unchanged_once(tmp_path):
    root = _skill(tmp_path / 'skill')
    (root / 'references/unselected.md').write_text('# Source-local notes\n')
    captured = solving_skill.load_solving_skill(root)
    assert set(captured) == {'SKILL.md', 'references/checks.md',
                             'references/more.md', 'scripts/delivery.py'}
    assert captured == {path: (root / path).read_bytes() for path in captured}
    assert captured == solving_skill.load_solving_skill(root)
    (root / 'scripts/delivery.py').write_bytes(b'print("new helper")\n')
    changed = solving_skill.load_solving_skill(root)
    assert captured['scripts/delivery.py'] == b'print("synthetic helper")\n'
    assert changed['scripts/delivery.py'] == b'print("new helper")\n'


def test_inline_examples_do_not_create_dependencies_but_html_and_images_do(tmp_path):
    root = _skill(tmp_path / 'skill')
    (root / 'image.bin').write_bytes(b'image fixture')
    (root / 'SKILL.md').write_text(
        '# Method\n\n`[illustration](missing.md)`\n\n'
        '```md\n[example](also-missing.md)\n```\n\n'
        '<!-- [draft](missing-too.md) -->\n'
        '[external](https://example.org/paper_(figure))\n'
        '![image](image.bin)\n<a href="references/checks.md#limits">checks</a>\n')
    assert 'image.bin' in solving_skill.load_solving_skill(root)


@pytest.mark.parametrize('target', [
    'missing.md', '../../other-skill/SKILL.md', '%2e%2e/%2e%2e/private.md',
    '/private.md', 'file:///private.md', 'skill://other/SKILL.md',
    'checks.md#absent', 'checks.md?hidden=1',
])
def test_missing_or_cross_skill_references_fail_closed(tmp_path, target):
    root = _skill(tmp_path / 'skill')
    (root / 'references/more.md').write_text('[bad](' + target + ')\n')
    with pytest.raises(ValueError, match='reference|anchor'):
        solving_skill.load_solving_skill(root)


@pytest.mark.parametrize('directory', [False, True])
def test_symlinks_cannot_supply_an_input_even_after_a_path_is_selected(tmp_path, directory):
    root = _skill(tmp_path / 'skill')
    external = tmp_path / 'external'
    external.mkdir()
    (external / 'helper.py').write_text('secret = 1\n')
    if directory:
        (root / 'foreign').symlink_to(external, target_is_directory=True)
        target = 'foreign/helper.py'
    else:
        (root / 'helper.py').symlink_to(external / 'helper.py')
        target = 'helper.py'
    (root / 'SKILL.md').write_text('[helper](' + target + ')\n')
    with pytest.raises(ValueError, match='unsafe solving reference'):
        solving_skill.load_solving_skill(root)


def test_source_change_during_capture_is_rejected_instead_of_mixing_bytes(tmp_path, monkeypatch):
    root = _skill(tmp_path / 'skill')
    read = solving_skill._read_source
    changed = False

    def mutate_after_read(root_fd, relative):
        nonlocal changed
        result = read(root_fd, relative)
        if relative == 'SKILL.md' and not changed:
            changed = True
            (root / 'SKILL.md').write_text('# Replaced method\n')
        return result

    monkeypatch.setattr(solving_skill, '_read_source', mutate_after_read)
    with pytest.raises(ValueError, match='changed while loading'):
        solving_skill.load_solving_skill(root)


def test_undefined_reference_link_and_missing_required_helper_are_rejected(tmp_path):
    root = _skill(tmp_path / 'skill')
    (root / 'references/more.md').write_text('[unknown][undeclared]\n')
    with pytest.raises(ValueError, match='undefined solving Markdown reference'):
        solving_skill.load_solving_skill(root)
    (root / 'references/more.md').write_text('# More\n')
    (root / 'scripts/delivery.py').unlink()
    with pytest.raises(ValueError, match='scripts/delivery.py'):
        solving_skill.load_solving_skill(root)
