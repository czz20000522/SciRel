"""Frozen J-pole tables for the Z-function resonance sum of the fluidBW fluid model."""

from __future__ import annotations

import operator
import numpy as np

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
    """Return the ``(bzj, czj)`` pole pair of order ``j_order``.

    ``j_order`` is the number of poles J the caller's matrix assembly uses. The
    residues ``bzj`` weight the resonant response and the positions ``czj`` give the
    complex resonance offsets. The source writes only the first half of each table
    and completes it by conjugate symmetry, so the second half is derived, not
    tabulated independently.
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
