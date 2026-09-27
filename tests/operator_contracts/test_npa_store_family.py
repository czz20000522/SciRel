"""r81 NPA store_npa leaf tests: saved probes, quirk pins, hardenings, composition.

Saved-package probes, source quirk pins, registered hardening
regressions, and the N8 composition witness for the NPA detection-chain
leaf integrated from the saved FIDASIM bundle:

- ``scirel.fusion.npa-energy-bin-increment``
  (``NPA能量通道通量增量``, src/fidasim.f90:10600-10724::store_npa)

The bundle records a native source microprobe for this relation
(``npa_store_flux_audit``): three real ``store_npa`` calls replayed the
tie-first ``minloc``, the nearest-bin and the passive/class-cap cases
with ``max_abs = 0``.
"""
import numpy as np
import pytest

from scirel.fusion import select_npa_energy_bin_increment


# ------------------- saved probes -------------------

def test_source_nearest_bin_tie_is_first_and_class_is_capped():
    result = select_npa_energy_bin_increment((3.0, 4.0, 0.0), 2.0, 1.0, (40.0, 60.0, 80.0), 2, 5, 3, 10.0)
    assert result == {
        "energy_kev": 50.0,
        "energy_bin_one_based": 1,
        "detector_index_one_based": 2,
        "class_index_one_based": 3,
        "spectral_flux_increment_per_kev": 0.5,
    }


def test_rejects_implicit_grid_or_index_contracts():
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment((1.0, 0.0, 0.0), 2.0, 1.0, (10.0,), 1, 1, 1, 1.0)
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment((1.0, 0.0, 0.0), 2.0, 1.0, (20.0, 10.0), 1, 1, 1, 1.0)
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment((1.0, 0.0, 0.0), 2.0, 1.0, (10.0, 20.0), 0, 1, 1, 1.0)


def test_energy_and_increment_follow_the_source_formulas():
    # energy = m * v2_to_E * dot(v, v); increment = flux / (c2 - c1)
    result = select_npa_energy_bin_increment(
        (0.0, 0.0, 5.0), 3.0, 2.0, (10.0, 40.0, 90.0, 160.0), 1, 1, 2, 8.0
    )
    assert result["energy_kev"] == pytest.approx(150.0)
    assert result["energy_bin_one_based"] == 4
    assert result["spectral_flux_increment_per_kev"] == pytest.approx(8.0 / 30.0)
    assert result["class_index_one_based"] == 1


# ------------------- source quirk pins -------------------

def test_first_adjacent_centers_define_de_not_the_local_width():
    # the source fixes dE = grid(2) - grid(1) even when the hit bins far
    # from the first two centers, and non-uniform grids keep that dE
    result = select_npa_energy_bin_increment(
        (1.0, 0.0, 0.0), 1.0, 100.0, (50.0, 60.0, 200.0, 400.0), 1, 1, 1, 20.0
    )
    assert result["energy_kev"] == pytest.approx(100.0)
    assert result["energy_bin_one_based"] == 2
    assert result["spectral_flux_increment_per_kev"] == pytest.approx(20.0 / 10.0)


def test_detector_index_is_passed_through_verbatim():
    result = select_npa_energy_bin_increment((1.0, 0.0, 0.0), 1.0, 1.0, (1.0, 2.0), 7, 1, 9, 1.0)
    assert result["detector_index_one_based"] == 7


def test_exact_tie_between_two_centers_selects_the_first():
    centers = (40.0, 60.0, 80.0)
    result = select_npa_energy_bin_increment((3.0, 4.0, 0.0), 2.0, 1.0, centers, 1, 1, 1, 4.0)
    assert result["energy_bin_one_based"] == 1
    # the tie is against the middle center from both sides; the first
    # channel wins over the equidistant later one
    down = select_npa_energy_bin_increment((3.0, 4.0, 0.0), 2.0, 1.0, centers, 1, 1, 1, 4.0)
    up = select_npa_energy_bin_increment((3.0, 4.0, 0.0), 2.0, 1.0, (0.0, 30.0, 60.0, 90.0, 120.0), 1, 1, 1, 4.0)
    assert down["energy_bin_one_based"] == 1
    assert up["energy_bin_one_based"] == 3


# ------------------- registered hardenings -------------------

def test_index_contracts_accept_np_integer_and_reject_bools_and_floats():
    result = select_npa_energy_bin_increment(
        (1.0, 0.0, 0.0), 1.0, 1.0, (1.0, 2.0), np.int64(2), np.int32(1), np.int64(4), 1.0
    )
    assert result["detector_index_one_based"] == 2 and result["class_index_one_based"] == 1
    for overrides in (
        {"detector_index_one_based": True},
        {"detector_index_one_based": 2.0},
        {"orbit_class_one_based": np.bool_(True)},
        {"orbit_class_one_based": 1.0},
        {"class_count": False},
        {"class_count": 3.0},
    ):
        with pytest.raises(ValueError):
            select_npa_energy_bin_increment(
                (1.0, 0.0, 0.0), 1.0, 1.0, (1.0, 2.0),
                overrides.get("detector_index_one_based", 1),
                overrides.get("orbit_class_one_based", 1),
                overrides.get("class_count", 1),
                1.0,
            )


