import inspect

from scirel.closures.mirror_quasineutral_closure import solve_mirror_quasineutral_closure
from cross_domain._review_bindings import load_asset as _load_asset
# 覆盖：解析准中性、损失锥闭合、零密度回退与 caller profile(psi) 端口。

import numpy as np

from scirel.closures import mirror_quasineutral_closure as composition

E = 1.602176634e-19
M = 1.67262192595e-27


def _loader(asset_ref):
    return _load_asset(asset_ref)


def _inputs(**overrides):
    inputs = dict(
        b_t=np.array([1.0, 1.4, 2.0]),
        psi=np.zeros(3),
        mass_kg=M,
        charge_c=E,
        density_ref_m3=2e18,
        temperature_parallel_j=1200 * E,
        temperature_perpendicular_ref_j=2400 * E,
        b_ref_t=1.0,
        electron_temperature_j=600 * E,
    )
    inputs.update(overrides)
    return inputs


def test_public_callable_documents_the_catalog_contract():
    text = inspect.getdoc(solve_mirror_quasineutral_closure) or ""
    assert "b_t" in text
    assert "electrostatic potential" in text
    assert "RuntimeError" in text


def test_no_plug_limit_matches_analytic_potential_and_neutrality():
    result = composition._run_composition(_inputs(), asset_loader=_loader)
    b = np.array([1.0, 1.4, 2.0])
    t_perp = b / ((b - 1.0) / (1200 * E) + 1.0 / (2400 * E))
    expected = np.log(t_perp / (2400 * E)) / (E / (1200 * E) + E / (600 * E))
    np.testing.assert_allclose(result["electrostatic_potential"], expected, atol=2e-8)
    assert np.max(np.abs(result["relative_charge_residual"])) < 1e-10


def test_loss_cone_closure_remains_neutral():
    result = composition._run_composition(
        _inputs(
            b_plug_left_t=4.0,
            b_plug_right_t=5.0,
            phi_plug_left_v=800.0,
            phi_plug_right_v=1000.0,
            loss_cone_refill=0.0,
            quadrature_order=40,
        ),
        asset_loader=_loader,
    )
    assert np.all(result["kinetic_moments"]["density_pitch_integral"] < 1.0)
    assert np.max(np.abs(result["relative_charge_residual"])) < 1e-9


def test_zero_density_returns_reference_potential():
    result = composition._run_composition(
        _inputs(density_ref_m3=0.0, phi_ref_v=15.0), asset_loader=_loader
    )
    np.testing.assert_allclose(result["electrostatic_potential"], 15.0)
    np.testing.assert_array_equal(result["ion_density"], 0.0)
    np.testing.assert_array_equal(result["electron_density"], 0.0)
    assert result["iterations"] == 0 and result["converged"] is True


def test_final_moments_and_electrons_are_reevaluated_after_potential_solve():
    events = []

    def tracing_loader(asset_ref):
        implementation = _loader(asset_ref)
        if asset_ref == "scirel.closures.quasineutral_potential":

            def solve(*args, **kwargs):
                events.append("solver_begin")
                result = implementation(*args, **kwargs)
                events.append("solver_end")
                return result

            return solve

        def evaluate(*args, **kwargs):
            events.append(asset_ref)
            return implementation(*args, **kwargs)

        return evaluate

    result = composition._run_composition(_inputs(), asset_loader=tracing_loader)

    assert result["converged"] is True
    assert events[-4:] == [
        "solver_end",
        "scirel.kinetic.mirror_constrained_moments",
        "scirel.closures.boltzmann_quasineutrality",
        "scirel.kinetic.mirror_total_pressure",
    ]


def test_solver_failure_propagates_without_terminal_pressure_assembly():
    import pytest

    failure = RuntimeError("unbracketed potential")

    def failing_loader(asset_ref):
        if asset_ref == "scirel.closures.quasineutral_potential":

            def fail(*_args, **_kwargs):
                raise failure

            return fail
        if asset_ref == "scirel.kinetic.mirror_total_pressure":

            def unexpected(*_args, **_kwargs):
                pytest.fail("terminal pressure assembly ran after solver failure")

            return unexpected
        return _loader(asset_ref)

    with pytest.raises(RuntimeError) as caught:
        composition._run_composition(_inputs(), asset_loader=failing_loader)
    assert caught.value is failure


def test_supplied_electron_reference_density_skips_default_calculation():
    def loader(asset_ref):
        if asset_ref == "scirel.closures.quasineutral_reference_density":

            def unexpected(*_args, **_kwargs):
                raise AssertionError("supplied electron reference was ignored")

            return unexpected
        return _loader(asset_ref)

    result = composition._run_composition(
        _inputs(electron_density_ref_m3=2e18),
        asset_loader=loader,
    )
    assert np.max(np.abs(result["relative_charge_residual"])) < 1e-10


def test_profile_ports_receive_current_psi_values():
    psi = np.array([0.0, 0.2, 0.4])
    density = lambda value: 2e18 * (1.0 + 0.1 * value)
    callable_result = composition._run_composition(
        _inputs(psi=psi, density_ref_m3=density), asset_loader=_loader
    )
    array_result = composition._run_composition(
        _inputs(psi=psi, density_ref_m3=density(psi)), asset_loader=_loader
    )
    np.testing.assert_allclose(callable_result["ion_density"], array_result["ion_density"])
    assert np.max(np.abs(callable_result["relative_charge_residual"])) < 1e-10


def test_contract_propagates_invalid_quasineutral_iteration_budget():
    import pytest

    with pytest.raises(ValueError, match="at least 2"):
        composition._run_composition(
            _inputs(
                max_iterations=1, potential_tolerance_v=1.0e-30, quasineutral_tolerance=1.0e-30
            ),
            asset_loader=_loader,
        )


def test_contract_rejects_fractional_max_iterations_without_truncation():
    import pytest

    with pytest.raises(ValueError, match="max_iterations must be an integer"):
        composition._run_composition(_inputs(max_iterations=3.5), asset_loader=_loader)
