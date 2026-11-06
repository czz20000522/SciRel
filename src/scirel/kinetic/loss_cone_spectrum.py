"""Compute ordered even loss-cone eigenmodes with a local Sturm phase and boundary check."""

from functools import lru_cache
import numpy as np
from ._loss_cone_modes import regular_even_mode


def _mode(degree, xi, n_terms=15, backend="truncated"):
    if backend not in {"truncated", "hypergeometric"}:
        raise ValueError("backend must be truncated or hypergeometric")
    return regular_even_mode(degree, xi)


def _endpoint_phase(eigenvalue, end, order):
    if eigenvalue == 0.0:
        return np.pi / 2.0
    k = np.sqrt(eigenvalue)

    # y=rho*sin(theta), (1-x²)y'/k=rho*cos(theta).
    # This phase is continuous through zeros and counts the ordered modes.
    def rhs(x, theta):
        return k * (np.cos(theta) ** 2 / (1.0 - x * x) + np.sin(theta) ** 2)

    from scipy.integrate import solve_ivp

    solution = solve_ivp(
        rhs,
        (0.0, end),
        [np.pi / 2],
        method="DOP853",
        rtol=2e-13,
        atol=2e-14,
        max_step=end / max(32, 8 * (order + 1)),
    )
    if not solution.success or not np.isfinite(solution.y[0, -1]):
        raise RuntimeError("loss-cone Sturm phase integration did not converge")
    return float(solution.y[0, -1])


@lru_cache(maxsize=128)
def _ordered_degrees(xi_tp, mode_count):
    from scipy.optimize import brentq

    roots = []
    for order in range(mode_count):
        target = (order + 1) * np.pi
        # Rayleigh quotient: p(x)=1-x² <= 1, so this constant-p
        # Neumann/Dirichlet eigenvalue bounds the same indexed root above.
        upper = ((order + 0.5) * np.pi / xi_tp) ** 2
        lower = roots[-1] if roots else 0.0
        residual = lambda value: _endpoint_phase(value, xi_tp, order) - target
        root = brentq(residual, lower, upper * (1.0 + 1e-12), xtol=2e-11, rtol=2e-12)
        roots.append(root)
    degrees = (np.sqrt(1.0 + 4.0 * np.asarray(roots)) - 1.0) / 2.0
    return tuple(float(x) for x in degrees)


