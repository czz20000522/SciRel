"""Pleiades cubic/polynomial basis functions, derived for SciRel D2.

Lineage: frozen D0 be412aa14b775f2a8170315242b92208bd11fc0e,
pleiades/analysis/basis_functions.py. D2 corrects the unequal-knot interior
matrix in ClampedCubicSpline and FirstClampedCubicSpline using C2 Hermite
continuity. Other formulas and defaults, including zero outside the knot
interval and value evaluation for deriv other than 1/2, remain source rules.

Supported claims require finite, strictly increasing 1-D knots (N>=3),
matched finite ordinates, and deriv=0/1/2. Natural boundary means f''=0;
clamped boundary supplies f'. FirstClamped uses supplied left f' and right
f''+f'/x-m**2*f/x**2=0. SecondClamped additionally requires x[0]=y[0]=0,
x[-1]>0 and applies its source left natural relation. Neither special
closure is certified as a physical magnetic-fitting boundary. Quartic and
special-function factory selections retain explicit rejection behavior.
"""
import numpy as np
import scipy.special as spec


def _validated_spline_data(x_data, y_data):
    """Coerce and validate the knot/ordinate contract before matrix assembly."""
    try:
        raw_x = np.asarray(x_data)
        raw_y = np.asarray(y_data)
    except (TypeError, ValueError) as exc:
        raise ValueError("spline knots and ordinates must be finite real arrays") from exc
    if (
        raw_x.ndim != 1
        or raw_y.ndim != 1
        or raw_x.dtype.kind not in "iuf"
        or raw_y.dtype.kind not in "iuf"
        or raw_x.size != raw_y.size
        or raw_x.size < 3
    ):
        raise ValueError(
            "spline knots and ordinates must be finite real one-dimensional arrays "
            "with equal length at least 3"
        )
    x = np.asarray(raw_x, dtype=float)
    y = np.asarray(raw_y, dtype=float)
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("spline knots and ordinates must be finite")
    if not np.all(np.diff(x) > 0.0):
        raise ValueError("spline knots must be strictly increasing")
    return x, y


class spline:
    '''
    Master Spline Class
    defines basic data structures and basic functions
    '''
    def __init__(self, x_data, y_data):
        x_data, y_data = _validated_spline_data(x_data, y_data)
        self.x_data = x_data
        self.y_data = y_data
        self.dimension = len(x_data)
        self.d_x = (x_data[1:] - x_data[0:-1])  # length = dimension-1
        self.d_y = (y_data[1:] - y_data[0:-1])  # length = dimension-1
        
    def __call__(self, x_value, deriv=0):
        return self._interpolate(x_value, deriv)
        
    def _interpolate(self, x_value, deriv=0):
        return
        
class CubicSpline(spline):
    '''
    Spline Class for Cubic Splines
    Includes Cubic Spline _interpolate function
    '''
    def __init__(self, x_data, y_data):
        spline.__init__(self, x_data, y_data)
        
    def _interpolate(self,x_value,deriv=0):
        '''Interpolate to get the functional value to x_value.

        Segment selection is vectorized with ``searchsorted``.  The public
        contract remains the source behavior: values outside the knot
        interval (including nonfinite queries) return zero, the final knot is
        evaluated on the final segment, and only derivatives 1 and 2 select
        derivative formulas; every other selector returns the value.
        '''
        x_value=np.array(x_value,dtype=float)
        y_int=np.zeros_like(x_value)
        in_domain=(x_value>=self.x_data[0]) & (x_value<=self.x_data[-1])
        if not np.any(in_domain):
            return y_int

        # ``self.k`` is created through ``np.matrix`` in the retained source
        # constructors, so flatten it before gathering one slope per query.
        xs=np.asarray(x_value[in_domain]).reshape(-1)
        interval=np.searchsorted(self.x_data,xs,side='right')-1
        interval=np.minimum(interval,self.k.size-2)
        k=np.asarray(self.k).reshape(-1)
        x_l=self.x_data[interval]
        x_u=self.x_data[interval+1]
        y_l=self.y_data[interval]
        y_u=self.y_data[interval+1]
        k_l=k[interval]
        k_u=k[interval+1]
        d_x=x_u-x_l
        t=(xs-x_l)/d_x
        a=k_l*d_x-(y_u-y_l)
        b=-k_u*d_x+(y_u-y_l)
        if deriv == 1:
            values=(y_u-y_l)/d_x+(1.-2.*t)*(a*(1-t)+b*t)/d_x+\
                   t*(1-t)*(b-a)/d_x
        elif deriv == 2:
            values=2.*(b-2.*a+(a-b)*3.*t)/d_x**2
        else:
            values=(1.-t)*y_l+t*y_u+t*(1.-t)*(a*(1.-t)+b*t)
        y_int[in_domain]=values
        return y_int
        
