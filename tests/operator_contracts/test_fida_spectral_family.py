"""r80 FIDA spectral family tests: Doppler-Stark-Zeeman wavelengths + FIDA binning.

Saved-package probes, source quirk pins, registered hardening regressions,
and the N5 -> N6 combination witness (component wavelengths fed into the
store_fw_photons_at_chan binning boundary) for the two FIDA weight-chain
leaves integrated from the saved FIDASIM bundle:

- ``scirel.fusion.doppler-stark-zeeman-wavelengths``
  (``多普勒StarkZeeman谱线波长``, src/fidasim.f90:69-81,11891-11963)
- ``scirel.fusion.fida-wavelength-binning``
  (``FIDA权重谱线分箱``, src/fidasim.f90:12297-12347)
"""
import math

import numpy as np
import pytest

from scirel.fusion import bin_fida_los_components, doppler_stark_zeeman_wavelengths


# ------------------- doppler_stark_zeeman_wavelengths: saved probes -------------------

def test_zero_fields_return_the_doppler_shift_for_every_component():
    # saved probe: one cm/s -> m/s conversion only (v = 0.01 c along the sightline)
    result = doppler_stark_zeeman_wavelengths(
        (2.0, 0.0, 0.0), (2.99792458e8, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 0.0, 656.28, 15,
    )
    assert result == (656.28 * 1.01,) * 15


def test_electric_only_lyman_components_are_finite_and_symmetric_in_wavenumber():
    # saved probe: the three Lyman Stark components stay ordered and the
    # wavenumber shifts are symmetric around the unperturbed component
    result = doppler_stark_zeeman_wavelengths(
        (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 1.0e5, 121.57, 3,
    )
    assert len(result) == 3
    assert all(math.isfinite(value) for value in result)
    assert result[1] == 121.57
    inverse_wavelength = tuple(1.0 / (value * 1.0e-9) for value in result)
    assert result[0] > result[1] > result[2]
    assert abs(inverse_wavelength[0] + inverse_wavelength[2] - 2.0 * inverse_wavelength[1]) / inverse_wavelength[1] < 1.0e-14


def test_zero_field_because_shifts_are_degenerate_across_all_balmer_components():
    # with no electromagnetic field the 15 Balmer components collapse onto
    # the single Doppler center (q0 = q1 = 0); the component table only
    # separates them when a field is present
    result = doppler_stark_zeeman_wavelengths(
        (2.0, 0.0, 0.0), (2.99792458e8, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 0.0, 656.28, 15,
    )
    assert len(set(result)) == 1


def test_moving_electric_field_magnitude_is_e_plus_v_cross_b():
    # source E' = ||E + v x B||: v = (0, v, 0) cm/s, B along +z gives a
    # purely x-directed moving field of magnitude v[m/s] * B
    speed = 1.0e7  # cm/s -> 1.0e5 m/s
    magnitude = doppler_stark_zeeman_wavelengths(
        (1.0, 0.0, 0.0), (0.0, speed, 0.0), (0.0, 0.0, 1.0), 2.0,
        (1.0, 0.0, 0.0), 0.0, 656.28, 3,
    )
    reference = doppler_stark_zeeman_wavelengths(
        (1.0, 0.0, 0.0), (0.0, speed, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 0.0, 656.28, 3,
    )
    assert magnitude != reference  # the B term must enter through E'


def test_sightline_normalization_is_internal():
    unit = doppler_stark_zeeman_wavelengths(
        (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 0.0, 656.28, 3,
    )
    scaled = doppler_stark_zeeman_wavelengths(
        (5.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 0.0, 656.28, 3,
    )
    assert unit == scaled


# ------------------- doppler_stark_zeeman_wavelengths: registered hardenings -------------------

def test_invalid_sightline_and_transition_counts_fail_closed():
    for kwargs in (
        {"sightline_to_head": (0.0, 0.0, 0.0), "component_count": 3},
        {"sightline_to_head": (1.0, 0.0, 0.0), "component_count": 4},
    ):
        with pytest.raises(ValueError):
            doppler_stark_zeeman_wavelengths(
                kwargs["sightline_to_head"], (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
                (1.0, 0.0, 0.0), 0.0, 656.28, kwargs["component_count"],
            )


def test_component_count_must_be_a_genuine_integer():
    # registered hardening: the saved arm's `not in (3, 15)` accepted
    # whole-number floats such as 3.0
    with pytest.raises(ValueError):
        doppler_stark_zeeman_wavelengths(
            (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
            (1.0, 0.0, 0.0), 0.0, 656.28, 3.0,
        )
    with pytest.raises(ValueError):
        doppler_stark_zeeman_wavelengths(
            (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
            (1.0, 0.0, 0.0), 0.0, 656.28, True,
        )
    np_accept = doppler_stark_zeeman_wavelengths(
        (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 0.0, 656.28, np.int64(3),
    )
    assert len(np_accept) == 3


def test_nonfinite_inputs_are_rejected():
    for kwargs in (
        {"ion_velocity_cm_s": (float("nan"), 0.0, 0.0)},
        {"ion_velocity_cm_s": (0.0, float("inf"), 0.0)},
        {"magnetic_unit_vector": (float("nan"), 0.0, 1.0)},
        {"magnetic_magnitude_t": float("nan")},
        {"electric_unit_vector": (1.0, 0.0, float("inf"))},
        {"electric_magnitude_v_m": float("nan")},
        {"reference_wavelength_nm": float("nan")},
        {"sightline_to_head": (1.0, float("nan"), 0.0)},
    ):
        with pytest.raises(ValueError):
            doppler_stark_zeeman_wavelengths(
                kwargs.get("sightline_to_head", (1.0, 0.0, 0.0)),
                kwargs.get("ion_velocity_cm_s", (0.0, 0.0, 0.0)),
                kwargs.get("magnetic_unit_vector", (0.0, 0.0, 1.0)),
                kwargs.get("magnetic_magnitude_t", 0.0),
                kwargs.get("electric_unit_vector", (1.0, 0.0, 0.0)),
                kwargs.get("electric_magnitude_v_m", 0.0),
                kwargs.get("reference_wavelength_nm", 656.28),
                3,
            )


def test_scalar_magnitudes_reject_booleans():
    # registered hardening: True must not numerify to 1.0 T or 1.0 V/m
    with pytest.raises(ValueError):
        doppler_stark_zeeman_wavelengths(
            (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), True,
            (1.0, 0.0, 0.0), 0.0, 656.28, 3,
        )
    with pytest.raises(ValueError):
        doppler_stark_zeeman_wavelengths(
            (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
            (1.0, 0.0, 0.0), True, 656.28, 3,
        )


def test_reference_wavelength_must_be_positive():
    # registered hardening: the saved arm accepted nonpositive references
    for reference in (0.0, -656.28):
        with pytest.raises(ValueError):
            doppler_stark_zeeman_wavelengths(
                (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
                (1.0, 0.0, 0.0), 0.0, reference, 3,
            )


# ------------------- bin_fida_los_components: saved probes -------------------

def test_source_floor_bins_and_factor_are_conservative():
    result = bin_fida_los_components(
        wavelength_nm=[650.0, 650.5, 651.999999],
        component_intensity=[1.0, 2.0, 3.0],
        lambdamin_nm=650.0,
        lambdamax_nm=652.0,
        nlambda=4,
    )
    assert result["bin_index_zero_based"].tolist() == [0, 1, 3]
    assert result["accepted_component_count"] == 3
    assert np.sum(result["weight_bins"]) == pytest.approx(6.0 / (4.0 * np.pi * 0.5))


def test_out_of_range_components_are_dropped_but_keep_their_index():
    result = bin_fida_los_components(
        wavelength_nm=[649.0, 650.25, 653.0],
        component_intensity=[1.0, 2.0, 4.0],
        lambdamin_nm=650.0,
        lambdamax_nm=652.0,
        nlambda=2,
    )
    assert result["accepted_component_count"] == 1
    assert np.sum(result["weight_bins"]) == pytest.approx(2.0 / (4.0 * np.pi))
    # the out-of-range raw bin indices are retained for boundary audit
    assert result["bin_index_zero_based"].tolist() == [-1, 0, 3]


def test_upper_edge_is_exclusive():
    # lambdamax falls into the discarded bin >= nlambda (half-open interval)
    result = bin_fida_los_components(
        wavelength_nm=[652.0, 652.0, 652.0], component_intensity=[1.0, 1.0, 1.0],
        lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=4,
    )
    assert result["accepted_component_count"] == 0
    assert result["bin_index_zero_based"].tolist() == [4, 4, 4]


def test_invalid_component_and_bin_contracts_fail_closed():
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0], component_intensity=[1.0, 1.0],
            lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=2,
        )
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0, 651.5], component_intensity=[1.0, -1.0, 1.0],
            lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=2,
        )
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0, 651.5], component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=652.0, lambdamax_nm=650.0, nlambda=2,
        )
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0, 651.5], component_intensity=[1.0, float("nan"), 1.0],
            lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=2,
        )


def test_nlambda_genuine_integer_contract_is_pinned():
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0, 651.5], component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=True,
        )
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0, 651.5], component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=0,
        )
    result = bin_fida_los_components(
        wavelength_nm=[650.0, 651.0, 651.5], component_intensity=[1.0, 1.0, 1.0],
        lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=np.int64(4),
    )
    assert result["weight_bins"].shape == (4,)


