"""Independent original-input evidence for six existing closure relations.

These are bounded mathematical checks, not physical equilibrium or experimental
calibration. References below use only prescribed binary64 inputs, exact rational
arithmetic or 180-digit Decimal arithmetic; production returns/intermediates and
saved source/replay traces never generate the expected values.

Boltzmann electrons and gauge (J, V, m^-3, Pa)
--------------------------------------------
For charge -e, the Maxwell weight is exp[-(m*v**2/2-e*phi)/T_e]. Integrating
velocity and dividing by the reference weight gives
n_e = n_ref*exp[e*(phi-phi_ref)/T_e], with T_e already in joules and
p_e = n_e*T_e. Thus positive potential raises electron density. For
a=Z*n_i and b=n_e, the number-density residual is a-b (not C/m^3),
the log residual is log(a)-log(b), and the relative residual is (a-b)/(a+b).
The independent Decimal reference evaluates these definitions from exact input
floats. Six inputs retain the original ordinary, large common-potential, +/-800
compensated-exponent and opposite-sign 1e308 cases. A common gauge cancels only
while the input difference remains represented. The fixed budget is rtol=3e-13,
atol=0, and log error <=3e-13*max(1, abs(reference)). Exact absence checks only
the declared finite proxy sign/magnitude and exact relative residual, not a
physical infinite logarithm. Spatially varying T_e is a pointwise prescription,
not proof of global thermal equilibrium.

Reference density and monotone potential
---------------------------------------
Single-ion charge balance Z*e*n_i-e*n_e=0 gives n_e=Z*n_i. Fraction multiplies
the exact original float inputs, rounding only the final product. Zero, 2**500,
the least subnormal and permitted underflow are retained, with exact equality;
this neither proves all binary64 products nor multi-ion physics.
For a caller-owned decreasing residual R(phi), lower positive/upper negative
bracket a root. The manufactured R=phi_root-phi is independent of a production
Boltzmann callback. Roots 6.375 and -1.625 retain atol=1e-10 V and the original
residual gate; inactive callbacks retain 17 V. The exact rational root
1+2**-53 lies between adjacent floats 1 and 1+2**-52, so every returned float
has residual magnitude at least 2**-53 > 2**-55. A narrow bracket (width tolerance
2**-50 V) cannot make that residual attainable: RuntimeError is required with
the original 100-iteration limit. Inactive cells still require finite callback
values. Neither these roots nor an exact callback zero validate arbitrary
callback physics, continuity or thermal-scale representability.

Directional two-fluid pressure bookkeeping
-----------------------------------------
For each direction, P_total=P_i+P_e+P_residual. Electrons default to the
prescribed scalar pressure in the ordinary direct tests; the distinct explicit
electron components here require distinct omitted-ion subtractions. The original
binary-fraction profiles give ion parallel 16+2*B+psi and perpendicular
13+B+2*psi, with zero residual. At unit total pressure, 32*eps and 128*eps
perturbations straddle the declared 64*eps comparison in independent_fit and
species_sum modes. These checks verify numerical accounting and exception
propagation, not the pressure law or a force-balanced state. Independent fitted
residual stress is not an additional particle species.

Cylindrical tensor force, Hall projection and ion thermal speed
-------------------------------------------------------------
For poloidal b and delta=p_parallel-p_perpendicular, P=p_perp*I+delta*b*b:
P_RR=p_perp+delta*b_R**2, P_ZZ=p_perp+delta*b_Z**2,
P_RZ=delta*b_R*b_Z, P_phi_phi=p_perp. Hence
F_R=d_R(P_RR)+d_Z(P_RZ)+(P_RR-P_phi_phi)/R and
F_Z=d_R(P_RZ)+d_Z(P_ZZ)+P_RZ/R. Since
J_phi*e_phi cross B=(J_phi*B_Z,-J_phi*B_R),
J_phi=(B_Z*F_R-B_R*F_Z)/B**2 closes only the perpendicular projection.
For b=(3/5,4/5), p_perp=30+2R+3Z and delta=4R+Z, direct differentiation gives
F_R=134/25+9Z/(25R), F_Z=187/25+12Z/(25R).
Electron p_perp=2+R, p_parallel=2+3R give F_e=(61/25,48/25).
With phi=R-2Z, E=(-1,2), n=2 and q=1, the no-inertia, uncapped relation
E+v_i cross B=(J cross B-div(P_e))/(q*n) projected across B gives
J=-1/5, v_i=3/2, v_e=v_i-J/(q*n)=8/5. Its actual Ohm residual is (3/2,2),
not zero. The constant tilted field is an algebraic tensor test with nonzero
cylindrical div(B), not a Maxwell equilibrium. Mask checks keep unmasked force
fields separate from zeroed current/drift/Ohm fields. Fixed rtol=atol=1e-12.

Omitted ion components are p_i,parallel=28+3R+4Z and
p_i,perp=28+R+3Z, so v_th**2=(p_i,parallel+2*p_i,perp)/(3*m*n)
=(84+5R+10Z)/6. Decimal square roots of original coordinates independently
predict gyroradius m*v_th/(q*abs(B)), raw Mach (3/2)/v_th and the cap.
Caps 10 and 1/4 remain two distinct pytest nodes: the latter must actually
limit velocity to v_th/4 and return Mach=1/4. The former must remain uncapped.
This distinguishes ion-only thermal speed even when raw drift is unchanged.
Both keep rtol=atol=1e-12. Density floors and caps are numerical/model controls,
not experimentally established regimes.

The separate divergence-free B_Z=1, isotropic P=20+3R**2, m=n=q=1 case gives
F_R=6R. Radial centrifugal acceleration is -v_phi**2/R, so the local current
map is J=6R-J**2/R. Its positive branch J=2R retains rtol=atol=1e-10 and
inertia_tolerance=1e-10; a one-iteration, 1e-30 residual budget must fail.
No pressure_divergence or production iteration output supplies the reference.
Floating-point budgets do not bound continuous-domain discretization error.

Discrete feedback state timing (T, A, s)
---------------------------------------
At each enabled sample, e_k=reference-measurement,
P_k=Kp*e_k, I_+=I_-+enable_int*Ki*dt*e_k,
D_k=Kd*N*(e_k-f_-), f_+=f_-+N*dt*(e_k-f_-).
Current uses the UPDATED I_+ and the derivative uses OLD f_-; a forward-Euler
state-update label must not move the current back one sample. Kp, Ki, Kd, N
have units 1, s^-1, s, s^-1 if PID/state terms are T; the map is A/T.
The seven-sample exact rational trajectory below fixes all PID components,
current, reset and effective pre/post states, including hold and feedforward
while disabled. For dt=1/4, Kp=2, Ki=3, Kd=1/2, N=2, the first enabled
sample e=1 gives (P,I,D)=(2,3/4,1) after reset; the second gives (2,3/2,1/2).
The two-channel nondiagonal map separately checks axis order and one scale
application with exact Fraction arithmetic. Six invalid-input branches retain
ValueError assertions. These are independent sampled arithmetic references;
existing saved-source tests remain transcription evidence. Native Simulink,
plant dynamics, saturation, stability and calibration remain unestablished.
"""

