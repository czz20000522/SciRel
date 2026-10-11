"""Independent checks for the bounded TORAX algebra/grid leaf family."""
import numpy as np
import pytest
from decimal import Decimal, localcontext

from scirel.geometry import face_to_cell
from scirel.physics import (
    calculate_log_lambda_ee,
    calculate_log_lambda_ei,
    calculate_log_lambda_ii,
    calculate_main_ion_dilution_factor,
)


def test_face_to_cell_midpoints_and_shape_boundary():
    faces = np.array([0.0, 2.0, 8.0, 10.0])
    np.testing.assert_array_equal(face_to_cell(faces), [1.0, 5.0, 9.0])
    assert face_to_cell(np.array([3.0, 7.0])).shape == (1,)
    with pytest.raises(ValueError, match="at least two"):
        face_to_cell([1.0])
    with pytest.raises(ValueError, match="one-dimensional"):
        face_to_cell([[1.0, 2.0]])
    with pytest.raises(ValueError, match="finite"):
        face_to_cell([1.0, np.inf])


def test_face_to_cell_avoids_finite_endpoint_intermediate_overflow():
    faces = np.array([np.finfo(float).max, np.finfo(float).max])
    np.testing.assert_allclose(face_to_cell(faces), [np.finfo(float).max])


def test_dilution_independent_quasineutrality_algebra_and_broadcast():
    zi = 1.0
    zimp = np.array([3.0, 6.0])
    zeff = np.array([[1.0], [2.5]])
    expected = (zimp - zeff) / (zi * (zimp - zi))
    np.testing.assert_allclose(calculate_main_ion_dilution_factor(zi, zimp, zeff), expected)
    # Endpoints represent pure main-ion and pure impurity limits.
    np.testing.assert_array_equal(calculate_main_ion_dilution_factor(2, 6, [2, 6]), [1 / 2, 0])


@pytest.mark.parametrize(
    "args, message",
    [
        ((1, 1, 1), "differ"),
        ((1, 6, 0.5), "between"),
        ((0, 6, 2), "positive"),
        ((1, [6, 7], [2, 3, 4]), "broadcast"),
    ],
)
def test_dilution_rejects_singular_or_nonphysical_inputs(args, message):
    with pytest.raises(ValueError, match=message):
        calculate_main_ion_dilution_factor(*args)


def test_coulomb_logs_match_independent_hand_formulas_and_broadcast():
    te = np.array([1.0, 2.0])
    ne = np.array([[1e18], [1e19]])
    ee = calculate_log_lambda_ee(te, ne)
    ei = calculate_log_lambda_ei(te, ne)
    expected_ee = 31.0 - 0.5 * np.log(ne) + np.log(1e3 * te)
    expected_ei = 31.3 - 0.5 * np.log(ne) + np.log(1e3 * te)
    np.testing.assert_allclose(ee, expected_ee, rtol=0, atol=1e-14)
    np.testing.assert_allclose(ei, expected_ei, rtol=0, atol=1e-14)
    ti, ni, zi = 3.0, 2e19, 2.0
    expected_ii = 30.0 - 0.5 * np.log(ni) + 1.5 * np.log(1e3 * ti) - 3.0 * np.log(zi)
    np.testing.assert_allclose(calculate_log_lambda_ii(ti, ni, zi), expected_ii, rtol=0, atol=1e-14)
    np.testing.assert_allclose(calculate_log_lambda_ei(te, ne) - calculate_log_lambda_ee(te, ne), 0.3)


@pytest.mark.parametrize(
    "fn, args, message",
    [
        (calculate_log_lambda_ee, (0.0, 1e19), "T_e"),
        (calculate_log_lambda_ei, (1.0, -1.0), "n_e"),
        (calculate_log_lambda_ii, (1.0, 1e19, 0.0), "Z_i"),
        (calculate_log_lambda_ee, ([1.0, 2.0], [1e19, 2e19, 3e19]), "broadcast"),
    ],
)
def test_coulomb_logs_reject_invalid_domain_and_shapes(fn, args, message):
    with pytest.raises(ValueError, match=message):
        fn(*args)


def test_coulomb_logs_stable_for_large_but_finite_temperature():
    got = calculate_log_lambda_ee(1e308, 1.0)
    expected = 31.0 + np.log(1e3) + np.log(1e308)
    np.testing.assert_allclose(got, expected)


def test_face_to_cell_preserves_smallest_subnormal_equal_endpoints():
    tiny = np.nextafter(0.0, 1.0)
    np.testing.assert_array_equal(face_to_cell([tiny, tiny]), [tiny])


