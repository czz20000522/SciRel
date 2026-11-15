"""Exact paired-harmonic identities; supplements the b=0 endpoint tests.

For b != 0, every nonzero integer x has a pole in R or H: the residues
are proportional to I_n(b) and I_n'(b)-I_n(b), which cannot both vanish
at nonzero b by uniqueness of the modified Bessel differential equation.
At x=0, pairing +/-n makes R and H odd and analytic; both scaled-x
derivatives are zero. An enormous finite cot(pi*n) is not a regularization.
"""

import numpy as np
import pytest

from scirel.kinetic import evaluate_ronnmark_r


@pytest.mark.parametrize("x", [1.0, -1.0, 2.0, 12.0, -12.0, 12.0 + 0j])
@pytest.mark.parametrize("b", [0.2, 9.0, 100.0, 10.0 + 20.0j])
def test_nonzero_integer_resonance_cannot_return_a_finite_pseudo_pole(x, b):
    with pytest.raises(FloatingPointError, match="(?i)(pole|resonan)"):
        evaluate_ronnmark_r(x, b)


@pytest.mark.parametrize("b", [0.2, 4.0, 9.0, 100.0, 10.0 + 20.0j])
@pytest.mark.parametrize("x", [0.0, 0.0j])
def test_zero_x_is_an_analytic_paired_harmonic_endpoint(x, b):
    result = evaluate_ronnmark_r(x, b)
    assert np.isfinite(result["RC"]).all(), "paired +/-n terms remove the n=0 apparent singularity"
    assert (np.abs(result["RC"]) <= 8 * np.nextafter(0.0, 1.0)).all(), (
        "the analytic odd response and both x-scaled derivatives vanish at exact x=0"
    )
