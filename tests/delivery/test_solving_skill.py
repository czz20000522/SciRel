"""A hierarchical skill export is an unchanged, closed snapshot of its inputs."""

from pathlib import Path
import os
import sys

import pytest
from fs_links import directory_link, file_link_or_reparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import solving_skill  # noqa: E402


def _skill(root):
    (root / "references").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "SKILL.md").write_text("# Method\n\n[checks](references/checks.md#limits)\n")
    (root / "references/checks.md").write_text(
        "# Limits\n\n[helper](../scripts/delivery.py)\n[more][detail]\n\n"
        '[detail]: more.md "Further checks"\n'
    )
    (root / "references/more.md").write_text("# More\n\n[back](checks.md)\n")
    (root / "scripts/delivery.py").write_bytes(b'print("synthetic helper")\n')
    return root


def test_linked_hierarchy_and_helper_are_exported_unchanged_once(tmp_path):
    root = _skill(tmp_path / "skill")
    (root / "references/unselected.md").write_text("# Source-local notes\n")
    captured = solving_skill.load_solving_skill(root)
    assert set(captured) == {
        "SKILL.md",
        "references/checks.md",
        "references/more.md",
        "scripts/delivery.py",
    }
    assert captured == {path: (root / path).read_bytes() for path in captured}
    assert captured == solving_skill.load_solving_skill(root)
    (root / "scripts/delivery.py").write_bytes(b'print("new helper")\n')
    changed = solving_skill.load_solving_skill(root)
    assert captured["scripts/delivery.py"] == b'print("synthetic helper")\n'
    assert changed["scripts/delivery.py"] == b'print("new helper")\n'


def test_inline_examples_do_not_create_dependencies_but_html_and_images_do(tmp_path):
    root = _skill(tmp_path / "skill")
    (root / "image.bin").write_bytes(b"image fixture")
    (root / "SKILL.md").write_text(
        "# Method\n\n`[illustration](missing.md)`\n\n"
        "```md\n[example](also-missing.md)\n```\n\n"
        "<!-- [draft](missing-too.md) -->\n"
        "[external](https://example.org/paper_(figure))\n"
        '![image](image.bin)\n<a href="references/checks.md#limits">checks</a>\n'
    )
    assert "image.bin" in solving_skill.load_solving_skill(root)


def test_used_reference_forms_and_html_srcset_declare_the_actual_skill_closure(tmp_path):
    root = _skill(tmp_path / "skill")
    images = {
        "full.svg",
        "collapsed.svg",
        "shortcut.svg",
        "angle image.svg",
        "raw.svg",
        "small.svg",
        "large.svg",
        "multi.svg",
        "multi-small.svg",
        "multi-large.svg",
        "nested.svg",
        "container.svg",
    }
    for name in images:
        (root / name).write_bytes(b"<svg/>\n")
    (root / "SKILL.md").write_text(
        "# Method\n\n![full][figure]\n\n[figure]: full.svg\n\n"
        "![collapsed][]\n\n[collapsed]: collapsed.svg\n\n"
        "![shortcut]\n\n[shortcut]: shortcut.svg\n\n"
        "![angle](<angle image.svg>)\n\n"
        '<img src="raw.svg" srcset="small.svg 1x, large.svg 2x">\n\n'
        '<img\n    src="multi.svg"\n'
        '    srcset="multi-small.svg 1x, multi-large.svg 2x"\n>\n\n'
        '<div>\n    <img src="container.svg">\n</div>\n\n'
        "`<div>`\n\n    [quoted HTML](absent-quoted-html.svg)\n\n"
        "    <div>\n    [indented HTML](absent-indented-html.svg)\n    </div>\n\n"
        '<img src="raw.svg">\n\n    [after void](absent-after-void.svg)\n\n'
        "<div/>\n\n    [after self-closing](absent-after-self-closing.svg)\n\n"
        "[unused]: absent-definition.svg\n\n"
        "`[inline](absent-inline.svg)`\n\n"
        "~~~md\n[fenced](absent-fenced.svg)\n~~~\n\n"
        "    [indented](absent-indented.svg)\n\n"
        "- Outer\n    - [download](nested.svg)\n\n"
        "          [nested code](absent-nested-code.svg)\n\n"
        "    ~~~md\n    [nested fenced](absent-nested-fenced.svg)\n    ~~~\n"
    )
    assert set(solving_skill.load_solving_skill(root)) == {"SKILL.md", *images}


@pytest.mark.parametrize("srcset", ["small.svg 1x 2x", "small.svg nonsense"])
def test_ambiguous_html_image_candidates_fail_closed(tmp_path, srcset):
    root = _skill(tmp_path / "skill")
    (root / "SKILL.md").write_text('<img srcset="' + srcset + '">\n')
    with pytest.raises(ValueError, match="invalid static resource srcset"):
        solving_skill.load_solving_skill(root)


@pytest.mark.parametrize(
    "target",
    [
        "missing.md",
        "../../other-skill/SKILL.md",
        "%2e%2e/%2e%2e/private.md",
        "/private.md",
        "file:///private.md",
        "skill://other/SKILL.md",
        "checks.md#absent",
        "checks.md?hidden=1",
    ],
)
def test_missing_or_cross_skill_references_fail_closed(tmp_path, target):
    root = _skill(tmp_path / "skill")
    (root / "references/more.md").write_text("[bad](" + target + ")\n")
    with pytest.raises(ValueError, match="reference|anchor"):
        solving_skill.load_solving_skill(root)


