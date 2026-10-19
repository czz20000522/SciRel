"""Local cold-plasma dielectric tensor.

The relation
------------
Accumulates the Stix cold-plasma scalars ``S``, ``D`` and ``P`` over the species
list with the collision-shifted frequency ``omega + i nu``, then assembles the
coordinate-free tensor

    epsilon_r = S I + (P - S) b b + i D [b]_x

with ``b`` the unit magnetic direction and ``[b]_x`` the real antisymmetric
cross-product matrix.  The returned matrix is the representation, in the
**caller's supplied Cartesian basis**, of that operator built from the supplied
field direction; it is not a hidden field-aligned coordinate transform and not a
field-aligned frame representation, and the caller's basis is the one the field
was supplied in.  The time convention ``exp(-i*omega*t)`` and the model label
``LOCAL_COLD_PLASMA`` are constants of the relation, so the call returns the
tensor and nothing else.  No tolerance, magnitude cutoff, numeric threshold or
dependency is introduced anywhere.

The four species routes
-----------------------
1.  **Declared inert, skipped first.**  ``density_m3 == 0.0`` or
    ``charge_c == 0.0`` is the caller stating that the entry contributes
    nothing.  The skip is decided on those two inputs, before the numerator is
    formed, before the divisor is used, before the field and cyclotron guards
    and before the resonance guard, so such an entry cannot reject a call.  It
    is the only route on which a species leaves the loop without contributing.
2.  **Unrepresentable operands, rejected.**  The numerator ``n * q * q`` is
    rejected when it is not finite; the divisor ``eps0 * m`` is rejected when it
    is not a representable non-zero double.  Both raise the same named class
    with the same message, so which stage fired is not observable.
3.  **Representable operands, zero quotient, rejected.**  A computed
    ``wp2`` of exactly zero is rejected rather than skipped.  An intermediate
    underflow is evidence about the intermediate, not about the result: ``wp2``
    is rescaled by ``1 / omega**2`` before it reaches the Stix scalars, and that
    divisor can itself be subnormal.  At ``density_m3 = 5e-324``,
    ``charge_c = 1.0``, ``mass_kg = 4e11`` the quotient is ``0.0`` while its
    exact value ``1.3950055507265265e-324``, divided by the subnormal
    ``omega**2 = 1e-323``, gives the exact Stix correction
    ``0.14134361358724294`` -- so ``P`` is ``0.8586563864127571`` rather than
    one.  A zero quotient between two representable operands is therefore not a
    negligible contribution, and the reachable band is the positive-subnormal
    numerator over a large divisor: the quotient of two positive subnormal
    doubles is at least the ratio of the smallest to the largest subnormal,
    about ``2.22e-16``, so it cannot round to zero.
4.  **Representable operands, collapsed field or cyclotron, rejected.**  A
    contributing species whose represented field magnitude is zero beside a
    field that is not zero, or whose represented cyclotron term ``q |B| / m``
    is zero beside a non-zero field magnitude, is rejected, because the ``D``
    term it would carry is a representable contribution that this arithmetic
    dropped one stage earlier.

Where the arithmetic is checked, and why it is checked there
------------------------------------------------------------
A species accumulates through five intermediates: the field magnitude, the
plasma contribution ``wp2``, the signed cyclotron term ``Omega_c``, the shifted
frequency ``shifted`` and the Stix denominator ``den``.  Any of them can
overflow to infinity for *finite* inputs, and IEEE arithmetic then turns a real
overflow into a silent ``NaN`` by evaluating ``inf / inf``; any of them can also
collapse to zero from non-zero inputs, and a collapsed *operand* silently
removes a contribution instead of raising.  Each is therefore checked where the
code forms it.

* ``magnitude``: formed by ``np.linalg.norm``, which squares before it sums.  A
  non-zero field whose squares all underflow is not the zero field and is
  rejected.  A finite field whose norm overflows stays finite-vector arithmetic
  and is caught later by the cyclotron or accumulation check.
* ``wp2``: formed in stages, with the numerator and the divisor each checked
  before the division that consumes them, and the quotient checked after it.
  The numerator overflow stage is defensive -- at a charge of electronic
  magnitude no finite density reaches it -- and the reachable routes are the
  numerator underflow, the subnormal-mass divisor and the zero quotient.
* ``Omega_c``, ``shifted``, ``den``: each is used as a divisor or a factor, and
  an infinity in any of them produces ``NaN`` rather than an infinity.  This is
  the *field* overflow route, reachable from about ``1e143 T`` for ``den``.
* the four *products* the Stix divisions consume: ``omega * den``,
  ``cyclotron * wp2``, ``wp2 * shifted`` and ``omega * shifted``.  Each is a
  product of two factors that can be individually representable while the
  product is not.

An intermediate underflow is evidence about the intermediate, not about the
result: a zero at any one of these stages does not by itself say that the
contribution it stands for is negligible, which is why each is checked where the
code forms it and why the check is a rejection rather than a skip.

No magnitude cutoff appears anywhere.  The checks reject only values the
double-precision arithmetic could not represent, so no platform-dependent bound
becomes part of the contract and no threshold is chosen.  One consequence is
worth stating rather than leaving implicit: ``Omega_c`` stays finite up to about
``1e297 T`` while ``Omega_c^2`` overflows from about ``1e143 T``, so between
those magnitudes the denominator is infinite while the *leading-order* tensor is
representable.  That value is an artifact of ``x / inf == 0`` dropping the
species contribution, not an evaluation of it, and the call is rejected.  The
boundary is the arithmetic's own -- ``1e142 T`` is accepted and ``1e143 T`` is
not -- and it is measured by a direct regression rather than asserted.

The zero field
--------------
A genuine zero field is supported and is not a representability failure.  There
the represented field magnitude and the represented cyclotron term are exactly
zero by the intended arithmetic, ``q |B| / m`` is zero because ``|B|`` is zero
and not because a non-zero quotient rounded away, and the tensor collapses to
the isotropic scalar ``P`` times the identity with the off-diagonal term set
exactly to zero.  What the field and cyclotron guards reject is the opposite
state: a field that is *not* the zero field whose represented magnitude has
collapsed, or a non-zero field magnitude beside a cyclotron term that has
collapsed.  The guards are conditioned on the represented field being non-zero,
so the zero-field point, the zero-field collapse to the isotropic tensor, the
inert skip and every ordinary-range result are unchanged.

Hermiticity: what is established, and what is not
-------------------------------------------------
With the signed cyclotron term ``Omega_c = q |B| / m`` and a **contributing**
species, the Stix scalars are

    S = 1 - wp2 * shifted / (omega * den),   P = 1 - wp2 / (omega * shifted),
    D = Omega_c * wp2 / (omega * den),
    shifted = omega + i nu,   den = shifted^2 - Omega_c^2,

so the tensor is

    epsilon_r = S I + (P - S) b b + i D [b]_x

* **Sufficient condition, exact.**  If ``nu == 0`` for every species, ``shifted``
  and ``den`` are real, so ``S``, ``P`` and ``D`` are real.  ``i D [b]_x`` is then
  purely imaginary and antisymmetric, and ``epsilon_r == epsilon_r^H`` exactly --
  at *any* field strength, including a nonzero axial field.  The sign of ``D``
  only selects which of the two conjugate off-diagonal entries carries ``+iD``.
  Measured: ``max |epsilon_r - epsilon_r^H| == 0.0``.

* **The converse does not hold.**  A nonzero collision rate is not by itself
  enough to break Hermiticity.  ``den = (omega^2 - nu^2 - Omega_c^2) + 2 i omega nu``
  acquires an imaginary part, but ``S``, ``P`` and ``D`` are each scaled by
  ``wp2``, so a species with ``n == 0`` or ``q == 0`` moves none of them.
  Measured: with the same electron species and the same ``nu = 1e6 s^-1``,
  setting ``density_m3 = 0`` or ``charge_c = 0`` leaves
  ``max |epsilon_r - epsilon_r^H| == 0.0``.

* **A contributing collisional species does break it.**  With ``n = 1e19 m^-3``,
  ``q = -e``, ``B = 0.3 T``, ``f = 60 MHz`` and ``nu = 1e6 s^-1`` the measured
  deviation is ``1188.0005607305914``, because the scalars become complex: the
  diagonal acquires an imaginary part and the off-diagonal stops being purely
  imaginary.

Resonance contract
------------------
A species whose cyclotron frequency exactly equals the wave frequency drives
``den`` to exactly zero and the tensor is undefined there.  This module **fails
closed** with :class:`ColdPlasmaResonanceError`, a subclass of ``ValueError``.
The singularity test is exact equality on the computed denominator, not a
tolerance, and the rejection is whole-call rather than per-point.  Both
decisions match the retained aorsa3d sibling operator's own contract -- the
``AORSA冷Stix电导张量`` route guards the identical denominator with an exact
``== 0.0`` test and raises ``ValueError``.  That sibling route is a source-project
artifact and is not reachable from the maintained package, so the maintained
tests re-derive its closed form rather than loading it.

A species the caller declares inert -- exactly zero density or exactly zero
charge -- is skipped first, so it cannot reject a call.  The retained dielectric
route has no guard at all and raises ``ZeroDivisionError`` for that species at
resonance; the guard here is therefore not a reproduction of the retained
dielectric route but an explicit extension of the sibling conductivity route's
contract.

Final tensor assembly
---------------------
The final projection does not form ``P-S`` and add it back to ``S``: that
sequence can both overflow and erase a small, finite parallel response.
The parallel weights are exact ratios ``B_i*B_j / sum(B_k**2)`` over the
supplied binary64 field. Perpendicular diagonal weights use the other two
squared components directly, and off-diagonal weights negate the parallel
weight. The Hall term uses the same field norm. Each real/imaginary entry has
the form ``a + b/sqrt(q)`` with exact rational ``a,b,q``. Opposite-sign terms
are rationalized as ``(a*a*q-b*b)/(sqrt(q)*(a*sqrt(q)-b))``: the numerator is
exact and the denominator adds same-sign terms. Only the well-conditioned
square root/divisions use 80-digit Decimal arithmetic, followed by one
binary64 rounding. A genuinely unrepresentable final component rejects the
whole call with ``ColdPlasmaOverflowError``.

The Stix coefficients and their conservative representability guards remain
binary64 and unchanged. Final projection does not recover information already
lost in those coefficients, and a rounded Cartesian matrix can remain
ill-conditioned for a later consumer extracting a much smaller eigenresponse.
This standard-library assembly is not an all-input high-precision plasma
solver. Artificial extreme species establish arithmetic behavior, not physical
applicability of the cold model.

Evidence ceiling
----------------
Establishes the tensor identity, its exact agreement with the retained sibling
conductivity route's closed form under the stated sign convention, the stated
sign convention, the sufficient Hermiticity condition and its counterexample,
the exact resonance rejection contract, and that every accepted call returns a
finite tensor -- the last by the upstream representability checks, stable
final projection across overflow and finite cancellation, and a final finite gate.  It also
establishes that a non-zero field cannot present as an exactly zero cyclotron
term on either route: neither a field whose magnitude the norm rounds to zero
nor a cyclotron term that underflows from finite non-zero ``q``, ``|B|`` and
``m`` reaches the accumulation, so no ``D`` contribution is dropped that way.

It does **not** establish that no other statement in this function can raise
``ZeroDivisionError``, and it does not establish that every arithmetic
intermediate is guarded.  It does **not** establish that the cold-plasma model
is adequate at any particular frequency or collisionality, and it does not
represent the physically correct resonant response, which is a kinetic question.
It also does not establish that the accepted set is the largest one this
relation could be evaluated on: the boundary is the representability of the
intermediates this arithmetic forms in this order, and the band in which an
intermediate collapses while the exact contribution would still be representable
is disclosed rather than closed.  A finite return is not evidence that a call is
inside the relation's scientific domain; see the exact document's
``applicability`` and the maintained test module's envelope statement.  The
saved bundle grants no licence: ``license_status`` is ``pending-human-decision``.
"""
from __future__ import annotations