import copy
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import subprocess
import sys

import numpy as np
import pytest

from scirel.closures import (
    compute_boltzmann_electron_state as boltz,
    compute_reference_electron_density as reference_density,
    solve_quasineutral_potential as potential,
    close_hall_two_fluid_pressure as pressure_state,
    close_reduced_hall_drift as drift,
    simulate_discrete_vector_feedback as feedback,
)

E = 1.602176634e-19  # Declared numerical constant, not imported from production.


BOLTZ_INPUTS = [
    (0.5, E, 3.0, 0.0, 1.5, 2.0),
    (1000000.25, 0.25 * E, 2.0, 1000000.0, 1.0, 3.0),
    (-1000000.5, 0.5 * E, 2.0, -1000000.0, 1.0, 1.0),
    (800.0, E, 1e-300, 0.0, 1e40, 1.0),
    (-800.0, E, 1e300, 0.0, 1e-40, 1.0),
    (1e308, 1e308, 1e-308, -1e308, 1.0, 1.0),
]


def decimal_electron(raw):
    with localcontext() as ctx:
        ctx.prec = 180
        phi, t, n0, phi0, ni, z = map(D.from_float, raw)
        exponent = D.from_float(E) * (phi - phi0) / t
        ne = n0 * exponent.exp()
        pressure = ne * t
        charge = z * ni - ne
        logs = (z * ni).ln() - ne.ln()
        rel = (z * ni - ne) / (z * ni + ne)
        return dict(
            electron_density_m3=float(ne),
            electron_pressure_pa=float(pressure),
            charge_residual_m3=float(charge),
            logarithmic_charge_residual=float(logs),
            relative_charge_residual=float(rel),
        )


