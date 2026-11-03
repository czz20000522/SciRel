"""Sauter and Redl neoclassical bootstrap-current fits.

The functions accept already evaluated face quantities.  They do not infer
collisionality, trapped fraction, magnetic geometry, or pressure profiles.
"""

from __future__ import annotations

import numpy as np

from scirel.geometry.face_to_cell import face_to_cell

__all__ = [
    "calculate_sauter_coefficients",
    "calculate_redl_coefficients",
    "calculate_bootstrap_current",
]


def _face(name, value):
    """Convert a finite real one-dimensional face array."""
    if np.ma.isMaskedArray(value) and np.any(np.ma.getmaskarray(value)):
        raise ValueError(f"{name} must not be masked")
    try:
        raw = np.asarray(value)
        original = np.asarray(value, dtype=object)
        if any(isinstance(item, (bool, np.bool_)) for item in original.flat):
            raise ValueError
        if raw.dtype.kind not in "iuf":
            raise ValueError
        array = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a real numeric face array") from exc
    if array.ndim != 1 or array.size < 2 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite one-dimensional face array (length >= 2)")
    return array


def _scalar(name, value):
    """Convert a finite real scalar while rejecting masked/bool values."""
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


def _common(f_trap, nu_e_star, z_eff):
    trapped = _face("f_trap", f_trap)
    electron = _face("nu_e_star", nu_e_star)
    charge = _face("Z_eff", z_eff)
    if not (trapped.shape == electron.shape == charge.shape):
        raise ValueError("f_trap, nu_e_star and Z_eff must have equal shapes")
    if np.any((trapped < 0.0) | (trapped > 1.0)) or np.any(electron < 0.0) or np.any(charge <= 0.0):
        raise ValueError("require 0 <= f_trap <= 1, nu_e_star >= 0 and Z_eff > 0")
    return trapped, electron, charge


def _weighted_alpha(first, f, nu, numerator, denominator):
    """Evaluate the ``nu**2*f**6`` correction without overflow."""
    nu_mantissa, nu_exponent = np.frexp(nu)
    f_mantissa, f_exponent = np.frexp(f)
    mantissa = nu_mantissa**2 * f_mantissa**6
    exponent = 2 * nu_exponent + 6 * f_exponent
    result = np.array(first, copy=True)
    positive = (f > 0.0) & (nu > 0.0)
    small = positive & (exponent <= 0)
    large = positive & (exponent > 0)
    correction = np.ldexp(mantissa[small], exponent[small])
    result[small] = (first[small] + numerator * correction) / (1.0 + denominator * correction)
    inverse = np.ldexp(1.0 / mantissa[large], -exponent[large])
    result[large] = (first[large] * inverse + numerator) / (inverse + denominator)
    return result


def _alpha_sauter(f, nu):
    root = np.sqrt(nu)
    alpha0 = -1.17 * (1.0 - f) / (1.0 - 0.22 * f - 0.19 * f**2)
    first = (alpha0 + 0.25 * (1.0 - f**2) * root) / (1.0 + 0.5 * root)
    return _weighted_alpha(first, f, nu, 0.315, 0.15)


def calculate_sauter_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star):
    """Return Sauter's ``(L31, L32, L34, alpha)`` arrays on faces."""
    f, nue, z = _common(f_trap, nu_e_star, Z_eff)
    nui = _face("nu_i_star", nu_i_star)
    if nui.shape != f.shape or np.any(nui < 0.0):
        raise ValueError("nu_i_star must match the face shape and be nonnegative")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        d31 = 1.0 + (1.0 - 0.1 * f) * np.sqrt(nue) + 0.5 * (1.0 - f) * nue / z
        ft31 = f / d31
        l31 = (
            (1.0 + 1.4 / (z + 1.0)) * ft31
            - 1.9 / (z + 1.0) * ft31**2
            + 0.3 / (z + 1.0) * ft31**3
            + 0.2 / (z + 1.0) * ft31**4
        )
        ee = f / (
            1.0 + 0.26 * (1.0 - f) * np.sqrt(nue) + 0.18 * (1.0 - 0.37 * f) * nue / np.sqrt(z)
        )
        ei = f / (1.0 + (1.0 + 0.6 * f) * np.sqrt(nue) + 0.85 * (1.0 - 0.37 * f) * nue * (1.0 + z))
        l32 = (
            (0.05 + 0.62 * z) / (z * (1.0 + 0.44 * z)) * (ee - ee**4)
            + 1.0 / (1.0 + 0.22 * z) * (ee**2 - ee**4 - 1.2 * (ee**3 - ee**4))
            + 1.2 / (1.0 + 0.5 * z) * ee**4
            - (0.56 + 1.93 * z) / (z * (1.0 + 0.44 * z)) * (ei - ei**4)
            + 4.95 / (1.0 + 2.48 * z) * (ei**2 - ei**4 - 0.55 * (ei**3 - ei**4))
            - 1.2 / (1.0 + 0.5 * z) * ei**4
        )
        d34 = 1.0 + (1.0 - 0.1 * f) * np.sqrt(nue) + 0.5 * (1.0 - 0.5 * f) * nue / z
        ft34 = f / d34
        l34 = (
            (1.0 + 1.4 / (z + 1.0)) * ft34
            - 1.9 / (z + 1.0) * ft34**2
            + 0.3 / (z + 1.0) * ft34**3
            + 0.2 / (z + 1.0) * ft34**4
        )
    result = (l31, l32, l34, _alpha_sauter(f, nui))
    if not all(np.all(np.isfinite(value)) for value in result):
        raise FloatingPointError("Sauter coefficients are not finite for the supplied faces")
    return result


