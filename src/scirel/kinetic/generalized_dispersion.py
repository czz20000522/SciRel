"""Generalized one-dimensional dispersion relations. Analytic kernels handle Gaussian, top-hat, and finite-support cases while quadrature remains a validated fallback."""

from __future__ import annotations

import ast
import warnings

import numpy as np

# These names remain module globals because the warning and solver contracts
# deliberately permit tests and callers to replace the numerical backends.
quad = None
IntegrationWarning = None
root = None


def _load_quadrature_backend():
    global quad, IntegrationWarning
    if quad is None:
        from scipy.integrate import quad as scipy_quad

        quad = scipy_quad
    if IntegrationWarning is None:
        from scipy.integrate import IntegrationWarning as scipy_warning

        IntegrationWarning = scipy_warning
    return quad, IntegrationWarning


def _load_root_backend():
    global root
    if root is None:
        from scipy.optimize import root as scipy_root

        root = scipy_root
    return root


def _evaluate_cauchy_transform(*args, **kwargs):
    from .cauchy_transform import evaluate_cauchy_transform

    return evaluate_cauchy_transform(*args, **kwargs)


def _evaluate_plasma_dispersion(*args, **kwargs):
    from .plasma_dispersion import evaluate_plasma_dispersion

    return evaluate_plasma_dispersion(*args, **kwargs)


def _evaluate_maxwellian_electrostatic(*args, **kwargs):
    from .maxwellian_electrostatic import evaluate_maxwellian_electrostatic

    return evaluate_maxwellian_electrostatic(*args, **kwargs)


def _maxwellian_susceptibility(*args, **kwargs):
    from .maxwellian_electrostatic import _susceptibility

    return _susceptibility(*args, **kwargs)


class DensityExpression:
    """Evaluate a restricted real density expression and its first derivative.

    Supported names are ``v``, ``pi`` and the elementary functions
    ``exp``, ``log``, ``sqrt``, ``sin``, ``cos``, ``sinh``, ``cosh`` and
    ``tanh``.  the reference environment elementwise operators are normalized before parsing;
    arbitrary attributes, indexing, names and calls are rejected.
    """

    _functions = {
        "exp": (np.exp, np.exp),
        "log": (np.log, lambda value: 1.0 / value),
        "sqrt": (np.sqrt, lambda value: 0.5 / np.sqrt(value)),
        "sin": (np.sin, np.cos),
        "cos": (np.cos, lambda value: -np.sin(value)),
        "sinh": (np.sinh, np.cosh),
        "cosh": (np.cosh, np.sinh),
        "tanh": (np.tanh, lambda value: 1.0 / np.cosh(value) ** 2),
    }
    _allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.USub,
        ast.UAdd,
    )

    def __init__(self, expression):
        if not isinstance(expression, str) or len(expression) > 4096:
            raise ValueError("expression must be a string of at most 4096 characters")
        normalized = expression.replace(".^", "**").replace("^", "**")
        normalized = normalized.replace(".*", "*").replace("./", "/")
        try:
            tree = ast.parse(normalized, mode="eval").body
        except (SyntaxError, RecursionError) as error:
            raise ValueError("invalid density expression") from error
        if len(list(ast.walk(tree))) > 256:
            raise ValueError("density expression is too complex")
        for node in ast.walk(tree):
            if not isinstance(node, self._allowed_nodes):
                raise ValueError("unsupported density expression syntax")
            if isinstance(node, ast.Constant) and (
                type(node.value) not in (int, float) or not np.isfinite(node.value)
            ):
                raise ValueError("only finite real constants are allowed")
            if isinstance(node, ast.Name) and node.id not in {"v", "pi", *self._functions}:
                raise ValueError("unknown density expression name")
            if isinstance(node, ast.Call) and (
                not isinstance(node.func, ast.Name)
                or node.func.id not in self._functions
                or len(node.args) != 1
                or node.keywords
            ):
                raise ValueError("unsupported density expression call")
        self.tree = tree

    @staticmethod
    def _velocity(value):
        raw = np.asarray(value)
        if raw.dtype.kind not in "iufc" or raw.size == 0 or not np.isfinite(raw).all():
            raise ValueError("velocity must contain finite numeric values")
        return np.asarray(raw, dtype=complex if raw.dtype.kind == "c" else float)

    def _dual(self, node, velocity):
        if isinstance(node, ast.Constant):
            return node.value, 0.0
        if isinstance(node, ast.Name):
            if node.id == "v":
                return velocity, 1.0
            if node.id == "pi":
                return np.pi, 0.0
            raise ValueError("function name must be called")
        if isinstance(node, ast.UnaryOp):
            value, derivative = self._dual(node.operand, velocity)
            return (-value, -derivative) if isinstance(node.op, ast.USub) else (value, derivative)
        if isinstance(node, ast.Call):
            value, derivative = self._dual(node.args[0], velocity)
            function, derivative_function = self._functions[node.func.id]
            return function(value), derivative_function(value) * derivative

        left, left_prime = self._dual(node.left, velocity)
        right, right_prime = self._dual(node.right, velocity)
        if isinstance(node.op, ast.Add):
            return left + right, left_prime + right_prime
        if isinstance(node.op, ast.Sub):
            return left - right, left_prime - right_prime
        if isinstance(node.op, ast.Mult):
            return left * right, left_prime * right + left * right_prime
        if isinstance(node.op, ast.Div):
            return left / right, (left_prime * right - left * right_prime) / right**2
        if np.all(np.asarray(right_prime) == 0):
            if right == 0:
                return np.ones_like(left), np.zeros_like(left)
            return left**right, right * left ** (right - 1) * left_prime
        value = left**right
        derivative = value * (right_prime * np.log(left) + right * left_prime / left)
        return value, derivative

    def __call__(self, velocity):
        return self._dual(self.tree, self._velocity(velocity))[0]

    def derivative(self, velocity):
        return self._dual(self.tree, self._velocity(velocity))[1]