@pytest.mark.parametrize("raw", BOLTZ_INPUTS)
def test_boltzmann_from_raw_decimal_maxwell_weight(raw):
    expected = decimal_electron(raw)
    result = boltz(*raw)
    for key in (
        "electron_density_m3",
        "electron_pressure_pa",
        "charge_residual_m3",
        "relative_charge_residual",
    ):
        np.testing.assert_allclose(result[key], expected[key], rtol=3e-13, atol=0.0)
    value = expected["logarithmic_charge_residual"]
    assert abs(float(result["logarithmic_charge_residual"]) - value) <= 3e-13 * max(1.0, abs(value))


@pytest.mark.parametrize("n0,ni,relative", [(0.0, 0.0, 0.0), (0.0, 2.0, 1.0), (2.0, 0.0, -1.0)])
def test_exact_absence_is_diagnostic_not_a_false_root(n0, ni, relative):
    result = boltz(0.0, E, n0, 0.0, ni, 1.0)
    assert float(result["relative_charge_residual"]) == relative
    if relative:
        assert float(result["logarithmic_charge_residual"]) * relative >= 1.0
    else:
        assert float(result["logarithmic_charge_residual"]) == 0.0


def test_boltzmann_true_overflow_and_invalid_temperature_reject():
    with pytest.raises(FloatingPointError):
        boltz(10000.0, E, 1.0, 0.0, 1.0, 1.0)
    with pytest.raises(ValueError):
        boltz(0.0, 0.0, 1.0, 0.0, 1.0, 1.0)


def test_reference_product_fraction_broadcast_and_input_immutability():
    ns = np.array([0.0, 1.0, float.fromhex("0x1p+500"), float.fromhex("0x0.0000000000001p-1022")])
    zs = np.array([[0.5], [1.0], [2.0]])
    n_before, z_before = ns.copy(), zs.copy()
    expected = np.array([[float(F(float(z)) * F(float(n))) for n in ns] for z in zs[:, 0]])
    result = reference_density(ns, zs)
    np.testing.assert_array_equal(result["electron_density_ref_m3"], expected)
    np.testing.assert_array_equal(ns, n_before)
    np.testing.assert_array_equal(zs, z_before)


def test_reference_true_failure():
    with np.errstate(over="ignore"):
        with pytest.raises(FloatingPointError):
            reference_density(float.fromhex("0x1.fffffffffffffp+1023"), 2.0)
    with pytest.raises(ValueError):
        reference_density(1.0, 0.0)


def test_potential_fraction_roots_mixed_mask_and_gauge():
    roots = np.array([6.375, -1.625, 999.0])
    refs = np.array([0.0, 0.0, 17.0])
    calls = []

    def residual(phi):
        calls.append(np.asarray(phi).copy())
        assert phi[2] == 17.0
        return {"logarithmic_charge_residual": roots - phi}

    result = potential(
        refs,
        0.125 * E,
        0.125 * E,
        E,
        [True, True, False],
        residual,
        initial_bracket_thermal=0.1,
        potential_tolerance_v=1e-10,
        quasineutral_tolerance=1e-10,
        max_iterations=150,
    )
    np.testing.assert_allclose(result["potential_v"][:2], roots[:2], rtol=0.0, atol=1e-10)
    assert result["potential_v"][2] == 17.0 and result["converged"]
    assert np.max(abs(result["logarithmic_charge_residual"][:2])) <= 1e-10
    np.testing.assert_array_equal(refs, [0.0, 0.0, 17.0])