def _alpha_redl(f, nu, z):
    alpha0 = -((0.62 + 0.055 * (z - 1.0)) / (0.53 + 0.17 * (z - 1.0))) * (
        (1.0 - f) / (1.0 - (0.31 - 0.065 * (z - 1.0)) * f - 0.25 * f**2)
    )
    first = (alpha0 + 0.7 * z * np.sqrt(f) * np.sqrt(nu)) / (1.0 + 0.18 * np.sqrt(nu))
    return _weighted_alpha(first, f, nu, -0.002, 0.004)


def calculate_redl_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star):
    """Return Redl's ``(L31, L32, L34, alpha)`` arrays on faces."""
    f, nue, z = _common(f_trap, nu_e_star, Z_eff)
    nui = _face("nu_i_star", nu_i_star)
    if nui.shape != f.shape or np.any(nui < 0.0) or np.any(z < 1.0):
        raise ValueError("Redl requires nu_i_star >= 0 and Z_eff >= 1")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        root_nu = np.sqrt(nue)
        fe31 = f / (
            1.0
            + 0.67 * (1.0 - 0.7 * f) * root_nu / (0.56 + 0.44 * z)
            + (0.52 + 0.086 * root_nu) * (1.0 + 0.87 * f) * nue / (1.0 + 1.13 * np.sqrt(z - 1.0))
        )
        denominator = z**1.2 - 0.71
        l31 = (
            (1.0 + 0.15 / denominator) * fe31
            - 0.22 / denominator * fe31**2
            + 0.01 / denominator * fe31**3
            + 0.06 / denominator * fe31**4
        )
        fee = f / (
            1.0
            + 0.23 * (1.0 - 0.96 * f) * root_nu / np.sqrt(z)
            + (0.13 * (1.0 - 0.38 * f) * nue / z**2)
            * (
                np.sqrt(1.0 + 2.0 * np.sqrt(z - 1.0))
                + f**2 * np.sqrt((0.075 + 0.25 * (z - 1.0) ** 2) * nue)
            )
        )
        l32ee = (
            (0.1 + 0.6 * z) / (z * (0.77 + 0.63 * (1.0 + (z - 1.0) ** 1.1))) * (fee - fee**4)
            + 0.7 / (1.0 + 0.2 * z) * (fee**2 - fee**4 - 1.2 * (fee**3 - fee**4))
            + 1.3 / (1.0 + 0.5 * z) * fee**4
        )
        fei = f / (
            1.0
            + 0.87 * (1.0 + 0.39 * f) * root_nu / (1.0 + 2.95 * (z - 1.0) ** 2)
            + 1.53 * (1.0 - 0.37 * f) * nue * (2.0 + 0.375 * (z - 1.0))
        )
        l32ei = (
            -(0.4 + 1.93 * z) / (z * (0.8 + 0.6 * z)) * (fei - fei**4)
            + 5.5 / (1.5 + 2.0 * z) * (fei**2 - fei**4 - 0.8 * (fei**3 - fei**4))
            - 1.3 / (1.0 + 0.5 * z) * fei**4
        )
        l32 = l32ee + l32ei
    result = (l31, l32, l31.copy(), _alpha_redl(f, nui, z))
    if not all(np.all(np.isfinite(value)) for value in result):
        raise FloatingPointError("Redl coefficients are not finite for the supplied faces")
    return result


