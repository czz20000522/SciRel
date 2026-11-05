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
    r"""Compile a restricted density expression into value and analytic first-derivative callables.

    Parameters
    ----------
    expression : str
        Analytic density in v using finite real constants, pi, arithmetic and
        exp/log/sqrt/sin/cos/sinh/cosh/tanh; MATLAB point operators accepted. [dimensionless] Shape: scalar.
        Real integrable density with decaying derivative; no arbitrary code, comparisons, attributes or
        indexing.

    Raises
    ------
    ValueError
        ValueError for unsupported AST nodes, non-finite constants, malformed expressions, or non-numeric
        velocity values.

    See Also
    --------
    scirel.kinetic : Public kinetic-domain operators.

    Notes
    -----
    Parse finite real constants, pi, v, arithmetic and the declared elementary functions; propagate
    pairs (value, derivative) by exact analytic chain rules. MATLAB elementwise operators are normalized
    before parsing. One-dimensional unmagnetized collisionless electrostatic plasma Assumptions: Density
    is real and integrable on the real contour. No collective-mode uniqueness or certified global
    quadrature bound is asserted. Expression has a valid analytic extension where continuation is
    requested. Explicit increasing mesh resolves all density features and tails.

    References
    ----------
    Hua-Sheng Xie, Generalized plasma dispersion function, Phys. Plasmas. 20 (2013), 092125 (scientific context)

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic.generalized_dispersion import DensityExpression
    >>> f=DensityExpression('1./(1+v.^2)/pi')
    >>> v=.7
    >>> assert abs(f(v)-1/(1+v*v)/np.pi)<1e-14
    >>> assert abs(f.derivative(v)+2*v/(1+v*v)**2/np.pi)<1e-14
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
    r"""Evaluate a safe analytic expression and its derivative transforms.

    Parameters
    ----------
    z : real or complex numeric
        Complex phase point z=omega/(sqrt(2)*k) for the Maxwellian normalization. [dimensionless] Shape:
        scalar or nonempty array. Finite and representable.
    expression : str
        Analytic density in v using finite real constants, pi, arithmetic and
        exp/log/sqrt/sin/cos/sinh/cosh/tanh; MATLAB point operators accepted. [dimensionless] Shape: scalar.
        Real integrable density with decaying derivative; no arbitrary code, comparisons, attributes or
        indexing.
    integration_mesh : real vector
        Feature-resolving finite increasing velocity mesh; infinite tails are also integrated.
        [dimensionless] Shape: one-dimensional at least two points. All material features resolved; no
        unresolved tail features.
    continuation : bool
        Add 2*pi*i*f(z) and derivative in the lower plane when true. [dimensionless] Shape: scalar. Default:
        True. Finite and representable.

    Returns
    -------
    Z : complex array
        Integral f(v)/(v-z) dv with the declared continuation. [dimensionless] Shape: same as z. Finite and
        representable.
    Zp : complex array
        Derivative dZ/dz including distributional jumps. [dimensionless] Shape: same as z. Finite and
        representable.

    Raises
    ------
    FloatingPointError
        FloatingPointError for a non-finite continued transform and RuntimeError when quadrature fails; no
        fallback path is selected.
    RuntimeError
        FloatingPointError for a non-finite continued transform and RuntimeError when quadrature fails; no
        fallback path is selected. RuntimeError when real-axis/exterior quadrature fails or the declared
        removable-point estimate is not representable.
    ValueError
        ValueError for an unsupported expression, non-finite phase/mesh, or malformed
        integration_mesh/continuation.

    See Also
    --------
    scirel.kinetic : Public kinetic-domain operators.

    Notes
    -----
    DensityExpression interprets the restricted AST and propagates analytic first derivatives by chain
    rules without eval or SymPy. Real-axis integrands subtract f(x)*exp(-(v-x)²), whose whole-line odd
    PV vanishes. Boundary values add i*pi*f(x); optional lower continuation adds 2*pi*i*f(z). For
    |z|>=12 the vanishing-endpoint identity Zp=Cauchy[v*fprime]/z avoids cancellation of the zero-mass
    derivative; the absolute quadrature tolerance scales inversely with phase magnitude. The density
    derivative and its analytic continuation are not reconstructed from rounded Z or epsilon. One-
    dimensional unmagnetized collisionless electrostatic plasma Assumptions: Density is real and
    integrable on the real contour. No collective-mode uniqueness or certified global quadrature bound
    is asserted. Expression has a valid analytic extension where continuation is requested. Explicit
    increasing mesh resolves all density features and tails.

    References
    ----------
    Hua-Sheng Xie, Generalized plasma dispersion function, Phys. Plasmas. 20 (2013), 092125 (scientific context)

    Examples
    --------
    >>> from scirel.kinetic.generalized_dispersion import evaluate_generalized_hilbert
    >>> z=.4-.7j
    >>> r=evaluate_generalized_hilbert(z,'1/(1+v**2)/pi',integration_mesh=[-20,-2,-1,0,1,2,20])
    >>> assert abs(r['Z']+1/(z+1j))<2e-9
    """
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
    """Return ``Z(z) = integral f(v)/(v - z) dv`` and ``Zp = dZ/dz`` for a selected density.

    ``z`` is in the velocity variable of the density. Selector 0 uses
    ``expression`` (default ``exp(-v**2)/sqrt(pi)``, the Maxwellian with ``v``
    in units of ``sqrt(2) v_t``, so ``z = omega/(sqrt(2) k v_t)``). Selectors:
    1 ``delta(v)``; 2 top-hat on ``[-0.5, 0.5]``; 3 triangle ``max(0, 1-|v|)``;
    4 ``sqrt(2)/pi/(1+v**2/2)**2``; 5 ``H(v-0.1) exp(-v**2)/sqrt(pi)``
    (mass-incomplete); 6 ``3 sqrt(3)/(4 pi)/(1+|v|**3)`` truncated at ``|v| <= 4``.
    Expressions accept ``**`` or ``^`` for powers and MATLAB ``.^ .* ./``.

    Parameters
    ----------
    z : real or complex numeric, shape scalar or nonempty array
        Complex phase point z in the same velocity variable v as the selected
        density [dimensionless]: Z(z)=integral f(v)/(v-z) dv. For the default Maxwellian
        exp(-v^2)/sqrt(pi), v is in units of sqrt(2) v_t, so z=omega/(sqrt(2) k
        v_t); for a custom expression z is omega/k in the units of v used in
        that expression. Finite and representable.
    selector : integer, default 0
        Density family in the velocity variable v, of unit integral except
        selectors 5 (mass-incomplete) and 6 (truncated): 0 the expression
        argument (default exp(-v^2)/sqrt(pi), the Maxwellian with v in units of
        sqrt(2) v_t); 1 delta(v); 2 top-hat 1 on [-0.5,0.5]; 3 triangle
        max(0,1-|v|); 4 power law sqrt(2)/pi/(1+v^2/2)^2 (a kappa=2
        Lorentzian-type density, not a gamma distribution); 5 incomplete
        Maxwellian H(v-0.1) exp(-v^2)/sqrt(pi), mass-incomplete; 6 truncated
        slowing-down 3sqrt(3)/(4pi)/(1+|v|^3) on |v|<=4. Integer 0 through 6;
        booleans rejected.
    expression : str, default 'exp(-v.^2)/sqrt(pi)'
        Analytic density in v [dimensionless] using finite real constants, pi, + - * / and
        powers, and exp/log/sqrt/sin/cos/sinh/cosh/tanh. Powers may be written
        ** or ^, and MATLAB element-wise .^ .* ./ are accepted as the same
        operators. Real integrable density with decaying derivative; no
        arbitrary code, comparisons, attributes or indexing.
    integration_mesh : real vector, shape one-dimensional at least two points, default None
        Feature-resolving finite increasing velocity mesh [dimensionless]; infinite tails are
        also integrated. All material features resolved; no unresolved tail
        features.

    Returns
    -------
    Z : complex array, shape same as z
        Integral f(v)/(v-z) dv with the declared continuation [dimensionless]. Finite and
        representable.
    Zp : complex array, shape same as z
        Derivative dZ/dz including distributional jumps [dimensionless]. Finite and
        representable.

    Raises
    ------
    RuntimeError
        When the real-axis or exterior quadrature fails to converge; no
        unconverged value is returned.
    ValueError
        For non-numeric or non-broadcastable z, selector outside 0..6, a
        nonpositive selector-grid endpoint, an unsupported expression or
        integration mesh, or a non-finite Z/Zp result that is not representable.

    See Also
    --------
    evaluate_plasma_dispersion : Maxwellian plasma dispersion function.
    vp_init : Time-domain check with the same equilibrium.

    Notes
    -----
    For selector 0 the default Maxwellian expression is evaluated with the
    analytic plasma-dispersion kernel; a custom expression requires a finite
    feature-resolution integration mesh. The returned derivative includes
    distributional jumps for the piecewise density selectors. No root search or
    mode identification is performed by this function.

    References
    ----------
    Hua-Sheng Xie, Generalized plasma dispersion function, Phys. Plasmas 20
    (2013), 092125.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic.generalized_dispersion import evaluate_generalized_dispersion
    >>> r=evaluate_generalized_dispersion(1j,2)
    >>> assert r['Z'].imag>0
    >>> assert np.isfinite(r['Zp'])
    """
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
    r"""Evaluate Langmuir, ion-acoustic, beam and generalized residuals.

    Parameters
    ----------
    kind : str
        langmuir, iaw, beam or generalized. [dimensionless] Shape: scalar. Finite and representable.
    x : complex numeric
        Phase omega/(sqrt(2)*k). [dimensionless] Shape: scalar or nonempty array. Finite and representable.
    k : positive real
        Inverse Debye-length normalized wavenumber. [dimensionless] Shape: scalar. Finite and representable.
    ion_temperature : positive real
        Ti/Te. [dimensionless] Shape: scalar. Default: 1.0. Finite and representable.
    ion_mass : positive real
        mi/me. [dimensionless] Shape: scalar. Default: 1836.0. Finite and representable.
    beam_fraction : real
        Beam density divided by total density. [dimensionless] Shape: scalar. Default: 0.1.
        0<=beam_fraction<=1.
    beam_temperature : positive real
        Tb/Te. [dimensionless] Shape: scalar. Default: 1.0. Finite and representable.
    beam_drift : real
        Beam drift divided by beam thermal speed. [dimensionless] Shape: scalar. Default: 5.0. Finite and
        representable.
    selector : integer
        Generalized distribution selector. [dimensionless] Shape: scalar. Default: 0. 0 through 6.
    expression : str
        Analytic density in v using finite real constants, pi, arithmetic and
        exp/log/sqrt/sin/cos/sinh/cosh/tanh; MATLAB point operators accepted. [dimensionless] Shape: scalar.
        Default: 'exp(-v.^2)/sqrt(pi)'. Real integrable density with decaying derivative; no arbitrary code,
        comparisons, attributes or indexing.
    integration_mesh : real vector
        Feature-resolving finite increasing velocity mesh; infinite tails are also integrated.
        [dimensionless] Shape: one-dimensional at least two points. Default: None. All material features
        resolved; no unresolved tail features.

    Returns
    -------
    return : complex array
        Source-normalized D residual. [dimensionless] Shape: same as x. Finite and representable.

    Raises
    ------
    FloatingPointError
        FloatingPointError for a non-representable Faddeeva/generalized response; bound quadrature errors
        propagate.
    RuntimeError
        RuntimeError only where a bound generalized quadrature fails; IAW/beam use closed Faddeeva values.
    ValueError
        ValueError for an unknown kind, non-finite x/k, or invalid selector/expression/mesh; named IAW/beam
        parameters must satisfy the declared domain.

    See Also
    --------
    scirel.kinetic : Public kinetic-domain operators.

    Notes
    -----
    IAW D=k²+[1+xZ(x)]+[1+qZ(q)]/Ti with q=x/sqrt(Ti/mi). Beam D=k²+(1-nb)[1+xZ(x)]+nb/Tb[1+qZ(q)] with
    q=x/sqrt(Tb)-vd. Generalized D=k²-Zp/2. Vacuum and susceptibility normalization match the frozen
    scripts. One-dimensional unmagnetized collisionless electrostatic plasma Assumptions: Density is
    real and integrable on the real contour. No collective-mode uniqueness or certified global
    quadrature bound is asserted. k is finite positive scalar.

    References
    ----------
    Hua-Sheng Xie, Generalized plasma dispersion function, Phys. Plasmas. 20 (2013), 092125 (scientific context)

    Examples
    --------
    >>> from scirel.kinetic.generalized_dispersion import evaluate_gpdf_residual
    >>> r=evaluate_gpdf_residual('langmuir',1j,.3)
    >>> assert abs(r.imag)<1e-12
    """
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
    r"""Evaluate source Langmuir frequency and damping asymptotics.

    Parameters
    ----------
    k : positive real
        Inverse Debye-length normalized small wavenumber. [dimensionless] Shape: scalar or nonempty array.
        Finite and representable.

    Returns
    -------
    omega_real : real array
        Leading Bohm-Gross real frequency. [dimensionless] Shape: same as k. Finite and representable.
    omega_imag : real array
        Leading small-k Landau damping. [dimensionless] Shape: same as k. Finite and representable.

    Raises
    ------
    ValueError
        Raises ValueError for non-real, boolean, string, complex, empty, nonfinite or nonpositive `k`.
        Raises ValueError when the computed real frequency or damping is not representable as finite
        float64; there is no callback, quadrature or fallback path.

    See Also
    --------
    scirel.kinetic : Public kinetic-domain operators.

    Notes
    -----
    Logarithmic evaluation of the damping amplitude avoids the 0/0 form the direct expression takes when
    k³ underflows. Exact k=0 is rejected. One-dimensional unmagnetized collisionless electrostatic
    plasma Assumptions: Maxwellian normalized thermal standard deviation and plasma frequency equal one.
    Asymptotic use requires k much smaller than one.

    References
    ----------
    Hua-Sheng Xie, Generalized plasma dispersion function, Phys. Plasmas. 20 (2013), 092125 (scientific context)

    Examples
    --------
    >>> from scirel.kinetic.generalized_dispersion import evaluate_gpdf_small_k
    >>> r=evaluate_gpdf_small_k(.1)
    >>> assert abs(r['omega_real']-1.015)<1e-14
    >>> assert r['omega_imag']<0
    """
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
    r"""Run all four seeded electrostatic root scans.

    Parameters
    ----------
    kind : str
        langmuir, iaw, beam or generalized. [dimensionless] Shape: scalar. Finite and representable.
    k_values : real vector
        Optional ordered positive scan grid; None selects the family grid. [dimensionless] Shape: nonempty
        one-dimensional. Default: None. Finite and representable.
    initial_guess : complex scalar
        Optional complex seed: phase x except generalized uses frequency omega. None selects the family
        seed. [dimensionless] Shape: scalar. Default: None. Finite and representable.
    residual_tolerance : positive real
        Absolute dielectric residual gate. [dimensionless] Shape: scalar. Default: 1e-09. Finite and
        representable.
    max_evaluations : positive integer
        Per-point MINPACK function-evaluation limit. [dimensionless] Shape: scalar. Default: 300. Finite and
        representable.
    **parameters : mapping
        Additional named scientific controls [dimensionless]; documented below.

    Other Parameters
    ----------------
    ion_temperature : positive real
        Ti/Te. [dimensionless] Shape: scalar. Default: 1.0. Finite and representable.
    ion_mass : positive real
        mi/me. [dimensionless] Shape: scalar. Default: 1836.0. Finite and representable.
    beam_fraction : real
        Beam density divided by total density. [dimensionless] Shape: scalar. Default: 0.1.
        0<=beam_fraction<=1.
    beam_temperature : positive real
        Tb/Te. [dimensionless] Shape: scalar. Default: 1.0. Finite and representable.
    beam_drift : real
        Beam drift divided by beam thermal speed. [dimensionless] Shape: scalar. Default: 5.0. Finite and
        representable.
    selector : integer
        Generalized distribution selector. [dimensionless] Shape: scalar. Default: 0. 0 through 6.
    expression : str
        Analytic density in v using finite real constants, pi, arithmetic and
        exp/log/sqrt/sin/cos/sinh/cosh/tanh; MATLAB point operators accepted. [dimensionless] Shape: scalar.
        Default: 'exp(-v.^2)/sqrt(pi)'. Real integrable density with decaying derivative; no arbitrary code,
        comparisons, attributes or indexing.
    integration_mesh : real vector
        Feature-resolving finite increasing velocity mesh; infinite tails are also integrated.
        [dimensionless] Shape: one-dimensional at least two points. Default: None. All material features
        resolved; no unresolved tail features.

    Returns
    -------
    k : real vector
        Scan grid preserving requested order. [dimensionless] Shape: number of points. Finite and
        representable.
    omega : complex vector
        Qualified roots normalized by plasma frequency. [dimensionless] Shape: number of points. Finite and
        representable.
    dielectric_residual : nonnegative real vector
        Norm of real/imaginary dielectric residual. [dimensionless] Shape: number of points. Finite and
        representable.
    evaluations : integer vector
        MINPACK function evaluations at each point. [count] Shape: number of points. Finite and
        representable.

    Raises
    ------
    RuntimeError
        RuntimeError for Cauchy, real-axis or principal-value quadrature nonconvergence, or root
        nonconvergence.
    ValueError
        ValueError for invalid, nonfinite or singular declared inputs. Callback arithmetic failures
        propagate; nonrepresentable transform raises ValueError.

    See Also
    --------
    scirel.kinetic.generalized_dispersion.evaluate_gpdf_residual : Related contract dependency.

    Notes
    -----
    Declared grids: Langmuir .1:.1:1 then2:1:10 with fixed phase1-.1i; IAW1.1:-.05:.05 with
    phase.04-.02i; beam.4:-.005:.05 with phase(1-.01i)*sqrt(2)*.4; generalized.1:.1:1 then1.5:.5:5 with
    frequency1.5-.001i. IAW/beam continue previous phase; generalized continues previous frequency. k is
    closed over instead of passed as the invalid fourth fsolve argument. Solvers use D/k², or qualified
    Maxwellian epsilon directly, and require solver success, residual tolerance, and function-evaluation
    budget. One-dimensional unmagnetized collisionless electrostatic plasma Assumptions: Each seeded
    root must converge within its budget and dielectric residual tolerance. k_values preserve
    continuation order; initial_guess units depend on family exactly as declared.

    References
    ----------
    Hua-Sheng Xie, Generalized plasma dispersion function, Phys. Plasmas. 20 (2013), 092125 (scientific context)

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic.generalized_dispersion import scan_gpdf_roots
    >>> r=scan_gpdf_roots('beam',k_values=[.3,.295],initial_guess=(1-.01j)/(np.sqrt(2)*.4))
    >>> assert np.max(r['dielectric_residual'])<1e-9
    >>> assert r['omega'][0].imag>0
    """
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
