"""Independent evidence for the equilibrium diagnostic synthesis.

Asset: ``scirel.diagnostics.equilibrium-synthesis-diagnostics``.

Evidence sources:

1. **Hand-computed bilinear sampling.**  The diagnostic is a composition: it
   samples ``equilibrium['psi']`` and the profile fields at caller points and
   applies one declared unit factor.  For fields affine in ``R`` and ``Z`` the
   bilinear sample is *exactly* the affine value at the point, so the expected
   output is written out by hand instead of taken from any sampler.
2. **The unit factor is a declared algebraic rule, checked on both branches.**
   ``raw_psi`` multiplies by one; ``magnetic_flux`` multiplies by ``2*pi`` when
   ``psi_unit == 'Wb/rad'`` and by one when it is ``'Wb'``.  The two branches are
   separated so a factor applied on the wrong branch is visible, and the reported
   ``units`` labels are checked against the declared target unit.
3. **Unit-label gating.**  A profile whose declared unit differs from
   ``equilibrium['profile_units']`` is rejected, and pressures are required to be
   ``Pa`` while density is required to be ``m^-3``; temperature accepts ``K``,
   ``eV`` or ``J`` with no conversion.  These are contract statements, so they are
   tested as rejections and as pass-throughs, not with tolerances.

Budgets: the affine samples and the ``2*pi`` factor are exact up to one rounding
of the factor, so ``64 * eps`` of the local scale.

Not established here (recorded as a limitation on the contract): whether
``Wb/rad -> Wb`` by ``2*pi`` is the physically correct convention for a given
consumer.  That is a modelling decision about single-turn linked flux, and the
repository cannot settle it; what *is* established is that the implementation and
the contract agree on which branch multiplies by ``2*pi``.  Also not established:
whether a caller's ``points`` are physically meaningful sampling locations.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.diagnostics import synthesize_equilibrium_diagnostics

EPS = np.finfo(float).eps

R_GRID = np.array([[0.0, 1.0, 2.0]] * 3)
Z_GRID = np.array([[-1.0] * 3, [0.0] * 3, [1.0] * 3])


def _equilibrium(psi_unit, scale=1.0):
    """An affine psi field and an affine density profile, both exactly sampled."""
    psi = scale * (2.0 * R_GRID - 3.0 * Z_GRID + 0.5)
    density = 1.0e19 + 2.0e18 * R_GRID + 5.0e17 * Z_GRID
    return {
        "psi": psi,
        "psi_unit": psi_unit,
        "profiles": {"density": density},
        "profile_units": {"density": "m^-3"},
    }


POINTS = np.array([[0.5, -0.25], [1.5, 0.5], [0.0, 1.0]])


def _affine_expectation(points):
    return 2.0 * points[:, 0] - 3.0 * points[:, 1] + 0.5


def test_magnetic_flux_from_wb_per_rad_multiplies_by_two_pi():
    """Evidence 2, first branch: the declared ``Wb/rad`` conversion."""
    equilibrium = _equilibrium("Wb/rad")
    result = synthesize_equilibrium_diagnostics(
        equilibrium=equilibrium,
        R=R_GRID,
        Z=Z_GRID,
        observations={"flux_loops": {"points": POINTS, "quantity": "magnetic_flux", "unit": "Wb"}},
    )
    expected = 2.0 * np.pi * _affine_expectation(POINTS)
    got = np.asarray(result["flux_loops"])
    assert np.max(np.abs(got - expected) / np.abs(expected)) <= 64.0 * EPS
    assert result["units"]["flux_loops"] == "Wb"


def test_magnetic_flux_from_wb_is_unchanged():
    """Evidence 2, second branch: a ``Wb`` source must not pick up the factor."""
    equilibrium = _equilibrium("Wb")
    result = synthesize_equilibrium_diagnostics(
        equilibrium=equilibrium,
        R=R_GRID,
        Z=Z_GRID,
        observations={"flux_loops": {"points": POINTS, "quantity": "magnetic_flux", "unit": "Wb"}},
    )
    expected = _affine_expectation(POINTS)
    got = np.asarray(result["flux_loops"])
    assert np.max(np.abs(got - expected) / np.abs(expected)) <= 64.0 * EPS
    # The branch really differs from the other one.
    assert not np.allclose(got, 2.0 * np.pi * expected)


def test_raw_psi_keeps_its_unit_and_value():
    equilibrium = _equilibrium("Wb/rad")
    result = synthesize_equilibrium_diagnostics(
        equilibrium=equilibrium,
        R=R_GRID,
        Z=Z_GRID,
        observations={"flux_loops": {"points": POINTS, "quantity": "raw_psi", "unit": "Wb/rad"}},
    )
    expected = _affine_expectation(POINTS)
    assert np.max(np.abs(np.asarray(result["flux_loops"]) - expected)) <= 64.0 * EPS
    assert result["units"]["flux_loops"] == "Wb/rad"


def test_profile_channels_are_sampled_bilinearly_and_keep_their_units():
    density = 1.0e19 + 2.0e18 * R_GRID + 5.0e17 * Z_GRID
    equilibrium = {
        "psi": _equilibrium("Wb/rad")["psi"],
        "psi_unit": "Wb/rad",
        "profiles": {"density": density, "electron_temperature": 300.0 + 10.0 * R_GRID},
        "profile_units": {"density": "m^-3", "electron_temperature": "eV"},
    }
    result = synthesize_equilibrium_diagnostics(
        equilibrium=equilibrium,
        R=R_GRID,
        Z=Z_GRID,
        observations={
            "thomson": {
                "points": POINTS,
                "density": {"unit": "m^-3"},
                "electron_temperature": {"unit": "eV"},
            }
        },
    )
    expected_density = 1.0e19 + 2.0e18 * POINTS[:, 0] + 5.0e17 * POINTS[:, 1]
    expected_temperature = 300.0 + 10.0 * POINTS[:, 0]
    assert (
        np.max(
            np.abs(np.asarray(result["thomson"]["density"]) - expected_density) / expected_density
        )
        <= 64.0 * EPS
    )
    assert (
        np.max(np.abs(np.asarray(result["thomson"]["electron_temperature"]) - expected_temperature))
        <= 64.0 * EPS
    )
    assert result["units"]["thomson"] == {
        "density": "m^-3",
        "electron_temperature": "eV",
    }


def test_only_requested_outputs_are_returned():
    result = synthesize_equilibrium_diagnostics(
        equilibrium=_equilibrium("Wb"),
        R=R_GRID,
        Z=Z_GRID,
        observations={"flux_loops": {"points": POINTS, "quantity": "magnetic_flux", "unit": "Wb"}},
    )
    assert "flux_loops" in result
    assert "thomson" not in result


def test_rejection_channels_are_bound_to_their_contract():
    equilibrium = _equilibrium("Wb/rad")
    valid_flux = {"points": POINTS, "quantity": "magnetic_flux", "unit": "Wb"}
    for call, fragment in [
        (
            lambda: synthesize_equilibrium_diagnostics(
                equilibrium=equilibrium, R=R_GRID, Z=Z_GRID, observations={}
            ),
            "nonempty",
        ),
        (
            lambda: synthesize_equilibrium_diagnostics(
                equilibrium=equilibrium,
                R=R_GRID,
                Z=Z_GRID,
                observations={"flux_loops": {"points": POINTS, "unit": "Wb"}},
            ),
            "quantity",
        ),
        (
            lambda: synthesize_equilibrium_diagnostics(
                equilibrium=equilibrium,
                R=R_GRID,
                Z=Z_GRID,
                observations={"flux_loops": {**valid_flux, "unit": "Wb/rad"}},
            ),
            "Wb",
        ),
        (
            lambda: synthesize_equilibrium_diagnostics(
                equilibrium=equilibrium,
                R=R_GRID,
                Z=Z_GRID,
                observations={"flux_loops": {**valid_flux, "turns": 2}},
            ),
            "unsupported",
        ),
        (
            lambda: synthesize_equilibrium_diagnostics(
                equilibrium=equilibrium,
                R=R_GRID,
                Z=Z_GRID,
                observations={"flux_loops": {**valid_flux, "points": np.array([[9.0, 9.0]])}},
            ),
            "outside",
        ),
        (
            lambda: synthesize_equilibrium_diagnostics(
                equilibrium={**equilibrium, "psi_unit": "T*m^2"},
                R=R_GRID,
                Z=Z_GRID,
                observations={"flux_loops": valid_flux},
            ),
            "Wb/rad or Wb",
        ),
    ]:
        with pytest.raises(ValueError) as caught:
            call()
        assert fragment in str(caught.value), (fragment, str(caught.value))
