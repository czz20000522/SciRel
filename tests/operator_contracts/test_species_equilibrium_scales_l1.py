"""Bounded source-parity checks against the saved fluidBW L1 operator."""

import hashlib
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic.species_equilibrium_scales import derive_species_equilibrium_scales


SOURCE_SHA256 = "17d06f1520d5d703a30d2493ae85086ecd6a271b1d9fe56dc16b58f8dc4b5397"

QE = 1.60217662e-19
MP = 1.6726219e-27
ME = 9.1094e-31
KB = 1.38064852e-23
CASES = [
    (
        dict(ms=[ME], qs=[-QE], ns_unit=[1.0], Ts_unit=[1.0], B0=1.0, n00=6.075e19, T00=1e3),
        dict(kn=13261.94247879565, wn=175881684853.009,
             vts=[18755492.605238933], wcs=[-175881684853.009],
             wps2=[1.9334304735564685e23], rhocs=[-7.5403735282285168e-05],
             sgns=[-1.0]),
    ),
    (
        dict(ms=[ME, 2 * MP], qs=[-QE, QE], ns_unit=[1.0, 1.0], Ts_unit=[1.0, 1.0],
             B0=6.0, n00=2e20, T00=4e3),
        dict(kn=656.53728326980831, wn=287364996.2373445,
             vts=[37510985.210477866, 618998.3194954904],
             wcs=[-1055290109118.054, 287364996.2373445],
             wps2=[6.3652032051241764e23, 1.7333021311259338e20],
             rhocs=[-2.5134578427428392e-05, 0.0015231427452522045],
             sgns=[-1.0, 1.0]),
    ),
]


def _source_operator():
    historical = os.environ.get("SCIREL_HISTORICAL_FLUIDBW_ROOT")
    delivery = os.environ.get("SCIREL_L1_ROOT")
    project_root = Path(historical) if historical else Path(delivery) / "fluidBW" if delivery else None
    if project_root is None or not project_root.is_dir():
        pytest.skip("fluidBW L1 input is not configured; scientific contract tests remain active")
    path = project_root / "operators/species_equilibrium_scales/scientific_operator.py"
    source = path.read_bytes()
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA256
    namespace = {"__name__": "fluidbw_species_equilibrium_scales"}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace["scientific_operator"]


@pytest.mark.parametrize("case,oracle", CASES)
def test_scirel_matches_source_and_saved_oracle(case, oracle):
    source = _source_operator()
    candidate = derive_species_equilibrium_scales(**case)
    retained = source(**case)
    assert candidate.keys() == retained.keys()
    for key in candidate:
        np.testing.assert_array_equal(candidate[key], retained[key])
    assert candidate["c2"] == 89875517873681760.0
    assert candidate["epsilon0"] == 8.854187817e-12
    assert candidate["kB"] == KB
    for key, reference in oracle.items():
        np.testing.assert_array_equal(candidate[key], reference)
