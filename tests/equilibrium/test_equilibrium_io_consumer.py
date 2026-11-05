"""D2 bounded serialization consumer of a manufactured feedback result."""

import numpy as np
import pytest
from scirel.equilibrium import compute_equilibrium
from scirel.io.eqdsk import EQDSKFormatError, read_eqdsk, write_eqdsk


def test_manufactured_equilibrium_result_has_loss_bounded_io_consumer(tmp_path):
    R, Z = np.meshgrid(np.arange(1.0, 6.0), [-1.0, 0.0])
    P = lambda r: 5.0 - r
    result = compute_equilibrium(R, Z, P, R, np.full((10, 10), 1.0 / 300.0))
    assert result.status == "converged"
    assert result.iterations == 2
    profile_psi = result.psi[-1]
    mapping = dict(
        title="D2 MANUFACTURED FEEDBACK EXCHANGE",
        cursign=-1,
        nnr=5,
        nnz=2,
        nnv=5,
        rbox=4.0,
        zbox=1.0,
        psi_lim=4.9,
        Ip=float(result.plas_currents.sum()),
        tor_flux=np.zeros(5),
        p_flux=5.0 - R[-1],
        rbphi_flux=np.zeros(5),
        pprime_flux=result.p_psifit.derivative()(profile_psi),
        psi=result.psi,
        q_flux=np.zeros(5),
        nlim_pairs=0,
        nves_pairs=0,
        lim_pairs=np.empty((0, 2)),
        ves_pairs=np.empty((0, 2)),
    )
    path = tmp_path / "result.eqdsk"
    # Preserve the predecessor observation: the solver grid starts at R=1,
    # while this dialect encodes only an R=0 origin.  D2 must reject before
    # truncating the destination rather than silently shifting the geometry.
    with pytest.raises(EQDSKFormatError, match="not representable"):
        write_eqdsk({**mapping, "R": R, "Z": Z}, path)
    write_eqdsk(mapping, path)
    read = read_eqdsk(path)
    # This record cannot losslessly preserve an R-origin at one; parser's R
    # reconstruction convention starts at zero. It preserves the flux values
    # and profile ordering, not physical geometry of an arbitrary solver grid.
    np.testing.assert_allclose(read["psi"], R - 0.1, rtol=1e-9, atol=1e-10)
    np.testing.assert_allclose(read["pprime_flux"], -1.0, rtol=1e-9, atol=1e-10)
    assert read["Ip"] == -30.0
    assert read["R"][0, 0] == 0.0
    assert R[0, 0] == 1.0
