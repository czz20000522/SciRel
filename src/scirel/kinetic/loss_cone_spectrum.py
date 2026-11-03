"""Compute ordered even loss-cone eigenmodes with a local Sturm phase and boundary check."""
from functools import lru_cache
import numpy as np
from ._loss_cone_modes import regular_even_mode


def _mode(degree, xi, n_terms=15, backend='truncated'):
    if backend not in {'truncated', 'hypergeometric'}:
        raise ValueError('backend must be truncated or hypergeometric')
    return regular_even_mode(degree, xi)


def _endpoint_phase(eigenvalue, end, order):
    if eigenvalue == 0.0:
        return np.pi / 2.0
    k = np.sqrt(eigenvalue)
    # y=rho*sin(theta), (1-x²)y'/k=rho*cos(theta).
    # This phase is continuous through zeros and counts the ordered modes.
    def rhs(x, theta):
        return k * (np.cos(theta) ** 2 / (1.0 - x*x) + np.sin(theta) ** 2)
    from scipy.integrate import solve_ivp

    solution = solve_ivp(rhs, (0.0, end), [np.pi/2], method='DOP853',
                         rtol=2e-13, atol=2e-14,
                         max_step=end / max(32, 8*(order+1)))
    if not solution.success or not np.isfinite(solution.y[0, -1]):
        raise RuntimeError('loss-cone Sturm phase integration did not converge')
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
        root = brentq(residual, lower, upper*(1.0+1e-12),
                      xtol=2e-11, rtol=2e-12)
        roots.append(root)
    degrees = (np.sqrt(1.0+4.0*np.asarray(roots))-1.0)/2.0
    return tuple(float(x) for x in degrees)


def solve_loss_cone_spectrum(xi_tp, mode_count, grid_points=256, backend='truncated'):
    """Return the lowest Neumann-at-zero/Dirichlet-at-xi_tp even modes.

    Both legacy backend names now use the regular, untruncated even
    solution through scaled initial-value integration. ``backend`` records the requested name and
    ``evaluation_method`` the actual method. A Sturm phase orders roots and
    retains integer degrees; an independently evaluated boundary value must
    agree. The xi grid includes zero and excludes the Dirichlet endpoint.
    This angular eigenproblem does not itself validate a kinetic population.
    """
    xi_tp = float(xi_tp)
    if not np.isfinite(xi_tp) or not 0.0 < xi_tp < 1.0:
        raise ValueError('xi_tp must be inside the open interval (0, 1)')
    if isinstance(mode_count, (bool, np.bool_)) or int(mode_count) != mode_count or mode_count <= 0:
        raise ValueError('mode_count must be a positive integer')
    if isinstance(grid_points, (bool, np.bool_)) or int(grid_points) != grid_points or grid_points < 2:
        raise ValueError('grid_points must be an integer of at least two')
    mode_count, grid_points = int(mode_count), max(int(grid_points), int(mode_count)+8)
    backend = str(backend)
    if backend not in {'truncated', 'hypergeometric'}:
        raise ValueError('backend must be truncated or hypergeometric')
    degrees = np.asarray(_ordered_degrees(xi_tp, mode_count))
    eigenvalues = degrees*(degrees+1)
    boundaries = np.asarray([float(regular_even_mode(v, xi_tp)) for v in degrees])
    if np.any(np.abs(boundaries) > 2e-8):
        raise RuntimeError('ordered eigenvalues failed independent regular-mode boundary verification')
    xi = np.linspace(0., xi_tp, grid_points, endpoint=False)
    modes = np.column_stack([regular_even_mode(v, xi) for v in degrees])
    return {'xi': xi, 'eigenvalues': eigenvalues, 'degrees': degrees,
            'eigenfunctions': modes, 'backend': backend,
            'evaluation_method': 'regular_even_scaled_ivp_with_sturm_phase_ordering',
            'boundary_residuals': boundaries}

__all__ = ['solve_loss_cone_spectrum']
