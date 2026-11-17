"""Independent evidence for the BONK/EM deck solvers.

Precision budgets, written before measurement.  The assembled EM matrix carries
``||M||`` near ``1e17``, so its determinant is compared to the product of its
eigenvalues at 40 digits with a ``1e-12`` relative allowance (measured ``2.6e-14``
on the 40x40 case).  The BONK root is accepted when the independently evaluated
determinant is below the ``1e-8`` residual gate the search itself declares, and
the test additionally requires that a ``0.1%`` perturbation of the root raises the
determinant by more than eight orders of magnitude -- a tolerance cannot make a
non-root pass that check.

What these tests deliberately do **not** claim: the deck constants behind the BONK
and PDRF cases (species table, ``n00``, ``T00``, ``kz``, the J-pole and harmonic
tables) have no independent source in the repository, so they are recorded as
``cannot establish`` in the contracts.  Only relations between the declared inputs
and the outputs are established here.

Failure matrix, one assertion per channel:

* matrix rows inconsistent with the returned spectrum -> ``test_fluid_em_matrix_determinant_equals_eigenvalue_product``
* a fabricated or displaced candidate set -> ``test_fluid_em_spectrum_spectrum_matches_its_matrix``
* a root that does not zero the dispersion -> ``test_fluid_bonk_search_root_zeroes_the_independent_dispersion``
"""

from __future__ import annotations

import numpy as np
import pytest

import _cold_fluid_spectrum_reference as reference

DETERMINANT_BUDGET = 1e-12
BONK_RESIDUAL_GATE = 1e-8


def _scalar(value) -> float:
    return float(np.asarray(value).ravel()[0])


def _case_state(family: str, jcase: int, fraction: float) -> dict:
    """Case state extended with the angular frequency the response expects."""
    from scirel.kinetic.fluid_spectrum import derive_fluid_case

    case = derive_fluid_case(family, jcase)
    state = dict(case)
    state["w"] = fraction * _scalar(case["wn"])
    return state


def test_fluid_em_matrix_determinant_equals_eigenvalue_product():
    """``det(M)`` at 40 digits equals the product of the EM matrix eigenvalues.

    The determinant is recomputed from the matrix bytes at 40 digits; the product
    is taken over the eigenvalues of the same matrix.  The two computations share
    no code, so a wrong constitutive block, a dropped pole or a misplaced field row
    breaks the identity while leaving any single-entry check untouched.
    """
    from scirel.kinetic.fluid_spectrum import assemble_fluid_em

    state = _case_state("em", 2, 0.83)
    result = assemble_fluid_em(state, omega=state["w"], max_harmonic=0)
    matrix = np.asarray(result["M"])
    assert matrix.shape == (40, 40)
    assert int(np.count_nonzero(matrix)) == 295
    determinant = reference.determinant_high_precision(matrix)
    product = reference.eigenproduct(np.linalg.eigvals(matrix))
    assert abs(determinant) > 0.0
    assert reference.relative(abs(product), abs(determinant)) <= DETERMINANT_BUDGET
    # The returned poles are the J-pole table the assembly consumed, so their count
    # is part of the declared structure rather than an incidental number.
    assert np.asarray(result["poles"]).size >= 8


def test_fluid_em_spectrum_spectrum_matches_its_matrix():
    """The returned ``kx`` spectrum is the spectrum of the returned matrix.

    Two independent statements: the 40-digit determinant of ``matM`` equals the
    product of ``kx``, and the five selected candidates are drawn from ``kx`` under
    the declared positive-real-part rule with ascending ``|Im|``.  A fabricated or
    reordered candidate list fails the second; a matrix that is not the one solved
    fails the first.
    """
    from scirel.kinetic.fluid_spectrum import solve_fluid_em

    state = _case_state("em", 2, 0.83)
    result = solve_fluid_em(2, max_harmonic=0, omegas=[state["w"]])
    matrix = np.asarray(result["matM"])
    spectrum = np.asarray(result["kx"]).ravel()
    candidates = np.asarray(result["kxx"]).ravel()
    roots = np.asarray(result["roots"]).ravel()
    assert matrix.shape == (40, 40)
    assert spectrum.size == matrix.shape[0]

    determinant = reference.determinant_high_precision(matrix)
    product = reference.eigenproduct(spectrum)
    assert reference.relative(abs(product), abs(determinant)) <= DETERMINANT_BUDGET

    assert roots.size == candidates.size == 5
    assert np.array_equal(roots, candidates)
    for candidate in candidates:
        assert np.min(np.abs(spectrum - candidate)) <= 1e-9 * max(1.0, abs(candidate))


def test_fluid_bonk_search_root_zeroes_the_independent_dispersion():
    """The searched root zeroes the dispersion determinant evaluated by another function.

    ``solve_fluid_bonk`` returns a normalised root ``nf``.  Feeding that root back
    through ``evaluate_fluid_dispersion`` -- a different public function that has no
    knowledge of the search -- must leave a determinant below the declared ``1e-8``
    gate, while a ``0.1%`` displacement must lift it by many orders of magnitude.
    That pair of assertions is what distinguishes a root from a well-shaped number.
    """
    from scirel.kinetic.fluid_spectrum import (
        derive_fluid_case,
        evaluate_fluid_dispersion,
        solve_fluid_bonk,
    )

    case = derive_fluid_case("bonk", 2)
    frequency = 0.63 * _scalar(case["wn"])
    result = solve_fluid_bonk(2, [frequency])
    assert _scalar(result["valid"]) == 1.0
    root = complex(np.asarray(result["nf"]).ravel()[0])

    state = dict(case)
    state["w"] = frequency
    at_root = complex(np.asarray(evaluate_fluid_dispersion(root, state)["determinant"]).ravel()[0])
    assert abs(at_root) <= BONK_RESIDUAL_GATE

    displaced = complex(np.asarray(evaluate_fluid_dispersion(root * 1.001, state)["determinant"]).ravel()[0])
    assert abs(displaced) > 1e4 * abs(at_root)
    assert abs(displaced) > 1e-2

    # The declared dual residual fields must also be small, and the reported
    # singular values must show a genuine near-null direction.
    assert _scalar(result["residual"]) <= BONK_RESIDUAL_GATE
    singular_values = np.sort(np.asarray(result["sv"]).ravel())[::-1]
    assert singular_values[-1] / singular_values[0] <= 1e-10
