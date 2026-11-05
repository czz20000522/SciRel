"""The extended EQDSK dialect keeps a fixed origin and opaque header slots."""

import inspect

import numpy as np

from scirel.io.eqdsk import read_eqdsk, write_eqdsk


def _minimal_document():
    return {
        "title": "fixed-origin fixture",
        "cursign": 1,
        "nnr": 2,
        "nnz": 2,
        "nnv": 2,
        "rbox": 1.0,
        "zbox": 2.0,
        "psi_lim": 0.0,
        "Ip": 0.0,
        "tor_flux": np.zeros(2),
        "p_flux": np.zeros(2),
        "rbphi_flux": np.zeros(2),
        "pprime_flux": np.zeros(2),
        "q_flux": np.zeros(2),
        "psi": np.zeros((2, 2)),
        "nlim_pairs": 0,
        "nves_pairs": 0,
        "lim_pairs": np.empty((0, 2)),
        "ves_pairs": np.empty((0, 2)),
        "header_scalars": np.zeros((4, 5)),
    }


def test_nonzero_header_slot_does_not_shift_the_reconstructed_grid(tmp_path):
    document = _minimal_document()
    document["header_scalars"][0, 3] = 7.5
    path = tmp_path / "fixed-origin.eqdsk"
    write_eqdsk(document, path)

    parsed = read_eqdsk(path)

    assert parsed["header_scalars"][0, 3] == 7.5
    np.testing.assert_array_equal(parsed["R"][0], [0.0, 1.0])
    np.testing.assert_array_equal(parsed["Z"][:, 0], [-1.0, 1.0])


def test_public_docstring_states_the_fixed_origin_and_standard_reader():
    doc = inspect.getdoc(read_eqdsk) or ""

    assert "R origin 0" in doc
    assert "opaque dialect values" in doc
    assert "scirel.io.read_geqdsk" in doc
