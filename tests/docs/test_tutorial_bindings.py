"""Human tutorial references stay checked independently of runtime export."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from scirel_docs import tutorial_imports, tutorial_source_bindings  # noqa: E402

ASSET = "scirel.synthetic.evaluate"
DOCUMENT = {
    "asset_id": ASSET,
    "public_api": {"python": {"module": "scirel.synthetic", "symbol": "evaluate"}},
}


def test_authored_python_imports_use_ast_names_and_ignore_prose_comments_and_strings():
    text = """Prose mentioning from scirel.prose import ignored.

.. code-block:: python

   from scirel.synthetic import evaluate as local_name
   import scirel.synthetic as scientific
   import numpy as np
   note = "from scirel.string import ignored"
   # from scirel.comment import ignored

End of block.
"""
    assert set(tutorial_imports(text)) == {
        ("scirel.synthetic", "evaluate"),
        ("scirel.synthetic", None),
    }


@pytest.mark.parametrize("problem", ["renamed_reference", "renamed_import", "syntax"])
def test_human_tutorial_binding_rejects_stale_reference_import_and_invalid_code(tmp_path, problem):
    manual = tmp_path / "tools/docs/manual"
    manual.mkdir(parents=True)
    text = f"See :doc:`../reference/generated/{ASSET}`.\n\n"
    text += ".. code-block:: python\n\n   from scirel.synthetic import evaluate\n"
    if problem == "renamed_reference":
        text = text.replace(ASSET, "scirel.synthetic.renamed")
    elif problem == "renamed_import":
        text = text.replace("import evaluate", "import renamed")
    else:
        text += "   incomplete = (\n"
    (manual / "example.rst").write_text(text)
    with pytest.raises(ValueError):
        tutorial_source_bindings(tmp_path, [DOCUMENT], excluded_ids=set())


def test_public_exception_is_bound_statically_without_running_module_and_held_guide_is_placeholder(
    tmp_path,
):
    manual = tmp_path / "tools/docs/manual"
    manual.mkdir(parents=True)
    (manual / "example.rst").write_text(""".. code-block:: python

   from scirel.synthetic import evaluate, FormatError
""")
    source = tmp_path / "src/scirel/synthetic.py"
    source.parent.mkdir(parents=True)
    source.write_text("""__all__ = ['evaluate', 'FormatError']
class FormatError(ValueError): pass
raise AssertionError('tutorial binding must never import this module')
""")
    bound = tutorial_source_bindings(tmp_path, [DOCUMENT], excluded_ids=set())
    assert bound[0]["public_imports"] == [["scirel.synthetic", "evaluate"]]
    proof = bound[0]["public_exception_imports"]["scirel.synthetic.FormatError"]
    assert set(proof) == {"src/scirel/synthetic.py"}
    assert bound[0]["review_status"] == "NOT_RUN"
    (manual / "held.rst").write_text("""See :doc:`../reference/generated/scirel.synthetic.held`.

.. code-block:: python

   from scirel.synthetic import held
""")
    bound = tutorial_source_bindings(tmp_path, [DOCUMENT], excluded_ids={"scirel.synthetic.held"})
    assert bound[1]["delivery_status"] == "subset-placeholder"
