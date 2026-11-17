"""Independent evidence for the six multifluid declarative assets.

Assets: ``scirel.kinetic.multifluid-deck``, ``multifluid-equilibrium``,
``multifluid-frequency-pencil``, ``multifluid-frequency-solve``,
``multifluid-relative-rate-equilibrium`` and ``multifluid-scan``.

Evidence sources, none of them the implementation or its fixtures:

1. **The SI definitions, evaluated at 40 digits.**  ``omega_p = sqrt(n q**2 /
   (epsilon0 m))``, ``Omega = q B0 / m``, ``rho = sum_s m_s n_s``,
   ``rho_q = sum_s q_s n_s`` and ``J_k = sum_s q_s n_s v_{s,k}`` are recomputed
   from the *named* state entries.  No column index of the deck is assumed: an
   earlier draft of the companion rational batch guessed a column layout and was
   disproved at run time, so this file only uses entries whose names state their
   meaning.
2. **The definition of a generalized eigenvalue.**  For every returned ``omega``
   the pencil ``M - lambda A`` with ``lambda = -i omega`` must be singular, and
   the returned eigenvector must satisfy ``(M - lambda A) x ~ 0``.  This is the
   definition, not a second solver: the pencil's ``A`` is singular on the
   electrostatic support (the implementation documents a support decomposition
   for that reason), so a naive dense ``eig(M, A)`` is ill-conditioned there --
   measured at ~1e-4 relative on the default case -- and is therefore **not**
   used as an oracle.
3. **Two orderings of one spectrum.**  ``w1`` is sorted by descending real part
   and ``w2`` by descending imaginary part; they are the same multiset of
   values, which is an algebraic claim about the returned arrays alone.
4. **Conditioning scales do not move the answer.**  ``state_scales`` is
   documented as a numerical-conditioning device, so tripling it must leave the
   spectrum unchanged.
5. **The scan is the point solve.**  Every scan point carries the full solution
   of the same pencil at that wavevector, so the two must agree.
6. **The Maxwell blocks are one curl operator up to ``c2``.**  The two
   electromagnetic coupling blocks of the pencil are checked against each other:
   the upper-right block must equal ``-c2`` times the lower-left one, with ``c2``
   the state's own named field, and each block must be the ``-1j`` multiple of an
   antisymmetric matrix.  This is an internal relation between two blocks of the
   returned matrix plus one named state field, so it does not depend on the
   solver; it is the anchor that sees a sign flip *inside* the field coupling,
   which the residual tests cannot because they are self-consistent.
7. **The deck reaches the pencil.**  Scaling the state's density column scales
   ``omega_p`` by the square root of the factor -- a relation that a hard-coded
   constant cannot reproduce.

Precision budgets, fixed before the comparison was run:

* SI definitions: ``32 eps`` relative.  Each is a product/quotient of exact
  float entries plus one square root, so a few ulp is the floor; the same budget
  is used to *discriminate* -- the state is also scaled by four and the wrong
  scaling law is required to exceed it.
* Eigenvalue residual: ``sigma_min(M - lambda A) / ||M - lambda A|| <= 1024 eps``.
  For an exact eigenvalue the numerator is at the rounding floor (measured
  ``2.5e-24`` on the default case, i.e. ``1e-8 eps``); 1024 eps is the
  cancellation allowance of a 14x14 pencil whose entries span ~1e5.  The
  discrimination on this statistic is a **factor-10 floor**, not an
  order-of-magnitude claim: displacing one root by one per cent raises the
  smallest singular value by only ~40x, because at 14x14 with fourteen
  eigenvalues the smallest singular value of a near-singular pencil is dominated
  by its other near-null directions.  The floor still fails a value that is not
  in the spectrum at all.
* Eigenvector residual: the same 1024 eps, normalised by ``||M - lambda A||`` and
  ``||x||``.
* Ordering multiset identity: zero tolerance on the values (the two arrays hold
  the same numbers, so any difference is a real difference).
* Scale invariance: ``1024 eps`` relative on the largest magnitude, because the
  scaled and unscaled solves are two different floating-point paths.
* Scan composition: ``1024 eps`` relative for the same reason.

What is deliberately **not** established: the numerical contents of the packaged
SI example deck.  Its species data (charges, masses, densities, temperatures,
drift, transport coefficients) are an external case declaration copied from the
source implementation, so the two deck-facing contracts record that part as
``cannot establish`` while the relations *among* the fields are established
here.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.testing import assert_allclose
from scirel.kinetic.dispersion.multifluid import (
    fluid_deck,
    fluid_equilibrium_relative_rates,
    fluid_equilibrium_si,
    fluid_frequency_pencil,
    fluid_solve_state,
    scan_fluid_corrected,
)

import _fluid_pencil_reference as reference

EPS = reference.EPS

BUDGET = 1024 * EPS
KX, KZ = 1e-5, 2e-5


def test_pencil_carries_the_si_plasma_and_gyro_frequencies():
    """``wps`` and ``wcs`` are the 40-digit definitions of the state's own columns."""
    state = fluid_equilibrium_si()
    pencil = fluid_frequency_pencil(state, KX, KZ)
    expected_plasma = reference.plasma_frequencies(state)
    expected_gyro = reference.gyro_frequencies(state)
    assert_allclose(
        pencil["wps"], expected_plasma, rtol=0, atol=32 * EPS * np.abs(expected_plasma).max()
    )
    assert_allclose(
        pencil["wcs"], expected_gyro, rtol=0, atol=32 * EPS * np.abs(expected_gyro).max()
    )
    # Discrimination: the mass and charge roles are not interchangeable and the
    # plasma frequency is not linear in the density.
    assert not np.allclose(expected_plasma, expected_gyro, rtol=1e-3, atol=0)
    scaled = dict(state)
    scaled["n"] = np.asarray(state["n"], dtype=float) * 4.0
    scaled_pencil = fluid_frequency_pencil(scaled, KX, KZ)
    assert_allclose(
        scaled_pencil["wps"],
        2.0 * expected_plasma,
        rtol=0,
        atol=32 * EPS * np.abs(expected_plasma).max() * 4,
    )
    assert not np.allclose(scaled_pencil["wps"], 4.0 * expected_plasma, rtol=1e-6, atol=0)


