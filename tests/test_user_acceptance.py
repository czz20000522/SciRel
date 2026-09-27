"""Exercise the maintained user tasks without a source-project checkout."""

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = runpy.run_path(str(ROOT / "examples" / "user_acceptance.py"))


def test_user_acceptance_tasks_create_their_declared_results(tmp_path):
    tasks = (
        ("green_field_synthesis", "green_field_synthesis.csv"),
        ("quasineutral_profile", "quasineutral_profile.json"),
        ("pressure_state_and_residual", "pressure_state_and_residual.json"),
    )
    for task, artifact in tasks:
        report = ACCEPTANCE[task](tmp_path)
        assert report["passed"] is True
        assert (tmp_path / artifact).is_file()
