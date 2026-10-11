"""Bounded downstream graph regression for exporting the computed terminal state."""
import numpy as np

from scirel.equilibrium import compute_equilibrium
from scirel.io.eqdsk import read_pleiades_eqdsk, write_pleiades_eqdsk_legacy_raw


def test_raw_export_consumes_result_psi_and_pressure_fit(tmp_path):
    # This is the smallest source-shaped graph: feedback -> terminal export /
    # pressure diagnostic.  ``psi`` is deliberately distinct from the input
    # vacuum state by choosing a nonzero but rank-one Green map.
    R, Z = np.meshgrid(np.linspace(0., 1.2, 13), np.linspace(-1., 1., 11))
    psi_vac = R + 1.0
    result = compute_equilibrium(
        R, Z, lambda r: 1.2-r, psi_vac,
        np.full((R.size, R.size), 1e-4), maxiter=10,
    )
    assert result.status == 'converged'
    assert not np.array_equal(result.psi, psi_vac)
    # Correct terminal wiring: both exported flux and any pressure diagnostic
    # consume result.psi, never the pre-feedback vacuum array.
    destination = tmp_path/'terminal.eqdsk'
    write_pleiades_eqdsk_legacy_raw(R, Z, result.psi, result.plas_currents,
                                    destination, 'terminal')
    exported = read_pleiades_eqdsk(destination)
    np.testing.assert_allclose(exported['psi'], result.psi, rtol=1e-9, atol=1e-10)
    pressure = result.p_psifit(result.psi.ravel()).reshape(result.psi.shape)
    np.testing.assert_allclose(pressure[Z == 0.0], 1.2-R[Z == 0.0],
                               rtol=1e-8, atol=1e-10)
