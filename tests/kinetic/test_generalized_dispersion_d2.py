import numpy as np
import pytest
from scipy.special import wofz
from scirel.kinetic import evaluate_cauchy_transform, evaluate_maxwellian_electrostatic, solve_maxwellian_electrostatic_mode

def test_cauchy_transform_matches_gaussian_identity_and_reports_error():
    density=lambda v: np.exp(-v*v)/np.sqrt(np.pi)
    z=0.4+0.7j
    r=evaluate_cauchy_transform(z,density,bounds=(-10,10))
    expected=1j*np.sqrt(np.pi)*wofz(z)
    assert abs(r['G']-expected)<1e-9
    assert np.all(r['quadrature_error'] >= 0)

def test_cauchy_transform_requires_off_axis_and_rejects_bad_callback():
    with pytest.raises(ValueError): evaluate_cauchy_transform(0.4, lambda v: 1.0)
    with pytest.raises(ValueError): evaluate_cauchy_transform(0.4+0.2j, lambda v: np.nan)

def test_maxwellian_residual_matches_analytic_identity():
    r=evaluate_maxwellian_electrostatic(1.2+0.3j,0.4)
    z=(1.2+0.3j)/(np.sqrt(2)*0.4)
    expected=0.4**2+1+z*(1j*np.sqrt(np.pi)*wofz(z))
    assert abs(r['D']-expected)<1e-12

def test_maxwellian_root_checks_residual():
    result=solve_maxwellian_electrostatic_mode(0.4,1.45-0.1j)
    assert abs(result['residual'])<1e-9
    with pytest.raises(RuntimeError): solve_maxwellian_electrostatic_mode(0.4,1.45-0.1j,max_evaluations=1)
