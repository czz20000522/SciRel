"""Analytic contour/writer criteria fixed before held-out repair output."""
import numpy as np
import pytest

from scirel.io import eqdsk


@pytest.mark.parametrize('sign', [1., -1.])
def test_raw_cylindrical_contours_are_sign_independent_and_on_surface(tmp_path, sign):
    R, Z = np.meshgrid(np.linspace(0., 1.2, 121), np.linspace(-1., 1., 101))
    psi = sign*R**2
    path = tmp_path/'cylinder.eqdsk'
    eqdsk.write_eqdsk_legacy_raw(R, Z, psi, np.ones(R.shape), path, 'cylinder')
    got = eqdsk.read_eqdsk(path)
    assert got['nnv'] == 101
    assert got['nlim_pairs'] == got['nves_pairs'] == 100
    np.testing.assert_allclose(got['psi'], psi, rtol=1e-9, atol=1e-10)
    np.testing.assert_allclose(got['lim_pairs'][:, 0], .6, rtol=0, atol=1e-9)
    np.testing.assert_allclose(got['ves_pairs'][:, 0]**2, .36*1.02, rtol=0, atol=3e-5)
    np.testing.assert_allclose(got['lim_pairs'][[0, -1], 1], [.5, -.5], rtol=0, atol=1e-9)
    assert got['Ip'] == R.size


def test_raw_heldout_elliptic_contour_uses_parametric_geometry(tmp_path):
    R, Z = np.meshgrid(np.linspace(0., 1.2, 241), np.linspace(-1., 1., 201))
    psi = (R-.3)**2+Z**2
    path = tmp_path/'ellipse.eqdsk'
    eqdsk.write_eqdsk_legacy_raw(R, Z, psi, -np.ones(R.shape), path, 'ellipse')
    got = eqdsk.read_eqdsk(path)
    for key, level in [('lim_pairs', .09), ('ves_pairs', .09*1.02)]:
        pairs = got[key]
        np.testing.assert_allclose((pairs[:, 0]-.3)**2+pairs[:, 1]**2,
                                   level, rtol=0, atol=1e-4)
        assert np.all(np.isfinite(pairs))
        assert np.all(np.linalg.norm(np.diff(pairs, axis=0), axis=1)>0.)
    assert got['Ip'] == -R.size
    assert got['cursign'] == -1


def test_raw_missing_contour_preserves_destination_and_closes_figure(tmp_path):
    import matplotlib.pyplot as plt
    R, Z = np.meshgrid(np.linspace(0., 1.2, 121), np.linspace(-1., 1., 101))
    path = tmp_path/'existing.eqdsk'
    path.write_text('protected')
    before = plt.get_fignums()
    with pytest.raises(eqdsk.EQDSKFormatError, match='contour'):
        eqdsk.write_eqdsk_legacy_raw(R, Z, R*0, R*0, path, 'zero')
    assert path.read_text() == 'protected'
    assert plt.get_fignums() == before


def test_raw_arbitrary_origin_is_not_silently_shifted(tmp_path):
    R, Z = np.meshgrid(np.linspace(.2, 1.4, 121), np.linspace(-1., 1., 101))
    path = tmp_path/'existing.eqdsk'
    path.write_text('protected')
    with pytest.raises(eqdsk.EQDSKFormatError, match='representable'):
        eqdsk.write_eqdsk_legacy_raw(R, Z, R**2, R*0, path, 'offset')
    assert path.read_text() == 'protected'


def test_resampling_is_invariant_to_open_contour_reversal():
    arc = np.column_stack([np.full(9, .6), np.linspace(-1., 1., 9)])
    forward = eqdsk._resample_contour(arc, 100, (.05, .5), (.05, -.5))
    reverse = eqdsk._resample_contour(arc[::-1], 100, (.05, .5), (.05, -.5))
    np.testing.assert_array_equal(forward, reverse)
