"""Cancellation-aware electrostatic Maxwellian response and a residual-gated complex mode solver."""

import numpy as np
from .plasma_dispersion import evaluate_plasma_dispersion


def _numeric(value, name, scalar=False, positive=False):
    try:
        raw = np.asarray(value)
        objects = np.asarray(value, dtype=object)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain finite numeric values") from exc
    if (
        raw.size == 0
        or raw.dtype.kind not in ("iuf" if positive else "iufc")
        or any(isinstance(v, (bool, np.bool_)) for v in objects.flat)
        or (scalar and raw.shape != ())
    ):
        raise ValueError(f"{name} must contain finite numeric values")
    if not np.all(np.isfinite(raw)) or (positive and np.any(raw <= 0)):
        raise ValueError(f"{name} must contain finite numeric values")
    return raw


def _susceptibility(omega, k, z):
    """Return chi and a numerical error estimate (not an interval certificate).

    |z|=12 separates cancellation-prone asymptotics from direct Faddeeva.
    In the upper half-plane the inverse-power expansion is optimally truncated;
    terms stop at roundoff or before growth. Reflection supplies the exact
    exponential for Im(z)<0; on the real axis its half contribution is retained.
    """
    u = np.finfo(float).eps
    if abs(z) < 12:
        Z = complex(evaluate_plasma_dispersion(z)["Z"])
        product = z * Z
        chi = ((1 + product) / k) / k
        sensitivity = 1 + abs(z) ** 2 if z.imag < 0 else 1
        err = ((32 * u * sensitivity * (1 + abs(product))) / k) / k
        return chi, err
    ratio = (k / omega) ** 2
    total = term = 1 + 0j
    last = 0.0
    for n in range(1, 201):
        next_term = term * (2 * n + 1) * ratio
        if abs(next_term) >= abs(term):
            last = abs(next_term)
            break
        total += next_term
        term = next_term
        last = abs(term * (2 * n + 3) * ratio)
        if last <= u * abs(total):
            break
    inverse = 1 / omega
    algebraic = -(inverse * inverse) * total
    err = abs(inverse) * abs(inverse) * (last + 16 * u * abs(total))
    exponential = 0j
    if z.imag <= 0:
        factor = 2 if z.imag < 0 else 1
        # Form in log amplitude to avoid an underflowed exponential multiplied
        # by an overflowing 1/k**2. Phase reduction is NumPy complex exp.
        wide_z = np.clongdouble(z)
        square = wide_z * wide_z
        logterm = -square + np.log(factor * np.sqrt(np.pi)) + np.log(wide_z) - 2 * np.log(k)
        exponential = complex(1j * np.exp(logterm))
        if exponential != 0:
            sensitivity = np.longdouble(1) + abs(square) + abs(np.log(k))
            err += float(32 * u * sensitivity * abs(exponential))
    return algebraic + exponential, err


def evaluate_maxwellian_electrostatic(omega, k):
    """Return epsilon, D=k²*epsilon, z and epsilon_error estimate.

    omega is normalized by plasma frequency, k by inverse Debye length with
    thermal standard deviation one. Any nonempty real/complex omega shape and
    finite positive real scalar k are accepted when all outputs are representable.
    epsilon_error estimates arithmetic/truncation error; it is not a rigorous
    enclosure. No k cutoff or real/lower-plane restriction is imposed.
    """
    k = float(_numeric(k, "k", scalar=True, positive=True))
    values = np.asarray(_numeric(omega, "omega"), dtype=complex)
    epsilon = np.empty(values.shape, dtype=complex)
    errors = np.empty(values.shape, dtype=float)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
        z = (values / k) / np.sqrt(2)
        if not np.all(np.isfinite(z)):
            raise ValueError("electrostatic response is not representable")
        for index in np.ndindex(values.shape):
            chi, err = _susceptibility(complex(values[index]), k, complex(z[index]))
            epsilon[index] = 1 + chi
            errors[index] = err + np.finfo(float).eps * (1 + abs(chi))
        D = (epsilon * k) * k
    if (
        not np.all(np.isfinite(D))
        or not np.all(np.isfinite(epsilon))
        or not np.all(np.isfinite(errors))
    ):
        raise ValueError("electrostatic response is not representable")
    return {"epsilon": epsilon, "D": D, "z": z, "epsilon_error": errors}


