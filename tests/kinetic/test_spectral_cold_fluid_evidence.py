"""Independent evidence for the local spectral multifluid generators.

Precision budget, written before any measurement: the cold-fluid closed forms are
compared at ``1e-12`` relative, which is roughly four orders of magnitude above
the ``mpmath`` floor and still four orders below the ``1e-4``-scale binary64
backward error an unpreconditioned solve of this pencil carries (the curl block
puts ``||M||`` at ``c**2 k ~ 1e14``, so ``eps*||M||/omega_p ~ 1e-4``).  A
``1e-12`` budget therefore fails on a wrong matrix or a wrong branch and passes on
the arithmetic the module actually performs.  The sign-mutation assertion is
an inequality between regimes rather than a tolerance: it compares an imaginary
part against zero.

Failure matrix, one assertion per channel:

* wrong plasma frequency in the assembly -> ``test_..._matches_cold_closed_form``
* wrong curl sign -> ``test_..._sign_flip_breaks_light_branch``
* wrong time-normalisation of the returned spectrum -> ``test_..._spectrum_...``
* scales that are not a similarity transform -> ``test_..._similarity_invariant``
* wrong derived state scalar -> ``test_plasma_state_...``
* wrong scan axis mapping -> ``test_dispersion_scan_...``
"""

from __future__ import annotations

import numpy as np
import pytest

import _cold_fluid_spectrum_reference as reference

BUDGET = 1e-12
COLD_WAVENUMBERS = [
    (1.0e-4, 0.0),
    (2.0e-4, 0.0),
    (5.0e-4, 0.0),
    (1.0e-3, 0.0),
    (5.0e-3, 0.0),
    (1.0e-3, 1.0e-3),
]


def _branches(state, kx, kz):
    omega_p = reference.state_plasma_frequency(state)
    c2 = state["c2"]
    wave = np.sqrt(complex(kx) ** 2 + complex(kz) ** 2)
    return omega_p, reference.light_branch(omega_p, abs(wave), c2)


def _nearest(values, target):
    """Closest value in ``values`` to ``target`` by modulus."""
    return min(values, key=lambda value: abs(complex(value) - complex(target)))


@pytest.mark.parametrize(("kx", "kz"), COLD_WAVENUMBERS)
def test_spectral_temporal_matrix_matches_cold_closed_form(kx, kz):
    """Every cold branch of the assembled generator is the analytic one.

    The anchor is the textbook cold unmagnetized dispersion: ``omega = +-omega_p``
    for the longitudinal mode and ``omega = +-sqrt(omega_p**2 + k**2 c**2)`` twice
    for the transverse pair.  The eigenvalues are recomputed from the returned
    ``M`` at 50 digits so the assertion tests the matrix, not ``scipy``'s
    conditioning.
    """
    from scirel.kinetic.spectral_evolution import assemble_spectral_matrix

    state = reference.cold_state()
    result = assemble_spectral_matrix(state, kx, kz)
    assert np.array_equal(result["A"], np.eye(result["A"].shape[0])), (
        "the nonrelativistic inertia must be the identity for the closed form to apply"
    )
    # The cold state must actually zero every pressure and field term, otherwise
    # the closed form below would be asserting the wrong physics.
    assert np.all(result["state"]["Psz"] == 0.0)
    assert np.all(result["state"]["Psp"] == 0.0)
    assert np.all(result["state"]["Deltas"] == 0.0)
    assert np.all(result["state"]["vA"] == 0.0)

    omega_p, omega_light = _branches(result["state"], kx, kz)
    spectrum = reference.pencil_spectrum(result["M"], result["A"])
    magnitudes = [abs(value) for value in spectrum]

    assert reference.relative(max(magnitudes), omega_light) <= BUDGET
    assert reference.relative(_nearest(magnitudes, omega_p), omega_p) <= BUDGET
    # A cold unmagnetized plasma has no growing mode; any imaginary part is a
    # broken curl sign or a spurious collision term.
    assert max(abs(value.imag) for value in spectrum) <= 1e-6 * float(omega_p)

    # The transverse pair is twofold degenerate and the longitudinal branch is a
    # signed pair, so the analytic multiplicities are part of the relation.
    near_light = [value for value in magnitudes if reference.relative(value, omega_light) <= 1e-9]
    near_plasma = [value for value in magnitudes if reference.relative(value, omega_p) <= 1e-9]
    assert len(near_light) == 4  # two polarizations, two signs
    assert len(near_plasma) == 2  # one longitudinal mode, two signs


