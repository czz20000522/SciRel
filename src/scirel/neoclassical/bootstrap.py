# Copyright 2024, 2026 DeepMind Technologies Limited
# Licensed under the Apache License, Version 2.0; retained license: licenses/torax/LICENSE.
"""Source-bound Sauter/Redl bootstrap-current operators.

The fits are the TORAX Sauter (PoP 1999) and Redl (PoP 2021) relations.  This
module deliberately takes face quantities and logarithmic gradients explicitly:
it does not reconstruct a magnetic equilibrium, collisionality, trapped
fraction, or pressure from names.  ``calculate_bootstrap_current`` returns the
parallel-current density on faces and arithmetic cell averages.

The TORAX source formed ``nu_i_star**2`` directly.  That gives ``inf/inf`` for
finite ``nu_i_star`` near the binary64 ceiling.  The alpha implementation below
evaluates the same rational function with binary exponent scaling, preserving ordinary values while making the declared finite domain true.
"""
from __future__ import annotations

import numpy as np
from scirel.geometry.face_to_cell import face_to_cell

__all__ = ["calculate_sauter_coefficients", "calculate_redl_coefficients", "calculate_bootstrap_current"]


def _face(name, value):
    if np.ma.isMaskedArray(value) and np.any(np.ma.getmaskarray(value)):
        raise ValueError(f"{name} must not be masked")
    try:
        if any(isinstance(x, (bool, np.bool_)) for x in np.asarray(value, dtype=object).flat):
            raise ValueError
        a = np.asarray(value)
        if a.dtype.kind not in "iuf":
            raise ValueError
        a = np.asarray(a, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a real numeric face array") from exc
    if a.ndim != 1 or a.size < 2 or not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be a finite one-dimensional face array (length >= 2)")
    return a


def _common(f_trap, nu_e_star, z_eff):
    f = _face("f_trap", f_trap)
    nue = _face("nu_e_star", nu_e_star)
    z = _face("Z_eff", z_eff)
    if not (f.shape == nue.shape == z.shape):
        raise ValueError("f_trap, nu_e_star and Z_eff must have equal shapes")
    if np.any((f < 0) | (f > 1)) or np.any(nue < 0) or np.any(z <= 0):
        raise ValueError("require 0 <= f_trap <= 1, nu_e_star >= 0 and Z_eff > 0")
    return f, nue, z


def _scalar(name, value):
    if np.ma.isMaskedArray(value) and np.any(np.ma.getmaskarray(value)):
        raise ValueError(f"{name} must not be masked")
    try:
        raw = np.asarray(value)
        if raw.shape != () or raw.dtype.kind not in "iuf":
            raise ValueError
        result = float(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a real numeric scalar") from exc
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _alpha_sauter(f, nu):
    t = np.sqrt(nu)
    alpha0 = -1.17 * (1 - f) / (1 - 0.22 * f - 0.19 * f**2)
    first = (alpha0 + 0.25 * (1 - f**2) * t) / (1 + 0.5 * t)
    return _weighted_alpha(first, f, nu, .315, .15)


def _weighted_alpha(first, f, nu, numerator, denominator):
    # y=nu**2*f**6: combine binary exponents before materializing y. This
    # avoids both squaring overflow and loss in cancelling logarithms.
    mn, en = np.frexp(nu)
    mf, ef = np.frexp(f)
    mantissa = mn**2 * mf**6
    exponent = 2*en + 6*ef
    out = np.array(first, copy=True)
    positive = (f > 0) & (nu > 0)
    small = positive & (exponent <= 0)
    large = positive & (exponent > 0)
    y = np.ldexp(mantissa[small], exponent[small])
    out[small] = (first[small] + numerator*y)/(1+denominator*y)
    inverse = np.ldexp(1/mantissa[large], -exponent[large])
    out[large] = (first[large]*inverse + numerator)/(inverse+denominator)
    return out


def calculate_sauter_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star):
    """Return Sauter ``(L31, L32, L34, alpha)`` on faces.

    ``f_trap`` is dimensionless trapped fraction, ``nu_*`` are dimensionless
    collisionalities, and ``Z_eff`` is dimensionless effective charge.  Inputs
    are finite arrays with common shape, ``0 <= f_trap <= 1``, ``nu_* >= 0`` and
    ``Z_eff > 0``.  Values are empirical fit coefficients, not a full
    neoclassical or equilibrium solution.
    """
    f, nue, z = _common(f_trap, nu_e_star, Z_eff)
    nui = _face("nu_i_star", nu_i_star)
    if nui.shape != f.shape or np.any(nui < 0):
        raise ValueError("nu_i_star must match the face shape and be nonnegative")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        d31 = 1 + (1 - .1*f)*np.sqrt(nue) + .5*(1-f)*nue/z
        ft31 = f/d31
        l31 = (1+1.4/(z+1))*ft31 - 1.9/(z+1)*ft31**2 + .3/(z+1)*ft31**3 + .2/(z+1)*ft31**4
        ee = f/(1+.26*(1-f)*np.sqrt(nue)+.18*(1-.37*f)*nue/np.sqrt(z))
        ei = f/(1+(1+.6*f)*np.sqrt(nue)+.85*(1-.37*f)*nue*(1+z))
        l32 = ((.05+.62*z)/(z*(1+.44*z))*(ee-ee**4)+1/(1+.22*z)*(ee**2-ee**4-1.2*(ee**3-ee**4))+1.2/(1+.5*z)*ee**4
                -(.56+1.93*z)/(z*(1+.44*z))*(ei-ei**4)+4.95/(1+2.48*z)*(ei**2-ei**4-.55*(ei**3-ei**4))-1.2/(1+.5*z)*ei**4)
        d34 = 1+(1-.1*f)*np.sqrt(nue)+.5*(1-.5*f)*nue/z
        ft34 = f/d34
        l34 = (1+1.4/(z+1))*ft34 - 1.9/(z+1)*ft34**2 + .3/(z+1)*ft34**3 + .2/(z+1)*ft34**4
    alpha = _alpha_sauter(f, nui)
    out = (l31, l32, l34, alpha)
    if not all(np.all(np.isfinite(x)) for x in out):
        raise FloatingPointError("Sauter coefficients are not finite for the supplied faces")
    return out


def _alpha_redl(f, nu, z):
    a0 = -((.62+.055*(z-1)) / (.53+.17*(z-1))) * ((1-f)/(1-(.31-.065*(z-1))*f-.25*f**2))
    first = (a0 + .7*z*np.sqrt(f)*np.sqrt(nu))/(1+.18*np.sqrt(nu))
    return _weighted_alpha(first, f, nu, -.002, .004)


def calculate_redl_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star):
    """Return Redl ``(L31, L32, L34, alpha)`` on faces.

    Redl's published fit requires ``Z_eff >= 1`` because it contains
    ``sqrt(Z_eff - 1)``; Redl Eq. 19 sets the shared-expression ``L34`` equal
    to ``L31``.
    """
    f, nue, z = _common(f_trap, nu_e_star, Z_eff)
    nui = _face("nu_i_star", nu_i_star)
    if nui.shape != f.shape or np.any(nui < 0) or np.any(z < 1):
        raise ValueError("Redl requires nu_i_star >= 0 and Z_eff >= 1")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        s = np.sqrt(nue)
        fe31 = f/(1+(.67*(1-.7*f)*s)/(.56+.44*z)+((.52+.086*s)*(1+.87*f)*nue)/(1+1.13*np.sqrt(z-1)))
        den = z**1.2-.71
        l31 = (1+.15/den)*fe31-.22/den*fe31**2+.01/den*fe31**3+.06/den*fe31**4
        fee = f/(1+.23*(1-.96*f)*s/z**.5 + (.13*(1-.38*f)*nue/z**2)*(np.sqrt(1+2*np.sqrt(z-1))+f**2*np.sqrt((.075+.25*(z-1)**2)*nue)))
        l32ee = ((.1+.6*z)/(z*(.77+.63*(1+(z-1)**1.1)))*(fee-fee**4)+.7/(1+.2*z)*(fee**2-fee**4-1.2*(fee**3-fee**4))+1.3/(1+.5*z)*fee**4)
        fei = f/(1+(.87*(1+.39*f)*s)/(1+2.95*(z-1)**2)+1.53*(1-.37*f)*nue*(2+.375*(z-1)))
        l32ei = (-(.4+1.93*z)/(z*(.8+.6*z))*(fei-fei**4)+5.5/(1.5+2*z)*(fei**2-fei**4-.8*(fei**3-fei**4))-1.3/(1+.5*z)*fei**4)
        l32 = l32ee+l32ei
    alpha = _alpha_redl(f, nui, z)
    # Redl Eq. 19 identifies L34 with L31 in the shared bootstrap expression.
    out = (l31, l32, l31.copy(), alpha)
    if not all(np.all(np.isfinite(x)) for x in out):
        raise FloatingPointError("Redl coefficients are not finite for the supplied faces")
    return out


