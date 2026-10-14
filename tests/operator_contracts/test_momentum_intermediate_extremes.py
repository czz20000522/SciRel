"""Independent Decimal witnesses distinguish intermediates from final values."""
from decimal import Decimal, localcontext
import math
import numpy as np
import pytest
from scirel.collisions.momentum_scales import normalized_momentum, thermal_electron_momentum

def decimal_thermal(t, r):
    with localcontext() as c:
        c.prec=200
        return float((Decimal(2)*Decimal.from_float(t)/Decimal.from_float(r)).sqrt())

def decimal_grid(x, v, c):
    with localcontext() as ctx:
        ctx.prec=200
        return float(Decimal.from_float(x)*Decimal.from_float(v)/Decimal.from_float(c))

@pytest.mark.parametrize('t,r',[(1e308,511.),(1e-300,1e300),(5e-324,1.),(1e308,1e308)])
def test_finite_thermal_after_dangerous_intermediate(t,r):
    actual=thermal_electron_momentum(temperature_kev=t,restmkev=r)
    assert actual==decimal_thermal(t,r)
    assert math.isfinite(actual) and actual>0

@pytest.mark.parametrize('x,v,c',[(1e308,1e308,1e308),(-1e308,1e308,1e308),(1e-300,1e-100,1e-200),(5e-324,0.5,5e-324),(1.,5e-324,5e-324),(0.,1e308,5e-324),(-0.,1e308,5e-324)])
def test_signed_zero_and_finite_grid_after_dangerous_intermediate(x,v,c):
    actual=normalized_momentum(x=[x],vnorm=v,clight=c)[0]
    assert actual==decimal_grid(x,v,c)
    assert np.signbit(actual)==np.signbit(x)

@pytest.mark.parametrize('t,r',[(1e308,5e-324)])
def test_genuinely_unrepresentable_thermal_still_rejected(t,r):
    assert not math.isfinite(decimal_thermal(t,r))
    with pytest.raises(ValueError,match='not representable'):
        thermal_electron_momentum(temperature_kev=t,restmkev=r)

def test_genuinely_unrepresentable_grid_still_rejected():
    with pytest.raises(ValueError,match='not representable'):
        normalized_momentum(x=[1e308],vnorm=1e308,clight=5e-324)

def test_subnormal_product_equal_scales_preserves_grid_not_rounded_intermediate():
    grid=np.array([-2.,-.5,0.,.5,2.,7.25])
    np.testing.assert_array_equal(normalized_momentum(x=grid,vnorm=5e-324,clight=5e-324),grid)

def test_grid_extremes_against_exact_rational_arithmetic():
    from fractions import Fraction
    for x,v,c in [(1e308,1e308,1e308),(1e-300,1e-100,1e-200),(5e-324,.5,5e-324),(-1e308,1e308,1e308)]:
        expected=float(Fraction(x)*Fraction(v)/Fraction(c))
        assert normalized_momentum(x=[x],vnorm=v,clight=c)[0]==expected
