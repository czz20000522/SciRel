"""Molecular-hydrogen charge-exchange Maxwellian rate coefficient.

One leaf recovered from the saved KN1DPy ``sigmav_cx_hh`` slice (source anchor
``KN1DPy/sigma/sigmav_cx_hh.py:5-95``, ledger entry N15
``EQ-N15-H2-CX-RATE``; direct caller ``KN1DPy/kinetic_h2.py:1196-1206`` and
mesh evidence ``KN1DPy/kinetic_mesh.py:137``), integrated as
:func:`evaluate_hydrogen2_charge_exchange_rate`:

the H2 charge-exchange Maxwellian rate coefficient in ``m^3/s`` as a
nine-by-nine bivariate logarithmic polynomial in ``log(T)`` and ``log(E)``,
where ``T`` is the plasma temperature and ``E`` the impact energy, both in eV.

**The evaluation is the saved source's, exactly.**  Both inputs are
sequentially clipped to ``[0.1, 2.01e4] eV``, the polynomial is accumulated in
the source's summation order (energy power outer, temperature power inner,
coefficient indexed ``[temperature_power, energy_power]``), and the result is
``exp(log_rate) * 1e-6``.  The bounded fit domain keeps the polynomial small
enough that the exponential is representable for every accepted input.

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
    "evaluate_hydrogen2_charge_exchange_rate",
]

_COEFFICIENTS = np.array(
    [
        [-2.013143517466e01, 1.875197914224e-01, 6.865479604288e-02, 6.246595384100e-03, -5.017891372102e-03, -3.907644829287e-04, 2.786239030986e-04, -2.942576591004e-05, 9.352275354690e-07],
        [2.643458086299e-01, -1.177247941077e-01, -6.758032286178e-03, 8.585003721992e-03, -3.261863407467e-04, -3.322528542186e-04, 6.015471216449e-05, -4.039435357369e-06, 9.730479674748e-08],
        [7.295645990688e-02, 6.053418575149e-03, -1.068656224307e-02, -9.371235639464e-04, 9.735708783528e-04, -9.933049259228e-05, -6.786246802840e-06, 1.438327767305e-06, -5.530742535057e-08],
        [-1.022454343675e-02, 7.350954380641e-03, 6.814213275702e-04, -8.156435157073e-04, 2.903991825737e-05, 3.223596225946e-05, -5.199055182831e-06, 2.852443990256e-07, -4.825480212106e-09],
        [-4.801198168030e-03, -1.111612877392e-03, 8.373319888351e-04, 1.392977576749e-04, -9.316910697276e-05, 8.814981236658e-06, 6.675626166047e-07, -1.325441927019e-07, 5.012529587757e-09],
        [1.141613586234e-03, -1.371389288760e-04, -1.733761953296e-04, 1.602610140599e-05, 1.464235749797e-05, -2.944711701791e-06, 6.365231650682e-08, 1.872976659964e-08, -1.014883015867e-09],
        [-3.388853048483e-05, 4.426148343648e-05, 9.992317920676e-06, -5.333970870280e-06, -2.999105886511e-07, 2.275612517364e-07, -1.173422836715e-08, -1.364602870139e-09, 9.566404348683e-11],
        [-6.418225985394e-06, -3.652063962019e-06, 1.351312819077e-07, 4.285396408056e-07, -7.184302986068e-08, -3.265552364687e-10, 1.585228996542e-10, 6.431866226702e-11, -4.507074278992e-12],
        [3.555592819527e-07, 1.012701361110e-07, -1.993091213299e-08, -1.131561847140e-08, 3.678869095972e-09, -3.639982258214e-10, 2.056662091085e-11, -1.804254277469e-12, 9.042973335167e-14],
    ],
    dtype=float,
)


def evaluate_hydrogen2_charge_exchange_rate(temperature_ev, energy_ev):
    """Return the source H2 charge-exchange rate coefficient in m^3/s.

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
