"""Independent counterexamples discovered during the Pleiades semantic review."""
import numpy as np
import pytest

from scirel.closures.mirror_ambipolar_potential import solve_mirror_ambipolar_potential
from scirel.closures.mirror_quasineutral_closure import solve_mirror_quasineutral_closure
from scirel.diagnostics.parallel_pressure_residual import compute_parallel_pressure_residual

E = 1.602176634e-19


@pytest.mark.parametrize('strict', [False, True])
def test_duplicate_field_nodes_cannot_pass_by_ignoring_nan(strict):
    b = np.array([1., 1., 2., 3.])
    with pytest.raises(ValueError, match='unique'):
        compute_parallel_pressure_residual(
            b, np.zeros_like(b), b, strict=strict, field_axis=0, psi=np.zeros_like(b))


def test_nonfinite_derived_pressure_cannot_pass():
    with np.errstate(all='ignore'), pytest.raises(FloatingPointError, match='finite'):
        compute_parallel_pressure_residual(
            [1e308, 1e308], [0., 0.], [2., 3.], dp_parallel_dB=-1e308)


def test_negative_field_magnitude_cannot_enter_pressure_diagnostic():
    with pytest.raises(ValueError, match='strictly positive'):
        compute_parallel_pressure_residual(
            [1e308, 1e308], [0., 0.], [-2., -1.], dp_parallel_dB=0.)


def _end_loss(ions, electrons, **kwargs):
    return solve_mirror_ambipolar_potential(
        [1., 1.], 2., [0., 1.], 1.67e-27, E, ions, 100*E, 100*E,
        100*E, electron_density_ref_m3=electrons, **kwargs)


def _quasineutral(ions, electrons):
    return solve_mirror_quasineutral_closure(
        b_t=1., psi=np.array([0., 1.]), mass_kg=1.67e-27, charge_c=E,
        density_ref_m3=ions, temperature_parallel_j=100*E,
        temperature_perpendicular_ref_j=100*E, b_ref_t=1.,
        electron_temperature_j=100*E, electron_density_ref_m3=electrons)


@pytest.mark.parametrize('solve', [_end_loss, _quasineutral])
@pytest.mark.parametrize('ions,electrons', [([1e18, 1e18], [1e18, 0.]), ([1e18, 0.], [1e18, 1e18])])
def test_one_sided_vacuum_is_not_a_converged_solution(solve, ions, electrons):
    with pytest.raises(ValueError, match='both positive or both zero'):
        solve(ions, electrons)


@pytest.mark.parametrize('solve,residual', [(_end_loss, 'relative_current_residual'), (_quasineutral, 'relative_charge_residual')])
def test_valid_plasma_and_joint_vacuum_remain_supported(solve, residual):
    result = solve([1e18, 0.], [1e18, 0.])
    assert result['converged']
    np.testing.assert_allclose(result[residual], 0., atol=1e-9)


def test_prescribed_end_loss_evaluation_still_exposes_unbalanced_current():
    result = _end_loss([1e18, 1e18], [0., 0.], mode='evaluate', phi_plug_v=0.)
    np.testing.assert_allclose(result['relative_current_residual'], 1.)
    assert result['iterations'] == 0
    assert result['converged'] is True


def test_constant_field_without_derivative_evidence_is_indeterminate():
    with pytest.raises(ValueError, match='fixed-flux derivative'):
        compute_parallel_pressure_residual([2., 3.], [0., 0.], [1., 1.], strict=True)


def test_constant_field_with_explicit_pressure_law():
    # p_parallel(B, psi) = C(psi)*B gives p_perp = 0. Repeated B samples
    # alone cannot establish that derivative across separate flux surfaces.
    result = compute_parallel_pressure_residual(
        [2., 3.], [0., 0.], [1., 1.], strict=True, dp_parallel_dB=[2., 3.])
    assert result['passed']
    np.testing.assert_array_equal(result['rhs'], [0., 0.])


def test_constant_field_retains_declared_zero_derivative():
    result = compute_parallel_pressure_residual(
        [2., 3.], [2., 3.], [1., 1.], strict=True, dp_parallel_dB=0.)
    assert result['passed']
    np.testing.assert_array_equal(result['dp_parallel_dB'], [0., 0.])
    np.testing.assert_array_equal(result['rhs'], [2., 3.])
