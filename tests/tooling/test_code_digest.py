"""Correctness evidence goes stale when behaviour can change, and only then."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from code_digest import contract_digest, source_digest  # noqa: E402

BASE = '''"""Module."""


def f(x):
    """Doc."""
    return x + 1
'''


def _digest(tmp_path, text):
    path = tmp_path / "m.py"
    path.write_text(text)
    return source_digest(path)


def test_docstrings_comments_and_layout_do_not_change_the_digest(tmp_path):
    base = _digest(tmp_path, BASE)
    assert (
        _digest(
            tmp_path,
            BASE.replace(
                '"""Doc."""', '"""Rewritten at length.\n\n    Notes\n    -----\n    More.\n    """'
            ),
        )
        == base
    )
    assert _digest(tmp_path, BASE.replace('"""Module."""', "# only a comment")) == base
    assert (
        _digest(tmp_path, BASE.replace("return x + 1", "return (x +\n            1)  # why"))
        == base
    )


def test_any_code_change_changes_the_digest(tmp_path):
    base = _digest(tmp_path, BASE)
    for changed in (
        BASE.replace("x + 1", "x + 2"),
        BASE.replace("x + 1", "x - 1"),
        BASE.replace("def f(x)", "def f(x, y=0)"),
        BASE + "\nLIMIT = 1\n",
        BASE.replace('"""Doc."""', 'NOTE = "Doc."'),
    ):
        assert _digest(tmp_path, changed) != base


def test_a_string_that_is_not_a_docstring_counts(tmp_path):
    text = 'def f():\n    x = 1\n    "not a docstring"\n    return x\n'
    assert _digest(tmp_path, text) != _digest(
        tmp_path, text.replace('"not a docstring"', '"other"')
    )


def test_data_files_are_digested_by_their_bytes(tmp_path):
    path = tmp_path / "table.in"
    path.write_text("1 2\n")
    before = source_digest(path)
    path.write_text("1  2\n")
    assert source_digest(path) != before


def test_contract_digest_follows_the_call_and_not_the_prose(tmp_path):
    path = tmp_path / "c.json"
    document = {
        "public_api": {"s": 1},
        "inputs": [],
        "outputs": [],
        "example": {"code": "x"},
        "summary": "a",
        "version": "1",
    }
    path.write_text(json.dumps(document))
    before = contract_digest(path)
    path.write_text(json.dumps({**document, "summary": "b", "version": "2"}))
    assert contract_digest(path) == before
    path.write_text(json.dumps({**document, "example": {"code": "y"}}))
    assert contract_digest(path) != before
