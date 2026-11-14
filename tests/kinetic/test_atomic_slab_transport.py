"""Self-contained behavior checks for the review-only slab candidate.

The synthetic inputs exercise composition and stopping behavior. They do not
reconstruct the old private case or provide an independent physical reference.
``tests/conftest.py`` makes the candidate importable only in the review harness.
"""

import numpy as np
import pytest

from scirel.kinetic.atomic_slab_transport import solve_atomic_slab_transport


@pytest.fixture
def slab_inputs():
    # Four aligned spatial samples, positive temperatures/density, and a short
    # slab keep this a small transport exercise. The mesh inserts one positive
    # energy node into three base radial nodes and supplies both axial branches.
    # Only fields consumed by the current candidate are supplied. In particular,
    # incident.density_m3 retains its existing use as the boundary target;
    # no density-to-flux conversion or private-case normalization is assumed.
    return {
        "profiles": {
            "x": [0.0, 1.0e-4, 2.0e-4, 3.0e-4],
            "Ti": [5.0] * 4,
            "Te": [5.0] * 4,
            "n": [1.0e18] * 4,
            "mu": 2.0,
        },
        "configuration": {"kinetic_h": {"mesh_size": 3}},
        "incident": {"energies_eV": [3.0], "density_m3": 1.0e15},
        "pipe_diameter_m": [0.0] * 4,
        # A small positive threshold keeps the short runs focused on the cap.
        "solver": {"truncate": 1.0e-30, "max_generations": 3},
    }


def test_atomic_slab_generation_cap_preserves_generations_and_accumulation(slab_inputs):
    results = []
    for limit in (1, 2, 3):
        slab_inputs["solver"]["max_generations"] = limit
        result = solve_atomic_slab_transport(slab_inputs)
        results.append(result)

        assert result["schema"] == "scirel.atomic-slab-transport.v1"
        np.testing.assert_array_equal(result["x_m"], slab_inputs["profiles"]["x"])
        assert result["vr"].shape == (4,)
        assert result["vx"].shape == (8,)
        assert np.isfinite(result["vr"]).all()
        assert np.isfinite(result["vx"]).all()
        assert np.any(result["vx"] < 0.0) and np.any(result["vx"] > 0.0)
        assert np.isfinite(result["normalization_temperature_ev"])
        assert result["normalization_temperature_ev"] > 0.0

        distribution = result["distribution"]
        generations = result["generation_distributions"]
        assert distribution.shape == (4, 8, 4)
        assert generations.shape == (limit, 4, 8, 4)
        assert np.isfinite(distribution).all()
        assert np.isfinite(generations).all()
        assert np.all(distribution >= 0.0)
        assert np.all(generations >= 0.0)
        assert np.any(generations > 0.0, axis=(1, 2, 3)).all()
        # This checks returned bookkeeping, not the transport formula.
        np.testing.assert_allclose(distribution, generations.sum(axis=0), rtol=2.0e-15, atol=0.0)

        for name in (
            "density_m3",
            "particle_flux_m2_s",
            "flow_velocity_m_s",
            "pressure_ev_m3",
            "temperature_ev",
            "random_heat_flux_w_m2",
            "ionization_source_m3_s",
            "recombination_source_m3_s",
        ):
            assert result[name].shape == (4,), name
            assert np.isfinite(result[name]).all(), name
        assert np.all(result["density_m3"] > 0.0)
        assert np.all(result["recombination_source_m3_s"] > 0.0)
        assert result["charge_exchange_frequency_m_inv"].shape == distribution.shape
        assert np.isfinite(result["charge_exchange_frequency_m_inv"]).all()
        assert np.all(result["charge_exchange_frequency_m_inv"] > 0.0)

        assert result["generation_count"] == limit
        assert result["generation_stopped"] is False
        assert result["generation_stop_reason"] == "max_generations"
        assert np.isfinite(result["generation_delta"])
        assert result["generation_delta"] >= slab_inputs["solver"]["truncate"]

    # Raising the cap preserves earlier generations and adds nonzero transport.
    # Density must also include the added generations, rather than a stale first
    # generation moment. No leaf formula is repeated to calculate an oracle.
    for shorter, longer in zip(results[:-1], results[1:]):
        np.testing.assert_array_equal(
            shorter["generation_distributions"],
            longer["generation_distributions"][: shorter["generation_count"]],
        )
        assert np.any(longer["distribution"] > shorter["distribution"])
        assert np.all(longer["density_m3"] > shorter["density_m3"])


@pytest.mark.parametrize(("truncate", "generation_count"), [(2.0, 1), (1.0, 2)])
def test_atomic_slab_reports_threshold_stop_before_cap(slab_inputs, truncate, generation_count):
    slab_inputs["solver"]["truncate"] = truncate
    result = solve_atomic_slab_transport(slab_inputs)

    assert result["generation_stopped"] is True
    assert result["generation_stop_reason"] == "truncate"
    assert result["generation_count"] == generation_count
    assert generation_count < slab_inputs["solver"]["max_generations"]
    assert result["generation_distributions"].shape == (generation_count, 4, 8, 4)
    assert np.isfinite(result["generation_delta"])
    assert 0.0 < result["generation_delta"] < truncate
    np.testing.assert_allclose(
        result["distribution"],
        result["generation_distributions"].sum(axis=0),
        rtol=2.0e-15,
        atol=0.0,
    )


def test_atomic_slab_rejects_nonmapping_input():
    with pytest.raises(ValueError, match="inputs must be a mapping"):
        solve_atomic_slab_transport([])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("Ti", [5.0] * 3, "aligned one-dimensional arrays"),
        ("Ti", [0.0] * 4, "positive temperatures"),
        ("Te", [-1.0] * 4, "positive temperatures"),
        ("n", [-1.0] * 4, "nonnegative density"),
        ("n", [np.nan] * 4, "profiles must be finite"),
        ("x", [0.0, 1.0e-4, 1.0e-4, 3.0e-4], "finite positive spatial steps"),
    ],
)
def test_atomic_slab_rejects_invalid_profiles(slab_inputs, field, value, message):
    slab_inputs["profiles"][field] = value
    with pytest.raises(ValueError, match=message):
        solve_atomic_slab_transport(slab_inputs)


@pytest.mark.parametrize("limit", [0, -1])
def test_atomic_slab_rejects_nonpositive_generation_cap(slab_inputs, limit):
    slab_inputs["solver"]["max_generations"] = limit
    with pytest.raises(ValueError, match="solver.max_generations must be a positive integer"):
        solve_atomic_slab_transport(slab_inputs)


@pytest.mark.parametrize("truncate", [0.0, np.nan])
def test_atomic_slab_rejects_invalid_stopping_threshold(slab_inputs, truncate):
    slab_inputs["solver"]["truncate"] = truncate
    with pytest.raises(ValueError, match="truncate"):
        solve_atomic_slab_transport(slab_inputs)


@pytest.mark.parametrize(
    ("diameter", "message"),
    [
        ("unspecified", "string must declare the zero-pipe contract"),
        ([0.0, 0.0], "x-aligned array"),
    ],
)
def test_atomic_slab_rejects_invalid_pipe_input(slab_inputs, diameter, message):
    slab_inputs["pipe_diameter_m"] = diameter
    with pytest.raises(ValueError, match=message):
        solve_atomic_slab_transport(slab_inputs)
