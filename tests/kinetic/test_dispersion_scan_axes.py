"""Regression coverage for the colon-ladder axes used by the two wavevector scans."""
from fractions import Fraction

import numpy as np
import pytest

from scirel.kinetic.fluid_wavevector_scan import scan_frequencies as fluid_scan_frequencies
from scirel.kinetic.kinetic_wavevector_scan import scan_frequencies as kinetic_scan_frequencies


@pytest.mark.parametrize("scan", [fluid_scan_frequencies, kinetic_scan_frequencies])
@pytest.mark.parametrize("start,step,stop", [(0.1, 0.1, 0.3), (0.1, 0.05, 0.3), (0.05, 0.05, 0.15)])
def test_wavevector_scan_colon_ladder_includes_endpoint(scan, start, step, stop):
    """A colon ladder includes stop when stop-start is an integer multiple of step."""
    result = scan(omega_scale=start, omega_step=step, omega_stop=stop, wn=1.0)
    exact_count = int((Fraction(str(stop)) - Fraction(str(start))) / Fraction(str(step))) + 1
    assert result["count"] == exact_count
    expected = np.array([float(Fraction(str(start)) + k * Fraction(str(step)))
                         for k in range(exact_count)])
    np.testing.assert_allclose(result["omegas"], expected, rtol=0, atol=1e-15)
    assert np.isclose(result["omegas"][-1], stop, rtol=0, atol=1e-15)
