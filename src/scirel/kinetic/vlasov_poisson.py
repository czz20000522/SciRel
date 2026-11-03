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
    """Evaluate the selected equilibrium derivative on a velocity grid."""
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
    """Close Poisson's equation, ``E = i * dv * sum(df) / k``."""
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


def vp_init(Fn=2, kappa=1.0, nv=2048, dt=0.01, nt=2000, *, k=0.15, vmax=20.0):
    """Construct an independent initial state satisfying discrete Poisson closure."""
    if isinstance(nv, bool) or not isinstance(nv, (int, np.integer)) or nv < 2:
        raise ValueError("nv must be an integer >= 2")
    if isinstance(nt, bool) or not isinstance(nt, (int, np.integer)) or nt < 0:
        raise ValueError("nt must be a nonnegative integer")
    _positive_scalar(dt, "dt")
    _positive_scalar(k, "k")
    _positive_scalar(vmax, "vmax")

    velocity = np.linspace(-vmax, vmax, nv + 1)
    spacing = 2.0 * vmax / nv
    derivative, real_frequency, imaginary_frequency = vp_distribution(
        velocity, Fn, k=k, kappa=kappa
    )
    distribution = (0.1 * np.exp(-velocity * velocity)).astype(complex)
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
    """Advance ``nt`` steps and return a copied state with its field history."""
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
    """Fit peak spacing and logarithmic damping from an oscillatory field."""
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
    """Compose initialization, evolution, envelope, and an optional diagnostic."""
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
