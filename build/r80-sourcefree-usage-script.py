"""r80 source-free public API usage smoke (run outside the repository)."""
import os
import sys

assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
assert os.environ.get("PYTHONPATH") is None, os.environ.get("PYTHONPATH")
assert not os.path.basename(os.getcwd()).startswith("SciRel"), os.getcwd()

import math
import numpy as np

import scirel

assert "site-packages" in scirel.__file__.replace("/", "\\"), scirel.__file__
try:
    import tests
except ImportError:
    pass
else:
    raise AssertionError("repository tests package must not be importable in the isolated runtime")

from scirel.fusion import doppler_stark_zeeman_wavelengths, bin_fida_los_components

# doppler_stark_zeeman_wavelengths: zero-field Doppler degeneracy (one cm/s -> m/s conversion)
result = doppler_stark_zeeman_wavelengths(
    (2.0, 0.0, 0.0), (2.99792458e8, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
    (1.0, 0.0, 0.0), 0.0, 656.28, 15)
assert result == (656.28 * 1.01,) * 15

# electric-only Lyman probe with wavenumber symmetry
lyman = doppler_stark_zeeman_wavelengths(
    (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
    (1.0, 0.0, 0.0), 1.0e5, 121.57, 3)
assert lyman[1] == 121.57 and lyman[0] > lyman[1] > lyman[2]
inv = [1.0 / (v * 1e-9) for v in lyman]
assert abs(inv[0] + inv[2] - 2.0 * inv[1]) / inv[1] < 1.0e-14

# fail-closed hardening: whole-number float component_count
try:
    doppler_stark_zeeman_wavelengths(
        (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
        (1.0, 0.0, 0.0), 0.0, 656.28, 3.0)
except ValueError:
    pass
else:
    raise AssertionError("3.0 must be rejected (registered hardening)")

# bin_fida_los_components: source floor binning + conservation factor
bins = bin_fida_los_components(
    wavelength_nm=[650.0, 650.5, 651.999999],
    component_intensity=[1.0, 2.0, 3.0],
    lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=4)
assert bins["bin_index_zero_based"].tolist() == [0, 1, 3]
assert bins["accepted_component_count"] == 3
assert np.sum(bins["weight_bins"]) == 6.0 / (4.0 * math.pi * 0.5)

# out-of-range drop with retained raw indices
dropped = bin_fida_los_components(
    wavelength_nm=[649.0, 650.25, 653.0],
    component_intensity=[1.0, 2.0, 4.0],
    lambdamin_nm=650.0, lambdamax_nm=652.0, nlambda=2)
assert dropped["accepted_component_count"] == 1
assert dropped["bin_index_zero_based"].tolist() == [-1, 0, 3]

# N5 -> N6 combination witness
wavelengths = doppler_stark_zeeman_wavelengths(
    (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.0,
    (0.0, 0.0, 1.0), 2.0e5, 656.28, 15)
witness = bin_fida_los_components(
    wavelength_nm=list(wavelengths), component_intensity=[1.0] * 15,
    lambdamin_nm=650.0, lambdamax_nm=660.0, nlambda=20)
assert witness["accepted_component_count"] == 15
assert abs(np.sum(witness["weight_bins"]) - 15.0 / (4.0 * math.pi * 0.5)) < 1e-12

print("R80-SOURCE-FREE-USAGE-PASSED")
