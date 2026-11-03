"""Neutral source-free relativistic co-drift generalized spectrum operator.

The callable accepts the typed normalized case mapping used by the source adapter.
It preserves source matrix coordinates and returns both source orderings of the
complete complex spectrum.  This module has no source checkout dependency.
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import eig

__all__ = ["solve_relativistic_codrift_spectrum"]

def solve_relativistic_codrift_spectrum(case: dict) -> dict:
    c = float(case["constants"]["c"])
    eps0 = float(case["constants"]["epsilon0"])
    mu0 = float(case["constants"]["mu0"])
    b0 = float(case["constants"]["B0"])
    if (c, eps0, mu0, b0) != (1.0, 1.0, 1.0, 1.0):
        raise ValueError("This bound normalized initial function requires c=epsilon0=mu0=B0=1")
    if case.get("collision_matrix") != "zero":
        raise ValueError("Only the declared zero collision matrix is supported")
    k = np.asarray(case["k"], dtype=float)
    if k.ndim != 2 or k.shape[1] != 3 or np.any(k[:, 1] != 0):
        raise ValueError("k must be N x 3 with ky=0")
    rel = bool(case["relativistic"])
    species = case["species"]
    s = len(species)
    q = np.array([float(x["q"]) for x in species])
    m = np.array([float(x["m"]) for x in species])
    n = np.array([float(x["n0"]) for x in species])
    v = np.array([x["v0"] for x in species], dtype=float)
    cspar = np.array([float(x["cs_parallel"]) for x in species])
    csperp = np.array([float(x["cs_perp"]) for x in species])
    grad = np.array([x["grad_log_n"] for x in species], dtype=float)
    for sp in species:
        if float(sp["gamma_pressure"]) != 1 or float(sp["m"]) <= 0 or float(sp["n0"]) <= 0:
            raise ValueError("Source initial requires gamma_pressure=1 and positive mass/density")
        if len(sp["v0"]) != 3 or len(sp["grad_log_n"]) != 2:
            raise ValueError("Species velocity/gradient dimensions are invalid")
    if rel and np.any(np.sum(v * v, axis=1) >= c * c):
        raise ValueError("Relativistic speed must be less than c")

    out = []
    for kx, _, kz in k:
        dim = 4 * s + 6
        M = np.zeros((dim, dim), dtype=complex)
        A = np.eye(dim, dtype=complex)
        ind2 = 4 * s
        rho = m * n
        # Source initial.m defines Deltas = -(Pperp-Pparallel)/B0.
        delta = (rho * cspar**2 - rho * csperp**2) / b0
        wc = q * b0 / m
        for j in range(s):
            ind = 4 * j
            dotkv = kx * v[j, 0] + kz * v[j, 2]
            M[ind, ind] = -1j * dotkv
            M[ind, ind + 1] = -1j * kx * n[j] - grad[j, 0] * n[j]
            M[ind, ind + 2] = -grad[j, 1] * n[j]
            M[ind, ind + 3] = -1j * kz * n[j]
            aj = np.eye(3)
            if rel:
                vv = v[j]
                gamma = 1.0 / np.sqrt(1.0 - np.dot(vv, vv) / c**2)
                aj = gamma * np.eye(3) + gamma**3 * np.outer(vv, vv) / c**2
            A[ind + 1:ind + 4, ind + 1:ind + 4] = aj
            M[ind + 1:ind + 4, ind + 1:ind + 4] = -1j * dotkv * aj
            M[ind + 1, ind] = -1j * kx * csperp[j] ** 2 / n[j]
            M[ind + 3, ind] = -1j * kz * cspar[j] ** 2 / n[j]
            M[ind + 1, ind + 2] += wc[j]
            M[ind + 2, ind + 1] -= wc[j]
            M[ind + 1, ind2] = q[j] / m[j]
            M[ind + 2, ind2 + 1] = q[j] / m[j]
            M[ind + 3, ind2 + 2] = q[j] / m[j]
            M[ind + 1, ind2 + 4] = -q[j] / m[j] * v[j, 2]
            M[ind + 1, ind2 + 5] = q[j] / m[j] * v[j, 1]
            M[ind + 2, ind2 + 3] = q[j] / m[j] * v[j, 2]
            M[ind + 2, ind2 + 5] = -q[j] / m[j] * v[j, 0]
            M[ind + 3, ind2 + 3] = -q[j] / m[j] * v[j, 1]
            M[ind + 3, ind2 + 4] = q[j] / m[j] * v[j, 0]
            M[ind + 1, ind2 + 3] += -1j * kz * delta[j] / rho[j]
            M[ind + 2, ind2 + 4] += -1j * kz * delta[j] / rho[j]
            M[ind + 3, ind2 + 3] += -1j * kx * 2 * delta[j] / rho[j]
            M[ind2, ind] = -q[j] * v[j, 0] / eps0
            M[ind2 + 1, ind] = -q[j] * v[j, 1] / eps0
            M[ind2 + 2, ind] = -q[j] * v[j, 2] / eps0
            M[ind2, ind + 1] = -q[j] * n[j] / eps0
            M[ind2 + 1, ind + 2] = -q[j] * n[j] / eps0
            M[ind2 + 2, ind + 3] = -q[j] * n[j] / eps0
        M[ind2, ind2 + 4] = -1j * kz * c**2
        M[ind2 + 1, ind2 + 3] = 1j * kz * c**2
        M[ind2 + 1, ind2 + 5] = -1j * kx * c**2
        M[ind2 + 2, ind2 + 4] = 1j * kx * c**2
        M[ind2 + 3, ind2 + 1] = 1j * kz
        M[ind2 + 4, ind2] = -1j * kz
        M[ind2 + 4, ind2 + 2] = 1j * kx
        M[ind2 + 5, ind2 + 1] = -1j * kx
        d = eig(M, A, right=False)
        w = 1j * d
        w_real = w[np.argsort(-w.real)]
        w_imag = w[np.argsort(-w.imag)]
        if not np.all(np.isfinite(w.real)) or not np.all(np.isfinite(w.imag)):
            raise FloatingPointError("Source returned wrong-size or nonfinite frequency spectrum")
        out.append({"real_order": np.column_stack((w_real.real, w_real.imag)).tolist(),
                    "imag_order": np.column_stack((w_imag.real, w_imag.imag)).tolist()})
    return {"spectra": out}


solve_spectrum = solve_relativistic_codrift_spectrum