def test_adjacent_float_exact_root_is_unattainable_and_rejected():
    exact = F(1) + F(1, 2**53)
    minimum_residual = F(1, 2**53)
    tolerance = float.fromhex("0x1p-55")
    assert minimum_residual > F(tolerance)

    def residual(phi):
        a = np.asarray(phi)
        return {
            "logarithmic_charge_residual": np.array(
                [float(exact - F(float(x))) for x in a.flat]
            ).reshape(a.shape)
        }

    with pytest.raises(RuntimeError, match="did not converge"):
        potential(
            1.0,
            0.25 * E,
            0.25 * E,
            E,
            True,
            residual,
            potential_tolerance_v=float.fromhex("0x1p-50"),
            quasineutral_tolerance=tolerance,
            max_iterations=100,
        )


def test_potential_no_bracket_and_bad_callback_fail():
    with pytest.raises(RuntimeError, match="bracket"):
        potential(0.0, E, E, E, True, lambda p: {"logarithmic_charge_residual": np.ones_like(p)})
    with pytest.raises(ValueError):
        potential(0.0, E, E, E, False, lambda p: {"logarithmic_charge_residual": np.nan})


@pytest.mark.parametrize("mode", ["independent_fit", "species_sum"])
def test_pressure_state_directional_defaults_and_bookkeeping(mode):
    b = np.array([[1.0], [2.0]])
    psi = np.array([[0.0, 0.25, 1.0]])

    def law(B, P):
        return {"p_parallel": 20.0 + 2.0 * B + P, "p_perpendicular": 15.0 + B + 2.0 * P}

    result = pressure_state(
        b,
        psi,
        law,
        2.0,
        3.0,
        0.0,
        electron_p_parallel_pa=4.0,
        electron_p_perpendicular_pa=2.0,
        pressure_composition_mode=mode,
    )
    B, P = np.broadcast_arrays(b, psi)
    np.testing.assert_array_equal(result["ion_p_parallel"], 16.0 + 2.0 * B + P)
    np.testing.assert_array_equal(result["ion_p_perpendicular"], 13.0 + B + 2.0 * P)
    for key in ("residual_stress_parallel_pa", "residual_stress_perpendicular_pa"):
        np.testing.assert_array_equal(result[key], 0.0)
    assert result["species_pressure_sum_consistent"]
    np.testing.assert_array_equal(result["electron_density"], np.full((2, 3), 2.0))


@pytest.mark.parametrize("steps,consistent", [(32, True), (128, False)])
def test_pressure_sum_threshold_is_original_64eps(steps, consistent):
    value = 1.0 + steps * np.finfo(float).eps
    law = lambda b, p: {"p_parallel": np.ones_like(b), "p_perpendicular": np.ones_like(b)}
    args = (1.0, 0.0, law, 1.0, 0.0, 0.0)
    out = pressure_state(*args, ion_p_parallel_pa=value, ion_p_perpendicular_pa=value)
    assert out["species_pressure_sum_consistent"] is consistent
    if consistent:
        assert pressure_state(
            *args,
            ion_p_parallel_pa=value,
            ion_p_perpendicular_pa=value,
            pressure_composition_mode="species_sum",
        )["species_pressure_sum_consistent"]
    else:
        with pytest.raises(ValueError):
            pressure_state(
                *args,
                ion_p_parallel_pa=value,
                ion_p_perpendicular_pa=value,
                pressure_composition_mode="species_sum",
            )


