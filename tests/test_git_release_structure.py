from __future__ import annotations

import subprocess
from pathlib import Path
import tomllib
import json


ROOT = Path(__file__).resolve().parents[1]


def test_git_release_structure_has_one_version_source() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    assert current["version"] == version
    assert current["wheel"]["version"] == version
    assert current["documentation"]["compatible_wheel"] == version
    assert (ROOT / f"docs/release/{version}-notes.md").is_file()


def test_historical_release_data_is_not_parallel_wheel_or_doc_copies() -> None:
    assert not list((ROOT / "release/wheel/versions").glob("*"))
    assert not list((ROOT / "release/docs/versions").glob("*"))
    tracked = subprocess.check_output(
        ["git", "ls-files", "*.whl", "dist", "build"],
        cwd=ROOT,
        text=True,
    )
    assert tracked.strip() == ""


def test_current_release_receipt_is_not_the_version_source() -> None:
    text = (ROOT / "release/README.md").read_text(encoding="utf-8")
    assert "not a second version" in text
    assert "pyproject.toml" in text
