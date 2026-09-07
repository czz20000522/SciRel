"""Loss-cone angular eigenpairs used by the SciRel anisotropic pressure closure."""
import numpy as np
from scipy.optimize import brentq
from scipy.special import hyp2f1

def _legendre_p(degree, xi, n_terms=15, backend='truncated'):
    xi = np.asarray(xi, dtype=float)
    if backend == 'hypergeometric':
        return hyp2f1(-float(degree), float(degree) + 1.0, 1.0, (1.0 - xi) / 2.0)
    z = np.clip((1.0 - xi) / 2.0, 0.0, 1.0)
    result = np.ones_like(z, dtype=float)
    coefficient = 1.0
    for order in range(1, int(n_terms)):
        coefficient *= (-degree + order - 1.0) * (degree + order) / (order * order)
        result += coefficient * np.power(z, order)
    return result

def _legendre_q(degree, xi, n_terms=15, backend='truncated'):
    sine = np.sin(np.pi * float(degree))
    if abs(sine) < 1e-12:
        raise ValueError('fractional Legendre Q requires a non-integer degree')
    return 0.5 * np.pi / sine * (np.cos(np.pi * float(degree)) * _legendre_p(degree, xi, n_terms, backend) - _legendre_p(degree, -np.asarray(xi, dtype=float), n_terms, backend))

def _mode(degree, xi, n_terms=15, backend='truncated'):
    h = 1e-05
    p0, q0 = (float(_legendre_p(degree, 0.0, n_terms, backend)), float(_legendre_q(degree, 0.0, n_terms, backend)))
    dp0 = float((_legendre_p(degree, h, n_terms, backend) - _legendre_p(degree, -h, n_terms, backend)) / (2.0 * h))
    dq0 = float((_legendre_q(degree, h, n_terms, backend) - _legendre_q(degree, -h, n_terms, backend)) / (2.0 * h))
    a_coeff, b_coeff = np.linalg.solve(np.array([[p0, q0], [dp0, dq0]]), np.array([1.0, 0.0]))
    return a_coeff * _legendre_p(degree, xi, n_terms, backend) + b_coeff * _legendre_q(degree, xi, n_terms, backend)

def _analytic_degrees(xi_tp, mode_count, n_terms=15, backend='truncated'):
    upper = max(8.0, 4.0 * int(mode_count) + 4.0)
    grid = np.linspace(0.05, upper, max(2048, 256 * int(mode_count)))
    values = []
    for degree in grid:
        if abs(degree - round(degree)) < 1e-07:
            values.append(np.nan)
            continue
        try:
            values.append(float(_mode(degree, xi_tp, n_terms, backend)))
        except (ValueError, np.linalg.LinAlgError, FloatingPointError):
            values.append(np.nan)
    roots = []
    for left, right, f_left, f_right in zip(grid[:-1], grid[1:], values[:-1], values[1:]):
        if not np.isfinite(f_left) or not np.isfinite(f_right) or f_left * f_right >= 0.0:
            continue
        try:
            root = brentq(lambda degree: float(_mode(degree, xi_tp, n_terms, backend)), left, right, xtol=1e-11)
        except (ValueError, RuntimeError, FloatingPointError):
            continue
        if abs(root - round(root)) < 1e-06 or (roots and abs(root - roots[-1]) <= 1e-05):
            continue
        roots.append(root)
        if len(roots) >= int(mode_count):
            break
    if len(roots) < int(mode_count):
        raise ValueError('unable to find the requested analytic loss-cone modes')
    return np.asarray(roots, dtype=float)

def solve_loss_cone_spectrum(xi_tp, mode_count, grid_points=256, backend='truncated'):
    """Solve the source-defined loss-cone angular spectrum.

    Returns a mapping containing the cell-centre pitch grid, the lowest
    positive eigenvalues, fractional Legendre degrees, and eigenfunctions
    normalized to one at the symmetry endpoint.
    """
    xi_tp = float(xi_tp)
    mode_count = int(mode_count)
    grid_points = int(grid_points)
    if not 0.0 < xi_tp < 1.0:
        raise ValueError('xi_tp must be inside the open interval (0, 1)')
    if mode_count <= 0:
        raise ValueError('mode_count must be positive')
    grid_points = max(grid_points, mode_count + 8)
    xi = np.linspace(0.0, xi_tp, grid_points, endpoint=False, dtype=float)
    backend = str(backend)
    if backend not in {'truncated', 'hypergeometric'}:
        raise ValueError('backend must be truncated or hypergeometric')
    degrees = _analytic_degrees(xi_tp, mode_count, backend=backend)
    eigenvalues = degrees * (degrees + 1.0)
    eigenfunctions = np.column_stack([_mode(degree, xi, backend=backend) for degree in degrees])
    return {'xi': xi, 'eigenvalues': eigenvalues, 'degrees': degrees, 'eigenfunctions': eigenfunctions, 'backend': backend}
__all__ = ['solve_loss_cone_spectrum']
