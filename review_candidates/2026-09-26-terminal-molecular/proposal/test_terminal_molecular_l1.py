"""Bounded historical replay of the r65 terminal molecular diagnostics family
against the saved KN1DPy implementations, when present.

The saved operator bundles sit in the re-review archive ``KN1DPy-631d0bf1``:
KN1DPy's strict D1 qualification has been withdrawn, so this replay is
bounded historical development evidence about the arithmetic, not
qualified-L1 provenance and not expert approval.  Skipped unless
``SCIREL_KN1DPY_REVIEW_ROOT`` points at the bundle root; every saved
implementation file is pinned by SHA-256.

All six operators have saved-arm parity coverage on declared legal inputs.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import (
    reduce_qh2_total_conservation_diagnostic,
    reduce_terminal_molecular_energy_transfer,
    reduce_terminal_molecular_flux_velocity,
    reduce_terminal_molecular_heat_flux,
    reduce_terminal_molecular_ion_state,
    reduce_terminal_molecular_pressure_temperature,
)

_PINNED = {
    "终态分子通量与轴向速度归约": "73dfe7df71e537f35c69d9ac7470303501fb933c43eced6772e915498f873ea9",
    "终态分子压力与温度归约": "5574ec2415d1df7cddc373432f82553c23595b61620ce9689b093dc39c8a116a",
    "终态分子随机与总热通量归约": "46e9c00fb9cce1f2d6e82efa83a176a91500ea06c00de4f224aa2a337bdf7aeb",
    "终态分子能量转移率归约": "da8da87c2030fadcb2c21cd7ae064398dbf91aeb461a591d11a641ccdc5b44b3",
    "终态分子离子密度与温度归约": "a04b3049e4d33af713eb5632f88135777e683f7df257dfc061c8a853c06edb57",
    "终态分子总能量守恒诊断": "258ef36f7d265f5a7cc08f021cbf91fbd83ad9ce6876a1c56d1064655d4c2af3",
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
    spec = importlib.util.spec_from_file_location(f"kn1dpy_r65_{len(_LOADED)}", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LOADED[package] = module
    return module


def _assert_dict_equal(saved_result, port_result):
    for key in saved_result:
        np.testing.assert_array_equal(saved_result[key], port_result[key])


def test_terminal_flux_velocity_matches_saved_bit_for_bit():
    saved = _saved("终态分子通量与轴向速度归约")
    vr = np.linspace(0.5, 2.0, 4)
    vx = np.linspace(-1.5, 1.5, 6)
    dvx = np.full(6, 0.5)
    weight = np.ones(4)
    dist = np.exp(-(vr[:, None] ** 2 + vx[None, :] ** 2))[:, :, None] * np.ones((4, 6, 3))
    saved_result = saved.reduce_terminal_molecular_flux_velocity(vx, 5000.0, dist, weight, dvx)
    port_result = reduce_terminal_molecular_flux_velocity(vx, 5000.0, dist, weight, dvx)
    _assert_dict_equal(saved_result, port_result)


def test_terminal_pressure_temperature_matches_saved_bit_for_bit():
    saved = _saved("终态分子压力与温度归约")
    vr = np.linspace(0.5, 2.0, 4)
    vx = np.linspace(-1.5, 1.5, 6)
    dvx = np.full(6, 0.5)
    weight = np.ones(4)
    dist = np.exp(-(vr[:, None] ** 2 + vx[None, :] ** 2))[:, :, None] * np.ones((4, 6, 3))
    saved_result = saved.reduce_terminal_molecular_pressure_temperature(
        vr, vx, 2.0, 5000.0, dist, weight, dvx
    )
    port_result = reduce_terminal_molecular_pressure_temperature(
        vr, vx, 2.0, 5000.0, dist, weight, dvx
    )
    _assert_dict_equal(saved_result, port_result)


def test_terminal_heat_flux_matches_saved_bit_for_bit():
    saved = _saved("终态分子随机与总热通量归约")
    vr = np.linspace(0.5, 2.0, 4)
    vx = np.linspace(-1.5, 1.5, 6)
    dvx = np.full(6, 0.5)
    weight = np.ones(4)
    dist = np.exp(-(vr[:, None] ** 2 + vx[None, :] ** 2))[:, :, None] * np.ones((4, 6, 3))
    saved_result = saved.reduce_terminal_molecular_heat_flux(
        vr, vx, 2.0, 5000.0, dist, weight, dvx
    )
    port_result = reduce_terminal_molecular_heat_flux(
        vr, vx, 2.0, 5000.0, dist, weight, dvx
    )
    _assert_dict_equal(saved_result, port_result)


def test_terminal_energy_transfer_matches_saved_bit_for_bit():
    saved = _saved("终态分子能量转移率归约")
    vr = np.linspace(0.5, 2.0, 4)
    vx = np.linspace(-1.5, 1.5, 6)
    x = np.linspace(0.0, 1.0, 3)
    dvx = np.full(6, 0.5)
    weight = np.ones(4)
    dist = np.exp(-(vr[:, None] ** 2 + vx[None, :] ** 2))[:, :, None] * np.ones((4, 6, 3))
    rhs = np.ones((4, 6, 3))
    ext_src = np.ones(3)
    saved_result = saved.reduce_terminal_molecular_energy_transfer(
        vr, vx, 2.0, 5000.0, dist, rhs, weight, dvx, ext_src
    )
    port_result = reduce_terminal_molecular_energy_transfer(
        vr, vx, 2.0, 5000.0, dist, rhs, weight, dvx, ext_src
    )
    _assert_dict_equal(saved_result, port_result)


def test_terminal_ion_state_matches_saved_bit_for_bit():
    saved = _saved("终态分子离子密度与温度归约")
    nx = 3
    molecular_density = np.full(nx, 1.0e18)
    neutral_density = np.full(nx, 5.0e17)
    ion_temperature = np.full(nx, 3.0)
    mass_ratio = 2.0
    ionization_rate = np.full(nx, 1.0e-14)
    reaction_rate = np.full((nx, 11), 5.0e-15)
    loss_frequency = np.full(nx, 100.0)
    saved_result = saved.reduce_terminal_molecular_ion_state(
        molecular_density, neutral_density, ion_temperature,
        mass_ratio, ionization_rate, reaction_rate, loss_frequency,
    )
    port_result = reduce_terminal_molecular_ion_state(
        molecular_density, neutral_density, ion_temperature,
        mass_ratio, ionization_rate, reaction_rate, loss_frequency,
    )
    _assert_dict_equal(saved_result, port_result)


def test_conservation_diagnostic_matches_saved_bit_for_bit():
    saved = _saved("终态分子总能量守恒诊断")
    x = np.linspace(0, 1, 5)
    flux = np.linspace(10.0, 5.0, 5)
    transfer = np.linspace(1.0, 0.5, 5)
    saved_result = saved.reduce_qh2_total_conservation_diagnostic(x, flux, transfer)
    port_result = reduce_qh2_total_conservation_diagnostic(x, flux, transfer)
    _assert_dict_equal(saved_result, port_result)


def test_the_saved_rejection_behavior_agrees_exactly():
    saved_flux = _saved("终态分子通量与轴向速度归约")
    saved_cons = _saved("终态分子总能量守恒诊断")
    vr = np.linspace(0.5, 2.0, 4)
    vx = np.linspace(-1.5, 1.5, 6)
    dvx = np.full(6, 0.5)
    weight = np.ones(4)
    with pytest.raises(ValueError):
        saved_flux.reduce_terminal_molecular_flux_velocity(vx, 5000.0, np.zeros((4, 6, 2)), weight, dvx)
    with pytest.raises(ValueError):
        reduce_terminal_molecular_flux_velocity(vx, 5000.0, np.zeros((4, 6, 2)), weight, dvx)
    with pytest.raises(ValueError):
        saved_cons.reduce_qh2_total_conservation_diagnostic(np.linspace(0, 1, 3), np.full(3, np.nan), np.ones(3))
    with pytest.raises(ValueError):
        reduce_qh2_total_conservation_diagnostic(np.linspace(0, 1, 3), np.full(3, np.nan), np.ones(3))
