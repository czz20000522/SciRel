"""A compact one-dimensional Vlasov--Poisson integrator with explicit discrete Poisson closure and vectorized state validation."""

from __future__ import annotations

from math import lgamma, pi, sqrt

import numpy as np

__all__ = [
    "vp_distribution",
    "vp_init",
    "vp_field",
    "vp_rhs",
    "vp_rk4_step",
    "vp_evolve",
    "vp_envelope",
    "vp_diagnostic",
    "solve_vlasov_poisson",
]


def _finite_vectors(*values):
    """Convert aligned one-dimensional numerical vectors to NumPy arrays."""
    arrays = [np.asarray(value) for value in values]
    if not arrays or arrays[0].ndim != 1 or arrays[0].size < 2:
        raise ValueError("velocity arrays must be one-dimensional with at least two nodes")
    shape = arrays[0].shape
    if any(array.shape != shape or not np.isfinite(array).all() for array in arrays):
        raise ValueError("velocity arrays must have the same shape and finite values")
    return arrays


def _positive_scalar(value, name):
    """Require a finite scalar greater than zero."""
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")


def vp_distribution(vv, Fn=2, *, k=0.15, kappa=1.0, cutoff_mode="weak"):
    """Evaluate the derivative ``f0'(v)`` of a built-in equilibrium on a velocity grid.

    Velocities are in units of ``v_t = sqrt(T/m)`` for ``Fn=1``. All
    families are normalized to unit density.

    * ``Fn=1``: Maxwellian ``f0 = exp(-v**2/2)/sqrt(2*pi)`` (unit variance).
    * ``Fn=2``: kappa family ``f0 = Gamma(kappa)/(Gamma(kappa-1/2)*sqrt(2*pi*kappa))
      * (1 + v**2/(2*kappa))**(-kappa)``. This is the one-dimensional kappa form
      with ``theta**2 = 2``; its variance is ``2*kappa/(2*kappa-3)`` for
      ``kappa > 3/2`` (infinite otherwise), so it is not at unit temperature.
      For a kappa distribution with a prescribed temperature, build ``f0'`` on
      the grid yourself and pass it to ``vp_init(Fn=None, df0dv=...)``.
      ``kappa=1`` is the Lorentzian, for which the exact root
      ``omega = 1 - i*sqrt(2)*k`` is returned as ``(wr, wi)``.
    * ``Fn=3``: triangle ``max(0, 1 - |v|)``.
    * ``Fn=4``: cutoff slowing-down distribution (see the contract).

    Returns ``(f0_prime, wr, wi)``; ``wr, wi`` are None except for the Lorentzian.

    Parameters
    ----------
    vv : real array, shape [N]
        Velocity nodes. Finite one-dimensional; aligned with df and df0dv when
        applicable.
    Fn : integer, default 2
        Built-in equilibrium, unit density: 1 Maxwellian exp(-v^2/2)/sqrt(2pi)
        (unit variance); 2 kappa Gamma(kappa)/(Gamma(kappa-1/2) sqrt(2 pi
        kappa)) (1+v^2/(2 kappa))^-kappa, i.e. theta^2=2 with variance
        2kappa/(2kappa-3), NOT unit temperature; 3 triangle max(0,1-|v|); 4
        cutoff slowing-down. One of 1,2,3,4.
    k : real scalar, default 0.15
        Spatial Fourier wavenumber in inverse Debye length. Positive finite.
    kappa : real scalar, default 1.0
        Kappa index of the Fn=2 family. The family is not rescaled to unit
        variance; for a kappa distribution at a prescribed temperature pass its
        derivative as df0dv to vp_init. For Fn=2 finite >1/2.
    cutoff_mode : string, default 'weak'
        Fn4 weak derivative or explicit source smooth-only forcing. weak or
        smooth; weak Fn4 requires increasing uniform grid.

    Returns
    -------
    result : tuple, shape As described in output mapping or tuple.
        Tuple (g,wr,wi): g [N], theoretical wr=1 and wi=-k sqrt(2) only for
        Fn=2,kappa=1; otherwise theory is None. Tuple of finite derivative and
        optional theoretical frequencies; no hidden state.

    Raises
    ------
    FloatingPointError
        FloatingPointError when the derivative is not finite.
    ValueError
        ValueError for unsupported Fn/cutoff_mode, nonfinite or non-vector vv,
        invalid kappa, invalid k or a non-increasing/nonuniform weak-cutoff
        grid.

    See Also
    --------
    vp_init : Build an initial state from this family.

    Examples
    --------
    >>> from scirel.kinetic.vlasov_poisson import vp_distribution
    >>> import numpy as np
    >>> g,wr,wi=vp_distribution(np.linspace(-6,6,101),4)
    >>> assert g.shape == (101,)
    """
    if cutoff_mode not in ("weak", "smooth"):
        raise ValueError("cutoff_mode must be weak or smooth")
    velocity = np.asarray(vv, dtype=float)
    if velocity.ndim != 1 or not np.isfinite(velocity).all():
        raise ValueError("vv must be a finite real vector")
    _positive_scalar(k, "k")

    real_frequency = imaginary_frequency = None
    if Fn == 1:
        derivative = -velocity * np.exp(-velocity * velocity / 2.0) / sqrt(2.0 * pi)
    elif Fn == 2:
        if not np.isfinite(kappa) or kappa <= 0.5:
            raise ValueError("kappa must exceed 1/2 for a normalized distribution")
        amplitude = np.exp(lgamma(kappa) - lgamma(kappa - 0.5)) / sqrt(2.0 * pi * kappa)
        derivative = (
            -amplitude * velocity * (1.0 + velocity * velocity / (2.0 * kappa)) ** (-kappa - 1.0)
        )
        if kappa == 1:
            real_frequency, imaginary_frequency = 1.0, -k * sqrt(2.0)
    elif Fn == 3:
        derivative = np.where(
            (velocity > -1.0) & (velocity < 0.0),
            1.0,
            np.where((velocity > 0.0) & (velocity < 1.0), -1.0, 0.0),
        )
    elif Fn == 4:
        derivative = _slowing_down_derivative(velocity, cutoff_mode)
    else:
        raise ValueError("Fn must be one of 1, 2, 3, 4")

    if not np.isfinite(derivative).all():
        raise FloatingPointError("distribution derivative is not representable")
    return derivative, real_frequency, imaginary_frequency


