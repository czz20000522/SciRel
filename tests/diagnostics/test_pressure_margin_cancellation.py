"""Independent Decimal oracles for pressure-margin cancellation (no frozen answers)."""
from decimal import Decimal, localcontext
import numpy as np
import pytest
from scirel.diagnostics.pointwise_firehose_margin import compute_pointwise_firehose_margin
from scirel.diagnostics.firehose_mirror_margins import compute_firehose_mirror_margins


def decimal_margin(B, mu, pt=0., pp=0., derivative=None):
    # 2000 decimal digits cover the exponent span of products/quotients of
    # binary64 inputs, including tiny representable residuals after cancellation.
    with localcontext() as context:
        context.prec = 2000
        b, m, t, p = map(Decimal.from_float, (B, mu, pt, pp))
        return float(b*b/m + (t-p if derivative is None else b*Decimal.from_float(derivative)))


@pytest.mark.parametrize('B,mu,pt,pp', [
    (1., 1., 1e100, 1e100),
    (1., 1., -1e100, -1e100),
    (1e-100, 1., 1e100, 1e100),
    (1e100, 1e100, 1e300, 1e300),
    (1.1, .7, 0., 1.1*1.1/.7),
    (1e50, 1., 1., 1e50*1e50),
    (1e50, 1., -1e50*1e50, -1.),
    (1., 1., 1e100, float(np.nextafter(1e100, np.inf))),
    (1e-200, 1e-300, 0., 1e-100),
])
def test_finite_cancellation_both_public_firehose_entries(B, mu, pt, pp):
    expected = decimal_margin(B, mu, pt, pp)
    point = compute_pointwise_firehose_margin(pp, pt, B, mu0=mu)
    joint = compute_firehose_mirror_margins(pp, pt, B, mu0=mu, dp_perp_dB=0.)
    assert float(point['firehose_margin']) == expected
    assert float(joint['firehose_margin']) == expected
    assert joint['firehose_stable'] == (expected > 0.)


@pytest.mark.parametrize('B,mu', [(1.1,.7),(.3,.7),(1e150,1e100),(1e-100,1e-200)])
def test_mirror_cancellation_retains_residual_sign_and_magnitude(B,mu):
    derivative = -B/mu
    expected = decimal_margin(B,mu,derivative=derivative)
    got = compute_firehose_mirror_margins(0.,0.,B,mu0=mu,dp_perp_dB=derivative)
    assert float(got['mirror_margin']) == expected
    assert got['mirror_stable'] == (expected > 0.)


def test_strided_multidimensional_and_broadcast_derivative_are_elementwise():
    B = np.array([[1.1,.3,2.],[2.,.3,1.1]])[:,::-1]
    derivative = -B/.7
    pt = np.full(B.shape,1e100)
    got = compute_firehose_mirror_margins(pt,pt,B,mu0=.7,dp_perp_dB=derivative)
    expected_fire=np.array([decimal_margin(float(b),.7,1e100,1e100) for b in B.flat]).reshape(B.shape)
    expected_mirror=np.array([decimal_margin(float(b),.7,derivative=float(d)) for b,d in zip(B.flat,derivative.flat)]).reshape(B.shape)
    np.testing.assert_array_equal(got['firehose_margin'],expected_fire)
    np.testing.assert_array_equal(got['mirror_margin'],expected_mirror)
    assert got['firehose_stable']
    assert not got['mirror_stable']
    assert got['min_mirror_margin']==expected_mirror.min()


def test_exact_zero_is_not_labeled_positive():
    got=compute_firehose_mirror_margins(2.,1.,1.,mu0=1.,dp_perp_dB=-1.)
    assert float(got['firehose_margin'])==float(got['mirror_margin'])==0.
    assert not got['firehose_stable'] and not got['mirror_stable']


def test_genuinely_unrepresentable_margin_still_fails():
    with pytest.raises(ValueError, match='must be finite'):
        compute_pointwise_firehose_margin(-1e308,1e308,1.,mu0=1.)
    with pytest.raises(FloatingPointError, match='must be finite'):
        compute_firehose_mirror_margins(0.,0.,1e200,mu0=1.,dp_perp_dB=0.)