def test_pencil_dimension_and_layout_follow_the_species_count():
    """``d = 4 S + 6`` and every returned array is a finite ``(d, d)`` or ``(S,)`` block."""
    state = fluid_equilibrium_si()
    species = np.atleast_1d(np.asarray(state["n"], dtype=float)).size
    pencil = fluid_frequency_pencil(state, KX, KZ)
    dimension = 4 * species + 6
    for name in ("M", "A"):
        matrix = np.asarray(pencil[name])
        assert matrix.shape == (dimension, dimension), (name, matrix.shape)
        assert np.isfinite(matrix).all(), name
    for name in ("wps", "wcs"):
        assert np.asarray(pencil[name]).shape == (species,), name
    # A complex wavevector is documented as supported: the pencil stays finite
    # and keeps its shape rather than silently taking the real part.
    complex_pencil = fluid_frequency_pencil(state, KX + 1e-7j, KZ - 2e-7j)
    assert np.asarray(complex_pencil["M"]).shape == (dimension, dimension)
    assert np.isfinite(np.asarray(complex_pencil["M"])).all()


def test_every_returned_frequency_is_an_eigenvalue_of_the_returned_pencil():
    """``sigma_min(M - lambda A)`` and the eigenvector residual are at the rounding floor."""
    state = fluid_equilibrium_si()
    solution = fluid_solve_state(state, KX, KZ)
    matrix = np.asarray(solution["M"])
    inertia = np.asarray(solution["A"])
    omega = np.asarray(solution["w1"])
    worst_value = max(reference.generalized_residual(matrix, inertia, value) for value in omega)
    assert worst_value <= BUDGET, worst_value
    vectors = np.asarray(solution["X1"])
    worst_vector = max(
        reference.eigenvector_residual(matrix, inertia, omega[index], vectors[:, index])
        for index in range(omega.size)
    )
    assert worst_vector <= BUDGET, worst_vector
    # Discrimination on the same statistic: displacing one root by one per cent
    # must raise the smallest singular value.  The factor is a floor, not an
    # order-of-magnitude claim: at 14x14 with fourteen eigenvalues the smallest
    # singular value of a *near*-singular pencil is dominated by its other
    # near-null directions, so the measured ratio on this case is ~40 and the
    # assertion only requires 10.  A root that is not an eigenvalue at all --
    # e.g. a constant returned in place of the spectrum -- exceeds it by orders
    # of magnitude, which is what the floor is there to catch.
    displaced = omega.copy()
    displaced[0] *= 1.01
    assert reference.generalized_residual(matrix, inertia, displaced[0]) > 10.0 * worst_value