def _slowing_down_derivative(velocity, cutoff_mode):
    """Return the smooth derivative and, for ``weak``, deposit cutoff jumps."""
    thermal_speed = sqrt(2.0)
    amplitude = 3.0 * sqrt(3.0) * thermal_speed**2 / (4.0 * pi)
    derivative = np.zeros_like(velocity)
    inside = np.abs(velocity) <= 4.0
    selected = velocity[inside]
    denominator = np.abs(selected) ** 3 + thermal_speed**3
    derivative[inside] = -np.sign(selected) * 3.0 * selected**2 / denominator**2 * amplitude
    derivative[np.abs(velocity) == 4.0] *= 0.5
    if cutoff_mode == "weak":
        _require_uniform_grid(velocity)
        spacing = float(velocity[1] - velocity[0])
        jump = amplitude / (4.0**3 + thermal_speed**3)
        _deposit_point_mass(derivative, velocity, -4.0, jump, spacing)
        _deposit_point_mass(derivative, velocity, 4.0, -jump, spacing)
    return derivative


def _require_uniform_grid(velocity):
    """Validate the grid required for finite-volume jump deposition."""
    if velocity.size < 2 or np.any(np.diff(velocity) <= 0.0):
        raise ValueError("weak cutoff derivative requires an increasing uniform grid")
    spacing = float(velocity[1] - velocity[0])
    if not np.allclose(np.diff(velocity), spacing, rtol=1e-10, atol=1e-13):
        raise ValueError("weak cutoff derivative requires an increasing uniform grid")


def _deposit_point_mass(values, grid, location, mass, spacing):
    """Deposit a point mass on the two bracketing nodes."""
    if not (grid[0] <= location <= grid[-1]):
        return
    right = int(np.searchsorted(grid, location))
    if right == 0:
        values[0] += mass / spacing
    elif right == grid.size:
        values[-1] += mass / spacing
    else:
        fraction = (location - grid[right - 1]) / spacing
        values[right - 1] += mass * (1.0 - fraction) / spacing
        values[right] += mass * fraction / spacing


