"""The tutorial execution proof is regenerated from the RST, not hand-edited.

These tests drive ``scripts/render_tutorial_execution.py`` as the maintainer does.
The real proof must be fresh; a source change must be reported; and the two
failure modes that the old hand-edited workflow could hide -- a failing block and
displayed output that the RST does not actually produce -- must refuse to write
``all_checks_passed: true``.
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/render_tutorial_execution.py"
PROOF = Path("tools/docs/kinetic-tutorial/execution.json")
RST = Path("tools/docs/sphinx/tutorials/kinetic-initial-value.rst")
BOUND_SOURCE = Path("src/scirel/kinetic/vlasov_poisson.py")


def _run(*arguments):
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=environment,
    )


def _copy_binding(tmp_path):
    """Copy the proof, the RST and every file the proof binds into a throwaway checkout."""
    proof = json.loads((ROOT / PROOF).read_bytes())
    bound = {*proof["source_files"], *proof["document_files"], PROOF, RST}
    for relative in bound:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    return proof


def _write_rst(tmp_path, body):
    rst = tmp_path / RST
    rst.parent.mkdir(parents=True, exist_ok=True)
    rst.write_text(textwrap.dedent(body), encoding="utf-8")
    return rst


def _mutate_one_ast_digit(path):
    """Change one digit of one numeric literal, which the behaviour digest must notice."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for node in ast.walk(ast.parse("".join(lines))):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            line = lines[node.lineno - 1]
            offset = node.col_offset
            while offset < len(line) and not line[offset].isdigit():
                offset += 1
            replacement = "2" if line[offset] != "2" else "3"
            lines[node.lineno - 1] = line[:offset] + replacement + line[offset + 1 :]
            mutated = "".join(lines)
            ast.parse(mutated)
            path.write_text(mutated, encoding="utf-8")
            return
    raise AssertionError("the bound source has no integer literal to mutate")


def test_repository_tutorial_proof_bindings_are_current():
    """A stale binding must fail the normal suite, not only a maintainer's memory.

    ``build_scirel_sphinx`` refuses to publish the kinetic tutorial while the
    proof disagrees with the bound bytes, but that only helps someone who runs a
    documentation build. This test puts the same comparison in ``dev.py check``,
    so a change to a bound source file, contract or the tutorial RST that forgets
    to rebind the proof fails here with the stale file named. It runs
    ``--digests-only`` (milliseconds, no tutorial replay); the replaying
    ``--write`` stays a manual step because it executes the tutorial and rewrites
    the record.
    """
    done = _run("--check", "--digests-only")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "FRESH" in done.stdout


def test_real_tutorial_proof_is_fresh():
    done = _run("--check")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "FRESH" in done.stdout


def test_check_reports_a_changed_bound_source_file(tmp_path):
    _copy_binding(tmp_path)
    _mutate_one_ast_digit(tmp_path / BOUND_SOURCE)
    done = _run("--check", "--digests-only", "--root", str(tmp_path))
    assert done.returncode == 1, done.stdout + done.stderr
    assert "STALE" in done.stdout
    assert f"source_files: {BOUND_SOURCE.as_posix()}" in done.stdout


def test_failed_tutorial_block_never_writes_a_passing_proof(tmp_path):
    _copy_binding(tmp_path)
    before = (tmp_path / PROOF).read_bytes()
    _write_rst(
        tmp_path,
        """\
        .. code-block:: python

           assert 1 == 2
        """,
    )
    done = _run("--write", "--root", str(tmp_path))
    assert done.returncode == 2, done.stdout + done.stderr
    assert "REPLAY FAILED" in done.stderr
    assert "AssertionError" in done.stderr
    assert (tmp_path / PROOF).read_bytes() == before


def test_displayed_output_mismatch_is_rejected(tmp_path):
    _copy_binding(tmp_path)
    before = (tmp_path / PROOF).read_bytes()
    _write_rst(
        tmp_path,
        """\
        .. code-block:: python

           print("19 1.038967e-12")

        .. code-block:: text

           19 1.038968e-12
        """,
    )
    done = _run("--write", "--root", str(tmp_path))
    assert done.returncode == 2, done.stdout + done.stderr
    assert "printed output the RST does not record" in done.stderr
    assert "1.038968e-12" in done.stderr
    assert (tmp_path / PROOF).read_bytes() == before