def test_the_two_orderings_hold_the_same_spectrum():
    """``w1`` and ``w2`` are one multiset sorted by real and by imaginary part."""
    solution = fluid_solve_state(fluid_equilibrium_si(), KX, KZ)
    first = np.asarray(solution["w1"])
    second = np.asarray(solution["w2"])
    assert first.shape == second.shape
    assert_allclose(np.sort_complex(first), np.sort_complex(second), rtol=0, atol=0)
    assert np.all(np.diff(first.real) <= 0.0)
    assert np.all(np.diff(second.imag) <= 0.0)


def test_conditioning_scales_do_not_move_the_spectrum():
    """Tripling ``state_scales`` leaves every frequency unchanged."""
    state = fluid_equilibrium_si()
    plain = fluid_solve_state(state, KX, KZ)
    scales = np.asarray(plain["state_scales"], dtype=float)
    rescaled = fluid_solve_state(state, KX, KZ, state_scales=3.0 * scales)
    reference = np.sort_complex(np.asarray(plain["w1"]))
    measured = np.sort_complex(np.asarray(rescaled["w1"]))
    scale = np.abs(reference).max()
    assert_allclose(measured, reference, rtol=0, atol=BUDGET * scale)


def test_scan_points_are_the_point_solves():
    """Each scanned wavevector reproduces the point solution of the same pencil."""
    state = fluid_equilibrium_si()
    scan = scan_fluid_corrected(
        dict(state=state, method=2, grid_controls=dict(scan_k=[1e-5, 2.0e-5]))
    )
    assert scan["axis_names"] == ("k", "theta")
    wave_numbers = np.asarray(scan["axis_values"][0], dtype=float)
    angles = np.asarray(scan["axis_values"][1], dtype=float)
    assert wave_numbers.shape == (2,) and angles.size == 1
    for index, wave_number in enumerate(wave_numbers):
        kx = float(np.asarray(scan["kx"])[index, 0])
        kz = float(np.asarray(scan["kz"])[index, 0])
        point = fluid_solve_state(state, kx, kz)
        reference = np.sort_complex(np.asarray(point["w1"]))
        scanned = np.sort_complex(np.asarray(scan["w1"])[index, 0, :])
        assert_allclose(scanned, reference, rtol=0, atol=BUDGET * np.abs(reference).max())


def test_maxwell_blocks_are_one_curl_operator_up_to_c2():
    """``upper = -c2 * lower`` and both blocks are ``-1j`` times an antisymmetric matrix."""
    state = fluid_equilibrium_si()
    species = np.atleast_1d(np.asarray(state["n"], dtype=float)).size
    c2 = float(np.asarray(state["c2"]).ravel()[0])
    for kx, kz in ((KX, KZ), (-3.5e-5, 1.25e-5)):
        matrix = np.asarray(fluid_frequency_pencil(state, kx, kz)["M"])
        lower, upper = reference.maxwell_blocks(matrix, species)
        scale = np.abs(upper).max()
        assert scale > 0.0
        # The Ampere block is the Faraday block scaled by -c2: the two curls are
        # the same operator.  A sign flip on either block turns the sum below
        # into twice the block instead of zero.
        assert_allclose(upper + c2 * lower, 0.0, rtol=0, atol=32 * EPS * scale)
        assert np.abs(upper + c2 * (-lower)).max() > 0.5 * scale
        # Each block is -1j times a real antisymmetric matrix, i.e. a curl.
        for block in (lower, upper):
            scaled = block * 1j  # (-1j X) * 1j = X
            cap = 32 * EPS * np.abs(block).max()
            assert np.allclose(scaled.imag, 0.0, atol=cap)
            assert_allclose(scaled, -scaled.T, rtol=0, atol=cap)