import math
from fractions import Fraction
from decimal import Context, Decimal, localcontext

import numpy as np

__all__ = [
    "ColdPlasmaOverflowError",
    "ColdPlasmaResonanceError",
    "cold_plasma_dielectric_tensor",
]

VACUUM_PERMITTIVITY = 8.8541878128e-12
TIME_CONVENTION = "exp(-i*omega*t)"
MODEL = "LOCAL_COLD_PLASMA"

# Stable message prefix; the species index is appended.  Tests match the prefix
# so the contract does not depend on the index formatting.
RESONANCE_MESSAGE = "cold-plasma dielectric tensor is singular at the supplied resonance"
OVERFLOW_MESSAGE = (
    "cold-plasma dielectric tensor arithmetic is not representable at the "
    "supplied inputs"
)


class ColdPlasmaResonanceError(ValueError):
    """The cold-plasma dielectric tensor is undefined at an exact resonance.

    Subclasses ``ValueError`` so that callers already treating the operator's
    input rejections as ``ValueError`` keep working unchanged, while callers that
    need to distinguish a resonance from a malformed input can catch this type.
    """


class ColdPlasmaOverflowError(ValueError):
    """A finite input whose guarded arithmetic or final tensor is not representable.

    Distinct from :class:`ColdPlasmaResonanceError` because the cause is
    different and so is the remedy: the resonance is a physical singularity the
    caller must move away from, whereas this rejection says the supplied
    frequency, field or species is too large -- or, for the divisor ``eps0 * m``,
    the quotient ``wp2``, the products the Stix divisions consume and the
    cyclotron term ``q |B| / m``, too small -- for the intermediate arithmetic to
    represent.  The input contract is satisfied -- every value is finite -- so
    the caller's mistake, if any, is magnitude rather than type.  Subclasses
    ``ValueError`` for the same reason as the resonance class.
    """


