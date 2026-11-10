"""Vectorized Boltzmann electron response and charge-neutrality residual."""

from __future__ import annotations

import numpy as np

from scirel._numerics import _scaled_difference
from scirel._result import Result

ELEMENTARY_CHARGE_C = 1.602176634e-19


def compute_boltzmann_electron_state(
    potential_v,
    electron_temperature_j,
    electron_density_ref_m3,
    electron_phi_ref_v,
    ion_density_m3,
    ion_charge_state,
):
    """Evaluate an unclipped Boltzmann electron state as a named result.

    The supplied potential is evaluated pointwise against a prescribed electron
    temperature and reference state, then compared with the supplied ion state.
    The potential difference is formed before charge multiplication, so a common
    potential gauge does not erase a represented difference.

    Parameters
    ----------
    potential_v : array_like, shape (...)
        Electrostatic potential where the electron response is evaluated [V].
        Values must be finite after conversion to float64.
    electron_temperature_j : array_like, shape (...)
        Electron thermal-energy scale [J]. Values must be finite and strictly
        positive.
    electron_density_ref_m3 : array_like, shape (...)
        Electron number density at the reference potential [m^-3]. Values must
        be finite and nonnegative; zero is valid.
    electron_phi_ref_v : array_like, shape (...)
        Electrostatic reference potential [V]. Values must be finite.
    ion_density_m3 : array_like, shape (...)
        Supplied positive-ion number density [m^-3]. Values must be finite and
        nonnegative; zero is valid.
    ion_charge_state : float-convertible scalar
        Positive ion charge-state multiplier [dimensionless]. The value must be
        finite and strictly positive; it is not required to be integral.

    Returns
    -------
    electron_density_m3 : float64 scalar or ndarray of float64, shape (...)
        Field of the returned ``scirel._result.Result`` mapping containing the
        unclipped Boltzmann electron number density [m^-3]. It is finite on
        return but may underflow to zero.
    electron_pressure_pa : float64 scalar or ndarray of float64, shape (...)
        Field containing ``electron_density_m3 * electron_temperature_j`` [Pa].
        It remains representable when only the density underflows.
    logarithmic_charge_residual : float64 scalar or ndarray of float64, shape (...)
        Field containing the ion-electron logarithmic density ratio
        [dimensionless]. For exactly one absent species, a signed finite
        diagnostic proxy with magnitude at least one is returned; joint vacuum
        gives zero.
    charge_residual_m3 : float64 scalar or ndarray of float64, shape (...)
        Field containing ``ion_charge_state * ion_density_m3 -
        electron_density_m3`` [m^-3]. This is a number-density residual, not an
        electric charge density in C/m^3.
    relative_charge_residual : float64 scalar or ndarray of float64, shape (...)
        Field containing ``tanh(logarithmic_charge_residual / 2)``
        [dimensionless]. It is finite in [-1, 1], with exact +/-1 for exactly
        one absent species and zero for joint vacuum.

    Raises
    ------
    TypeError
        If ``ion_charge_state`` is not a real scalar, or a field or charge
        conversion raises ``TypeError``.
    ValueError
        If a field is nonfinite, the electron temperature is not positive, a
        density is negative, ``ion_charge_state`` is not finite and positive,
        the five field inputs cannot be broadcast together, or a nonnumeric
        field conversion raises ``ValueError``.
    FloatingPointError
        If a nonrepresentable dimensionless potential, electron density,
        pressure, charge residual, or logarithmic residual would be returned.

    See Also
    --------
    scirel.closures.compute_reference_electron_density
        Computes a charge-state-weighted reference electron density.
    scirel.mirror.solve_mirror_quasineutral_closure
        Solves a mirror-electron quasineutrality relation that consumes this
        state.

    Notes
    -----
    With elementary charge ``e = 1.602176634e-19 C``, the electron logarithmic
    density is

    ``L_e = log(n_ref) + e * (phi - phi_ref) / T_e``

    for positive reference density, and the returned electron density and
    pressure are ``exp(L_e)`` and ``exp(L_e + log(T_e))``. For positive ions,
    ``L_i = log(n_i) + log(Z_i)`` and the logarithmic residual is ``L_i - L_e``.
    Binary scaling keeps the potential difference meaningful near floating-point
    range limits. Positive populations retain analytic log diagnostics even when
    a density rounds to zero, and the relative residual avoids overflow from
    forming a density sum. No physical exponent clipping or self-consistent
    potential solve is performed.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.closures import compute_boltzmann_electron_state
    >>> e = 1.602176634e-19
    >>> result = compute_boltzmann_electron_state(np.log(2.0), e, 3.0, 0.0, 3.0, 2.0)
    >>> assert isinstance(result, Result)
    >>> assert result.electron_density_m3 is result['electron_density_m3']
    >>> np.testing.assert_allclose(result['electron_density_m3'], 6.0)
    >>> np.testing.assert_allclose(result['electron_pressure_pa'], 6.0*e)
    >>> np.testing.assert_allclose(result['logarithmic_charge_residual'], 0.0, atol=1e-14)
    >>> np.testing.assert_allclose(result['charge_residual_m3'], 0.0, atol=1e-14)
    """
    potential, temperature, n_ref, phi_ref, ion_density = np.broadcast_arrays(
        *[
            np.asarray(x, dtype=float)
            for x in (
                potential_v,
                electron_temperature_j,
                electron_density_ref_m3,
                electron_phi_ref_v,
                ion_density_m3,
            )
        ]
    )
    z_i = float(ion_charge_state)
    if not np.isfinite(z_i) or z_i <= 0.0:
        raise ValueError("ion_charge_state must be finite and positive")
    if not all(
        np.all(np.isfinite(value))
        for value in (potential, temperature, n_ref, phi_ref, ion_density)
    ):
        raise ValueError("all fields must be finite")
    if np.any(temperature <= 0.0):
        raise ValueError("electron_temperature_j must be positive")
    if np.any(n_ref < 0.0) or np.any(ion_density < 0.0):
        raise ValueError("reference and ion densities cannot be negative")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        exponent = _scaled_difference(potential, phi_ref, ELEMENTARY_CHARGE_C, temperature)
    if not np.all(np.isfinite(exponent)):
        raise FloatingPointError("dimensionless electron potential is not representable")
    electron_log = np.full(n_ref.shape, -np.inf)
    ion_log = np.full(n_ref.shape, -np.inf)
    electrons = n_ref > 0
    ions = ion_density > 0
    electron_log[electrons] = np.log(n_ref[electrons]) + exponent[electrons]
    ion_log[ions] = np.log(ion_density[ions]) + np.log(z_i)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        electron_density = np.exp(electron_log)
        charge_density = z_i * ion_density
        electron_pressure = np.exp(electron_log + np.log(temperature))
    if not all(
        np.all(np.isfinite(x)) for x in (electron_density, charge_density, electron_pressure)
    ):
        raise FloatingPointError("density or pressure exceeds the finite output range")
    both = electrons & ions
    logarithmic_residual = np.zeros(n_ref.shape)
    logarithmic_residual[both] = ion_log[both] - electron_log[both]
    tiny_log = np.log(np.finfo(float).tiny)
    logarithmic_residual[ions & ~electrons] = np.maximum(
        1.0, np.abs(ion_log[ions & ~electrons] - tiny_log)
    )
    logarithmic_residual[electrons & ~ions] = -np.maximum(
        1.0, np.abs(electron_log[electrons & ~ions] - tiny_log)
    )
    if not np.all(np.isfinite(logarithmic_residual)):
        raise FloatingPointError("logarithmic charge residual must be finite")
    relative_residual = np.asarray(np.tanh(0.5 * logarithmic_residual))
    relative_residual[ions & ~electrons] = 1.0
    relative_residual[electrons & ~ions] = -1.0
    return Result(
        {
            "electron_density_m3": electron_density,
            "electron_pressure_pa": electron_pressure,
            "logarithmic_charge_residual": logarithmic_residual,
            "charge_residual_m3": charge_density - electron_density,
            "relative_charge_residual": relative_residual,
        }
    )


__all__ = ["compute_boltzmann_electron_state"]
