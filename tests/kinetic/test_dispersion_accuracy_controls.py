"""Invalid accuracy controls cannot disable accepted-root residual gates."""

import numpy as np
import pytest
from scirel.kinetic.dispersion import multifluid
from scirel.kinetic.dispersion import parallel_continuation as parallel


@pytest.mark.parametrize("api", ["fluid_solve_state", "continue_em1d"])
@pytest.mark.parametrize(
    "criterion",
    [np.nan, np.inf, 0.0, -1.0, np.longdouble("1e400")],
    ids=["nan", "infinity", "zero", "negative", "finite_narrowing_overflow"],
)
def test_invalid_accuracy_criterion_rejected_before_acceptance(api, criterion):
    if isinstance(criterion, np.longdouble):
        if not np.isfinite(criterion):
            pytest.skip("platform longdouble has no wider finite range than float64")
        assert not np.isfinite(float(criterion))
    if api == "fluid_solve_state":
        state = multifluid.fluid_equilibrium_si(
            [[0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]], B0=0.0
        )
        with pytest.raises(ValueError, match="backward_tolerance"):
            multifluid.fluid_solve_state(state, 0.0, 0.0, backward_tolerance=criterion)
    else:
        state = dict(
            wps2=np.array([0.0]),
            vds=np.array([0.0]),
            vtzs=np.array([1.0]),
            wcs=np.array([1.0]),
            c2=1.0,
        )
        with pytest.raises(ValueError, match="residual_tolerance"):
            parallel.continue_em1d(
                dict(
                    state=state,
                    k_grid=np.array([0.1]),
                    initial_guess=0.1 + 0j,
                    residual_tolerance=criterion,
                )
            )
