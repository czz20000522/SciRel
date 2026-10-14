"""Shared finite pressure-spline and current/Green equations."""
import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline


def fit_pressure_spline(psi_samples, pressure_samples):
    """Fit exactly the supplied edge prefix, with zero pressure extrapolation."""
    x,y=np.asarray(psi_samples,dtype=float),np.asarray(pressure_samples,dtype=float)
    if x.ndim!=1 or x.size<4 or y.shape!=x.shape or not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(np.diff(x)<=0):
        raise FloatingPointError('midplane flux must be finite and strictly increasing with at least four points')
    fitted=InterpolatedUnivariateSpline(x,y,ext='zeros')
    if not np.isfinite(fitted.get_coeffs()).all():
        raise FloatingPointError('nonfinite pressure-current spline coefficients')
    return fitted


def pressure_derivative(fitted,flux,edge,clip=None):
    """Evaluate a finite derivative before applying physical clipping."""
    values=np.asarray(fitted.derivative()(flux),dtype=float)
    if not np.isfinite(values).all():
        raise FloatingPointError('nonfinite pressure-current derivative')
    values[np.asarray(flux)>edge]=0.
    if clip is not None:values[clip]=0.
    return values


def current_target(radius,derivative,dr,dz):
    """I_cell=R*dP/dpsi*dR*dZ in amperes; no nonfinite-to-zero mask."""
    with np.errstate(over='ignore',invalid='ignore'):
        target=np.asarray(radius)*np.asarray(derivative)*dr*dz
    if not np.isfinite(target).all():
        raise FloatingPointError('nonfinite pressure-current target')
    return target


def relaxed_green_update(target,old,relax,green,vacuum):
    """Mix currents and contract Green matrix, rejecting every nonfinite state."""
    with np.errstate(over='ignore',invalid='ignore'):
        currents=(1.-relax)*target+relax*old
        plasma=green @ currents
        flux=plasma+vacuum
    if not np.isfinite(currents).all():raise FloatingPointError('nonfinite relaxed current')
    if not np.isfinite(plasma).all():raise FloatingPointError('nonfinite Green update')
    if not np.isfinite(flux).all():raise FloatingPointError('nonfinite total flux')
    return currents,flux
