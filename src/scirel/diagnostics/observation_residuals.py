"""Fixed-layout normalized residuals for declared observation channels."""

from __future__ import annotations
from collections.abc import Mapping
import numpy as np

from scirel._result import Result

_CHANNELS = ("density", "electron_temperature", "p_parallel", "p_perp")


def _observation_layout(observations):
    """Validate observations independently of predictions and freeze their order."""
    if not isinstance(observations, Mapping) or not observations:
        raise ValueError("observations must contain at least one usable signal")
    unknown = set(observations) - {"flux_loops", "thomson"}
    if unknown:
        raise ValueError(f"unknown observation kinds: {sorted(unknown)}")
    layout = []
    if "flux_loops" in observations:
        layout.append(("flux_loops", None, observations["flux_loops"]))
    if "thomson" in observations:
        observed = observations["thomson"]
        if not isinstance(observed, Mapping):
            raise ValueError("thomson observation must be a mapping")
        unknown = set(observed) - set(_CHANNELS) - {"points"}
        if unknown:
            raise ValueError(f"unknown thomson channels: {sorted(unknown)}")
        if not any(key in observed for key in _CHANNELS):
            raise ValueError("thomson must request at least one usable signal")
        layout.extend(("thomson", key, observed[key]) for key in _CHANNELS if key in observed)
    validated = []
    for kind, key, observation in layout:
        label = kind if key is None else f"{kind}.{key}"
        if not isinstance(observation, Mapping) or "values" not in observation:
            raise ValueError(f"{label} observation must contain values")
        values = np.asarray(observation["values"], dtype=float)
        if not values.size or not np.all(np.isfinite(values)):
            raise ValueError(f"{label} values must be nonempty and finite")
        try:
            sigma = np.broadcast_to(
                np.asarray(observation.get("sigma", 1.0), dtype=float), values.shape
            )
        except ValueError as exc:
            raise ValueError(
                f"{label} sigma must be scalar or broadcast exactly to the observation shape"
            ) from exc
        if not np.all(np.isfinite(sigma)) or np.any(sigma <= 0.0):
            raise ValueError(f"{label} values and sigma must be finite and sigma must be positive")
        unit = observation.get("unit")
        if unit is not None and (not isinstance(unit, str) or not unit.strip()):
            raise ValueError(f"{label} unit must be a nonempty string")
        validated.append((kind, key, values, sigma, unit))
    return validated


def reduce_observation_residuals(*, predicted, observations):
    """Reduce declared observations to ordered normalized residuals.

    Parameters
    ----------
    predicted : mapping
        Mapping containing a ``flux_loops`` array and/or a ``thomson`` mapping
        of profile arrays.  Entries use ``[same as the corresponding values]``.
        When an observation declares a unit, a matching nested ``units``
        mapping is required.  Every requested channel must be present, finite,
        and have exactly the observation shape; no missing channel is skipped.
    observations : mapping
        Nonempty ``flux_loops`` and/or ``thomson`` request mapping.  Each
        channel contains ``values``, an optional ``sigma``, and an optional
        ``unit``.  Values and ``sigma`` use
        ``[values and sigma in the same unit]``.  A Thomson request may also
        contain ``points``, which this function does not consume.  ``sigma``
        defaults to ``1.0`` and must be positive, finite, and broadcastable to
        the values shape.

    Returns
    -------
    residual_vector : ndarray of float64, shape (N_residual,)
        Field ``residual_vector`` of the returned ``scirel._result.Result``
        mapping, containing signed residuals
        ``(prediction - observation) / sigma`` in ``[dimensionless]``,
        concatenated in fixed channel order and then in NumPy C order within
        each channel.  ``N_residual`` is positive.
    chi2 : float
        Field ``chi2`` of the returned result mapping, containing the inner
        product of ``residual_vector`` in ``[dimensionless]``.  It has no
        division by degrees of freedom.

    Raises
    ------
    ValueError
        If observations are empty or contain unknown kinds or channels, a
        prediction is missing, values are empty or nonfinite, shapes differ,
        ``sigma`` is nonpositive or incompatible, an explicit unit does not
        match, or a normalized residual or ``chi2`` is not finite.
    TypeError
        If a value cannot be converted to a floating-point array.

    See Also
    --------
    scirel.diagnostics.synthesize_equilibrium_diagnostics
        Produce the prediction mapping consumed by this reducer.
    scirel.diagnostics.compute_picard_flux_residual
        Compute a relative change between two whole flux-state arrays.

    Notes
    -----
    Channels are visited in the fixed order ``flux_loops``,
    ``thomson.density``, ``thomson.electron_temperature``,
    ``thomson.p_parallel``, and ``thomson.p_perp``.  The ``residual_vector``
    and ``chi2`` fields are returned in a ``scirel._result.Result`` mapping,
    which retains dictionary access and also exposes each field as an
    attribute.  Units are matched as declared labels only; no unit conversion,
    calibration, noise covariance, or instrument response is inferred.
    ``chi2`` is an algebraic diagonal-weight sum, not by itself a statistical
    significance result.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.diagnostics import reduce_observation_residuals
    >>> r=reduce_observation_residuals(predicted={'flux_loops':[3.],'thomson':{'p_perp':[5.]},'units':{'flux_loops':'Wb','thomson':{'p_perp':'Pa'}}}, observations={'flux_loops':{'values':[1.],'sigma':[2.],'unit':'Wb'},'thomson':{'p_perp':{'values':[3.],'sigma':[1.],'unit':'Pa'}}})
    >>> assert isinstance(r, Result)
    >>> assert r.residual_vector is r['residual_vector']
    >>> np.testing.assert_allclose(r['residual_vector'],[1.,2.])
    >>> assert r['chi2']==5.
    """
    if not isinstance(predicted, Mapping):
        raise ValueError("predicted and observations must be mappings")
    residuals = []
    for kind, key, observed, sigma, unit in _observation_layout(observations):
        label = kind if key is None else f"{kind}.{key}"
        source = predicted.get(kind)
        if key is not None:
            source = source.get(key) if isinstance(source, Mapping) else None
        if source is None:
            raise ValueError(f"predicted must contain {label} for every requested usable signal")
        values = np.asarray(source, dtype=float)
        if values.shape != observed.shape:
            raise ValueError(
                f"{label} prediction and observation values must have exact same shape"
            )
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{label} prediction must be finite")
        if unit is not None:
            units = predicted.get("units", {})
            actual_unit = units.get(kind) if isinstance(units, Mapping) else None
            if key is not None:
                actual_unit = actual_unit.get(key) if isinstance(actual_unit, Mapping) else None
            if actual_unit != unit:
                raise ValueError(f"{label} prediction unit must match observation unit {unit!r}")
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            normalized = (values - observed) / sigma
        if not np.all(np.isfinite(normalized)):
            raise ValueError(f"{label} normalized residual must be finite")
        residuals.append(normalized.ravel())
    vector = np.concatenate(residuals)
    with np.errstate(over="ignore"):
        chi2 = float(vector @ vector)
    if not np.isfinite(chi2):
        raise ValueError("chi2 must be finite")
    return Result(residual_vector=vector, chi2=chi2)


run = reduce_observation_residuals
__all__ = ["reduce_observation_residuals"]
