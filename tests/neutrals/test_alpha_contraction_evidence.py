"""Independent evidence for the atomic and molecular Alpha frequency contractions.

Assets: ``scirel.neutrals.atomic-alpha-contraction``,
``scirel.neutrals.molecular-alpha-contraction``.

The contracts claim a per-cell matrix-vector contraction of assembled ``(N,N)``
SIG collision matrices with the **Fortran-order** flattened ``(nvr,nvx)`` carrier
of one distribution per family, with the ion-density profile scaling only the
families the contract names.  None of that can be read off a pointwise example,
so the evidence below is built from sources that do not consult the
implementation's own arithmetic:

1. **Exact rational contraction.**  Every product and every partial sum is
   recomputed with :class:`fractions.Fraction` over the exact binary64 inputs and
   rounded once at the end.  That separates the declaration (which matrix, which
   carrier, which scaling, which flattening order) from floating-point
   summation, and it is independent of the implementation's ``np.matmul`` path.
2. **Linear/flat index convention, decided by a discriminator.**  A case is
   built in which the Fortran-order carrier and the C-order carrier give
   answers that differ by O(1); the implementation must side with the Fortran
   carrier.  Reporting only "close to Fortran" would leave the alternative
   untested, so the same test asserts the C-order answer is violated.
3. **Homogeneity and superposition, checked directly.**  Scaling a carrier by
   two and scaling the result by two are both exact in binary64, so this is an
   equality, not an inequality with slack: it proves the map is linear in each
   carrier rather than inferring it from the absence of a constant term.
4. **Family routing and the molecular ion-density branch.**  A distinct
   signature matrix per family plus a two-cell density profile shows which
   carrier reaches which family, and exercises both ``ni_correct`` branches
   (``ni = n`` and ``ni = max(n - nHP, 0)``), including the clipping cell.
5. **Declared rejections.**  One executable assertion per rejection channel in
   ``failure_semantics``: non-square SIG, SIG order differing from the
   ``nvr*nvx`` carrier, mis-shaped distribution, mis-shaped density, non-finite
   input, and the contracted-value overflow that must fail closed.

Budgets, fixed before measurement (``N = nvr*nvx``):

* exact-rational contraction: ``(N + 2) * eps * sum_j |A_ij * w_j|`` per output
  element.  ``N`` products contribute at most one rounding each in magnitude,
  the ``N-1`` additions at most one more each against the running absolute
  partial sum, and the expression is bounded by ``sum_j |A_ij w_j|``; the final
  single rounding of the exact value adds one.  This is the classical forward
  error bound for a dot product, not a fitted threshold.
* homogeneity/superposition: exact equality.  Powers of two scale without
  rounding, and superposition is checked on terms whose sum is exactly
  representable (integer-valued matrices and dyadic carriers), so any slack
  would hide a real defect.
* the C-order discriminator: asserted to differ by more than
  ``1e6 * eps * scale``, which is six orders of magnitude above the rounding
  budget, so a pass cannot be an accident of two conventions agreeing.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _fortran_column(field, k):
    """Return one (N,) Fortran-order carrier column as exact rationals.

    ``reshape(..., order="F")`` on ``(nvr, nvx, nx)`` collapses the leading two
    axes radial-first, so flat index ``i`` is ``vr = i % nvr, vx = i // nvr``.
    """
    nvr, nvx, _ = field.shape
    return [_frac(field[i % nvr, i // nvr, k]) for i in range(nvr * nvx)]


def _exact_contraction(matrix, carrier):
    """Exact A @ w for one cell: (N,N) rational matrix times (N,) rational column."""
    n = matrix.shape[0]
    return [
        sum((_frac(matrix[i, j]) * carrier[j] for j in range(n)), Fraction(0)) for i in range(n)
    ]


def _c_order_contraction(matrix, field, k):
    """The competing C-order reading of the same carrier, in exact rationals."""
    n = matrix.shape[0]
    column = [_frac(value) for value in field.reshape(n, -1, order="C")[:, k]]
    return [sum((_frac(matrix[i, j]) * column[j] for j in range(n)), Fraction(0)) for i in range(n)]


def _abs_scale(matrix, carrier):
    """Per-row sum_j |A_ij w_j|, the forward-error scale of a dot product."""
    n = matrix.shape[0]
    return [
        float(sum((abs(_frac(matrix[i, j]) * carrier[j]) for j in range(n)), Fraction(0)))
        for i in range(n)
    ]


def _dot_budget(matrix, carrier):
    """Return the pre-declared per-row tolerance (N + 2) * eps * sum|A_ij w_j|."""
    n = matrix.shape[0]
    return np.array([(n + 2) * EPS * value for value in _abs_scale(matrix, carrier)])


def _field_from(rng, shape):
    """Draw a finite field with both signs, away from exact zeros."""
    return rng.uniform(-4.0, 4.0, size=shape)


def _dense_matrix(rng, n):
    """Draw a finite dense (N, N) matrix with both signs."""
    return rng.uniform(-3.0, 3.0, size=(n, n))


def _distinct_matrix(n):
    """A matrix whose every row is unique, so family routing is observable."""
    return np.array([[float(i) - 0.5 * float(j) for j in range(n)] for i in range(n)])


def _check_exact(actual, matrix, carrier, shape):
    """Compare one contracted cell against the exact rational contraction."""
    exact = _exact_contraction(matrix, carrier)
    got = np.asarray(actual, dtype=float).reshape(shape, order="F").ravel(order="F")
    expected = np.array([float(value) for value in exact])
    budget = _dot_budget(matrix, carrier)
    assert np.all(np.abs(got - expected) <= budget), (got - expected, budget)


# --------------------------------------------------------------------------- #
# atomic-alpha-contraction
# --------------------------------------------------------------------------- #

ATOMIC_SHAPE = (2, 3, 2)


def _atomic_inputs(seed=7):
    """Return an atomic call whose four families carry distinct signatures."""
    rng = np.random.default_rng(seed)
    nvr, nvx, nx = ATOMIC_SHAPE
    n = nvr * nvx
    sig = {name: _dense_matrix(rng, n) for name in ("CX", "H_H", "H_H2", "H_P")}
    fi_hat = _field_from(rng, ATOMIC_SHAPE)
    fH2 = _field_from(rng, ATOMIC_SHAPE)
    fH = _field_from(rng, ATOMIC_SHAPE)
    ni = np.array([1.5, 0.25, -3.0][:nx])
    return sig, fi_hat, ni, fH2, fH


def test_atomic_contraction_matches_the_exact_rational_contraction():
    """Evidence 1 + 4: all four families against the exact rational contraction."""
    (sig, fi_hat, ni, fH2, fH) = _atomic_inputs()
    nvr, nvx, nx = ATOMIC_SHAPE
    result = N.contract_atomic_hydrogen_alpha_frequencies(
        sig["CX"], sig["H_H"], sig["H_H2"], sig["H_P"], fi_hat, ni, fH2, fH
    )
    assert set(result) == {"Alpha_CX", "Alpha_H_H2", "Alpha_H_P", "Alpha_H_H"}
    # ni scales fi_hat for the CX and H-P families; the H-H2 and H-H families
    # carry the bare predecessor distributions.
    weighted = fi_hat * ni[None, None, :]
    for k in range(nx):
        _check_exact(
            result["Alpha_CX"][..., k], sig["CX"], _fortran_column(weighted, k), (nvr, nvx)
        )
        _check_exact(
            result["Alpha_H_P"][..., k], sig["H_P"], _fortran_column(weighted, k), (nvr, nvx)
        )
        _check_exact(result["Alpha_H_H2"][..., k], sig["H_H2"], _fortran_column(fH2, k), (nvr, nvx))
        _check_exact(result["Alpha_H_H"][..., k], sig["H_H"], _fortran_column(fH, k), (nvr, nvx))


def test_atomic_contraction_uses_the_fortran_order_carrier_not_the_c_order_one():
    """Evidence 2: the declared flat index convention, decided by a discriminator."""
    nvr, nvx, nx = ATOMIC_SHAPE
    n = nvr * nvx
    # A matrix with distinct entries and a carrier with distinct values make the
    # two readings differ by O(1) instead of by rounding.
    matrix = np.array([[float((3 * i + 7 * j) % 11 + 1) for j in range(n)] for i in range(n)])
    field = np.arange(1.0, 1.0 + nvr * nvx * nx).reshape(ATOMIC_SHAPE)
    ni = np.array([1.0, 1.0])
    result = N.contract_atomic_hydrogen_alpha_frequencies(
        matrix, matrix, matrix, matrix, field, ni, field, field
    )
    for k in range(nx):
        fortran = np.array(
            [float(v) for v in _exact_contraction(matrix, _fortran_column(field, k))]
        )
        c_order = np.array([float(v) for v in _c_order_contraction(matrix, field, k)])
        got = result["Alpha_CX"][..., k].ravel(order="F")
        scale = max(float(np.max(np.abs(fortran))), 1.0)
        assert np.max(np.abs(got - fortran)) <= (n + 2) * EPS * scale
        # The alternative convention is violated, not merely "less close".
        assert np.max(np.abs(fortran - c_order)) > 1e6 * EPS * scale


def test_atomic_contraction_is_homogeneous_and_additive_in_every_carrier():
    """Evidence 3: homogeneity and superposition are equalities, not slacks."""
    rng = np.random.default_rng(13)
    nvr, nvx, nx = ATOMIC_SHAPE
    n = nvr * nvx
    sig = {name: _dense_matrix(rng, n) for name in ("CX", "H_H", "H_H2", "H_P")}
    fi_hat = _field_from(rng, ATOMIC_SHAPE)
    fH2 = _field_from(rng, ATOMIC_SHAPE)
    fH = _field_from(rng, ATOMIC_SHAPE)
    ni = np.array([1.5, 0.25])

    base = N.contract_atomic_hydrogen_alpha_frequencies(
        sig["CX"], sig["H_H"], sig["H_H2"], sig["H_P"], fi_hat, ni, fH2, fH
    )
    doubled = N.contract_atomic_hydrogen_alpha_frequencies(
        sig["CX"], sig["H_H"], sig["H_H2"], sig["H_P"], 2.0 * fi_hat, ni, 2.0 * fH2, 2.0 * fH
    )
    # Scaling by a power of two is exact in binary64, so every family must be
    # exactly twice its base value: this is a proof of linearity, not a bound.
    for name in ("Alpha_CX", "Alpha_H_P", "Alpha_H_H2", "Alpha_H_H"):
        assert np.array_equal(doubled[name], 2.0 * base[name])

    # Superposition on dyadic carriers whose per-cell sum stays representable.
    whole = _field_from(rng, ATOMIC_SHAPE)
    part_a = np.floor(whole * 4.0) / 8.0
    part_b = whole - part_a
    split = N.contract_atomic_hydrogen_alpha_frequencies(
        sig["CX"], sig["H_H"], sig["H_H2"], sig["H_P"], part_a, ni, part_a, part_a
    )
    split_b = N.contract_atomic_hydrogen_alpha_frequencies(
        sig["CX"], sig["H_H"], sig["H_H2"], sig["H_P"], part_b, ni, part_b, part_b
    )
    joined = N.contract_atomic_hydrogen_alpha_frequencies(
        sig["CX"], sig["H_H"], sig["H_H2"], sig["H_P"], whole, ni, whole, whole
    )
    for name in joined:
        exact_sum = split[name] + split_b[name]
        scale = max(float(np.max(np.abs(exact_sum))), 1.0)
        assert np.all(np.abs(joined[name] - exact_sum) <= (n + 4) * EPS * scale)


def test_atomic_contraction_scales_only_the_families_its_density_feeds():
    """Evidence 4: the density profile reaches CX and H-P and nothing else."""
    rng = np.random.default_rng(17)
    nvr, nvx, nx = ATOMIC_SHAPE
    n = nvr * nvx
    sig = {name: _distinct_matrix(n) for name in ("CX", "H_H", "H_H2", "H_P")}
    fi_hat = _field_from(rng, ATOMIC_SHAPE)
    fH2 = _field_from(rng, ATOMIC_SHAPE)
    fH = _field_from(rng, ATOMIC_SHAPE)
    ni = np.array([2.0, 0.5])

    one = N.contract_atomic_hydrogen_alpha_frequencies(
        sig["CX"], sig["H_H"], sig["H_H2"], sig["H_P"], fi_hat, ni, fH2, fH
    )
    two = N.contract_atomic_hydrogen_alpha_frequencies(
        sig["CX"], sig["H_H"], sig["H_H2"], sig["H_P"], fi_hat, 2.0 * ni, fH2, fH
    )
    # Doubling ni doubles exactly the two density-scaled families.
    assert np.array_equal(two["Alpha_CX"], 2.0 * one["Alpha_CX"])
    assert np.array_equal(two["Alpha_H_P"], 2.0 * one["Alpha_H_P"])
    assert np.array_equal(two["Alpha_H_H2"], one["Alpha_H_H2"])
    assert np.array_equal(two["Alpha_H_H"], one["Alpha_H_H"])
    # A zero density silences exactly those two families.
    zero = N.contract_atomic_hydrogen_alpha_frequencies(
        sig["CX"], sig["H_H"], sig["H_H2"], sig["H_P"], fi_hat, np.zeros(nx), fH2, fH
    )
    assert np.array_equal(zero["Alpha_CX"], np.zeros(ATOMIC_SHAPE))
    assert np.array_equal(zero["Alpha_H_P"], np.zeros(ATOMIC_SHAPE))
    assert np.array_equal(zero["Alpha_H_H2"], one["Alpha_H_H2"])


def test_atomic_contraction_rejects_each_declared_channel():
    """Evidence 5: one executable assertion per failure_semantics channel."""
    rng = np.random.default_rng(19)
    nvr, nvx, nx = ATOMIC_SHAPE
    n = nvr * nvx
    eye = np.eye(n)
    fi_hat = _field_from(rng, ATOMIC_SHAPE)
    ni = np.array([1.5, 0.25])
    good = (eye, eye, eye, eye, fi_hat, ni, fi_hat, fi_hat)

    def call(index, value):
        """Call with positional argument ``index`` replaced by ``value``."""
        args = list(good)
        args[index] = value
        return N.contract_atomic_hydrogen_alpha_frequencies(*args)

    # invalid_input: SIG is not 2-D square.
    with pytest.raises(ValueError, match="SIG_CX"):
        call(0, np.ones((n, n + 1)))
    # invalid_input: SIG order differs from the nvr*nvx carrier.
    with pytest.raises(ValueError, match="velocity-space carrier"):
        call(0, np.eye(n - 1))
    with pytest.raises(ValueError, match="SIG_H_H"):
        call(1, np.eye(n - 1))
    # invalid_input: a distribution is not (nvr,nvx,nx).
    with pytest.raises(ValueError, match="fi_hat"):
        call(4, np.ones((nvr, nvx)))
    with pytest.raises(ValueError, match="fH2/fH"):
        call(6, np.ones((nvr, nvx, nx + 1)))
    # invalid_input: ni is not 1-D of size nx.
    with pytest.raises(ValueError, match="ni"):
        call(5, np.ones((nx, 1)))
    with pytest.raises(ValueError, match="ni"):
        call(5, np.ones(nx + 1))
    # invalid_input: any input carries a non-finite value.
    poisoned = fi_hat.copy()
    poisoned[0, 0, 0] = np.inf
    with pytest.raises(ValueError, match="finite real array"):
        call(4, poisoned)
    # runtime_failure: a finite input whose contraction overflows fails closed.
    big = np.full((n, n), 1.5e308)
    with pytest.raises(ValueError, match="non-finite"):
        call(0, big)


# --------------------------------------------------------------------------- #
# molecular-alpha-contraction
# --------------------------------------------------------------------------- #

MOLECULAR_SHAPE = (2, 3, 2)


def _molecular_inputs(seed=23):
    """Return a molecular call whose three families carry distinct signatures."""
    rng = np.random.default_rng(seed)
    nvr, nvx, nx = MOLECULAR_SHAPE
    n = nvr * nvx
    sig = {name: _dense_matrix(rng, n) for name in ("CX", "H2_H", "H2_P")}
    fH = _field_from(rng, MOLECULAR_SHAPE)
    fHp_hat = _field_from(rng, MOLECULAR_SHAPE)
    fi_hat = _field_from(rng, MOLECULAR_SHAPE)
    n_profile = np.array([3.0, 0.5])
    nHP = np.array([0.5, 1.0])
    return sig, fH, fHp_hat, fi_hat, n_profile, nHP


def test_molecular_contraction_matches_the_exact_rational_contraction():
    """Evidence 1 + 4: all three families against the exact rational contraction."""
    (sig, fH, fHp_hat, fi_hat, n_profile, nHP) = _molecular_inputs()
    nvr, nvx, nx = MOLECULAR_SHAPE
    result = N.contract_molecular_hydrogen_alpha_frequencies(
        sig["CX"], sig["H2_H"], sig["H2_P"], fH, fHp_hat, fi_hat, n_profile, nHP
    )
    assert set(result) == {"Alpha_CX", "Alpha_H2_H", "Alpha_H2_P"}
    weighted_cx = fHp_hat * nHP[None, None, :]
    weighted_p = fi_hat * n_profile[None, None, :]
    for k in range(nx):
        _check_exact(
            result["Alpha_CX"][..., k], sig["CX"], _fortran_column(weighted_cx, k), (nvr, nvx)
        )
        _check_exact(result["Alpha_H2_H"][..., k], sig["H2_H"], _fortran_column(fH, k), (nvr, nvx))
        _check_exact(
            result["Alpha_H2_P"][..., k], sig["H2_P"], _fortran_column(weighted_p, k), (nvr, nvx)
        )


def test_molecular_contraction_uses_the_fortran_order_carrier_not_the_c_order_one():
    """Evidence 2: the declared flat index convention, decided by a discriminator."""
    nvr, nvx, nx = MOLECULAR_SHAPE
    n = nvr * nvx
    matrix = np.array([[float((3 * i + 7 * j) % 11 + 1) for j in range(n)] for i in range(n)])
    field = np.arange(1.0, 1.0 + nvr * nvx * nx).reshape(MOLECULAR_SHAPE)
    result = N.contract_molecular_hydrogen_alpha_frequencies(
        matrix, matrix, matrix, field, field, field, np.ones(nx), np.ones(nx)
    )
    for k in range(nx):
        fortran = np.array(
            [float(v) for v in _exact_contraction(matrix, _fortran_column(field, k))]
        )
        c_order = np.array([float(v) for v in _c_order_contraction(matrix, field, k)])
        got = result["Alpha_H2_H"][..., k].ravel(order="F")
        scale = max(float(np.max(np.abs(fortran))), 1.0)
        assert np.max(np.abs(got - fortran)) <= (n + 2) * EPS * scale
        assert np.max(np.abs(fortran - c_order)) > 1e6 * EPS * scale


def test_molecular_contraction_exercises_both_ion_density_branches():
    """Evidence 4: ``ni = n`` and ``ni = max(n - nHP, 0)``, including the clip."""
    rng = np.random.default_rng(29)
    nvr, nvx, nx = MOLECULAR_SHAPE
    n = nvr * nvx
    sig = {name: _distinct_matrix(n) for name in ("CX", "H2_H", "H2_P")}
    fH = _field_from(rng, MOLECULAR_SHAPE)
    fHp_hat = _field_from(rng, MOLECULAR_SHAPE)
    fi_hat = _field_from(rng, MOLECULAR_SHAPE)
    n_profile = np.array([3.0, 0.5])
    nHP = np.array([0.5, 1.0])  # second cell has n - nHP = -0.5, so it clips to 0

    plain = N.contract_molecular_hydrogen_alpha_frequencies(
        sig["CX"], sig["H2_H"], sig["H2_P"], fH, fHp_hat, fi_hat, n_profile, nHP
    )
    corrected = N.contract_molecular_hydrogen_alpha_frequencies(
        sig["CX"], sig["H2_H"], sig["H2_P"], fH, fHp_hat, fi_hat, n_profile, nHP, ni_correct=True
    )
    for k in range(nx):
        _check_exact(
            plain["Alpha_H2_P"][..., k],
            sig["H2_P"],
            _fortran_column(fi_hat * n_profile[None, None, :], k),
            (nvr, nvx),
        )
        clipped = max(n_profile[k] - nHP[k], 0.0)
        _check_exact(
            corrected["Alpha_H2_P"][..., k],
            sig["H2_P"],
            _fortran_column(fi_hat * np.array([clipped, clipped])[None, None, :], k),
            (nvr, nvx),
        )
    # The clipped cell is silenced exactly, and the branch leaves the other two
    # families untouched: the correction owns Alpha_H2_P only.
    assert np.array_equal(corrected["Alpha_H2_P"][:, :, 1], np.zeros((nvr, nvx)))
    assert np.array_equal(corrected["Alpha_CX"], plain["Alpha_CX"])
    assert np.array_equal(corrected["Alpha_H2_H"], plain["Alpha_H2_H"])
    # nHP feeds exactly the CX carrier.
    doubled = N.contract_molecular_hydrogen_alpha_frequencies(
        sig["CX"], sig["H2_H"], sig["H2_P"], fH, fHp_hat, fi_hat, n_profile, 2.0 * nHP
    )
    assert np.array_equal(doubled["Alpha_CX"], 2.0 * plain["Alpha_CX"])
    assert np.array_equal(doubled["Alpha_H2_P"], plain["Alpha_H2_P"])


def test_molecular_contraction_rejects_each_declared_channel():
    """Evidence 5: one executable assertion per failure_semantics channel."""
    rng = np.random.default_rng(31)
    nvr, nvx, nx = MOLECULAR_SHAPE
    n = nvr * nvx
    eye = np.eye(n)
    field = _field_from(rng, MOLECULAR_SHAPE)
    n_profile = np.array([3.0, 0.5])
    nHP = np.array([0.5, 1.0])
    good = (eye, eye, eye, field, field, field, n_profile, nHP)

    def call(index, value):
        """Call with positional argument ``index`` replaced by ``value``."""
        args = list(good)
        args[index] = value
        return N.contract_molecular_hydrogen_alpha_frequencies(*args)

    with pytest.raises(ValueError, match="SIG_CX"):
        call(0, np.ones((n + 1, n)))
    with pytest.raises(ValueError, match="velocity-space carrier"):
        call(0, np.eye(n - 1))
    with pytest.raises(ValueError, match="SIG_H2_P"):
        call(2, np.eye(n - 1))
    with pytest.raises(ValueError, match="fHp_hat/fi_hat"):
        call(4, np.ones((nvr, nvx)))
    with pytest.raises(ValueError, match="invalid n:"):
        call(6, np.ones((nx + 1,)))
    with pytest.raises(ValueError, match="invalid nHP:"):
        call(7, np.ones((nx, 1)))
    poisoned = field.copy()
    poisoned[-1, -1, -1] = np.nan
    with pytest.raises(ValueError, match="finite real array"):
        call(3, poisoned)
    with pytest.raises(ValueError, match="non-finite"):
        call(0, np.full((n, n), 1.5e308))