def solve_maxwellian_electrostatic_mode(
    k, initial_omega, *, xtol=1e-10, residual_tolerance=1e-9, max_evaluations=200
):
    """Solve one seeded mode using dielectric components and an error-aware gate.

    Acceptance requires MINPACK success, its evaluation budget, and
    (abs(epsilon)+epsilon_error)/(1+abs(chi)) <= residual_tolerance;
    epsilon_error/(1+abs(chi)) must be <= residual_tolerance/4.
    This relative backward residual measures cancellation between vacuum and
    susceptibility independently of k². It does not prove root uniqueness or
    select the least damped branch. Numerical error is estimated, not certified.

    Parameters
    ----------
    k : positive real
        Positive normalized wave number [inverse normalized length]. Finite
        strictly positive real scalar; booleans, complex values and arrays
        rejected.
    initial_omega : complex numeric
        Complex root seed [normalized frequency]. Finite and representable.
    xtol : positive real, default 1e-10
        MINPACK step tolerance. Finite strictly positive real scalar, booleans
        and arrays rejected.
    residual_tolerance : positive real, default 1e-09
        Acceptance threshold for normalized epsilon residual plus estimated
        error. Finite strictly positive real scalar, booleans and arrays
        rejected.
    max_evaluations : positive integer, default 200
        Maximum residual evaluations [count]. Positive integer scalar; booleans
        rejected.

    Returns
    -------
    omega : complex
        Converged complex mode [normalized frequency]. Finite and representable.
    residual : complex
        Final complex D. Finite and representable.
    evaluations : integer
        Residual evaluations [count]. Finite and representable.
    epsilon : complex
        Final dielectric. Finite and representable.
    normalized_residual : real
        Absolute epsilon residual normalized by 1+|chi|. Finite and accepted
        only below residual_tolerance after estimated-error gate.
    normalized_residual_error : real
        Estimated epsilon error on the same normalization. Finite and accepted
        only below residual_tolerance/4.

    Raises
    ------
    RuntimeError
        Raises RuntimeError when MINPACK fails, exceeds max_evaluations, or the
        normalized residual/error gate fails; no partial mode is returned.
        Unrepresentable evaluation raises ValueError; solver unrepresentable
        trial response raises RuntimeError. Unexpected SciPy execution errors
        propagate.
    ValueError
        Raises ValueError for invalid, nonfinite, singular or incompatible
        inputs. Unrepresentable evaluation raises ValueError; solver
        unrepresentable trial response raises RuntimeError. Unexpected SciPy
        execution errors propagate.

    See Also
    --------
    evaluate_plasma_dispersion : The Z function used in the dispersion relation.
    solve_vlasov_poisson : Time-domain Landau damping.

    Examples
    --------
    >>> from scirel.kinetic import solve_maxwellian_electrostatic_mode
    >>> r=solve_maxwellian_electrostatic_mode(0.4,1.45-0.1j)
    >>> assert r["normalized_residual"]+r["normalized_residual_error"]<=1e-9
    >>> assert r["normalized_residual_error"]<=2.5e-10
    """
    seed = complex(_numeric(initial_omega, "initial_omega", scalar=True))
    if (
        isinstance(max_evaluations, (bool, np.bool_))
        or not isinstance(max_evaluations, (int, np.integer))
        or max_evaluations < 1
    ):
        raise ValueError("max_evaluations must be a positive integer")
    xtol = float(_numeric(xtol, "xtol", scalar=True, positive=True))
    tolerance = float(
        _numeric(residual_tolerance, "residual_tolerance", scalar=True, positive=True)
    )
    evaluate_maxwellian_electrostatic(seed, k)

    def residual(parts):
        value = complex(evaluate_maxwellian_electrostatic(complex(*parts), k)["epsilon"])
        return [value.real, value.imag]

    # Keep the nonlinear solver backend out of module import and rejected-input
    # paths.  SciPy remains a declared core runtime dependency; loading it only
    # after the seed response has passed its representability contract keeps
    # discovery and validation cheap while preserving the exact solver path.
    from scipy.optimize import root

    try:
        result = root(
            residual,
            [seed.real, seed.imag],
            method="hybr",
            options={"xtol": xtol, "maxfev": int(max_evaluations)},
        )
    except ValueError as exc:
        raise RuntimeError(
            "Maxwellian solve encountered an unrepresentable trial response"
        ) from exc
    omega = complex(*result.x)
    response = evaluate_maxwellian_electrostatic(omega, k)
    epsilon = complex(response["epsilon"])
    scale = 1 + abs(epsilon - 1)
    error = float(response["epsilon_error"]) / scale
    normalized = abs(epsilon) / scale
    if (
        not result.success
        or normalized + error > tolerance
        or error > tolerance / 4
        or result.nfev > max_evaluations
    ):
        raise RuntimeError(
            f"Maxwellian mode solve failed: normalized_residual={normalized:.17g}; estimated_error={error:.17g}; evaluations={result.nfev}; {result.message}"
        )
    return {
        "omega": omega,
        "residual": complex(response["D"]),
        "evaluations": int(result.nfev),
        "epsilon": epsilon,
        "normalized_residual": normalized,
        "normalized_residual_error": error,
    }


__all__ = ["evaluate_maxwellian_electrostatic", "solve_maxwellian_electrostatic_mode"]
