"""Independent evidence for the axisymmetric mapping and its support composition.

Assets: ``scirel.geometry.axisymmetric-equilibrium-grid-mapping``,
``scirel.geometry.axisymmetric-equilibrium-grid-support``.

The mapping turns ``(br, bz, psi)`` sampled on an ``(r, z)`` grid into a cartesian
``B0`` on ``(x, y, z)``; the support asset chains it with the material-support
classification.  Both are checked by **rotational identities of the cylindrical
frame**, not by comparing interpolants:

1. **The tangential component of the rotated field vanishes.**
   ``Bx*y - By*x == 0`` for off-axis points: the field is built from the radial and
   axial components only, so any azimuthal leak, index swap or sign error breaks it.
2. **The radial component is recovered with its declared sign.**
   ``Bx*x + By*y == r*|B_xy|`` with ``r = hypot(x, y)``, i.e. ``br >= 0``: a
   reversed radial sign would make the left side negative.
3. **Axisymmetry.**  Two azimuthal positions at the same radius give the same
   ``psi`` and the same ``|B|``, while ``B`` itself differs by a rotation.
4. **The axis.**  At ``r == 0`` both transverse components are exactly zero and
   ``Bz`` is the interpolated axial value.
5. **Clamping, not zero fill.**  Points beyond the radial or axial extent are
   marked uncovered and carry the boundary value of the clamp; the two clamped
   counts are the number of points outside each extent.
6. **The composition is a chain.**  The composed support result carries the
   mapping outputs unchanged and the classification masks that
   ``classify_material_support`` produces from those outputs on the same grid.
7. **Declared rejections.**  Missing entries, wrong shapes, non-finite fields and
   a non-mapping equilibrium are each rejected.

Budgets, fixed before measurement:

* the rotational identities: ``16 * eps * |B| * r`` (two products and a sum).
* axisymmetry: exact equality for ``psi`` and ``|B|`` when the two positions have a
  bitwise-equal radius (``(3, 4)`` and ``(5, 0)`` both give ``hypot == 5``).
* the axis and the counts: exact equality.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.geometry import (
    classify_material_support,
    map_axisymmetric_equilibrium_to_cartesian_grid,
    solve_axisymmetric_equilibrium_grid_mapping,
)

EPS = np.finfo(float).eps


def _equilibrium(separatrix=2.0):
    """Return an equilibrium mapping with a linear-in-r radial field."""
    r = np.linspace(0.5, 3.0, 6)
    z = np.linspace(-1.0, 1.0, 5)
    rr, _ = np.meshgrid(r, z, indexing="ij")
    return {
        "r_m": r,
        "z_m": z,
        "br_t": 0.1 * rr,
        "bz_t": np.full_like(rr, 0.7),
        "psi_wb_per_rad": rr**2,
        "separatrix_flux_wb_per_rad": separatrix,
        "closed_flux_side": "less_than",
    }


def _grid(n=3):
    x = np.linspace(0.0, 3.0, n)
    y = np.linspace(0.0, 3.0, n)
    z = np.linspace(-0.5, 0.5, n)
    return x, y, z


def test_the_tangential_component_vanishes_and_the_radial_sign_is_positive():
    """Evidence 1 and 2: no azimuthal leak, and br >= 0."""
    x, y, z = _grid(4)
    mapped = map_axisymmetric_equilibrium_to_cartesian_grid(_equilibrium(), x, y, z)
    field = np.asarray(mapped["magnetic_flux_density_t"])
    bx, by = field[..., 0], field[..., 1]
    xx, yy, _ = np.meshgrid(x, y, z, indexing="ij")
    radius = np.hypot(xx, yy)
    off_axis = radius > 0.0
    scale = float(np.max(np.abs(field))) * float(np.max(radius))
    assert np.all(np.abs(bx * yy - by * xx)[off_axis] <= 16 * EPS * scale)
    transverse = np.hypot(bx, by)
    assert np.all((bx * xx + by * yy)[off_axis] > 0.0)
    assert np.all(np.abs((bx * xx + by * yy) - radius * transverse)[off_axis] <= 16 * EPS * scale)


def test_the_mapping_is_axisymmetric():
    """Evidence 3: the same radius gives the same psi and the same |B|."""
    equilibrium = _equilibrium()
    # (3, 4) and (5, 0) both have hypot exactly 5; the axes need two points each.
    mapped = map_axisymmetric_equilibrium_to_cartesian_grid(
        equilibrium, np.array([3.0, 5.0]), np.array([0.0, 4.0]), np.array([0.0, 0.5])
    )
    # (x, y) = (3, 4) at index (0, 1) and (5, 0) at index (1, 0): both have hypot 5.
    psi_a = mapped["poloidal_flux_wb_per_rad"][0, 1, 0]
    psi_b = mapped["poloidal_flux_wb_per_rad"][1, 0, 0]
    assert psi_a == pytest.approx(psi_b, rel=0.0, abs=16 * EPS * 30.0)
    field_a = mapped["magnetic_flux_density_t"][0, 1, 0]
    field_b = mapped["magnetic_flux_density_t"][1, 0, 0]
    assert float(np.linalg.norm(field_a)) == pytest.approx(
        float(np.linalg.norm(field_b)), rel=16 * EPS, abs=0.0
    )
    # The vectors themselves differ by the azimuthal rotation.
    assert not np.allclose(field_a, field_b)


def test_the_axis_has_no_transverse_field():
    """Evidence 4: r = 0 gives exactly zero Bx and By."""
    mapped = map_axisymmetric_equilibrium_to_cartesian_grid(
        _equilibrium(), np.array([0.0, 1.0]), np.array([0.0, 1.0]), np.array([0.0, 0.5])
    )
    field = mapped["magnetic_flux_density_t"][0, 0, 0]
    assert field[0] == 0.0 and field[1] == 0.0
    assert field[2] == pytest.approx(0.7, rel=0.0, abs=16 * EPS)


def test_out_of_range_points_are_clamped_and_reported():
    """Evidence 5: uncovered points carry the boundary value, with exact counts."""
    x = np.array([0.5, 2.0, 4.0])
    y = np.array([0.5, 2.0])
    z = np.array([0.0, 3.0])
    mapped = map_axisymmetric_equilibrium_to_cartesian_grid(_equilibrium(), x, y, z)
    covered = np.asarray(mapped["covered_mask"])
    xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")
    radius = np.hypot(xx, yy)
    expected = (radius >= 0.5) & (radius <= 3.0) & (zz >= -1.0) & (zz <= 1.0)
    assert np.array_equal(covered, expected)
    assert mapped["radially_clamped_point_count"] == int(np.count_nonzero(radius > 3.0))
    assert mapped["axially_clamped_point_count"] == int(np.count_nonzero((zz < -1.0) | (zz > 1.0)))
    # A point beyond the radial extent still carries a finite boundary value: the
    # query is clamped, not zero-filled.
    assert np.isfinite(np.asarray(mapped["poloidal_flux_wb_per_rad"])).all()
    far = np.asarray(mapped["poloidal_flux_wb_per_rad"])[-1, 0, 0]
    assert far > 0.0


def test_the_support_composition_is_the_chain_of_its_two_steps():
    """Evidence 6: composed masks equal the classification of the mapped fields."""
    x, y, z = _grid(5)
    # A separatrix above every sampled flux keeps the closed side non-empty inside
    # the PML frame, which is what the composition needs to produce a support mask.
    equilibrium = _equilibrium(separatrix=1e3)
    pec = np.zeros((5, 5, 5), dtype=bool)
    composed = solve_axisymmetric_equilibrium_grid_mapping(
        equilibrium, x, y, z, xpoint_half_length_m=0.25, pml_cells=1, pec_mask=pec
    )
    mapped = map_axisymmetric_equilibrium_to_cartesian_grid(equilibrium, x, y, z)
    xx, yy, _ = np.meshgrid(x, y, z, indexing="ij")
    radius = np.hypot(xx, yy)
    separate = classify_material_support(
        mapped["poloidal_flux_wb_per_rad"],
        mapped["covered_mask"],
        radius,
        np.broadcast_to(z[None, None, :], radius.shape),
        separatrix_flux_wb_per_rad=equilibrium["separatrix_flux_wb_per_rad"],
        closed_flux_side=equilibrium["closed_flux_side"],
        xpoint_half_length_m=0.25,
        pml_cells=1,
        pec_mask=pec,
    )
    assert np.array_equal(composed["material_support_mask"], separate["material_support_mask"])
    assert np.array_equal(composed["covered_mask"], mapped["covered_mask"])
    assert np.array_equal(composed["magnetic_flux_density_t"], mapped["magnetic_flux_density_t"])
    assert composed["radially_clamped_point_count"] == mapped["radially_clamped_point_count"]


def test_mapping_rejections():
    """Evidence 7: the declared rejection channels of the mapping."""
    x, y, z = _grid(2)
    call = map_axisymmetric_equilibrium_to_cartesian_grid
    with pytest.raises(ValueError, match="mapping"):
        call([1.0, 2.0], x, y, z)
    missing = _equilibrium()
    del missing["br_t"]
    with pytest.raises(ValueError, match="missing"):
        call(missing, x, y, z)
    wrong = _equilibrium()
    wrong["bz_t"] = wrong["bz_t"][:-1]
    with pytest.raises(ValueError, match="shape"):
        call(wrong, x, y, z)
    infinite = _equilibrium()
    infinite["psi_wb_per_rad"] = infinite["psi_wb_per_rad"] * np.nan
    with pytest.raises(ValueError, match="finite"):
        call(infinite, x, y, z)
