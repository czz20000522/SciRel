"""Bounded historical replay of the r60 neutral-moment family against the
saved KN1DPy implementations, when present.

The saved operator bundles sit in the re-review archive
``KN1DPy-631d0bf1``: KN1DPy's strict D1 qualification has been withdrawn, so
this replay is bounded historical development evidence about the arithmetic,
not qualified-L1 provenance and not expert approval.  The tests are skipped
unless ``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root, and every
saved implementation file is pinned by SHA-256 so different byte streams can
never masquerade as the compared arms.

Imports of the saved tree are read-only: the harness runs with
``PYTHONDONTWRITEBYTECODE=1`` and the test session asserts zero writes by
construction (modules are loaded from their exact byte-pinned paths).
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import (
    aggregate_elastic_regeneration_source,
    assemble_neutral_total_collision_frequency,
    assemble_simple_charge_exchange_source,
    compute_thermal_speed_m_s,
    normalize_incoming_neutral_boundary,
    normalize_spatial_source_shape,
    reduce_atomic_scattered_sources,
    reduce_axisymmetric_neutral_moments,
    reduce_generation_density,
    reduce_molecular_scattered_sources,
    sum_elastic_frequency_channels,
)

_PINNED = {
    "热速度标度换算": "9867b3fbc30317e519d0b1ed62d885c8550d00337d889542b5653c267b82fda8",
    "中性分布密度归约": "d11b3ece9c168f6e19df37a14aec5e46adf279f379f6bf835b0e26271cb8776c",
    "轴对称中性分布矩归约": "02b58e9447e632d071877b15da871e07a5032654d6d79db8e2945dc8e3f9987e",
    "弹性频率通道求和": "7058571007eeeb435610369b3db7ed6b7b4757ba49619cd24a605e59e1f769d8",
    "入射中性边界通量归一化": "7251bb29eca994683134966abac0a7f731baf557202db1d19fc798f70474768e",
    "空间源形状归一化": "83b2d7b9e860d8ee57cef6b5332b97fe31a6269a861c6e2a6df42506bfd18629",
    "中性总损失碰撞频率组装": "69c25bd24033e3d7cdbaf2cdbc3becadd35e09a6149f8a1bfea4534c9e35bcbd",
    "原子双通道散射源归约": "6fe5d850c7aef5c07f8c5996dc65948a6ba35f1ea10e120dcb6fd28ed61ff159",
    "分子三通道散射源归约": "4b17a8e6a15d2c7ebf4e0fdc58db7e7b81af8c0139687182dbe8c5a9e6542898",
    "弹性重生散射源聚合": "8957adc7a5f0cd11cbdc6b3c6738057adbab660285c38fb2da490db09f7919c0",
    "简化电荷交换散射源": "b4962366c43c308aa0ca8e047d00fb34ce2756f1db025e14a77339b1de50770f",
}

_LOADED = {}


def _saved(package):
    root = os.environ.get("SCIREL_KN1DPY_REVIEW_ROOT")
    if not root:
        pytest.skip("SCIREL_KN1DPY_REVIEW_ROOT is not set; source-free contract tests remain active")
    if package in _LOADED:
        return _LOADED[package]
    source = Path(root) / "operators" / package / "scientific_operator.py"
    assert source.is_file(), f"saved operator bundle missing: {source}"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == _PINNED[package], f"saved operator bytes drifted from the compared arm: {source}"
    spec = importlib.util.spec_from_file_location(f"kn1dpy_r60_{len(_LOADED)}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LOADED[package] = module
    return module


def _fixture(seed=42):
    rng = np.random.default_rng(seed)
    vr = np.linspace(0.1, 1.0, 6)
    vx = np.linspace(-1.0, 1.0, 7)
    volume = (vr[:, None] * np.ones_like(vx[None, :])) * 0.2
    speed_squared = vr[:, None] ** 2 + vx[None, :] ** 2
    distribution = rng.random((6, 7, 5)) * np.exp(-speed_squared)[:, :, None]
    return rng, distribution, vx, vr, volume


def _assert_same(saved_value, new_value):
    if isinstance(saved_value, dict):
        assert set(saved_value) == set(new_value)
        for key in saved_value:
            np.testing.assert_array_equal(saved_value[key], new_value[key])
    elif isinstance(saved_value, tuple):
        for saved_item, new_item in zip(saved_value, new_value):
            if isinstance(saved_item, np.ndarray):
                np.testing.assert_array_equal(saved_item, new_item)
            else:
                assert saved_item == new_item
    else:
        np.testing.assert_array_equal(saved_value, new_value)


def test_thermal_speed_matches_the_saved_implementation_exactly():
    saved = _saved("热速度标度换算")
    for temperature, mass in ((1.0, 1.0), (5.0, 2.0), (0.3, 3.0)):
        _assert_same(
            saved.compute_thermal_speed_m_s(temperature, mass),
            compute_thermal_speed_m_s(temperature, mass),
        )


def test_generation_density_matches_the_saved_implementation_exactly():
    saved = _saved("中性分布密度归约")
    rng, distribution, _, _, volume = _fixture(3)
    dx = rng.random(7) + 0.1
    _assert_same(saved.reduce_generation_density(distribution, volume, dx),
                 reduce_generation_density(distribution, volume, dx))
    radial = np.full(6, 0.2)
    _assert_same(saved.reduce_generation_density(distribution, radial, dx),
                 reduce_generation_density(distribution, radial, dx))
    uniform = np.repeat(radial[:, None], 7, axis=1)
    _assert_same(saved.reduce_generation_density(distribution, uniform, dx),
                 reduce_generation_density(distribution, uniform, dx))


def test_axisymmetric_moments_match_the_saved_implementation_exactly():
    saved = _saved("轴对称中性分布矩归约")
    _, distribution, vx, vr, volume = _fixture(4)
    kw = dict(normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2)
    _assert_same(saved.reduce_axisymmetric_neutral_distribution(distribution, vx, vr, volume, **kw),
                 reduce_axisymmetric_neutral_moments(distribution, vx, vr, volume, **kw))
    axial_weight = np.full(vx.size, 0.1)
    radial_weight = np.full(vr.size, 0.2)
    volume2 = radial_weight[:, None] * axial_weight[None, :]
    _assert_same(
        saved.reduce_axisymmetric_neutral_distribution(
            distribution, vx, vr, volume2, axial_quadrature=axial_weight, radial_quadrature=radial_weight, **kw
        ),
        reduce_axisymmetric_neutral_moments(
            distribution, vx, vr, volume2, axial_quadrature=axial_weight, radial_quadrature=radial_weight, **kw
        ),
    )
    zeroed = distribution.copy()
    zeroed[:, :, 2] = 0.0
    _assert_same(
        saved.reduce_axisymmetric_neutral_distribution(zeroed, vx, vr, volume, empty_slice_policy="source_default", **kw),
        reduce_axisymmetric_neutral_moments(zeroed, vx, vr, volume, empty_slice_policy="source_default", **kw),
    )


def test_elastic_channel_sum_matches_the_saved_implementation_exactly():
    saved = _saved("弹性频率通道求和")
    rng = np.random.default_rng(5)
    channels = [rng.random(8), rng.random(8), rng.random(8)]
    _assert_same(saved.sum_elastic_frequency_channels(channels),
                 sum_elastic_frequency_channels(channels))


def test_boundary_flux_normalization_matches_the_saved_implementation_exactly():
    saved = _saved("入射中性边界通量归一化")
    rng = np.random.default_rng(6)
    shape = rng.random((4, 9))
    volume = rng.random((4, 9))
    vx = np.linspace(-2.0, 2.0, 9)
    for target in (1.0e18, -5.0e17):
        _assert_same(
            saved.normalize_incoming_neutral_boundary(shape, vx, volume, 3000.0, target),
            normalize_incoming_neutral_boundary(shape, vx, volume, 3000.0, target),
        )


def test_spatial_source_shape_matches_the_saved_implementation_exactly():
    saved = _saved("空间源形状归一化")
    rng = np.random.default_rng(7)
    profile = rng.random(9)
    coordinates = np.linspace(0.0, 1.0, 9)
    _assert_same(saved.normalize_spatial_source_shape(profile, coordinates),
                 normalize_spatial_source_shape(profile, coordinates))


def test_total_collision_frequency_matches_the_saved_implementation_exactly():
    saved = _saved("中性总损失碰撞频率组装")
    rng = np.random.default_rng(8)
    base = rng.random(4)
    elastic = rng.random(4)
    diameter = rng.random(4)
    charge_exchange = rng.random((5, 3, 4))
    vr = np.linspace(0.1, 1.0, 5)
    vx = np.linspace(-1.0, 1.0, 3)
    _assert_same(
        saved.assemble_neutral_total_collision_frequency(vr, vx, base, elastic, diameter, charge_exchange),
        assemble_neutral_total_collision_frequency(vr, vx, base, elastic, diameter, charge_exchange),
    )
    _assert_same(
        saved.assemble_neutral_total_collision_frequency(
            vr, vx, base, elastic, diameter, charge_exchange_enabled=False
        ),
        assemble_neutral_total_collision_frequency(
            vr, vx, base, elastic, diameter, charge_exchange_enabled=False
        ),
    )


def test_scattered_source_reductions_match_the_saved_implementations_exactly():
    saved_atomic = _saved("原子双通道散射源归约")
    saved_molecular = _saved("分子三通道散射源归约")
    rng = np.random.default_rng(9)
    fields = [rng.random((3, 4, 5)) for _ in range(3)]
    _assert_same(saved_atomic.reduce_atomic_scattered_sources(fields[0], fields[1]),
                 reduce_atomic_scattered_sources(fields[0], fields[1]))
    _assert_same(
        saved_molecular.reduce_molecular_scattered_sources(fields[0], fields[1], fields[2]),
        reduce_molecular_scattered_sources(fields[0], fields[1], fields[2]),
    )
    signed = -fields[1]
    _assert_same(saved_atomic.reduce_atomic_scattered_sources(fields[0], signed),
                 reduce_atomic_scattered_sources(fields[0], signed))


def test_elastic_regeneration_matches_the_saved_implementation_exactly():
    saved = _saved("弹性重生散射源聚合")
    rng = np.random.default_rng(10)
    freqs = {"h": rng.random(5), "h2": rng.random(5)}
    dists = {"h": rng.random((3, 4, 5)), "h2": rng.random((3, 4, 5))}
    _assert_same(saved.aggregate_elastic_regeneration_source(freqs, dists),
                 aggregate_elastic_regeneration_source(freqs, dists))


def test_simple_charge_exchange_source_matches_the_saved_implementation_exactly():
    saved = _saved("简化电荷交换散射源")
    rng = np.random.default_rng(11)
    target = rng.random((4, 3, 5))
    alpha = rng.random((4, 3, 5))
    previous = rng.random((4, 3, 5))
    weight = rng.random((4, 3))
    dx = rng.random(3) + 0.1
    _assert_same(saved.assemble_simple_charge_exchange_source(target, alpha, previous, weight, dx),
                 assemble_simple_charge_exchange_source(target, alpha, previous, weight, dx))


def test_extreme_but_valid_inputs_fail_closed_on_nonfinite_outputs():
    """Pre-review regression (applies to every aggregation-style asset): the
    saved arms do not gate their outputs, so extreme-but-valid inputs can
    overflow to non-finite results; every r60 asset fail-closes instead,
    per the exact documents' finite-output contracts."""
    big = np.array([[[1e308]]])
    with pytest.raises(ValueError, match="not finite"):
        reduce_generation_density(
            np.full((2, 2, 2), 1e308), np.full((2, 2), 1e300), np.array([1e308, 1e308])
        )
    with pytest.raises(ValueError, match="not finite"):
        assemble_neutral_total_collision_frequency(
            np.array([1e308]), np.array([0.0]), np.array([0.0]), np.array([0.0]),
            np.array([1e-308]), charge_exchange_enabled=False,
        )
    with pytest.raises(ValueError, match="not finite"):
        reduce_atomic_scattered_sources(big, big)
    with pytest.raises(ValueError, match="not finite"):
        reduce_molecular_scattered_sources(big, big, big)
    with pytest.raises(ValueError, match="not finite"):
        aggregate_elastic_regeneration_source({"a": np.array([1e308])}, {"a": np.array([[[1e308]]])})
    with pytest.raises(ValueError, match="not finite"):
        assemble_simple_charge_exchange_source(
            big, big, big, np.array([[1e308]]), np.array([1e308])
        )


