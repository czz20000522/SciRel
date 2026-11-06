"""Device-neutral discrete vector feedback primitive.

The implementation is intentionally source-free.  It models only the declared
sampled state path: error subtraction, per-channel PID terms with a first-order
filtered derivative, an 11-by-10 feedback map, feed-forward addition, and
sample-and-hold enable behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from scirel._result import Result


_SCHEMA = "magnetic-error-current-feedback-discrete"
_CHANNELS = 10
_OUTPUTS = 11

__all__ = ["simulate_feedback"]


def _array(value: Any, *, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    arr = np.asarray(value, dtype=float)
    if shape is not None and arr.shape != shape:
        raise ValueError(f"{name} must have shape {shape}, got {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values")
    return arr


def _vector(controller: Mapping[str, Any], name: str) -> np.ndarray:
    return _array(controller[name], name=name, shape=(_CHANNELS,))


def simulate_feedback(inputs: Mapping[str, Any], controller: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the declared ten-channel discrete feedback state primitive.

    Parameters
    ----------
    inputs : Python mapping
        Sampled input mapping with ``input_time_s`` and ``observation_time_s``
        vectors of shape ``(n,)`` and a ``signals`` mapping. [mixed T, A and s]
        Shape: mapping with ``n`` samples. ``signals`` contains
        ``reference_T`` and ``measured_T`` with shape ``(n, 10)``,
        ``feedforward_current_A`` with shape ``(n, 11)``, and a binary
        ``enable`` vector with shape ``(n,)``. Observation times must equal
        input times in this interpolation-off path.
    controller : Python mapping
        Sampled controller parameters: ten-entry ``P``, ``I``, ``D`` and
        ``N_per_s`` vectors, an ``(11, 10)`` unscaled coefficient matrix,
        coefficient scale, sample period, ten-entry initial filter and
        integrator states, and the declared binary integration controls.
        [mixed controller units] Shape: mapping. ``sample_period_s`` must be
        positive; ``N_per_s`` must be nonnegative; ``internal_reset`` must be
        zero.

    Returns
    -------
    result : scirel._result.Result mapping
        Top-level mapping with ``schema``, ``time_s``, ``values`` and
        ``state_trace``. [mixed T, A, s and controller state units] Shape:
        mapping. ``values`` contains ``total_current_A`` and
        ``feedback_current_A`` with shape ``(n, 11)``, ``pid_components`` with
        shape ``(n, 30)`` in P1, I1, D1 channel order, and ``error_T`` with
        shape ``(n, 10)``. Non-colliding fields support attribute access; the
        key ``values`` collides with ``dict.values`` and must be read as
        ``result["values"]``.

    Raises
    ------
    TypeError
        If ``inputs`` or ``controller`` is not a mapping.
    ValueError
        If required signals are missing, shapes are incompatible, values are
        nonfinite, the enable or integration controls are nonbinary, sample
        timing is invalid, a filter rate is negative, or ``internal_reset`` is
        nonzero.

    See Also
    --------
    scirel.closures.close_reduced_hall_drift : Related current and Hall-state closure.

    Notes
    -----
    Each sample forms ``error = reference - measured``. The enabled P, I and
    filtered-D terms use the supplied gains and the first-order filter
    ``f_k = f_(k-1) + N*dt*(error-f_(k-1))``. The scaled ``(11, 10)`` map
    converts the three ten-channel PID terms to eleven feedback currents, and
    the total current is feed-forward plus feedback while enabled. The first
    sample and each rising enable edge reset the filter and integrator;
    disabled samples retain the last PID and feedback values and emit only the
    feed-forward current. This finite sampled pass makes no plant, saturation,
    closed-loop convergence or stability claim.

    Examples
    --------
    >>> from pathlib import Path
    >>> import json
    >>> from scirel.closures import simulate_discrete_vector_feedback
    >>> root = Path('tests/fixtures/closures/discrete_vector_feedback/evidence')
    >>> result = simulate_discrete_vector_feedback(json.loads((root/'fixtures/feedback-input.json').read_text()), json.loads((root/'source-defaults.json').read_text()))
    >>> assert result['values']['total_current_A'][40] == result['values']['total_current_A'][40]
    >>> assert len(result['time_s']) == 121
    """
    if not isinstance(inputs, Mapping) or not isinstance(controller, Mapping):
        raise TypeError("inputs and controller must be mappings")
    signals = inputs.get("signals")
    if not isinstance(signals, Mapping):
        raise ValueError("inputs['signals'] is required")
    required = ("reference_T", "measured_T", "feedforward_current_A", "enable")
    if any(name not in signals for name in required):
        raise ValueError(
            "signals must contain reference_T, measured_T, feedforward_current_A and enable"
        )

    input_time = _array(inputs.get("input_time_s"), name="input_time_s")
    observation_time = _array(inputs.get("observation_time_s"), name="observation_time_s")
    if input_time.ndim != 1 or observation_time.shape != input_time.shape:
        raise ValueError("input_time_s and observation_time_s must be equal-length vectors")
    n = input_time.size
    if n == 0:
        raise ValueError("at least one sample is required")
    reference = _array(signals["reference_T"], name="reference_T", shape=(n, _CHANNELS))
    measured = _array(signals["measured_T"], name="measured_T", shape=(n, _CHANNELS))
    feedforward = _array(
        signals["feedforward_current_A"], name="feedforward_current_A", shape=(n, _OUTPUTS)
    )
    enable_raw = np.asarray(signals["enable"])
    if enable_raw.shape != (n,) or np.any((enable_raw != 0) & (enable_raw != 1)):
        raise ValueError("enable must be a binary vector with one value per sample")
    enable = enable_raw.astype(bool)

    dt = float(controller["sample_period_s"])
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError("sample_period_s must be positive and finite")
    if n > 1 and not np.allclose(np.diff(input_time), dt, rtol=0.0, atol=1e-12):
        raise ValueError("input_time_s spacing must equal sample_period_s")
    if not np.allclose(observation_time, input_time, rtol=0.0, atol=1e-12):
        raise ValueError("observation_time_s must match input_time_s for interpolation-off mode")

    p_gain = _vector(controller, "P")
    i_gain = _vector(controller, "I")
    d_gain = _vector(controller, "D")
    filter_rate = _vector(controller, "N_per_s")
    if np.any(filter_rate < 0):
        raise ValueError("N_per_s must be nonnegative")
    coefficient = _array(
        controller["coefficient_matrix_unscaled"],
        name="coefficient_matrix_unscaled",
        shape=(_OUTPUTS, _CHANNELS),
    )
    scale = float(controller["coefficient_scale"])
    if not np.isfinite(scale):
        raise ValueError("coefficient_scale must be finite")
    feedback_map = coefficient * scale
    integrator = _array(
        controller["integrator_initial_state"], name="integrator_initial_state", shape=(_CHANNELS,)
    ).copy()
    filt = _array(
        controller["filter_initial_state"], name="filter_initial_state", shape=(_CHANNELS,)
    ).copy()
    integration_enable = np.asarray(controller["internal_integration_enable"], dtype=float)
    if integration_enable.shape != (_CHANNELS,) or np.any(
        (integration_enable != 0) & (integration_enable != 1)
    ):
        raise ValueError("internal_integration_enable must be binary with ten entries")
    if float(controller.get("internal_reset", 0)) != 0:
        raise ValueError("nonzero internal_reset is outside this declared path")

    values = {"total_current_A": [], "feedback_current_A": [], "pid_components": [], "error_T": []}
    trace = {
        "reset_at_sample": [],
        "pre_integrator_state": [],
        "pre_filter_state": [],
        "post_integrator_state": [],
        "post_filter_state": [],
    }
    previous_enable = False
    held_pid = np.zeros(3 * _CHANNELS, dtype=float)
    held_feedback = np.zeros(_OUTPUTS, dtype=float)

    for index in range(n):
        error = reference[index] - measured[index]
        rising = bool(enable[index] and not previous_enable)
        reset = bool(index == 0 or rising)
        if enable[index] and reset:
            integrator = np.zeros(_CHANNELS, dtype=float)
            filt = np.zeros(_CHANNELS, dtype=float)
        # Trace records the effective state after the reset branch and before
        # the current sample's state update.
        trace["reset_at_sample"].append(reset)
        trace["pre_integrator_state"].append(integrator.tolist())
        trace["pre_filter_state"].append(filt.tolist())

        if enable[index]:
            proportional = p_gain * error
            integrated = integrator + integration_enable * (i_gain * error * dt)
            derivative = d_gain * filter_rate * (error - filt)
            filt = filt + filter_rate * dt * (error - filt)
            integrator = integrated
            pid = np.column_stack((proportional, integrated, derivative)).reshape(-1)
            feedback = feedback_map @ (proportional + integrated + derivative)
            held_pid = pid
            held_feedback = feedback
        else:
            pid = held_pid
            feedback = held_feedback
        total = feedforward[index] + feedback if enable[index] else feedforward[index]

        values["error_T"].append(error.tolist())
        values["pid_components"].append(np.asarray(pid).tolist())
        values["feedback_current_A"].append(np.asarray(feedback).tolist())
        values["total_current_A"].append(np.asarray(total).tolist())
        trace["post_integrator_state"].append(integrator.tolist())
        trace["post_filter_state"].append(filt.tolist())
        previous_enable = bool(enable[index])

    return Result(
        {
            "schema": _SCHEMA,
            "time_s": input_time.tolist(),
            "values": values,
            "state_trace": trace,
        }
    )
