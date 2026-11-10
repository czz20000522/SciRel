"""Integrate density and gyrotropic pressures of an invariant mirror distribution."""

import numpy as np
from scirel._numerics import _scaled_difference
from ._mirror_numerics import (
    _trapped_fractions,
    _density_exponential,
    _positive_product,
)


def _field(value, psi, name):
    if callable(value):
        value = value(np.asarray(psi, dtype=float))
    values = np.asarray(value, dtype=float)
    try:
        values = np.broadcast_to(values, np.shape(psi))
    except ValueError as exc:
        raise ValueError(f"{name} cannot be broadcast over psi") from exc
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must be finite")
    return values


def evaluate_mirror_constrained_moments(
    b_t,
    psi,
    potential_v,
    mass_kg,
    charge_c,
    density_ref_m3,
    temperature_parallel_j,
    temperature_perpendicular_ref_j,
    b_ref_t,
    phi_ref_v=0.0,
    b_plug_left_t=None,
    b_plug_right_t=None,
    phi_plug_left_v=0.0,
    phi_plug_right_v=0.0,
    loss_cone_refill=0.0,
    quadrature_order=32,
):
    """Evaluate local density and gyrotropic pressure moments of an invariant bi-Maxwellian, optionally reducing them by two-plug loss-cone pitch integrals.

    Parameters
    ----------
    b_t : real array-like converted to float64, scalar or array; broadcasts with psi and potential_v
        Local magnetic-field magnitude B. [T] Constraints: All broadcast elements finite and strictly positive.
    psi : real array-like converted to float64, scalar or array; broadcasts with b_t and potential_v
        Caller flux-profile coordinate and shared shape carrier. [Wb (historical source convention; not runtime-enforced)] Constraints: All broadcast elements finite; no range or flux-normalization check.
    potential_v : real array-like converted to float64, scalar or array; broadcasts with b_t and psi
        Local electrostatic potential phi. [V] Constraints: All broadcast elements finite.
    mass_kg : float-convertible, scalar
        Species mass, validated but not used in the evaluated moments. [kg] Constraints: Finite and strictly positive.
    charge_c : real numeric scalar, scalar
        Signed species charge q in the potential factor and plug barriers. [C] Constraints: Finite and nonzero; the function does not require a positive ion. Later arithmetic uses the original argument after float-based validation.
    density_ref_m3 : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Reference species number-density profile n_ref. [m^-3] Constraints: Evaluated elements must be finite and nonnegative.
    temperature_parallel_j : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Parallel temperature energy scale T_parallel. [J] Constraints: Evaluated elements must be finite and strictly positive.
    temperature_perpendicular_ref_j : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Reference perpendicular temperature energy scale T_perp,ref. [J] Constraints: Evaluated elements must be finite and strictly positive.
    b_ref_t : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Reference magnetic-field magnitude B_ref profile. [T] Constraints: Evaluated elements must be finite and strictly positive; the derived coefficient C must also be positive.
    phi_ref_v : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Reference electrostatic-potential profile phi_ref. [V] Constraints: Evaluated elements must be finite. Default: ``0``.
    b_plug_left_t : null, real array-like or callable yielding float64-convertible values, None, scalar, broadcast-compatible array or callable(psi)
        Left-end plug magnetic-field profile. [T or not applicable] Constraints: Must be supplied together with b_plug_right_t; evaluated for finiteness and positivity only when the plug branch is active (refill != 1). Default: ``None``.
    b_plug_right_t : null, real array-like or callable yielding float64-convertible values, None, scalar, broadcast-compatible array or callable(psi)
        Right-end plug magnetic-field profile. [T or not applicable] Constraints: Must be supplied together with b_plug_left_t; evaluated for finiteness and positivity only when the plug branch is active (refill != 1). Default: ``None``.
    phi_plug_left_v : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi)
        Left-end plug electrostatic-potential profile. [V] Constraints: Evaluated for finiteness only when both plug fields are supplied and refill != 1. Default: ``0``.
    phi_plug_right_v : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi)
        Right-end plug electrostatic-potential profile. [V] Constraints: Evaluated for finiteness only when both plug fields are supplied and refill != 1. Default: ``0``.
    loss_cone_refill : real numeric scalar, scalar
        Fraction restoring the unconfined bi-Maxwellian pitch occupation. [dimensionless] Constraints: Finite in [0,1]; zero is the source-defined empty loss cone and one bypasses plug integration. Later arithmetic uses the original argument after float-based validation. Default: ``0``.
    quadrature_order : float- and int-convertible, scalar
        Subdivision work-budget control for error-controlled trapped fractions; analytic magnetic-only limits bypass integration. [count] Constraints: Finite with int(quadrature_order) at least 8; validated on every call, even without plug integration. Exact integer-valued input is not enforced; nodes are used only when plug integration is active. Default: ``32``.

    Returns
    -------
    density_m3 : float64 ndarray, common broadcast shape
        Local density after the pitch-occupation factor. [m^-3] Constraints: Finite on successful return; computed from untruncated normalization and its dimensionless fraction.
    p_parallel_pa : float64 ndarray, common broadcast shape
        Gyrotropic parallel pressure moment after pitch reduction. [Pa] Constraints: Finite on successful return; computed from untruncated normalization and its dimensionless fraction.
    p_perpendicular_pa : float64 ndarray, common broadcast shape
        Gyrotropic perpendicular pressure moment after pitch reduction. [Pa] Constraints: Finite on successful return; computed from untruncated normalization and its dimensionless fraction.
    temperature_parallel_j : float64 ndarray, common broadcast shape
        Evaluated input parallel temperature parameter, not a pressure-over-depleted-density effective temperature. [J] Constraints: Finite and strictly positive on successful validated input.
    temperature_perpendicular_local_j : float64 ndarray, common broadcast shape
        Untruncated local perpendicular temperature parameter B/C. [J] Constraints: Requires C>0; not reconstructed from depleted pressure and density.
    untruncated_density_m3 : float64 ndarray, common broadcast shape
        Local bi-Maxwellian density before plug pitch reduction. [m^-3] Constraints: Includes the unclipped potential exponent combined with density and temperature ratio in log space.
    density_pitch_integral : float64 ndarray, common broadcast shape
        Dimensionless density pitch-reduction integral. [dimensionless] Constraints: Fraction in [0,1] within numerical accuracy. General quadrature has absolute 2e-13 / relative 2e-11 error-estimate targets; errors scale with the untruncated moment normalization.
    parallel_pitch_integral : float64 ndarray, common broadcast shape
        Dimensionless parallel-pressure pitch-reduction integral. [dimensionless] Constraints: Fraction in [0,1] within numerical accuracy. General quadrature has absolute 2e-13 / relative 2e-11 error-estimate targets; errors scale with the untruncated moment normalization.
    perpendicular_pitch_integral : float64 ndarray, common broadcast shape
        Dimensionless perpendicular-pressure pitch-reduction integral. [dimensionless] Constraints: Fraction in [0,1] within numerical accuracy. General quadrature has absolute 2e-13 / relative 2e-11 error-estimate targets; errors scale with the untruncated moment normalization.

    Raises
    ------
    ValueError
        For invalid mass/charge, refill or quadrature controls, one-sided plug
        fields, nonfinite or nonpositive checked fields/temperatures, negative
        reference density, nonfinite profile results, or nonbroadcastable
        shapes. Native conversion and callable errors may propagate.
    FloatingPointError
        For a nonpositive/nonfinite integrability coefficient or an
        unrepresentable density or pressure output.
    RuntimeError
        If general trapped-fraction quadrature does not meet its error estimate
        within the work budget.
    See Also
    --------
    evaluate_mirror_invariant_distribution
        Evaluate the underlying invariant phase-space distribution.
    assemble_mirror_total_pressure
        Combine these ion moments with an electron pressure.
    Notes
    -----
    For ``C=(B-B_ref)/T_parallel+B_ref/T_perp,ref`` and ``T_perp,local=B/C``, the untruncated density is formed without exponent clipping. With no plugs or ``loss_cone_refill=1`` the three pitch fractions are one. Otherwise the two plug barriers define the trapped pitch fractions, and refill mixes them as ``refill+(1-refill)*fraction``. The final density and pressure products are formed without premature overflow. ``quadrature_order`` is converted with ``int`` for the work budget: a finite non-integer value at least eight is accepted and truncated, for example ``8.9`` becomes ``8``; this historical behavior is recorded, not corrected here. The callable does not solve the potential, field-line geometry or a self-consistent mirror equilibrium.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.mirror import evaluate_mirror_constrained_moments
    >>> e = 1.602176634e-19
    >>> b = np.array([1.0, 2.0])
    >>> r = evaluate_mirror_constrained_moments(b, np.zeros(2), 0.0, 1.67262192595e-27, e, 2.0e18, 1200.0*e, 2400.0*e, 1.0)
    >>> t_perp = b / ((b-1.0)/(1200.0*e) + 1.0/(2400.0*e))
    >>> n = 2.0e18*t_perp/(2400.0*e)
    >>> np.testing.assert_allclose(r['density_m3'], n)
    >>> np.testing.assert_allclose(r['p_parallel_pa'], n*1200.0*e)
    >>> np.testing.assert_allclose(r['p_perpendicular_pa'], n*t_perp)
    >>> np.testing.assert_allclose(r['density_pitch_integral'], 1.0)

    """
    mass = float(mass_kg)
    charge = float(charge_c)
    refill = float(loss_cone_refill)
    order_value = float(quadrature_order)
    if not np.isfinite(mass) or mass <= 0.0 or (not np.isfinite(charge)) or (charge == 0.0):
        raise ValueError(
            "mass_kg and charge_c must be finite; mass must be positive and charge must be non-zero"
        )
    if (
        not np.isfinite(refill)
        or not 0.0 <= refill <= 1.0
        or (not np.isfinite(order_value))
        or (int(order_value) < 8)
    ):
        raise ValueError(
            "loss_cone_refill must be finite in [0,1] and quadrature_order must be finite with int value at least 8"
        )
    if (b_plug_left_t is None) != (b_plug_right_t is None):
        raise ValueError("both left and right plug fields are required")
    b_t, psi, potential_v = np.broadcast_arrays(
        np.asarray(b_t, dtype=float),
        np.asarray(psi, dtype=float),
        np.asarray(potential_v, dtype=float),
    )
    if not all((np.all(np.isfinite(value)) for value in (b_t, psi, potential_v))) or np.any(
        b_t <= 0.0
    ):
        raise ValueError("b_t, psi, and potential_v must be finite; b_t must be positive")
    density_ref = _field(density_ref_m3, psi, "density_ref_m3")
    t_parallel = _field(temperature_parallel_j, psi, "temperature_parallel_j")
    t_perpendicular_ref = _field(
        temperature_perpendicular_ref_j, psi, "temperature_perpendicular_ref_j"
    )
    b_ref = _field(b_ref_t, psi, "b_ref_t")
    phi_ref = _field(phi_ref_v, psi, "phi_ref_v")
    if (
        np.any(density_ref < 0.0)
        or np.any(t_parallel <= 0.0)
        or np.any(t_perpendicular_ref <= 0.0)
        or np.any(b_ref <= 0.0)
    ):
        raise ValueError("reference density/temperatures/field are invalid")
    coefficient = (b_t - b_ref) / t_parallel + b_ref / t_perpendicular_ref
    if np.any(coefficient <= 0.0):
        raise FloatingPointError("invariant bi-Maxwellian is not integrable")
    t_perpendicular_local = b_t / coefficient
    exponent = -_scaled_difference(potential_v, phi_ref, charge, t_parallel)
    density_full = _density_exponential(
        density_ref, t_perpendicular_local / t_perpendicular_ref, exponent
    )
    density_integral = np.ones_like(b_t)
    parallel_integral = np.ones_like(b_t)
    perpendicular_integral = np.ones_like(b_t)
    if b_plug_left_t is not None and loss_cone_refill != 1.0:
        b_left = _field(b_plug_left_t, psi, "b_plug_left_t")
        b_right = _field(b_plug_right_t, psi, "b_plug_right_t")
        phi_left = _field(phi_plug_left_v, psi, "phi_plug_left_v")
        phi_right = _field(phi_plug_right_v, psi, "phi_plug_right_v")
        if np.any(b_left <= 0.0) or np.any(b_right <= 0.0):
            raise ValueError("plug magnetic fields must be positive")
        alpha_left = (b_left - b_t) / (coefficient * t_parallel)
        alpha_right = (b_right - b_t) / (coefficient * t_parallel)
        beta_left = _scaled_difference(phi_left, potential_v, charge, t_parallel)
        beta_right = _scaled_difference(phi_right, potential_v, charge, t_parallel)
        density_integral, parallel_integral, perpendicular_integral = _trapped_fractions(
            alpha_left, beta_left, alpha_right, beta_right, int(order_value)
        )
        density_integral = refill + (1.0 - refill) * density_integral
        parallel_integral = refill + (1.0 - refill) * parallel_integral
        perpendicular_integral = refill + (1.0 - refill) * perpendicular_integral
    final_moments = (
        _positive_product(density_full, density_integral),
        _positive_product(density_full, t_parallel, parallel_integral),
        _positive_product(density_full, t_perpendicular_local, perpendicular_integral),
    )
    return {
        "density_m3": final_moments[0],
        "p_parallel_pa": final_moments[1],
        "p_perpendicular_pa": final_moments[2],
        "temperature_parallel_j": t_parallel,
        "temperature_perpendicular_local_j": t_perpendicular_local,
        "untruncated_density_m3": density_full,
        "density_pitch_integral": density_integral,
        "parallel_pitch_integral": parallel_integral,
        "perpendicular_pitch_integral": perpendicular_integral,
    }


__all__ = ["evaluate_mirror_constrained_moments"]
