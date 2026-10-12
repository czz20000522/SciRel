"""Regular even solutions of -((1-x²)y')' = nu(nu+1)y, y(0)=1,y'(0)=0."""
import numpy as np
from scipy.integrate import solve_ivp


def regular_even_mode(degree, xi):
    """Evaluate the regular solution, including integer degrees, for |xi|<1.

    Substitution t=xi² gives the Gauss hypergeometric equation with
    a=-nu/2, b=(nu+1)/2, c=1/2. No singular P/Q connection coefficients
    or fixed polynomial truncation enter this definition. Its values are
    computed through the equivalent scaled initial-value equation because
    special-function connection formulas can lose accuracy at high degree.
    """
    degree = float(degree)
    xi = np.asarray(xi, dtype=float)
    if not np.isfinite(degree) or degree < 0.0:
        raise ValueError('degree must be finite and nonnegative')
    if not np.all(np.isfinite(xi)) or np.any(np.abs(xi) >= 1.0):
        raise ValueError('pitch coordinates must be finite and strictly inside (-1,1)')
    if xi.size == 0:
        return np.empty_like(xi)
    # Hypergeometric connection formulas can return finite but inaccurate
    # values at high degree, and overflow at large degree/small abscissa.
    # Integrate the equivalent regular equation using a dimensionless
    # abscissa and scaled flux throughout, with no degree exclusion.
    end = float(np.max(np.abs(xi)))
    if end == 0.0 or degree == 0.0:
        return np.ones_like(xi)
    k = np.sqrt(degree * (degree + 1.0))
    scale = end * k
    def rhs(t, state):
        return [scale * state[1] / (1.0-(end*t)**2), -scale * state[0]]
    steps = max(64, int(np.ceil(8.0*k*np.arcsin(end)/np.pi)))
    solution = solve_ivp(rhs, (0., 1.), [1., 0.], method='DOP853',
                         rtol=3e-13, atol=3e-14, max_step=1.0/steps,
                         dense_output=True)
    if not solution.success:
        raise RuntimeError('regular even mode initial-value integration failed')
    result = solution.sol(np.abs(xi).ravel()/end)[0].reshape(xi.shape)
    if not np.all(np.isfinite(result)):
        raise FloatingPointError('regular even loss-cone mode is not finite')
    return result