def _points(value):
    raw = np.asarray(value)
    if raw.size == 0 or raw.dtype.kind not in "iufc" or not np.isfinite(raw).all():
        raise ValueError("z must be finite nonempty numeric values")
    return np.asarray(raw, dtype=complex)


def _transform(points, density, derivative, mesh, bounds=None, analytic=None, epsabs=1e-10):
    """Evaluate the Cauchy transform with explicit real-axis PV handling."""
    values = _points(points)
    result = np.empty(values.shape, dtype=complex)
    quadrature, warning_type = _load_quadrature_backend()

    for index in np.ndindex(values.shape):
        point = complex(values[index])
        if point.imag:
            result[index] = _evaluate_cauchy_transform(
                point,
                density,
                bounds=bounds,
                integration_mesh=mesh,
                analytic_density=analytic,
                epsabs=epsabs,
            )["G"]
            continue

        real_point = point.real
        if bounds is not None and not bounds[0] < real_point < bounds[1]:
            if real_point in bounds:
                raise ValueError("real-axis endpoint singularity")
            edges = sorted(set([*bounds[:1], *mesh, *bounds[1:]]))
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", warning_type)
                    integral = sum(
                        quadrature(
                            lambda velocity: density(velocity) / (velocity - real_point),
                            left,
                            right,
                            epsabs=epsabs,
                            epsrel=1e-10,
                        )[0]
                        for left, right in zip(edges[:-1], edges[1:])
                    )
            except warning_type as error:
                raise RuntimeError("generalized real-axis quadrature did not converge") from error
            result[index] = integral
            continue

        density_at_point = float(density(real_point))

        def regularized(velocity):
            offset = velocity - real_point
            if abs(offset) < 1e-7:
                return float(derivative(real_point))
            return (density(velocity) - density_at_point * np.exp(-offset * offset)) / offset

        edges = sorted(set([-np.inf, *mesh, real_point, np.inf]))
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", warning_type)
                integral = sum(
                    quadrature(
                        regularized,
                        left,
                        right,
                        epsabs=epsabs / len(edges),
                        epsrel=1e-10,
                    )[0]
                    for left, right in zip(edges[:-1], edges[1:])
                )
        except warning_type as error:
            raise RuntimeError("generalized principal-value quadrature did not converge") from error
        result[index] = integral + 1j * np.pi * density_at_point

    if not np.isfinite(result).all():
        raise ValueError("generalized transform is not representable")
    return result


