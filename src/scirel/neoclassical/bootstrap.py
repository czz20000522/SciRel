"""Sauter and Redl neoclassical bootstrap-current fits.

The functions accept already evaluated face quantities.  They do not infer
collisionality, trapped fraction, magnetic geometry, or pressure profiles.
"""

from __future__ import annotations

import numpy as np

from scirel._result import Result
from scirel.numerics.interpolate import face_to_cell

__all__ = [
    "compute_bootstrap_coefficients",
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


def _sauter_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star):
    """Evaluate the existing Sauter coefficient fit."""
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
    return Result(L31=result[0], L32=result[1], L34=result[2], alpha=result[3])


def _alpha_redl(f, nu, z):
    alpha0 = -((0.62 + 0.055 * (z - 1.0)) / (0.53 + 0.17 * (z - 1.0))) * (
        (1.0 - f) / (1.0 - (0.31 - 0.065 * (z - 1.0)) * f - 0.25 * f**2)
    )
    first = (alpha0 + 0.7 * z * np.sqrt(f) * np.sqrt(nu)) / (1.0 + 0.18 * np.sqrt(nu))
    return _weighted_alpha(first, f, nu, -0.002, 0.004)


def _redl_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star):
    """Evaluate the existing Redl coefficient fit."""
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
    return Result(L31=result[0], L32=result[1], L34=result[2], alpha=result[3])