def _is_finite(value):
    """True when every element of ``value`` is finite (real or complex)."""
    return bool(np.all(np.isfinite(value)))


def _is_representable_product(left, right):
    """True when no element of ``left * right`` is a collapsed product.

    The Stix scalars are accumulated as products divided by products, so a
    multiplication is consumed by a division.  Checking that product *before*
    the division is not an optional refinement of a finiteness check on the
    quotient: a product of two representable non-zero operands that rounds to
    exactly zero makes the division raise an undocumented
    ``ZeroDivisionError``.  That is a representability failure of this
    arithmetic, so it is decided here, on the product the code actually forms.

    The test is deliberately narrow, and it is narrower than "the product is a
    representable non-zero double".  A product is rejected only when

    * either operand is not finite -- every comparison with ``NaN`` is false, so
      an untested ``NaN`` operand would read as representable; or
    * the product is exactly zero while **both** operands are non-zero, which is
      the only way a product can collapse.

    An exactly zero operand is accepted here, because this helper decides the
    collapse of the *product* and not the provenance of its operands.  A
    product that overflows to infinity is accepted too, because that is not a
    division-by-zero failure: ``finite / inf`` is a representable zero and
    ``inf / inf`` is a ``NaN`` that the accumulation check already rejects.
    Rejecting it here would move the accepted set at large field magnitudes,
    where the retained route returns a finite tensor.

    Neither acceptance is a statement that the operand is right.  A zero
    cyclotron operand in particular can mean either a zero field or a
    ``q |B| / m`` that this precision rounded to zero, and this helper cannot
    tell them apart.  That question is decided upstream, by the two field and
    cyclotron guards in :func:`cold_plasma_dielectric_tensor`, which is why no
    contributing species reaches this helper with a cyclotron operand that is
    zero because of an underflow.

    ``denominator`` is an array when the field has a leading shape, so the test
    is elementwise, exactly like the ``== 0.0`` resonance test it follows.  A
    single collapsed element therefore rejects the whole call, which is the same
    whole-call contract the resonance guard uses.

    No tolerance and no magnitude bound is involved -- only exact zero and
    finiteness -- so this rejects exactly the products the double-precision
    arithmetic cannot form as non-zero, and accepts everything else.
    """
    if not _is_finite(left) or not _is_finite(right):
        return False
    product = left * right
    collapsed = np.asarray(product == 0.0) & (np.asarray(left) != 0.0) & (
        np.asarray(right) != 0.0
    )
    return not bool(np.any(collapsed))