class NaturalCubicSpline(CubicSpline):
    def __init__(self, x_data, y_data):
        CubicSpline.__init__(self, x_data, y_data)
        '''Convience Pointers'''
        dimension=self.dimension
        d_x=self.d_x
        d_y=self.d_y
        
        '''Define Matrix'''
        A=np.zeros((dimension,dimension), dtype=float)
        for i in range(0,dimension-1):
            A[i,i]=2*(1/d_x[i]+1/d_x[i-1])
            A[i+1,i]=1/d_x[i]
            A[i,i+1]=1/d_x[i]
        A[0,0]=2/d_x[0]
        A[-1,-1]=2/d_x[-1]
        
        '''Define the b vector'''
        b=np.zeros(dimension, dtype=float)
        b[0]=3*d_y[0]/d_x[0]**2
        b[-1]=3*d_y[-1]/d_x[-1]**2
        for i in range(1,dimension-1):
            b[i]=3*(d_y[i]/d_x[i]**2+d_y[i-1]/d_x[i-1]**2)
            
        '''Solve for Slopes'''
        k=np.linalg.solve(A,b)
        self.k=np.array(k)
        
class ClampedCubicSpline(CubicSpline):
    def __init__(self, x_data, y_data,yp=[0,0]):
        CubicSpline.__init__(self, x_data, y_data)
        '''Data check'''
        assert len(yp)==2,'yp must be a vector of length 2'
        '''Convience Pointers'''
        dimension=self.dimension
        d_x=self.d_x
        d_y=self.d_y
        '''Define Matrix'''
        A=np.zeros((dimension-2,dimension-2), dtype=float)
        # Row i describes slope at knot i+1, adjacent h[i] and h[i+1].
        for i in range(0,dimension-2):
            A[i,i]=2*(1./d_x[i]+1./d_x[i+1])
            if i+1 < dimension-2:
                A[i+1,i]=1/d_x[i+1]
                A[i,i+1]=1/d_x[i+1]
        '''Define the b vector'''
        b=np.zeros(dimension-2, dtype=float)
        for i in range(0,dimension-2):
            b[i]=3.*(d_y[i]/d_x[i]**2+d_y[i+1]/d_x[i+1]**2)
        b[0]+=-1.*yp[0]/d_x[0]
        b[-1]+=-1.*yp[-1]/d_x[-1]
        '''Solve for Slopes and add clamped slopes'''
        k=np.linalg.solve(A,b)
        ktmp=np.zeros(dimension)
        ktmp[0]=yp[0]
        ktmp[-1]=yp[-1]
        ktmp[1:-1]=k.T
        k=ktmp
        self.k=np.array(k)
        
class FirstClampedCubicSpline(CubicSpline):
    '''
    Class for doing special clamped splines for 
    BC's on Cylindrical Magnetic Fitting Problem
    '''
    def __init__(self, x_data, y_data,yp=0,m=0):
        CubicSpline.__init__(self, x_data, y_data)
        '''Convience Pointers'''
        dimension=self.dimension
        d_x=self.d_x
        d_y=self.d_y
        x_data=self.x_data
        y_data=self.y_data
        A=np.zeros((dimension-1,dimension-1), dtype=float)
        # Interior C2 continuity at knot i+1; outer Robin row follows.
        for i in range(0,dimension-2):
            A[i,i]=2*(1/d_x[i]+1/d_x[i+1])
            A[i+1,i]=1/d_x[i+1]
            A[i,i+1]=1/d_x[i+1]
        A[-1,-2]=2/d_x[-1]
        A[-1,-1]=4/d_x[-1]+1/x_data[-1]
        b=np.zeros(dimension-1, dtype=float)
        for i in range(0,dimension-2):
            b[i]=3*(d_y[i]/d_x[i]**2+d_y[i+1]/d_x[i+1]**2)
        b[0]+=-1*yp/d_x[0]
        b[-1]+=6*d_y[-1]/d_x[-1]**2+m**2*y_data[-1]/x_data[-1]**2
        k=np.linalg.solve(A,b)
        ktmp=np.zeros(dimension)
        ktmp[0]=yp
        ktmp[1:]=k.T
        k=ktmp
        self.k=np.array(k)
        