def test_pressure_callback_failure_and_negative_species_are_not_hidden():
    def fail(*args):
        raise RuntimeError("raw-law-failure")

    with pytest.raises(RuntimeError, match="raw-law-failure"):
        pressure_state(1.0, 0.0, fail, 1.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        pressure_state(
            1.0, 0.0, lambda b, p: {"p_parallel": 1.0, "p_perpendicular": 1.0}, 1.0, 2.0, 0.0
        )


@pytest.mark.parametrize("masked", [False, True])
def test_hall_tilted_anisotropic_tensor_and_omitted_ion_components(masked):
    r = np.array([1.0, 1.25, 1.75, 2.0])
    z = np.array([-0.25, 0.0, 0.5])
    R, Z = np.meshgrid(r, z)
    mask = np.ones(R.shape, dtype=bool)
    if masked:
        mask[1, 1] = False
    pp = 30.0 + 2 * R + 3 * Z
    pa = 30.0 + 6 * R + 4 * Z
    state = {
        "ion_density": np.full_like(R, 2.0),
        "electron_pressure": 2.0 + R,
        "electron_p_parallel": 2.0 + 3 * R,
        "electron_p_perpendicular": 2.0 + R,
        "electrostatic_potential": R - 2 * Z,
    }
    original = {k: v.copy() for k, v in state.items()}
    out = drift(
        R,
        Z,
        np.full_like(R, 0.6),
        np.full_like(R, 0.8),
        pa,
        pp,
        state,
        mask,
        1.0,
        1.0,
        include_toroidal_inertia=False,
        maximum_inertial_mach=10.0,
    )
    expected = {
        "pressure_force_R": 134.0 / 25 + 9.0 * Z / (25 * R),
        "pressure_force_Z": 187.0 / 25 + 12.0 * Z / (25 * R),
        "electron_pressure_force_R": np.full_like(R, 61.0 / 25),
        "electron_pressure_force_Z": np.full_like(R, 48.0 / 25),
        "electric_field_R": np.full_like(R, -1.0),
        "electric_field_Z": np.full_like(R, 2.0),
    }
    for key, value in expected.items():
        np.testing.assert_allclose(out[key], value, rtol=1e-12, atol=1e-12)
    for key, value in [
        ("J_phi", -0.2),
        ("ion_toroidal_velocity", 1.5),
        ("electron_toroidal_velocity", 1.6),
        ("ohm_residual_R", 1.5),
        ("ohm_residual_Z", 2.0),
    ]:
        np.testing.assert_allclose(out[key], np.where(mask, value, 0.0), rtol=1e-12, atol=1e-12)
    assert out["inertia_converged"] and out["inertia_iterations"] == 1
    for key, value in original.items():
        np.testing.assert_array_equal(state[key], value)


def test_hall_inertia_second_analytic_fixed_point_and_true_budget_failure():
    R, Z = np.meshgrid([0.5, 0.625, 0.75, 0.875, 1.0], [-0.5, 0.0, 0.5])
    p = 20.0 + 3.0 * R**2
    state = {
        "ion_density": np.ones_like(R),
        "electron_pressure": np.zeros_like(R),
        "electrostatic_potential": np.zeros_like(R),
    }
    args = (
        R,
        Z,
        np.zeros_like(R),
        np.ones_like(R),
        p,
        p,
        state,
        np.ones_like(R, dtype=bool),
        1.0,
        1.0,
    )
    out = drift(*args, inertia_relax=0.8, maximum_inertial_mach=10.0, inertia_tolerance=1e-10)
    # J=6R-J^2/R => roots 2R,-3R; positive branch reached from 6R.
    np.testing.assert_allclose(out["J_phi"], 2 * R, rtol=1e-10, atol=1e-10)
    assert out["inertia_fixed_point_residual"] <= 1e-10
    with pytest.raises(RuntimeError, match="inertia iteration"):
        drift(
            *args,
            inertia_relax=0.8,
            maximum_inertial_mach=10.0,
            inertia_max_iterations=1,
            inertia_tolerance=1e-30,
        )


def test_hall_mask_never_swallow_invalid_state():
    R, Z = np.meshgrid([0.5, 1.0, 1.5], [-0.5, 0.0, 0.5])
    zero = np.zeros_like(R)
    state = {
        "ion_density": np.ones_like(R),
        "electron_pressure": zero.copy(),
        "electrostatic_potential": zero.copy(),
    }
    state["electron_pressure"][0, 0] = np.nan
    with pytest.raises(ValueError):
        drift(
            R,
            Z,
            zero,
            np.ones_like(R),
            zero + 10,
            zero + 10,
            state,
            np.zeros_like(R, dtype=bool),
            1.0,
            1.0,
        )


def feedback_inputs(errors, enable):
    n = len(errors)
    return {
        "input_time_s": [0.25 * k for k in range(n)],
        "observation_time_s": [0.25 * k for k in range(n)],
        "signals": {
            "reference_T": [[float(e)] + [0.0] * 9 for e in errors],
            "measured_T": [[0.0] * 10 for _ in errors],
            "feedforward_current_A": [[1.0, -1.0] + [0.0] * 9 for _ in errors],
            "enable": list(enable),
        },
    }


def feedback_controller():
    matrix = [[0.0] * 10 for _ in range(11)]
    matrix[0][0] = 2.0
    matrix[1][0] = -1.0
    return {
        "sample_period_s": 0.25,
        "P": [2.0] + [0.0] * 9,
        "I": [3.0] + [0.0] * 9,
        "D": [0.5] + [0.0] * 9,
        "N_per_s": [2.0] + [0.0] * 9,
        "coefficient_matrix_unscaled": matrix,
        "coefficient_scale": 1.0,
        "integrator_initial_state": [7.0] * 10,
        "filter_initial_state": [9.0] * 10,
        "internal_integration_enable": [1.0] * 10,
        "internal_reset": 0,
    }


def test_feedback_independent_rational_trace_and_hold_reset():
    raw = feedback_inputs([1, 1, 1, 4, 4, 2, 2], [1, 1, 0, 0, 1, 1, 1])
    control = feedback_controller()
    before = copy.deepcopy((raw, control))
    out = feedback(raw, control)
    expected_pid = [
        [2.0, 0.75, 1.0],
        [2.0, 1.5, 0.5],
        [2.0, 1.5, 0.5],
        [2.0, 1.5, 0.5],
        [8.0, 3.0, 4.0],
        [4.0, 4.5, 0.0],
        [4.0, 6.0, 0.0],
    ]
    expected_feedback = [7.5, 8.0, 8.0, 8.0, 30.0, 17.0, 20.0]
    expected_total = [8.5, 9.0, 1.0, 1.0, 31.0, 18.0, 21.0]
    np.testing.assert_array_equal(np.asarray(out["values"]["pid_components"])[:, :3], expected_pid)
    np.testing.assert_array_equal(
        np.asarray(out["values"]["feedback_current_A"])[:, 0], expected_feedback
    )
    np.testing.assert_array_equal(
        np.asarray(out["values"]["total_current_A"])[:, 0], expected_total
    )
    assert out["state_trace"]["reset_at_sample"] == [True, False, False, False, True, False, False]
    np.testing.assert_array_equal(
        np.asarray(out["state_trace"]["pre_integrator_state"])[:, 0],
        [0.0, 0.75, 1.5, 1.5, 0.0, 3.0, 4.5],
    )
    np.testing.assert_array_equal(
        np.asarray(out["state_trace"]["post_integrator_state"])[:, 0],
        [0.75, 1.5, 1.5, 1.5, 3.0, 4.5, 6.0],
    )
    np.testing.assert_array_equal(
        np.asarray(out["state_trace"]["pre_filter_state"])[:, 0],
        [0.0, 0.5, 0.75, 0.75, 0.0, 2.0, 2.0],
    )
    np.testing.assert_array_equal(
        np.asarray(out["state_trace"]["post_filter_state"])[:, 0],
        [0.5, 0.75, 0.75, 0.75, 2.0, 2.0, 2.0],
    )
    assert (raw, control) == before


def test_feedback_non_diagonal_map_and_scale():
    raw = feedback_inputs([1, 3, 0], [1, 1, 1])
    control = feedback_controller()
    second = [2.0, -1.0, 4.0]
    for row, e in zip(raw["signals"]["reference_T"], second):
        row[1] = e
    control["P"] = [2.0, -1.0] + [0.0] * 8
    control["I"] = [0.0] * 10
    control["D"] = [0.0] * 10
    control["coefficient_matrix_unscaled"][0][:2] = [2.0, 3.0]
    control["coefficient_matrix_unscaled"][1][:2] = [-4.0, 5.0]
    control["coefficient_scale"] = 0.5
    result = feedback(raw, control)
    expected = []
    for a, b in zip([1.0, 3.0, 0.0], second):
        expected.append(
            [
                float(F(1, 2) * (2 * F(2 * a) + 3 * F(-b))),
                float(F(1, 2) * (-4 * F(2 * a) + 5 * F(-b))),
            ]
        )
    np.testing.assert_array_equal(
        np.asarray(result["values"]["feedback_current_A"])[:, :2], expected
    )


@pytest.mark.parametrize("kind", ["enable", "rate", "reset", "timing", "nonfinite", "shape"])
def test_feedback_declared_true_failures(kind):
    raw = feedback_inputs([1, 1], [1, 1])
    control = feedback_controller()
    if kind == "enable":
        raw["signals"]["enable"][0] = 2
    elif kind == "rate":
        control["N_per_s"][0] = -1.0
    elif kind == "reset":
        control["internal_reset"] = 1
    elif kind == "timing":
        raw["observation_time_s"][1] = 0.5
    elif kind == "nonfinite":
        raw["signals"]["measured_T"][0][0] = np.inf
    else:
        control["P"] = [1.0]
    with pytest.raises(ValueError):
        feedback(raw, control)


@pytest.mark.parametrize("cap", [10.0, 0.25])
def test_omitted_ion_components_determine_ion_only_thermal_diagnostics_and_cap(cap):
    R, Z = np.meshgrid([1.0, 1.25, 1.75, 2.0], [-0.25, 0.0, 0.5])
    state = {
        "ion_density": np.full_like(R, 2.0),
        "electron_pressure": 2.0 + R,
        "electron_p_parallel": 2.0 + 3 * R,
        "electron_p_perpendicular": 2.0 + R,
        "electrostatic_potential": R - 2 * Z,
    }
    with localcontext() as ctx:
        ctx.prec = 180
        expected = []
        for r, z in zip(R.flat, Z.flat):
            square = (D(84) + D(5) * D.from_float(float(r)) + D(10) * D.from_float(float(z))) / D(6)
            expected.append(float(square.sqrt()))
        thermal = np.array(expected).reshape(R.shape)
        b2 = F(0.6) ** 2 + F(0.8) ** 2
        B = float((D(b2.numerator) / D(b2.denominator)).sqrt())
    out = drift(
        R,
        Z,
        np.full_like(R, 0.6),
        np.full_like(R, 0.8),
        30.0 + 6 * R + 4 * Z,
        30.0 + 2 * R + 3 * Z,
        state,
        np.ones_like(R, dtype=bool),
        1.0,
        1.0,
        include_toroidal_inertia=False,
        maximum_inertial_mach=cap,
    )
    np.testing.assert_allclose(out["ion_gyroradius"], thermal / B, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(out["raw_ion_toroidal_mach"], 1.5 / thermal, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(
        out["ion_toroidal_velocity"], np.minimum(1.5, cap * thermal), rtol=1e-12, atol=1e-12
    )
    if cap == 0.25:
        np.testing.assert_allclose(out["ion_toroidal_mach"], 0.25, rtol=1e-12, atol=1e-12)
        assert out["velocity_cap_fraction"] == 1.0
    else:
        assert out["velocity_cap_fraction"] == 0.0


def test_feedback_docstring_example_runs_without_repository_fixtures(tmp_path):
    """Execute the public example from an empty cwd using the installed package.

    Isolated Python ignores the working directory and PYTHONPATH for imports.
    Doctest executes every example assertion; missing fixtures and wrong numeric
    expectations must fail the child process and this test.
    """
    program = """
import doctest
from scirel.closures import simulate_discrete_vector_feedback

example = doctest.DocTestParser().get_doctest(
    simulate_discrete_vector_feedback.__doc__, {}, "feedback public example", None, 0
)
result = doctest.DocTestRunner().run(example)
assert result.attempted > 0, "the public docstring must contain executable examples"
raise SystemExit(1 if result.failed else 0)
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", program],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