def _species_terms(item):
    if not isinstance(item, dict):
        raise ValueError("each species entry must be a mapping")
    if "collision_hz" in item:
        raise ValueError("collision_hz is ambiguous; use collision_rate_s_inv")
    try:
        density = float(item["density_m3"])
        charge = float(item["charge_c"])
        mass = float(item["mass_kg"])
        collision = float(item.get("collision_rate_s_inv", 0.0))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "species entries require density_m3, charge_c, and mass_kg"
        ) from exc
    if (
        not np.all(np.isfinite([density, charge, mass, collision]))
        or density < 0.0
        or mass <= 0.0
        or collision < 0.0
    ):
        raise ValueError(
            "species values must be finite; density/collision nonnegative and mass positive"
        )
    return density, charge, mass, collision



def _assemble_tensor(field, magnitude, stix_s, stix_d, stix_p):
    """Project Stix scalars into the caller basis with stable local arithmetic."""
    # The symmetric projector is evaluated from exact binary64 rationals.  This
    # avoids forming P-S first, which can overflow or erase a small parallel
    # response when the two coefficients are large and close.
    field = np.asarray(field, dtype=float)
    shape = magnitude.shape
    tensor = np.empty(shape + (3, 3), dtype=complex)
    for prefix in np.ndindex(shape):
        s, d, p = (complex(value[prefix]) for value in (stix_s, stix_d, stix_p))
        if s == p and d == 0:
            tensor[prefix] = 0.0
            for axis in range(3):
                tensor[prefix + (axis, axis)] = p
            continue

        components = [Fraction(float(field[prefix + (axis,)])) for axis in range(3)]
        squares = [component * component for component in components]
        norm_squared = sum(squares)
        cross = ((0, -components[2], components[1]),
                 (components[2], 0, -components[0]),
                 (-components[1], components[0], 0))
        sr, si, dr, di, pr, pi = map(
            Fraction, (s.real, s.imag, d.real, d.imag, p.real, p.imag)
        )
        with localcontext(Context(prec=80)):
            def decimal(value):
                return Decimal(value.numerator) / Decimal(value.denominator)

            norm = decimal(norm_squared).sqrt()

            def component(symmetric, hall_numerator):
                if not hall_numerator:
                    return float(symmetric)
                a, b = symmetric, hall_numerator
                if a * b < 0:
                    numerator = a * a * norm_squared - b * b
                    if not numerator:
                        return 0.0
                    value = decimal(numerator) / (
                        norm * (decimal(a) * norm - decimal(b))
                    )
                else:
                    value = decimal(a) + decimal(b) / norm
                return float(value)

            for i in range(3):
                for j in range(3):
                    parallel = components[i] * components[j] / norm_squared
                    perpendicular = (
                        sum(squares[k] for k in range(3) if k != i) / norm_squared
                        if i == j else -parallel
                    )
                    try:
                        real = component(sr * perpendicular + pr * parallel, -di * cross[i][j])
                        imag = component(si * perpendicular + pi * parallel, dr * cross[i][j])
                        tensor[prefix + (i, j)] = complex(real, imag)
                    except OverflowError as error:
                        raise ColdPlasmaOverflowError(
                            f"{OVERFLOW_MESSAGE} (final tensor assembly)"
                        ) from error
    if not _is_finite(tensor):
        raise ColdPlasmaOverflowError(f"{OVERFLOW_MESSAGE} (final tensor assembly)")
    return tensor

