"""Local gyrotropic tension and fixed-flux pressure-slope diagnostics."""
import numpy as np
from ._fixed_flux_derivative import fixed_flux_derivative
from .pointwise_firehose_margin import _firehose_kernel, _mirror_kernel
MU0 = 4e-7*np.pi


def compute_firehose_mirror_margins(p_parallel,p_perp,magnetic_field,mu0=MU0,
                                  parallel_equilibrium=None, *,
                                  dp_perp_dB=None,field_axis=None,psi=None):
    """Return local firehose and long-wavelength mirror margins in Pa.

    Firehose margin is B²/mu0+p_perp-p_parallel. The mirror margin is
    B*d(p_perp+B²/(2*mu0))/dB at fixed psi, hence B²/mu0+B*dp_perp_dB.
    This positive total-pressure-slope criterion assumes a gyrotropic,
    no-flow equilibrium pressure law. For an invariant bi-Maxwellian it
    gives 1-beta_perp*(T_perp/T_parallel-1)>0. It is not global stability,
    a finite-Larmor-radius/finite-wave-number calculation, or a Hall-flow
    stability theorem. Frank2509.17288v4 Eq6 prints an opposing sign;
    this implementation follows the explicit total-pressure derivative,
    Kotelnikov2025 Eq3.7 and the kinetic bi-Maxwellian threshold, without
    claiming a publisher/author-confirmed erratum.

    dp_perp_dB must be an explicit fixed-psi derivative (Pa/T), or supply
    field_axis and psi for sampled fixed-flux lines. No spatial B sort or
    undocumented zero-derivative replacement is performed.
    """
    p_parallel,p_perp,magnetic_field=(np.asarray(x,dtype=float) for x in (p_parallel,p_perp,magnetic_field))
    if p_parallel.shape != p_perp.shape or p_parallel.shape != magnetic_field.shape:
        raise ValueError('p_parallel, p_perp, and magnetic_field must have the same shape')
    if not np.all(np.isfinite(p_parallel)):
        raise ValueError('parallel pressure must be finite')
    if not np.isfinite(mu0) or mu0 <= 0:
        raise ValueError('mu0 must be positive and finite')
    derivative,method=fixed_flux_derivative(p_perp,magnetic_field,
        derivative=dp_perp_dB,field_axis=field_axis,psi=psi)
    firehose=_firehose_kernel(p_parallel,p_perp,magnetic_field,mu0)
    mirror=_mirror_kernel(magnetic_field,derivative,mu0)
    if not np.all(np.isfinite(firehose)) or not np.all(np.isfinite(mirror)):
        raise FloatingPointError('local pressure margins are not finite')
    if parallel_equilibrium is not None and not isinstance(parallel_equilibrium,dict):
        raise ValueError('parallel_equilibrium must be a mapping when provided')
    state=parallel_equilibrium or {}
    return {'firehose_margin':firehose,'mirror_margin':mirror,
            'firehose_stable':bool(np.min(firehose)>0),'mirror_stable':bool(np.min(mirror)>0),
            'min_firehose_margin':float(np.min(firehose)),'min_mirror_margin':float(np.min(mirror)),
            'parallel_equilibrium_error':state.get('error'),
            'max_parallel_equilibrium_error':state.get('max_relative_error'),
            'dp_perp_dB':derivative,'derivative_method':method,
            'criterion':'local_gyrotropic_tension_and_fixed_flux_total_pressure_slope'}

__all__=['compute_firehose_mirror_margins']
