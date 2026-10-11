"""Regular current-grid flux consumer derived from Pleiades helpers.py:183–210.

Frozen D0 be412aa14b77 sums one leading current layer, converts A/cm² to
A/m², uses full node-cell area and linearly triangulates to the EQDSK grid.
This successor keeps those conventions but evaluates each off-self pair using
the separately qualified circular-filament kernel. It does not use or repair
the unresolved irregular reflected-block implementation. Zero self-cell is a
compatibility quadrature choice, not a finite-wire self-inductance model.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import LinearNDInterpolator

from .greens import compute_greens


def get_deltapsi(data, Req, Zeq):
    """Return distributed toroidal-current flux ``psi=R*A_phi`` in Wb/rad.

    ``data`` supplies netCDF variables/dimensions. ``curr_diamcurv_phi`` has
    trailing dimensions (nzeqadim,nreqadim), optionally one additive leading
    layer dimension, and is expressed in A/cm². No temporal interpretation of
    the leading axis is asserted. Finite targets are equally shaped 2-D R,Z
    arrays in metres with nonnegative R and positive spans. The source axes
    are uniform over target extrema, with at least two nodes each. Masked or
    nonfinite currents and incompatible declared units/shapes raise ValueError.
    Input arrays/dataset are not modified. Self and zero-radius source cells
    contribute zero; no continuum or mesh-refinement accuracy is claimed.
    """
    R, Z = np.asarray(Req, dtype=float), np.asarray(Zeq, dtype=float)
    if (R.ndim != 2 or Z.shape != R.shape or R.size == 0 or
            not np.all(np.isfinite(R)) or not np.all(np.isfinite(Z)) or
            np.any(R < 0) or np.ptp(R) <= 0 or np.ptp(Z) <= 0):
        raise ValueError('finite equal 2-D targets with nonnegative R and positive R,Z spans required')
    try:
        nr = data.dimensions['nreqadim'].size
        nz = data.dimensions['nzeqadim'].size
        variable = data.variables['curr_diamcurv_phi']
    except (KeyError, AttributeError) as exc:
        raise ValueError('current variable and named source-grid dimensions required') from exc
    if nr < 2 or nz < 2:
        raise ValueError('source grid needs at least two nodes in each direction')
    values = np.ma.asarray(variable[:], dtype=float)
    if (values.ndim not in (2, 3) or values.shape[-2:] != (nz, nr) or
            tuple(variable.dimensions[-2:]) != ('nzeqadim', 'nreqadim') or
            np.any(np.ma.getmaskarray(values)) or not np.all(np.isfinite(values.data))):
        raise ValueError('finite unmasked current with trailing (nzeqadim,nreqadim) dimensions required')
    if getattr(variable, 'units', 'A/cm^2') != 'A/cm^2':
        raise ValueError('current must be expressed in A/cm^2')
    current = np.array(values.data, copy=True)
    if current.ndim == 3:
        current = current.sum(axis=0)
    r, z = np.linspace(R.min(), R.max(), nr), np.linspace(Z.min(), Z.max(), nz)
    rr, zz = np.meshgrid(r, z)
    points = np.column_stack((rr.ravel(), zz.ravel()))
    with np.errstate(over='raise', invalid='raise'):
        amperes = current.ravel() * 1e4 * (r[1]-r[0]) * (z[1]-z[0])
        flux = np.zeros(len(points))
        for index, ((a, h), weight) in enumerate(zip(points, amperes)):
            if a == 0 or weight == 0:
                continue
            off_self = np.arange(len(points)) != index
            flux[off_self] += compute_greens(np.array([[a, h, weight]]), points[off_self])[0]
    if not np.all(np.isfinite(flux)):
        raise FloatingPointError('distributed flux is not finite')
    targets = np.column_stack((R.ravel(), Z.ravel()))
    result = np.asarray(LinearNDInterpolator(points, flux)(targets))
    # Preserve nodal values exactly: triangulation roundoff must not create a
    # spurious self response at an exactly equal source coordinate.
    # linspace may represent e.g. the interior decimal 0.1 differently from
    # the supplied target. Match only within a float64 construction error,
    # bounded relative to axis scale and capped below half the cell spacing.
    eps = np.finfo(float).eps
    r_bound = min(4*eps*max(np.max(np.abs(r)), np.ptp(r)), (r[1]-r[0])/4)
    z_bound = min(4*eps*max(np.max(np.abs(z)), np.ptp(z)), (z[1]-z[0])/4)
    for i, (a, h) in enumerate(targets):
        ir, iz = np.argmin(np.abs(r-a)), np.argmin(np.abs(z-h))
        if abs(r[ir]-a) <= r_bound and abs(z[iz]-h) <= z_bound:
            result[i] = flux[iz*nr+ir]
    if not np.all(np.isfinite(result)):
        raise FloatingPointError('interpolated flux is not finite')
    return result.reshape(R.shape)


__all__ = ['get_deltapsi']