def test_equilibrium_assembles_the_named_si_moments():
    """``rho``, ``charge_density`` and ``current_density`` are the sums their names state."""
    state = fluid_equilibrium_si()
    # ``rho`` is the per-species mass density m_s n_s; ``charge_density`` and
    # ``current_density`` are the summed moments their names state.  The
    # per-species shape was established by reading the arrays, not assumed.
    expected_rho = reference.per_species_mass_density(state)
    assert_allclose(
        np.asarray(state["rho"], dtype=float).ravel(),
        expected_rho,
        rtol=0,
        atol=32 * EPS * np.abs(expected_rho).max(),
    )
    assert_allclose(
        float(np.asarray(state["charge_density"]).ravel()[0]),
        reference.total_charge_density(state),
        rtol=0,
        atol=32 * EPS * max(abs(reference.total_charge_density(state)), 1e-30),
    )
    expected_current = reference.current_density(state)
    assert_allclose(
        np.asarray(state["current_density"], dtype=float).ravel(),
        expected_current,
        rtol=0,
        atol=32 * EPS * max(np.abs(expected_current).max(), 1e-300),
    )
    species = np.atleast_1d(np.asarray(state["n"], dtype=float)).size
    for name in ("q", "m", "n", "csz2", "csp2", "epsnx", "epsny"):
        assert np.asarray(state[name]).size == species, name
        assert np.isfinite(np.asarray(state[name], dtype=float)).all(), name


def test_relative_rate_equilibrium_is_a_consistent_state_for_the_pencil():
    """The relative-rate construction yields a state the pencil accepts and whose rates conserve the pair."""
    deck = np.asarray(fluid_deck(), dtype=float)
    species = deck.shape[0]
    species_classes = ["electron"] + ["ion"] * (species - 1)
    state = fluid_equilibrium_relative_rates(deck, species_classes=species_classes)
    pencil = fluid_frequency_pencil(state, KX, KZ)
    assert np.isfinite(np.asarray(pencil["M"])).all()
    assert np.asarray(pencil["wps"]).shape == (species,)
    solution = fluid_solve_state(state, KX, KZ)
    matrix = np.asarray(solution["M"])
    inertia = np.asarray(solution["A"])
    worst = max(
        reference.generalized_residual(matrix, inertia, value)
        for value in np.asarray(solution["w1"])
    )
    assert worst <= BUDGET, worst
    # ``velocity_collision`` is a (species, species) rate table on this path.
    # Its layout is read, not assumed: an earlier draft treated it as a velocity
    # generator and the multiplication failed on the shape.
    collision = np.asarray(state["velocity_collision"], dtype=float)
    assert collision.shape == (species, species), collision.shape
    assert np.isfinite(collision).all()


@pytest.mark.parametrize(
    "call, message",
    [
        (lambda: fluid_frequency_pencil(fluid_equilibrium_si(), np.nan, KZ), ""),
        (lambda: fluid_solve_state(fluid_equilibrium_si(), KX, KZ, state_scales=np.zeros(14)), ""),
        (lambda: fluid_solve_state(fluid_equilibrium_si(), KX, KZ, backward_tolerance=-1.0), ""),
        (lambda: scan_fluid_corrected(dict(state=fluid_equilibrium_si(), method=9)), ""),
        (lambda: fluid_solve_state(fluid_equilibrium_si(), KX, KZ, state_scales=np.ones(3)), ""),
    ],
)
def test_each_rejection_channel_has_its_own_assertion(call, message):
    """Every documented failure channel of the six assets is reached by at least one call."""
    with pytest.raises((ValueError, TypeError, ArithmeticError), match=message):
        call()