def evaluate_generalized_hilbert(z, expression, *, integration_mesh, continuation=True):
    """Return ``Z`` and ``Zp`` for an analytic density expression."""
    density = DensityExpression(expression)
    mesh = np.asarray(integration_mesh, dtype=float)
    if mesh.ndim != 1 or mesh.size < 2 or not np.isfinite(mesh).all() or np.any(np.diff(mesh) <= 0):
        raise ValueError("integration_mesh must be finite increasing points")

    points = _points(z)
    derivative = density.derivative
    second = lambda value: (derivative(value + 1e-5) - derivative(value - 1e-5)) / 2e-5
    result = {
        "Z": _transform(
            points, density, derivative, mesh, analytic=density if continuation else None
        )
    }
    derivative_transform = np.empty(points.shape, dtype=complex)
    weighted = lambda value: value * derivative(value)
    weighted_prime = lambda value: derivative(value) + value * second(value)
    for index in np.ndindex(points.shape):
        point = complex(points[index])
        if np.abs(np.clongdouble(point)) >= 12:
            tolerance = float(np.longdouble(1e-10) / np.abs(np.clongdouble(point)))
            derivative_transform[index] = (
                _transform(
                    point,
                    weighted,
                    weighted_prime,
                    mesh,
                    analytic=weighted if continuation else None,
                    epsabs=tolerance,
                )
                / point
            )
        else:
            derivative_transform[index] = _transform(
                point,
                derivative,
                second,
                mesh,
                analytic=derivative if continuation else None,
            )
    if not np.isfinite(derivative_transform).all():
        raise ValueError("analytic density derivative transform is not representable")
    result["Zp"] = derivative_transform
    return result


def _gaussian_derivative(points, transform):
    """Evaluate the Gaussian derivative transform without cancellation."""
    values = np.empty(points.shape, dtype=complex)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        for index in np.ndindex(points.shape):
            point = complex(points[index])
            wide = np.clongdouble(point)
            magnitude = np.abs(wide)
            if magnitude < 12:
                value = -2.0 * (1.0 + point * complex(transform[index]))
            elif magnitude <= 1e150:
                value = -_maxwellian_susceptibility(point, 1 / np.sqrt(2.0), point)[0]
            else:
                inverse = 1 / wide
                value = inverse * inverse
                if point.imag <= 0:
                    factor = 4 if point.imag < 0 else 2
                    logarithm = (
                        -wide * wide
                        + np.log(np.longdouble(factor) * np.sqrt(np.longdouble(np.pi)))
                        + np.log(wide)
                    )
                    value -= 1j * np.exp(logarithm)
                value = complex(value)
            if point.real == 0:
                value = complex(value.real, 0.0)
            values[index] = value
    if not np.isfinite(values).all():
        raise ValueError("Gaussian derivative is not representable")
    return values


