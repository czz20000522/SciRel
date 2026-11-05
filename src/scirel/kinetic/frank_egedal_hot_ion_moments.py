"""Compute Frank--Egedal hot-ion density and pressure moments using vectorized quadrature."""

import math
import numpy as np


def _mode_sum(xi0, speed, degrees, coefficients, vc, beta_m, n_terms, fractional_mode):
    u = np.power(np.clip((1.0 + vc**3) / (speed**3 + vc**3) * speed**3, 0.0, None), beta_m / 3.0)
    total = np.zeros(np.broadcast_shapes(np.shape(xi0), np.shape(speed)), dtype=float)
    for degree, coefficient in zip(degrees, coefficients):
        total += (
            coefficient
            * fractional_mode(degree, xi0, n_terms)
            * np.power(u, degree * (degree + 1.0))
        )
    return total


def evaluate_frank_egedal_hot_ion_moments(
    magnetic_field, params, degrees, source_coefficients, legendre_terms, fractional_mode
):
    """Integrate density and both pressure moments of one common population.

    Parameters
    ----------
    magnetic_field : array_like
        Local magnetic-field magnitude ``B`` on a ``[N_Z, N_R]`` grid [T].
        Every present value must be finite and strictly positive.
    params : mapping
        Scalar model, compatibility and quadrature controls with mixed units
        [B0: T; ratios and beta_m: dimensionless; nodes: count]. ``B0``
        defaults to ``median(B)``. ``mirror_ratio`` falls back to ``turning_b``
        and then ``2``. ``vc_over_v0`` defaults to ``0.25``.
        ``velocity_lower`` falls back to ``perp_velocity_lower`` and then ``0``.
        ``beta_m`` falls back to ``zeff / 2`` and then ``0.5``. Initial
        ``velocity_nodes`` and ``pitch_nodes`` default to ``24``.
        ``quadrature_rtol`` defaults to ``1e-7``. ``max_quadrature_nodes``
        defaults to ``max(768, 2 * max(initial node counts))``. Canonical
        ``mirror_ratio`` and ``beta_m`` take precedence over their legacy
        aliases; both speed-lower aliases must agree when supplied. These are
        declared model, compatibility and numerical-control defaults, not
        inferred measurements.
    degrees : array_like
        Nonempty finite fractional angular-mode degrees [dimensionless] with
        shape ``[N_mode]``; values must be nonnegative.
    source_coefficients : array_like
        Finite source-mode amplitudes [dimensionless in this normalized closure]
        with the same shape as ``degrees``; signs are allowed.
    legendre_terms : scalar
        Legacy retained-term count [count] passed unchanged to
        ``fractional_mode``.
    fractional_mode : callable
        Callable invoked as ``fractional_mode(degree, xi0, legendre_terms)``.
        It must return finite values [dimensionless output] broadcast-compatible
        with the quadrature grid.

    Returns
    -------
    normalized_field : ndarray
        Positive ``B / B0`` samples [dimensionless] with shape ``[N_Z, N_R]``.
    xi_tp_mid : float
        Reference trapped-pitch cosine [dimensionless],
        ``sqrt(1 - 1 / mirror_ratio)``.
    hot_parallel_shape : ndarray
        Parallel pressure relative to its reference value [dimensionless] with
        shape ``[N_Z, N_R]``.
    hot_perpendicular_shape : ndarray
        Perpendicular pressure relative to the reference *parallel* pressure
        [dimensionless] with shape ``[N_Z, N_R]``.
    hot_density_shape : ndarray
        Density relative to its reference value [dimensionless] with shape
        ``[N_Z, N_R]``.
    quadrature : dict
        Requested initial Gaussian node counts [count].
    velocity_domain : dict
        Common speed domain [normalized speed], including lower and upper bounds.
    quadrature_convergence : dict
        Raw-moment refinement diagnostics [counts and relative tolerance].
    reference_raw_moments : dict
        Raw reference moments [dimensionless in the stated normalized distribution].

    Raises
    ------
    ValueError
        If field, configuration, degrees, speed aliases or normalizers violate
        the declared constraints.
    FloatingPointError
        If the reference-population distribution is not finite at quadrature
        nodes.
    RuntimeError
        If raw-moment refinement does not converge within the node cap.

    See Also
    --------
    project_frank_egedal_source_modes
        Build fractional modes and source coefficients.
    assemble_frank_egedal_pressure
        Assemble physical pressure and density fields from normalized shapes.
    solve_frank_egedal_pressure_closure
        Run the source-to-pressure composition.

    Notes
    -----
    The default normalized speed interval is [0, 1], as in the common-f
    moment definitions of Frank2509.17288v4 Eq16. Its Eq19b prints a
    perpendicular-only vc lower bound, inconsistent with that unchanged
    speed-variable substitution; no author-confirmed erratum is assumed.
    ``velocity_lower`` may select a common truncated population. The legacy
    ``perp_velocity_lower`` is a compatibility alias for this same lower bound
    for all three moments, not an independent tensor-component cut.
    Normalization still uses parallel pressure and density at b=1.

    For b<1 the supplied reference population has support only where
    ``xi >= sqrt(1-b)``; other orbits cannot reach B0 and are not supplied. The
    modal sum uses its declared nonnegative part, not an unmodified exact
    kinetic solution. With vc=0 the speed factor equals one and density diverges
    logarithmically at a zero lower cutoff; positive lower cutoffs remain
    supported. Empty or zero-normalization populations are rejected. Integrable
    zero-speed powers are factored into a Gauss-Jacobi weight, including
    admissible negative beta. Raw moments are refined before normalization;
    unresolved or divergent quadrature raises RuntimeError. A refinement
    agreement is a numerical estimate, not proof for an arbitrary
    caller-provided angular callable. Only the internal source-projection
    callback marked ``_scirel_batch_safe`` uses batched field evaluation;
    unmarked callbacks retain scalar calls. This reconstruction does not
    validate a measured plasma population.

    References
    ----------
    Frank and Egedal, arXiv:2509.17288 (2025).

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments
    >>> r = evaluate_frank_egedal_hot_ion_moments(
    ...     [[1.0, 0.25]],
    ...     {'B0': 1.0, 'mirror_ratio': 4.0, 'beta_m': 0.0, 'velocity_lower': 0.2},
    ...     [0.0],
    ...     [1.0],
    ...     2,
    ...     lambda degree, xi, terms: np.ones_like(xi),
    ... )
    >>> a = np.sqrt(0.75)
    >>> lo = np.sqrt(0.75)
    >>> hi = np.sqrt(1 - 0.25 / 4)
    >>> np.testing.assert_allclose(r['hot_density_shape'], [[1.0, (hi - lo) / a]], rtol=2e-11)
    >>> np.testing.assert_allclose(r['hot_perpendicular_shape'][0, 0], 1.5, rtol=2e-11)
    >>> assert r['velocity_domain']['common_to_density_and_both_pressures']
    """
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    if magnetic_field.ndim != 2 or not np.all(np.isfinite(magnetic_field)):
        raise ValueError("B must be a finite two-dimensional [Z,R] grid")
    reference = float(params.get("B0", np.nanmedian(magnetic_field)))
    if not np.isfinite(reference) or reference <= 0.0 or np.any(magnetic_field <= 0.0):
        raise ValueError("B and B0 must be finite and strictly positive")
    normalized_field = magnetic_field / reference
    if not np.all(np.isfinite(normalized_field)) or np.any(normalized_field <= 0.0):
        raise ValueError("B/B0 must be representable as finite positive numbers")
    mirror_ratio = float(params.get("mirror_ratio", params.get("turning_b", 2.0)))
    if not np.isfinite(mirror_ratio) or mirror_ratio <= 1.0:
        raise ValueError("mirror_ratio must be finite and greater than one")
    xi_tp_mid = math.sqrt(1.0 - 1.0 / mirror_ratio)
    vc = float(params.get("vc_over_v0", 0.25))
    if not np.isfinite(vc) or vc < 0.0:
        raise ValueError("vc_over_v0 must be finite and nonnegative")
    lower = float(params.get("velocity_lower", params.get("perp_velocity_lower", 0.0)))
    if not np.isfinite(lower) or not 0.0 <= lower < 1.0:
        raise ValueError("velocity_lower must be finite and in [0,1)")
    if (
        "velocity_lower" in params
        and "perp_velocity_lower" in params
        and float(params["perp_velocity_lower"]) != lower
    ):
        raise ValueError(
            "velocity_lower and legacy perp_velocity_lower must select the same population"
        )
    if vc == 0.0 and lower == 0.0:
        raise ValueError(
            "zero critical speed and zero lower cutoff give a divergent density; normalization is undefined"
        )
    beta_m = float(params.get("beta_m", params.get("zeff", 1.0) / 2.0))
    velocity_nodes = int(params.get("velocity_nodes", 24))
    pitch_nodes = int(params.get("pitch_nodes", 24))
    if not np.isfinite(beta_m) or velocity_nodes < 2 or pitch_nodes < 2:
        raise ValueError("beta_m must be finite and quadrature nodes must be at least two")
    degrees, source_coefficients = (
        np.asarray(degrees, dtype=float),
        np.asarray(source_coefficients, dtype=float),
    )
    if (
        degrees.ndim != 1
        or degrees.size == 0
        or np.any(degrees < 0)
        or source_coefficients.shape != degrees.shape
        or (not np.all(np.isfinite(degrees)))
        or (not np.all(np.isfinite(source_coefficients)))
    ):
        raise ValueError(
            "degrees and source_coefficients must be finite one-dimensional arrays of equal length"
        )

    quadrature_rtol = float(params.get("quadrature_rtol", 1e-7))
    max_nodes = int(
        params.get("max_quadrature_nodes", max(768, 2 * max(velocity_nodes, pitch_nodes)))
    )
    if (
        not np.isfinite(quadrature_rtol)
        or quadrature_rtol <= 0
        or max_nodes < 2 * max(velocity_nodes, pitch_nodes)
    ):
        raise ValueError(
            "quadrature_rtol must be positive and max_quadrature_nodes permit a refinement"
        )
    active_powers = (
        beta_m * degrees[source_coefficients != 0] * (degrees[source_coefficients != 0] + 1)
    )
    leading_power = float(np.min(active_powers)) if active_powers.size else 0.0
    weighted_endpoint = vc > 0.0 and lower == 0.0 and leading_power > -3.0
    batch_safe_fractional_mode = bool(getattr(fractional_mode, "_scirel_batch_safe", False))
    quadrature_key = None
    quadrature_cached = None

    def get_quadrature_rules(nv, nx):
        """Return field-independent quadrature nodes and base weights once."""
        nonlocal quadrature_key, quadrature_cached
        key = (nv, nx)
        if key == quadrature_key:
            return quadrature_cached

        # Keep the public kinetic namespace dependency-light.  The import is
        # still delayed until a valid quadrature call, while the same rules
        # are reused across fields and refinement passes in this evaluation.
        from scipy.special import roots_jacobi, roots_legendre

        if weighted_endpoint:
            speed_nodes, speed_weights = roots_jacobi(nv, 0.0, 2.0 + leading_power)
        else:
            speed_nodes, speed_weights = roots_legendre(nv)
        pitch_nodes_raw, pitch_weights = roots_legendre(nx)
        quadrature_key = key
        quadrature_cached = (speed_nodes, speed_weights, pitch_nodes_raw, pitch_weights)
        return quadrature_cached

    def integrals(b, nv, nx):
        xi_tp_loc = math.sqrt(max(0.0, 1.0 - float(b) / max(mirror_ratio, 1e-12)))
        if xi_tp_loc <= 0.0 or xi_tp_mid <= 0.0:
            return (0.0, 0.0, 0.0)
        speed_nodes, base_speed_weights, pitch_nodes_raw, base_pitch_weights = get_quadrature_rules(
            nv, nx
        )
        if weighted_endpoint:
            # Factor the exact small-speed density power v^(2+leading).
            # Gauss-Jacobi resolves integrable singularities near leading=-3
            # without evaluating an overflowing f and vanishing v² separately.
            speed, speed_weights = (
                0.5 * (speed_nodes + 1.0),
                base_speed_weights / 2.0 ** (3.0 + leading_power),
            )
        else:
            speed, speed_weights = (
                0.5 * ((1.0 - lower) * speed_nodes + 1.0 + lower),
                0.5 * (1.0 - lower) * base_speed_weights,
            )
        pitch_weights = base_pitch_weights
        # A distribution specified at B0 only supplies orbits reaching B0.
        # For b<1, xi²<1-b would make the invariant xi0 imaginary.
        xi_lower = math.sqrt(max(0.0, 1.0 - b))
        xi, pitch_weights = (
            0.5 * ((xi_tp_loc - xi_lower) * pitch_nodes_raw + xi_tp_loc + xi_lower),
            0.5 * (xi_tp_loc - xi_lower) * pitch_weights,
        )
        speed_2d, xi_2d = (speed[:, None], xi[None, :])
        xi0 = np.sqrt(np.clip((xi_2d * xi_2d - (1.0 - b)) / b, 0.0, xi_tp_mid * xi_tp_mid))
        if weighted_endpoint:
            total = np.zeros((nv, nx))
            logc = np.log((1.0 + vc**3) / (speed_2d**3 + vc**3))
            for degree, coefficient in zip(degrees, source_coefficients):
                if coefficient == 0.0:
                    continue
                power = beta_m * degree * (degree + 1)
                total += (
                    coefficient
                    * fractional_mode(degree, xi0, legendre_terms)
                    * np.exp((power / 3.0) * logc + (power - leading_power) * np.log(speed_2d))
                )
            distribution = np.maximum(total / (speed_2d**3 + vc**3), 0.0)
            density_factor, pressure_factor = 1.0, speed_2d**2
        else:
            distribution = np.maximum(
                _mode_sum(
                    xi0,
                    speed_2d,
                    degrees,
                    source_coefficients,
                    vc,
                    beta_m,
                    legendre_terms,
                    fractional_mode,
                )
                / (speed_2d**3 + vc**3),
                0.0,
            )
            density_factor, pressure_factor = speed_2d**2, speed_2d**4
        if not np.all(np.isfinite(distribution)):
            raise FloatingPointError(
                "reference population distribution is not finite at quadrature nodes"
            )
        weights = speed_weights[:, None] * pitch_weights[None, :]
        parallel = 4.0 * math.pi * np.sum(weights * pressure_factor * xi_2d**2 * distribution)
        density = 4.0 * math.pi * np.sum(weights * density_factor * distribution)
        perpendicular = (
            2.0 * math.pi * np.sum(weights * pressure_factor * (1.0 - xi_2d**2) * distribution)
        )
        return tuple((float(max(value, 0.0)) for value in (parallel, perpendicular, density)))

    def integrals_block(b_values, nv, nx):
        """Evaluate a block of fields when the angular callback is array-aware.

        The callback receives one extra trailing field axis.  Reductions remain
        per field, so callers that only accept the historical 2-D ``xi`` shape
        can use the scalar fallback without changing their contract.
        """
        b_values = np.asarray(b_values, dtype=float)
        nb = b_values.size
        xi_tp_loc = np.sqrt(np.maximum(0.0, 1.0 - b_values / max(mirror_ratio, 1e-12)))
        # A block can contain fields above the mirror limit.  Let the scalar
        # path handle that mixed case so those entries keep their per-field
        # zero result without suppressing valid neighbours.
        if np.any(xi_tp_loc <= 0.0) or xi_tp_mid <= 0.0:
            return None
        speed_nodes, base_speed_weights, pitch_nodes_raw, base_pitch_weights = get_quadrature_rules(
            nv, nx
        )
        if weighted_endpoint:
            speed = 0.5 * (speed_nodes + 1.0)
            speed_weights = base_speed_weights / 2.0 ** (3.0 + leading_power)
        else:
            speed = 0.5 * ((1.0 - lower) * speed_nodes + 1.0 + lower)
            speed_weights = 0.5 * (1.0 - lower) * base_speed_weights
        pitch_weights = base_pitch_weights
        xi_lower = np.sqrt(np.maximum(0.0, 1.0 - b_values))
        xi = 0.5 * (
            (xi_tp_loc - xi_lower)[None, :] * pitch_nodes_raw[:, None]
            + xi_tp_loc[None, :]
            + xi_lower[None, :]
        )
        pitch_weights = 0.5 * (xi_tp_loc - xi_lower) * pitch_weights[:, None]
        xi0 = np.sqrt(
            np.clip(
                (xi[None, :, :] ** 2 - (1.0 - b_values)[None, None, :]) / b_values[None, None, :],
                0.0,
                xi_tp_mid * xi_tp_mid,
            )
        )
        speed_3d = speed[:, None, None]
        xi_3d = xi[None, :, :]
        mode_values = []
        try:
            for degree, coefficient in zip(degrees, source_coefficients):
                if coefficient == 0.0:
                    mode_values.append(None)
                    continue
                values = np.asarray(fractional_mode(degree, xi0, legendre_terms))
                if values.ndim == 0:
                    values = np.full(xi0.shape, values, dtype=float)
                if values.shape != xi0.shape:
                    return None
                mode_values.append(values)
        except (TypeError, ValueError, IndexError) as error:
            # A callback may keep the historical 2-D contract.  Only errors
            # that identify an array-shape/ndim incompatibility may select the
            # scalar fallback; scientific/runtime failures must propagate.
            message = str(error).lower()
            shape_markers = (
                "ndim",
                "dimension",
                "shape",
                "broadcast",
                "scalar-only",
                "too many indices",
                "not enough indices",
            )
            if any(marker in message for marker in shape_markers):
                return None
            raise

        logc = np.log((1.0 + vc**3) / (speed_3d**3 + vc**3))
        if weighted_endpoint:
            total = np.zeros((nv, nx, nb), dtype=float)
            log_speed = np.log(speed_3d)
            for (degree, coefficient), values in zip(
                zip(degrees, source_coefficients), mode_values
            ):
                if coefficient == 0.0:
                    continue
                power = beta_m * degree * (degree + 1.0)
                total += (
                    coefficient
                    * values
                    * np.exp((power / 3.0) * logc + (power - leading_power) * log_speed)
                )
            distribution = np.maximum(total / (speed_3d**3 + vc**3), 0.0)
            density_factor, pressure_factor = 1.0, speed_3d**2
        else:
            total = np.zeros((nv, nx, nb), dtype=float)
            u = np.power(
                np.clip(
                    (1.0 + vc**3) / (speed_3d**3 + vc**3) * speed_3d**3,
                    0.0,
                    None,
                ),
                beta_m / 3.0,
            )
            for (degree, coefficient), values in zip(
                zip(degrees, source_coefficients), mode_values
            ):
                if coefficient == 0.0:
                    continue
                total += coefficient * values * np.power(u, degree * (degree + 1.0))
            distribution = np.maximum(total / (speed_3d**3 + vc**3), 0.0)
            density_factor, pressure_factor = speed_3d**2, speed_3d**4
        if not np.all(np.isfinite(distribution)):
            raise FloatingPointError(
                "reference population distribution is not finite at quadrature nodes"
            )

        outputs = np.empty((nb, 3), dtype=float)
        for index in range(nb):
            weights = speed_weights[:, None] * pitch_weights[:, index][None, :]
            if np.ndim(pressure_factor) == 3:
                pressure_i = pressure_factor[:, :, 0]
            else:
                pressure_i = pressure_factor
            if np.ndim(density_factor) == 3:
                density_i = density_factor[:, :, 0]
            else:
                density_i = density_factor
            parallel = (
                4.0
                * math.pi
                * np.sum(weights * pressure_i * xi_3d[:, :, index] ** 2 * distribution[:, :, index])
            )
            density = 4.0 * math.pi * np.sum(weights * density_i * distribution[:, :, index])
            perpendicular = (
                2.0
                * math.pi
                * np.sum(
                    weights
                    * pressure_i
                    * (1.0 - xi_3d[:, :, index] ** 2)
                    * distribution[:, :, index]
                )
            )
            outputs[index] = np.maximum((parallel, perpendicular, density), 0.0)
        return outputs

    def integrals_many(field_values, nv, nx):
        field_values = np.asarray(field_values, dtype=float)
        if field_values.size < 2 or not batch_safe_fractional_mode:
            return np.asarray([integrals(float(b), nv, nx) for b in field_values])
        block_size = 32
        blocks = []
        for begin in range(0, field_values.size, block_size):
            block = integrals_block(field_values[begin : begin + block_size], nv, nx)
            if block is None:
                return np.asarray([integrals(float(b), nv, nx) for b in field_values])
            blocks.append(block)
        return np.concatenate(blocks, axis=0)

    fields = np.unique(np.r_[normalized_field.ravel(), 1.0])
    nv, nx = velocity_nodes, pitch_nodes
    previous = integrals_many(fields, nv, nx)
    # Compare RAW moments, not normalized ratios: a divergent reference
    # moment can otherwise cancel algebraically and appear converged.
    for refinement in range(32):
        nv, nx = min(2 * nv, max_nodes), min(2 * nx, max_nodes)
        current = integrals_many(fields, nv, nx)
        reference = current[np.searchsorted(fields, 1.0)]
        scales = np.maximum(
            np.maximum(np.abs(current), np.abs(previous)), np.abs(reference) * 1e-12
        )
        differences = np.abs(current - previous)
        if np.all(np.isfinite(current)) and np.all(differences <= quadrature_rtol * scales):
            break
        if nv == max_nodes and nx == max_nodes:
            raise RuntimeError(
                "hot-ion raw-moment quadrature did not converge; population may be nonintegrable or unresolved"
            )
        previous = current
    else:
        raise RuntimeError("hot-ion raw-moment quadrature refinement limit reached")
    midplane = current[np.searchsorted(fields, 1.0)]
    if not np.all(np.isfinite(midplane)) or midplane[0] <= 0.0 or midplane[2] <= 0.0:
        raise ValueError(
            "reference population must have finite positive parallel pressure and density"
        )
    values = current[np.searchsorted(fields, normalized_field.ravel())]
    parallel, perpendicular, density = (
        values[:, index].reshape(normalized_field.shape) for index in range(3)
    )
    return {
        "normalized_field": normalized_field,
        "xi_tp_mid": xi_tp_mid,
        "hot_parallel_shape": parallel / midplane[0],
        "hot_perpendicular_shape": perpendicular / midplane[0],
        "hot_density_shape": density / midplane[2],
        "quadrature": {"velocity_nodes": velocity_nodes, "pitch_nodes": pitch_nodes},
        "reference_raw_moments": {
            "parallel": float(midplane[0]),
            "perpendicular": float(midplane[1]),
            "density": float(midplane[2]),
        },
        "quadrature_convergence": {
            "velocity_nodes": nv,
            "pitch_nodes": nx,
            "relative_tolerance": quadrature_rtol,
            "raw_moments_checked": True,
            "velocity_rule": "jacobi_factored_density_power" if weighted_endpoint else "legendre",
            "factored_density_power": 2.0 + leading_power if weighted_endpoint else None,
        },
        "velocity_domain": {
            "lower": lower,
            "upper": 1.0,
            "common_to_density_and_both_pressures": True,
        },
    }


__all__ = ["evaluate_frank_egedal_hot_ion_moments"]
