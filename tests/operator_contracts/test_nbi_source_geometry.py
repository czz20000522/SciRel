"""Direct contract tests for the r75 FIDASIM N2 source-geometry operator family:
``construct_nbi_source_ray`` (saved package ``NBI源面射线与孔径接受``, the
``mc_nbi`` source-plane branch) and ``intersect_ray_with_rectilinear_grid``
(saved package ``有限直角束网格射线交点``, the finite ``grid_intersect``
branch).

The saved packages' own probes (centerline rectangle acceptance, forward and
reverse face ordering, degenerate zero-length returns) are reproduced.
Registered hardenings -- finite focus lengths and divergences, bool rejection
of the source shape, the finite-output gate on the ray outputs, finite grid
lengths, and the finite-output gate on the intersection geometry --
discriminate against the saved arms' silent NaN/Inf returns.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.fusion import construct_nbi_source_ray, intersect_ray_with_rectilinear_grid


def _source_ray_kwargs(**overrides):
    kwargs = dict(
        source_uniform=[0.5, 0.5], divergence_normal=[0.0, 0.0],
        source_shape=1, half_width_y_cm=2.0, half_width_z_cm=3.0,
        focus_y_cm=10.0, focus_z_cm=10.0,
        divergence_y_rad=0.1, divergence_z_rad=0.1,
        aperture_distance_cm=[5.0], aperture_shape=[1],
        aperture_offset_y_cm=[0.0], aperture_offset_z_cm=[0.0],
        aperture_half_width_y_cm=[1.0], aperture_half_width_z_cm=[1.0],
        beam_basis=np.eye(3), beam_source_cm=[1.0, 2.0, 3.0],
    )
    kwargs.update(overrides)
    return kwargs


# ------------------- source-plane ray: saved probe and mapping -------------------

def test_centerline_rectangle_matches_the_saved_probe():
    source, direction, accepted = construct_nbi_source_ray(**_source_ray_kwargs())
    assert np.allclose(source, [1.0, 2.0, 3.0])
    assert np.allclose(direction, [1.0, 0.0, 0.0])
    assert accepted


def test_rectangle_source_maps_the_uniform_pair_affinely():
    source, _, _ = construct_nbi_source_ray(**_source_ray_kwargs(
        source_uniform=[0.25, 0.75], beam_source_cm=[0.0, 0.0, 0.0]))
    # y = 2 * 2 * (0.25 - 0.5) = -1, z = 3 * 2 * (0.75 - 0.5) = 1.5
    np.testing.assert_allclose(source, [0.0, -1.0, 1.5], rtol=1e-15)


def test_ellipse_source_uses_sqrt_and_2pi_mapping():
    source, _, _ = construct_nbi_source_ray(**_source_ray_kwargs(
        source_uniform=[0.25, 0.5], source_shape=2, beam_source_cm=[0.0, 0.0, 0.0]))
    rho, theta = np.sqrt(0.25), np.pi
    np.testing.assert_allclose(
        source, [0.0, 2.0 * rho * np.cos(theta), 3.0 * rho * np.sin(theta)], rtol=1e-15)


def test_ray_carries_focus_and_divergence_terms_and_stays_unit():
    _, ray, _ = construct_nbi_source_ray(**_source_ray_kwargs(
        source_uniform=[0.0, 1.0], divergence_normal=[1.0, -1.0],
        beam_source_cm=[0.0, 0.0, 0.0]))
    # y = -(-2)/10 + tan(0.1 * 1), z = -(3)/10 + tan(0.1 * -1)
    expected = np.array([1.0, 0.2 + np.tan(0.1), -0.3 - np.tan(0.1)])
    np.testing.assert_allclose(ray, expected / np.linalg.norm(expected), rtol=1e-15)
    assert np.isclose(np.linalg.norm(ray), 1.0, rtol=1e-15)


def test_beam_basis_transforms_source_and_ray_together():
    angle = 0.7
    basis = np.array([
        [np.cos(angle), -np.sin(angle), 0.0],
        [np.sin(angle), np.cos(angle), 0.0],
        [0.0, 0.0, 1.0],
    ])
    origin = [4.0, -2.0, 1.0]
    source, ray, accepted = construct_nbi_source_ray(**_source_ray_kwargs(
        beam_basis=basis, beam_source_cm=origin))
    np.testing.assert_allclose(source, basis @ [0.0, 0.0, 0.0] + origin, rtol=1e-15)
    np.testing.assert_allclose(ray, basis @ [1.0, 0.0, 0.0], rtol=1e-15)
    assert accepted


def test_aperture_acceptance_covers_rectangle_ellipse_and_rejection():
    # Rectangle boundary point is accepted (closed comparison).
    _, _, accepted = construct_nbi_source_ray(**_source_ray_kwargs(
        divergence_normal=[1.0, 0.0], aperture_distance_cm=[5.0],
        aperture_half_width_y_cm=[5.0 * np.tan(0.1)]))
    assert accepted
    # Far-offset rectangle rejects.
    _, _, rejected = construct_nbi_source_ray(**_source_ray_kwargs(
        aperture_offset_y_cm=[50.0]))
    assert not rejected
    # Ellipse aperture accepts the centerline and rejects a displaced one.
    _, _, ellipse_ok = construct_nbi_source_ray(**_source_ray_kwargs(aperture_shape=[2]))
    assert ellipse_ok
    _, _, ellipse_no = construct_nbi_source_ray(**_source_ray_kwargs(
        aperture_shape=[2], aperture_offset_z_cm=[50.0]))
    assert not ellipse_no


def test_source_ray_rejects_bad_contracts():
    for overrides in (
        {"source_uniform": [-0.1, 0.5]}, {"source_uniform": [1.1, 0.5]},
        {"source_uniform": [0.5]}, {"divergence_normal": [np.nan, 0.0]},
        {"source_shape": 3}, {"source_shape": True}, {"source_shape": np.bool_(True)},
        {"half_width_y_cm": 0.0}, {"half_width_z_cm": -1.0},
        {"half_width_y_cm": np.nan},
        {"focus_y_cm": 0.0}, {"focus_z_cm": np.nan},
        {"divergence_y_rad": np.nan}, {"divergence_z_rad": np.inf},
        {"beam_basis": np.eye(2)}, {"beam_source_cm": [1.0, 2.0]},
        {"aperture_shape": [3]}, {"aperture_distance_cm": [5.0, 6.0]},
        {"aperture_half_width_z_cm": [np.nan]},
    ):
        with pytest.raises(ValueError):
            construct_nbi_source_ray(**_source_ray_kwargs(**overrides))


def test_source_ray_extreme_geometry_fails_closed_not_silent():
    # half_width 1e308 through focus 0.5 overflows the transverse ray term;
    # the saved arm normalizes the resulting Inf/NaN silently.
    with pytest.raises(ValueError, match="registered hardening"):
        construct_nbi_source_ray(**_source_ray_kwargs(half_width_z_cm=1.0e308, focus_z_cm=0.5))


def test_source_ray_norm_overflow_is_rejected_not_a_zero_unit_ray():
    # half_width 1e200 through focus 1 overflows the beam-ray squared norm to
    # Inf, so beam_ray / Inf collapses to the zero vector; the saved arm (and
    # a finiteness-only gate) would return it as a "unit" ray with accepted
    # still True.  The contract requires a normalizable finite ray instead.
    with pytest.raises(ValueError, match="registered hardening"):
        construct_nbi_source_ray(
            [1, 0.5], [0, 0], 1, 1e200, 1, 1, 1, 0, 0,
            [], [], [], [], [], [], np.eye(3), np.zeros(3))


# ------------------------- beam-grid ray intersection -------------------------

def test_intersection_matches_the_saved_forward_probe():
    result = intersect_ray_with_rectilinear_grid(
        ray_origin_cm=[-2, 0, 0], ray_direction=[1, 0, 0],
        grid_center_cm=[0, 0, 0], grid_lengths_cm=[2, 4, 6])
    assert result["intersects_grid"] and result["intersection_length_cm"] == 2.0
    np.testing.assert_allclose(result["entry_point_cm"], [-1, 0, 0])
    np.testing.assert_allclose(result["exit_point_cm"], [1, 0, 0])


def test_intersection_orders_entry_along_the_direction():
    result = intersect_ray_with_rectilinear_grid(
        ray_origin_cm=[2, 0, 0], ray_direction=[-2, 0, 0],
        grid_center_cm=[0, 0, 0], grid_lengths_cm=[2, 4, 6])
    np.testing.assert_allclose(result["entry_point_cm"], [1, 0, 0])
    np.testing.assert_allclose(result["exit_point_cm"], [-1, 0, 0])
    assert result["intersection_length_cm"] == 2.0


def test_miss_tangential_and_missing_pair_return_origin_zero_length():
    for direction in ([0, 1, 0], [1, 0, 0]):
        result = intersect_ray_with_rectilinear_grid(
            ray_origin_cm=[2, 3, 0], ray_direction=direction,
            grid_center_cm=[0, 0, 0], grid_lengths_cm=[2, 2, 2])
        assert not result["intersects_grid"] and result["intersection_length_cm"] == 0.0
        np.testing.assert_allclose(result["entry_point_cm"], [2, 3, 0])
        np.testing.assert_allclose(result["exit_point_cm"], [2, 3, 0])


def test_intersection_rejects_bad_contracts():
    for kwargs in (
        {"ray_origin_cm": [np.nan, 0, 0]},
        {"ray_direction": [1, 0, np.inf]},
        {"grid_center_cm": [0, 0]},
        {"grid_lengths_cm": [1, 0, 1]},
        {"grid_lengths_cm": [1, np.nan, 1]},
        {"grid_lengths_cm": [-1, 1, 1]},
    ):
        merged = dict(ray_origin_cm=[0, 0, 0], ray_direction=[1, 0, 0],
                      grid_center_cm=[0, 0, 0], grid_lengths_cm=[2, 2, 2])
        merged.update(kwargs)
        with pytest.raises(ValueError):
            intersect_ray_with_rectilinear_grid(**merged)


def test_intersection_chord_through_an_off_axis_diagonal():
    result = intersect_ray_with_rectilinear_grid(
        ray_origin_cm=[-4, 0, 0], ray_direction=[1, 0, 0],
        grid_center_cm=[0, 0, 0], grid_lengths_cm=[2, 4, 6])
    np.testing.assert_allclose(result["entry_point_cm"], [-1, 0, 0])
    np.testing.assert_allclose(result["exit_point_cm"], [1, 0, 0])
    # A ray passing outside the y-bound of a finite grid must miss.
    result = intersect_ray_with_rectilinear_grid(
        ray_origin_cm=[-4, 3.0, 0], ray_direction=[1, 0, 0],
        grid_center_cm=[0, 0, 0], grid_lengths_cm=[2, 4, 6])
    assert not result["intersects_grid"]
