"""Manual Pleiades record oracle independent of the library's writer."""
from scirel.io import eqdsk as io
import numpy as np
import pytest


def independent_text():
    # Distinct rectangular/profile sizes reveal swapped dimensions; signs and
    # adjacent full fields exercise lexical splitting. No library writer used.
    scalar = np.arange(20, dtype=float).reshape(4, 5)
    scalar[0, :2] = [2.0, 3.0]
    scalar[1, 3] = -0.25
    scalar[2, 0] = -7.0
    profiles = [np.array([1., -2., 3., -4.]), np.array([-1., 2., -3., 4.]),
                np.arange(4.), -np.arange(4.)]
    psi = np.array([[1., -2., 3.], [-4., 5., -6.]])
    q = np.array([0.1, -0.2, 0.3, -0.4])
    pairs = np.array([[.125, -.25], [.5, -.75], [1., -1.25]])
    groups = [*scalar, *profiles, psi.ravel(), q, pairs.ravel()]
    lines = ['INDEPENDENT SIGNED RECTANGULAR ORACLE'.ljust(48) + '  -1   3   2   4']
    for group_i, group in enumerate(groups):
        if group_i == len(groups)-1:
            lines.append('    2    1')
        for start in range(0, len(group), 5):
            lines.append(''.join('%16.9E' % value for value in group[start:start+5]))
    return '\n'.join(lines) + '\n', scalar, profiles, psi, q, pairs


def test_manual_signed_rectangular_record_oracle(tmp_path):
    text, scalar, profiles, psi, q, pairs = independent_text()
    path = tmp_path/'manual.eqdsk'
    path.write_text(text)
    parsed = io.read_pleiades_eqdsk(path)
    assert (parsed['nnr'], parsed['nnz'], parsed['nnv']) == (3, 2, 4)
    assert parsed['cursign'] == -1
    np.testing.assert_array_equal(parsed['header_scalars'], scalar)
    for key, profile in zip(('tor_flux','p_flux','rbphi_flux','pprime_flux'), profiles):
        np.testing.assert_array_equal(parsed[key], profile)
    np.testing.assert_array_equal(parsed['psi'], psi)
    np.testing.assert_array_equal(parsed['q_flux'], q)
    np.testing.assert_array_equal(parsed['lim_pairs'], pairs[:2])
    np.testing.assert_array_equal(parsed['ves_pairs'], pairs[2:])
    # Canonical serializer must recover independently constructed text bytes.
    out = tmp_path/'roundtrip.eqdsk'
    io.write_pleiades_eqdsk(parsed, out)
    assert out.read_bytes() == path.read_bytes()


def test_standard_three_integer_geqdsk_is_not_this_dialect(tmp_path):
    text, *_ = independent_text()
    lines = text.splitlines()
    lines[0] = 'STANDARD GEQDSK IS NOT THE PLEIADES DIALECT'.ljust(48) + '   0   3   2'
    path = tmp_path/'standard.eqdsk'; path.write_text('\n'.join(lines)+'\n')
    with pytest.raises(io.EQDSKFormatError, match='header'):
        io.read_pleiades_eqdsk(path)
