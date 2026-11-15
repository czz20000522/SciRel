"""Public model selection preserves each original coefficient fit's API results."""

import numpy as np
import pytest

import scirel.neoclassical as neoclassical
from scirel.neoclassical import bootstrap

INPUTS = ([0.2, 0.7], [0.01, 10.0], [1.0, 2.0], [0.03, 2.0])
# Captured at aa36536f, before replacing the two public entry points. These
# values test interface migration; they are not independent physical oracles.
EXPECTED = {
    "redl": [
        [0.25891715355093914, 0.09794884455187292],
        [-0.13741101388531185, 0.15025026175687706],
        [0.25891715355093914, 0.09794884455187292],
        [-0.9253856004084087, 0.9909687335480339],
    ],
    "sauter": [
        [0.2782440448905807, 0.20512493408305033],
        [-0.15025947242076929, 0.12447614545341956],
        [0.27813108140753395, 0.17465414407652444],
        [-0.870010942879218, -0.01796197337373604],
    ],
}


@pytest.mark.parametrize("method", ["redl", "sauter"])
def test_selecting_each_method_preserves_all_four_existing_arrays(method):
    result = neoclassical.compute_bootstrap_coefficients(*INPUTS, method=method)
    assert list(result) == ["L31", "L32", "L34", "alpha"]
    for key, expected in zip(result, EXPECTED[method]):
        np.testing.assert_array_equal(result[key], expected)
        assert getattr(result, key) is result[key]


def test_default_is_the_declared_redl_method():
    default = neoclassical.compute_bootstrap_coefficients(*INPUTS)
    explicit = neoclassical.compute_bootstrap_coefficients(*INPUTS, method="redl")
    for key in default:
        np.testing.assert_array_equal(default[key], explicit[key])


@pytest.mark.parametrize("method", ["unknown", "REDL", ""])
def test_unknown_method_names_give_the_closed_choices_and_contract(method):
    with pytest.raises(
        ValueError, match="method.*redl.*sauter.*scirel.neoclassical.bootstrap-coefficients"
    ):
        neoclassical.compute_bootstrap_coefficients(*INPUTS, method=method)


@pytest.mark.parametrize("method", [None, 1, ["redl"], np.array(["redl"])])
def test_nonstring_method_is_rejected_before_a_model_runs(method):
    with pytest.raises(TypeError, match="method.*str.*scirel.neoclassical.bootstrap-coefficients"):
        neoclassical.compute_bootstrap_coefficients(*INPUTS, method=method)


def test_selector_is_keyword_only_and_no_unimplemented_control_is_silently_ignored():
    with pytest.raises(TypeError):
        neoclassical.compute_bootstrap_coefficients(*INPUTS, "sauter")
    for method in ("redl", "sauter"):
        with pytest.raises(TypeError, match="order"):
            neoclassical.compute_bootstrap_coefficients(*INPUTS, method=method, order=8)


def test_existing_method_specific_charge_domain_is_preserved():
    inputs = ([0.2, 0.7], [0.01, 10.0], [0.5, 0.5], [0.03, 2.0])
    result = neoclassical.compute_bootstrap_coefficients(*inputs, method="sauter")
    assert all(np.isfinite(array).all() for array in result.values())
    with pytest.raises(ValueError, match="Z_eff"):
        neoclassical.compute_bootstrap_coefficients(*inputs, method="redl")


@pytest.mark.parametrize("module", [neoclassical, bootstrap])
@pytest.mark.parametrize("name", ["calculate_sauter_coefficients", "calculate_redl_coefficients"])
def test_old_public_entries_are_removed_without_aliases(module, name):
    assert name not in module.__all__
    assert not hasattr(module, name)