def cold_plasma_dielectric_tensor(frequency_hz, magnetic_flux_density_t, species):
    """Return the local cold-plasma relative dielectric tensor.

    The returned matrix is the representation, in the **caller's supplied
    Cartesian basis**, of the coordinate-free operator
    ``S I + (P - S) b b + i D [b]_x`` built from the supplied field direction.
    It is not a field-aligned coordinate transform: with the field along a
    coordinate axis the two descriptions coincide, but for a tilted field the
    matrix entries are basis-dependent and only ``b^H epsilon b == P`` is
    frame-invariant.  The time convention ``exp(-i*omega*t)`` and the model
    ``LOCAL_COLD_PLASMA`` are constants of the relation, so they are stated here
    and in the asset document rather than returned: the call returns the tensor
    and nothing else.

    ``magnetic_flux_density_t`` is a finite array whose last axis is the field
    vector, so any leading shape is accepted.  The returned array has that shape
    plus two trailing tensor axes, and is finite on every accepted call.
    Final projection avoids both overflowing and finite cancellation-prone
    P-S assembly. Exact rational projectors and cancellation-safe 80-digit
    algebraic evaluation round each final real/imaginary part to binary64;
    genuinely unrepresentable final components reject the whole call.

    The returned tensor is **exactly Hermitian at any field strength** whenever
    every species has ``collision_rate_s_inv == 0``.  That is a sufficient
    condition, not an equivalence: a species with zero density or zero charge
    contributes nothing, so a nonzero collision rate on such a species does not
    make the tensor non-Hermitian.  A contributing collisional species does.  See
    the module docstring for the measured deviations.

    A species the caller declares inert -- ``density_m3 == 0.0`` or
    ``charge_c == 0.0`` -- is skipped before the numerator is formed, before the
    divisor check, before the field and cyclotron guards and before the
    resonance guard, so it cannot reject a call at any field value.  That is the
    *only* route on which a species leaves without contributing.  The skip is
    decided on those inputs and not on the product ``n q^2``: two non-zero
    inputs can multiply down to zero, and such a species is *not* inert.  A
    species the caller declared non-zero is rejected with
    :class:`ColdPlasmaOverflowError` when its numerator ``n q^2`` is not finite,
    when its divisor ``eps0 * m`` is not a representable non-zero double, when
    its computed plasma contribution is exactly zero, when the field is not the
    zero field but the represented field magnitude is zero, when the field is
    not the zero field but the represented cyclotron term ``q |B| / m`` is zero,
    and when a product consumed by one of the three Stix divisions is not a
    representable non-zero double.  A genuine zero field is not rejected: there
    the represented field magnitude and the cyclotron term are exactly zero by
    the intended arithmetic, and the call returns the isotropic tensor with the
    off-diagonal term exactly zero.

    A zero quotient is not evidence that the contribution is negligible: ``wp2``
    is rescaled by ``1 / omega**2`` before it reaches the Stix scalars, and that
    denominator can be subnormal too, so the final contribution of a zero
    ``wp2`` can be an ordinary representable number.  Nor is a representable
    factor evidence that the product is representable: ``omega`` and the Stix
    denominator can each be finite and positive while their exact product is
    below the smallest positive subnormal double, so the double product is
    exactly zero and the division would raise ``ZeroDivisionError``.  Nor is a
    zero cyclotron *term* evidence of a zero field: ``q |B| / m`` can round to
    zero from a finite non-zero field, and the ``D`` contribution it would carry
    is then a representable number that this arithmetic dropped.  The boundary
    is therefore a conservative fail-closed one on what this arithmetic can
    represent, not a claim that every rejected input has an unrepresentable
    exact contribution.

    A finite return is not evidence that the call is inside the relation's
    scientific domain: this function implements the local cold-plasma model and
    nothing about it validates that model for the supplied plasma.

    Raises
    ------
    ColdPlasmaResonanceError
        If any **contributing** species makes the Stix denominator exactly zero
        at any field point.  A near-resonant but non-zero denominator is not
        rejected, and a non-contributing species never rejects.
    ColdPlasmaOverflowError
        If the input contract is satisfied but a guarded intermediate of the
        Stix arithmetic or a final tensor component cannot be represented.
        Final assembly uses exact rational field projectors and a stable
        algebraic evaluation of the Hall term with the same field norm; only
        an unrepresentable final component is rejected on that route.  The numerator ``n q^2`` is rejected
        when it is not finite.  The divisor ``eps0 * m`` is rejected when it is
        not a representable non-zero double, which is the subnormal-mass route.
        The plasma contribution ``n q^2 / (eps0 m)`` is rejected when it is not
        finite and when it is **exactly zero**: the quotient can underflow to
        zero while the contribution it stands for is representable, because it is
        divided by ``omega**2`` later.  The field magnitude is rejected when the
        field is not the zero field but its norm is exactly zero, and the
        cyclotron term ``q |B| / m`` is rejected when it is not finite and when
        it is exactly zero beside a non-zero field magnitude.  The shifted
        frequency ``omega + i nu``, the denominator and the accumulated ``S``,
        ``D`` and ``P`` are rejected when they are not finite.  The four products
        the three Stix divisions consume -- ``omega * denominator``,
        ``cyclotron * plasma_frequency_squared``, ``wp2 * shifted`` and
        ``omega * shifted`` -- are rejected when either operand is not finite or
        when the product of two non-zero operands is exactly zero: a
        representable factor does not make the product representable, and a
        collapsed product would otherwise raise an undocumented
        ``ZeroDivisionError`` or silently drop the contribution it carried.  An
        exactly zero operand is not a collapse for the product test, but the
        cyclotron operand is separately required to be non-zero when the field
        is, and a product that overflows to infinity is left to the accumulation
        check below.  A genuine zero field is not one of those failures: the
        represented field magnitude and the cyclotron term are exactly zero
        there by the intended arithmetic, and the call is evaluated rather than
        rejected.  Each of those documented failures is whole-call: it rejects
        the call with the named exception rather than evaluating it, and no
        partial tensor is returned.  That is the coverage this asset's evidence
        audits -- the named operands, the quotient, the field magnitude, the
        cyclotron term and the four products the three Stix divisions consume --
        and it is not a claim that every other statement in the function is
        guarded; the module docstring's evidence ceiling states what is not
        established.
    ValueError
        For malformed inputs, as documented.  In particular a frequency that is
        not finite and strictly positive is rejected before any arithmetic, so
        no accepted call can return a non-finite tensor.
    """
    frequency = float(frequency_hz)
    # Finite first: `omega <= 0.0` is false for NaN and for positive infinity, so
    # a non-finite frequency would otherwise reach the arithmetic and return an
    # all-NaN tensor instead of failing closed.
    if not math.isfinite(frequency) or frequency <= 0.0:
        raise ValueError("positive finite frequency is required")
    omega = 2.0 * math.pi * frequency
    field = np.asarray(magnetic_flux_density_t, dtype=float)
    if field.ndim < 1 or field.shape[-1] != 3 or not np.all(np.isfinite(field)):
        raise ValueError("finite (...,3) magnetic field is required")

    magnitude = np.linalg.norm(field, axis=-1)
    # `np.linalg.norm` squares before it sums, so a non-zero field whose squares
    # all underflow is classified as the zero field: `[5e-324, 0, 0]` T has an
    # exactly representable norm of `5e-324` but a represented norm of `0.0`.
    # The test for "the field is not zero" must not square either -- `5e-324 *
    # 5e-324` is `0.0` as well, so a squared test would be defeated by the same
    # rounding it is looking for -- and it is therefore the exact elementwise
    # comparison against zero.
    field_is_nonzero = np.any(field != 0.0, axis=-1)
    field_magnitude_collapsed = field_is_nonzero & (np.asarray(magnitude) == 0.0)

    shape = magnitude.shape
    stix_s = np.ones(shape, dtype=complex)
    stix_d = np.zeros(shape, dtype=complex)
    stix_p = np.ones(shape, dtype=complex)
    for index, item in enumerate(species):
        density, charge, mass, collision = _species_terms(item)
        # The skip is decided on the *inputs*, not on a computed product.  A
        # species is inert only when the caller says so: `density == 0.0` or
        # `charge == 0.0`.  That has to come first, because the operand and
        # field checks below would otherwise reject an inert species for a mass,
        # a charge or a field it never uses.
        #
        # It must not be decided on `n * q * q` either.  Two non-zero inputs can
        # multiply down to zero -- at `density = 1e308, charge = 5e-324` the
        # product underflows to exactly zero -- and the species is not inert.
        # Skipping it there would silently drop a non-zero contribution.
        if density == 0.0 or charge == 0.0:
            continue
        # The field guard.  A contributing species in a non-zero field whose norm
        # the double arithmetic rounded to zero would otherwise be evaluated as a
        # zero-field point: the direction is the zero vector and the
        # off-diagonal term is forced to zero, so the species contribution is
        # dropped rather than evaluated.
        if bool(np.any(field_magnitude_collapsed)):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        # Formed in stages so that an operand the arithmetic cannot represent is
        # detected where it occurs rather than absorbed or masked further down.
        # `n q^2 / (eps0 m)` can be representable even when the numerator is not,
        # and IEEE would then turn the collapse into a silent zero.
        #
        # The overflow direction is defensive: at a charge of electronic
        # magnitude no finite density reaches it.  The *underflow* direction is
        # reachable, and it is caught at the quotient rather than at the
        # numerator -- see the quotient guard below.
        numerator = density * charge * charge
        if not math.isfinite(numerator):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        # The divisor is checked before the division, for the mirror-image
        # failure.  `mass` is finite and strictly positive, but the *product*
        # `eps0 * m` need not be representable: for a finite subnormal mass it
        # underflows to exactly zero, and the division would then raise an
        # undocumented ZeroDivisionError instead of failing closed.  Like the
        # finiteness checks this is representability, not a magnitude cutoff,
        # and it catches a non-finite mass by the same rule.
        divisor = VACUUM_PERMITTIVITY * mass
        if not math.isfinite(divisor) or divisor == 0.0:
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        plasma_frequency_squared = numerator / divisor
        if not math.isfinite(plasma_frequency_squared):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        # `wp2` is not the last quantity this arithmetic forms.  It is rescaled
        # by `1 / omega**2` -- through `omega * shifted` and `omega * denominator`
        # -- before it reaches `S`, `P` or `D`, and that denominator can itself be
        # subnormal.  So a quotient that underflows to exactly zero here says
        # nothing about the contribution: at `density = 5e-324, charge = 1.0,
        # mass = 4e11` the quotient is `0.0` while its exact value
        # `1.3950055507265265e-324`, divided by the subnormal `omega**2 = 1e-323`,
        # gives the exact Stix correction `0.14134361358724294` and `P` is
        # `0.8586563864127571` rather than one.  An intermediate underflow is
        # evidence about the intermediate, not about the result.
        #
        # The numerator-zero case is subsumed rather than checked separately: a
        # numerator that collapses to zero makes this quotient zero, and a
        # numerator that is not finite was already rejected above.  Both raise
        # the same class with the same message, so no caller can tell which
        # statement fired.
        #
        # No tolerance and no magnitude bound is introduced: the test is exact
        # zero on the value the code actually formed.  The only species that now
        # leaves without contributing is one the caller declared inert, above.
        if plasma_frequency_squared == 0.0:
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        cyclotron = charge * magnitude / mass
        # The field overflow route: an infinite cyclotron term or shifted
        # frequency makes `denominator` infinite, and the accumulation then
        # evaluates `inf / inf` -- a NaN, not an infinity, so the result would be
        # masked rather than obviously wrong.
        if not _is_finite(cyclotron):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        # The cyclotron guard, and the other half of the field correction.  An
        # exactly zero cyclotron term is correct at a zero field, but it is also
        # what `q |B| / m` rounds to when the field is finite and non-zero and
        # the quotient is below the double range: at `frequency_hz = 1e-100 /
        # (2 pi)` with field `[0, 0, 1e-150]` T and a species of density `1e308`,
        # charge `1e-200` C and mass `1.0` kg, the exact cyclotron term is
        # `1e-350` and the represented one is `0.0`.  Every operand and product
        # guard passes there and the returned tensor has `D == 0`, while the
        # exact `D` over the same represented doubles is
        # `1.129409067373019e-131` -- an ordinary representable double.  A zero
        # cyclotron *operand* would make the product guard accept the `D`
        # numerator as representable, so the question is decided here, where the
        # collapse occurs.
        if bool(np.any(np.asarray(cyclotron == 0.0) & np.asarray(magnitude != 0.0))):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        shifted = omega + 1j * collision
        if not _is_finite(shifted):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        denominator = shifted * shifted - cyclotron * cyclotron
        if not _is_finite(denominator):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        # Fail closed on an exact resonance.  Exact equality, not a tolerance: a
        # near-resonant denominator is large but finite and must stay
        # distinguishable from the singular point.  Checked after the finiteness
        # test so an unrepresentable denominator is reported as an overflow
        # rather than as a resonance.
        if np.any(denominator == 0.0):
            raise ColdPlasmaResonanceError(
                f"{RESONANCE_MESSAGE} (species index {index})"
            )
        # Every one of the three Stix scalars is a product divided by a product,
        # and the guards above cover the *factors* of the plasma contribution and
        # the field, not the products.  A factor that is representable does not
        # make the product representable: at `frequency_hz = 2e-109` the product
        # `omega * denominator` is the product of two representable positive
        # doubles whose exact value `1.984e-324` is below the smallest positive
        # subnormal double, so the double product is `0.0` and the divisions
        # would raise an undocumented ZeroDivisionError; when the collapsed
        # product is a *numerator* instead, the division does not raise and the
        # contribution is silently zeroed.
        #
        # Each product is therefore required to be a representable non-zero
        # double *before* the division that consumes it.  The check is exact --
        # zero and finiteness, no tolerance and no bound -- so it fires on the
        # ordinary range nowhere.  A product that overflows to infinity is *not*
        # rejected, because that is not a division-by-zero failure --
        # `finite / inf` is a representable zero and `inf / inf` is a NaN the
        # accumulation check below already rejects -- and rejecting it would move
        # the accepted set at large field magnitudes, where the retained route
        # returns a finite tensor.
        if not _is_representable_product(omega, denominator):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        if not _is_representable_product(cyclotron, plasma_frequency_squared):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        if not _is_representable_product(plasma_frequency_squared, shifted):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        if not _is_representable_product(omega, shifted):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )
        stix_s -= plasma_frequency_squared * shifted / (omega * denominator)
        stix_d += cyclotron * plasma_frequency_squared / (omega * denominator)
        stix_p -= plasma_frequency_squared / (omega * shifted)
        # The scalar-stage statement about the *result*: it requires the three
        # accumulated Stix scalars to be finite, and it is kept because a later
        # change to the guards above must not be able to make the tensor
        # non-finite silently.  It is not a substitute for the guards -- it
        # observes the accumulator after the division, so a quotient that is
        # finite but wrong passes it.
        if not (_is_finite(stix_s) and _is_finite(stix_d) and _is_finite(stix_p)):
            raise ColdPlasmaOverflowError(
                f"{OVERFLOW_MESSAGE} (species index {index})"
            )

    # A zero field has no direction; its response is isotropic and has no Hall
    # term.  A nonzero field whose norm collapsed was rejected above.
    stix_s = np.where(magnitude == 0.0, stix_p, stix_s)
    stix_d = np.where(magnitude == 0.0, 0.0 + 0.0j, stix_d)
    return _assemble_tensor(field, magnitude, stix_s, stix_d, stix_p)