def test_boolean_entries_are_rejected_in_both_forms():
    # registered hardening: the saved arm's np.asarray(..., dtype=float)
    # silently coerced True to 1.0 in both the bool-dtype and the mixed
    # object form
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=np.array([True, True, True]),
            component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=4,
        )
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=np.asarray([True, 1.0, 1.0], dtype=object),
            component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=4,
        )
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0, 651.5],
            component_intensity=np.array([False, True, False]),
            lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=4,
        )
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0, 651.5],
            component_intensity=np.asarray([False, True, False], dtype=object),
            lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=4,
        )


def test_boolean_interval_bounds_are_rejected():
    # registered hardening
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0, 651.5], component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=True, lambdamax_nm=652.0, nlambda=4,
        )
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[650.0, 651.0, 651.5], component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=650.0, lambdamax_nm=np.bool_(True), nlambda=4,
        )


# ------------------- N5 -> N6 combination witness -------------------

def test_balmer_components_flow_through_the_binning_boundary():
    # the FIDA weight chain slice: the Doppler-Stark-Zeeman component
    # wavelengths (N5) are placed into the FIDA wavelength bins (N6,
    # store_fw_photons_at_chan) with equal component intensities; the
    # conservation factor applies exactly to the accepted components
    wavelengths = doppler_stark_zeeman_wavelengths(
        (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (0.0, 0.0, 1.0), 2.0e5, 656.28, 15,
    )
    out = bin_fida_los_components(
        wavelength_nm=list(wavelengths),
        component_intensity=[1.0] * 15,
        lambdamin_nm=650.0,
        lambdamax_nm=660.0,
        nlambda=20,
    )
    assert out["accepted_component_count"] == 15
    assert out["weight_bins"].shape == (20,)
    assert np.sum(out["weight_bins"]) == pytest.approx(15.0 / (4.0 * np.pi * 0.5))
    # every accepted bin index is inside the range and the components
    # stay inside the Stark-split band around the Doppler center
    accepted = out["bin_index_zero_based"][:15]
    assert np.all(accepted >= 0) and np.all(accepted < 20)
    assert min(wavelengths) > 650.0 and max(wavelengths) < 660.0


def test_lyman_triplet_partially_outside_the_window_is_split():
    # a narrow window keeps only the central Lyman component; the shifted
    # pair is dropped without changing the other bins
    wavelengths = doppler_stark_zeeman_wavelengths(
        (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 1.0e5, 121.57, 3,
    )
    out = bin_fida_los_components(
        wavelength_nm=list(wavelengths),
        component_intensity=[1.0, 2.0, 4.0],
        lambdamin_nm=121.5699,
        lambdamax_nm=121.5701,
        nlambda=2,
    )
    assert out["accepted_component_count"] == 1
    assert np.sum(out["weight_bins"]) == pytest.approx(2.0 / (4.0 * np.pi * 1.0e-4))


# ------------------- r80-v2 repairs (read-only expert review findings) -------------------

def test_overflowing_sightline_keeps_the_nonzero_doppler_shift():
    # r80-v1 defect: sqrt(1e308^2 + 1e308^2) overflowed to inf and the
    # direction collapsed to zero, silently returning the bare 656.28 and
    # dropping the nonzero Doppler shift the declared relation requires
    result = doppler_stark_zeeman_wavelengths(
        (1e308, 1e308, 0.0), (1e5, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 0.0, 656.28, 3,
    )
    expected = 656.28 * (1.0 + (1e5 * 0.01 * (0.5 ** 0.5)) / 2.99792458e8)
    assert len(set(result)) == 1  # zero fields keep the components degenerate
    assert result[0] == pytest.approx(expected, rel=1e-12)
    assert result[0] != 656.28


def test_extreme_field_magnitudes_fail_closed_instead_of_returning_nan():
    # r80-v1 defect: B = 1e308 overflowed the quadrature and the saved
    # arm's arithmetic produced nan components for finite inputs
    with pytest.raises(ValueError):
        doppler_stark_zeeman_wavelengths(
            (1.0, 0.0, 0.0), (1e5, 0.0, 0.0), (0.0, 0.0, 1.0), 1e308,
            (1.0, 0.0, 0.0), 0.0, 656.28, 3,
        )
    with pytest.raises(ValueError):
        doppler_stark_zeeman_wavelengths(
            (1.0, 0.0, 0.0), (1e5, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
            (1.0, 0.0, 0.0), 1e308, 656.28, 3,
        )


def test_boolean_vector_entries_are_rejected():
    # r80-v1 defect: the vector boolean check ran after the dtype=float
    # conversion and was dead code; bool vectors silently numerified
    with pytest.raises(ValueError):
        doppler_stark_zeeman_wavelengths(
            (True, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
            (1.0, 0.0, 0.0), 0.0, 656.28, 3,
        )
    with pytest.raises(ValueError):
        doppler_stark_zeeman_wavelengths(
            (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), np.array([True, False, False]), 1.0,
            (1.0, 0.0, 0.0), 0.0, 656.28, 3,
        )
    with pytest.raises(ValueError):
        doppler_stark_zeeman_wavelengths(
            (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
            np.asarray([True, 0.0, 0.0], dtype=object), 1.0, 656.28, 3,
        )
    # note: np.array([True, 0.0, 0.0]) is float64 at construction time, so
    # a bool hidden in a mixed numpy array is not detectable at the port;
    # the contract covers the container, bool-dtype and object forms


def test_degenerate_bin_width_fails_closed_as_declared():
    # r80-v1 defect: dlambda = 5e-324 / 2 underflowed to 0.0 and the
    # saved arm raised ZeroDivisionError instead of the declared ValueError
    with pytest.raises(ValueError) as excinfo:
        bin_fida_los_components(
            wavelength_nm=[0.0, 0.0, 0.0],
            component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=0.0,
            lambdamax_nm=5e-324,
            nlambda=2,
        )
    assert not isinstance(excinfo.value, ZeroDivisionError)


def test_overflowing_bin_width_fails_closed():
    # the window width overflows to inf and the normalization factor
    # would silently become zero
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[0.0, 0.0, 0.0],
            component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=-1e308,
            lambdamax_nm=1e308,
            nlambda=2,
        )


def test_subnormal_bin_width_fails_closed_before_inf_factor():
    # r80-v1 defect (second review reproduction): dlambda = 1e-320 is
    # positive and finite, but 1/(4*pi*dlambda) overflows to inf and the
    # weight bins silently carried inf despite the document's finite
    # factor/bins promise
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[0.0, 0.0, 0.0],
            component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=0.0,
            lambdamax_nm=1e-320,
            nlambda=1,
        )


def test_unrepresentable_bin_index_fails_closed_instead_of_int64_sentinel():
    # r80-v1 defect (second review reproduction): (1e308 - 650)/0.5
    # overflowed to inf and the int cast wrote the int64 sentinel
    # -9223372036854775808 as the component's "raw index"
    with pytest.raises(ValueError):
        bin_fida_los_components(
            wavelength_nm=[1e308, 650.0, 651.0],
            component_intensity=[1.0, 1.0, 1.0],
            lambdamin_nm=650.0,
            lambdamax_nm=652.0,
            nlambda=4,
        )
    # a large-but-representable out-of-range index is still kept raw
    out = bin_fida_los_components(
        wavelength_nm=[1e6, 650.0, 651.0],
        component_intensity=[1.0, 1.0, 1.0],
        lambdamin_nm=650.0,
        lambdamax_nm=652.0,
        nlambda=4,
    )
    assert out["bin_index_zero_based"].tolist()[0] == 1998700
    assert out["accepted_component_count"] == 2