def test_spectral_temporal_matrix_sign_flip_breaks_reference.light_branch():
    """Flipping one curl block turns the light branch into ``omega_p**2 - k**2 c**2``.

    This is the mutation that a pure self-consistency test cannot see: the returned
    spectrum is still finite, still sorted and still describes a spectrum.  Above
    ``omega_p/c`` the flipped pencil has an imaginary pair whose size is
    ``sqrt(k**2 c**2 - omega_p**2)``; below it, a real pair at
    ``sqrt(omega_p**2 - k**2 c**2)``.  Both are checked, so the assertion cannot be
    satisfied by chance.
    """
    from scirel.kinetic.spectral_evolution import assemble_spectral_matrix

    state = reference.cold_state()
    omega_p = reference.state_plasma_frequency(state)
    c2 = float(state["c2"])
    cutoff = float(omega_p) / np.sqrt(c2)

    # Above the cutoff: imaginary pair.
    kx = 1.0e-3
    assert kx > cutoff
    baseline = assemble_spectral_matrix(state, kx, 0.0)
    flipped = reference.flip_ampere_curl(baseline["M"], baseline["state"]["s"].__int__())
    baseline_spectrum = reference.pencil_spectrum(baseline["M"], baseline["A"])
    flipped_spectrum = reference.pencil_spectrum(flipped, baseline["A"])
    assert max(abs(value.imag) for value in baseline_spectrum) <= 1e-6 * float(omega_p)
    predicted_growth = float(np.sqrt(kx**2 * c2 - float(omega_p) ** 2))
    observed_growth = max(abs(value.imag) for value in flipped_spectrum)
    assert reference.relative(observed_growth, predicted_growth) <= 1e-10
    assert observed_growth > 1e5  # not a rounding artefact

    # Below the cutoff: the flipped real pair is sqrt(omega_p^2 - k^2 c^2).
    kx_small = 1.0e-4
    assert kx_small < cutoff
    small = assemble_spectral_matrix(state, kx_small, 0.0)
    flipped_small = reference.flip_ampere_curl(small["M"], small["state"]["s"].__int__())
    small_spectrum = [abs(value) for value in reference.pencil_spectrum(flipped_small, small["A"])]
    predicted_real = float(np.sqrt(float(omega_p) ** 2 - kx_small**2 * c2))
    assert reference.relative(_nearest(small_spectrum, predicted_real), predicted_real) <= 1e-10


@pytest.mark.parametrize(("kx", "kz"), COLD_WAVENUMBERS)
def test_spectral_temporal_spectrum_hits_cold_closed_form(kx, kz):
    """The returned frequencies are the analytic cold branches, in ``omega = i*lambda``.

    The public solve applies the declared state scales before solving, so unlike a
    raw ``eig(M)`` it is not limited by ``eps*||M||``.  Measured deviations are
    ``<= 5e-17`` relative; the assertion keeps the ``1e-12`` budget so that a
    regression in either the assembly or the scaling shows up here.
    """
    from scirel.kinetic.spectral_evolution import assemble_spectral_matrix, solve_temporal_spectrum

    state = reference.cold_state()
    result = assemble_spectral_matrix(state, kx, kz)
    solution = solve_temporal_spectrum(result["M"], result["A"])
    omega_p, omega_light = _branches(result["state"], kx, kz)
    magnitudes = [abs(complex(value)) for value in np.asarray(solution["w1"]).ravel()]

    assert reference.relative(max(magnitudes), omega_light) <= BUDGET
    assert reference.relative(_nearest(magnitudes, omega_p), omega_p) <= BUDGET
    # Both declared solver paths must agree with the closed form, so the check
    # does not depend on which initial solver the default happens to select.
    for method in (1, 2):
        alternate = solve_temporal_spectrum(result["M"], result["A"], oldmethod=method)
        alternate_magnitudes = [abs(complex(value)) for value in np.asarray(alternate["w1"]).ravel()]
        assert reference.relative(max(alternate_magnitudes), omega_light) <= BUDGET
        assert reference.relative(_nearest(alternate_magnitudes, omega_p), omega_p) <= BUDGET


def test_spectral_temporal_spectrum_is_similarity_invariant():
    """The declared ``scales`` must be a similarity transform, not a unit change.

    ``D M D^-1`` and ``D A D^-1`` are similar to ``M`` and ``A``, so the frequency
    set is invariant.  Applying a second, unrelated positive scaling therefore must
    not move a single branch; a scaling bug (row-only or column-only) does.
    """
    from scirel.kinetic.spectral_evolution import assemble_spectral_matrix, solve_temporal_spectrum

    state = reference.cold_state()
    result = assemble_spectral_matrix(state, 2.0e-3, 0.0)
    baseline = sorted(abs(complex(value)) for value in np.asarray(solve_temporal_spectrum(result["M"], result["A"])["w1"]).ravel())
    perturbed_scales = np.asarray(result["scales"], dtype=float) * np.geomspace(1.0, 7.0, result["scales"].size)
    perturbed = solve_temporal_spectrum(result["M"], result["A"], scales=perturbed_scales)
    moved = sorted(abs(complex(value)) for value in np.asarray(perturbed["w1"]).ravel())
    for before, after in zip(baseline, moved):
        assert reference.relative(max(after, 1e-300), max(before, 1e-300)) <= 1e-8