def solve_loss_cone_spectrum(xi_tp, mode_count, grid_points=256, backend="truncated"):
    """Compute the lowest ordered even angular eigenmodes, returning integer degrees where they occur, with a regular initial-value solution.

    Parameters
    ----------
    xi_tp : float-convertible, scalar
        Loss-cone pitch-cosine endpoint where the angular mode is set to zero. [dimensionless] Constraints: Converted with float; must satisfy 0 < xi_tp < 1.
    mode_count : integer-valued real or integer, scalar
        Number of lowest ordered modes, including any integer degree. [count] Constraints: Positive integer value; booleans and fractional values are rejected.
    grid_points : int-convertible, scalar
        Requested number of pitch-cosine samples for returned eigenfunctions. [count] Constraints: Integer value at least two; actual sample count is max(grid_points,mode_count+8). Default: ``256``.
    backend : string-convertible, scalar
        Backend selector; both accepted values select the same regular scaled evaluation. [text] Constraints: Only 'truncated' and 'hypergeometric'; both use regular scaled initial-value evaluation and Sturm root ordering. No truncated series is used. Default: ``'truncated'``.

    Returns
    -------
    xi : float64 ndarray, (N_grid,)
        Uniform pitch-cosine sample positions starting at the symmetry endpoint. [dimensionless] Constraints: xi[i]=i*xi_tp/N_grid for i=0..N_grid-1; xi_tp itself is not sampled.
    eigenvalues : float64 ndarray, (N_mode,)
        Angular eigenvalue nu(nu+1) for each returned degree. [dimensionless] Constraints: Positive and ordered with degrees for successful finite solves.
    degrees : float64 ndarray, (N_mode,)
        Nonnegative regular even-mode degree for each eigenvalue. [dimensionless] Constraints: Ordered with the eigenvalues; integer degrees are preserved.
    eigenfunctions : float64 ndarray, (N_grid, N_mode)
        Angular mode samples, one column per degree. [dimensionless] Constraints: First row is numerically normalized to one; no boundary row at xi_tp is returned.
    backend : str, scalar
        Requested legacy evaluator name; see evaluation_method for the actual numerical method. [text] Constraints: Either 'truncated' or 'hypergeometric'.
    evaluation_method : str, scalar
        Actual common evaluator used by both legacy backend names. [text] Constraints: regular_even_scaled_ivp_with_sturm_phase_ordering
    boundary_residuals : float64 array, (N_mode,)
        Regular-mode values at the Dirichlet endpoint. [dimensionless] Constraints: Absolute value at most 2e-8 on successful return.

    Raises
    ------
    ValueError
        If ``xi_tp`` is outside ``(0, 1)``, a count is invalid, the backend name
        is unknown, or native numeric conversion fails.
    RuntimeError
        If the Sturm phase integration fails or an independently evaluated
        endpoint residual exceeds ``2e-8``.
    FloatingPointError
        If a mode or boundary evaluation returns an unrepresentable non-finite
        value.
    See Also
    --------
    evaluate_plasma_dispersion
        Maxwellian plasma dispersion function used by related wave calculations.
    evaluate_generalized_dispersion
        Generalized density transform for broader velocity distributions.
    Notes
    -----
    The regular even solution satisfies ``-[(1-xi**2)u']' = lambda u`` with ``u(0)=1``, ``u'(0)=0`` and a Dirichlet condition at ``xi_tp``. A continuous Sturm phase orders roots; integer-coincident degrees are preserved. Both accepted backend names select the same regular scaled initial-value evaluator and Sturm ordering; no finite polynomial truncation is used. The returned pitch grid includes zero and excludes ``xi_tp``. This angular problem alone does not validate a kinetic population, transport model or global equilibrium.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum
    >>> r=solve_loss_cone_spectrum(1/np.sqrt(3),2,grid_points=40)
    >>> np.testing.assert_allclose(r['eigenvalues'][0],6.,rtol=1e-10)
    >>> np.testing.assert_allclose(r['eigenfunctions'][:,0],1-3*r['xi']**2,atol=2e-10)
    >>> assert np.max(np.abs(r['boundary_residuals']))<2e-8

    """
    xi_tp = float(xi_tp)
    if not np.isfinite(xi_tp) or not 0.0 < xi_tp < 1.0:
        raise ValueError("xi_tp must be inside the open interval (0, 1)")
    if isinstance(mode_count, (bool, np.bool_)) or int(mode_count) != mode_count or mode_count <= 0:
        raise ValueError("mode_count must be a positive integer")
    if (
        isinstance(grid_points, (bool, np.bool_))
        or int(grid_points) != grid_points
        or grid_points < 2
    ):
        raise ValueError("grid_points must be an integer of at least two")
    mode_count, grid_points = int(mode_count), max(int(grid_points), int(mode_count) + 8)
    backend = str(backend)
    if backend not in {"truncated", "hypergeometric"}:
        raise ValueError("backend must be truncated or hypergeometric")
    degrees = np.asarray(_ordered_degrees(xi_tp, mode_count))
    eigenvalues = degrees * (degrees + 1)
    boundaries = np.asarray([float(regular_even_mode(v, xi_tp)) for v in degrees])
    if np.any(np.abs(boundaries) > 2e-8):
        raise RuntimeError(
            "ordered eigenvalues failed independent regular-mode boundary verification"
        )
    xi = np.linspace(0.0, xi_tp, grid_points, endpoint=False)
    modes = np.column_stack([regular_even_mode(v, xi) for v in degrees])
    return {
        "xi": xi,
        "eigenvalues": eigenvalues,
        "degrees": degrees,
        "eigenfunctions": modes,
        "backend": backend,
        "evaluation_method": "regular_even_scaled_ivp_with_sturm_phase_ordering",
        "boundary_residuals": boundaries,
    }


__all__ = ["solve_loss_cone_spectrum"]