def compute_bootstrap_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star, *, method="redl"):
    """Evaluate one of the existing bootstrap-current coefficient fits.

    Parameters
    ----------
    f_trap : real array_like, shape (N+1,)
        Trapped-particle fraction [1], not inverse aspect ratio. Finite values
        in [0, 1]; at least two faces and the same shape as all other inputs.
    nu_e_star : real array_like, shape (N+1,)
        Electron collisionality [1] in the selected fit's normalization.
        Finite and nonnegative; no broadcasting or normalization is inferred.
    Z_eff : real array_like, shape (N+1,)
        Effective charge [1]. Strictly positive for Sauter; at least one for
        Redl. Values below one are not a fully ionized quasineutral plasma.
    nu_i_star : real array_like, shape (N+1,)
        Ion collisionality [1] in the selected fit's normalization. Finite and
        nonnegative, with the same explicit face shape as f_trap.
    method : {'redl', 'sauter'}, optional
        Closed fit selector [1]. The default is the newer Redl refit; this does
        not imply it is more accurate for every plasma. Read the selected
        method's range and limitations in the family contract.

    Returns
    -------
    L31 : float64 array, shape (N+1,)
        Density-gradient fit coefficient [1] in the returned Result mapping.
    L32 : float64 array, shape (N+1,)
        Electron-temperature coefficient correction [1] in the same mapping.
    L34 : float64 array, shape (N+1,)
        Ion-temperature fit coefficient [1]; equal to L31 for Redl.
    alpha : float64 array, shape (N+1,)
        Ion-temperature-gradient multiplier [1]. All four fields are finite
        and follow the explicit input face shape.

    Raises
    ------
    TypeError
        If method is not a string, or an unsupported parameter is supplied.
    ValueError
        If method is unknown or any physical input is masked, non-real,
        nonfinite, incorrectly shaped or outside the selected fit's domain.
    FloatingPointError
        If the computed coefficients are not finite.

    See Also
    --------
    calculate_bootstrap_current : Assemble current from explicit coefficients.

    Notes
    -----
    Both methods accept the same physical quantities and return the Result
    fields L31, L32, L34, alpha in that order. Each retains its existing fit,
    charge domain and failure behavior. The caller supplies trapped fraction
    and collisionality; this function derives no magnetic geometry or profiles.
    Method-specific applicability and evidence remain separate in contract
    scirel.neoclassical.bootstrap-coefficients. No numerical order option is
    implemented. Finite coefficient evaluation alone is not physical calibration.

    The Sauter choice retains the selected corrected positive 0.315 alpha
    term. The 1999 author manuscript prints a negative term; the fixed
    nonzero-trapped-fraction high-collisionality limit +2.1 in the 2021
    author paper and OMFIT's corrected implementation corroborate the
    positive choice. The original 2002 publisher erratum was not read here.
    Independent 80/120-digit paper-expression anchors check eighteen
    selected inputs per method; they do not estimate empirical fit error.

    References
    ----------
    .. [1] O. Sauter, C. Angioni and Y. R. Lin-Liu, Physics of Plasmas 6,
       2834 (1999), doi:10.1063/1.873240.
    .. [2] A. Redl et al., Physics of Plasmas 28, 022502 (2021),
       doi:10.1063/5.0012664.
    .. [3] OMFIT utils_fusion, corrected Sauter implementation,
       https://omfit.io/_modules/omfit_classes/utils_fusion.html.

    Examples
    --------
    >>> from scirel.neoclassical import compute_bootstrap_coefficients
    >>> redl = compute_bootstrap_coefficients([0.2, 0.4], [0.1, 1.0], [1.0, 2.0], [0.1, 1.0], method='redl')
    >>> sauter = compute_bootstrap_coefficients([0.2, 0.4], [0.1, 1.0], [1.0, 2.0], [0.1, 1.0], method='sauter')
    >>> assert list(redl) == list(sauter) == ['L31', 'L32', 'L34', 'alpha']
    >>> assert redl.L31.shape == sauter.L31.shape == (2,)
    """
    asset = "scirel.neoclassical.bootstrap-coefficients"
    if not isinstance(method, str):
        raise TypeError(
            f"method must be str selecting 'redl' or 'sauter'; received {type(method).__name__}; "
            f"see {asset}"
        )
    if method == "redl":
        return _redl_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star)
    if method == "sauter":
        return _sauter_coefficients(f_trap, nu_e_star, Z_eff, nu_i_star)
    raise ValueError(f"method={method[:64]!r} must be 'redl' or 'sauter'; see {asset}")


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
    """Evaluate the parallel bootstrap current density on faces and cell means as a named result.

    ``<j.B>/B0 = -(F / (B0 dpsi/drho)) [L31 p_e dln n_e + L31 p_i dln n_i
    + (L31 + L32) p_e dln T_e + (L31 + alpha L34) p_i dln T_i]`` with the
    gradients taken with respect to the same radius as ``dpsi/drho``, and
    ``psi`` the poloidal flux per radian (``R * A_phi``, Wb/rad).

    The two arrays are returned together in one ``scirel._result.Result``
    mapping; mapping lookup and attribute access expose the same fields.

    Parameters
    ----------
    bootstrap_multiplier : real numeric converted to float64, default 1.0
        Dimensionless multiplicative scale; signed algebra preserved. Finite
        real scalar; physical source configuration uses nonnegative multiplier.
    rho_face : real numeric converted to float64, shape N+1
        Radial coordinate of the faces. A face at rho_face == 0 is the magnetic
        axis and gets zero current; no other face is treated as the axis.
        Finite, nonnegative and strictly increasing; sets the face shape of
        every other array.
    F_face : real numeric converted to float64, shape N+1
        Toroidal flux function R*B_toroidal on faces [T m]. Finite explicit
        matching faces.
    B0 : real numeric converted to float64
        Reference toroidal magnetic field with a signed convention [T]. Finite
        nonzero scalar.
    dpsi_drho_face : real numeric converted to float64, shape N+1, default None
        Derivative of the TOTAL poloidal flux (2*pi times the per-radian psi =
        R*A_phi) with respect to rho_face. Give this or
        dpsi_per_radian_drho_face, not both [Wb]. Exactly one of dpsi_drho_face
        or dpsi_per_radian_drho_face; finite matching faces, nonzero wherever
        rho_face > 0.
    dpsi_per_radian_drho_face : real numeric converted to float64, shape N+1, default None
        Derivative of the poloidal flux per radian psi = R*A_phi (the G-EQDSK
        and scirel.io.read_geqdsk convention) with respect to rho_face. Give
        this or dpsi_drho_face, not both [Wb/rad]. Exactly one of dpsi_drho_face
        or dpsi_per_radian_drho_face; finite matching faces, nonzero wherever
        rho_face > 0.
    p_e_face : real numeric converted to float64, shape N+1
        Electron scalar thermal pressure [Pa]. Finite explicit matching faces.
    p_i_face : real numeric converted to float64, shape N+1
        Ion scalar thermal pressure [Pa]. Finite explicit matching faces.
    dlnne_drho_face : real numeric converted to float64, shape N+1
        Electron density logarithmic gradient. Finite explicit matching faces.
    dlnni_drho_face : real numeric converted to float64, shape N+1
        Main-ion density logarithmic gradient. Finite explicit matching faces.
    dlnte_drho_face : real numeric converted to float64, shape N+1
        Electron temperature logarithmic gradient. Finite explicit matching
        faces.
    dlnti_drho_face : real numeric converted to float64, shape N+1
        Ion temperature logarithmic gradient. Finite explicit matching faces.
    L31 : real numeric converted to float64, shape N+1
        Density-gradient fit coefficient. Finite explicit matching faces.
    L32 : real numeric converted to float64, shape N+1
        Electron-temperature coefficient correction. Finite explicit matching
        faces.
    L34 : real numeric converted to float64, shape N+1
        Ion-temperature coefficient; Redl must use L31. Finite explicit matching
        faces.
    alpha : real numeric converted to float64, shape N+1
        Ion temperature-gradient fit multiplier. Finite explicit matching faces.

    Returns
    -------
    j_parallel_bootstrap_face : real numeric converted to float64, shape N+1
        Field of the returned ``scirel._result.Result`` mapping: parallel current
        density <j.B>/B0 on faces; zero at a face with rho_face == 0 [A/m^2].
        Finite; equal explicit one-dimensional face shape; no broadcasting.
    j_parallel_bootstrap : real numeric converted to float64, shape N
        Field of the returned ``scirel._result.Result`` mapping: arithmetic
        adjacent-face cell current density [A/m^2]. Finite; equal explicit
        one-dimensional face shape; no broadcasting.

    Raises
    ------
    FloatingPointError
        FloatingPointError for nonfinite coefficient/current arithmetic; no
        fallback is returned.
    ValueError
        ValueError for malformed, nonfinite, masked, mismatched or out-of-domain
        face inputs; no partial result.

    See Also
    --------
    compute_bootstrap_coefficients : Select Sauter or Redl coefficients with method.
    scirel.io.read_geqdsk : G-EQDSK flux is per radian (Wb/rad).

    Notes
    -----
    The pressure form is L31*d(p_e+p_i)/drho + L32*p_e*dln(T_e)/drho
    + alpha*L34*p_i*dln(T_i)/drho. Expanding each scalar thermal pressure
    differential gives the four explicit drive terms above. Independent
    manufactured references check six signed-field/scale and flux-convention
    cases using this pressure form and 80/120-digit arithmetic. They validate
    assembly and the explicit rho=0 policy, not a physical magnetic-axis
    regularity theorem, transport calculation or coefficient calibration.

    References
    ----------
    .. [1] O. Sauter, C. Angioni and Y. R. Lin-Liu, Physics of Plasmas 6,
       2834 (1999), doi:10.1063/1.873240.
    .. [2] A. Redl et al., Physics of Plasmas 28, 022502 (2021),
       doi:10.1063/5.0012664.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.neoclassical import calculate_bootstrap_current
    >>> one=np.ones(3); zero=np.zeros(3)
    >>> kw=dict(rho_face=[0.,.5,1.],F_face=one,B0=2.,p_e_face=one,p_i_face=one,dlnne_drho_face=one,dlnni_drho_face=zero,dlnte_drho_face=zero,dlnti_drho_face=zero,L31=one,L32=zero,L34=one,alpha=one)
    >>> x=calculate_bootstrap_current(dpsi_drho_face=one,**kw)
    >>> assert isinstance(x, Result)
    >>> assert list(x) == ['j_parallel_bootstrap_face', 'j_parallel_bootstrap']
    >>> assert x.j_parallel_bootstrap_face is x['j_parallel_bootstrap_face']
    >>> np.testing.assert_allclose(x['j_parallel_bootstrap_face'],[0,-np.pi,-np.pi])
    >>> y=calculate_bootstrap_current(dpsi_per_radian_drho_face=one/(2*np.pi),**kw)
    >>> np.testing.assert_allclose(y['j_parallel_bootstrap_face'],x['j_parallel_bootstrap_face'])
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
    return Result(
        {
            "j_parallel_bootstrap_face": current,
            "j_parallel_bootstrap": face_to_cell(current),
        }
    )
