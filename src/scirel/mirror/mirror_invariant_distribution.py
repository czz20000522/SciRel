"""Evaluate a trapped or refilled invariant bi-Maxwellian directly on broadcast velocity and flux coordinates."""

import math
import numpy as np
from scirel._numerics import _scaled_difference


def _field(value, psi, name):
    if callable(value):
        value = value(np.asarray(psi, dtype=float))
    try:
        values = np.broadcast_to(np.asarray(value, dtype=float), np.shape(psi))
    except ValueError as exc:
        raise ValueError(f"{name} cannot be broadcast over psi") from exc
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must be finite")
    return values


def _require_finite_scalar(value, name, *, positive=False, nonzero=False):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a finite scalar")
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite scalar") from exc
    if array.ndim != 0 or not np.isrealobj(array) or (not bool(np.all(np.isfinite(array)))):
        raise ValueError(f"{name} must be a finite scalar")
    result = float(array)
    if positive and result <= 0.0:
        raise ValueError(f"{name} must be strictly positive")
    if nonzero and result == 0.0:
        raise ValueError(f"{name} must be non-zero")
    return result


def evaluate_mirror_invariant_distribution(
    v_parallel_m_s,
    v_perpendicular_m_s,
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
):
    """Evaluate a reference bi-Maxwellian phase-space density from energy and magnetic moment, optionally multiplying by a two-plug loss-cone occupation with fractional refill.

    Parameters
    ----------
    v_parallel_m_s : real array-like converted to float64, scalar or array broadcasting with the other four local quantities
        Signed velocity along the local magnetic field. [m/s] Constraints: Finite; sign reversal leaves the energy contribution unchanged.
    v_perpendicular_m_s : real array-like converted to float64, scalar or array broadcasting with the other four local quantities
        Perpendicular speed argument used through its square. [m/s] Constraints: Finite; no nonnegative check; the sign does not change mu.
    b_t : real array-like converted to float64, scalar or array broadcasting with the other four local quantities
        Local magnetic-field magnitude B. [T] Constraints: Finite and strictly positive.
    psi : real array-like converted to float64, scalar or array broadcasting with the other four local quantities
        Caller flux-profile coordinate and shape carrier for profile evaluation. [Wb (historical source label, not runtime-enforced)] Constraints: Finite; no range or flux-normalization check.
    potential_v : real array-like converted to float64, scalar or array broadcasting with the other four local quantities
        Local electrostatic potential phi in particle energy. [V] Constraints: Finite.
    mass_kg : real numeric scalar, scalar
        Particle mass m. [kg] Constraints: Finite, strictly positive and not bool.
    charge_c : real numeric scalar, scalar
        Signed particle charge q. [C] Constraints: Finite, nonzero and not bool; either sign is accepted.
    density_ref_m3 : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Reference number-density profile n_ref. [m^-3] Constraints: Evaluated values finite and nonnegative.
    temperature_parallel_j : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Reference parallel thermal energy T_parallel. [J] Constraints: Evaluated values finite and strictly positive.
    temperature_perpendicular_ref_j : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Reference perpendicular thermal energy T_perp,ref. [J] Constraints: Evaluated values finite and strictly positive.
    b_ref_t : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Reference magnetic-field magnitude B_ref. [T] Constraints: Evaluated values finite and strictly positive; C must also be positive.
    phi_ref_v : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi) returning such values
        Reference electrostatic-potential profile phi_ref. [V] Constraints: Evaluated values finite. Default: ``0``.
    b_plug_left_t : null or real array-like/callable yielding float64-convertible values, None, scalar, broadcast-compatible array or callable(psi)
        Left-end magnetic barrier field. [T or not applicable] Constraints: Must be supplied together with b_plug_right_t; if supplied, evaluated values finite and strictly positive. Default: ``None``.
    b_plug_right_t : null or real array-like/callable yielding float64-convertible values, None, scalar, broadcast-compatible array or callable(psi)
        Right-end magnetic barrier field. [T or not applicable] Constraints: Must be supplied together with b_plug_left_t; if supplied, evaluated values finite and strictly positive. Default: ``None``.
    phi_plug_left_v : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi)
        Left-end electrostatic barrier potential. [V] Constraints: Evaluated for finiteness only when both plug fields are present. Default: ``0``.
    phi_plug_right_v : real array-like or callable yielding float64-convertible values, scalar, broadcast-compatible array or callable(psi)
        Right-end electrostatic barrier potential. [V] Constraints: Evaluated for finiteness only when both plug fields are present. Default: ``0``.
    loss_cone_refill : real numeric scalar, scalar
        Fractional occupation of particles outside the trapped energy region. [dimensionless] Constraints: Finite, not bool and within [0,1]; with no plugs it does not change the full occupation. Default: ``0``.

    Returns
    -------
    f0_s3_m6 : float64 ndarray, common broadcast shape
        Physical phase-space density after the optional loss-cone occupation. [s^3/m^6] Constraints: Finite on successful return; f0 underflow may round to zero.
    energy_j : float64 ndarray, common broadcast shape
        Particle total energy E=mv_parallel^2/2+mu*B+q*phi. This absolute binary64 output can lose sub-ULP thermal contributions at a large potential origin; stable relative energies independently determine f0 and occupation. [J] Constraints: Finite on successful return; f0 underflow may round to zero.
    magnetic_moment_j_t : float64 ndarray, common broadcast shape
        Magnetic moment mu=m*v_perpendicular^2/(2*B). [J/T] Constraints: Finite on successful return; f0 underflow may round to zero.
    occupation : Python float or float64 ndarray, scalar 1.0 without plugs; common broadcast shape with plugs
        One for trapped particles and refill for untrapped particles when plugs exist. [dimensionless] Constraints: The trapped comparison is strict; E equal to the lower barrier gets refill.

    Raises
    ------
    ValueError
        For invalid scalar mass/charge/refill controls, nonfinite local velocity,
        field, flux or potential values, one-sided plug fields, nonbroadcastable
        profile values, nonpositive checked fields/temperatures, or negative
        reference density. Native conversion and callable errors may propagate.
    FloatingPointError
        For a nonpositive/nonfinite integrability coefficient, unrepresentable
        invariants or exponent, or a nonfinite phase-space density.
    See Also
    --------
    evaluate_mirror_constrained_moments
        Reduce this distribution to density and gyrotropic pressure moments.
    assemble_mirror_total_pressure
        Combine ion moments with an electron pressure state.
    Notes
    -----
    The magnetic moment is ``mu=m*v_perpendicular**2/(2*B)`` and the absolute energy is ``E=m*v_parallel**2/2+mu*B+q*phi``. The distribution uses the reference bi-Maxwellian normalization and the relative potential and barrier differences in its exponent. Without both plug fields, ``occupation`` is the scalar ``1.0``. With both plug fields, it is an array and the strict trapped comparison is ``parallel_scaled < min(barrier_left, barrier_right)``; equality is in the depleted branch and receives ``loss_cone_refill``. All five local broadcast inputs must be finite; nonfinite values are rejected. The returned absolute energy can lose sub-ULP kinetic information at a large potential origin, while f0 and occupation use scaled relative terms.

    Examples
    --------
    >>> import math
    >>> import numpy as np
    >>> from scirel.mirror import evaluate_mirror_invariant_distribution
    >>> e = 1.602176634e-19
    >>> m = 1.67262192595e-27
    >>> t_parallel, t_perp = 1200.0*e, 2400.0*e
    >>> r = evaluate_mirror_invariant_distribution(0.0, 0.0, 1.0, 0.0, 0.0, m, e, 2.0e18, t_parallel, t_perp, 1.0)
    >>> expected = 2.0e18*(m/(2.0*math.pi))**1.5/(t_perp*math.sqrt(t_parallel))
    >>> np.testing.assert_allclose(r['f0_s3_m6'], expected)
    >>> np.testing.assert_allclose(r['energy_j'], 0.0)
    >>> np.testing.assert_allclose(r['magnetic_moment_j_t'], 0.0)
    >>> assert r['occupation'] == 1.0

    """
    mass_kg = _require_finite_scalar(mass_kg, "mass_kg", positive=True)
    charge_c = _require_finite_scalar(charge_c, "charge_c", nonzero=True)
    loss_cone_refill = _require_finite_scalar(loss_cone_refill, "loss_cone_refill")
    if not 0.0 <= loss_cone_refill <= 1.0:
        raise ValueError("mass, charge, or loss_cone_refill is invalid")
    if (b_plug_left_t is None) != (b_plug_right_t is None):
        raise ValueError("both plug fields are required together")
    v_parallel_m_s, v_perpendicular_m_s, b_t, psi, potential_v = np.broadcast_arrays(
        np.asarray(v_parallel_m_s, dtype=float),
        np.asarray(v_perpendicular_m_s, dtype=float),
        np.asarray(b_t, dtype=float),
        np.asarray(psi, dtype=float),
        np.asarray(potential_v, dtype=float),
    )
    if not all(
        np.all(np.isfinite(x)) for x in (v_parallel_m_s, v_perpendicular_m_s, b_t, psi, potential_v)
    ):
        raise ValueError("velocities, b_t, psi and potential_v must be finite")
    density_ref, t_parallel, t_perpendicular_ref, b_ref, phi_ref = (
        _field(value, psi, name)
        for value, name in (
            (density_ref_m3, "density_ref_m3"),
            (temperature_parallel_j, "temperature_parallel_j"),
            (temperature_perpendicular_ref_j, "temperature_perpendicular_ref_j"),
            (b_ref_t, "b_ref_t"),
            (phi_ref_v, "phi_ref_v"),
        )
    )
    if (
        np.any(b_t <= 0.0)
        or np.any(density_ref < 0.0)
        or np.any(t_parallel <= 0.0)
        or np.any(t_perpendicular_ref <= 0.0)
        or np.any(b_ref <= 0.0)
    ):
        raise ValueError("field, reference density, or temperatures are invalid")
    coefficient = (b_t - b_ref) / t_parallel + b_ref / t_perpendicular_ref
    if not np.all(np.isfinite(coefficient)) or np.any(coefficient <= 0.0):
        raise FloatingPointError("invariant bi-Maxwellian is not integrable")
    mu = mass_kg * v_perpendicular_m_s**2 / (2.0 * b_t)
    energy = 0.5 * mass_kg * v_parallel_m_s**2 + mu * b_t + charge_c * potential_v
    parallel_scaled = _scaled_difference(0.5 * mass_kg * v_parallel_m_s**2, 0.0, 1.0, t_parallel)
    potential_scaled = _scaled_difference(potential_v, phi_ref, charge_c, t_parallel)
    exponent = -(parallel_scaled + mu * coefficient + potential_scaled)
    if not all(np.all(np.isfinite(x)) for x in (mu, energy, exponent)):
        raise FloatingPointError("invariant energy or exponent exceeds the finite range")
    occupation = 1.0
    if b_plug_left_t is not None:
        b_left, b_right = (
            _field(b_plug_left_t, psi, "b_plug_left_t"),
            _field(b_plug_right_t, psi, "b_plug_right_t"),
        )
        phi_left, phi_right = (
            _field(phi_plug_left_v, psi, "phi_plug_left_v"),
            _field(phi_plug_right_v, psi, "phi_plug_right_v"),
        )
        if np.any(b_left <= 0.0) or np.any(b_right <= 0.0):
            raise ValueError("plug fields must be positive")
        # Compare parallel kinetic energy to barriers relative to this point;
        # subtracting huge absolute energies would destroy the trapped bit.
        barrier_left = _scaled_difference(b_left, b_t, mu, t_parallel) + _scaled_difference(
            phi_left, potential_v, charge_c, t_parallel
        )
        barrier_right = _scaled_difference(b_right, b_t, mu, t_parallel) + _scaled_difference(
            phi_right, potential_v, charge_c, t_parallel
        )
        occupation = loss_cone_refill + (1.0 - loss_cone_refill) * (
            parallel_scaled < np.minimum(barrier_left, barrier_right)
        ).astype(float)
    density_ref, occupation_array = np.broadcast_arrays(density_ref, occupation)
    f0 = np.zeros(density_ref.shape)
    active = (density_ref > 0) & (occupation_array > 0)
    log_normalization = (
        np.log(density_ref[active])
        + 1.5 * (math.log(mass_kg) - math.log(2.0 * math.pi))
        - np.log(t_perpendicular_ref[active])
        - 0.5 * np.log(t_parallel[active])
    )
    with np.errstate(over="ignore", under="ignore"):
        f0[active] = np.exp(log_normalization + exponent[active] + np.log(occupation_array[active]))
    if not np.all(np.isfinite(f0)):
        raise FloatingPointError("phase-space density exceeds the finite output range")
    return {"f0_s3_m6": f0, "energy_j": energy, "magnetic_moment_j_t": mu, "occupation": occupation}


__all__ = ["evaluate_mirror_invariant_distribution"]