def _top_hat_transform(points):
    """Evaluate the unit top-hat transform with stable near/far formulas."""
    wide = points.astype(np.clongdouble)
    far = np.abs(wide) >= 1
    transform = np.empty(points.shape, dtype=complex)
    if np.any(far):
        inverse = 1 / wide[far]
        ratio = (inverse / 2) ** 2
        power = np.ones(inverse.shape, dtype=np.clongdouble)
        total = power.copy()
        for order in range(1, 129):
            power *= ratio
            term = power / (2 * order + 1)
            total += term
            if np.all(np.abs(term) <= np.finfo(float).eps * np.abs(total) / 4):
                break
        transform[far] = np.asarray(-inverse * total, dtype=complex)
    if np.any(~far):
        near = wide[~far]
        x, y = near.real, near.imag
        center = np.abs(x) <= 0.25
        real_part = np.empty(x.shape, dtype=np.longdouble)
        denominator = (x[center] + 0.5) ** 2 + y[center] ** 2
        real_part[center] = np.log1p(-2 * x[center] / denominator) / 2
        real_part[~center] = np.log(np.hypot(x[~center] - 0.5, y[~center])) - np.log(
            np.hypot(x[~center] + 0.5, y[~center])
        )
        imaginary_part = np.arctan2(y, (x - 0.5) * (x + 0.5) + y * y)
        imaginary_part = np.where(y == 0, np.pi * (np.abs(x) < 0.5), imaginary_part)
        transform[~far] = np.asarray(real_part + 1j * imaginary_part, dtype=complex)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        x, y = wide.real, wide.imag
        denominator = (x - 0.5) * (x + 0.5) - y * y + 1j * (2 * x * y)
        derivative = np.asarray(1 / denominator, dtype=complex)
    if not np.isfinite(transform).all() or not np.isfinite(derivative).all():
        raise ValueError("top-hat transform is not representable")
    return {"Z": transform, "Zp": derivative}


def evaluate_generalized_dispersion(
    z, selector=0, *, expression="exp(-v.^2)/sqrt(pi)", integration_mesh=None
):
    """Evaluate the normalized transform for selectors 0 through 6."""
    points = _points(z)
    if (
        isinstance(selector, (bool, np.bool_))
        or not isinstance(selector, (int, np.integer))
        or selector not in range(7)
    ):
        raise ValueError("selector must be an integer from 0 through 6")
    if selector == 0:
        if expression in ("exp(-v.^2)/sqrt(pi)", "exp(-v**2)/sqrt(pi)"):
            transform = np.asarray(_evaluate_plasma_dispersion(points)["Z"])
            return {"Z": transform, "Zp": _gaussian_derivative(points, transform)}
        if integration_mesh is None:
            raise ValueError("custom expression requires integration_mesh")
        return evaluate_generalized_hilbert(points, expression, integration_mesh=integration_mesh)
    if selector == 1:
        if np.any(points == 0):
            raise ValueError("delta transform pole at zero")
        return {"Z": -1 / points, "Zp": 1 / points**2}
    if selector == 4:
        return evaluate_generalized_hilbert(
            points,
            "sqrt(2)/pi/(1+v**2/2)**2",
            integration_mesh=[-16, -4, -1, 0, 1, 4, 16],
        )
    if selector == 2:
        if np.any((points.imag == 0) & (np.abs(points.real) == 0.5)):
            raise ValueError("top-hat endpoint singularity")
        return _top_hat_transform(points)

    if selector == 3:
        density = lambda value: max(0.0, 1 - abs(value))
        derivative = lambda value: 1.0 if -1 < value < 0 else (-1.0 if 0 < value < 1 else 0.0)
        mesh, bounds, jumps = [-1.0, 0.0, 1.0], (-1.0, 1.0), []
    elif selector == 5:
        density = lambda value: np.exp(-value * value) / np.sqrt(np.pi) if value > 0.1 else 0.0
        derivative = lambda value: -2 * value * density(value)
        mesh, bounds, jumps = (
            [0.1, 0.5, 1.0, 2.0, 4.0, 8.0],
            None,
            [(0.1, np.exp(-0.01) / np.sqrt(np.pi))],
        )
    else:
        coefficient = 3 * np.sqrt(3) / (4 * np.pi)
        density = lambda value: coefficient / (abs(value) ** 3 + 1) if abs(value) < 4 else 0.0
        derivative = lambda value: (
            -3 * coefficient * value * abs(value) / (abs(value) ** 3 + 1) ** 2
            if abs(value) < 4
            else 0.0
        )
        mesh, bounds, jumps = (
            [-4.0, -2.0, -1.0, 0.0, 1.0, 2.0, 4.0],
            (-4.0, 4.0),
            [(-4.0, coefficient / 65), (4.0, -coefficient / 65)],
        )

    singular = (
        ([0.0] if selector == 3 else []) + [location for location, _ in jumps] + list(bounds or [])
    )
    if any(np.any((points.imag == 0) & (points.real == location)) for location in singular):
        raise ValueError("real-axis distribution corner or endpoint singularity")
    second = lambda value: (derivative(value + 1e-5) - derivative(value - 1e-5)) / 2e-5
    result = {
        "Z": _transform(points, density, derivative, mesh, bounds),
        "Zp": _transform(points, derivative, second, mesh, bounds),
    }
    for location, jump in jumps:
        result["Zp"] += jump / (location - points)
    return result


