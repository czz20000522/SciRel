"""Local assembly of the fluid wavevector matrix from species scales, pole residues, and harmonic response terms."""

from __future__ import annotations

import operator
import numpy as np

__all__ = ["assemble_fluid_dispersion_matrix"]


def _integer(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be an integer")
    try:
        return operator.index(value)
    except TypeError:
        raise ValueError(f"{name} must be an integer") from None


def assemble_fluid_dispersion_matrix(
    *,
    omega,
    kz,
    c2,
    epsilon0,
    wps2,
    wcs,
    vts,
    rhocs,
    sgns,
    absrhocs,
    cn_residues,
    cn_poles,
    order_lengths,
    bzj,
    czj,
    max_harmonic,
    n_species,
):
    """Return the fluid matrix ``M`` whose eigenvalues are the perpendicular wavenumbers.

    The eigenproblem solved by the caller is ``kx * X = M @ X`` for the state
    ``X = [vx_snl, vy_snl, vz_snl, Ey, Ez, By, Bz]``; the electric current components
    ``Jx, Jy, Jz`` are the sums over the ``v*_snl`` blocks. ``M`` is a dense complex
    ``(3*NSL+4, 3*NSL+4)`` matrix with ``NSL = n_species * sum(order_lengths)``.
    """

    omega = float(omega)
    kz = float(kz)
    c2 = float(c2)
    epsilon0 = float(epsilon0)
    n_species = _integer(n_species, "n_species")
    max_harmonic = _integer(max_harmonic, "max_harmonic")
    if not np.isfinite([omega, kz, c2, epsilon0]).all():
        raise ValueError("omega, kz, c2 and epsilon0 must be finite")
    if omega == 0.0:
        raise ValueError("omega must be non-zero: the assembly divides by omega")
    if c2 <= 0.0 or epsilon0 <= 0.0:
        raise ValueError("c2 and epsilon0 must be strictly positive")
    if n_species < 1:
        raise ValueError("n_species must be at least 1")
    if max_harmonic < 0:
        raise ValueError("max_harmonic must be non-negative")

    wps2 = np.asarray(wps2, dtype=complex)
    wcs = np.asarray(wcs, dtype=complex)
    vts = np.asarray(vts, dtype=complex)
    rhocs = np.asarray(rhocs, dtype=complex)
    sgns = np.asarray(sgns, dtype=complex)
    absrhocs = np.asarray(absrhocs, dtype=float)
    bzj = np.asarray(bzj, dtype=complex)
    czj = np.asarray(czj, dtype=complex)
    for name, arr in (
        ("wps2", wps2),
        ("wcs", wcs),
        ("vts", vts),
        ("rhocs", rhocs),
        ("sgns", sgns),
        ("absrhocs", absrhocs),
        ("bzj", bzj),
        ("czj", czj),
    ):
        if arr.shape != (n_species,) and name not in ("bzj", "czj"):
            raise ValueError(f"{name} must have shape (n_species,)")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} must be finite")
    if bzj.shape != czj.shape or bzj.ndim != 1 or bzj.size < 1:
        raise ValueError("bzj and czj must be one-dimensional with equal length J >= 1")
    if np.any(absrhocs <= 0.0):
        raise ValueError("absrhocs must be strictly positive")
    if np.any(wcs == 0.0):
        raise ValueError("wcs must be non-zero: the resonance denominator divides by wcs")

    residues = {
        _integer(k, "cn_residues order"): np.asarray(v, dtype=complex)
        for k, v in cn_residues.items()
    }
    poles = {
        _integer(k, "cn_poles order"): np.asarray(v, dtype=complex) for k, v in cn_poles.items()
    }
    order_lengths = {
        _integer(k, "order_lengths order"): _integer(v, "order_lengths value")
        for k, v in order_lengths.items()
    }
    required = set(range(1, max_harmonic + 2))
    if (
        not required.issubset(residues)
        or not required.issubset(poles)
        or not required.issubset(order_lengths)
    ):
        raise ValueError("coefficient tables and lengths must cover orders 1..max_harmonic+1")
    for order in required:
        if order_lengths[order] < 1:
            raise ValueError(f"order_lengths[{order}] must be positive")
        if residues[order].shape != (order_lengths[order],) or poles[order].shape != (
            order_lengths[order],
        ):
            raise ValueError(f"coefficient order {order} does not match order_lengths[{order}]")
        if not np.all(np.isfinite(residues[order])) or not np.all(np.isfinite(poles[order])):
            raise ValueError(f"coefficient order {order} must be finite")

    J = int(bzj.size)
    n_l = sum(order_lengths[order] for order in range(1, max_harmonic + 2))
    n_sl = n_species * n_l
    n_sl3 = 3 * n_sl
    size = n_sl3 + 4
    mat = np.zeros((size, size), dtype=complex)

    snl = 0
    for s in range(n_species):
        xsj = (omega - kz * vts[s] * czj) / wcs[s]
        if any(np.any(xsj**2 == n**2) for n in range(max_harmonic + 2)):
            raise ValueError("resonance denominators must be non-zero for finite M")
        for n in range(max_harmonic + 1):
            order = n + 1
            for l in range(order_lengths[order]):
                pln = poles[order][l]
                rln = residues[order][l]
                csnl = pln / absrhocs[s]

                nn = float(n)
                xsj2 = xsj**2
                ctmpxx = np.sum(bzj / pln**2 * (nn**2 * xsj / (xsj2 - nn**2)))
                ctmpxy = np.sum(
                    bzj
                    * (
                        0.5 * (nn + 1.0) ** 2 / (xsj2 - (nn + 1.0) ** 2)
                        - (nn >= 1.0) * nn**2 / (xsj2 - nn**2)
                        + (nn >= 2.0) * 0.5 * (nn - 1.0) ** 2 / (xsj2 - (nn - 1.0) ** 2)
                    )
                )
                ctmpxz = np.sum(sgns[s] / pln * bzj * czj * (nn**2 / (xsj2 - nn**2)))
                ctmpyy = np.sum(
                    bzj
                    * (
                        xsj / pln**2 * nn**2 / (xsj2 - nn**2)
                        + pln**2
                        / xsj
                        * (
                            -((nn + 1.0) ** 2) / (xsj2 - (nn + 1.0) ** 2)
                            + (nn >= 1.0) * 2.0 * nn**2 / (xsj2 - nn**2)
                            - (nn >= 2.0) * (nn - 1.0) ** 2 / (xsj2 - (nn - 1.0) ** 2)
                        )
                    )
                )
                ctmpyz = np.sum(
                    sgns[s]
                    * pln
                    * bzj
                    * czj
                    / xsj
                    * (
                        0.5 * (nn + 1.0) ** 2 / (xsj2 - (nn + 1.0) ** 2)
                        - (nn >= 1.0) * nn**2 / (xsj2 - nn**2)
                        + (nn >= 2.0) * 0.5 * (nn - 1.0) ** 2 / (xsj2 - (nn - 1.0) ** 2)
                    )
                )
                ctmpzz = np.sum(bzj * czj**2 * xsj * (1.0 + (nn >= 1.0)) / (xsj2 - nn**2))

                btmp = epsilon0 * wps2[s] / wcs[s] * rln / absrhocs[s]
                blxx = -2j * btmp * ctmpxx
                blxy = 2.0 * btmp * ctmpxy
                blyx = -blxy
                blxz = -2j * np.sqrt(2.0) * btmp * ctmpxz
                blzx = blxz
                blyy = -2j * btmp * ctmpyy
                blyz = -2.0 * np.sqrt(2.0) * btmp * ctmpyz
                blzy = -blyz
                blzz = -2j * btmp * ctmpzz

                mat[snl, snl] += csnl
                mat[n_sl + snl, n_sl + snl] += csnl
                mat[2 * n_sl + snl, 2 * n_sl + snl] += csnl

                mat[snl, n_sl3 + 0] = blxy
                mat[snl, n_sl3 + 1] = blxz
                mat[snl, n_sl3 + 2] = kz * c2 / omega * blxx
                mat[n_sl + snl, n_sl3 + 0] = blyy
                mat[n_sl + snl, n_sl3 + 1] = blyz
                mat[n_sl + snl, n_sl3 + 2] = kz * c2 / omega * blyx
                mat[2 * n_sl + snl, n_sl3 + 0] = blzy
                mat[2 * n_sl + snl, n_sl3 + 1] = blzz
                mat[2 * n_sl + snl, n_sl3 + 2] = kz * c2 / omega * blzx

                mat[snl, 0:n_sl] -= 1j / (omega * epsilon0) * blxx
                mat[n_sl + snl, 0:n_sl] -= 1j / (omega * epsilon0) * blyx
                mat[2 * n_sl + snl, 0:n_sl] -= 1j / (omega * epsilon0) * blzx

                mat[n_sl3 + 1, snl] = -1j * kz / (omega * epsilon0)
                mat[n_sl3 + 2, 2 * n_sl + snl] = -1j / (c2 * epsilon0)
                mat[n_sl3 + 3, n_sl + snl] = 1j / (c2 * epsilon0)

                snl += 1

    mat[n_sl3 + 0, n_sl3 + 3] = omega
    mat[n_sl3 + 1, n_sl3 + 2] = kz**2 * c2 / omega - omega
    mat[n_sl3 + 2, n_sl3 + 1] = -omega / c2
    mat[n_sl3 + 3, n_sl3 + 0] = omega / c2 - kz**2 / omega

    if not np.all(np.isfinite(mat)):
        raise ValueError("fluid dispersion matrix M must be finite")

    return {
        "M": mat,
        "n_sl": n_sl,
        "n_sl3": n_sl3,
        "matrix_size": size,
        "n_l": n_l,
        "nonzero_entries": int(np.count_nonzero(mat)),
        "state_layout": ["vx_snl", "vy_snl", "vz_snl", "Ey", "Ez", "By", "Bz"],
    }
