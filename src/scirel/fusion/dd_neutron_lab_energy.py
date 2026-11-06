"""Non-relativistic DD neutron energy along a laboratory detector ray.

The declared masses and Q value determine the neutron speed ``u`` in the centre
of mass.  A laboratory ray ``n`` requires a neutron velocity ``s*n`` satisfying
``|s*n - V_cm|**2 = u**2``.  Only strictly positive speeds reach the detector.
This single-value operator accepts one distinct positive root and rejects
unreachable rays and rays with two distinct positive roots.

Root signs are classified with the exact rational values of the supplied
binary64 inputs and the declared binary64 constants, including the numerical
``1e-4`` conversion factor.  Decimal arithmetic evaluates the unique root
without subtractive cancellation or an overflowing product of energies.  This
numerical convention does not establish the accuracy of the non-relativistic
model or independently measure the declared constants.  No angular weighting,
reaction rate or neutron transport is computed.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from fractions import Fraction

import numpy as np

__all__ = [
    "ATOMIC_MASS_KG",
    "DD_Q_VALUE_MEV",
    "DEUTERON_MASS_AMU",
    "DETECTOR_NORM_ATOL",
    "HELIUM3_MASS_AMU",
    "NEUTRON_MASS_AMU",
    "calculate_dd_neutron_lab_energy_kev",
]

# Declared model constants; their measurement accuracy is not validated here.
DEUTERON_MASS_AMU = 2.013553212745
NEUTRON_MASS_AMU = 1.008665
HELIUM3_MASS_AMU = 3.01603
ATOMIC_MASS_KG = 1.660539040e-27
MEV_J = 1.60218e-13
DD_Q_VALUE_MEV = 3.27
DETECTOR_NORM_ATOL = 1e-12

NON_REPRESENTABLE_MESSAGE = "the DD neutron lab energy is not representable for these finite inputs"


def _require_representable(value, quantity):
    """Fail closed when a required result is not finite."""
    if not bool(np.all(np.isfinite(value))):
        raise ValueError(f"{NON_REPRESENTABLE_MESSAGE}: {quantity} is not finite")


def _validated_vectors(reactant1_velocity_cm_s, reactant2_velocity_cm_s, detector_unit_vector):
    """Enforce the shape, finiteness and absolute unit-norm input contract."""
    supplied = (reactant1_velocity_cm_s, reactant2_velocity_cm_s, detector_unit_vector)
    if any(np.iscomplexobj(value) for value in supplied):
        raise ValueError("velocity vectors and detector_unit_vector must be real")
    vectors = tuple(np.asarray(value, dtype=float) for value in supplied)
    if any(vector.shape != (3,) or not np.all(np.isfinite(vector)) for vector in vectors):
        raise ValueError(
            "velocity vectors and detector_unit_vector must be finite shape-(3,) vectors"
        )
    if not np.isclose(np.linalg.norm(vectors[2]), 1.0, rtol=0.0, atol=DETECTOR_NORM_ATOL):
        raise ValueError("detector_unit_vector must have unit norm")
    return vectors


def _decimal(value):
    return Decimal(value.numerator) / Decimal(value.denominator)


def _positive_finite_energy(value):
    try:
        result = float(value)
    except OverflowError:
        raise ValueError(
            f"{NON_REPRESENTABLE_MESSAGE}: the laboratory-frame energy in keV is not finite"
        ) from None
    _require_representable(result, "the laboratory-frame energy in keV")
    if result <= 0.0:
        raise ValueError(
            f"{NON_REPRESENTABLE_MESSAGE}: the positive laboratory-frame energy underflows"
        )
    return result


def _unique_lab_energy_kev(centre_velocity, neutron_speed_squared, detector, coefficient):
    """Intersect a velocity sphere with an outgoing ray, with exact root signs.

    Inputs are exact rational velocities, squared CM speed and the coefficient
    converting squared cm/s to MeV.  Keeping the unnormalized ray gives an exact
    discriminant numerator even when its accepted norm differs slightly from one.
    """
    norm_squared = sum(component * component for component in detector)
    projection = sum(v * d for v, d in zip(centre_velocity, detector))
    product = sum(v * v for v in centre_velocity) - neutron_speed_squared
    discriminant = projection * projection - product * norm_squared
    if discriminant < 0:
        raise ValueError("the detector ray has no real outgoing neutron velocity")
    if discriminant == 0:
        if projection <= 0:
            raise ValueError("the detector ray has no strictly positive outgoing speed")
        return _positive_finite_energy(1000 * coefficient * projection * projection / norm_squared)
    if product >= 0:
        if projection <= 0:
            raise ValueError("the detector ray has no strictly positive outgoing speed")
        if product > 0:
            raise ValueError("the detector ray has two distinct positive outgoing speeds")
        # One root is exactly zero, so only the other can reach the detector.
        return _positive_finite_energy(4000 * coefficient * projection * projection / norm_squared)

    # The product of the roots is negative, hence exactly one root is positive.
    # For a negative projection use the product of roots instead of subtracting
    # nearly equal square roots.  All coefficients remain exact until evaluation.
    previous = None
    for precision in (80, 160, 320):
        with localcontext() as context:
            context.prec = precision
            root = _decimal(discriminant).sqrt()
            if projection >= 0:
                speed_squared = (_decimal(projection) + root) ** 2 / _decimal(norm_squared)
            else:
                speed_squared = (
                    _decimal(product) ** 2
                    * _decimal(norm_squared)
                    / (root - _decimal(projection)) ** 2
                )
            energy = 1000 * _decimal(coefficient) * speed_squared
            rounded = float(energy)
        if rounded == previous:
            return _positive_finite_energy(rounded)
        previous = rounded
    raise ValueError("the laboratory-frame energy could not be resolved at bounded precision")


def calculate_dd_neutron_lab_energy_kev(
    *,
    reactant1_velocity_cm_s,
    reactant2_velocity_cm_s,
    detector_unit_vector,
):
    """Return the unique positive DD neutron energy along a laboratory ray.

    Parameters
    ----------
    reactant1_velocity_cm_s : array_like, shape (3,)
        First deuteron velocity in the laboratory Cartesian frame [cm/s].
        Finite and real.
    reactant2_velocity_cm_s : array_like, shape (3,)
        Second deuteron velocity in the same laboratory frame [cm/s]. Finite
        and real.
    detector_unit_vector : array_like, shape (3,)
        Unit direction from the reaction point to the detector [dimensionless].
        The Euclidean norm must be within ``1e-12`` of one; after that gate
        its direction is treated as an exact ray.

    Returns
    -------
    neutron_energy_kev : float
        Unique positive neutron kinetic energy along the detector ray [keV].
        The returned value is finite and strictly positive.

    Raises
    ------
    ValueError
        If an input is non-real, non-finite, not shape ``(3,)``, the detector
        norm is outside the stated gate, the ray has no strictly positive
        speed, the ray has two distinct positive speeds, or the selected
        positive energy cannot be represented as a finite positive float.

    See Also
    --------
    fast_ion_fractional_heating : Evaluate a local fast-ion heating partition.

    Notes
    -----
    For deuteron velocities ``v1`` and ``v2``, let ``V=(v1+v2)/2`` and let
    ``u`` be the centre-of-mass neutron speed obtained from the
    non-relativistic two-body energy balance with the fixed D(d,n)3He mass and
    Q value. Along a detector unit vector ``n``, the laboratory speed ``s``
    satisfies ``|s n - V|^2 = u^2``. Only strictly positive roots reach the
    detector. The function returns only when one distinct positive root
    exists; a zero-speed tangent and two distinct positive roots are not
    single-valued results. No angular weight, reaction rate, transport model
    or empirical clamp is applied.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.fusion import calculate_dd_neutron_lab_energy_kev as energy
    >>> def E(v1, v2, d=(1.0, 0.0, 0.0)):
    ...     return energy(reactant1_velocity_cm_s=v1,
    ...                   reactant2_velocity_cm_s=v2,
    ...                   detector_unit_vector=d)
    >>> assert E((0, 0, 0), (0, 0, 0)) == 2450.47589941598
    >>> v1, v2 = (1.0e8, 0, 0), (5.0e7, 0, 0)
    >>> assert E(v1, v2) > E(v1, v2, (-1, 0, 0)) > 0
    >>> perpendicular = E((1.0e8, 0, 0), (1.0e8, 0, 0), (0, 1, 0))
    >>> assert np.isclose(perpendicular, 2445.2488724565214, rtol=1e-12)
    >>> tiny = (-2165199149.095298, 0, 0)
    >>> assert 0 < E(tiny, tiny) < 1e-24
    >>> assert np.isfinite(E((1.0e150, 0, 0), (0, 0, 0)))
    >>> for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0)):
    ...     try:
    ...         E((3.0e9, 0, 0), (3.0e9, 0, 0), d)
    ...     except ValueError:
    ...         pass
    ...     else:
    ...         raise AssertionError('an ambiguous or unreachable ray must fail')
    >>> for bad in ((2, 0, 0), np.array([1+1j, 0, 0])):
    ...     try:
    ...         E((0, 0, 0), (0, 0, 0), bad)
    ...     except ValueError:
    ...         pass
    ...     else:
    ...         raise AssertionError('the detector contract must be enforced')
    """
    v1, v2, direction = _validated_vectors(
        reactant1_velocity_cm_s, reactant2_velocity_cm_s, detector_unit_vector
    )
    first, second, detector = (
        tuple(Fraction.from_float(float(component)) for component in vector)
        for vector in (v1, v2, direction)
    )
    centre = tuple((x + y) / 2 for x, y in zip(first, second))
    relative_squared = sum((x - y) ** 2 for x, y in zip(first, second))
    mass_d, mass_n, mass_he, mass_unit, mev_j, conversion, q_value = (
        Fraction.from_float(value)
        for value in (
            DEUTERON_MASS_AMU,
            NEUTRON_MASS_AMU,
            HELIUM3_MASS_AMU,
            ATOMIC_MASS_KG,
            MEV_J,
            1.0e-4,
            DD_Q_VALUE_MEV,
        )
    )
    available = mass_d * mass_unit * conversion * relative_squared / (4 * mev_j) + q_value
    coefficient = mass_n * mass_unit * conversion / (2 * mev_j)
    centre_energy = mass_he * available / (mass_n + mass_he)
    if all(component == 0 for component in centre):
        # With zero boost every ray has one positive speed.  Evaluate this
        # closed mass-partition expression in its established floating order.
        try:
            available_float = float(available)
        except OverflowError:
            raise ValueError(
                f"{NON_REPRESENTABLE_MESSAGE}: the available energy is not finite"
            ) from None
        result = HELIUM3_MASS_AMU / (NEUTRON_MASS_AMU + HELIUM3_MASS_AMU) * available_float * 1000.0
        return _positive_finite_energy(result)
    return _unique_lab_energy_kev(centre, centre_energy / coefficient, detector, coefficient)