def evaluate_gpdf_residual(
    kind,
    x,
    k,
    *,
    ion_temperature=1.0,
    ion_mass=1836.0,
    beam_fraction=0.1,
    beam_temperature=1.0,
    beam_drift=5.0,
    selector=0,
    expression="exp(-v.^2)/sqrt(pi)",
    integration_mesh=None,
):
    """Evaluate the dimensionless dielectric residual for a selected mixture."""
    phase = _points(x)
    if not np.isscalar(k) or not np.isreal(k) or not np.isfinite(k) or k <= 0:
        raise ValueError("k must be finite positive scalar")
    response = lambda value: 1 + value * _evaluate_plasma_dispersion(value)["Z"]
    if kind == "langmuir":
        return _evaluate_maxwellian_electrostatic(phase * np.sqrt(2) * k, k)["D"]
    if kind == "generalized":
        if selector == 0 and expression == "exp(-v.^2)/sqrt(pi)":
            return _evaluate_maxwellian_electrostatic(phase * np.sqrt(2) * k, k)["D"]
        return (
            k * k
            - evaluate_generalized_dispersion(
                phase, selector, expression=expression, integration_mesh=integration_mesh
            )["Zp"]
            / 2
        )
    if kind == "iaw":
        if (
            not np.isfinite([ion_temperature, ion_mass]).all()
            or min(ion_temperature, ion_mass) <= 0
        ):
            raise ValueError("ion temperature and mass must be positive")
        return (
            k * k
            + response(phase)
            + response(phase / np.sqrt(ion_temperature / ion_mass)) / ion_temperature
        )
    if kind == "beam":
        if (
            not np.isfinite([beam_fraction, beam_temperature, beam_drift]).all()
            or not 0 <= beam_fraction <= 1
            or beam_temperature <= 0
        ):
            raise ValueError("invalid beam parameters")
        return (
            k * k
            + (1 - beam_fraction) * response(phase)
            + beam_fraction
            / beam_temperature
            * response(phase / np.sqrt(beam_temperature) - beam_drift)
        )
    raise ValueError("unknown residual kind")


def evaluate_gpdf_small_k(k):
    """Return the small-k real frequency and Landau damping asymptotic."""
    raw = np.asarray(k)
    if (
        raw.dtype.kind not in "iuf"
        or raw.size == 0
        or not np.isfinite(raw).all()
        or np.any(raw <= 0)
    ):
        raise ValueError("k must be finite positive real values")
    values = np.asarray(raw, dtype=float)
    with np.errstate(over="ignore", under="ignore", divide="ignore"):
        damping = -np.exp(0.5 * np.log(np.pi / 8) - 0.5 / values**2 - 1.5 - 3 * np.log(values))
    with np.errstate(over="ignore"):
        real = 1 + 1.5 * values * values
    if not np.isfinite(real).all() or not np.isfinite(damping).all():
        raise ValueError("small-k asymptotic is not representable")
    return {"omega_real": real, "omega_imag": damping}