def vp_field(df, k, dv):
    """Close Poisson's equation, ``E = i * dv * sum(df) / k``.

    Parameters
    ----------
    df : complex array, shape [N]
        Complex perturbation on velocity nodes. Finite one-dimensional N>=2.
    k : real scalar
        Nonzero spatial Fourier wavenumber. Finite and nonzero.
    dv : real scalar
        Uniform velocity quadrature spacing. Positive finite.

    Returns
    -------
    result : complex scalar, shape As described in output mapping or tuple.
        Complex scalar electric field satisfying ikE=-dv sum(df). Finite complex
        scalar equal to the discrete Poisson field.

    Raises
    ------
    FloatingPointError
        FloatingPointError when the computed field is not finite.
    ValueError
        ValueError for non-vector/nonfinite df, nonfinite or zero k, or
        nonpositive/nonfinite dv.

    See Also
    --------
    vp_init : Initial state with a Poisson-consistent field.
    vp_evolve : Uses this closure at every step.

    Examples
    --------
    >>> from scirel.kinetic.vlasov_poisson import vp_field
    >>> assert vp_field([1,2],.5,.1) == .6000000000000001j
    """
    _positive_scalar(dv, "dv")
    if not np.isfinite(k) or k == 0:
        raise ValueError("k must be finite and nonzero")
    (distribution,) = _finite_vectors(df)
    field = (1j / k) * dv * np.sum(distribution)
    if not np.isfinite(field):
        raise FloatingPointError("Poisson field is not representable")
    return field


def vp_rhs(df, dE, vv, df0dv, k):
    """Evaluate the linear Vlasov RHS for one shared electric field."""
    distribution, velocity, derivative = _finite_vectors(df, vv, df0dv)
    if np.ndim(dE) != 0 or not np.isfinite(dE) or not np.isfinite(k) or k == 0:
        raise ValueError("dE must be a finite scalar and k finite and nonzero")
    rhs = -1j * k * velocity * distribution + dE * derivative
    if not np.isfinite(rhs).all():
        raise FloatingPointError("Vlasov RHS is not representable")
    return rhs


def vp_init(
    Fn=2, kappa=1.0, nv=2048, dt=0.01, nt=2000, *, k=0.15, vmax=20.0, df_initial=None, df0dv=None
):
    """Construct an initial state for :func:`vp_evolve` that satisfies discrete Poisson closure.

    The velocity grid is ``vv = linspace(-vmax, vmax, nv + 1)``. The linearized
    equation is ``d(df)/dt = -i k v df + E f0'(v)`` with ``i k E = -integral(df) dv``.

    Parameters
    ----------
    Fn : int or None, default 2
        Built-in equilibrium family (see :func:`vp_distribution`). Pass
        ``Fn=None`` together with ``df0dv`` to use your own equilibrium.
    kappa : float, default 1.0
        Kappa index or family parameter used by the built-in family.
    nv : int, default 2048
        Number of equal velocity intervals; at least 2.
    dt : float, default 0.01
        Time step in inverse plasma frequency; positive.
    nt : int, default 2000
        Number of time steps; nonnegative.
    k : float, default 0.15
        Spatial Fourier wavenumber in inverse Debye length; positive.
    vmax : float, default 20.0
        Half-width of the velocity window, in the grid's velocity units.
    df_initial : array_like, optional
        Initial perturbation ``df(v, 0)`` on ``vv`` (length ``nv + 1``, real or
        complex). The default is ``0.1 * exp(-v**2)``, a fixed Gaussian in the
        grid's velocity units that is *not* proportional to ``f0``; pass your
        own when the initial condition matters.
    df0dv : array_like, optional
        Equilibrium derivative ``f0'(v)`` sampled on ``vv`` (length ``nv + 1``),
        used instead of a built-in family. Requires ``Fn=None``.

    Returns
    -------
    result : dict, shape As described in output mapping or tuple.
        State mapping: Fn,kappa,nv,dt,nt,k,vmax,vmin,dv,TR; vv,df,df0dv [nv+1];
        scalar dE; dEt,tt [nt+1]; wr,wi are kappa=1 theory or None. Fields and
        arrays are independently owned. State mapping with finite arrays and an
        initial field satisfying discrete Poisson closure.

    Raises
    ------
    FloatingPointError
        FloatingPointError if the generated derivative or Poisson field is not
        finite.
    ValueError
        ValueError for invalid scalar controls, a distribution branch that
        rejects the selected parameters, df_initial or df0dv of the wrong length
        or nonfinite, a complex df0dv, or df0dv given together with Fn (or
        Fn=None without df0dv).

    See Also
    --------
    vp_distribution : Built-in equilibrium families.
    vp_evolve : Advance the returned state.
    solve_vlasov_poisson : vp_init followed by vp_evolve.

    Notes
    -----
    The state records ``TR = 2*pi/(k*dv)``, the recurrence time of the
    discrete velocity grid; fit damping only well before it.

    Examples
    --------
    >>> from scirel.kinetic.vlasov_poisson import vp_init
    >>> s=vp_init(nv=32,nt=5)
    >>> assert s["df"].shape == (33,)
    """
    if isinstance(nv, bool) or not isinstance(nv, (int, np.integer)) or nv < 2:
        raise ValueError("nv must be an integer >= 2")
    if isinstance(nt, bool) or not isinstance(nt, (int, np.integer)) or nt < 0:
        raise ValueError("nt must be a nonnegative integer")
    _positive_scalar(dt, "dt")
    _positive_scalar(k, "k")
    _positive_scalar(vmax, "vmax")

    velocity = np.linspace(-vmax, vmax, nv + 1)
    spacing = 2.0 * vmax / nv
    if (Fn is None) != (df0dv is not None):
        raise ValueError("give either a built-in Fn or Fn=None with a custom df0dv array")
    if df0dv is None:
        derivative, real_frequency, imaginary_frequency = vp_distribution(
            velocity, Fn, k=k, kappa=kappa
        )
    else:
        derivative = _grid_array(df0dv, velocity, "df0dv").real
        if np.iscomplexobj(np.asarray(df0dv)) and np.any(np.imag(df0dv) != 0):
            raise ValueError("df0dv must be real")
        real_frequency = imaginary_frequency = None
    if df_initial is None:
        distribution = (0.1 * np.exp(-velocity * velocity)).astype(complex)
    else:
        distribution = _grid_array(df_initial, velocity, "df_initial").astype(complex)
    field = vp_field(distribution, k, spacing)
    history = np.zeros(nt + 1, dtype=complex)
    history[0] = field
    return {
        "Fn": Fn,
        "kappa": kappa,
        "nv": nv,
        "dt": dt,
        "nt": nt,
        "k": k,
        "vmax": vmax,
        "vmin": -vmax,
        "dv": spacing,
        "TR": 2.0 * pi / (k * spacing),
        "vv": velocity,
        "df": distribution,
        "df0dv": derivative,
        "dE": field,
        "dEt": history,
        "tt": np.arange(nt + 1) * dt,
        "wr": real_frequency,
        "wi": imaginary_frequency,
    }


