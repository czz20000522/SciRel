"""High precision perpendicular Harris roots in nearest-pole coordinates."""

import numpy as np


def solve_perpendicular_harris(
    *,
    alpha,
    rho,
    gyro,
    temperature_ratio,
    kx,
    N,
    source_pole_order=8,
    precision=80,
    frequency_scale=1.0,
):
    """Solve the positive interlacing finite-Harris relation.

    Roots are bracketed in ``omega²`` and reported as a high precision base
    plus signed offset. Decimal carriers preserve sub-ulp information while
    the compatibility ``omega`` and ``w`` arrays remain binary64 values.
    """

    arrays = [np.asarray(value) for value in (alpha, rho, gyro, temperature_ratio)]
    if (
        not arrays[0].size
        or any(
            value.ndim != 1
            or value.shape != arrays[0].shape
            or value.dtype.kind not in "iuf"
            or not np.isfinite(value).all()
            for value in arrays
        )
    ):
        raise ValueError("finite aligned species vectors required")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        arrays = [np.asarray(value, dtype=np.float64) for value in arrays]
    if not all(np.isfinite(value).all() for value in arrays):
        raise ValueError("species values not representable in float64")
    if (
        np.any(arrays[0] <= 0)
        or np.any(arrays[1] <= 0)
        or np.any(arrays[2] == 0)
        or np.any(arrays[3] <= 0)
    ):
        raise ValueError("alpha/rho/temperature ratio positive, gyro nonzero required")

    for value, name, minimum in (
        (N, "N", 0),
        (source_pole_order, "source_pole_order", 1),
        (precision, "precision", 32),
    ):
        if isinstance(value, (bool, np.bool_)) or int(value) != value or value < minimum:
            raise ValueError(name + " integer outside declared domain")
    if (
        not np.isfinite(kx)
        or kx == 0
        or not np.isfinite(frequency_scale)
        or frequency_scale <= 0
    ):
        raise ValueError("finite nonzero kx and positive frequency_scale required")

    import mpmath as mp

    N = int(N)
    pole_order = int(source_pole_order)
    digits = int(precision)
    with mp.workdps(digits):
        constant = mp.mpf(1)
        grouped_weights = {}
        source_groups = {}
        for alpha_value, rho_value, gyro_value, ratio in zip(*arrays):
            alpha_mp, rho_mp, gyro_mp, ratio_mp = (
                mp.mpf(float(value))
                for value in (alpha_value, rho_value, gyro_value, ratio)
            )
            argument = (mp.mpf(float(kx)) * rho_mp) ** 2
            harmonics = [
                mp.exp(-argument) * mp.besseli(order, argument)
                for order in range(N + 1)
            ]
            constant += alpha_mp * (1 - harmonics[0] - 2 * sum(harmonics[1:]))
            for order in range(-N, N + 1):
                source_pole = order * gyro_mp
                source_groups[source_pole] = source_groups.get(source_pole, 0) + pole_order
            for order in range(1, N + 1):
                pole_square = (order * gyro_mp) ** 2
                grouped_weights[pole_square] = grouped_weights.get(
                    pole_square, mp.mpf(0)
                ) + 2 * alpha_mp * harmonics[order] * ratio_mp * pole_square

        if constant <= 0:
            raise ArithmeticError("positive finite-Harris closure violated")
        poles = sorted(grouped_weights)
        weights = [grouped_weights[pole] for pole in poles]
        if any(weight <= 0 for weight in weights):
            raise ArithmeticError("positive interlacing weight violated")

        target = mp.power(10, -digits // 2)
        roots = []
        for interval, pole in enumerate(poles):
            center = interval
            lower = mp.mpf(0)
            upper = (
                poles[interval + 1] - pole
                if interval + 1 < len(poles)
                else sum(weights) / constant + 1
            )

            def evaluate(reference, offset):
                terms = [
                    weight / offset
                    if index == reference
                    else weight / (poles[reference] - pole_value + offset)
                    for index, (pole_value, weight) in enumerate(zip(poles, weights))
                ]
                return constant - sum(terms), terms

            if interval + 1 < len(poles):
                midpoint = upper / 2
                value, _ = evaluate(interval, midpoint)
                if value < 0:
                    center = interval + 1
                    lower = -midpoint
                    upper = mp.mpf(0)
                else:
                    upper = midpoint

            minimum_weight = (
                min(weights[interval:interval + 2])
                if interval + 1 < len(poles)
                else weights[interval]
            )
            max_iterations = max(
                1000,
                8 * digits
                + 4 * int(abs(mp.log10(minimum_weight / constant)))
                + 128,
            )
            for _ in range(max_iterations):
                midpoint = (lower + upper) / 2
                value, _ = evaluate(center, midpoint)
                if value > 0:
                    upper = midpoint
                else:
                    lower = midpoint
                if upper - lower <= target * abs(midpoint):
                    break
            else:
                raise ArithmeticError("nearest-pole root bracket did not converge")

            offset = (lower + upper) / 2
            value, terms = evaluate(center, offset)
            residual = abs(value) / (abs(constant) + sum(abs(term) for term in terms))
            if residual > 4 * target:
                raise ArithmeticError("offset-coordinate rational residual failed")
            base = mp.sqrt(poles[center])
            frequency_offset = offset / (mp.sqrt(poles[center] + offset) + base)
            roots.append({
                "interval": interval,
                "reference": center,
                "delta": offset,
                "base": base,
                "offset": frequency_offset,
                "residual": residual,
                "bracket": (lower, upper),
            })

        modes = []
        scale = mp.mpf(float(frequency_scale))
        for sign in (-1, 1):
            for index, root in enumerate(roots):
                base = sign * root["base"]
                offset = sign * root["offset"]
                modes.append({
                    "sign": sign,
                    "index": index,
                    "root": root,
                    "base": base,
                    "offset": offset,
                    "published_base": base / scale,
                    "published_offset": offset / scale,
                    "rounded": float(base + offset),
                    "published_rounded": float(base / scale + offset / scale),
                })
        modes.sort(key=lambda mode: mode["rounded"])
        if any(
            not np.isfinite([mode["rounded"], mode["published_rounded"]]).all()
            for mode in modes
        ):
            raise FloatingPointError("frequency midpoint not representable")

        stringify = lambda values: [mp.nstr(value, digits) for value in values]
        raw_count = len(arrays[0]) * (2 * N + 1) * pole_order
        physical_count = 2 * len(poles)
        zero_residue_count = source_groups.get(mp.mpf(0), 0)
        mode_classification = {
            "source_auxiliary_modes": raw_count,
            "physical_finite_simple_modes": physical_count,
            "physical_zero_frequency_modes": 0,
            "zero_residue_source_pole_aliases": zero_residue_count,
            "repeated_nonzero_source_pole_aliases": (
                raw_count - zero_residue_count - physical_count
            ),
            "total_canceled_source_auxiliary_modes": raw_count - physical_count,
            "associated_descriptor_infinite_constraint_modes": 1,
            "associated_descriptor_constructed": False,
            "source_pole_groups": [
                {
                    "frequency_decimal": mp.nstr(pole, digits),
                    "multiplicity": count,
                    "physical_pole": pole != 0,
                }
                for pole, count in sorted(source_groups.items())
            ],
        }
        return {
            "omega": np.asarray([mode["rounded"] for mode in modes], complex),
            "w": np.asarray([mode["rounded"] for mode in modes], complex),
            "frequency_base": np.asarray([float(mode["base"]) for mode in modes]),
            "frequency_offset": np.asarray([float(mode["offset"]) for mode in modes]),
            "frequency_base_decimal": stringify([mode["base"] for mode in modes]),
            "frequency_offset_decimal": stringify([mode["offset"] for mode in modes]),
            "published_omega": np.asarray(
                [mode["published_rounded"] for mode in modes], complex
            ),
            "published_frequency_base_decimal": stringify(
                [mode["published_base"] for mode in modes]
            ),
            "published_frequency_offset_decimal": stringify(
                [mode["published_offset"] for mode in modes]
            ),
            "frequency_scale_decimal": mp.nstr(scale, digits),
            "pole_square_decimal": stringify(poles),
            "weights_decimal": stringify(weights),
            "constant_decimal": mp.nstr(constant, digits),
            "root_interval_index": [mode["root"]["interval"] for mode in modes],
            "reference_pole_index": [mode["root"]["reference"] for mode in modes],
            "root_sign": [mode["sign"] for mode in modes],
            "square_offset_decimal": stringify(
                [mode["root"]["delta"] for mode in modes]
            ),
            "shift_chart_residual_decimal": stringify(
                [mode["root"]["residual"] for mode in modes]
            ),
            "root_brackets_delta_decimal": [
                [mp.nstr(value, digits) for value in mode["root"]["bracket"]]
                for mode in modes
            ],
            "precision_digits": digits,
            "N": N,
            "source_pole_order": pole_order,
            "mode_count": physical_count,
            "classification": "PERPENDICULAR_INTERLACING_NEAREST_POLE_OFFSET_CARRIER",
            "mode_classification": mode_classification,
            "precision_limit": (
                "Canonical/published omega are binary64 rounded midpoints. "
                "Decimal nearest-base+signed-offset pairs retain sub-ulp "
                "displacement and are separately normalized before rounding; "
                "numerical brackets not rigorous intervals."
            ),
        }
