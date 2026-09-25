"""Atomic-hydrogen charge-exchange Maxwellian rate coefficient.

One leaf recovered from the saved KN1DPy ``sigmav_cx_h0`` slice (source anchor
``KN1DPy/sigma/sigmav_cx_h0.py:8-95``, ledger entry N25
``EQ-N25-N4-H-CX-RATE``), integrated as
:func:`evaluate_atomic_hydrogen_charge_exchange_rate`:

the atomic-H charge-exchange Maxwellian rate coefficient in ``m^3/s`` as a
nine-by-nine bivariate logarithmic polynomial in ``log(T)`` and ``log(E)``,
where ``T`` is the plasma temperature and ``E`` the impact energy, both in eV.

**The evaluation is the saved source's, exactly.**  Both inputs are
sequentially clipped to ``[0.1, 2.01e4] eV``, the polynomial is accumulated in
the source's summation order (energy power outer, temperature power inner,
coefficient indexed ``[temperature_power, energy_power]``), and the result is
``exp(log_rate) * 1e-6``.  The bounded fit domain keeps the polynomial small
enough that the exponential is representable for every accepted input, which
the finite-output check below makes a contract instead of an accident.

**Two repairs relative to the saved implementation, both documented.**  The
saved document declares a positive temperature and a nonnegative energy, but
its implementation silently clipped a nonpositive temperature or negative
energy into the fit domain; this module rejects them.  The rejection domain is
otherwise unchanged: same shapes, the same finite checks the saved
implementation already performed, the same clipping of in-domain values and
the same arithmetic, bit for bit.

Evidence ceiling: this module establishes the bivariate fit against an
independent ``polyval2d`` evaluation of the same coefficient table, the source
summation order by exact equality, the input and failure contracts, the two
repairs, and -- in the environment-gated replay test -- exact agreement with
the saved KN1DPy implementation on the declared domain.  The saved bundle's
strict D1 qualification has been withdrawn; that replay is historical
development evidence, not qualified-L1 provenance.  No test establishes the
fit against an external atomic-physics reference: the saved package records
that residual as ``validation_oracle_gap``.  This module is a tabulated-fit
evaluation, not a Maxwellian integral: it does not average a cross section and
is distinct from
:func:`scirel.collisions.average_cross_section_over_maxwellian`.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "evaluate_atomic_hydrogen_charge_exchange_rate",
]

_COEFFICIENTS = np.array(
    [
        [-1.829079581680e1, 1.640252721210e-1, 3.364564509137e-2, 9.530225559189e-3, -8.519413589968e-4, -1.247583860943e-3, 3.014307545716e-4, -2.499323170044e-5, 6.932627237765e-7],
        [2.169137615703e-1, -1.106722014459e-1, -1.382158680424e-3, 7.348786286628e-3, -6.343059502294e-4, -1.919569450380e-4, 4.075019351738e-5, -2.850044983009e-6, 6.966822400446e-8],
        [4.307131243894e-2, 8.948693624917e-3, -1.209480567154e-2, -3.675019470470e-4, 1.039643390686e-3, -1.553840717902e-4, 2.670827249272e-6, 7.695300597935e-7, -3.783302281524e-8],
        [-5.754895093075e-4, 6.062141761233e-3, 1.075907881928e-3, -8.119301728339e-4, 8.911036876068e-6, 3.175388949811e-5, -4.515123641755e-6, 2.187439283954e-7, -2.911233951880e-9],
        [-1.552077120204e-3, -1.210431587568e-3, 8.297212635856e-4, 1.361661816974e-4, -1.008928628425e-4, 1.080693990468e-5, 5.106059413591e-7, -1.299275586093e-7, 5.117133050290e-9],
        [-1.876800283030e-4, -4.052878751584e-5, -1.907025662962e-4, 1.141663041636e-5, 1.775681984457e-5, -3.149286923815e-6, 3.105491554749e-8, 2.274394089017e-8, -1.130988250912e-9],
        [1.125490270962e-4, 2.875900435985e-5, 1.338839628570e-5, -4.340802793033e-6, -7.003521917385e-7, 2.318308730487e-7, -6.030983538280e-9, -1.755944926274e-9, 1.005189187279e-10],
        [-1.238982763007e-5, -2.616998139678e-6, -1.171762874107e-7, 3.517971869029e-7, -4.928692832866e-8, 1.756388998863e-10, -1.446756795654e-10, 7.143183138281e-11, -3.989884105603e-12],
        [4.163596197181e-7, 7.558092849125e-8, -1.328404104165e-8, -9.170850253981e-9, 3.208853883734e-9, -3.952740758950e-10, 2.739558475782e-11, -1.693040208927e-12, 6.388219930167e-14],
    ],
    dtype=float,
)


def evaluate_atomic_hydrogen_charge_exchange_rate(temperature_ev, energy_ev):
    """Return the source atomic-H charge-exchange rate coefficient in m^3/s.

    Parameters
    ----------
    temperature_ev
        Plasma temperatures in eV, scalar or array; must be finite and
        strictly positive.  In-domain values above or below the fit range are
        clipped to ``[0.1, 2.01e4] eV``, the saved source's declared behavior.
    energy_ev
        Impact energies in eV, scalar or array with the same shape; must be
        finite and nonnegative, with the same clipping.

    Returns
    -------
    numpy.ndarray
        Rate coefficients in ``m^3/s`` with the inputs' shape.  Finite and
        strictly positive for every accepted input.

    Raises
    ------
    ValueError
        If the two inputs differ in shape, contain a non-finite value, or if
        ``temperature_ev`` contains a nonpositive value or ``energy_ev`` a
        negative value.
    """
    temperature = np.asarray(temperature_ev, dtype=float)
    energy = np.asarray(energy_ev, dtype=float)
    if temperature.shape != energy.shape:
        raise ValueError("temperature_ev and energy_ev must have the same shape")
    if not np.all(np.isfinite(temperature)) or not np.all(np.isfinite(energy)):
        raise ValueError("temperature_ev and energy_ev must be finite")
    if bool(np.any(temperature <= 0.0)):
        raise ValueError("temperature_ev must be positive")
    if bool(np.any(energy < 0.0)):
        raise ValueError("energy_ev must be nonnegative")
    clipped_temperature = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
    clipped_energy = np.minimum(np.maximum(energy, 0.1), 2.01e4)
    log_temperature = np.log(clipped_temperature)
    log_energy = np.log(clipped_energy)
    log_rate = np.zeros_like(log_energy, dtype=float)
    for energy_power in range(9):
        for temperature_power in range(9):
            log_rate = log_rate + _COEFFICIENTS[temperature_power, energy_power] * log_energy**energy_power * log_temperature**temperature_power
    return np.exp(log_rate) * 1.0e-6
