"""The spline evidence tests must go red when the evaluator returns a wrong value.

``scripts/mutation_check.py`` cannot answer that question for these two assets: its five output
mutants change numeric leaves of a returned value, and a spline constructor returns a callable
object, so every mutant reports ``not_exercised``.  ``tests/numerics/spline_value_mutant_check.py``
moves the mutation one level down, onto the evaluator, and re-runs the evidence file.

This test exists so that diagnostic is part of the gate rather than a script someone has to
remember to run.  It asserts the verdict only, not the literal numbers: the script's own floor
is a share of the collected tests, so adding a test to the evidence file does not turn this red.
A "not observed" verdict (exit code 2) is not a pass here either — it fails this test.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).with_name("spline_value_mutant_check.py")


def _load():
    spec = importlib.util.spec_from_file_location("spline_value_mutant_check", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_evidence_file_is_red_under_a_broken_evaluator(capsys):
    """A wrong evaluator must fail the spline evidence file, and the device must be proven loaded."""
    module = _load()
    code = module.main()
    captured = capsys.readouterr()
    report = captured.out + captured.err
    assert code == 0, report
    # The run must have reported an observation for all three runs, not merely exited 0:
    # a mutant that never loaded and a mutant that never changed a value both look green
    # otherwise.  The script's positive control is the marker column printed above.
    assert "collected" in report and "zero red" in report and "scale red" in report, report
    assert "marker True" in report, report
