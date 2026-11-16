"""Independent evidence for the Frank--Egedal pressure assembly.

Asset: ``scirel.mirror.frank-egedal-pressure-state``.

The maintained test checks a two-by-two case whose expectation was written from
the same algebra.  The assembly is a finite sum of products, so the evidence here
is exact rational recomputation on dyadic inputs, which makes every comparison
bitwise:

``density = gas_density * r + hot_density_scale * r * h_n``
``electron_pressure = density * electron_temperature``
``p_parallel = gas_dynamic_pressure * r + electron_pressure + hot_pressure_scale * r * h_parallel``
``p_perp     = gas_dynamic_pressure * r + electron_pressure + hot_pressure_scale * r * h_perp``

Statements, each of which a wrong implementation cannot pass:

1. **Exact assembly** of all four outputs, including the shared gas and electron
   contributions, so a component that dropped the gas term or applied the
   electron pressure to only one component fails.
2. **Anisotropy is preserved exactly**: ``p_parallel - p_perp`` equals
   ``hot_pressure_scale * r * (h_parallel - h_perp)`` bit for bit, independent of
   the gas and electron contributions.
3. **The declared omission conventions**: omitting both density scales returns
   ``density is None``, an explicit zero scale returns a zero density array, and
   omitting the electron temperature returns ``None`` with no electron pressure.
4. **Linearity in the hot pressure scale**: doubling the scale doubles the
   hot-ion increment exactly.

Failure channels (contract ``failure_semantics``):

* ``invalid_input`` -- a non-2D, empty or shape-mismatched field, a negative
  field, a negative or nonfinite scale, and a non-finite assembled output each
  raise ``ValueError``;
* ``TypeError`` -- an object with no float conversion (a mapping) raises the
  native ``TypeError``, while a malformed string reaches ``float()`` and raises
  ``ValueError``; both are asserted;
* the contract declares no convergence or partial-result channel; the assertion
  is that the returned mapping has exactly the four declared keys.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.mirror import assemble_frank_egedal_pressure

PSI = np.zeros((2, 3))
RADIAL = np.array([[1.0, 0.5, 0.25], [2.0, 1.5, 0.75]])
HOT_PARALLEL = np.array([[2.0, 4.0, 8.0], [1.0, 2.0, 3.0]])
HOT_PERP = np.array([[3.0, 5.0, 9.0], [1.5, 2.5, 3.5]])
HOT_DENSITY = np.array([[4.0, 2.0, 1.0], [0.5, 1.0, 2.0]])

HOT_SCALE = 5.0
GAS_PRESSURE = 7.0
GAS_DENSITY = 11.0
HOT_DENSITY_SCALE = 13.0
ELECTRON_TEMPERATURE = 17.0


def _exact(radial, hot_parallel, hot_perp, hot_density):
    gas = Fraction(GAS_PRESSURE) * Fraction(radial)
    density = Fraction(GAS_DENSITY) * Fraction(radial) + Fraction(HOT_DENSITY_SCALE) * Fraction(
        radial
    ) * Fraction(hot_density)
    electron = density * Fraction(ELECTRON_TEMPERATURE)
    parallel = gas + electron + Fraction(HOT_SCALE) * Fraction(radial) * Fraction(hot_parallel)
    perpendicular = gas + electron + Fraction(HOT_SCALE) * Fraction(radial) * Fraction(hot_perp)
    return density, parallel, perpendicular


def _assemble(**overrides):
    arguments = dict(
        hot_pressure_scale=HOT_SCALE,
        gas_dynamic_pressure=GAS_PRESSURE,
        gas_dynamic_density=GAS_DENSITY,
        hot_density_scale=HOT_DENSITY_SCALE,
        electron_temperature=ELECTRON_TEMPERATURE,
    )
    arguments.update(overrides)
    return assemble_frank_egedal_pressure(
        PSI, RADIAL, HOT_PARALLEL, HOT_PERP, HOT_DENSITY, **arguments
    )


def test_exact_assembly_of_every_output():
    returned = _assemble()
    for node in range(RADIAL.size):
        radial = RADIAL.ravel()[node]
        density, parallel, perpendicular = _exact(
            radial, HOT_PARALLEL.ravel()[node], HOT_PERP.ravel()[node], HOT_DENSITY.ravel()[node]
        )
        assert float(returned["density"].ravel()[node]) == float(density)
        assert float(returned["p_parallel"].ravel()[node]) == float(parallel)
        assert float(returned["p_perp"].ravel()[node]) == float(perpendicular)
    np.testing.assert_array_equal(
        returned["electron_temperature"], np.full(RADIAL.shape, ELECTRON_TEMPERATURE)
    )


def test_anisotropy_is_preserved_exactly():
    returned = _assemble()
    for node in range(RADIAL.size):
        expected = (
            Fraction(HOT_SCALE)
            * Fraction(RADIAL.ravel()[node])
            * (Fraction(HOT_PARALLEL.ravel()[node]) - Fraction(HOT_PERP.ravel()[node]))
        )
        observed = returned["p_parallel"].ravel()[node] - returned["p_perp"].ravel()[node]
        assert float(observed) == float(expected)


def test_declared_omission_conventions():
    without_densities = assemble_frank_egedal_pressure(
        PSI,
        RADIAL,
        HOT_PARALLEL,
        HOT_PERP,
        HOT_DENSITY,
        hot_pressure_scale=HOT_SCALE,
        gas_dynamic_pressure=GAS_PRESSURE,
    )
    assert without_densities["density"] is None
    assert without_densities["electron_temperature"] is None
    # With no electron temperature the hot and gas terms alone remain.
    expected = np.array(
        [
            [
                GAS_PRESSURE * r + HOT_SCALE * r * h
                for r, h in zip(RADIAL.ravel(), HOT_PARALLEL.ravel())
            ]
        ]
    ).reshape(RADIAL.shape)
    np.testing.assert_array_equal(without_densities["p_parallel"], expected)

    zero_gas = _assemble(gas_dynamic_density=0.0)
    assert zero_gas["density"] is not None
    assert np.all(zero_gas["density"] == HOT_DENSITY_SCALE * RADIAL * HOT_DENSITY)


def test_the_hot_scale_enters_linearly():
    base = _assemble(hot_pressure_scale=HOT_SCALE)
    doubled = _assemble(hot_pressure_scale=2 * HOT_SCALE)
    increment_base = base["p_parallel"] - _assemble(hot_pressure_scale=0.0)["p_parallel"]
    increment_doubled = doubled["p_parallel"] - _assemble(hot_pressure_scale=0.0)["p_parallel"]
    np.testing.assert_array_equal(increment_doubled, 2.0 * increment_base)


def test_declared_keys_are_exactly_the_four_outputs():
    assert list(_assemble()) == ["p_parallel", "p_perp", "density", "electron_temperature"]


def test_invalid_input_channel_raises_value_error():
    with pytest.raises(ValueError, match="same-shape finite two-dimensional fields"):
        assemble_frank_egedal_pressure(PSI, RADIAL[0], HOT_PARALLEL, HOT_PERP, HOT_DENSITY)
    with pytest.raises(ValueError, match="same-shape finite two-dimensional fields"):
        assemble_frank_egedal_pressure(PSI, RADIAL[:-1], HOT_PARALLEL, HOT_PERP, HOT_DENSITY)
    with pytest.raises(ValueError, match="same-shape finite two-dimensional fields"):
        assemble_frank_egedal_pressure(
            PSI, RADIAL, np.full_like(RADIAL, np.nan), HOT_PERP, HOT_DENSITY
        )
    with pytest.raises(ValueError, match="same-shape finite two-dimensional fields"):
        assemble_frank_egedal_pressure(PSI, -RADIAL, HOT_PARALLEL, HOT_PERP, HOT_DENSITY)
    for scale in (-1.0, np.nan, np.inf):
        with pytest.raises(ValueError, match="finite and nonnegative"):
            _assemble(hot_pressure_scale=scale)
    with pytest.raises(ValueError, match="finite and nonnegative"):
        _assemble(electron_temperature=-5.0)
    # Finite inputs whose product leaves the finite range are rejected too.
    with pytest.raises(ValueError, match="non-finite fields"):
        assemble_frank_egedal_pressure(
            PSI,
            np.full_like(RADIAL, 1.0e300),
            np.full_like(RADIAL, 1.0e300),
            np.full_like(RADIAL, 1.0e300),
            HOT_DENSITY,
        )
    # A non-numeric object has no float conversion at all (TypeError); a
    # malformed string reaches float() and fails there (ValueError).  Both are
    # native conversion failures, and the contract names TypeError for the
    # former only.
    with pytest.raises(TypeError):
        _assemble(hot_pressure_scale={})
    with pytest.raises(ValueError):
        _assemble(hot_pressure_scale="not-a-scale")
