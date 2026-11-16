"""Every declared failure channel of a covered collision contract has one assertion.

`failure_semantics` names the exceptions and warnings a caller can actually see.
A contract that declares a channel nobody exercises is an unverified promise, so
this file carries one callable per declared channel and two checks:

* the table's channel set equals the classes the contract's ``failure_semantics``
  text names, so a channel cannot be added, renamed or dropped without editing
  the table deliberately;
* every callable really produces its declared channel, so the mapping stays
  executable rather than documentary.

`COVERED` records which contracts are bound here. It grows as the domain is
finished; the final state names all twenty ``scirel.collisions.*`` assets, which
is the domain-level claim of issue #2's companion evidence work. Channels are
matched by exception class name only; the message text stays owned by the
implementation and its own per-asset tests.
"""

from __future__ import annotations

import json
import re
import warnings
from pathlib import Path

import numpy as np
import pytest

from scirel.collisions import (
    assemble_atomic_hydrogen_collision_matrices,
    assemble_atomic_hydrogen_omega_frequencies,
    assemble_molecular_hydrogen_collision_matrices,
    assemble_molecular_hydrogen_omega_frequencies,
    average_cross_section_over_maxwellian,
    evaluate_atomic_hydrogen_1s_radiative_recombination_rate,
    evaluate_fast_ion_stopping_increment,
    normalized_momentum,
    thermal_electron_momentum,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "catalog" / "examples"
_DECLARED = re.compile(r"\b([A-Z][A-Za-z]*(?:Error|Warning|Exception))\b")

COVERED = (
    "scirel.collisions.normalized-momentum",
    "scirel.collisions.thermal-electron-momentum",
    "scirel.collisions.fast-ion-stopping-increment",
    "scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient",
    "scirel.collisions.maxwellian-relative-speed-rate-average",
    "scirel.collisions.atomic-hydrogen-collision-matrices",
    "scirel.collisions.molecular-hydrogen-collision-matrices",
    "scirel.collisions.atomic-hydrogen-omega-frequencies",
    "scirel.collisions.molecular-hydrogen-omega-frequencies",
)

_ATOMIC_MATRIX = dict(
    vr=np.array([0.5, 1.0]),
    vx=np.array([-1.0, 1.0]),
    Vr2pidVr=np.array([1.7671458676442586, 3.141592653589793]),
    dVx=np.array([2.0, 2.0]),
    Tnorm=1.0,
)


def _omega(**overrides):
    """Minimal two-axial-node carrier shared by the two Omega reducers."""
    values = dict(
        fH=np.array([[[1.0], [3.0]]]),
        nH=np.array([4.0]),
        Alpha_H_P=np.zeros((1, 2, 1)),
        Alpha_H_H2=np.zeros((1, 2, 1)),
        SIG_H_H=np.zeros((2, 2)),
        Vr2pidVr=np.ones(1),
        dVx=np.ones(2),
        vr=np.array([1.0]),
        vx=np.array([-1.0, 1.0]),
        Vth=1.0,
        vxi=np.array([0.0]),
        vxH2=np.array([0.0]),
        H_P_EL=False,
        H_H2_EL=False,
        H_H_EL=False,
    )
    values.update(overrides)
    return values


def _stopping(**overrides):
    values = dict(
        beam_mass_number=2.0,
        beam_energy_ev=1.0e5,
        birth_pitch_cosine=0.6,
        electron_density_m3=1.0e20,
        electron_temperature_ev=1.0e4,
        power_density_w_m3=1.0e6,
        electron_slowing_time_s=1.0e-3,
    )
    values.update(overrides)
    return values


CHANNELS = {
    "scirel.collisions.normalized-momentum": {
        "ValueError": lambda: normalized_momentum(x=[0.0], vnorm=-1.0, clight=1.0),
        "TypeError": lambda: normalized_momentum(x=[0.0], vnorm=object(), clight=1.0),
        "OverflowError": lambda: normalized_momentum(x=[0.0], vnorm=10**400, clight=1.0),
    },
    "scirel.collisions.thermal-electron-momentum": {
        "ValueError": lambda: thermal_electron_momentum(temperature_kev=-1.0, restmkev=511.0),
        "TypeError": lambda: thermal_electron_momentum(temperature_kev=1.0, restmkev=object()),
        "OverflowError": lambda: thermal_electron_momentum(temperature_kev=10**400, restmkev=511.0),
    },
    "scirel.collisions.fast-ion-stopping-increment": {
        "ValueError": lambda: evaluate_fast_ion_stopping_increment(
            **_stopping(beam_energy_ev=np.array([1.0, 2.0]), birth_pitch_cosine=np.ones(3))
        ),
        "TypeError": lambda: evaluate_fast_ion_stopping_increment(
            **_stopping(beam_mass_number=1.0 + 0.0j)
        ),
        "OverflowError": lambda: evaluate_fast_ion_stopping_increment(
            **_stopping(beam_mass_number=10**400)
        ),
        "RuntimeWarning": lambda: evaluate_fast_ion_stopping_increment(
            **_stopping(electron_density_m3=0.0)
        ),
    },
    "scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient": {
        "ValueError": lambda: evaluate_atomic_hydrogen_1s_radiative_recombination_rate(0.0),
        "ApplicabilityWarning": lambda: evaluate_atomic_hydrogen_1s_radiative_recombination_rate(
            5.0e4
        ),
    },
    "scirel.collisions.maxwellian-relative-speed-rate-average": {
        "ValueError": lambda: average_cross_section_over_maxwellian(
            particle_energy_ev=-1.0,
            particle_mass_amu=1.0,
            target_temperature_ev=1.0,
            target_mass_amu=1.0,
            vx=np.array([-1.0, 1.0]),
            vr=np.array([1.0]),
            tnorm_ev=1.0,
            cylindrical_volume=np.ones((1, 2)),
            cross_section_m2=lambda energy: np.ones_like(energy),
        ),
    },
    "scirel.collisions.atomic-hydrogen-collision-matrices": {
        "ValueError": lambda: assemble_atomic_hydrogen_collision_matrices(
            **{**_ATOMIC_MATRIX, "Vr2pidVr": np.array([1.0])}
        ),
    },
    "scirel.collisions.molecular-hydrogen-collision-matrices": {
        "ValueError": lambda: assemble_molecular_hydrogen_collision_matrices(
            **{**_ATOMIC_MATRIX, "Vr2pidVr": np.array([1.0])}
        ),
    },
    "scirel.collisions.atomic-hydrogen-omega-frequencies": {
        "ValueError": lambda: assemble_atomic_hydrogen_omega_frequencies(
            **_omega(nH=np.array([1.0]))
        ),
    },
    "scirel.collisions.molecular-hydrogen-omega-frequencies": {
        "ValueError": lambda: assemble_molecular_hydrogen_omega_frequencies(
            **{
                "fH2": np.array([[[1.0], [3.0]]]),
                "nH2": np.array([1.0]),
                "Alpha_H2_P": np.zeros((1, 2, 1)),
                "Alpha_H2_H": np.zeros((1, 2, 1)),
                "SIG_H2_H2": np.zeros((2, 2)),
                "Vr2pidVr": np.ones(1),
                "dVx": np.ones(2),
                "vr": np.array([1.0]),
                "vx": np.array([-1.0, 1.0]),
                "Vth": 1.0,
                "vxi": np.array([0.0]),
                "VxH": np.array([0.0]),
                "H2_P_EL": False,
                "H2_H_EL": False,
                "H2_H2_EL": False,
            }
        ),
    },
}


def _declared_channels(asset_id):
    document = json.loads((EXAMPLES / f"{asset_id}.json").read_text(encoding="utf-8"))
    names = set()
    for text in document["failure_semantics"].values():
        if isinstance(text, str):
            names.update(_DECLARED.findall(text))
    return names


def test_the_covered_set_is_explicit():
    assert set(CHANNELS) == set(COVERED)


@pytest.mark.parametrize("asset_id", COVERED)
def test_every_declared_channel_has_exactly_one_assertion(asset_id):
    assert set(CHANNELS[asset_id]) == _declared_channels(asset_id)


@pytest.mark.parametrize(
    "asset_id,channel",
    [(asset, channel) for asset, table in CHANNELS.items() for channel in sorted(table)],
    ids=lambda value: value.replace("scirel.collisions.", ""),
)
def test_the_assertion_really_produces_its_channel(asset_id, channel):
    call = CHANNELS[asset_id][channel]
    if channel.endswith("Warning"):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            call()
        assert caught, f"{asset_id} declares {channel} but the call emitted none"
        assert any(cls.__name__ == channel for cls in (item.category for item in caught))
        return
    with pytest.raises(Exception) as raised:
        call()
    assert type(raised.value).__name__ == channel, f"{asset_id}: {type(raised.value).__name__}"
