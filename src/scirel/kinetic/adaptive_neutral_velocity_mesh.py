"""Source-specific normalized cylindrical velocity mesh for neutral species.

One leaf recovered from the saved the neutral-transport formulation ``自适应中性粒子速度网格`` package, integrated as
:func:`create_adaptive_neutral_velocity_mesh`:

the source-equivalent symmetric cylindrical velocity mesh ``(vx, vr)`` built
from the species' ion temperatures and requested discharge energies: a
uniform base mesh ending at ``vmax = 3.5`` when the temperature spread is
small, otherwise the saved nonuniform quadratic stretching; requested
positive energies are inserted as exact mesh nodes (axial symmetry preserved),
including energies excluded from the capped normalization population; the normalization
temperature ``Tnorm`` is the mean of the selected population and the
requested-energy index positions are returned.

The saved finite real-valued calculation and single-index-or-array return
form are retained. This integration rejects non-real coercions, non-finite
requested energies or cap, and repeated or existing-node insertions that
would make the final radial mesh non-strictly increasing. The latter meshes
cannot feed SciRel's cylindrical quadrature; the saved arm returns them.

Evidence ceiling: direct tests establish the mesh against the saved source
formula (uniform 3.5 base mesh, quadratic stretching, exact energy-node
insertion, axial symmetry), with a separate bounded read-only comparison
against the saved the neutral-transport formulation implementation. The saved
bundle's strict D1 qualification has been withdrawn; that replay is
historical development evidence, not qualified-L1 provenance.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "create_adaptive_neutral_velocity_mesh",
]


def _real_array(name, value):
    try:
        if isinstance(value, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real-valued numeric values") from exc


def _real_scalar(name, value):
    raw = _real_array(name, value)
    if raw.ndim != 0:
        raise ValueError(f"{name} must be a real numeric scalar")
    return float(raw)


def _insert_energy_nodes(base, requested, normalization):
    """Insert positive requested energies in caller order, preserving nodes."""
    mesh = base
    last = 0.0
    for energy in requested:
        if energy <= 0.0:
            continue
        last = np.sqrt(energy / normalization)
        insertion = np.searchsorted(mesh, last, side="right")
        mesh = np.insert(mesh, insertion, last)
    return mesh, last


def create_adaptive_neutral_velocity_mesh(
    nv, ion_temperature_ev, requested_energy_ev=None, temperature_cap_ev=0.0
):
    """Return the source-equivalent ``vx``/``vr`` mesh, ``Tnorm`` and indices.

    Parameters
    ----------
    nv : int
        Positive integer base node count.
    ion_temperature_ev : array_like
        The species' ion temperatures [eV]: a nonempty finite positive
        one-dimensional array.
    requested_energy_ev : array_like, optional
        Optional finite one-dimensional discharge energies [eV]; positive
        entries are inserted as exact mesh nodes even when the cap excludes
        them from the normalization population. ``None`` means no requests.
    temperature_cap_ev : real scalar, optional
        Optional finite nonnegative scalar cap [eV]: temperatures/energies at or
        above the cap are dropped from the normalization population
        (``0.0`` disables the cap).

    Returns
    -------
    mesh : tuple
        ``(vx, vr, tnorm, ix, ir)`` [mixed], with normalized speed axes
        ``vx`` and ``vr`` [v/vth], normalization temperature ``tnorm`` [eV]
        (mean of the selected population), and the last positive requested
        energy's zero-based index positions. Indices are arrays unless there
        is exactly one match, in which case a scalar index is returned.

    Raises
    ------
    ValueError
        If the declared input contract is violated or inserted nodes make
        the final radial mesh non-finite or non-strictly increasing.

    See Also
    --------
    make_cylindrical_velocity_quadrature : Build measures from the returned axes.

    Notes
    -----
    The base mesh ends at 3.5 and is uniform if ``Tmax-Tmin <= 0.1*Tmax``;
    otherwise it uses quadratic stretching. The cap filters the population
    used for normalization and stretching. Every positive requested energy
    is then inserted, including entries above the cap, so the final mesh can
    exceed 3.5. Boolean, string and complex inputs are not coerced to real data.

    References
    ----------
    The base-mesh and insertion formulas are given in Notes and implemented
    directly in this operator.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import create_adaptive_neutral_velocity_mesh
    >>> vx, vr, tnorm, ix, ir = create_adaptive_neutral_velocity_mesh(4, (1.0, 1.05))
    >>> assert np.array_equal(vr, (0.875, 1.75, 2.625, 3.5))
    >>> assert np.array_equal(vx, -vx[::-1])
    >>> assert tnorm == 1.025
    >>> vx2, vr2, tnorm2, ix2, ir2 = create_adaptive_neutral_velocity_mesh(4, (1.0, 9.0), temperature_cap_ev=4.0)
    >>> assert tnorm2 == 1.0
    >>> try:
    ...     create_adaptive_neutral_velocity_mesh(0, (1.0,))
    ... except ValueError as error:
    ...     assert 'nv must be a positive integer' in str(error)
    ... else:
    ...     raise AssertionError('nv=0 must be rejected')
    """
    temperature = _real_array("ion_temperature_ev", ion_temperature_ev)
    if requested_energy_ev is None:
        requested_energy_ev = ()
    requested = _real_array("requested_energy_ev", requested_energy_ev)
    cap = _real_scalar("temperature_cap_ev", temperature_cap_ev)
    # Declared r61 pre-review tightenings: the saved arm accepts fractional
    # nv (building a fractional-count mesh) and non-finite temperatures
    # (returning an all-NaN mesh); the exact document requires a positive
    # integer nv, finite temperatures and a finite result, so this asset
    # fail-closes on all three.  The saved-arm divergences are pinned by
    # regression tests.
    if isinstance(nv, bool) or not isinstance(nv, (int, np.integer)) or nv < 1:
        raise ValueError("nv must be a positive integer")
    if (
        temperature.ndim != 1
        or temperature.size == 0
        or not np.all(np.isfinite(temperature))
        or np.any(temperature <= 0.0)
        or cap < 0.0
    ):
        raise ValueError(
            "nv must be positive; temperatures positive and one-dimensional; cap nonnegative"
        )
    if requested.ndim != 1 or not np.all(np.isfinite(requested)):
        raise ValueError("requested_energy_ev must be a finite one-dimensional array")
    if not np.isfinite(cap):
        raise ValueError("temperature_cap_ev must be finite and nonnegative")
    selected = np.concatenate((temperature, requested[requested > 0.0]))
    if cap > 0.0:
        selected = selected[selected < cap]
    if selected.size == 0 or np.any(selected <= 0.0):
        raise ValueError("selected temperature/energy population must be nonempty and positive")
    maximum, minimum, tnorm, vmax = selected.max(), selected.min(), selected.mean(), 3.5
    if not np.isfinite(tnorm) or tnorm <= 0.0:
        raise ValueError("mesh normalization temperature must be finite and positive")
    if maximum - minimum <= 0.1 * maximum:
        v = np.arange(nv + 1, dtype=float) * vmax / nv
    else:
        ratio = np.sqrt(minimum / maximum)
        g = 2.0 * nv * ratio / (1.0 - ratio)
        b = vmax / (nv * (nv + g))
        v = g * b * np.arange(nv + 1) + b * np.arange(nv + 1) ** 2
    v, v0 = _insert_energy_nodes(v, requested, tnorm)
    if not np.all(np.isfinite(v)) or np.any(np.diff(v) <= 0.0):
        raise ValueError("final radial mesh must be finite and strictly increasing")
    vr = v[1:]
    vx = np.concatenate((-vr[::-1], vr))
    ix, ir = np.flatnonzero(np.abs(vx) == v0), np.flatnonzero(vr == v0)
    return vx, vr, float(tnorm), (ix[0] if ix.size == 1 else ix), (ir[0] if ir.size == 1 else ir)
