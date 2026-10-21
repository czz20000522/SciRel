"""Held ion-ion Coulomb-log relation; review overlay only."""

from __future__ import annotations

from scirel._hold import require_review_import
require_review_import(__name__)

import numpy as np

from scirel.physics.coulomb_logs import _finite_result, _positive_broadcast


def calculate_log_lambda_ii(T_i, n_i, Z_i):
    """Return ``30 - .5 ln(n_i) + 1.5 ln(1000*T_i) - 3 ln(Z_i)``."""
    from scirel._hold import require_review_call
    require_review_call("calculate_log_lambda_ii")
    T, n, z = _positive_broadcast(("T_i", T_i), ("n_i", n_i), ("Z_i", Z_i))
    with np.errstate(over="ignore", invalid="ignore"):
        result = (
            30.0
            + 1.5 * (np.log(1000.0) + np.log(T))
            - 0.5 * np.log(n)
            - 3.0 * np.log(z)
        )
    return _finite_result(result, "ion-ion Coulomb logarithm")
