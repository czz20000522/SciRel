"""KN1DPy Janev Maxwellian electron-impact ionization-rate fits.

One leaf recovered from the saved KN1DPy ``sigmav_ion_h0``/``sigmav_ion_hh``
slice (source anchor ``KN1DPy/sigma/sigmav_ion_h0.py:1-22`` with
``KN1DPy/sigma/sigmav_ion_hh.py:1-27`` and the shared polynomial evaluation
``KN1DPy/sigma/poly.py:1-10``), integrated as
:func:`evaluate_janev_electron_impact_ionization_rate`:

the Maxwellian electron-impact ionization rate coefficient in ``m^3/s`` for
two target species -- H and H2 -- each as a temperature-only nine-coefficient
logarithmic polynomial, evaluated with ``polyval`` on the clipped domain
``[0.1, 2.01e4] eV`` and scaled by ``1e-6``.

**The saved source's species dispatch is kept as the declared contract.**  The
``target_species`` selector takes exactly the declared enum values ``"H"`` and
``"H2"``; the two coefficient tables are different fits of different physical
systems, and any other value is rejected.

**One repair relative to the saved implementation, documented.**  The saved
document declares a positive temperature, but its implementation folded the
temperature and species checks into one generic error and silently clipped a
nonpositive temperature into the fit domain; this module rejects a nonpositive
temperature with a message naming the quantity.  The rejection domain is
otherwise unchanged and both species' arithmetic is preserved bit for bit on
the declared domain.

Evidence ceiling: this module establishes both species' fits against
independent ``polyval`` evaluations of the same coefficient tables, the
endpoint clipping, the species distinction, the input and failure contracts,
the repair, and -- in the environment-gated replay test -- exact agreement
with the saved KN1DPy implementation on the declared domain.  The saved
bundle's strict D1 qualification has been withdrawn; that replay is historical
development evidence, not qualified-L1 provenance.  No test establishes either
fit against an external atomic-physics reference: the saved package records
that residual as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "evaluate_janev_electron_impact_ionization_rate",
]

_COEFFICIENTS = {
    "H": np.array([-3.271396786375e1, 1.353655609057e1, -5.739328757388, 1.563154982022, -2.877056004391e-1, 3.482559773737e-2, -2.631976175590e-3, 1.119543953861e-4, -2.039149852002e-6]),
    "H2": np.array([-3.568640293666e1, 1.733468989961e1, -7.767469363538, 2.211579405415, -4.169840174384e-1, 5.088289820867e-2, -3.832737518325e-3, 1.612863120371e-4, -2.893391904431e-6]),
}


def evaluate_janev_electron_impact_ionization_rate(electron_temperature_ev, target_species):
    """Return the source Maxwellian ionization rate coefficient in m^3/s.

    Parameters
    ----------
    electron_temperature_ev
        Electron temperatures in eV, scalar or array; must be finite and
        strictly positive.  In-domain values above or below the fit range are
        clipped to ``[0.1, 2.01e4] eV``, the saved source's declared behavior.
    target_species
        The declared species enum: ``"H"`` or ``"H2"``.  Each selects its own
        frozen coefficient table; any other value is rejected.

    Returns
    -------
    numpy.ndarray
        Rate coefficients in ``m^3/s`` with the temperature input's shape.
        Finite and strictly positive for every accepted input.

    Raises
    ------
    ValueError
        If ``electron_temperature_ev`` contains a non-finite or nonpositive
        value, or if ``target_species`` is not one of the declared values.
    """
    temperature = np.asarray(electron_temperature_ev, dtype=float)
    if target_species not in _COEFFICIENTS:
        raise ValueError("target_species must be H or H2")
    if not np.all(np.isfinite(temperature)):
        raise ValueError("electron_temperature_ev must be finite")
    if bool(np.any(temperature <= 0.0)):
        raise ValueError("electron_temperature_ev must be positive")
    clipped = np.clip(temperature, 0.1, 2.01e4)
    return np.exp(np.polynomial.polynomial.polyval(np.log(clipped), _COEFFICIENTS[target_species])) * 1.0e-6
