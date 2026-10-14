"""Independent installed R1/R2/R3 probes: defining equations, no saved answers."""
from pathlib import Path
import json,warnings
import numpy as np
from scipy.integrate import quad
from scirel import kinetic as K

checks=[]
def components(name,actual,expected,rtol=2e-10):
    actual=complex(actual);expected=complex(expected)
    np.testing.assert_allclose(actual.real,expected.real,rtol=rtol,atol=0)
    np.testing.assert_allclose(actual.imag,expected.imag,rtol=rtol,atol=0)
    checks.append({'name':name,'actual':str(actual),'independent':str(expected),'rtol':rtol,'atol':0,'passed':True})

def integral(f,a,b,epsabs):
    return quad(lambda v:float(np.real(f(v))),a,b,epsabs=epsabs,epsrel=2e-13,limit=300)[0]+1j*quad(lambda v:float(np.imag(f(v))),a,b,epsabs=epsabs,epsrel=2e-13,limit=300)[0]

for z in (1e8+1j,1e8-1j,1e8j,-1e8+1j,11.9+1j,12.1+1j,12j,12.1-1j):
    expected=integral(lambda v:np.exp(-v*v)/np.sqrt(np.pi)/(v-z)**2,-12,12,1e-40)
    if z.imag<0:
        expected-=4j*np.sqrt(np.pi)*z*np.exp(-z*z)
    components('R1 Gaussian squared-kernel '+str(z),K.evaluate_generalized_dispersion(z,0)['Zp'],expected)

for z in (1e16+1j,1e16-1j,-1e16+1j,-1e16-1j,1e16j,-1e16j,1e16+0j,-1e16+0j,1+.1j,1-.1j,0.51+.01j,0.51-.01j,-.51+.01j,-.51-.01j):
    value=K.evaluate_generalized_dispersion(z,2)
    for power,key in ((1,'Z'),(2,'Zp')):
        expected=integral(lambda v:1/(v-z)**power,-.5,.5,1e-60)
        components('R2 top-hat integral '+key+' '+str(z),value[key],expected)

# Explicit-expression entry uses the same Gaussian squared-kernel definition.
for shift in (0.,2.):
    expression=f'exp(-(v-{shift})^2)/sqrt(pi)'
    for z in (1e8+1j,1e8-1j,1e8+0j):
        expected=integral(lambda v:np.exp(-(v-shift)**2)/np.sqrt(np.pi)/(v-z)**2,shift-12,shift+12,1e-40)
        if z.imag<0:expected-=4j*np.sqrt(np.pi)*(z-shift)*np.exp(-(z-shift)**2)
        actual=K.evaluate_generalized_hilbert(z,expression,integration_mesh=[-12,-4,0,2,4,12])['Zp']
        components('R1 explicit Hilbert squared-kernel shift '+str(shift)+' '+str(z),actual,expected)

# Near-center Taylor coefficients follow the exact rational derivative;
# omitted terms are O(x^3) in ReZ and ImZp, far below float64 at these x.
for x,y in ((1e-20,.1),(-1e-20,-.1),(1e-100,.1),(-1e-100,.1)):
    response=K.evaluate_generalized_dispersion(complex(x,y),2)
    expected_real=-x/(.25+y*y)
    expected_derivative_imag=-2*x*y/(.25+y*y)**2
    np.testing.assert_allclose(response['Z'].real,expected_real,rtol=3e-13,atol=0)
    np.testing.assert_allclose(response['Zp'].imag,expected_derivative_imag,rtol=3e-13,atol=0)
checks.append({'name':'R2 near-center representable tiny components via analytic Taylor coefficients','passed':True})
for x,y in ((.75,1e-20),(.75,-1e-20),(-.75,1e-20),(-.75,-1e-20)):
    expected_imag=y/(x*x-.25)
    np.testing.assert_allclose(K.evaluate_generalized_dispersion(complex(x,y),2)['Z'].imag,expected_imag,rtol=3e-13,atol=0)
checks.append({'name':'R2 exterior tiny-height contour components','passed':True})

# Explicit upper and lower boundary signs inside support, independent Plemelj.
for x in (-.4,0.,.4):
    expected=np.log((.5-x)/(.5+x))+1j*np.pi
    np.testing.assert_allclose(K.evaluate_generalized_dispersion(x,2)['Z'],expected,rtol=1e-13,atol=1e-15)
checks.append({'name':'R2 real-axis upper-boundary branch signs','passed':True})

threshold=np.sqrt(np.log(np.finfo(float).max)-np.log(2*np.sqrt(np.pi)))
for y in (26.625,threshold+1e-6):
    assert np.isfinite(K.evaluate_faddeeva_gpdf(-1j*y)['w'])
    with warnings.catch_warnings():
        warnings.simplefilter('error',RuntimeWarning)
        try:K.evaluate_maxwellian_fft(-1j*y)
        except FloatingPointError:pass
        else:raise AssertionError('R3 final scaled nonfinite response returned')
assert np.isfinite(K.evaluate_maxwellian_fft(-1j*(threshold-1e-6))['Z'])
checks.append({'name':'R3 finite-w/final-Z failure closure and threshold neighbors','passed':True})
result={'schema':'scirel.gpdf-correction-independent-installed.v1','checks':checks,'all_passed':True,'reference':'defining squared Cauchy and finite unit-density integrals plus Plemelj/erfcx scaling identity','original_wrong_complex_log1p_oracle':'NOT_USED','source_or_answers':'NOT_USED'}
Path('/results/CORRECTION_SCIENCE.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