def _grid_array(values, velocity, name):
    """A finite array sampled on the vp_init velocity grid."""
    array = np.asarray(values)
    if (
        array.dtype.kind not in "iufc"
        or array.shape != velocity.shape
        or not np.isfinite(array).all()
    ):
        raise ValueError(
            f"{name} must be a finite numeric array with one value per velocity node (nv + 1)"
        )
    return array


def vp_rk4_step(df, dE, vv, df0dv, k, dv, dt):
    """Advance one classical RK4 step while enforcing Poisson at each stage."""
    _positive_scalar(dt, "dt")
    distribution, velocity, derivative = _finite_vectors(df, vv, df0dv)
    closed_field = vp_field(distribution, k, dv)
    if (
        np.ndim(dE) != 0
        or not np.isfinite(dE)
        or not np.isclose(dE, closed_field, rtol=1e-12, atol=1e-14)
    ):
        raise ValueError("incoming dE violates the discrete Poisson constraint")

    def rhs(state):
        return -1j * k * velocity * state + vp_field(state, k, dv) * derivative

    stage_a = rhs(distribution)
    stage_b = rhs(distribution + 0.5 * dt * stage_a)
    stage_c = rhs(distribution + 0.5 * dt * stage_b)
    stage_d = rhs(distribution + dt * stage_c)
    updated = distribution + (dt / 6.0) * (stage_a + 2.0 * stage_b + 2.0 * stage_c + stage_d)
    if not np.isfinite(updated).all():
        raise FloatingPointError("nonfinite RK4 state; reduce dt or revise velocity grid")
    return updated, vp_field(updated, k, dv)


