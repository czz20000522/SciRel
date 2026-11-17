"""Shared independent reference for the fluid pencil spectra and case constants.

Two kinds of independent statement live here, and they are kept apart because
they buy different things.

**Closed forms.**  The cold, drift-free, unmagnetized multifluid pencil reduces to
``omega**2 E = omega_p**2 E - c**2 k x (k x E)``.  For ``E`` parallel to ``k`` the
curl term vanishes and the branch is ``omega = +-omega_p``; for the two
transverse polarizations ``k x (k x E) = -k**2 E`` and the branch is
``omega = +-sqrt(omega_p**2 + k**2 c**2)``.  Nothing in this module reads that
relation out of the implementation: ``omega_p`` is recomputed at ``mpmath``
precision from the state's own ``n``, ``q``, ``m`` and ``epsilon0``, and the
comparison is made against eigenvalues of the assembled matrix recomputed at
higher precision than binary64.

**Why the eigenvalues are recomputed instead of taken from the caller.**  The
assembled pencil carries a ``1j*c2*k`` curl block, so ``||M||`` is ``c**2*k`` --
about ``1e14`` on the SI examples.  A binary64 backward error of ``eps*||M||``
is then about ``18 rad/s`` absolute, which is ``~1e-4`` relative at
``omega_p ~ 1.7e5``: measured, not assumed, and it is what made an earlier audit
report a constant ``2.7e-4`` Langmuir offset on a state that was in fact cold.
Recomputing the spectrum at 40-50 digits removes that floor and leaves the
matrix relation itself as the only thing under test.

What is deliberately **not** here: the BONK/PDRF deck constants (``6.0``,
``2e20``, ``4e3``, ``10.0``, ``1.0``, ``6.075e19``, ``1e3``, ``0.0``) and the
R43/R64 pole and harmonic tables.  No independent source for those survives in
the repository, so a reference that reproduced them would only be reproducing
the implementation; contracts record them as ``cannot establish``.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np

PRECISION = 50

# Fixed source constants as the fluid_spectrum module declares them.  These are
# published values, so the module can be checked against them instead of copying
# them: c is exact by the SI definition of the metre, and the other four are the
# CODATA-2014 literals.
DECLARED_C2 = (2.99792458e8) ** 2
DECLARED_EPSILON0 = 8.854187817e-12
DECLARED_KB = 1.38064852e-23
DECLARED_QE = 1.60217662e-19
DECLARED_MP = 1.6726219e-27
DECLARED_ME = 9.1094e-31
DECLARED_EV_TO_J = 1.6022e-19

# The ten-column species rows of initialize_plasma_state, cooled to cs=0 and
# stripped of drift and density gradients.  Two species at equal density keep the
# ion contribution to omega_p visible instead of making it vanish.
COLD_SI_ROWS = np.array(
    [
        [-1.602e-19, 9.109e-31, 8.7e6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [1.602e-19, 1.673e-27, 8.7e6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ],
    dtype=float,
)


def high_precision(precision: int = PRECISION) -> None:
    """Set the reference precision; ``mpmath`` precision is process-global."""
    mp.mp.dps = precision


def cold_state():
    """Return a cold SI state whose pressure, drift and field terms are exactly zero."""
    from scirel.kinetic.spectral_evolution import initialize_plasma_state

    return initialize_plasma_state(COLD_SI_ROWS, unit="si", cfg={"B0": 0.0})


def state_plasma_frequency(state) -> "mp.mpf":
    """``sqrt(sum_s n_s q_s**2 / (epsilon0 m_s))`` at high precision."""
    high_precision()
    epsilon0 = mp.mpf(float(np.asarray(state["epsilon0"]).ravel()[0]))
    total = mp.mpf(0)
    for index in range(len(state["qs"])):
        total += (
            mp.mpf(float(state["ns0"][index]))
            * mp.mpf(float(state["qs"][index])) ** 2
            / (epsilon0 * mp.mpf(float(state["ms"][index])))
        )
    return mp.sqrt(total)


def light_branch(omega_p, k, c2) -> "mp.mpf":
    """``sqrt(omega_p**2 + k**2 c**2)`` for the transverse cold-fluid branch."""
    high_precision()
    return mp.sqrt(mp.mpf(omega_p) ** 2 + mp.mpf(k) ** 2 * mp.mpf(c2))


def as_high_precision(matrix) -> "mp.matrix":
    """Lift a binary64 matrix into ``mpmath`` without changing its entries."""
    array = np.asarray(matrix, dtype=complex)
    return mp.matrix(
        [
            [
                mp.mpf(float(array[i, j].real)) + mp.mpf(float(array[i, j].imag)) * 1j
                for j in range(array.shape[1])
            ]
            for i in range(array.shape[0])
        ]
    )


def pencil_spectrum(M, A=None) -> list:
    """Eigenvalues of ``M x = lambda A x`` at high precision, sorted by decreasing modulus.

    The generalized path is not taken here: the only caller that needs it is the
    relativistic inertia case, and ``mpmath`` has no generalized eigensolver.  An
    inertia matrix that is not the identity is therefore an error rather than a
    silently wrong standard problem.
    """
    high_precision()
    matrix = as_high_precision(M)
    inertia = np.eye(np.asarray(M).shape[0]) if A is None else np.asarray(A)
    if not np.array_equal(inertia, np.eye(inertia.shape[0])):
        raise ValueError("high-precision reference only covers identity inertia")
    values = mp.eig(matrix, left=False, right=False)
    return sorted(values, key=lambda value: -abs(value))


def determinant_high_precision(matrix):
    """``det(M)`` at high precision, independent of the LAPACK/LAPACK-free caller."""
    high_precision()
    return mp.det(as_high_precision(matrix))


def eigenproduct(values):
    """``prod(values)`` at high precision."""
    high_precision()
    product = mp.mpf(1)
    for value in values:
        product *= mp.mpf(float(np.real(value))) + mp.mpf(float(np.imag(value))) * 1j
    return product


def flip_ampere_curl(matrix, species: int) -> np.ndarray:
    """Return a copy whose Ampere curl block has the opposite sign.

    Flipping **one** block is the sign mutation; flipping both is a similarity
    transformation by ``diag(1, -1)`` on the field blocks and leaves every
    eigenvalue unchanged, which is why it cannot be used as a probe.
    """
    array = np.array(matrix, dtype=complex, copy=True)
    field = 4 * species
    array[field : field + 3, field + 3 : field + 6] *= -1
    return array


def bessel_gamma(order, argument):
    """``I_order(argument) * exp(-argument)`` at high precision.

    This reproduces the fluid module's ``_gamma`` definition for the real,
    nonnegative arguments the fluid cases use, but with ``mpmath``'s Bessel
    function instead of the SciPy scaled one.
    """
    high_precision()
    return mp.besseli(int(order), mp.mpf(argument)) * mp.e**(-mp.mpf(argument))


def case_scales(ms, qs, ns_unit, Ts_unit, B0, n00, T00) -> dict:
    """Recompute every derived case scale from the declared deck inputs.

    The deck numbers themselves are inputs, not evidence: this function only
    restates the published relations ``v_t = sqrt(2 k_B T/m)``,
    ``omega_c = qB0/m``, ``omega_p**2 = n q**2/(eps0 m)``,
    ``rho = sqrt(k_B T/m)/omega_c``, ``k_n = 1/max|rho|`` and ``omega_n = min|omega_c|``.
    """
    high_precision()
    ms = np.asarray(ms, dtype=float)
    qs = np.asarray(qs, dtype=float)
    c2 = mp.mpf(DECLARED_C2)
    epsilon0 = mp.mpf(DECLARED_EPSILON0)
    kB = mp.mpf(DECLARED_KB)
    ns0 = [mp.mpf(float(factor)) * mp.mpf(float(n00)) for factor in np.asarray(ns_unit, float)]
    Ts0 = [
        mp.mpf(float(factor)) * mp.mpf(float(T00)) * mp.mpf(DECLARED_EV_TO_J) / kB
        for factor in np.asarray(Ts_unit, float)
    ]
    vts = [mp.sqrt(2 * kB * Ts0[i] / mp.mpf(float(ms[i]))) for i in range(ms.size)]
    wcs = [mp.mpf(float(qs[i])) * mp.mpf(float(B0)) / mp.mpf(float(ms[i])) for i in range(ms.size)]
    wps2 = [
        ns0[i] * mp.mpf(float(qs[i])) ** 2 / (epsilon0 * mp.mpf(float(ms[i])))
        for i in range(ms.size)
    ]
    rhocs = [mp.sqrt(kB * Ts0[i] / mp.mpf(float(ms[i]))) / wcs[i] for i in range(ms.size)]
    absrhocs = [abs(value) for value in rhocs]
    wcn = min(abs(value) for value in wcs)
    rhocn = max(absrhocs)
    return {
        "c2": c2,
        "epsilon0": epsilon0,
        "mu0": 1 / (c2 * epsilon0),
        "ns0": ns0,
        "Ts0": Ts0,
        "vts": vts,
        "wcs": wcs,
        "wps": [mp.sqrt(value) for value in wps2],
        "wps2": wps2,
        "rhocs": rhocs,
        "absrhocs": absrhocs,
        "sgns": [1 if value > 0 else -1 for value in rhocs],
        "wcn": wcn,
        "rhocn": rhocn,
        "kn": 1 / rhocn,
        "wn": wcn,
    }


def relative(measured, reference) -> float:
    """``|measured - reference| / |reference|`` as a float, zero-safe on the numerator."""
    high_precision()
    reference = mp.mpf(str(reference)) if not isinstance(reference, mp.mpf) else reference
    measured = mp.mpf(str(measured)) if not isinstance(measured, mp.mpf) else measured
    if reference == 0:
        return float(abs(measured))
    return float(abs(measured - reference) / abs(reference))
