"""Terminal H2+ density and temperature from caller-owned state profiles.

The relation takes the terminal H2 density, the electron density, the ion
temperature, the R1 two-body ionization rate coefficient, an eleven-channel
two-body reaction-rate table and a loss frequency. It does not assemble
collision tables or evolve a terminal molecular-ion state.
"""

from __future__ import annotations

import numpy as np

__all__ = ["reduce_terminal_molecular_ion_state"]


def _real_numeric(name, value):
    try:
        if not isinstance(value, np.ndarray) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real numeric values") from exc


def reduce_terminal_molecular_ion_state(
    molecular_density_m3,
    electron_density_m3,
    ion_temperature_ev,
    mass_ratio,
    ionization_rate_coefficient_m3_s,
    reaction_rate_table_m3_s,
    loss_frequency_s_inv,
):
    """Reduce explicit terminal state profiles to H2+ density and temperature diagnostics.

    Parameters
    ----------
    molecular_density_m3 : array_like, shape (nx,)
        Finite nonnegative terminal H2 density. [m^-3]
    electron_density_m3 : array_like, shape (nx,)
        Finite nonnegative electron density. It multiplies the two-body rate
        coefficients in the H2+ electron-loss frequency and in the energy
        exchange coefficient. [m^-3]
    ion_temperature_ev : array_like, shape (nx,)
        Finite strictly positive ion temperature. [eV]
    mass_ratio : float
        Positive finite source isotope mass factor in the energy exchange
        coefficient. It has physical standing only for the H=1 and D=2 mass
        factors; every other positive value is an algebraic extension.
        [1]
    ionization_rate_coefficient_m3_s : array_like, shape (nx,)
        Finite nonnegative R1 two-body ionization rate coefficient for
        ``e- + H2 -> H2+ + 2e-``, used in the H2+ density numerator.
        [m^3 s^-1]
    reaction_rate_table_m3_s : array_like, shape (nx, 11)
        Finite nonnegative two-body rate coefficients in source channel order:
        column ``0`` is unused, column ``1`` is source channel R1, and columns
        ``7:11`` are source channels R7 through R10. Only ``7:11`` are read, and
        they form the H2+ electron-loss frequency. [m^3 s^-1]
    loss_frequency_s_inv : array_like, shape (nx,)
        Finite nonnegative loss frequency added to the electron-loss frequency
        in both denominators. [s^-1]

    Returns
    -------
    molecular_ion_density_m3 : ndarray, shape (nx,)
        Algebraic terminal H2+ density from the supplied two-body rate form.
        [m^-3]
    molecular_ion_temperature_ev : ndarray, shape (nx,)
        Algebraic terminal H2+ temperature. [eV]
    electron_loss_frequency_s_inv : ndarray, shape (nx,)
        H2+ electron-impact loss frequency: electron density times the sum of
        reaction-table columns ``7:11``. [s^-1]
    energy_exchange_frequency_s_inv : ndarray, shape (nx,)
        Source-calibrated algebraic exchange coefficient with the explicit
        ``1e-6`` density scaling. [s^-1]

    Raises
    ------
    ValueError
        If inputs are non-real, non-finite or malformed, densities/rates are
        negative, ion temperature or mass ratio is nonpositive, either computed
        denominator is nonpositive or non-finite, or an output is invalid.

    See Also
    --------
    reduce_generation_density : Reduces a generation distribution to density.
    reduce_terminal_molecular_energy_transfer : Reduces signed transfer profiles.

    Notes
    -----
    The H2+ electron-loss frequency is the electron density times the sum of
    reaction-table columns ``7:11``, and the H2+ density is the H2 density times
    the electron density times the R1 ionization rate coefficient divided by
    that frequency plus the loss frequency. The temperature is the ion
    temperature times the exchange coefficient divided by the exchange
    coefficient plus the same denominator.

    Only columns ``7:11`` are read; the first seven columns, including the R1
    column, do not affect these outputs because the R1 coefficient arrives as
    its own profile. Column ``10`` is source channel R10, whose electron-product
    bookkeeping is unresolved: this relation treats it only as a source channel
    and asserts no product reaction for it.

    ``energy_exchange_frequency_s_inv`` is a source-calibrated algebraic
    coefficient with the stated arithmetic order. It is not a complete H2+
    energy-conservation closure, and this relation does not assemble collision
    tables or evolve a terminal state.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import reduce_terminal_molecular_ion_state
    >>> rates = np.zeros((2, 11))
    >>> rates[:, 7:11] = 1e-18
    >>> r = reduce_terminal_molecular_ion_state(np.array([4e17, 5e17]), np.array([1e18, 2e18]), np.array([2., 3.]), 2., np.array([4., 5.]), rates, np.array([1., 3.]))
    >>> assert set(r) == {'molecular_ion_density_m3', 'molecular_ion_temperature_ev', 'electron_loss_frequency_s_inv', 'energy_exchange_frequency_s_inv'}
    >>> assert all(value.shape == (2,) and np.isfinite(value).all() for value in r.values())

    """
    molecular_density = _real_numeric("molecular_density_m3", molecular_density_m3)
    electron_density = _real_numeric("electron_density_m3", electron_density_m3)
    ion_temperature = _real_numeric("ion_temperature_ev", ion_temperature_ev)
    mass = _real_numeric("mass_ratio", mass_ratio)
    ionization_rate = _real_numeric(
        "ionization_rate_coefficient_m3_s", ionization_rate_coefficient_m3_s
    )
    reaction_rates = _real_numeric("reaction_rate_table_m3_s", reaction_rate_table_m3_s)
    loss_frequency = _real_numeric("loss_frequency_s_inv", loss_frequency_s_inv)
    nx = molecular_density.size
    valid = (
        molecular_density.ndim == 1
        and nx > 0
        and electron_density.shape == (nx,)
        and ion_temperature.shape == (nx,)
        and mass.ndim == 0
        and np.isfinite(mass)
        and float(mass) > 0.0
        and ionization_rate.shape == (nx,)
        and reaction_rates.ndim == 2
        and reaction_rates.shape == (nx, 11)
        and loss_frequency.shape == (nx,)
        and all(
            np.all(np.isfinite(value))
            for value in (
                molecular_density,
                electron_density,
                ion_temperature,
                ionization_rate,
                reaction_rates,
                loss_frequency,
            )
        )
        and np.all(molecular_density >= 0.0)
        and np.all(electron_density >= 0.0)
        and np.all(ion_temperature > 0.0)
        and np.all(ionization_rate >= 0.0)
        and np.all(reaction_rates >= 0.0)
        and np.all(loss_frequency >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal molecular-ion inputs must be finite, shape-compatible, and physically nonnegative"
        )

    electron_loss_channels = reaction_rates[:, 7:11]
    electron_loss_frequency = electron_density * np.sum(electron_loss_channels, axis=1)
    energy_exchange_frequency = (7.7e-7 * electron_density * 1.0e-6) / (
        np.sqrt(float(mass)) * (ion_temperature**1.5)
    )
    density_denominator = electron_loss_frequency + loss_frequency
    if not np.all(np.isfinite(density_denominator)) or np.any(density_denominator <= 0.0):
        raise ValueError(
            "terminal molecular-ion reduction requires strictly positive molecular-ion density denominator"
        )
    molecular_ion_density = (
        molecular_density * electron_density * ionization_rate / density_denominator
    )
    temperature_denominator = energy_exchange_frequency + density_denominator
    if not np.all(np.isfinite(temperature_denominator)) or np.any(temperature_denominator <= 0.0):
        raise ValueError(
            "terminal molecular-ion reduction requires strictly positive temperature denominator"
        )
    molecular_ion_temperature = (
        ion_temperature * energy_exchange_frequency / temperature_denominator
    )
    values = (
        molecular_ion_density,
        molecular_ion_temperature,
        electron_loss_frequency,
        energy_exchange_frequency,
    )
    if not all(np.all(np.isfinite(value)) and np.all(value >= 0.0) for value in values):
        raise ValueError("terminal molecular-ion reduction produced an invalid profile")
    return {
        "molecular_ion_density_m3": molecular_ion_density,
        "molecular_ion_temperature_ev": molecular_ion_temperature,
        "electron_loss_frequency_s_inv": electron_loss_frequency,
        "energy_exchange_frequency_s_inv": energy_exchange_frequency,
    }
