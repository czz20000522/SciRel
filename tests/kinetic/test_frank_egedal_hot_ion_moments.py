import numpy as np
import pytest
from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments, evaluate_frank_egedal_hot_ion_moments as scientific_operator
def test_rejects_incomplete_moment_state():
    with pytest.raises((KeyError,ValueError,TypeError)): scientific_operator({})


def test_perpendicular_velocity_lower_accepts_full_moment_interval():
    mode = lambda degree, xi, terms: 1.0 + 0.0 * xi
    critical = scientific_operator(
        [[1.0]],
        {"B0": 1.0, "mirror_ratio": 20.0, "vc_over_v0": 0.8, "velocity_nodes": 8, "pitch_nodes": 8},
        [0.5],
        [1.0],
        15,
        mode,
    )
    full = scientific_operator(
        [[1.0]],
        {"B0": 1.0, "mirror_ratio": 20.0, "vc_over_v0": 0.8, "perp_velocity_lower": 0.0, "velocity_nodes": 8, "pitch_nodes": 8},
        [0.5],
        [1.0],
        15,
        mode,
    )
    # Omitted and explicit zero cutoff define the SAME population. Critical
    # speed is a slowing-down scale, not an implicit perpendicular-only cut.
    import numpy as np
    np.testing.assert_array_equal(full["hot_perpendicular_shape"], critical["hot_perpendicular_shape"])
    xi2 = 1.0 - 1.0 / 20.0
    np.testing.assert_allclose(full["hot_perpendicular_shape"],
        (3.0 - xi2) / (2.0 * xi2), rtol=2e-12)


def test_reviewed_relation_example():
    import math
    import numpy as np
    from scipy.integrate import quad
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments

    def mode(degree, xi, terms):
        # 一个非恒定的角向模态；改变 degree 必须改变垂直矩。
        return 1.0 + float(degree) * np.asarray(xi, dtype=float)
    base = {
        "B0": 1.0,
        "mirror_ratio": 4.0,
        "vc_over_v0": 0.5,
        "beta_m": 0.0,
        "perp_velocity_lower": 0.25,
        "velocity_nodes": 48,
        "pitch_nodes": 48,
    }
    def independent_perpendicular_shape(degree):
        # 独立自适应求积只重建 B=1 的公开定义，不调用实现内部的求积器。
        xi_mid = math.sqrt(1.0 - 1.0 / base["mirror_ratio"])
        vc = base["vc_over_v0"]
        lower = base["perp_velocity_lower"]
        speed_parallel = quad(lambda v: v**4 / (v**3 + vc**3), lower, 1.0, epsabs=1e-13)[0]
        speed_perp = quad(lambda v: v**4 / (v**3 + vc**3), lower, 1.0, epsabs=1e-13)[0]
        pitch_parallel = quad(lambda xi: xi**2 * (1.0 + degree * xi), 0.0, xi_mid, epsabs=1e-13)[0]
        pitch_perp = quad(lambda xi: (1.0 - xi**2) * (1.0 + degree * xi), 0.0, xi_mid, epsabs=1e-13)[0]
        return 0.5 * speed_perp * pitch_perp / (speed_parallel * pitch_parallel)

    first = evaluate_frank_egedal_hot_ion_moments(
        [[1.0]], base, [0.5], [1.0], 15, mode
    )
    second = evaluate_frank_egedal_hot_ion_moments(
        [[1.0]], base, [1.5], [1.0], 15, mode
    )
    assert np.allclose(first["hot_parallel_shape"], [[1.0]], rtol=2e-12)
    assert np.allclose(first["hot_density_shape"], [[1.0]], rtol=2e-12)
    assert np.allclose(
        first["hot_perpendicular_shape"], [[independent_perpendicular_shape(0.5)]], rtol=2e-12
    )
    assert np.allclose(
        second["hot_perpendicular_shape"], [[independent_perpendicular_shape(1.5)]], rtol=2e-12
    )
    assert not np.isclose(
        first["hot_perpendicular_shape"][0, 0], second["hot_perpendicular_shape"][0, 0]
    )
    assert first["quadrature"] == {"velocity_nodes": 48, "pitch_nodes": 48}


def test_scalar_only_fractional_mode_falls_back_without_contract_change():
    def scalar_only(degree, xi, terms):
        xi = np.asarray(xi)
        if xi.ndim != 2:
            raise ValueError("scalar-only callback")
        return 1.0 + float(degree) * xi

    result = evaluate_frank_egedal_hot_ion_moments(
        np.array([[0.9, 1.0, 1.1], [1.2, 1.0, 0.8]]),
        {"B0": 1.0, "mirror_ratio": 4.0, "velocity_nodes": 8, "pitch_nodes": 8},
        [0.5, 1.5],
        [0.75, -0.2],
        15,
        scalar_only,
    )
    assert np.all(np.isfinite(result["hot_parallel_shape"]))
    assert np.all(np.isfinite(result["hot_perpendicular_shape"]))


def test_fractional_mode_runtime_errors_are_not_hidden_by_batch_fallback():
    def broken(degree, xi, terms):
        raise RuntimeError("fractional mode failed")

    broken._scirel_batch_safe = True

    with pytest.raises(RuntimeError, match="fractional mode failed"):
        evaluate_frank_egedal_hot_ion_moments(
            np.array([[0.9, 1.0, 1.1]]),
            {"B0": 1.0, "mirror_ratio": 4.0, "velocity_nodes": 8, "pitch_nodes": 8},
            [0.5],
            [1.0],
            15,
            broken,
        )


def test_unmarked_shape_sensitive_callback_keeps_scalar_contract():
    seen = []

    def shape_sensitive(degree, xi, terms):
        xi = np.asarray(xi)
        seen.append(xi.ndim)
        return np.ones_like(xi) * (1.0 if xi.ndim == 2 else 2.0)

    evaluate_frank_egedal_hot_ion_moments(
        np.array([[0.9, 1.0, 1.1]]),
        {"B0": 1.0, "mirror_ratio": 4.0, "velocity_nodes": 8, "pitch_nodes": 8},
        [0.5],
        [1.0],
        15,
        shape_sensitive,
    )
    assert set(seen) == {2}
