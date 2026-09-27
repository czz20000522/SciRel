"""FIDASIM FIDA Stark-component wavelength bin accumulation.

Source: the saved package ``FIDA权重谱线分箱`` (source anchor
``src/fidasim.f90:12297-12347``, ``store_fw_photons_at_chan``): the
final numerical boundary of the FIDA weight production that places
Stark component wavelengths with their normalized intensities into the
FIDA wavelength bins and applies the ``1/(4*pi*dlambda)``
solid-angle/wavelength factor.  The binning is
``dlambda = (lambdamax - lambdamin) / nlambda``,
``bin = floor((lambda - lambdamin) / dlambda)``, the valid increment is
``intensity / (4*pi*dlambda)``, and the half-open interval
``[lambdamin, lambdamax)`` is equivalent to the source's
``bin < 1`` / ``bin > nlambda`` branches.  Out-of-range components are
dropped from the weight but keep their raw computed bin index for
boundary audit.

Registered hardening against the saved arm: the wavelength and
intensity inputs must not carry boolean entries -- neither bool dtype
arrays nor mixed object arrays such as ``[True, 1.0]`` (the saved arm's
``np.asarray(value, dtype=float)`` silently coerced ``True`` to 1.0,
following the same numerification gap closed for the r79 merge
family).  The saved arm's own ``nlambda`` genuine-integer contract
(bools rejected, ``np.integer`` accepted) is kept and pinned.

r80-v2 repairs (read-only expert review findings on the r80-v1 freeze):
the bin width is checked to be a positive finite float before the
factor is formed, so a window whose width underflows to zero (e.g.
``lambdamax = 5e-324`` with ``nlambda = 2``) raises the declared
``ValueError`` instead of ``ZeroDivisionError``, and a window whose
width overflows to ``inf`` fails closed instead of silently producing
a zero normalization factor; the normalization factor itself must
stay finite, so a positive but subnormal width such as ``1e-320``
(with ``nlambda = 1``) fails closed instead of returning ``inf``
factors and ``inf`` weight bins; and the per-component bin index is
computed in float and checked representable before the integer cast,
so a huge out-of-range wavelength fails closed instead of reporting
the int64 overflow sentinel ``-9223372036854775808`` as its "raw
index".

The upstream component-wavelength relation is
``scirel.fusion.doppler-stark-zeeman-wavelengths``; the full
``fida_weights_los`` phase producer around both remains deferred.
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["bin_fida_los_components"]


def _component_vector(value, *, name: str, size: int | None) -> np.ndarray:
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.dtype == np.bool_ or (
        array.dtype == np.object_ and any(isinstance(item, (bool, np.bool_)) for item in array)
    ):
        raise ValueError(f"{name} must not contain boolean entries (registered hardening)")
    try:
        array = array.astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite 1-D array")
    if size is not None and array.shape != (size,):
        raise ValueError(f"{name} must have shape ({size},)")
    return array


def bin_fida_los_components(
    *,
    wavelength_nm,
    component_intensity,
    lambdamin_nm,
    lambdamax_nm,
    nlambda,
):
    """Implement ``store_fw_photons_at_chan``'s explicit binning boundary."""
    wavelength = _component_vector(wavelength_nm, name="wavelength_nm", size=None)
    if wavelength.size not in (3, 15):
        raise ValueError("wavelength_nm must have length 3 or 15")
    wavelength = _component_vector(wavelength_nm, name="wavelength_nm", size=wavelength.size)
    intensity = _component_vector(
        component_intensity, name="component_intensity", size=wavelength.size
    )
    if np.any(intensity < 0.0):
        raise ValueError("component_intensity must be nonnegative")
    low, high = float(lambdamin_nm), float(lambdamax_nm)
    if isinstance(lambdamin_nm, (bool, np.bool_)) or isinstance(
        lambdamax_nm, (bool, np.bool_)
    ):
        raise ValueError("lambdamin_nm and lambdamax_nm must not be boolean (registered hardening)")
    if not math.isfinite(low) or not math.isfinite(high) or not high > low:
        raise ValueError("lambdamin_nm and lambdamax_nm must be finite with lambdamax_nm > lambdamin_nm")
    if isinstance(nlambda, (bool, np.bool_)) or not isinstance(nlambda, (int, np.integer)) or int(nlambda) <= 0:
        raise ValueError("nlambda must be a positive integer")
    nlambda = int(nlambda)
    dlambda = (high - low) / nlambda
    if not math.isfinite(dlambda) or dlambda <= 0.0:
        raise ValueError(
            "the wavelength window does not produce a positive finite bin width"
            " (r80-v2 repair: the saved arm raised ZeroDivisionError on underflow"
            " and silently produced a zero factor on overflow)"
        )
    factor = 1.0 / (4.0 * math.pi * dlambda)
    if not math.isfinite(factor):
        raise ValueError(
            "the normalization factor 1/(4*pi*dlambda) is not finite for the supplied"
            " window (r80-v2 repair: a positive but subnormal bin width such as"
            " 1e-320 overflowed the factor and the weight bins to inf)"
        )
    scaled = (wavelength - low) / dlambda
    if not np.all(np.isfinite(scaled)) or np.any(np.abs(scaled) >= 9.223372036854776e18):
        raise ValueError(
            "a component wavelength's bin index is not representable as a finite"
            " integer (r80-v2 repair: the saved arm wrote the int64 overflow sentinel"
            " -9223372036854775808 instead of a meaningful raw index)"
        )
    bins = np.floor(scaled).astype(int)
    output = np.zeros(nlambda, dtype=float)
    accepted = (bins >= 0) & (bins < nlambda)
    np.add.at(output, bins[accepted], intensity[accepted] * factor)
    return {
        "weight_bins": output,
        "bin_index_zero_based": bins,
        "accepted_component_count": int(np.sum(accepted)),
        "dlambda_nm": dlambda,
        "intensity_factor_per_sr_nm": factor,
    }
