"""Shared SI cylindrical discretization for the anisotropic solver family.

These are numerical kernels, not additional physical closures. Arrays use
[Z,R]; psi is R*A_phi (Wb/rad) and filament current is J_phi*dR*dZ (A).
"""
import numpy as np
from scirel._numerics import stable_gradient


def gradient_roundoff(values, coordinates, axis):
    """Conservative 64-epsilon tensor/stencil evaluation envelope, in value/m.

    The stencil coefficient 1-norm propagates local value uncertainty. The
    operation allowance covers tensor construction, subtraction, division and
    summation; it does not estimate truncation error or input measurement error.
    """
    f = np.moveaxis(np.abs(np.asarray(values, dtype=float)), axis, -1)
    h = np.abs(np.diff(coordinates))
    result = np.empty_like(f)
    a = h[1:] / (h[:-1] * (h[:-1] + h[1:]))
    c = h[:-1] / (h[1:] * (h[:-1] + h[1:]))
    result[..., 1:-1] = a * f[..., :-2] + (a + c) * f[..., 1:-1] + c * f[..., 2:]
    a = (2*h[0]+h[1])/(h[0]*(h[0]+h[1]))
    b = (h[0]+h[1])/(h[0]*h[1])
    c = h[0]/(h[1]*(h[0]+h[1]))
    result[..., 0] = a*f[..., 0]+b*f[..., 1]+c*f[..., 2]
    a = h[-1]/(h[-2]*(h[-2]+h[-1]))
    b = (h[-2]+h[-1])/(h[-2]*h[-1])
    c = (h[-2]+2*h[-1])/(h[-1]*(h[-2]+h[-1]))
    result[..., -1] = a*f[..., -3]+b*f[..., -2]+c*f[..., -1]
    return np.moveaxis(result * (64*np.finfo(float).eps), -1, axis)


def pressure_divergence(R, Z, br, bz, parallel, perpendicular):
    """div(P) for a smooth axisymmetric purely poloidal gyrotropic tensor."""
    r, z = R[0], Z[:, 0]
    B = np.hypot(br, bz)
    inv = np.divide(1., B, out=np.zeros_like(B), where=B>np.finfo(float).tiny)
    ur, uz = br*inv, bz*inv
    delta = parallel-perpendicular
    prr = perpendicular+delta*ur**2
    pzz = perpendicular+delta*uz**2
    prz = delta*ur*uz
    drz = stable_gradient(prz, r, 1)
    fr = stable_gradient(prr, r, 1)+stable_gradient(prz, z, 0)
    fz = drz+stable_gradient(pzz, z, 0)
    er = gradient_roundoff(prr, r, 1)+gradient_roundoff(prz, z, 0)
    ez = gradient_roundoff(prz, r, 1)+gradient_roundoff(pzz, z, 0)
    off = R>0.
    fr[off] += (prr[off]-perpendicular[off])/R[off]
    fz[off] += prz[off]/R[off]
    er[off] += 64*np.finfo(float).eps*(np.abs(prr[off])+np.abs(perpendicular[off]))/R[off]
    ez[off] += 64*np.finfo(float).eps*np.abs(prz[off])/R[off]
    if r[0] == 0.:
        # P_RZ is odd in R: lim(P_RZ/R)=d_R P_RZ. Regular FR=Jphi=0.
        fz[:, 0] += drz[:, 0]
        ez[:, 0] += gradient_roundoff(prz, r, 1)[:, 0]
        fr[:, 0] = 0.
        er[:, 0] = 0.
    b2 = B**2
    j = np.divide(bz*fr-br*fz, b2, out=np.zeros_like(B), where=b2>np.finfo(float).tiny)
    if r[0] == 0.:
        j[:, 0] = 0.
    fp = ur*fr+uz*fz
    ep = np.abs(ur)*er+np.abs(uz)*ez+64*np.finfo(float).eps*(np.abs(ur*fr)+np.abs(uz*fz))
    return {'force_R':fr, 'force_Z':fz, 'parallel_force':fp, 'J_phi':j, 'B':B,
            'force_roundoff_R':er, 'force_roundoff_Z':ez, 'parallel_force_roundoff':ep}


def rms(values, mask):
    v = np.asarray(values)[mask]
    if not v.size:
        return 0.
    scale = float(np.max(np.abs(v)))
    return 0. if scale == 0. else scale*float(np.sqrt(np.mean((v/scale)**2)))


def residual_metrics(residual, scale, roundoff, mask):
    """Return resolved relative error plus unmodified absolute/raw diagnostics."""
    absolute = rms(residual, mask)
    norm = rms(scale, mask)
    bound = rms(roundoff, mask)
    tiny = np.finfo(float).tiny
    return {'error': max(absolute-bound, 0.)/max(norm, bound, tiny),
            'absolute':absolute, 'raw_relative':absolute/max(norm, tiny),
            'roundoff':bound, 'roundoff_consistent':absolute<=bound}
