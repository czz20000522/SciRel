"""Order-selectable complex-error and Maxwellian rational approximations.

Independently written from Weideman (1994), doi:10.1137/0731077, and the
partial-fraction definition Z_J(z)=sum b_j/(z-c_j). GPDF's two Faddeeva
namespaces select orders 32 and 16 respectively; FFT Z defaults to 32.
The positive imaginary axis uses erfcx to avoid a spurious inf*0.
Finite input whose exact continuation exceeds float64 raises explicitly.
J-pole tabulated data are private source-bound numerical input, not a claim
of redistribution permission. Fixed pole approximations are not exact Z.
"""
from functools import lru_cache
import operator
import numpy as np
from ._gpdf_pole_data import POLES

__all__=['evaluate_faddeeva_gpdf','evaluate_faddeeva_dr',
         'evaluate_maxwellian_fft','evaluate_maxwellian_jpole']


def _order(value):
    if isinstance(value,(bool,np.bool_)):
        raise ValueError('order must be a positive integer')
    try: n=operator.index(value)
    except TypeError: raise ValueError('order must be a positive integer') from None
    if n<1: raise ValueError('order must be a positive integer')
    return n


def _input(z):
    a=np.asarray(z,dtype=complex)
    if a.size==0 or not np.all(np.isfinite(a)):
        raise ValueError('z must be finite and nonempty')
    return a


@lru_cache(maxsize=16)
def _coefficients(n):
    m=2*n
    length=np.sqrt(n/np.sqrt(2))
    nodes=length*np.tan(np.arange(-m+1,m)*np.pi/(2*m))
    samples=np.r_[0.,np.exp(-nodes**2)*(length**2+nodes**2)]
    coefficients=np.fft.fft(np.fft.fftshift(samples)).real/(2*m)
    return coefficients[1:n+1][::-1],length


def _evaluate(z,n):
    a=_input(z)
    shape=a.shape
    z=a.ravel()
    upper=np.where(z.imag<0,np.conj(z),z)
    coefficients,length=_coefficients(n)
    denom=length-1j*upper
    w=(2*np.polyval(coefficients,(length+1j*upper)/denom)/denom)/denom+(1/np.sqrt(np.pi))/denom
    axis=z.real==0
    with np.errstate(over='ignore',invalid='ignore',under='ignore'):
        if np.any(axis):
            # Keep the domain import light: erfcx is only needed for the
            # positive-imaginary-axis stabilization path.
            from scipy.special import erfcx
            w[axis]=erfcx(upper[axis].imag)
        lower=z.imag<0
        w[lower]=np.conj(2*np.exp(-upper[lower].astype(np.clongdouble)**2).astype(complex)-w[lower])
    if not np.all(np.isfinite(w)):
        raise FloatingPointError('Faddeeva continuation exceeds finite float64 range')
    return {'w':w.reshape(shape),'order':n}


def evaluate_faddeeva_gpdf(z,*,order=None):
    """Evaluate w(z)=exp(-z²)erfc(-iz), default order 32; None selects default.

    Input and output are dimensionless and preserve scalar/array shape.
    Truncation is an algorithm choice, not an error bound. Lower-plane
    reflection can overflow physically; this raises FloatingPointError.
    """
    return _evaluate(z,32 if order is None else _order(order))


def evaluate_faddeeva_dr(z,*,order=None):
    """Evaluate the retained DR variant of w, default order 16 (None also 16)."""
    return _evaluate(z,16 if order is None else _order(order))


def evaluate_maxwellian_fft(z,*,order=32):
    """Evaluate dimensionless Z=i√πw by FFT rational expansion, default 32.

    Unlike the two Faddeeva variants, explicit None is invalid for order.
    The final scaled Z is checked separately: finite w can overflow on scaling.
    """
    result=_evaluate(z,_order(order))
    with np.errstate(over='ignore',invalid='ignore'):
        scaled=1j*np.sqrt(np.pi)*result['w']
    if not np.all(np.isfinite(scaled)):
        raise FloatingPointError('Maxwellian FFT response exceeds finite float64 range after scaling')
    return {'Z':scaled,'order':result['order']}


def evaluate_maxwellian_jpole(z,*,order=8):
    """Evaluate fixed 8/12/16/24-pole Maxwellian Z approximation.

    Every matrix entry is evaluated (repair of source length(z) loop).
    Upper-plane poles are avoided by construction; lower values follow
    Z(z)=conj(Z(conj(z)))+2i√π exp(-z²). The tabulated rational function
    has finite truncation error; no arbitrary lower-plane accuracy is implied.
    """
    n=_order(order)
    if n not in POLES: raise ValueError('order must be 8,12,16 or 24')
    a=_input(z)
    bhalf,chalf=POLES[n]
    b=np.r_[bhalf,np.conj(bhalf)]
    c=np.r_[chalf,-np.conj(chalf)]
    upper=np.where(a.imag<0,np.conj(a),a)
    value=np.sum(b/(upper[...,None]-c),axis=-1)
    with np.errstate(over='ignore',invalid='ignore',under='ignore'):
        value=np.where(a.imag<0,np.conj(value)+2j*np.sqrt(np.pi)*np.exp(-a.astype(np.clongdouble)**2).astype(complex),value)
    if not np.all(np.isfinite(value)):
        raise FloatingPointError('J-pole continuation exceeds finite float64 range')
    return {'Z':value,'order':n}
