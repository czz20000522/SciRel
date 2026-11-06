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
    r"""Assemble the dense fluid wavevector matrix from species and pole data.

    Parameters
    ----------
    omega : real numeric
        Fixed angular frequency entering the resonance denominators and the Maxwell curl
        term Shape: scalar. Constraints: Finite and nonzero. Units: [rad/s].
    kz : real numeric
        Parallel wavenumber entering the parallel resonance and curl term Shape: scalar.
        Constraints: Finite; either sign, and the kx roots are the same for +kz and -kz.
        Units: [1/m].
    c2 : real numeric
        Speed of light squared in vacuum Shape: scalar. Constraints: Finite and strictly
        positive. Units: [m^2/s^2].
    epsilon0 : real numeric
        Vacuum permittivity Shape: scalar. Constraints: Finite and strictly positive.
        Units: [F/m].
    wps2 : real numeric
        Plasma-frequency squared of each species Shape: `(S,)` one-dimensional species
        axis. Constraints: Finite. Units: [rad^2/s^2].
    wcs : real numeric
        Signed cyclotron frequency of each species Shape: `(S,)`. Constraints: Finite
        and nonzero. Units: [rad/s].
    vts : real numeric
        Thermal speed of each species Shape: `(S,)`. Constraints: Finite. Units: [m/s].
    rhocs : real numeric
        Signed gyroradius of each species Shape: `(S,)`. Constraints: Finite. Units:
        [m].
    sgns : real numeric
        Gyroradius sign Shape: `(S,)`. Constraints: Takes values `±1`. Units:
        [dimensionless].
    absrhocs : real numeric
        Absolute gyroradius Shape: `(S,)`. Constraints: Finite and strictly positive.
        Units: [m].
    cn_residues : complex128
        L-pole residue table indexed by coefficient order 1..`max_harmonic+1` Shape:
        Mapping whose values are complex arrays. Constraints: Covers every required
        order and is finite. Units: [dimensionless].
    cn_poles : complex128
        L-pole location table indexed like `cn_residues` Shape: Mapping whose values are
        complex arrays. Constraints: Covers every required order and is finite. Units:
        [dimensionless].
    order_lengths : mapping
        Number of poles at each order Shape: Mapping. Constraints: Array lengths match
        `cn_residues`/`cn_poles`. Units: [dimensionless].
    bzj : complex128
        Residues of the Z-pole approximation Shape: `(J,)` one-dimensional pole axis.
        Constraints: Finite and nonempty. Units: [dimensionless].
    czj : complex128
        Pole locations of the Z-pole approximation Shape: `(J,)`, the same length as
        `bzj`. Constraints: Finite. Units: [dimensionless].
    max_harmonic : integer
        Maximum Bessel harmonic order $N$ Shape: integer scalar. Constraints:
        Nonnegative integer. Units: [dimensionless].
    n_species : integer
        Number of species $S$ Shape: integer scalar. Constraints: At least 1. Units:
        [dimensionless].

    Returns
    -------
    M : complex128
        Eigenmatrix to solve Shape: `(3*NSL+4, 3*NSL+4)` complex square matrix,
        `NSL=n_species*sum(order_lengths)`. Constraints: Finite complex numbers. Units:
        [Mixed dimensions (each block normalized to its own physical quantity)].
    n_sl : integer
        Velocity-expansion dimension of each species $\sum_l L(l)$ Shape: integer
        scalar. Constraints: Positive integer. Units: [dimensionless].
    n_sl3 : integer
        Total dimension of the three velocity-component blocks $3\,NSL$ Shape: integer
        scalar. Constraints: Positive integer. Units: [dimensionless].
    matrix_size : integer
        Matrix order $3\,NSL+4$ Shape: integer scalar. Constraints: Matches the number
        of rows of `M`. Units: [dimensionless].
    n_l : integer
        Total number of poles per species over all harmonics Shape: integer scalar.
        Constraints: Positive integer. Units: [dimensionless].
    nonzero_entries : integer
        Number of nonzero matrix entries, for structural checks Shape: integer scalar.
        Constraints: At most the total number of matrix entries. Units: [dimensionless].
    state_layout : string
        State-vector block order Shape: String list of length 7. Constraints: Fixed to
        `vx_snl, vy_snl, vz_snl, Ey, Ez, By, Bz`. Units: [not applicable].

    Raises
    ------
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    derive_species_equilibrium_scales
        Related kinetic amplitude or dispersion operator in the same workflow.
    get_gamma_lpole_coefficients
        Related kinetic amplitude or dispersion operator in the same workflow.
    get_z_pole_coefficients
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_wavevector_eigenproblem
        Related kinetic amplitude or dispersion operator in the same workflow.
    scan_fluid_wavevectors
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The matrix acts on the declared velocity, electric-field and magnetic-field
        block layout. Its eigenvalues are perpendicular wavenumbers, and the rational
        plasma-response tables are kept separate from the matrix state. Supported scope:
        Assemble the dense first-order fluid eigenmatrix for fixed angular frequency and
        parallel wavenumber. Excluded scope: No mode identity or arbitrary-parameter
        accuracy is inferred beyond the declared numerical method.

    Examples
    --------
    >>> from scirel.kinetic import derive_species_equilibrium_scales, get_gamma_lpole_coefficients, get_z_pole_coefficients
    >>> from scirel.kinetic import assemble_fluid_dispersion_matrix
    >>> s=derive_species_equilibrium_scales(ms=[9.1094e-31],qs=[-1.60217662e-19],ns_unit=[1],Ts_unit=[1],B0=1,n00=6.075e19,T00=1000); l=get_gamma_lpole_coefficients(max_harmonic=0); z=get_z_pole_coefficients(j_order=8); r=assemble_fluid_dispersion_matrix(omega=s['wn'],kz=0.1*s['kn'],c2=s['c2'],epsilon0=s['epsilon0'],wps2=s['wps2'],wcs=s['wcs'],vts=s['vts'],rhocs=s['rhocs'],sgns=s['sgns'],absrhocs=s['absrhocs'],cn_residues=l['residues'],cn_poles=l['poles'],order_lengths=l['order_lengths'],bzj=z['bzj'],czj=z['czj'],max_harmonic=0,n_species=1); assert r['M'].shape==(40,40)
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

    n_l = sum(order_lengths[order] for order in range(1, max_harmonic + 2))
    n_sl = n_species * n_l
    n_sl3 = 3 * n_sl
    size = n_sl3 + 4
    mat = np.zeros((size, size), dtype=complex)

    # The rational fit of Z holds for Im(zeta) > 0 only, so the poles must stay below the
    # omega axis for either sign of kz. Using |kz| here and flipping the kz-odd elements is
    # the same as mapping v_par -> -v_par in the velocity integral.
    czj = -czj if kz < 0.0 else czj
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