def test_boolean_velocity_and_center_entries_are_rejected():
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment((True, 0.0, 0.0), 1.0, 1.0, (1.0, 2.0), 1, 1, 1, 1.0)
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment(
            (1.0, 0.0, 0.0), 1.0, 1.0, np.asarray([True, 2.0], dtype=object), 1, 1, 1, 1.0
        )


def test_mixed_container_and_object_booleans_are_rejected_before_coercion():
    # r81 pre-freeze review finding: a mixed list such as [True, 2.0]
    # becomes float64 at asarray time, so the post-conversion bool-dtype
    # check was skipped; the container pre-check must catch it. The same
    # applies to object-dtype velocity arrays.
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment((1.0, 0.0, 0.0), 1.0, 1.0, [True, 2.0], 1, 1, 1, 1.0)
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment(
            np.asarray([True, 0.0, 0.0], dtype=object), 1.0, 1.0, (1.0, 2.0), 1, 1, 1, 1.0
        )
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment(
            (1.0, 0.0, 0.0), 1.0, 1.0, np.asarray([True, 2.0, 3.0], dtype=object), 1, 1, 1, 1.0
        )


def test_boolean_and_nonfinite_scalars_are_rejected():
    for overrides in (
        {"beam_mass_amu": True},
        {"velocity_squared_to_energy_per_amu_kev_s2_cm_minus2": float("nan")},
        {"flux_neutrals_per_s": float("inf")},
    ):
        with pytest.raises(ValueError):
            select_npa_energy_bin_increment(
                (1.0, 0.0, 0.0),
                overrides.get("beam_mass_amu", 1.0),
                overrides.get("velocity_squared_to_energy_per_amu_kev_s2_cm_minus2", 1.0),
                (1.0, 2.0),
                1, 1, 1,
                overrides.get("flux_neutrals_per_s", 1.0),
            )


def test_overflowing_velocity_energy_fails_closed():
    # registered hardening: a huge finite velocity must not be silently
    # binned through an inf energy
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment(
            (1e200, 1e200, 0.0), 1e154, 1.0, (1.0, 2.0), 1, 1, 1, 1.0
        )


def test_degenerate_first_spacing_fails_closed_before_inf_increment():
    # r81 review finding: dE = 5e-324 - 0.0 is positive but the saved
    # arm returned increment = inf, violating the exact document's
    # finite-nonnegative promise
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment((0, 0, 0), 1, 1, (0.0, 5e-324), 1, 1, 1, 1.0)


def test_overflowing_first_spacing_fails_closed_instead_of_zero_increment():
    # r81 review finding: dE = 1e308 - (-1e308) overflows to inf and the
    # saved arm returned a silent 0.0 increment
    with pytest.raises(ValueError):
        select_npa_energy_bin_increment((0, 0, 0), 1, 1, (-1e308, 1e308), 1, 1, 1, 1.0)


# ------------------- N8 composition witness -------------------

def test_caller_accumulation_over_three_hits_reproduces_the_flux_record():
    # the N8 store_npa slice: the caller owns the (energy, detector,
    # class) accumulator and adds each returned increment; three hits on
    # one channel reproduce the per-(bin, class) partial sums without
    # this leaf touching any storage
    centers = (40.0, 60.0, 80.0)
    accumulator = np.zeros((3, 2, 3))
    hits = (
        ((3.0, 4.0, 0.0), 2.0, 1.0, 5, 10.0),
        ((0.0, 0.0, 5.0), 3.0, 2.0, 5, 4.0),
        ((1.0, 0.0, 0.0), 1.0, 100.0, 5, 6.0),
    )
    for velocity, mass, conversion, orbit_class, flux in hits:
        record = select_npa_energy_bin_increment(
            velocity, mass, conversion, centers, 1, orbit_class, 3, float(flux)
        )
        accumulator[record["energy_bin_one_based"] - 1, 0, record["class_index_one_based"] - 1] += record[
            "spectral_flux_increment_per_kev"
        ]
    assert accumulator[0, 0, 2] == pytest.approx(10.0 / 20.0)
    # orbit_class 5 is capped to class_count 3 for the later two hits,
    # so both increments land in the capped class column
    assert accumulator[2, 0, 2] == pytest.approx(4.0 / 20.0 + 6.0 / 20.0)
    assert accumulator[2, 0, 0] == 0.0 and accumulator[1, 0, 0] == 0.0
