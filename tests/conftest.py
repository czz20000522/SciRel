"""Shared fixtures for maintained SciRel scientific contracts."""

from __future__ import annotations

import os
import sys

# Tests are the review harness and may import held implementations; the default
# package remains non-importable for held capabilities.
os.environ.setdefault("SCIREL_REVIEW_HOLD", "1")
from pathlib import Path

_REVIEW_SRC = Path(__file__).resolve().parents[1] / "catalog" / "review" / "candidates" / "src"
if _REVIEW_SRC.is_dir():
    import scirel.collisions as _collisions
    import scirel.equilibrium as _equilibrium
    import scirel.inference as _inference
    import scirel.kinetic as _kinetic
    import scirel.physics as _physics
    import scirel.kinetic.dispersion as _dispersion

    _collisions.__path__.append(str(_REVIEW_SRC / "scirel" / "collisions"))
    _equilibrium.__path__.append(str(_REVIEW_SRC / "scirel" / "equilibrium"))
    _inference.__path__.append(str(_REVIEW_SRC / "scirel" / "inference"))
    _kinetic.__path__.append(str(_REVIEW_SRC / "scirel" / "kinetic"))
    _physics.__path__.append(str(_REVIEW_SRC / "scirel" / "physics"))
    _dispersion.__path__.append(str(_REVIEW_SRC / "scirel" / "kinetic" / "dispersion"))

import pytest

# Domain fixtures live next to their domain. The geometry axisymmetric-grid
# fixtures are also consumed by cross-domain composition tests, so register
# that conftest as a root plugin; this file defines only the universal
# ``candidate`` fixture below.
pytest_plugins = ["geometry.conftest"]

UNIT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_SRC = UNIT_ROOT / "src"

# Test scope is directory-scoped so a moved or renamed module follows its
# functional domain instead of a hand-maintained list. ``tests/<domain>`` is a
# scientific contract, ``tests/cross_domain`` an integration suite, and the
# four generic layers own the remaining top-level directories.
TESTS_ROOT = Path(__file__).resolve().parent
LAYER_MARKERS = {
    "architecture": "architecture",
    "docs": "docs",
    "delivery": "delivery",
    "tooling": "tooling",
    "cross_domain": "integration",
}
UNMARKED_DIRECTORIES = {"fixtures", "__pycache__"}


def _marker_for_test_path(path: Path) -> str | None:
    """Return the single scope marker implied by a collected test path."""
    try:
        relative = path.resolve().relative_to(TESTS_ROOT)
    except ValueError:
        return None
    parts = relative.parts
    if len(parts) < 2:
        # Files directly under tests/ are not owned by one layer or domain.
        return None
    owner = parts[0]
    if owner in LAYER_MARKERS:
        return LAYER_MARKERS[owner]
    if owner in UNMARKED_DIRECTORIES or owner.startswith(("_", ".")):
        return None
    return "contract"


def pytest_collection_modifyitems(config, items):
    """Attach exactly one directory-derived scope marker to every test item."""
    for item in items:
        path = getattr(item, "path", None)
        if path is None:
            continue
        marker = _marker_for_test_path(Path(path))
        if marker is None or item.get_closest_marker(marker) is not None:
            continue
        item.add_marker(marker)


@pytest.fixture(scope="session")
def candidate():
    """Import the source candidate, or the installed wheel during release checks."""
    installed_runtime = os.environ.get("SCIREL_INSTALLED_RUNTIME") == "1"
    if not installed_runtime:
        sys.path.insert(0, str(CANDIDATE_SRC))
    import scirel
    from scirel.geometry import (  # noqa: F401
        classify_material_support,
        map_axisymmetric_equilibrium_to_cartesian_grid,
        solve_axisymmetric_equilibrium_grid_mapping,
    )
    from scirel.geometry import axisymmetric_grid_mapping, material_support

    module_root = Path(scirel.__file__).resolve()
    if installed_runtime:
        assert module_root.is_relative_to(Path(sys.prefix).resolve()), (
            "release tests must import the installed wheel"
        )
    else:
        assert module_root.is_relative_to(CANDIDATE_SRC.resolve()), (
            "the candidate package must not resolve to the frozen SciRel tree"
        )
    yield {
        "mapping": map_axisymmetric_equilibrium_to_cartesian_grid,
        "classification": classify_material_support,
        "composition": solve_axisymmetric_equilibrium_grid_mapping,
        "mapping_module": axisymmetric_grid_mapping,
        "classification_module": material_support,
    }
    if not installed_runtime:
        sys.path.remove(str(CANDIDATE_SRC))