@pytest.mark.parametrize("directory", [False, True])
def test_links_and_file_reparse_points_cannot_supply_selected_inputs(tmp_path, directory):
    root = _skill(tmp_path / "skill")
    external = tmp_path / "external"
    external.mkdir()
    (external / "helper.py").write_text("secret = 1\n")
    if directory:
        directory_link(root / "foreign", external)
        target = "foreign/helper.py"
    else:
        file_link_or_reparse(root / "helper.py", external / "helper.py")
        target = "helper.py"
    (root / "SKILL.md").write_text("[helper](" + target + ")\n")
    with pytest.raises(ValueError, match="unsafe solving reference") as error:
        solving_skill.load_solving_skill(root)
    if os.name == "nt" and not directory:
        assert "reparse point" in str(error.value.__cause__)


def test_a_redirected_skill_root_cannot_supply_any_input(tmp_path):
    external = _skill(tmp_path / "external")
    linked = directory_link(tmp_path / "linked", external)
    with pytest.raises(ValueError, match="unsafe solving skill root"):
        solving_skill.load_solving_skill(linked)


@pytest.mark.skipif(os.name != "nt", reason="Windows root component traversal")
def test_windows_skill_root_cannot_have_a_redirected_ancestor(tmp_path):
    external = tmp_path / "external"
    _skill(external / "skill")
    linked = directory_link(tmp_path / "linked", external)
    with pytest.raises(ValueError, match="unsafe solving skill root"):
        solving_skill.load_solving_skill(linked / "skill")


def test_a_directory_cannot_supply_regular_file_bytes(tmp_path):
    root = _skill(tmp_path / "skill")
    (root / "SKILL.md").write_text("[directory](references)\n")
    with pytest.raises(ValueError, match="reference"):
        solving_skill.load_solving_skill(root)


@pytest.mark.parametrize("target", ["helper.py:private", "helper.py%3Aprivate"])
def test_stream_syntax_cannot_supply_an_undeclared_file_input(tmp_path, target):
    root = _skill(tmp_path / "skill")
    (root / "helper.py").write_bytes(b"public helper\n")
    # This is a real alternate stream on Windows, and a distinct file on POSIX.
    (root / "helper.py:private").write_bytes(b"private stream\n")
    (root / "SKILL.md").write_text("[helper](" + target + ")\n")
    with pytest.raises(ValueError, match="reference"):
        solving_skill.load_solving_skill(root)


def test_a_directory_redirected_during_capture_is_never_followed(tmp_path, monkeypatch):
    root = _skill(tmp_path / "skill")
    external = _skill(tmp_path / "external")
    (root / "SKILL.md").write_text("[checks](foreign/checks.md#limits)\n")
    read = solving_skill._read_source
    changed = False

    def redirect_after_selection(root_fd, relative):
        nonlocal changed
        result = read(root_fd, relative)
        if relative == "SKILL.md" and not changed:
            changed = True
            directory_link(root / "foreign", external / "references")
        return result

    monkeypatch.setattr(solving_skill, "_read_source", redirect_after_selection)
    with pytest.raises(ValueError, match="unsafe solving reference"):
        solving_skill.load_solving_skill(root)


def test_replacing_a_source_with_identical_bytes_during_capture_is_rejected(tmp_path, monkeypatch):
    root = _skill(tmp_path / "skill")
    read = solving_skill._read_source
    changed = False

    def replace_after_read(root_fd, relative):
        nonlocal changed
        result = read(root_fd, relative)
        if relative == "scripts/delivery.py" and not changed:
            changed = True
            replacement = root / "replacement.py"
            replacement.write_bytes(result[0])
            replacement.replace(root / relative)
        return result

    monkeypatch.setattr(solving_skill, "_read_source", replace_after_read)
    with pytest.raises(ValueError, match="changed while loading"):
        solving_skill.load_solving_skill(root)


def test_source_change_during_capture_is_rejected_instead_of_mixing_bytes(tmp_path, monkeypatch):
    root = _skill(tmp_path / "skill")
    read = solving_skill._read_source
    changed = False

    def mutate_after_read(root_fd, relative):
        nonlocal changed
        result = read(root_fd, relative)
        if relative == "SKILL.md" and not changed:
            changed = True
            (root / "SKILL.md").write_text("# Replaced method\n")
        return result

    monkeypatch.setattr(solving_skill, "_read_source", mutate_after_read)
    with pytest.raises(ValueError, match="changed while loading"):
        solving_skill.load_solving_skill(root)


def test_undefined_reference_link_and_missing_required_helper_are_rejected(tmp_path):
    root = _skill(tmp_path / "skill")
    (root / "references/more.md").write_text("[unknown][undeclared]\n")
    with pytest.raises(ValueError, match="undefined solving Markdown reference"):
        solving_skill.load_solving_skill(root)
    (root / "references/more.md").write_text("# More\n")
    (root / "scripts/delivery.py").unlink()
    with pytest.raises(ValueError, match="scripts/delivery.py"):
        solving_skill.load_solving_skill(root)
