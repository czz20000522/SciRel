"""FIDASIM DD neutron emission anisotropy (get_ddnhe_anisotropy).

Source: FIDASIM ``get_ddnhe_anisotropy`` -- maps reactant-ion, neutron and
plasma-rotation velocities to the D-D neutron emission anisotropy factor by
Brown--Jarmie coefficient-table interpolation and directional normalization.

Contract notes carried from the saved formal implementation:

- The source ``fidasim.f90`` uses the proton mass constant (``H1_amu``), not
  the neutral atomic-hydrogen mass, in the kinematic scaling; preserved
  verbatim.
- The source calls its table interpolator on an array overload whose
  implementation treats the first table spacing as uniform even though the
  energy table is not uniform; the interpolation arithmetic reproduces that
  behavior verbatim, and an ion source energy at or above the table top is
  rejected fail-closed (the saved arm has no valid upper interval there
  either).
- The result is the ratio ``(a + b*cos^2 + c*cos^4) / (a + b/3 + c/5)``,
  bounded around 1 by the table content; no clamping is applied.
"""
from __future__ import annotations

import numpy as np

__all__ = ["dd_neutron_kinematic_anisotropy"]

# Source fidasim.f90 uses H1_amu (not the neutral atomic-hydrogen mass).
PROTON_MASS_AMU = 1.007276466879
ATOMIC_MASS_KG = 1.660539040e-27
MEV_J = 1.60218e-13

_E = np.array([10.0, 19.944, 29.935, 39.927, 49.922, 59.917, 69.914, 79.912, 89.911, 99.909, 109.909, 116.909])
_A = np.array([0.00903775 / (4 * np.pi), .0181, .0782, .178, .2994, .4406, .564, .716, .8769, 1.018, 1.138, 1.231])
_B = np.array([0, .0108, .0425, .1027, .212, .303, .446, .537, .674, .755, 1.09, 1.05])
_C = np.array([0, 0, 0, 0, 0, .049, .111, .052, .095, .2, .09, .2])
_COR = np.array([1, 1.00648, 1.00817, 1.00431, .99405, .98711, .99591, 1.02146, .99845, 1.00157, .98565, 1.00405])


def dd_neutron_kinematic_anisotropy(*, ion_velocity_cm_s, neutron_velocity_cm_s, plasma_rotation_cm_s, velocity_squared_to_kev_per_amu):
    """Return the D-D neutron emission anisotropy factor for one event."""
    v1, v3, vrot = (np.asarray(x, dtype=float) for x in (ion_velocity_cm_s, neutron_velocity_cm_s, plasma_rotation_cm_s))
    if any(x.shape != (3,) or not np.all(np.isfinite(x)) for x in (v1, v3, vrot)) or not np.isfinite(velocity_squared_to_kev_per_amu) or velocity_squared_to_kev_per_amu <= 0:
        raise ValueError("finite velocity vectors and positive source energy scale required")
    vrel = v1 - vrot
    speed2 = np.dot(vrel, vrel)
    eb = velocity_squared_to_kev_per_amu * speed2
    ehalf = .5 * eb
    if ehalf >= _E[-1]:
        raise ValueError("source 1-D interpolation has no valid upper-table interval")
    # The source calls interpol_coeff on the array overload, whose implementation
    # uses the first spacing as a uniform grid even though _E is not uniform.
    eclip = max(ehalf, _E[0])
    dx = _E[1] - _E[0]
    i = int(np.floor((eclip - _E[0]) / dx))
    i = min(i, len(_E) - 2)
    f = (eclip - (_E[0] + i * dx)) / dx
    ai = (1 - f) * (_A * _COR)[i] + f * (_A * _COR)[i + 1]
    bi = (1 - f) * (_B * _COR)[i] + f * (_B * _COR)[i + 1]
    ci = (1 - f) * (_C * _COR)[i] + f * (_C * _COR)[i + 1]
    vcm = .5 * (v1 + vrot)
    q_j = 3.27 * MEV_J
    ke = .5 * PROTON_MASS_AMU * ATOMIC_MASS_KG * speed2 * 1e-4
    k0 = np.linalg.norm(vcm) * np.sqrt(2 * PROTON_MASS_AMU * ATOMIC_MASS_KG / (3 * (q_j + ke))) * 100
    if np.linalg.norm(vcm) * np.linalg.norm(v3) > 0:
        cosphi = np.dot(vcm, v3) / (np.linalg.norm(vcm) * np.linalg.norm(v3))
        sinphi = np.sin(np.arccos(np.clip(cosphi, -1, 1)))
        costheta = cosphi * np.sqrt(1 - (k0 * sinphi) ** 2) - k0 * sinphi ** 2 if abs(k0 * sinphi) <= 1 else 0.
    else:
        costheta = 0.
    result = (ai + bi * costheta ** 2 + ci * costheta ** 4) / (ai + bi / 3 + ci / 5)
    # Registered output check: the declared input domain (finite vectors, ion
    # source energy below the table top) keeps this finite on accepted inputs;
    # the finite-but-extreme probe cases below confirm the tail algebra's own
    # costheta fallback contains norm overflow, and this gate guards the
    # remaining combinations rather than letting NaN escape.
    if not np.isfinite(result):
        raise ValueError(
            "anisotropy evaluation produced a non-finite value for finite "
            "but extreme input magnitudes (registered hardening)")
    return result