def vp_evolve(state):
    """Advance ``nt`` RK4 steps and return a copied state with its field history.

    ``state`` is a mapping from :func:`vp_init`. To start from another
    perturbation or equilibrium, pass ``df_initial`` or ``df0dv`` to
    ``vp_init`` rather than editing the mapping; an edited ``df`` must come
    with ``dE = vp_field(df, k, dv)`` or the call raises. The input is not
    mutated.

    Parameters
    ----------
    state : dict, shape mapping
        State mapping produced by vp_init. To start from another perturbation or
        equilibrium pass df_initial or df0dv to vp_init; an edited df needs dE =
        vp_field(df,k,dv) or the call raises. Complete VP state; finite aligned
        arrays; Poisson-closed initial field; integer nt>=0.

    Returns
    -------
    result : dict, shape As described in output mapping or tuple.
        State mapping: Fn,kappa,nv,dt,nt,k,vmax,vmin,dv,TR; vv,df,df0dv [nv+1];
        scalar dE; dEt,tt [nt+1]; wr,wi are kappa=1 theory or None. Fields and
        arrays are independently owned. Input is not mutated; repeated calls
        start a new local time trace from supplied df. Copied state with finite
        field history and closed initial field.

    Raises
    ------
    FloatingPointError
        FloatingPointError propagated from a nonfinite RK4 state or field.
    ValueError
        ValueError for missing/invalid state controls or an initial Poisson
        inconsistency.

    See Also
    --------
    vp_init : Build the state.
    vp_diagnostic : Fit damping and frequency from the history.

    Examples
    --------
    >>> from scirel.kinetic.vlasov_poisson import vp_init,vp_evolve
    >>> s=vp_evolve(vp_init(nv=32,nt=5))
    >>> assert s["dEt"].shape == (6,)
    """
    evolved = {
        key: value.copy() if isinstance(value, np.ndarray) else value
        for key, value in state.items()
    }
    nt = evolved["nt"]
    if isinstance(nt, bool) or not isinstance(nt, (int, np.integer)) or nt < 0:
        raise ValueError("nt must be a nonnegative integer")
    history = np.empty(nt + 1, dtype=complex)
    history[0] = vp_field(evolved["df"], evolved["k"], evolved["dv"])
    if not np.isclose(history[0], evolved["dE"], rtol=1e-12, atol=1e-14):
        raise ValueError("initial state violates the discrete Poisson constraint")
    for index in range(nt):
        evolved["df"], evolved["dE"] = vp_rk4_step(
            evolved["df"],
            evolved["dE"],
            evolved["vv"],
            evolved["df0dv"],
            evolved["k"],
            evolved["dv"],
            evolved["dt"],
        )
        history[index + 1] = evolved["dE"]
    evolved["dEt"] = history
    evolved["tt"] = np.arange(nt + 1) * evolved["dt"]
    return evolved


def vp_envelope(dEt, tt, *, wr=None, wi=None):
    """Return ``log(abs(E))`` and, when supplied, the theoretical envelope."""
    field, times = _finite_vectors(dEt, tt)
    if np.iscomplexobj(times) or np.any(np.diff(times) <= 0):
        raise ValueError("tt must be real and strictly increasing")
    with np.errstate(divide="ignore"):
        logarithm = np.log(np.abs(field))
        theory = None if wi is None else np.log(abs(field[0])) + wi * (times - times[0])
    return {"ttmp": times.copy(), "lndE": logarithm, "lndEe": theory, "wr": wr, "wi": wi}


def vp_diagnostic(dEt, tt, *, start=None, end=None):
    """Fit peak spacing and logarithmic damping from an oscillatory field.

    Parameters
    ----------
    dEt : complex array, shape [T]
        Complex electric field time series. Finite one-dimensional T>=2.
    tt : real array, shape [T]
        Sampling times. Finite strictly increasing, same shape as dEt.
    start : real scalar or None, default None
        Window start; None means 5% of actual time span. Finite; see
        function-specific scientific conditions.
    end : real scalar or None, default None
        Window end; None means 80% of actual time span. Finite; see
        function-specific scientific conditions.

    Returns
    -------
    result : dict, shape As described in output mapping or tuple.
        Mapping peak_indices,peak_times,peak_log_magnitudes [P>=2], scalar
        omega,gamma,gammas; gammas aliases gamma. Diagnostic mapping with finite
        fit when enough peaks are available; otherwise the declared status.

    Raises
    ------
    ValueError
        ValueError for misaligned/nonfinite vectors, non-real/non-increasing
        times, or fewer than two isolated nonzero peaks.

    See Also
    --------
    vp_evolve : Produces the field history.
    solve_maxwellian_electrostatic_mode : Dispersion-relation root to compare with.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic.vlasov_poisson import vp_diagnostic
    >>> t=np.linspace(0,30,3001)
    >>> r=vp_diagnostic(np.exp(-.1*t)*np.cos(t),t)
    >>> assert abs(r["gamma"]+.1) < 1e-4
    """
    field, times = _finite_vectors(dEt, tt)
    if np.iscomplexobj(times) or np.any(np.diff(times) <= 0):
        raise ValueError("tt must be real and strictly increasing")
    lower = times[0] + 0.05 * (times[-1] - times[0]) if start is None else start
    upper = times[0] + 0.8 * (times[-1] - times[0]) if end is None else end
    magnitude = np.abs(field)
    indices = (
        np.flatnonzero((magnitude[1:-1] > magnitude[:-2]) & (magnitude[1:-1] > magnitude[2:])) + 1
    )
    indices = indices[
        (times[indices] >= lower) & (times[indices] <= upper) & (magnitude[indices] > 0)
    ]
    if indices.size < 2:
        raise ValueError("at least two isolated nonzero field maxima are required")
    peak_times = times[indices]
    peak_logs = np.log(magnitude[indices])
    centered = peak_times - peak_times.mean()
    gamma = float(centered @ (peak_logs - peak_logs.mean()) / (centered @ centered))
    return {
        "peak_indices": indices,
        "peak_times": peak_times,
        "peak_log_magnitudes": peak_logs,
        "omega": float(pi / np.mean(np.diff(peak_times))),
        "gamma": gamma,
        "gammas": gamma,
    }


