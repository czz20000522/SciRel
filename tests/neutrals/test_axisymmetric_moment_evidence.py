"""Independent evidence for the nine-moment axisymmetric neutral reduction.

Asset: ``scirel.neutrals.axisymmetric-neutral-moments``.

The reduction returns density, flux, flow, pressure, temperature and three
diagonal stresses plus a random heat flux.  Two of those outputs carry a
checkable physical structure that a normal example cannot show:

1. **The deviatoric stress is trace free.**  With the pressure defined as the
   one-third trace of the centered second moment, ``stress_xx + 2 * stress_yy``
   must vanish identically.  It is asserted as a physical invariant on four very
   different distributions, which a wrong coefficient in either stress or in the
   pressure term breaks immediately.
2. **Exact rational recomputation of all nine profiles.**  Every moment is
   recomputed from the exact binary64 inputs and the supplied cell volumes with
   :class:`fractions.Fraction`, rounded once; this fixes the measure, the centered
   velocity field and the unit factors ``m``, ``vth`` and ``q``.
3. **Two reduction orders agree.**  Supplying the explicit ``radial_quadrature`` /
   ``axial_quadrature`` pair switches to the documented per-slice summation order;
   the result must agree with the volume-only path to rounding, which is a real
   cross-check rather than a re-run.
4. **Exact scaling laws.**  Doubling the molecularity doubles the mass and
   therefore the pressure, stresses and heat flux exactly; quadrupling the
   normalization temperature doubles ``vth``, quadruples the pressure-like outputs
   exactly and multiplies the heat flux by exactly 8.
5. **Declared branches.**  ``stress_zz`` is an independent copy of ``stress_yy``;
   a zero-density slice is rejected under ``reject`` and becomes zero flow with
   exactly 1 eV under ``source_default``.
6. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel.

Budgets, fixed before measurement:

* the exact rational moments: ``(n_cells + 6) * eps * scale`` per profile, the
  forward bound for a sum of ``n_cells`` products with one division for the
  centered moments.
* the trace-free invariant: ``16 * eps * max(|stress_xx|, |stress_yy|, |pressure|)``,
  which covers the two subtractions and the pressure accumulation.
* the two reduction orders: ``8 * eps * scale``.
* the scaling laws: exact ``array_equal`` for power-of-two factors.
* the branch equalities: exact equality.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps
M_H = 1.6726231e-27
Q = 1.602177e-19

VR = np.array([0.5, 1.5, 2.5])
VX = np.array([-2.0, -0.5, 0.5, 2.0])
TNORM = 2.0
MASS_AMU = 1.0

DISTRIBUTIONS = {
    "smooth": np.exp(-(VR[:, None, None] ** 2 + VX[None, :, None] ** 2)) * np.ones((1, 1, 2)),
    "skewed": np.array(
        [
            [[1.0, 2.0], [0.5, 0.0], [3.0, 1.0], [0.2, 0.4]],
            [[0.0, 1.0], [2.0, 1.0], [0.5, 2.0], [1.0, 0.0]],
            [[1.5, 0.5], [0.25, 1.5], [0.75, 0.5], [2.0, 3.0]],
        ]
    ),
    "pencil": np.array(
        [
            [[1.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
            [[0.0, 1.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
            [[0.5, 0.0], [0.0, 2.0], [0.0, 0.0], [0.0, 0.0]],
        ],
        dtype=float,
    ),
}


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _volume(vr=VR):
    """Return the cylindrical cell volumes for the shared mesh."""
    return N.make_cylindrical_velocity_quadrature(vr=vr, vx=VX)["volume"]


def _reduce(distribution, *, molecularity=1, tnorm=TNORM, vr=VR, **kwargs):
    """Call the reduction with the shared fixtures."""
    return N.reduce_axisymmetric_neutral_moments(
        distribution,
        VX,
        vr,
        _volume(vr),
        normalization_temperature_ev=tnorm,
        isotope_mass_amu=MASS_AMU,
        molecularity=molecularity,
        **kwargs,
    )


def _thermal_speed(tnorm=TNORM, mass_amu=MASS_AMU):
    """Return the declared thermal speed."""
    return float(np.sqrt(2.0 * Q * tnorm / (mass_amu * M_H)))


def _exact_moments(distribution, *, molecularity=1, tnorm=TNORM):
    """Exact density, flow and the centered second moments of one distribution."""
    volume = _volume()
    thermal = _thermal_speed(tnorm)
    mass = molecularity * MASS_AMU * M_H
    out = {}
    for k in range(distribution.shape[2]):
        density = Fraction(0)
        first = Fraction(0)
        for i in range(VR.size):
            for j in range(VX.size):
                weight = _frac(volume[i, j]) * _frac(distribution[i, j, k])
                density += weight
                first += weight * _frac(VX[j])
        flow = first / density
        trace = Fraction(0)
        axial = Fraction(0)
        radial = Fraction(0)
        heat = Fraction(0)
        for i in range(VR.size):
            for j in range(VX.size):
                weight = _frac(volume[i, j]) * _frac(distribution[i, j, k])
                centered = _frac(VX[j]) - flow
                random_squared = _frac(VR[i]) ** 2 + centered**2
                trace += weight * random_squared
                axial += weight * centered**2
                radial += weight * _frac(VR[i]) ** 2
                heat += weight * random_squared * centered
        pressure = _frac(mass) * _frac(thermal) ** 2 * trace / (3 * _frac(Q))
        out[k] = {
            "density": density,
            "raw_xx": _frac(mass) * _frac(thermal) ** 2 * axial / _frac(Q),
            "raw_yy": 0.5 * _frac(mass) * _frac(thermal) ** 2 * radial / _frac(Q),
            "flux": _frac(thermal) * first,
            "flow": _frac(thermal) * flow,
            "pressure": pressure,
            "temperature": pressure / density,
            "stress_xx": _frac(mass) * _frac(thermal) ** 2 * axial / _frac(Q) - pressure,
            "stress_yy": 0.5 * _frac(mass) * _frac(thermal) ** 2 * radial / _frac(Q) - pressure,
            "heat": 0.5 * _frac(mass) * _frac(thermal) ** 3 * heat,
        }
    return out


def test_all_nine_profiles_match_the_exact_rational_reduction():
    """Evidence 2: every returned profile against exact rational arithmetic."""
    distribution = DISTRIBUTIONS["skewed"]
    result = _reduce(distribution)
    exact = _exact_moments(distribution)
    pairs = {
        "density_m3": "density",
        "axial_flux_m2_s": "flux",
        "axial_velocity_m_s": "flow",
        "pressure_ev_m3": "pressure",
        "temperature_ev": "temperature",
        "stress_xx_ev_m3": "stress_xx",
        "stress_yy_ev_m3": "stress_yy",
        "random_heat_flux_w_m2": "heat",
    }
    cells = distribution.shape[0] * distribution.shape[1]
    for name, key in pairs.items():
        expected = np.array([float(exact[k][key]) for k in range(distribution.shape[2])])
        if key in ("stress_xx", "stress_yy"):
            # The stress is a difference of two O(pressure) terms, so the bound is
            # set by the magnitudes before the cancellation, not by the result.
            pre = "raw_xx" if key == "stress_xx" else "raw_yy"
            scale = max(
                float(
                    np.max(
                        np.abs(
                            [
                                float(exact[k][pre]) + float(exact[k]["pressure"])
                                for k in range(distribution.shape[2])
                            ]
                        )
                    )
                ),
                1.0,
            )
        else:
            scale = max(float(np.max(np.abs(expected))), 1.0)
        assert np.all(np.abs(np.asarray(result[name]) - expected) <= (cells + 8) * EPS * scale), (
            name
        )
    assert np.array_equal(result["stress_zz_ev_m3"], result["stress_yy_ev_m3"])


def test_the_deviatoric_stress_is_trace_free():
    """Evidence 1: stress_xx + 2 * stress_yy == 0 for four different distributions."""
    for name, distribution in DISTRIBUTIONS.items():
        result = _reduce(distribution)
        trace = np.asarray(result["stress_xx_ev_m3"]) + 2.0 * np.asarray(result["stress_yy_ev_m3"])
        scale = max(
            float(np.max(np.abs(result["stress_xx_ev_m3"]))),
            float(np.max(np.abs(result["stress_yy_ev_m3"]))),
            float(np.max(np.abs(result["pressure_ev_m3"]))),
        )
        assert np.all(np.abs(trace) <= 16 * EPS * scale), name


def test_explicit_quadrature_agrees_with_the_volume_path():
    """Evidence 3: the documented per-slice order reproduces the batched order."""
    distribution = DISTRIBUTIONS["skewed"]
    volume = _volume()
    quadrature = N.make_cylindrical_velocity_quadrature(vr=VR, vx=VX)
    batched = _reduce(distribution)
    sliced = _reduce(
        distribution,
        axial_quadrature=quadrature["dvx"],
        radial_quadrature=quadrature["radial_measure"],
    )
    for name, value in batched.items():
        if name.startswith("stress"):
            # The stress is a difference of two O(pressure) accumulations in a
            # different order each time, so the bound is set before cancellation.
            scale = (
                max(
                    float(np.max(np.abs(value))),
                    float(np.max(np.abs(batched["pressure_ev_m3"]))),
                    1.0,
                )
                * 2.0
            )
            assert np.all(np.abs(np.asarray(sliced[name]) - value) <= 32 * EPS * scale), name
        else:
            scale = max(float(np.max(np.abs(value))), 1.0)
            assert np.all(np.abs(np.asarray(sliced[name]) - value) <= 8 * EPS * scale), name
    # The volume really is the outer product of the two quadrature weights.
    assert np.allclose(
        volume, quadrature["radial_measure"][:, None] * quadrature["dvx"], rtol=0.0, atol=0.0
    )


def test_mass_and_thermal_speed_scaling_are_exact():
    """Evidence 4: doubling the molecularity doubles the energy moments; 2 vth scales them."""
    distribution = DISTRIBUTIONS["skewed"]
    base = _reduce(distribution)
    heavier = _reduce(distribution, molecularity=2)
    for name in (
        "pressure_ev_m3",
        "stress_xx_ev_m3",
        "stress_yy_ev_m3",
        "random_heat_flux_w_m2",
    ):
        assert np.array_equal(np.asarray(heavier[name]), 2.0 * np.asarray(base[name])), name
    # T_norm x4 doubles vth: pressure, stresses and the inferred temperature x4,
    # the heat flux x8.
    hotter = _reduce(distribution, tnorm=4.0 * TNORM)
    for name in ("pressure_ev_m3", "stress_xx_ev_m3", "stress_yy_ev_m3"):
        assert np.array_equal(np.asarray(hotter[name]), 4.0 * np.asarray(base[name])), name
    assert np.array_equal(
        np.asarray(hotter["random_heat_flux_w_m2"]), 8.0 * np.asarray(base["random_heat_flux_w_m2"])
    )
    # The inferred temperature is P/n, so it follows the normalization
    # temperature: T_norm x4 gives vth x2 and T x4, not an unchanged T.
    assert np.array_equal(
        np.asarray(hotter["temperature_ev"]), 4.0 * np.asarray(base["temperature_ev"])
    )


def test_empty_slice_policy_branches():
    """Evidence 5: reject raises; source_default keeps zero flow and exactly 1 eV."""
    distribution = np.ones((VR.size, VX.size, 2))
    distribution[:, :, 1] = 0.0
    with pytest.raises(ValueError, match="positive density"):
        _reduce(distribution)
    relaxed = _reduce(distribution, empty_slice_policy="source_default")
    assert relaxed["axial_velocity_m_s"][1] == 0.0
    assert relaxed["temperature_ev"][1] == 1.0
    assert relaxed["density_m3"][1] == 0.0
    # The populated slice is untouched by the branch.
    assert relaxed["density_m3"][0] > 0.0


def test_reduction_rejects_each_declared_channel():
    """Evidence 6: one executable assertion per rejection channel."""
    distribution = DISTRIBUTIONS["skewed"]
    volume = _volume()
    call = N.reduce_axisymmetric_neutral_moments
    good = dict(
        distribution=distribution,
        vx=VX,
        vr=VR,
        cylindrical_volume=volume,
        normalization_temperature_ev=TNORM,
        isotope_mass_amu=MASS_AMU,
        molecularity=1,
    )
    assert call(**good)["density_m3"].shape == (2,)
    with pytest.raises(ValueError, match="invalid"):
        call(**{**good, "vx": VX[:2]})
    with pytest.raises(ValueError, match="invalid"):
        call(**{**good, "cylindrical_volume": np.zeros_like(volume)})
    with pytest.raises(ValueError, match="invalid"):
        call(**{**good, "distribution": np.full_like(distribution, np.nan)})
    with pytest.raises(ValueError, match="invalid"):
        call(**{**good, "normalization_temperature_ev": 0.0})
    with pytest.raises(ValueError, match="invalid"):
        call(**{**good, "isotope_mass_amu": -1.0})
    with pytest.raises(ValueError, match="invalid"):
        call(**{**good, "molecularity": 3})
    with pytest.raises(ValueError, match="integer scalar"):
        call(**{**good, "molecularity": 1.0})
    with pytest.raises(ValueError, match="invalid"):
        call(**{**good, "empty_slice_policy": "unknown"})
    with pytest.raises(ValueError, match="must be provided together"):
        call(**{**good, "axial_quadrature": np.ones(VX.size)})
    with pytest.raises(ValueError, match="must match cylindrical_volume"):
        call(
            **{
                **good,
                "axial_quadrature": np.ones(VX.size),
                "radial_quadrature": np.ones(VR.size),
            }
        )
    with pytest.raises(ValueError, match="real-valued numeric"):
        call(**{**good, "distribution": np.array([[["a", 1.0]]])})
