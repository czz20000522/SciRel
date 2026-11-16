"""Shared reference for the multifluid pencil and its SI state fields.

Nothing here reuses the implementation's algebra: the fields are recomputed from
the named state entries with ``mpmath`` at 40 digits, and the eigenvalue
statement is checked against the *definition* of a generalized eigenvalue,
``(M - lambda A) x ~ 0``, rather than against a second solver.

Why a second solver is not the oracle: the pencil's ``A`` is singular on the
electrostatic support (the docstring documents a support decomposition for
exactly this reason), so a naive dense ``eig(M, A)`` is ill-conditioned there and
disagrees with the returned spectrum by ~1e-4 relative on the default case --
measured, not assumed.  A residual is the definition of an eigenvalue and does
not depend on the other solver's conditioning.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np

EPS = np.finfo(float).eps


def high_precision() -> None:
    """Set the reference precision; ``mpmath`` precision is process-global."""
    mp.mp.dps = 40


def plasma_frequencies(state: dict) -> np.ndarray:
    """``omega_p = sqrt(n q**2 / (epsilon0 m))`` per species, at 40 digits."""
    high_precision()
    n = np.atleast_1d(np.asarray(state["n"], dtype=float)).ravel()
    q = np.atleast_1d(np.asarray(state["q"], dtype=float)).ravel()
    m = np.atleast_1d(np.asarray(state["m"], dtype=float)).ravel()
    epsilon0 = float(np.asarray(state["epsilon0"]).ravel()[0])
    return np.array(
        [
            float(mp.sqrt(mp.mpf(float(n[i])) * mp.mpf(float(q[i])) ** 2
                          / (mp.mpf(epsilon0) * mp.mpf(float(m[i])))))
            for i in range(n.size)
        ]
    )


def gyro_frequencies(state: dict) -> np.ndarray:
    """Signed ``Omega = q B0 / m`` per species, at 40 digits."""
    high_precision()
    q = np.atleast_1d(np.asarray(state["q"], dtype=float)).ravel()
    m = np.atleast_1d(np.asarray(state["m"], dtype=float)).ravel()
    b0 = float(np.asarray(state["B0"]).ravel()[0])
    return np.array(
        [float(mp.mpf(float(q[i])) * mp.mpf(b0) / mp.mpf(float(m[i]))) for i in range(q.size)]
    )


def total_mass_density(state: dict) -> float:
    """``rho = sum_s m_s n_s`` at 40 digits."""
    high_precision()
    n = np.atleast_1d(np.asarray(state["n"], dtype=float)).ravel()
    m = np.atleast_1d(np.asarray(state["m"], dtype=float)).ravel()
    return float(sum(mp.mpf(float(m[i])) * mp.mpf(float(n[i])) for i in range(n.size)))


def total_charge_density(state: dict) -> float:
    """``rho_q = sum_s q_s n_s`` at 40 digits."""
    high_precision()
    n = np.atleast_1d(np.asarray(state["n"], dtype=float)).ravel()
    q = np.atleast_1d(np.asarray(state["q"], dtype=float)).ravel()
    return float(sum(mp.mpf(float(q[i])) * mp.mpf(float(n[i])) for i in range(n.size)))


def current_density(state: dict) -> np.ndarray:
    """``J_k = sum_s q_s n_s v_{s,k}`` at 40 digits."""
    high_precision()
    n = np.atleast_1d(np.asarray(state["n"], dtype=float)).ravel()
    q = np.atleast_1d(np.asarray(state["q"], dtype=float)).ravel()
    v = np.asarray(state["v"], dtype=float)
    velocity = v.reshape(n.size, -1) if v.size % n.size == 0 else v
    return np.array(
        [
            float(sum(mp.mpf(float(q[i])) * mp.mpf(float(n[i])) * mp.mpf(float(velocity[i, k]))
                      for i in range(n.size)))
            for k in range(velocity.shape[1])
        ]
    )


def generalized_residual(M: np.ndarray, A: np.ndarray, omega: complex) -> float:
    """``sigma_min(M - lambda A) / ||M - lambda A||`` with ``lambda = -i omega``."""
    pencil = np.asarray(M, complex) - (-1j * complex(omega)) * np.asarray(A, complex)
    norm = np.linalg.norm(pencil)
    if norm == 0.0:
        return 0.0
    return float(np.linalg.svd(pencil, compute_uv=False)[-1] / norm)


def eigenvector_residual(M: np.ndarray, A: np.ndarray, omega: complex, vector: np.ndarray) -> float:
    """``||(M - lambda A) x|| / (||M - lambda A|| ||x||)`` for a returned eigenvector."""
    pencil = np.asarray(M, complex) - (-1j * complex(omega)) * np.asarray(A, complex)
    x = np.asarray(vector, complex)
    denominator = np.linalg.norm(pencil) * np.linalg.norm(x)
    if denominator == 0.0:
        return 0.0
    return float(np.linalg.norm(pencil @ x) / denominator)