def calculate_bootstrap_current(*, bootstrap_multiplier=1.0, F_face, B0, dpsi_drho_face,
                                p_e_face, p_i_face, dlnne_drho_face,
                                dlnni_drho_face, dlnte_drho_face, dlnti_drho_face,
                                L31, L32, L34, alpha):
    """Evaluate the analytic parallel bootstrap current on faces and cells.

    ``F_face`` is the toroidal flux function [T m], ``B0`` [T],
    ``dpsi_drho_face`` [Wb], pressures are [Pa], and logarithmic gradients are
    per normalized-radius unit.  All arrays have length ``N+1``.  The axis
    coefficient is defined as exactly zero; subsequent cells are arithmetic
    averages of adjacent faces.  This is the bounded Sauter/Redl fit relation,
    not a geometry reconstruction or plasma calibration.
    """
    names = locals()
    arrays = {n: _face(n, names[n]) for n in ("F_face","dpsi_drho_face","p_e_face","p_i_face","dlnne_drho_face","dlnni_drho_face","dlnte_drho_face","dlnti_drho_face","L31","L32","L34","alpha")}
    shape = arrays["F_face"].shape
    if any(a.shape != shape for a in arrays.values()):
        raise ValueError("all bootstrap face arrays must have the same shape")
    b0 = _scalar("B0", B0)
    mult = _scalar("bootstrap_multiplier", bootstrap_multiplier)
    if not np.isfinite(b0) or b0 == 0 or not np.isfinite(mult):
        raise ValueError("B0 must be finite and nonzero; multiplier must be finite")
    if np.any(arrays["dpsi_drho_face"][1:] == 0.0):
        raise ValueError("dpsi_drho_face must be nonzero away from the axis")
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        g = -arrays["F_face"]*mult*2*np.pi/b0 / arrays["dpsi_drho_face"]
        term = (arrays["L31"]*arrays["p_e_face"]*arrays["dlnne_drho_face"]
                + arrays["L31"]*arrays["p_i_face"]*arrays["dlnni_drho_face"]
                + (arrays["L31"]+arrays["L32"])*arrays["p_e_face"]*arrays["dlnte_drho_face"]
                + (arrays["L31"]+arrays["alpha"]*arrays["L34"])*arrays["p_i_face"]*arrays["dlnti_drho_face"])
        j_face = g*term
    j_face = np.asarray(j_face, dtype=float); j_face[0] = 0.0
    if not np.all(np.isfinite(j_face)):
        raise FloatingPointError("bootstrap current is not finite")
    return {"j_parallel_bootstrap_face": j_face, "j_parallel_bootstrap": face_to_cell(j_face)}
