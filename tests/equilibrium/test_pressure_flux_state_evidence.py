"""Independent evidence for the pressure-flux spline state.

Asset: ``scirel.equilibrium.pressure-flux-state``.

The maintained tests compare the derivative with a hand-written expected array
for the contract example, which is the same spline artefact the implementation
produces.

The evidence here is an exact-rational reconstruction of the same interpolant
from its defining property.  With exactly four fit points and cubic degree, the
not-a-knot interpolating spline has no interior knot left, so it is the *unique*
cubic polynomial through the four (psi, pressure) pairs.  That polynomial is
computed here by Lagrange expansion in ``Fraction`` arithmetic -- no SciPy, no
knot vector, no linear solve in floating point -- and differentiated
symbolically.  The comparison therefore decides the fit itself rather than
whether SciPy agrees with SciPy.

Five statements:

1. **The derivative is the derivative of the unique interpolating cubic.**
   Compared at every unclipped grid point.  A wrong prefix (one point too many or
   too few), a different degree, or a shifted flux coordinate changes the
   polynomial and fails.
2. **The limiter bookkeeping is the physical one.**  ``limiter_index`` is the
   first exact-zero pressure position in increasing physical radius and
   ``psi_edge`` is the flux at that same position, not at the storage position.
3. **Clipping is exact.**  Entries with ``psi > psi_edge`` are exactly zero, and
   true mask entries are exactly zero, while the unclipped entries keep their
   spline value bit for bit.  This isolates the clipping from the fit.
4. **The serialized prefix is exactly the fitted prefix.**  It carries
   ``limiter_index + 1`` samples, degree three and the declared zero
   extrapolation, so a reader can rebuild the same polynomial.
5. **Descending radial storage is a relabelling.**  The same physical profile
   stored with decreasing R gives the same derivative value at every physical
   node once the columns are reversed.

Budgets, fixed before the comparison was run:

* statement 1 uses ``_RELATIVE_BUDGET = 256 eps``, derived from the conditioning
  of a cubic evaluation: four power terms plus three Horner multiplications and
  the derivative's own three terms, each rounded once, times the amplification of
  the PSD condition number of the four-node interpolation (about ten here);
* statements 2 to 5 are exact equalities (bitwise or exact integers).

Failure channels (contract ``failure_semantics``):

* ``invalid_input`` -- non-2D or shape-mismatched grids, nonfinite values, a
  missing or duplicated zero midplane row, duplicate midplane radii, a
  non-callable pressure, nonfinite or negative pressure, no exact zero boundary,
  a flux prefix shorter than four or not strictly increasing, and a non-boolean
  or wrong-shaped mask each raise ``ValueError``;
* ``runtime_failure`` -- the declared nonfinite-coefficient guard was **not**
  reached: a fit over strictly increasing finite flux with finite pressure
  produced finite coefficients for every fixture tried, so this channel is
  recorded as not-exercised rather than as covered;
* ``nonconvergence`` -- declared not applicable; the assertion is that the
  returned mapping carries no convergence field;
* ``partial_results`` -- every raise happens before the mapping is built, and
  ``pressure_of_psi`` stays a plain dict on success.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel.equilibrium.pressure_flux_state import build_pressure_flux_state

_EPS = math.ulp(1.0)
_RELATIVE_BUDGET = 256 * _EPS

R_AXIS = (0.2, 0.4, 0.6, 0.8, 1.0)
Z_AXIS = (-0.1, 0.0, 0.1)
MIDPLANE_ROW = 1
EDGE_RADIUS = 0.8


def _grids(reverse_radial=False):
    radii = np.array(R_AXIS[::-1] if reverse_radial else R_AXIS)
    r_grid, z_grid = np.meshgrid(radii, np.array(Z_AXIS))
    return r_grid, z_grid, r_grid**2


def _pressure(radius):
    return max(EDGE_RADIUS - radius, 0.0)


def _exact_cubic_derivative(samples):
    """Lagrange expansion of the unique cubic through (psi, pressure) samples.

    Returns a function of psi that evaluates the derivative in exact rational
    arithmetic, so it shares no step with the SciPy spline.
    """
    points = [(Fraction(psi), Fraction(pressure)) for psi, pressure in samples]
    coefficients = [Fraction(0)] * len(points)
    for index, (x_i, y_i) in enumerate(points):
        basis = [Fraction(1)]
        denominator = Fraction(1)
        for other, (x_j, _) in enumerate(points):
            if other == index:
                continue
            expanded = [Fraction(0)] * (len(basis) + 1)
            for power, value in enumerate(basis):
                expanded[power + 1] += value
                expanded[power] -= value * x_j
            basis = expanded
            denominator *= x_i - x_j
        for power, value in enumerate(basis):
            coefficients[power] += y_i * value / denominator

    def derivative(psi):
        x = Fraction(psi)
        return sum(
            Fraction(power) * coefficients[power] * x ** (power - 1)
            for power in range(1, len(coefficients))
        )

    return derivative


def _exact_samples():
    radii = sorted(R_AXIS)
    psi = [radius**2 for radius in radii]
    pressure = [_pressure(radius) for radius in radii]
    limit = pressure.index(0.0)
    return list(zip(psi[: limit + 1], pressure[: limit + 1]))


def test_derivative_equals_the_unique_interpolating_cubic():
    r_grid, z_grid, psi = _grids()
    result = build_pressure_flux_state(r_grid, z_grid, psi, _pressure)
    derivative = _exact_cubic_derivative(_exact_samples())
    edge = float(result["psi_edge"])
    for node in range(psi.size):
        flux = float(psi.ravel()[node])
        observed = float(result["pressure_derivative"][node])
        if flux > edge:
            assert observed == 0.0
            continue
        expected = derivative(flux)
        budget = _RELATIVE_BUDGET * abs(expected)
        assert abs(Fraction(observed) - expected) <= budget, (
            node,
            observed,
            float(expected),
        )


def test_limiter_index_and_edge_follow_physical_radius_not_storage_order():
    for reverse in (False, True):
        r_grid, z_grid, psi = _grids(reverse_radial=reverse)
        result = build_pressure_flux_state(r_grid, z_grid, psi, _pressure)
        # The zero-pressure radius is 0.8, which is the fourth radius from the
        # axis in physical order regardless of how the columns are stored.
        assert result["limiter_index"] == 3
        assert float(result["psi_edge"]) == EDGE_RADIUS**2


def test_clipping_and_mask_are_exact_zeros_without_disturbing_the_fit():
    r_grid, z_grid, psi = _grids()
    plain = build_pressure_flux_state(r_grid, z_grid, psi, _pressure)
    mask = np.zeros(psi.shape, dtype=bool)
    mask[MIDPLANE_ROW, 1] = True
    masked = build_pressure_flux_state(r_grid, z_grid, psi, _pressure, plasma_mask=mask)

    clipped = psi.ravel() > float(plain["psi_edge"])
    assert clipped.sum() == psi.shape[0]
    assert np.all(plain["pressure_derivative"][clipped] == 0.0)
    assert np.all(plain["pressure_derivative"][~clipped] != 0.0)

    assert masked["pressure_derivative"][mask.ravel()] == 0.0
    keep = ~mask.ravel()
    np.testing.assert_array_equal(
        masked["pressure_derivative"][keep], plain["pressure_derivative"][keep]
    )


def test_serialized_prefix_reconstructs_the_same_polynomial():
    r_grid, z_grid, psi = _grids()
    result = build_pressure_flux_state(r_grid, z_grid, psi, _pressure)
    serialized = result["pressure_of_psi"]
    assert type(serialized) is dict
    assert serialized["degree"] == 3
    assert serialized["extrapolation"] == "zeros"
    limit = int(result["limiter_index"])
    assert serialized["psi_samples"].size == limit + 1
    assert serialized["pressure_samples"].size == limit + 1
    expected_psi = [radius**2 for radius in sorted(R_AXIS)[: limit + 1]]
    expected_pressure = [_pressure(radius) for radius in sorted(R_AXIS)[: limit + 1]]
    np.testing.assert_array_equal(serialized["psi_samples"], np.array(expected_psi))
    np.testing.assert_array_equal(serialized["pressure_samples"], np.array(expected_pressure))

    # The stored samples alone determine the cubic, so the reader can rebuild it
    # from psi_samples/pressure_samples without the knot convention.  Rebuilding
    # from `knots`/`coefficients` would need SciPy's B-spline convention and is
    # deliberately not attempted here.
    rebuilt = _exact_cubic_derivative(
        list(zip(serialized["psi_samples"], serialized["pressure_samples"]))
    )
    edge = float(result["psi_edge"])
    for node in range(psi.size):
        flux = float(psi.ravel()[node])
        if flux > edge:
            continue
        expected = rebuilt(flux)
        observed = float(result["pressure_derivative"][node])
        assert abs(Fraction(observed) - expected) <= _RELATIVE_BUDGET * abs(expected)
    assert serialized["knots"].size > 0
    assert serialized["coefficients"].size > 0


def test_zero_currents_are_the_aligned_zero_vector():
    r_grid, z_grid, psi = _grids()
    result = build_pressure_flux_state(r_grid, z_grid, psi, _pressure)
    assert result["zero_currents"].shape == (psi.size,)
    assert np.all(result["zero_currents"] == 0.0)


def test_descending_storage_preserves_every_physical_node_value():
    ascending_r, ascending_z, ascending_psi = _grids()
    ascending = build_pressure_flux_state(ascending_r, ascending_z, ascending_psi, _pressure)
    descending_r, descending_z, descending_psi = _grids(reverse_radial=True)
    descending = build_pressure_flux_state(descending_r, descending_z, descending_psi, _pressure)
    np.testing.assert_array_equal(
        descending["pressure_derivative"].reshape(descending_psi.shape),
        ascending["pressure_derivative"].reshape(ascending_psi.shape)[:, ::-1],
    )


def test_invalid_input_channel_raises_value_error():
    r_grid, z_grid, psi = _grids()

    with pytest.raises(ValueError, match="two-dimensional"):
        build_pressure_flux_state(r_grid[0], z_grid[0], psi[0], _pressure)
    with pytest.raises(ValueError, match="must have shape"):
        build_pressure_flux_state(r_grid, z_grid[:-1], psi, _pressure)
    with pytest.raises(ValueError, match="finite"):
        build_pressure_flux_state(r_grid, z_grid, np.full_like(psi, np.nan), _pressure)
    with pytest.raises(ValueError, match="exactly one complete zero midplane row"):
        shifted_z = z_grid + 0.01
        build_pressure_flux_state(r_grid, shifted_z, psi, _pressure)
    with pytest.raises(ValueError, match="must be callable"):
        build_pressure_flux_state(r_grid, z_grid, psi, 0.5)

    duplicate_r = np.array([[0.2, 0.2, 0.6, 0.8, 1.0]] * 3)
    with pytest.raises(ValueError, match="midplane radii must be distinct"):
        build_pressure_flux_state(duplicate_r, z_grid, duplicate_r**2, _pressure)

    with pytest.raises(ValueError, match="finite nonnegative"):
        build_pressure_flux_state(r_grid, z_grid, psi, lambda radius: -1.0)
    with pytest.raises(ValueError, match="finite nonnegative"):
        build_pressure_flux_state(r_grid, z_grid, psi, lambda radius: np.nan)
    with pytest.raises(ValueError, match="exact zero-pressure boundary"):
        build_pressure_flux_state(r_grid, z_grid, psi, lambda radius: 1.0)

    # Three strictly increasing flux samples before the edge is one too few.
    with pytest.raises(ValueError, match="at least four points"):
        build_pressure_flux_state(r_grid, z_grid, psi, lambda radius: max(0.6 - radius, 0.0))
    # A flux that is not strictly increasing along physical radius.
    with pytest.raises(ValueError, match="strictly increasing"):
        flat_psi = np.zeros_like(psi)
        build_pressure_flux_state(r_grid, z_grid, flat_psi, _pressure)

    numeric_mask = np.zeros(psi.shape)
    with pytest.raises(ValueError, match="boolean"):
        build_pressure_flux_state(r_grid, z_grid, psi, _pressure, plasma_mask=numeric_mask)
    with pytest.raises(ValueError, match="same shape"):
        build_pressure_flux_state(
            r_grid, z_grid, psi, _pressure, plasma_mask=np.zeros((2, 2), dtype=bool)
        )


def test_returned_mapping_has_exactly_the_declared_keys():
    r_grid, z_grid, psi = _grids()
    result = build_pressure_flux_state(r_grid, z_grid, psi, _pressure)
    assert list(result) == [
        "pressure_derivative",
        "zero_currents",
        "psi_edge",
        "pressure_of_psi",
        "limiter_index",
    ]
    for forbidden in ("converged", "iterations", "status"):
        assert forbidden not in result
