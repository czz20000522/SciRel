"""Independent evidence for the circular-filament response matrices.

Asset: ``scirel.electromagnetism.green-response-matrices``.

The maintained test in ``tests/geometry/test_green_response_matrices.py``
compares against a SciPy quadrature at ``rtol=1e-11`` for one target table.
The evidence here uses ``_ideal_ring_reference`` (complement-free AgM elliptic
flux cross-certified against the Biot-Savart quadrature, and the two field
components obtained by differentiating the flux), which shares no algorithmic
step with either branch of the implementation.

Six statements:

1. **Every matrix entry against the reference.**  ``psi``, ``BR`` and ``BZ``
   entries are the weighted single-ring responses of the reference, so the
   matrix ordering convention (row = target, column = source, weight applied
   once) is decided by an outside computation rather than by reading the code.
2. **Implicit sources are the explicit unit-weight table.**  ``rzw=None`` must
   reproduce the explicit ``(R, Z, 1)`` call bitwise, including the zero
   diagonal; that is the documented "targets become unit-weight sources" rule.
3. **Exact self and inactive conventions.**  A source-target coincidence is an
   exact zero entry, a zero-radius row produces an all-zero column, and a
   repeated source row produces a bitwise identical column because the columns
   are independent by contract.
4. **Exact weight action.**  A power-of-two source weight scales its column
   bitwise, so the weight is applied once and to the right axis.
5. **Axis row from an elementary closed form.**  On the axis ``psi`` and ``BR``
   are exactly zero in that row and ``BZ`` matches
   ``1e-7 w 2 pi a^2 / (a^2 + (Z - z0)^2)^{3/2}``, which contains no elliptic
   integral at all.
6. **Contraction over the source axis.**  ``gpsi @ currents`` equals the
   weighted reference sum, checked with ``Fraction`` arithmetic on the
   binary64 values, so a transposed read of the source axis cannot pass.

Budgets are those of ``_ideal_ring_reference`` (``64 eps`` for ``psi``,
``128 eps`` for the fields), fixed there before this comparison was run.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import _ideal_ring_reference as reference
from scirel.electromagnetism import green_response_matrices

PSI_BUDGET = reference.PSI_BUDGET
FIELD_BUDGET = reference.FIELD_BUDGET
FIELDS = ("psi", "BR", "BZ")

TARGETS = np.array([[0.0, 0.35], [0.21, -0.4], [0.62, 0.17], [1.35, -0.6], [2.4, 0.9]])
SOURCES = np.array([[0.45, 0.0, 1.0], [0.8, -0.25, -2.0], [1.6, 0.55, 0.5], [0.0, 0.4, 3.0]])


def test_every_entry_matches_the_reference():
    """Evidence 1: all three matrices against the second source."""
    psi, br, bz = green_response_matrices(TARGETS, SOURCES)
    observed = dict.fromkeys(FIELDS, 0.0)
    for row, (radius, height) in enumerate(TARGETS):
        for column, (coil_radius, coil_z, weight) in enumerate(SOURCES):
            if coil_radius == 0.0 or weight == 0.0:
                # An inactive row contributes an exact zero column, asserted in
                # the dedicated test below; the reference does not model it.
                for name, got in zip(FIELDS, (psi, br, bz), strict=True):
                    assert float(got[row, column]) == 0.0, (name, row, column)
                continue
            expected = reference.response(radius, height, coil_radius, coil_z, weight)
            for name, got, want in zip(FIELDS, (psi, br, bz), expected, strict=True):
                want_value = float(want)
                got_value = float(got[row, column])
                if want_value == 0.0:
                    assert got_value == 0.0, (name, row, column, got_value)
                    continue
                deviation = abs(got_value - want_value) / abs(want_value)
                assert deviation <= (PSI_BUDGET if name == "psi" else FIELD_BUDGET), (
                    f"{name}[{row},{column}] deviates by {deviation:.3e} "
                    f"({got_value!r} against {want_value!r})"
                )
                observed[name] = max(observed[name], deviation)
    assert all(value > 0.0 for value in observed.values()), observed


def test_implicit_sources_equal_explicit_unit_weights():
    """Evidence 2: the documented implicit unit source table."""
    targets = np.array([[0.0, 0.55], [0.3, -0.2], [0.75, 0.4], [1.5, -0.85]])
    implicit = green_response_matrices(targets)
    explicit = green_response_matrices(targets, np.column_stack((targets, np.ones(len(targets)))))
    for name, implicit_values, explicit_values in zip(FIELDS, implicit, explicit, strict=True):
        np.testing.assert_array_equal(implicit_values, explicit_values, err_msg=name)
        # The zero diagonal is the declared discrete self convention; the
        # zero-radius node contributes nothing in either direction.
        np.testing.assert_array_equal(np.diag(implicit_values), 0.0, err_msg=name)
        np.testing.assert_array_equal(implicit_values[:, 0], 0.0, err_msg=name)
    # On the axis only the flux and the radial field vanish identically; the
    # axial field of a loop is nonzero there and must not be zeroed with them.
    np.testing.assert_array_equal(implicit[0][0, :], 0.0)
    np.testing.assert_array_equal(implicit[1][0, :], 0.0)
    assert np.all(implicit[2][0, 1:] != 0.0)


def test_inactive_rows_repeats_and_exact_weight_scaling():
    """Evidence 3 and 4: inactive sources, independent repeats, exact scaling."""
    targets = np.array([[0.25, 0.1], [0.7, -0.35], [1.4, 0.6]])
    base = green_response_matrices(targets, np.array([[0.5, 0.0, 1.0]]))
    repeated = green_response_matrices(
        targets, np.array([[0.5, 0.0, 1.0], [0.5, 0.0, 1.0], [0.0, 0.2, 5.0]])
    )
    for name, base_values, repeated_values in zip(FIELDS, base, repeated, strict=True):
        np.testing.assert_array_equal(repeated_values[:, 0], repeated_values[:, 1], err_msg=name)
        np.testing.assert_array_equal(repeated_values[:, 0], base_values[:, 0], err_msg=name)
        np.testing.assert_array_equal(repeated_values[:, 2], 0.0, err_msg=name)
    for power in (4, -9, 20):
        scaled = green_response_matrices(targets, np.array([[0.5, 0.0, float(2**power)]]))
        for name, base_values, scaled_values in zip(FIELDS, base, scaled, strict=True):
            np.testing.assert_array_equal(scaled_values, np.ldexp(base_values, power), err_msg=name)


def test_axis_row_matches_the_elementary_loop_field():
    """Evidence 5: the axis row against a source with no elliptic integral."""
    targets = np.array([[0.0, 0.0 + 0.42], [0.0, 0.0 - 1.1]])
    coil_radius, coil_z, weight = 0.65, 0.0, -1.5
    psi, br, bz = green_response_matrices(targets, np.array([[coil_radius, coil_z, weight]]))
    np.testing.assert_array_equal(psi[:, 0], 0.0)
    np.testing.assert_array_equal(br[:, 0], 0.0)
    for row, height in enumerate(targets[:, 1]):
        expected = (
            weight
            * 1e-7
            * 2.0
            * np.pi
            * coil_radius**2
            / (coil_radius**2 + (height - coil_z) ** 2) ** 1.5
        )
        deviation = abs(float(bz[row, 0]) - expected) / abs(expected)
        assert deviation <= FIELD_BUDGET, (float(bz[row, 0]), expected, deviation)


def test_contraction_over_the_source_axis_is_not_transposed():
    """Evidence 6: the source axis of the flux matrix, decided exactly."""
    currents = np.array([1.0, -0.25, 3.0, 0.5])
    psi, _, _ = green_response_matrices(TARGETS, SOURCES)
    contracted = psi @ currents
    singular = [
        green_response_matrices(TARGETS, SOURCES[index : index + 1])[0][:, 0]
        for index in range(len(SOURCES))
    ]
    for row in range(len(TARGETS)):
        expected = sum(
            (
                Fraction(float(singular[index][row])) * Fraction(float(currents[index]))
                for index in range(len(currents))
            ),
            Fraction(0),
        )
        difference = abs(Fraction(float(contracted[row])) - expected)
        scale = abs(expected) if expected != 0 else Fraction(1)
        assert difference <= scale * Fraction(4, 2**52), (row, float(difference))
    # A transposed read would contract along the target axis and give a
    # different length; the shape assertion is what makes that impossible.
    assert contracted.shape == (len(TARGETS),)
    assert psi.shape == (len(TARGETS), len(SOURCES))


def test_failure_channels_are_executable():
    """Failure matrix: one assertion per rejection channel of the contract."""
    targets = np.array([[0.3, 0.4]])
    with pytest.raises(ValueError, match="target and source coordinates/weights must be real"):
        green_response_matrices(np.array([[0.3 + 1j, 0.4]]))
    with pytest.raises(ValueError, match="target and source coordinates/weights must be real"):
        green_response_matrices(targets, np.array([[0.3 + 1j, 0.4, 1.0]]))
    with pytest.raises(ValueError, match="must be finite with non-negative cylindrical radius"):
        green_response_matrices(np.array([[-0.3, 0.4]]))
    with pytest.raises(ValueError, match="must be finite with non-negative cylindrical radius"):
        green_response_matrices(targets, np.array([[0.3, np.inf, 1.0]]))
    with pytest.raises(ValueError, match=r"rzw must have shape \(Nsource, 2\) or \(Nsource, 3\)"):
        green_response_matrices(targets, np.array([[0.3, 0.4, 1.0, 2.0]]))
    # Duplicate positive-radius implicit nodes: the unit-source set would be
    # ambiguous, so it is rejected instead of silently collapsed.
    with pytest.raises(ValueError, match="cannot be coincident"):
        green_response_matrices(np.array([[0.5, 0.0], [0.5, 0.0], [0.9, 0.0]]))
    # An unrepresentable column fails closed rather than returning ``inf``.
    with pytest.raises(FloatingPointError, match="not representable"):
        green_response_matrices(np.array([[0.4, 0.1 + 1e-9]]), np.array([[0.4, 0.1, 1e308]]))
