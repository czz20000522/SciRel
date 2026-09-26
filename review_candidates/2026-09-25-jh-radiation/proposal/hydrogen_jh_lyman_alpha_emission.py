"""Atomic-hydrogen Johnson-Hinnov Lyman-alpha line emission.

Task graph recovered from the saved KN1DPy ``原子氢JH-r系数B样条评价`` package
(source anchors ``KN1DPy/jh_related/lyman_alpha.py:42-64`` with the payload
anchor ``common/JH_Coef.py:5-29``, as recorded by the saved bundle's own
extraction report), integrated as :func:`solve_hydrogen_jh_lyman_alpha_emission`:

the Lyman-alpha photon rate and line emissivity of an explicit one-dimensional
hydrogen profile, composed from the already-integrated SciRel assets

- ``scirel.collisions.hydrogen-jh-r-coefficient`` (r02 = ion 0, level 2 and
  r12 = ion 1, level 2),
- ``scirel.kinetic.hydrogen-saha-equilibrium-population`` (levels 1 and 2),

with the saved composition's frozen constants and operation order preserved
bit for bit: ``photon_rate = A_Lyman[0] * (r02 + r12 * n0 / saha1) * saha2``
and ``emissivity = (13.6057 * (0.25 - 1/9)) * photon_rate * 1.602177e-19``.

**The composed domain is the intersection of the bound assets' contracts, and
it is narrower than the saved composition.**  The saved radiation callable
admits any positive finite electron density and temperature; the bound r56
Saha asset enforces its documented ``< 1e32`` scientific-domain limit, so this
graph declares density and temperature in ``(0, 1e32)``.  The neutral density
``n0`` is bounded ``< 1e32`` by the saved contract itself and is therefore
unchanged.  On the shared domain the outputs are bit-identical to the saved
composition (asserted by the environment-gated replay); above ``1e32`` this
graph fails closed where the saved composition would return a value.  This
declared narrowing is the r57 open expert question about the saved package's
internal Saha copy (positive finite only) versus the integrated r56 Saha
asset (positive finite below 1e32).

**The saved emissivity energy factor is preserved, not repaired.**  The saved
implementation multiplies both the Lyman-alpha and the Balmer-alpha photon
rate by ``13.6057 * (0.25 - 1/9)`` eV -- the n=3 -> 2 photon energy -- so the
returned Lyman emissivity carries that factor rather than the physical
n=1 -> 2 energy ``13.6057 * (1 - 1/4)`` eV.  The photon rate is unaffected.
Whether a successor should repair the Lyman factor is an open expert-review
question; no repair is claimed and the executed arithmetic is preserved.

The packaged payload producer (source anchor ``create_jh_bscoef.py:11-248``)
is deferred: it materializes coefficient data, and admitting that data as a
SciRel artifact is the still-open r57 expert decision.  The ``jh_payload``
therefore stays caller-supplied here, exactly like the r57 coefficient
assets, and no table physics is claimed.

Evidence ceiling: this graph establishes the composition against independent
recomputation from the bound SciRel assets and against an independent FITPACK
re-evaluation, the frozen constants, the composed-domain rejections, and --
in the environment-gated replay test -- bit-identical agreement with the
saved KN1DPy composition on the packaged coefficient payload.  The saved
bundle's strict D1 qualification has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.  No test
establishes the coefficient table or the Einstein coefficients against an
external atomic-physics reference: the saved package records that residual
as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

from scirel.diagnostics._jh_payload_validation import validate_jh_payload as _validate_jh_payload

__all__ = [
    "solve_hydrogen_jh_lyman_alpha_emission",
]

_ELEMENTARY_CHARGE_C = 1.602177e-19
_JH_ENERGY_FACTOR_EV = 13.6057 * (0.25 - 1.0 / 9.0)
_DENSITY_LIMIT_M3 = 1.0e32


def run_graph(inputs, *, asset_loader):
    """Compose the saved Lyman-alpha relation from the bound SciRel assets."""
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a mapping")
    required = ("density_m3", "temperature_ev", "n0_m3", "jh_payload")
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
    n0 = np.asarray(inputs["n0_m3"], dtype=float)
    if n0.shape != density.shape or not np.all(np.isfinite(n0)) or np.any(n0 <= 0.0) or np.any(n0 >= _DENSITY_LIMIT_M3):
        raise ValueError("n0_m3 must be finite, positive, and below the source null sentinel")
    no_null = inputs.get("no_null", 1)
    if no_null != 1:
        raise ValueError("radiation branches require the explicit source no_null=1 contract")
    jh_payload = inputs["jh_payload"]
    # The saved composition validates the full eight-field payload on every
    # radiation branch, including fields this branch does not numerically
    # consume; enforce the identical contract before any evaluation.
    _validate_jh_payload(jh_payload)

    r_coefficient = asset_loader("scirel.collisions.hydrogen_jh_r_coefficient")
    saha_population = asset_loader("scirel.kinetic.hydrogen_saha_equilibrium_population")
    r02 = r_coefficient(
        density, temperature, 0, 2, jh_payload["DKnot"], jh_payload["TKnot"],
        int(jh_payload["order"]), jh_payload["LogR_BSCoef"], no_null=no_null,
    )
    r12 = r_coefficient(
        density, temperature, 1, 2, jh_payload["DKnot"], jh_payload["TKnot"],
        int(jh_payload["order"]), jh_payload["LogR_BSCoef"], no_null=no_null,
    )
    saha1 = saha_population(density, temperature, 1)
    saha2 = saha_population(density, temperature, 2)
    photon_rate = np.asarray(jh_payload["A_Lyman"], dtype=float)[0] * (r02 + r12 * n0 / saha1) * saha2
    emissivity = _JH_ENERGY_FACTOR_EV * photon_rate * _ELEMENTARY_CHARGE_C
    # Source parity: the saved branch gates finiteness only.  A caller-supplied
    # A_Lyman[0] of zero returns zero rates (no emission) and a negative one
    # returns negative values; the sign convention is the caller's data
    # responsibility, not a graph-level rejection.
    if not np.all(np.isfinite(emissivity)) or not np.all(np.isfinite(photon_rate)):
        raise ValueError("Lyman-alpha evaluation produced non-finite output")
    return {"emissivity_w_m3": emissivity, "photon_rate_m3_s": photon_rate}


def solve_hydrogen_jh_lyman_alpha_emission(inputs=None, **kwargs):
    from scirel._composition import compose
    from scirel.collisions.hydrogen_jh_r_coefficient import evaluate_h_jh_r_coefficient as _dependency_0
    from scirel.kinetic.hydrogen_saha_equilibrium_population import (
        evaluate_h_saha_equilibrium_population as _dependency_1,
    )
    return compose(
        run_graph,
        inputs,
        kwargs,
        {
            "asset_loader": {
                "scirel.collisions.hydrogen_jh_r_coefficient": _dependency_0,
                "scirel.kinetic.hydrogen_saha_equilibrium_population": _dependency_1,
            }
        },
    )
