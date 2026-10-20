"""Dependency policy: mature scientific dependencies stay core; no plotting/IO extras."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_core_dependencies_are_declared_and_plot_io_extras_are_absent() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dependencies"] == ["numpy==2.5.4", "scipy==1.18.1", "mpmath==1.4.1"]
    assert "optional-dependencies" not in project
