"""Atomic-hydrogen Balmer-alpha inversion to ground-state density and sources.

Task graph recovered from the saved KN1DPy ``原子氢JH-r系数B样条评价`` package
(source anchor ``KN1DPy/jh_related/N0_from_balmer_alpha.py:12-70``, as
recorded by the saved bundle's own extraction report), integrated as
:func:`solve_hydrogen_jh_balmer_alpha_ground_state_inversion`:

the diagnostic inversion of an observed Balmer-alpha volumetric emissivity
into the ground-state neutral density and the accompanying source terms, for
an explicit one-dimensional hydrogen profile.  The inversion consumes the
already-integrated SciRel assets

- ``scirel.collisions.hydrogen-jh-r-coefficient`` (r03 = ion 0, level 3 and
  r13 = ion 1, level 3),
- ``scirel.collisions.hydrogen-jh-s-coefficient`` (ionization rate
  coefficient),
- ``scirel.collisions.hydrogen-jh-alpha-coefficient`` (recombination rate
  coefficient),
- ``scirel.kinetic.hydrogen-saha-equilibrium-population`` (levels 1 and 3),

with the saved composition's frozen constants and operation order preserved
bit for bit: ``photon_rate = balmer / ((13.6057 * (0.25 - 1/9)) *
1.602177e-19)``, ``n3 = photon_rate / A_Balmer[0]``,
``n0 = (n3 / saha3 - r03) * saha1 / r13``,
``ionization = n0 * (density * s)``, ``recombination = density *
(density * alpha)`` and ``net_source = ionization - recombination``.

**The composed domain is the intersection of the bound assets' contracts, and
it is narrower than the saved composition.**  The saved inversion admits any
positive finite electron density and temperature; the bound r56 Saha asset
enforces its documented ``< 1e32`` scientific-domain limit, so this graph
declares density and temperature in ``(0, 1e32)``.  The observed emissivity
must be finite and strictly positive on both arms.  On the shared domain the
outputs are bit-identical to the saved composition (asserted by the
environment-gated replay); above ``1e32`` this graph fails closed where the
saved composition would return a value.  This declared narrowing is the r57
open expert question about the saved package's internal Saha copy (positive
finite only) versus the integrated r56 Saha asset (positive finite below
1e32).

**The r and alpha branches overwrite their spline density coordinate with the
source ``1e32`` sentinel** (the preserved r57 behavior of the bound assets),
so the returned inversion is exactly the saved one; the ``s`` branch consumes
the caller's density.  The s/alpha density-semantics split therefore carries
into the returned ``ionization_rate_m3_s``/``recombination_rate_m3_s``
pair, unchanged from the saved composition.

The packaged payload producer (source anchor ``create_jh_bscoef.py:11-248``)
is deferred: it materializes coefficient data, and admitting that data as a
SciRel artifact is the still-open r57 expert decision.  The ``jh_payload``
therefore stays caller-supplied here, exactly like the r57 coefficient
assets, and no table physics is claimed.

Evidence ceiling: this graph establishes the inversion against independent
recomputation from the bound SciRel assets, the round-trip recovery of a
known neutral density through the forward Balmer-alpha emission graph, the
composed-domain rejections, and -- in the environment-gated replay test --
bit-identical agreement with the saved KN1DPy inversion on the packaged
coefficient payload.  The saved bundle's strict D1 qualification has been
withdrawn; that replay is historical development evidence, not qualified-L1
provenance.  No test establishes the coefficient table or the Einstein
coefficients against an external atomic-physics reference: the saved package
records that residual as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

from scirel._validation import validate_jh_payload as _validate_jh_payload

__all__ = [
    "solve_hydrogen_jh_balmer_alpha_ground_state_inversion",
]

_ELEMENTARY_CHARGE_C = 1.602177e-19
_JH_ENERGY_FACTOR_EV = 13.6057 * (0.25 - 1.0 / 9.0)
_DENSITY_LIMIT_M3 = 1.0e32


def run_graph(inputs, *, asset_loader):
    """Compose the saved Balmer-alpha inversion from the bound SciRel assets."""
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a mapping")
    required = ("balmer_alpha_w_m3", "density_m3", "temperature_ev", "jh_payload")
    missing = sorted(name for name in required if name not in inputs)
    if missing:
        raise ValueError(f"inputs are missing {', '.join(missing)}")
    density = np.asarray(inputs["density_m3"], dtype=float)
    temperature = np.asarray(inputs["temperature_ev"], dtype=float)
    if (
        density.ndim != 1
        or temperature.ndim != 1
        or density.size == 0
        or density.shape != temperature.shape
        or not np.all(np.isfinite(density))
        or not np.all(np.isfinite(temperature))
        or np.any(density <= 0.0)
        or np.any(temperature <= 0.0)
    ):
        raise ValueError("density_m3 and temperature_ev must be finite positive same-shaped 1-D arrays")
    if np.any(density >= _DENSITY_LIMIT_M3) or np.any(temperature >= _DENSITY_LIMIT_M3):
        raise ValueError(
            "density_m3 and temperature_ev must stay below the 1e32 domain limit of the bound Saha asset"
        )
    balmer = np.asarray(inputs["balmer_alpha_w_m3"], dtype=float)
    if balmer.shape != density.shape or not np.all(np.isfinite(balmer)) or np.any(balmer <= 0.0):
        raise ValueError("balmer_alpha_w_m3 must be finite, positive, and shape-compatible")
    no_null = inputs.get("no_null", 1)
    if no_null != 1:
        raise ValueError("inverse radiation requires the explicit source no_null=1 contract")
    jh_payload = inputs["jh_payload"]
    # The saved inversion validates the full eight-field payload before any
    # evaluation (the bound s/alpha assets re-validate inside); enforce the
    # identical contract up front so the rejection order matches the saved arm.
    _validate_jh_payload(jh_payload)

    r_coefficient = asset_loader("scirel.collisions.hydrogen_jh_r_coefficient")
    s_coefficient = asset_loader("scirel.collisions.hydrogen_jh_s_coefficient")
    alpha_coefficient = asset_loader("scirel.collisions.hydrogen_jh_alpha_coefficient")
    saha_population = asset_loader("scirel.kinetic.hydrogen_saha_equilibrium_population")
    r03 = r_coefficient(
        density, temperature, 0, 3, jh_payload["DKnot"], jh_payload["TKnot"],
        int(jh_payload["order"]), jh_payload["LogR_BSCoef"], no_null=no_null,
    )
    r13 = r_coefficient(
        density, temperature, 1, 3, jh_payload["DKnot"], jh_payload["TKnot"],
        int(jh_payload["order"]), jh_payload["LogR_BSCoef"], no_null=no_null,
    )
    saha1 = saha_population(density, temperature, 1)
    saha3 = saha_population(density, temperature, 3)
    s_rate = s_coefficient(density, temperature, jh_payload, no_null=no_null)
    alpha_rate = alpha_coefficient(density, temperature, jh_payload, no_null=no_null)
    photon_rate = balmer / (_JH_ENERGY_FACTOR_EV * _ELEMENTARY_CHARGE_C)
    n3_population = photon_rate / np.asarray(jh_payload["A_Balmer"], dtype=float)[0]
    n0 = (n3_population / saha3 - r03) * saha1 / r13
    ionization = n0 * (density * s_rate)
    recombination = density * (density * alpha_rate)
    net_source = ionization - recombination
    result = {
        "ground_state_density_m3": n0,
        "photon_rate_m3_s": photon_rate,
        "n3_population_m3": n3_population,
        "ionization_rate_m3_s": ionization,
        "recombination_rate_m3_s": recombination,
        "net_source_m3_s": net_source,
    }
    if not all(np.all(np.isfinite(value)) for value in result.values()):
        raise ValueError("inverse Balmer-alpha evaluation produced non-finite output")
    return result


def solve_hydrogen_jh_balmer_alpha_ground_state_inversion(inputs=None, **kwargs):
    from scirel._composition import compose
    from scirel.collisions.hydrogen_jh_r_coefficient import evaluate_h_jh_r_coefficient as _dependency_0
    from scirel.collisions.hydrogen_jh_s_coefficient import evaluate_h_jh_s_coefficient as _dependency_1
    from scirel.collisions.hydrogen_jh_alpha_coefficient import (
        evaluate_h_jh_alpha_coefficient as _dependency_2,
    )
    from scirel.kinetic.hydrogen_saha_equilibrium_population import (
        evaluate_h_saha_equilibrium_population as _dependency_3,
    )
    return compose(
        run_graph,
        inputs,
        kwargs,
        {
            "asset_loader": {
                "scirel.collisions.hydrogen_jh_r_coefficient": _dependency_0,
                "scirel.collisions.hydrogen_jh_s_coefficient": _dependency_1,
                "scirel.collisions.hydrogen_jh_alpha_coefficient": _dependency_2,
                "scirel.kinetic.hydrogen_saha_equilibrium_population": _dependency_3,
            }
        },
    )
