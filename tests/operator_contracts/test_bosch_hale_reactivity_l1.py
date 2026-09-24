"""Bounded comparisons with withdrawn historical ASCOT5 and TokaGrad inputs."""

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.fusion import evaluate_bosch_hale_reactivity


_SOURCES = {
    "ASCOT5": (
        "boschhale聚变反应速率",
        "35a5d7d603835ca33bfbb8b25dd56c8e73062711abf505788a5218d2e6753bf6",
    ),
    "TokaGrad": (
        "TokaGrad DT聚变与快离子分配",
        "62793cba556c8ca9519fc4fd3db58778a457842e5866940cabf4d7ec9f139840",
    ),
}


def _source(project):
    root = os.environ.get(f"SCIREL_HISTORICAL_{project.upper()}_ROOT")
    if not root:
        pytest.skip(f"historical {project} input is not configured")
    directory, digest = _SOURCES[project]
    path = Path(root) / "operators" / directory / "scientific_operator.py"
    assert path.is_file()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    spec = importlib.util.spec_from_file_location(f"{project}_bosch_hale", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("reaction", "source_id"),
    [("DT", 1), ("DHe3", 2), ("DD_Tp", 3), ("DD_He3n", 4)],
)
def test_ascot5_reactivity_matches_saved_implementation(reaction, source_id):
    source = _source("ASCOT5")
    for temperature in (0.1, 1.0, 10.0, 100.0, 200.0):
        expected = source.boschhale_sigmav(source_id, temperature)
        actual = evaluate_bosch_hale_reactivity(temperature, reaction=reaction)
        assert actual == pytest.approx(expected, rel=1e-12)


def test_tokagrad_dt_is_rounded_overlap_not_exact_implementation_reuse():
    source = _source("TokaGrad")
    temperatures = np.array([0.2, 1.0, 10.0, 100.0, 200.0])
    canonical = evaluate_bosch_hale_reactivity(temperatures, reaction="DT")
    retained = source.bosch_hale_dt_reactivity(temperatures)
    np.testing.assert_allclose(canonical, retained, rtol=5e-5, atol=0)
    assert canonical[2] != retained[2]
    assert canonical[2] == pytest.approx(1.1361654705836232e-22, rel=1e-11)
    assert retained[2] == pytest.approx(1.1361734886996077e-22, rel=1e-11)


def test_tokagrad_clipping_is_not_in_the_standard_relation():
    source = _source("TokaGrad")
    retained = source.bosch_hale_dt_reactivity([0.1])[0]
    clipped = source.bosch_hale_dt_reactivity([0.2])[0]
    assert retained == clipped
    canonical = evaluate_bosch_hale_reactivity(0.1, reaction="DT")
    assert canonical < retained
