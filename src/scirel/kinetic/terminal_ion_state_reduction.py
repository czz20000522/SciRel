"""Terminal H2+ density and temperature from caller-owned state profiles.

The reaction table and frequencies are supplied directly. This relation does
not assemble collision tables or evolve a terminal molecular-ion state.
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
    neutral_density_m3,
    ion_temperature_ev,
    mass_ratio,
    ionization_rate_s_inv,
    reaction_rate_table_s_inv,
    loss_frequency_s_inv,
):
    """Reduce explicit terminal state profiles to H2+ density and temperature diagnostics.

    Parameters
    ----------
    molecular_density_m3 : array_like, shape (nx,)
        Finite nonnegative terminal H2 density. [source-labeled m^-3]
    neutral_density_m3 : array_like, shape (nx,)
        Finite nonnegative neutral density used in dissociation and exchange terms.
        [source-labeled m^-3]
    ion_temperature_ev : array_like, shape (nx,)
        Finite strictly positive ion temperature. [eV]
    mass_ratio : float
        Positive finite source-defined mass factor in the exchange frequency.
        [source-defined dimensionless mass ratio]
    ionization_rate_s_inv : array_like, shape (nx,)
        Finite nonnegative ionization-rate profile. [source-labeled s^-1; density-scaled physical dimension unresolved]
    reaction_rate_table_s_inv : array_like, shape (nx, 11)
        Finite nonnegative reaction channels in source order; columns ``7:11``
        enter dissociation. [source-labeled s^-1; density-scaled physical dimension unresolved]
    loss_frequency_s_inv : array_like, shape (nx,)
        Finite nonnegative loss frequency added to the dissociation denominator.
        [source-labeled s^-1]

    Returns
    -------
    molecular_ion_density_m3 : ndarray, shape (nx,)
        Algebraic terminal H2+ density. [source-labeled m^-3; coefficient units pending review]
    molecular_ion_temperature_ev : ndarray, shape (nx,)
        Algebraic terminal H2+ temperature. [eV]
    dissociation_frequency_s_inv : ndarray, shape (nx,)
        Neutral density times the sum of reaction channels ``7:11``.
        [source-labeled s^-1; coefficient units pending review]
    energy_exchange_frequency_s_inv : ndarray, shape (nx,)
        Source-calibrated exchange frequency with the explicit ``1e-6`` density
        scaling. [source-labeled s^-1]

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
    ``dissociation_frequency`` is the neutral density times the sum of reaction
    channels 7 through 10. The H2+ density uses the ionization numerator divided
    by dissociation plus loss frequency. The temperature uses the exchange
    frequency divided by exchange plus that same denominator. Only channels
    ``7:11`` affect the outputs. The historical input names and source-labeled
    units leave the density-scaled dimensions unresolved; the numerical formulas
    are preserved pending expert unit review, and this relation does not assemble
    collision tables or evolve a terminal state.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import reduce_terminal_molecular_ion_state
    >>> rates = np.zeros((2, 11))
    >>> rates[:, 7:11] = 1e-18
    >>> r = reduce_terminal_molecular_ion_state(np.array([4e17, 5e17]), np.array([1e18, 2e18]), np.array([2., 3.]), 2., np.array([4., 5.]), rates, np.array([1., 3.]))
    >>> assert set(r) == {'molecular_ion_density_m3', 'molecular_ion_temperature_ev', 'dissociation_frequency_s_inv', 'energy_exchange_frequency_s_inv'}
    >>> assert all(value.shape == (2,) and np.isfinite(value).all() for value in r.values())

    """
    molecular_density = _real_numeric("molecular_density_m3", molecular_density_m3)
    neutral_density = _real_numeric("neutral_density_m3", neutral_density_m3)
    ion_temperature = _real_numeric("ion_temperature_ev", ion_temperature_ev)
    mass = _real_numeric("mass_ratio", mass_ratio)
    ionization_rate = _real_numeric("ionization_rate_s_inv", ionization_rate_s_inv)
    reaction_rates = _real_numeric("reaction_rate_table_s_inv", reaction_rate_table_s_inv)
    loss_frequency = _real_numeric("loss_frequency_s_inv", loss_frequency_s_inv)
    nx = molecular_density.size
    valid = (
        molecular_density.ndim == 1
        and nx > 0
        and neutral_density.shape == (nx,)
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
                neutral_density,
                ion_temperature,
                ionization_rate,
                reaction_rates,
                loss_frequency,
            )
        )
        and np.all(molecular_density >= 0.0)
        and np.all(neutral_density >= 0.0)
        and np.all(ion_temperature > 0.0)
        and np.all(ionization_rate >= 0.0)
        and np.all(reaction_rates >= 0.0)
        and np.all(loss_frequency >= 0.0)
    )
    if not valid:
        raise ValueError(
            "terminal molecular-ion inputs must be finite, shape-compatible, and physically nonnegative"
        )

    dissociation_channels = reaction_rates[:, 7:11]
    dissociation_frequency = neutral_density * np.sum(dissociation_channels, axis=1)
    energy_exchange_frequency = (7.7e-7 * neutral_density * 1.0e-6) / (
        np.sqrt(float(mass)) * (ion_temperature**1.5)
    )
    density_denominator = dissociation_frequency + loss_frequency
    if not np.all(np.isfinite(density_denominator)) or np.any(density_denominator <= 0.0):
        raise ValueError(
            "terminal molecular-ion reduction requires strictly positive molecular-ion density denominator"
        )
    molecular_ion_density = (
        molecular_density * neutral_density * ionization_rate / density_denominator
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
        dissociation_frequency,
        energy_exchange_frequency,
    )
    if not all(np.all(np.isfinite(value)) and np.all(value >= 0.0) for value in values):
        raise ValueError("terminal molecular-ion reduction produced an invalid profile")
    return {
        "molecular_ion_density_m3": molecular_ion_density,
        "molecular_ion_temperature_ev": molecular_ion_temperature,
        "dissociation_frequency_s_inv": dissociation_frequency,
        "energy_exchange_frequency_s_inv": energy_exchange_frequency,
    }