def test_saved_rejection_behavior_agrees_exactly():
    saved_thermal = _saved("热速度标度换算")
    saved_channels = _saved("弹性频率通道求和")
    saved_total = _saved("中性总损失碰撞频率组装")
    with pytest.raises(ValueError):
        saved_thermal.compute_thermal_speed_m_s(-1.0, 1.0)
    with pytest.raises(ValueError):
        compute_thermal_speed_m_s(-1.0, 1.0)
    with pytest.raises(ValueError):
        saved_channels.sum_elastic_frequency_channels([np.ones(3), np.ones(3)])
    with pytest.raises(ValueError):
        sum_elastic_frequency_channels([np.ones(3), np.ones(3)])
    with pytest.raises(ValueError):
        saved_total.assemble_neutral_total_collision_frequency(
            [1.0], [1.0], [1.0], [1.0], [0.0]
        )
    with pytest.raises(ValueError):
        assemble_neutral_total_collision_frequency([1.0], [1.0], [1.0], [1.0], [0.0])
    saved_moments = _saved("轴对称中性分布矩归约")
    _, distribution, vx, vr, volume = _fixture(4)
    zeroed = distribution.copy()
    zeroed[:, :, 0] = 0.0
    with pytest.raises(ValueError):
        saved_moments.reduce_axisymmetric_neutral_distribution(
            zeroed, vx, vr, volume,
            normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2,
        )
    with pytest.raises(ValueError):
        reduce_axisymmetric_neutral_moments(
            zeroed, vx, vr, volume,
            normalization_temperature_ev=3.0, isotope_mass_amu=2.0, molecularity=2,
        )