def test_dilution_avoids_overflow_of_denominator_product():
    got = calculate_main_ion_dilution_factor(1e200, 2e200, 1.5e200)
    np.testing.assert_allclose(got, 5e-201, rtol=1e-14, atol=0)


def test_midpoint_smallest_subnormal_half_rounding():
    tiny = np.nextafter(0.0, 1.0)
    # The exact midpoint is half the smallest subnormal: ties round to zero.
    np.testing.assert_array_equal(face_to_cell([tiny, 0.0]), [0.0])
    np.testing.assert_array_equal(face_to_cell([0.0, tiny]), [0.0])


def test_dilution_independent_charge_balance_system():
    # Build n_e and Z_eff from two positive species rather than computing
    # the expected answer using the production quotient.
    for zi in (0.5, 1.0, 2.0, 7.0):
        for zimp in (0.25, 3.0, 6.0, 11.0):
            for ni, nz in ((0.0, 3.0), (2.0, 0.0), (0.7, 2.3), (3.0, 0.1)):
                ne = zi * ni + zimp * nz
                zeff = (zi**2 * ni + zimp**2 * nz) / ne
                got = calculate_main_ion_dilution_factor(zi, zimp, zeff)
                np.testing.assert_allclose(got, ni / ne, rtol=3e-14, atol=3e-15)


@pytest.mark.parametrize("fn,c,p", [(calculate_log_lambda_ee,'31',1),(calculate_log_lambda_ei,'31.3',1)])
def test_electron_logs_decimal_complete_relation_and_scale_laws(fn, c, p):
    # Decimal ln is independent of NumPy's logarithm and 60-digit precision
    # makes float64 rounding the limiting scale of this gate.
    with localcontext() as ctx:
        ctx.prec = 60
        for t in (np.nextafter(0.0,1.0), 1e-200, 0.002, 2., 1e200, np.finfo(float).max):
            for n in (np.nextafter(0.0,1.0), 1e-100, 1e19, np.finfo(float).max):
                expected = Decimal(c) + (Decimal.from_float(float(t))*1000).ln() - Decimal.from_float(float(n)).ln()/2
                np.testing.assert_allclose(fn(t,n),float(expected),rtol=0,atol=3e-13)
    a=fn(2.,1e19)
    np.testing.assert_allclose(fn(6.,1e19)-a,np.log(3.),rtol=0,atol=1e-14)
    np.testing.assert_allclose(fn(2.,4e19)-a,-np.log(2.),rtol=0,atol=1e-14)


def test_ion_log_decimal_complete_relation_and_charge_scaling():
    with localcontext() as ctx:
        ctx.prec = 60
        for t in (np.nextafter(0.0,1.0), 0.003, 3., 1e200, np.finfo(float).max):
            for n in (np.nextafter(0.0,1.0), 2e19, np.finfo(float).max):
                for z in (np.nextafter(0.0,1.0), 0.5, 2., np.finfo(float).max):
                    expected = Decimal(30) - Decimal.from_float(float(n)).ln()/2 + Decimal('1.5')*(Decimal.from_float(float(t))*1000).ln()-3*Decimal.from_float(float(z)).ln()
                    np.testing.assert_allclose(calculate_log_lambda_ii(t,n,z),float(expected),rtol=0,atol=1e-12)
    a=calculate_log_lambda_ii(3.,2e19,2.)
    np.testing.assert_allclose(calculate_log_lambda_ii(3.,2e19,6.)-a,-3*np.log(3.),rtol=0,atol=1e-14)


@pytest.mark.parametrize('bad',[True, [1.,True], '1', 1+0j, np.nan, np.inf, [], np.ma.array([1.,2.],mask=[False,True])])
def test_coercion_empty_and_nonfinite_fail_closed(bad):
    for fn,args in ((calculate_log_lambda_ee,(bad,1e19)),(calculate_log_lambda_ei,(1.,bad)),(calculate_log_lambda_ii,(1.,1e19,bad)),(calculate_main_ion_dilution_factor,(1.,bad,1.5))):
        with pytest.raises(ValueError): fn(*args)
    with pytest.raises(ValueError): face_to_cell(bad)


def test_dilution_unrepresentable_valid_result_raises():
    tiny=np.nextafter(0.,1.)
    with pytest.raises(FloatingPointError):
        calculate_main_ion_dilution_factor(tiny, 1., tiny)