def calculate_bootstrap_current(
    *,
    bootstrap_multiplier=1.0,
    rho_face,
    F_face,
    B0,
    dpsi_drho_face=None,
    dpsi_per_radian_drho_face=None,
    p_e_face,
    p_i_face,
    dlnne_drho_face,
    dlnni_drho_face,
    dlnte_drho_face,
    dlnti_drho_face,
    L31,
    L32,
    L34,
    alpha,
):
    """Evaluate the parallel bootstrap current density on faces and cell means.

    ``<j.B>/B0 = -(F / (B0 dpsi/drho)) [L31 p_e dln n_e + L31 p_i dln n_i
    + (L31 + L32) p_e dln T_e + (L31 + alpha L34) p_i dln T_i]`` with the
    gradients taken with respect to the same radius as ``dpsi/drho``, and
    ``psi`` the poloidal flux per radian (``R * A_phi``, Wb/rad).

    Parameters
    ----------
    rho_face : array_like
        Radial coordinate of the faces, nonnegative and strictly increasing.
        A face at ``rho_face == 0`` is the magnetic axis; its current is set
        to zero there (the trapped fraction and the gradients vanish). No
        other face is treated as the axis, so a grid that starts off-axis
        keeps its first value.
    dpsi_drho_face, dpsi_per_radian_drho_face : array_like
        Give exactly one. ``dpsi_drho_face`` is the derivative of the total
        poloidal flux in Wb (``2*pi`` times the per-radian flux);
        ``dpsi_per_radian_drho_face`` is the derivative of ``psi = R*A_phi``
        in Wb/rad, the convention of G-EQDSK files and of
        ``scirel.io.read_geqdsk``. Both or neither raise ``ValueError``.
        Must be nonzero on every face except an axis face.

    The remaining face arrays (``F_face`` in T m, pressures in Pa,
    dimensionless logarithmic gradients and fit coefficients) must all have
    the shape of ``rho_face``. ``B0`` is a nonzero scalar in T.

    Returns
    -------
    dict
        ``j_parallel_bootstrap_face`` (A/m^2 on faces) and
        ``j_parallel_bootstrap`` (arithmetic means of adjacent faces).
    """
    if (dpsi_drho_face is None) == (dpsi_per_radian_drho_face is None):
        raise ValueError(
            "give exactly one of dpsi_drho_face (total poloidal flux, Wb) or "
            "dpsi_per_radian_drho_face (flux per radian, Wb/rad)"
        )
    per_radian = dpsi_per_radian_drho_face is not None
    names = locals()
    flux_name = "dpsi_per_radian_drho_face" if per_radian else "dpsi_drho_face"
    array_names = (
        "rho_face",
        "F_face",
        flux_name,
        "p_e_face",
        "p_i_face",
        "dlnne_drho_face",
        "dlnni_drho_face",
        "dlnte_drho_face",
        "dlnti_drho_face",
        "L31",
        "L32",
        "L34",
        "alpha",
    )
    arrays = {name: _face(name, names[name]) for name in array_names}
    shape = arrays["rho_face"].shape
    if any(value.shape != shape for value in arrays.values()):
        raise ValueError("all bootstrap face arrays must have the shape of rho_face")
    rho = arrays["rho_face"]
    if np.any(rho < 0.0) or np.any(np.diff(rho) <= 0.0):
        raise ValueError("rho_face must be nonnegative and strictly increasing")
    b0 = _scalar("B0", B0)
    multiplier = _scalar("bootstrap_multiplier", bootstrap_multiplier)
    if b0 == 0.0:
        raise ValueError("B0 must be finite and nonzero; multiplier must be finite")
    axis = rho == 0.0
    if np.any(arrays[flux_name][~axis] == 0.0):
        raise ValueError(f"{flux_name} must be nonzero away from the axis (rho_face > 0)")
    turn = 1.0 if per_radian else 2.0 * np.pi
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        prefactor = -arrays["F_face"] * multiplier * turn / b0 / arrays[flux_name]
        pressure_gradient = (
            arrays["L31"] * arrays["p_e_face"] * arrays["dlnne_drho_face"]
            + arrays["L31"] * arrays["p_i_face"] * arrays["dlnni_drho_face"]
            + (arrays["L31"] + arrays["L32"]) * arrays["p_e_face"] * arrays["dlnte_drho_face"]
            + (arrays["L31"] + arrays["alpha"] * arrays["L34"])
            * arrays["p_i_face"]
            * arrays["dlnti_drho_face"]
        )
        current = prefactor * pressure_gradient
    current = np.asarray(current, dtype=float)
    current[axis] = 0.0
    if not np.all(np.isfinite(current)):
        raise FloatingPointError("bootstrap current is not finite")
    return {"j_parallel_bootstrap_face": current, "j_parallel_bootstrap": face_to_cell(current)}
