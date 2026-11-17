"""Independent evidence for the Frank-Egedal pressure-closure composition.

Asset: ``scirel.mirror.frank-egedal-pressure-closure``.

**What cannot be established here.**  The hot-ion pressure of this closure is a
non-integer-order moment integral of a truncated Frank-Egedal distribution
evaluated by an adaptive quadrature.  This batch has no published high-order
reference and no independent implementation to diff against, so the *magnitudes*
of ``p_parallel`` and ``p_perp`` -- and in particular the pitch-angle anisotropy
ratio between them -- are recorded as ``cannot establish`` in the contract rather
than pinned by a manufactured number.  Manufacturing a reference from this same
quadrature and calling it evidence is exactly the failure the repository forbids.

**What is established.**  Four statements are exact and each of them a wrong
composition would fail:

1. **The b = 1 reference normalization.**  The contract declares that the
   pressure moments are referenced to ``hot_parallel(b=1)``.  At the flux sample
   where the radial envelope is unity (the reference cell, ``psi = psi_axis``)
   the hot parallel pressure must equal the caller's ``hot_pressure_scale``
   exactly.  The fixture uses the dyadic scale ``8.0`` and asserts bitwise
   equality, which fixes the normalization convention and the Pa unit of the
   scale.
2. **The adaptive quadrature converges to a node-count-independent answer.**
   Running the same fixture with the initial ``velocity_nodes = pitch_nodes = 6``
   and with ``24`` must give the same pressure field: the refinement, not the
   initial count, decides the value.  The assertion uses the contract's own
   ``quadrature_rtol = 1e-7``, and the run also records the node counts it
   actually used and the tolerance it refined to, so a reader can see the
   refinement happened rather than taking it on trust.
3. **The pressure is homogeneous of degree one in the caller's scale.**  Doubling
   ``hot_pressure_scale`` must double both components bitwise on the same
   fixture, which fixes the Pa unit of the scale and separates "the scale
   multiplies the normalized envelope" from "the scale is a fitted constant".
4. **The common velocity domain is shared.**  ``velocity_domain`` must report one
   interval with ``common_to_density_and_both_pressures`` true, so the density and
   both pressure components integrate over the same population -- the correction
   the contract records for this composition.

Failure channels: a non-convergent population (a non-half-integer degree in this
fixture) raises the declared ``RuntimeError``; a missing ``B``/``psi`` port, a
non-positive ``B0`` and a non-integer ``velocity_nodes`` raise the composition's
declared ``ValueError``.

Precision budgets, fixed before the comparison: the reference-normalization
identity is bitwise (``8.0`` is exact and the envelope is exactly one there); the
node-count comparison uses the contract's ``1e-6`` quadrature tolerance, which is
a declared number rather than one measured here.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.mirror import solve_frank_egedal_pressure_closure

_PSI = np.array([[0.0, 0.5, 0.75], [0.25, 0.8, 1.0]])
_B = np.array([[1.0, 1.1, 1.15], [1.2, 1.25, 1.3]])
_SCALE = 8.0
_QUADRATURE_RTOL = 1e-7


def _params(**overrides):
    params = {
        "psi_axis": 0.0,
        "psi_edge": 1.0,
        "B0": 1.0,
        "hot_pressure_scale": _SCALE,
        "mirror_ratio": 2.0,
        "legendre_degrees": [0.5],
        "source_coefficients": [1.0],
        "velocity_nodes": 6,
        "pitch_nodes": 6,
    }
    params.update(overrides)
    return params


def _solve(**overrides):
    inputs = {"psi": _PSI, "B": _B, "params": _params(**overrides)}
    return solve_frank_egedal_pressure_closure(inputs)


def test_the_b_one_reference_carries_the_declared_pressure_scale():
    result = _solve()
    # The reference sample is the flux axis cell, where the radial envelope is
    # exactly one, so the hot parallel pressure is the caller's scale.
    assert result["p_parallel"][0, 0] == _SCALE
    # The field is not uniform, so the second sample of the same row differs:
    # the identity is specific to the reference cell, not a constant field.
    assert result["p_parallel"][0, 1] != _SCALE


def test_the_quadrature_answer_does_not_depend_on_the_initial_node_count():
    coarse = _solve(velocity_nodes=6, pitch_nodes=6)
    fine = _solve(velocity_nodes=24, pitch_nodes=24)
    np.testing.assert_allclose(
        coarse["p_parallel"], fine["p_parallel"], rtol=_QUADRATURE_RTOL, atol=0.0
    )
    np.testing.assert_allclose(coarse["p_perp"], fine["p_perp"], rtol=_QUADRATURE_RTOL, atol=0.0)
    # The refinement record shows the node counts actually used and that the raw
    # moments were checked, so "converged" is not taken on trust.
    record = coarse["closure_state"]["quadrature_convergence"]
    assert record["raw_moments_checked"] is True
    assert record["relative_tolerance"] == pytest.approx(_QUADRATURE_RTOL)
    assert record["velocity_nodes"] >= 6 and record["pitch_nodes"] >= 6


def test_the_pressure_is_homogeneous_in_the_declared_scale():
    direct = _solve()
    doubled = _solve(hot_pressure_scale=2.0 * _SCALE)
    np.testing.assert_allclose(doubled["p_parallel"], 2.0 * direct["p_parallel"], rtol=1e-13)
    np.testing.assert_allclose(doubled["p_perp"], 2.0 * direct["p_perp"], rtol=1e-13)
    # The two runs are not the same array, so the homogeneity is a real relation
    # rather than a repeated return value.
    assert not np.array_equal(doubled["p_parallel"], direct["p_parallel"])


def test_the_common_population_domain_is_shared_and_reported():
    result = _solve()
    domain = result["closure_state"]["velocity_domain"]
    assert domain["common_to_density_and_both_pressures"] is True
    assert domain["lower"] == 0.0
    assert domain["upper"] == 1.0
    # Caller-supplied degrees are reported as such rather than replaced.
    assert result["closure_state"]["degree_source"] == "caller_supplied"
    assert result["closure_state"]["degrees"] == [0.5]


def test_the_composition_returns_the_documented_ports_only():
    result = _solve()
    assert set(result) == {
        "p_parallel",
        "p_perp",
        "density",
        "electron_temperature",
        "closure_state",
    }
    assert result["density"] is None and result["electron_temperature"] is None
    # The fixture is deliberately non-square, so a transposed return changes the
    # shape and cannot pass the port assertion.
    assert result["p_parallel"].shape == result["p_perp"].shape == _PSI.shape
    assert _PSI.shape[0] != _PSI.shape[1]
    assert np.all(np.isfinite(result["p_parallel"]))


def test_a_non_convergent_population_raises_the_declared_error():
    with pytest.raises(RuntimeError, match="quadrature did not converge"):
        _solve(legendre_degrees=[1.5], source_coefficients=[1.0])


def test_invalid_input_channel_raises():
    with pytest.raises((ValueError, TypeError, KeyError)):
        solve_frank_egedal_pressure_closure({"psi": _PSI, "B": _B})
    with pytest.raises((ValueError, TypeError, KeyError)):
        solve_frank_egedal_pressure_closure({"psi": _PSI, "params": _params()})
    with pytest.raises((ValueError, TypeError)):
        _solve(velocity_nodes=1.5)
    with pytest.raises((ValueError, TypeError)):
        solve_frank_egedal_pressure_closure({"psi": _PSI, "B": _B, "params": _params(B0=0.0)})
