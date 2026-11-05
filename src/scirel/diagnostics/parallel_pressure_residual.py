"""Fixed-flux gyrotropic parallel-pressure compatibility check."""

import numpy as np
from ._fixed_flux_derivative import fixed_flux_derivative


def compute_parallel_pressure_residual(
    p_parallel,
    p_perp,
    magnetic_field,
    rtol=0.01,
    atol=1e-6,
    strict=False,
    *,
    dp_parallel_dB=None,
    field_axis=None,
    psi=None,
):
    """Check p_perp = p_parallel - B*(partial p_parallel/partial B)_psi.

    Pressures are in Pa and B in tesla. Supply ``dp_parallel_dB`` (Pa/T,
    array/scalar or callable(B,psi)), or ``field_axis`` and fixed-psi sample
    lines. Spatial arrays sorted globally by B cannot establish this partial
    derivative. Constant-field isotropic samples pass with explicit zero
    derivative; without derivative information the result is indeterminate
    and raises ValueError. A finite-difference residual includes sampling
    error and is not a spatial force-balance or global-stability proof.
    """
    p_parallel, p_perp, magnetic_field = (
        np.asarray(x, dtype=float) for x in (p_parallel, p_perp, magnetic_field)
    )
    if p_parallel.shape != p_perp.shape or p_parallel.shape != magnetic_field.shape:
        raise ValueError("p_parallel, p_perp, and magnetic_field must have the same shape")
    if p_parallel.size == 0:
        raise ValueError("parallel-pressure equilibrium requires at least one sample")
    if not np.all(np.isfinite(p_perp)):
        raise ValueError("pressures must be finite")
    if not np.isfinite(rtol) or not np.isfinite(atol) or rtol < 0 or atol <= 0:
        raise ValueError("rtol must be non-negative and atol must be positive finite values")
    derivative, method = fixed_flux_derivative(
        p_parallel, magnetic_field, derivative=dp_parallel_dB, field_axis=field_axis, psi=psi
    )
    rhs = p_parallel - magnetic_field * derivative
    error = p_perp - rhs
    relative_error = np.abs(error) / np.maximum(np.maximum(np.abs(p_perp), np.abs(rhs)), atol)
    if not all(np.all(np.isfinite(x)) for x in (rhs, error, relative_error)):
        raise FloatingPointError("parallel-pressure residual is not finite")
    maximum = float(np.max(relative_error))
    passed = bool(maximum <= rtol)
    if strict and not passed:
        raise ValueError("parallel equilibrium check failed")
    return {
        "rhs": rhs,
        "error": error,
        "relative_error": relative_error,
        "max_relative_error": maximum,
        "mean_relative_error": float(np.mean(relative_error)),
        "passed": passed,
        "dp_parallel_dB": derivative,
        "derivative_method": method,
    }


__all__ = ["compute_parallel_pressure_residual"]
