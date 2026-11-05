"""Local gyrotropic tension and fixed-flux pressure-slope diagnostics."""

import numpy as np
from ._fixed_flux_derivative import fixed_flux_derivative
from .pointwise_firehose_margin import _firehose_kernel, _mirror_kernel

MU0 = 4e-7 * np.pi


def compute_firehose_mirror_margins(
    p_parallel,
    p_perp,
    magnetic_field,
    mu0=MU0,
    parallel_equilibrium=None,
    *,
    dp_perp_dB=None,
    field_axis=None,
    psi=None,
):
    """Compute local firehose and fixed-flux mirror pressure margins.

    Parameters
    ----------
    p_parallel : array_like, shape (...)
        Parallel pressure samples in ``[Pa]``.  Values must be finite; negative
        values are not rejected.  The shape must exactly match ``p_perp`` and
        ``magnetic_field``, and the sample set must be nonempty.
    p_perp : array_like, shape (...)
        Perpendicular pressure samples in ``[Pa]`` with the same shape and
        finiteness constraints as ``p_parallel``.
    magnetic_field : array_like, shape (...)
        Positive magnetic-field magnitudes in ``[T]`` at the same samples.
        Duplicate field values are allowed with an explicit derivative;
        sampled fixed-flux lines require strict monotonicity.
    mu0 : real scalar, optional
        Positive finite magnetic permeability in ``[H/m]``.  The default is
        ``4*pi*1e-7``.
    parallel_equilibrium : dict or None, optional
        Optional upstream diagnostic mapping in
        ``[mixed, defined by upstream fields]``.  Only its ``error`` and
        ``max_relative_error`` entries are forwarded; this function does not
        validate their units, shapes, or finiteness.  The default is ``None``.
    dp_perp_dB : real scalar, array_like, or callable, optional
        Explicit fixed-psi derivative ``(partial p_perp / partial B)_psi`` in
        ``[Pa/T]``.  A scalar or array must broadcast exactly to the sample
        shape; a callable is evaluated as ``callable(B, psi)``.  It cannot be
        combined with ``field_axis``.
    field_axis : integer, optional
        Axis whose lines vary magnetic-field magnitude at fixed ``psi`` in
        ``[axis index]``.  With no explicit derivative, each line must contain
        at least two unique strictly monotone field samples.
    psi : real scalar or array_like, optional
        Flux labels broadcastable to the sample shape in
        ``[consistent caller flux coordinate]``.  It is mandatory and exactly
        constant along ``field_axis`` for sampled derivatives, and is forwarded
        to an explicit derivative callable otherwise.

    Returns
    -------
    firehose_margin : ndarray of float64, same shape as the inputs
        Pointwise ``B**2 / mu0 + p_perp - p_parallel`` in ``[Pa]``.
    mirror_margin : ndarray of float64, same shape as the inputs
        Fixed-flux total-pressure-slope margin
        ``B**2 / mu0 + B * dp_perp_dB`` in ``[Pa]``.
    firehose_stable : bool
        ``True`` exactly when every sampled firehose margin is strictly
        positive in ``[boolean]``.
    mirror_stable : bool
        ``True`` exactly when every sampled mirror margin is strictly positive
        in ``[boolean]``.
    min_firehose_margin : float
        Minimum sampled firehose margin in ``[Pa]``.
    min_mirror_margin : float
        Minimum sampled mirror margin in ``[Pa]``.
    parallel_equilibrium_error : object or None
        Unmodified ``parallel_equilibrium['error']`` when supplied, otherwise
        ``None``, in
        ``[upstream-defined, normally Pa, or not applicable]``.
    max_parallel_equilibrium_error : object or None
        Unmodified ``parallel_equilibrium['max_relative_error']`` when
        supplied, otherwise ``None``, in
        ``[upstream-defined, normally dimensionless, or not applicable]``.
    dp_perp_dB : ndarray of float64, same shape as the pressures
        Fixed-psi derivative actually used by the diagnostic in ``[Pa/T]``.
    derivative_method : str
        Description of the derivative source in ``[text]``: either an explicit
        fixed-flux derivative or a declared fixed-flux axis finite difference.
    criterion : str
        Criterion identifier in ``[text]``, equal to
        ``local_gyrotropic_tension_and_fixed_flux_total_pressure_slope``.

    Raises
    ------
    ValueError
        If derivative information is missing or conflicts with ``field_axis``,
        array shapes or sample sets are invalid, values are nonfinite, the
        magnetic field is not strictly positive, a field axis is invalid,
        ``mu0`` is not positive and finite, or ``parallel_equilibrium`` is not
        a dictionary.
    FloatingPointError
        If a final local pressure margin cannot be represented as finite
        float64.
    TypeError
        If a numeric input cannot be converted to float64 or a derivative
        callable has an incompatible call signature.

    See Also
    --------
    scirel.diagnostics.compute_pointwise_firehose_margin
        Evaluate only the pointwise firehose margin, without a derivative or
        aggregate flags.
    scirel.diagnostics.compute_parallel_pressure_residual
        Check the parallel-pressure compatibility relation with a fixed-flux
        derivative.

    Notes
    -----
    The firehose margin is ``B**2 / mu0 + p_perp - p_parallel``.  The mirror
    margin is the fixed-psi derivative of total pressure,

    ``B * d[p_perp + B**2 / (2*mu0)] / dB = B**2 / mu0 + B * dp_perp_dB``.

    The positive total-pressure-slope criterion assumes a gyrotropic, no-flow
    equilibrium pressure law.  For an invariant bi-Maxwellian it becomes
    ``1 - beta_perp * (T_perp / T_parallel - 1) > 0``.  It is not a global
    stability proof or a finite-Larmor-radius, finite-wave-number, or Hall-flow
    calculation.  The implementation follows the explicit total-pressure
    derivative and kinetic bi-Maxwellian threshold rather than an opposing sign
    printed in one source; no publisher-confirmed erratum is asserted.

    The result is a plain ``dict``.  No spatial field sorting or undocumented
    zero-derivative fallback is used.  Normal values retain ordinary float64
    operation order; dangerous cancellation or intermediate range loss uses an
    exact binary-rational evaluation before one final float64 rounding.

    Examples
    --------
    >>> from scirel.diagnostics.firehose_mirror_margins import compute_firehose_mirror_margins
    >>> r=compute_firehose_mirror_margins(1.,2.,1.,mu0=1.,dp_perp_dB=-4.)
    >>> assert abs(float(r['firehose_margin'])-2.)<1e-12
    >>> assert abs(float(r['mirror_margin'])+3.)<1e-12
    >>> assert r['firehose_stable'] and not r['mirror_stable']
    >>> r=compute_firehose_mirror_margins(1e100,1e100,1.,mu0=1.,dp_perp_dB=0.)
    >>> assert float(r['firehose_margin'])==1. and r['firehose_stable']
    """
    p_parallel, p_perp, magnetic_field = (
        np.asarray(x, dtype=float) for x in (p_parallel, p_perp, magnetic_field)
    )
    if p_parallel.shape != p_perp.shape or p_parallel.shape != magnetic_field.shape:
        raise ValueError("p_parallel, p_perp, and magnetic_field must have the same shape")
    if not np.all(np.isfinite(p_parallel)):
        raise ValueError("parallel pressure must be finite")
    if not np.isfinite(mu0) or mu0 <= 0:
        raise ValueError("mu0 must be positive and finite")
    derivative, method = fixed_flux_derivative(
        p_perp, magnetic_field, derivative=dp_perp_dB, field_axis=field_axis, psi=psi
    )
    firehose = _firehose_kernel(p_parallel, p_perp, magnetic_field, mu0)
    mirror = _mirror_kernel(magnetic_field, derivative, mu0)
    if not np.all(np.isfinite(firehose)) or not np.all(np.isfinite(mirror)):
        raise FloatingPointError("local pressure margins are not finite")
    if parallel_equilibrium is not None and not isinstance(parallel_equilibrium, dict):
        raise ValueError("parallel_equilibrium must be a mapping when provided")
    state = parallel_equilibrium or {}
    return {
        "firehose_margin": firehose,
        "mirror_margin": mirror,
        "firehose_stable": bool(np.min(firehose) > 0),
        "mirror_stable": bool(np.min(mirror) > 0),
        "min_firehose_margin": float(np.min(firehose)),
        "min_mirror_margin": float(np.min(mirror)),
        "parallel_equilibrium_error": state.get("error"),
        "max_parallel_equilibrium_error": state.get("max_relative_error"),
        "dp_perp_dB": derivative,
        "derivative_method": method,
        "criterion": "local_gyrotropic_tension_and_fixed_flux_total_pressure_slope",
    }


__all__ = ["compute_firehose_mirror_margins"]