def solve_vlasov_poisson(Fn=2, kappa=1.0, nv=2048, dt=0.01, nt=2000, *, k=0.15, vmax=20.0):
    """Compose initialization, evolution, envelope, and an optional diagnostic.

    Parameters
    ----------
    Fn : integer, default 2
        Built-in equilibrium, unit density: 1 Maxwellian exp(-v^2/2)/sqrt(2pi)
        (unit variance); 2 kappa Gamma(kappa)/(Gamma(kappa-1/2) sqrt(2 pi
        kappa)) (1+v^2/(2 kappa))^-kappa, i.e. theta^2=2 with variance
        2kappa/(2kappa-3), NOT unit temperature; 3 triangle max(0,1-|v|); 4
        cutoff slowing-down. One of 1,2,3,4.
    kappa : real scalar, default 1.0
        Kappa index of the Fn=2 family. The family is not rescaled to unit
        variance; for a kappa distribution at a prescribed temperature pass its
        derivative as df0dv to vp_init. For Fn=2 finite >1/2.
    nv : integer, default 2048
        Number of equal velocity intervals. Integer >=2, boolean rejected.
    dt : real scalar, default 0.01
        Time step in inverse plasma frequency. Positive finite.
    nt : integer, default 2000
        Exact number of ordered time steps. Nonnegative integer, boolean
        rejected.
    k : real scalar, default 0.15
        Spatial Fourier wavenumber in inverse Debye length. Positive finite.
    vmax : real scalar, default 20.0
        Symmetric velocity window extent. Positive finite.

    Returns
    -------
    result : dict, shape As described in output mapping or tuple.
        Mapping state (complete VP state), envelope, diagnostic,
        diagnostic_status. For nt=0 envelope and diagnostic are None; inadequate
        peaks give diagnostic=None and reason while retaining evolution.
        Composed final state and diagnostics; no claim beyond the declared time
        window and grid.

    Raises
    ------
    FloatingPointError
        FloatingPointError from a nonfinite derivative, field or RK4 state is
        propagated.
    ValueError
        ValueError from initialization, state validation or Poisson closure is
        propagated.

    See Also
    --------
    vp_init : Initialization step.
    vp_evolve : Time advance.
    vp_diagnostic : Rate and frequency fit.

    Examples
    --------
    >>> from scirel.kinetic.vlasov_poisson import solve_vlasov_poisson
    >>> r=solve_vlasov_poisson(nv=32,nt=5)
    >>> assert r["state"]["dEt"].shape == (6,)
    """
    state = vp_evolve(vp_init(Fn, kappa, nv, dt, nt, k=k, vmax=vmax))
    if nt == 0:
        return {
            "state": state,
            "envelope": None,
            "diagnostic": None,
            "diagnostic_status": "insufficient samples",
        }
    envelope = vp_envelope(state["dEt"], state["tt"], wr=state["wr"], wi=state["wi"])
    try:
        diagnostic = vp_diagnostic(state["dEt"], state["tt"])
        status = "available"
    except ValueError as error:
        diagnostic, status = None, str(error)
    return {
        "state": state,
        "envelope": envelope,
        "diagnostic": diagnostic,
        "diagnostic_status": status,
    }