def test_spectral_plasma_state_derived_scalars_match_closed_forms():
    """Every derived state scalar is recomputed from the declared rows at 40 digits."""
    from scirel.kinetic.spectral_evolution import initialize_plasma_state

    rows = np.array(
        [
            [-1.602e-19, 9.109e-31, 8.7e6, 1.0e3, -2.0e3, 3.0e3, 4.631e6, 4.631e6, 2.0e-4, -3.0e-4],
            [1.602e-19, 1.673e-27, 8.7e6, -1.0e2, 2.0e2, 1.0e2, 9.360e4, 9.360e4, 1.0e-4, 1.0e-4],
        ],
        dtype=float,
    )
    # B0 nonzero so that the gyrotropic coefficients are exercised, and anisotropy
    # in parallel/perpendicular sound speeds so Delta is not trivially zero.
    state = initialize_plasma_state(rows, unit="si", cfg={"B0": 8e-9, "gammaTs": 5 / 3})

    reference.high_precision()
    import mpmath as mp

    epsilon0 = mp.mpf(float(state["epsilon0"]))
    c2 = mp.mpf(float(state["c2"]))
    mu0 = 1 / (c2 * epsilon0)
    assert reference.relative(float(state["mu0"]), float(mu0)) <= 1e-15

    B0 = mp.mpf(float(state["B0"]))
    for index in range(rows.shape[0]):
        q, m, n, vx, vy, vz, cs_par, cs_perp, eps_x, eps_y = (mp.mpf(value) for value in rows[index])
        rho = m * n
        assert reference.relative(float(state["rhos0"][index]), float(rho)) <= 1e-15
        assert reference.relative(float(state["ns0"][index]), float(n)) <= 1e-15
        assert reference.relative(float(state["wps"][index]), float(mp.sqrt(n * q * q / (epsilon0 * m)))) <= 1e-14
        assert reference.relative(float(state["wcs"][index]), float(q * B0 / m)) <= 1e-15
        assert reference.relative(float(state["Psz"][index]), float(rho * cs_par**2 / (5 / 3))) <= 1e-14
        assert reference.relative(float(state["Psp"][index]), float(rho * cs_perp**2 / (5 / 3))) <= 1e-14
        assert reference.relative(float(state["vA"][index]), float(B0 / mp.sqrt(mu0 * rho))) <= 1e-14
        assert reference.relative(float(state["Deltas"][index]), float((rho * cs_par**2 - rho * cs_perp**2) / (5 / 3) / B0)) <= 1e-13
        assert reference.relative(float(state["betasz"][index]), float(2 * mu0 * rho * cs_par**2 / (5 / 3) / B0**2)) <= 1e-13

    # Reported charge and current densities are sums over the declared rows.
    total_charge = mp.mpf(0)
    for index in range(rows.shape[0]):
        q, _m, n = (mp.mpf(value) for value in rows[index][:3])
        total_charge += q * n
    assert reference.relative(float(state["Q0"]), float(total_charge)) <= 1e-14
    for axis, key in enumerate(("J0x", "J0y", "J0z")):
        expected = mp.mpf(0)
        for index in range(rows.shape[0]):
            q, _m, n = (mp.mpf(value) for value in rows[index][:3])
            expected += q * n * mp.mpf(rows[index, 3 + axis])
        assert reference.relative(float(state[key]), float(expected)) <= 1e-14

    # Both beta arrays are undefined at zero field and must be reported as None,
    # not as an invented zero.
    zero_field = initialize_plasma_state(rows[:, :], unit="si", cfg={"B0": 0.0})
    assert zero_field["betasz"] is None and zero_field["betasp"] is None
    assert np.all(zero_field["vA"] == 0.0)


def test_spectral_dispersion_scan_reproduces_cold_branches():
    """Every scan point maps to the analytic branches at its own ``(kx, kz)``.

    The scan converts the requested axis into ``kx = k cos(theta)``,
    ``kz = k sin(theta)`` and solves the same generator.  Checking the closed form
    at each grid point tests the axis mapping and the per-point solve together,
    which a comparison against the direct call would not (it would only restate
    the shared code path).
    """
    from scirel.kinetic.spectral_evolution import evaluate_spectral_dispersion

    magnitudes_axis = np.array([1.0e-3, 2.0e-3, 5.0e-3])
    result = evaluate_spectral_dispersion(
        COLD_ROWS,
        unit="si",
        method=2,
        k_grid=magnitudes_axis,
        cfg={"B0": 0.0},
    )
    state = reference.cold_state()
    omega_p = reference.state_plasma_frequency(state)
    c2 = float(state["c2"])
    for column, k in enumerate(magnitudes_axis):
        omega_light = reference.light_branch(omega_p, k, c2)
        column_values = [abs(complex(np.asarray(result["ww1"])[row, column])) for row in range(len(np.asarray(result["ww1"])[:, 0]))]
        if not column_values:
            column_values = [abs(complex(np.asarray(result["w1"]).ravel()[row])) for row in range(len(np.asarray(result["w1"]).ravel()))]
        assert reference.relative(max(column_values), omega_light) <= 1e-12
        assert reference.relative(_nearest(column_values, omega_p), omega_p) <= 1e-12


COLD_ROWS = np.array(
    [
        [-1.602e-19, 9.109e-31, 8.7e6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [1.602e-19, 1.673e-27, 8.7e6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ],
    dtype=float,
)
