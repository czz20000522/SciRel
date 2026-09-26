"""Source-specific normalized cylindrical velocity mesh for neutral species.

One leaf recovered from the saved KN1DPy ``自适应中性粒子速度网格`` package
(source anchor ``KN1DPy/create_vr_vx_mesh.py:16-56`` -- ``create_vr_vx_mesh``,
as recorded by the saved bundle's own provenance), integrated as
:func:`create_adaptive_neutral_velocity_mesh`:

the source-equivalent symmetric cylindrical velocity mesh ``(vx, vr)`` built
from the species' ion temperatures and requested discharge energies: a
uniform ``vmax = 3.5`` mesh when the temperature spread is small, otherwise
the saved nonuniform quadratic stretching; requested positive energies are
inserted as exact mesh nodes (axial symmetry preserved); the normalization
temperature ``Tnorm`` is the mean of the selected population and the
requested-energy index positions are returned.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (positive ``nv``, nonempty positive one-dimensional
temperatures, nonnegative cap, nonempty positive selected population) and is
reproduced bit for bit, messages included.  Returned index positions are the
saved single-index-or-array form.

Evidence ceiling: this module establishes the mesh against the saved source
formula (uniform 3.5 truncation, quadratic stretching, exact energy-node
insertion, axial symmetry), and -- in the environment-gated replay test --
bit-identical agreement with the saved KN1DPy implementation.  The saved
bundle's strict D1 qualification has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "create_adaptive_neutral_velocity_mesh",
]


def create_adaptive_neutral_velocity_mesh(nv, ion_temperature_ev, requested_energy_ev=None, temperature_cap_ev=0.0):
    """Return the source-equivalent ``vx``/``vr`` mesh, ``Tnorm`` and indices.

    Parameters
    ----------
    nv
        Positive integer base node count.
    ion_temperature_ev
        The species' ion temperatures in eV: a nonempty positive
        one-dimensional array.
    requested_energy_ev
        Optional requested discharge energies in eV; positive entries are
        inserted as exact mesh nodes.
    temperature_cap_ev
        Optional cap: selected temperatures/energies at or above the cap are
        dropped (``0.0`` disables the cap).

    Returns
    -------
    tuple
        ``(vx, vr, tnorm, ix, ir)`` with the symmetric axial mesh, the radial
        mesh, the normalization temperature (mean of the selected
        population), and the requested-energy index positions.

    Raises
    ------
    ValueError
        If ``nv`` is not positive, temperatures are not nonempty/positive/
        one-dimensional, the cap is negative, or the selected population is
        empty or nonpositive.
    """
    temperature = np.asarray(ion_temperature_ev, dtype=float)
    if requested_energy_ev is None:
        requested_energy_ev = ()
    requested = np.asarray(requested_energy_ev, dtype=float)
    if nv < 1 or temperature.ndim != 1 or temperature.size == 0 or np.any(temperature <= 0.0) or temperature_cap_ev < 0.0:
        raise ValueError("nv must be positive; temperatures positive and one-dimensional; cap nonnegative")
    selected = np.concatenate((temperature, requested[requested > 0.0]))
    if temperature_cap_ev > 0.0:
        selected = selected[selected < temperature_cap_ev]
    if selected.size == 0 or np.any(selected <= 0.0):
        raise ValueError("selected temperature/energy population must be nonempty and positive")
    maximum, minimum, tnorm, vmax = selected.max(), selected.min(), selected.mean(), 3.5
    if maximum - minimum <= 0.1 * maximum:
        v = np.arange(nv + 1, dtype=float) * vmax / nv
    else:
        ratio = np.sqrt(minimum / maximum)
        g = 2.0 * nv * ratio / (1.0 - ratio)
        b = vmax / (nv * (nv + g))
        v = g * b * np.arange(nv + 1) + b * np.arange(nv + 1) ** 2
    v0 = 0.0
    for energy in requested:
        if energy > 0.0:
            target = np.sqrt(energy / tnorm)
            v0 = target
            index = np.flatnonzero(v > target)
            v = np.concatenate((v[:index[0]], (target,), v[index[0]:])) if index.size else np.concatenate((v, (target,)))
    vr = v[1:]
    vx = np.concatenate((-vr[::-1], vr))
    ix, ir = np.flatnonzero(np.abs(vx) == v0), np.flatnonzero(vr == v0)
    return vx, vr, float(tnorm), (ix[0] if ix.size == 1 else ix), (ir[0] if ir.size == 1 else ir)