class SecondClampedCubicSpline(CubicSpline):       
     def __init__(self, x_data, y_data,m=1):
        CubicSpline.__init__(self, x_data, y_data)
        '''Convience Pointers'''
        dimension=self.dimension
        d_x=self.d_x
        d_y=self.d_y
        x_data=self.x_data
        y_data=self.y_data
        A=np.zeros((dimension,dimension), dtype=float)
        for i in range(0,dimension-1):
            A[i,i]=2*(1/d_x[i]+1/d_x[i-1])
            A[i+1,i]=1/d_x[i]
            A[i,i+1]=1/d_x[i]
        A[0,0]=2
        A[0,1]=1
        A[-1,-2]=2/d_x[-1]
        A[-1,-1]=4/d_x[-1]+1/x_data[-1]
        b=np.zeros(dimension, dtype=float)
        for i in range(1,dimension-1):
            b[i]=3*(d_y[i]/d_x[i]**2+d_y[i-1]/d_x[i-1]**2)
        b[0]+=3*y_data[1]/x_data[1]
        b[-1]+=6*d_y[-1]/d_x[-1]**2+m**2*y_data[-1]/x_data[-1]**2
        k=np.linalg.solve(A,b)
        self.k=np.array(k)

class QuarticSpline(spline):
    '''
    Spline Class for Quartic Splines
    Includes Quartic Spline _interpolate function
    '''
    def __init__(self, x_data, y_data):
        raise NotImplementedError('Upstream quartic spline coefficient construction is incomplete')


basis_map = {"natural_cubic_spline":NaturalCubicSpline,
        "clamped_cubic_spline":ClampedCubicSpline,
        "clamped_cubic_spline1":FirstClampedCubicSpline,
        "clamped_cubic_spline2":SecondClampedCubicSpline,
        "quartic_spline":QuarticSpline,
        "poly":np.polynomial.polynomial.Polynomial,
        "j0":spec.j0,
        "j1":spec.j1,
        "y0":spec.y0,
        "y1":spec.y1,
        "i0":spec.i0,
        "i1":spec.i1,
        "k0":spec.k0,
        "k1":spec.k1,
        }

def build_basis(basis='poly',**kwargs):
    basis = basis.lower()
    basis_fn = basis_map[basis]
    if basis == 'poly':
        return _poly_basis(**kwargs)
    elif 'spline' in basis:
        return _spline_basis(basis_fn,**kwargs)
    else:
        raise NotImplementedError

def _poly_basis(**kwargs):
    poly_deg = kwargs.pop("poly_deg",3)
    coeffs = kwargs.pop("coeffs",None)
    if kwargs:
        unknown = ", ".join(sorted(kwargs))
        raise TypeError(f"build_basis() got unexpected keyword argument(s): {unknown}")
    if coeffs is None:
        coeffs = np.eye(poly_deg)
    return [np.polynomial.polynomial.Polynomial(coeffs[:,i]) for i in range(coeffs.shape[1])]

def _spline_basis(spline_fn,**kwargs):
    n_knots = kwargs.pop("n_knots",5)
    domain = tuple(kwargs.pop("domain",(0,1)))
    xdata = kwargs.pop("xdata",None)
    ydata = kwargs.pop("ydata",None)
    if xdata is None:
        xdata = np.linspace(domain[0],domain[1],n_knots)
    if ydata is None:
        ydata = np.eye(n_knots)
    if len(xdata.squeeze().shape) == 1:
        xdata = xdata.squeeze()
        return [spline_fn(xdata,ydata[:,i],**kwargs) for i in range(ydata.shape[1])]
    else:
        return [spline_fn(xdata[:,i],ydata[:,i],**kwargs) for i in range(ydata.shape[1])]

class BasisMatrix(object):
    def __init__(self,basis,**kwargs):
        self._basis_fns = build_basis(basis=basis,**kwargs)
        self._basis_dim = len(self._basis_fns)

    @property
    def basis_fns(self):
        return self._basis_fns

    @property
    def basis_dim(self):
        return self._basis_dim

    def __call__(self,domain,**kwargs):
        arr = np.zeros((len(domain),self._basis_dim))
        for i,fn in enumerate(self._basis_fns):
            arr[:,i] = fn(domain,**kwargs)
        return arr



__all__ = ['NaturalCubicSpline', 'ClampedCubicSpline', 'FirstClampedCubicSpline', 'SecondClampedCubicSpline', 'build_basis', 'BasisMatrix']
