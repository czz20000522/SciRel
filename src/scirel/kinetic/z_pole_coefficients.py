"""Private Z-function pole tables used by the local fluid dispersion assembly."""

from __future__ import annotations

import operator
import numpy as np

__all__ = ["get_z_pole_coefficients"]

# 冻结源码 em3d_Lpole.m:89-119 的极点表，前半段由源码写定，后半段按共轭对称补齐。
_TABLE = {
    8: (
        (
            -0.017340112270401 - 0.046306439626294j,
            -0.739917811220052 + 0.839518284620274j,
            5.840632105105495 + 0.953602751322040j,
            -5.583374181615043 - 11.208550459628098j,
        ),
        (
            2.237687725134293 - 1.625941024120362j,
            1.465234091939142 - 1.789620299603315j,
            0.839253966367922 - 1.891995211531426j,
            0.273936218055381 - 1.941787037576095j,
        ),
    ),
    12: (
        (
            -10.020983259474214017 - 14.728932929429874883j,
            -0.58878169153449514493 + 0.19067303610080007359j,
            -0.27475707659732384029 + 3.617920717493884482j,
            0.00045713742777499515344 + 0.00027155393843737098852j,
            0.017940627032508378515 - 0.036436053276701248142j,
            10.366124263145749629 - 2.5069048649816145967j,
        ),
        (
            0.22660012611958088507627 - 2.0716877594897791206264j,
            -1.70029215163003500750575 - 1.8822474221612724460388j,
            1.17139325085601178534269 - 1.97725033192085410977458j,
            3.0666201126826972102007 - 1.59002082593259971758095j,
            2.307327490410578276422 - 1.7546732543728200653674j,
            0.687200524906019065672977 - 2.040288525975844018682j,
        ),
    ),
}


def get_z_pole_coefficients(*, j_order):
    """Return fixed Maxwellian Z-function pole coefficients.

    Parameters
    ----------
    j_order : integer
        Total number of poles ``J`` [dimensionless]. The supported table
        orders are 8 and 12.

    Returns
    -------
    bzj : ndarray of complex128, shape (J,)
        Pole residues along the one-dimensional pole axis [dimensionless].
    czj : ndarray of complex128, shape (J,)
        Pole positions along the one-dimensional pole axis [dimensionless].
    j_order : int
        Effective total pole order [dimensionless].
    half_order : int
        Number of independently stored half-table entries [dimensionless].
    sum_bzj : complex
        Sum of ``bzj`` [dimensionless].
    sum_bzcj : complex
        Sum of ``bzj*czj`` [dimensionless].
    sum_bzcj2 : complex
        Sum of ``bzj*czj**2`` [dimensionless].

    Raises
    ------
    ValueError
        If ``j_order`` is not an integer or is not one of the two frozen table
        orders. Unsupported conversion errors may propagate.

    See Also
    --------
    scirel.kinetic.get_gamma_lpole_coefficients : Bessel-Gamma L-pole tables.
    scirel.kinetic.evaluate_plasma_dispersion : Direct Maxwellian Z evaluation.

    Notes
    -----
    The source table stores the first half of the residues and poles; the
    returned second half is completed by conjugation and negative conjugation,
    respectively. The pole sum is a bounded rational approximation, not an
    exact closed-form Z function.

    References
    ----------
    H. S. Xie, Phys. Plasmas 32, 082110 (2025).

    Examples
    --------
    >>> from scirel.kinetic import get_z_pole_coefficients
    >>> r=get_z_pole_coefficients(j_order=8); assert len(r['bzj'])==8 and len(r['czj'])==8
    """

    if isinstance(j_order, (bool, np.bool_)):
        raise ValueError("j_order must be an integer")
    try:
        j_order = operator.index(j_order)
    except TypeError:
        raise ValueError("j_order must be an integer") from None
    if j_order not in _TABLE:
        raise ValueError("j_order must be one of 8 or 12: the source defines no other table")
    base_b, base_c = _TABLE[j_order]
    half = j_order // 2
    bzj = np.zeros(j_order, dtype=complex)
    czj = np.zeros(j_order, dtype=complex)
    for k in range(half):
        bzj[k] = base_b[k]
        czj[k] = base_c[k]
    bzj[half:] = np.conj(bzj[:half])
    czj[half:] = -np.conj(czj[:half])
    return {
        "bzj": bzj,
        "czj": czj,
        "j_order": j_order,
        "half_order": half,
        "sum_bzj": complex(np.sum(bzj)),
        "sum_bzcj": complex(np.sum(bzj * czj)),
        "sum_bzcj2": complex(np.sum(bzj * czj**2)),
    }