def scan_gpdf_roots(
    kind,
    *,
    k_values=None,
    initial_guess=None,
    residual_tolerance=1e-9,
    max_evaluations=300,
    **parameters,
):
    """Follow a seeded complex root branch over the original scan grids."""
    grids = {
        "langmuir": np.r_[np.arange(1, 11) / 10, np.arange(2, 11)],
        "iaw": np.arange(22, 0, -1) / 20,
        "beam": np.arange(80, 9, -1) / 200,
        "generalized": np.r_[np.arange(1, 11) / 10, np.arange(3, 11) / 2],
    }
    seeds = {
        "langmuir": 1 - 0.1j,
        "iaw": 0.04 - 0.02j,
        "beam": (1 - 0.01j) * np.sqrt(2) * 0.4,
        "generalized": 1.5 - 0.001j,
    }
    if kind not in grids:
        raise ValueError("unknown scan kind")
    values = np.asarray(grids[kind] if k_values is None else k_values)
    if (
        values.ndim != 1
        or values.size == 0
        or values.dtype.kind not in "iuf"
        or not np.isfinite(values).all()
        or np.any(values <= 0)
    ):
        raise ValueError("k_values must be finite positive vector")
    if not np.isfinite(residual_tolerance) or residual_tolerance <= 0:
        raise ValueError("residual_tolerance must be positive")
    if (
        isinstance(max_evaluations, bool)
        or not isinstance(max_evaluations, (int, np.integer))
        or max_evaluations < 1
    ):
        raise ValueError("max_evaluations must be positive integer")
    guess = complex(seeds[kind] if initial_guess is None else initial_guess)
    if not np.isfinite(guess):
        raise ValueError("initial_guess must be finite")

    frequencies, residuals, evaluations = [], [], []
    for wave_number in values:
        seed = guess / (np.sqrt(2) * wave_number) if kind == "generalized" else guess

        def residual(parts):
            phase = complex(*parts)
            default_expression = parameters.get("expression", "exp(-v.^2)/sqrt(pi)")
            if (
                kind in ("langmuir", "generalized")
                and parameters.get("selector", 0) == 0
                and default_expression == "exp(-v.^2)/sqrt(pi)"
            ):
                value = complex(
                    _evaluate_maxwellian_electrostatic(
                        phase * np.sqrt(2) * wave_number, wave_number
                    )["epsilon"]
                )
            else:
                value = complex(
                    evaluate_gpdf_residual(kind, phase, wave_number, **parameters) / wave_number**2
                )
            return [value.real, value.imag]

        solved = _load_root_backend()(
            residual,
            [seed.real, seed.imag],
            method="hybr",
            options={"xtol": 1e-10, "maxfev": int(max_evaluations)},
        )
        phase = complex(*solved.x)
        norm = np.linalg.norm(residual(solved.x))
        if not solved.success or norm > residual_tolerance or solved.nfev > max_evaluations:
            raise RuntimeError(
                f"{kind} scan failed at k={wave_number}: residual={norm}; {solved.message}"
            )
        omega = phase * np.sqrt(2) * wave_number
        frequencies.append(omega)
        residuals.append(norm)
        evaluations.append(solved.nfev)
        if kind in ("iaw", "beam"):
            guess = phase
        elif kind == "generalized":
            guess = omega
    return {
        "k": values,
        "omega": np.asarray(frequencies),
        "dielectric_residual": np.asarray(residuals),
        "evaluations": np.asarray(evaluations),
    }


__all__ = [
    "DensityExpression",
    "evaluate_generalized_hilbert",
    "evaluate_generalized_dispersion",
    "evaluate_gpdf_residual",
    "evaluate_gpdf_small_k",
    "scan_gpdf_roots",
]
