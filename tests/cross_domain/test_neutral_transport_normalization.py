"""Bounded SI/spatial equivalence through real neutral transport consumers."""

from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    aggregate_elastic_regeneration_source,
    assemble_neutral_boltzmann_rhs,
    assemble_neutral_total_collision_frequency,
    assemble_neutral_upwind_transport_coefficients,
    assemble_simple_charge_exchange_source,
    contract_atomic_hydrogen_alpha_frequencies,
    make_cylindrical_velocity_quadrature,
    propagate_neutral_generation,
    reduce_atomic_scattered_sources,
    reduce_molecular_scattered_sources,
    sum_elastic_frequency_channels,
)


def _first_flight(vx, coefficients, boundary):
    return propagate_neutral_generation(
        vx,
        *(coefficients[name] for name in ("Ak", "Bk", "Fk", "Ck", "Dk", "Gk")),
        generation_kind="first_flight",
        incoming_boundary=boundary,
    )


def test_wall_inverse_length_connects_to_transport_and_physical_rhs():
    """D=2 m, u_r=1 gives alpha=1/m and nu=5000/s, not 1/s."""
    vx = np.array([-1.0, 1.0])
    shape = (1, 2, 2)
    zero = np.zeros(shape)
    alpha = assemble_neutral_total_collision_frequency(
        [1.0],
        vx,
        base_loss_frequency_m_inv=[0.0, 0.0],
        elastic_frequency_m_inv=[0.0, 0.0],
        pipe_diameter_m=[2.0, 2.0],
        charge_exchange_enabled=False,
    )
    np.testing.assert_array_equal(alpha, np.ones(shape))
    coefficient = assemble_neutral_upwind_transport_coefficients(
        [0.0, 1.0],
        vx,
        collision_frequency_m_inv=alpha,
        source_distribution=zero,
    )
    propagated = _first_flight(vx, coefficient, np.ones((1, 2)))
    np.testing.assert_allclose(propagated[0, 1, 1], 1.0 / 3.0, rtol=1e-14)
    # Independent physical collision balance: nu_wall=2*v_r/D=5000/s.
    rhs = assemble_neutral_boltzmann_rhs(
        5000.0,
        zero,
        zero,
        collision_frequency_m_inv=alpha,
        total_distribution=np.ones(shape),
        elastic_source_sum=zero,
        wall_source_sum=zero,
    )["rhs"]
    np.testing.assert_array_equal(rhs, np.full(shape, -5000.0))


@pytest.mark.parametrize("vth", [2500.0, 5000.0])
def test_physical_attenuation_and_stationary_source_use_same_speed(vth):
    """Physical nu/v equals spatial alpha/u; a balanced physical source stays F."""
    vx = np.array([-1.0, 1.0])
    errors = []
    nu_s_inv = 1500.0 + 500.0 + 2000.0
    exact = np.exp(-nu_s_inv / vth)
    for nx in (21, 41):
        x = np.linspace(0.0, 1.0, nx)
        shape = (1, 2, nx)
        alpha = assemble_neutral_total_collision_frequency(
            [1.0],
            vx,
            np.full(nx, 1500.0 / vth),
            np.full(nx, 500.0 / vth),
            np.zeros(nx),
            np.full(shape, 2000.0 / vth),
        )
        coefficient = assemble_neutral_upwind_transport_coefficients(
            x,
            vx,
            alpha,
            np.zeros(shape),
        )
        generation = _first_flight(vx, coefficient, np.ones((1, 2)))
        errors.append(abs(generation[0, 1, -1] - exact))
        # Q=nu*F in F/s. The spatial solver consumes Q/Vth in F/m.
        f_equilibrium = 7.0
        spatial_source = np.full(shape, nu_s_inv * f_equilibrium / vth)
        coefficient = assemble_neutral_upwind_transport_coefficients(
            x,
            vx,
            alpha,
            spatial_source,
        )
        equilibrium = _first_flight(vx, coefficient, np.full((1, 2), f_equilibrium))
        np.testing.assert_allclose(equilibrium[:, 1, :], f_equilibrium, rtol=2e-14)
        zero = np.zeros(shape)
        rhs = assemble_neutral_boltzmann_rhs(
            vth,
            spatial_source,
            zero,
            alpha,
            np.full(shape, f_equilibrium),
            zero,
            zero,
        )["rhs"]
        np.testing.assert_allclose(rhs, 0.0, atol=1e-11)
    # This characteristic has the trapezoidal method's second-order spatial error.
    assert 3.9 < errors[0] / errors[1] < 4.1


@pytest.mark.parametrize("vth", [2500.0, 5000.0])
def test_alpha_cx_elastic_source_sums_and_rhs_preserve_number_balance(vth):
    """SIG[m^2]*density gives alpha[m^-1]; only RHS restores physical time."""
    vr = np.array([0.5, 1.5])
    vx = np.array([-1.5, -0.5, 0.5, 1.5])
    quad = make_cylindrical_velocity_quadrature(vr=vr, vx=vx)
    volume = quad["volume"]
    shape = (vr.size, vx.size, 2)
    h = np.broadcast_to(np.full(volume.shape, 1.0 / volume.sum())[:, :, None], shape)
    previous_shape = np.exp(-(vr[:, None] ** 2) - (vx[None, :] - 0.4) ** 2)
    previous_shape /= np.sum(volume * previous_shape)
    previous = previous_shape[:, :, None] * np.array([2e12, 3e12])[None, None, :]
    ion_density = np.array([4e12, 5e12])
    n_velocity = volume.size
    # A positive cross-section/speed kernel; physical K has m^3/s,
    # while the actual Alpha producer accepts SIG=K/Vth in m^2.
    reduced_relative_speed = 0.5 + np.arange(n_velocity)[:, None] / n_velocity
    reduced_relative_speed = np.broadcast_to(reduced_relative_speed, (n_velocity, n_velocity))
    physical_kernel = 1e-15 * vth * reduced_relative_speed * volume.reshape(-1, order="F")
    zero_matrix = np.zeros((n_velocity, n_velocity))
    zeros = np.zeros(shape)
    alpha_cx = contract_atomic_hydrogen_alpha_frequencies(
        physical_kernel / vth,
        zero_matrix,
        zero_matrix,
        zero_matrix,
        h,
        ion_density,
        zeros,
        zeros,
    )["Alpha_CX"]
    physical_nu_cx = np.empty(shape)
    for k in range(shape[2]):
        physical_nu_cx[:, :, k] = (
            physical_kernel @ (h[:, :, k] * ion_density[k]).reshape(-1, order="F")
        ).reshape(volume.shape, order="F")
    np.testing.assert_allclose(vth * alpha_cx, physical_nu_cx, rtol=2e-15)
    beta_cx = assemble_simple_charge_exchange_source(
        h,
        charge_exchange_frequency_m_inv=alpha_cx,
        previous_generation_distribution=previous,
        cylindrical_weight=np.broadcast_to(quad["radial_measure"][:, None], volume.shape),
        dvx=quad["dvx"],
    )
    physical_q_cx = h * np.sum(volume[:, :, None] * physical_nu_cx * previous, axis=(0, 1))
    np.testing.assert_allclose(vth * beta_cx, physical_q_cx, rtol=2e-15)
    # The target's density factor is not inferred: doubling h doubles Q/Vth.
    doubled = assemble_simple_charge_exchange_source(
        2.0 * h,
        alpha_cx,
        previous,
        np.broadcast_to(quad["radial_measure"][:, None], volume.shape),
        quad["dvx"],
    )
    np.testing.assert_array_equal(doubled, 2.0 * beta_cx)
    omega = sum_elastic_frequency_channels(
        frequency_profiles_m_inv=[np.full(2, nu / vth) for nu in (100.0, 150.0, 250.0)]
    )["elastic_frequency_m_inv"]
    beta_elastic = aggregate_elastic_regeneration_source(
        frequencies_m_inv={"elastic": omega},
        regenerated_distributions={"elastic": previous},
    )
    np.testing.assert_allclose(vth * beta_elastic, 500.0 * previous, rtol=2e-15)
    alpha = assemble_neutral_total_collision_frequency(
        vr, vx, np.zeros(2), omega, np.zeros(2), alpha_cx
    )
    atomic_source = reduce_atomic_scattered_sources(beta_cx, beta_elastic)
    molecular_source = reduce_molecular_scattered_sources(zeros, beta_cx, beta_elastic)
    np.testing.assert_array_equal(atomic_source, molecular_source)
    physical_balance = physical_q_cx + 500.0 * previous - (physical_nu_cx + 500.0) * previous
    for summed_source in (atomic_source, molecular_source):
        rhs = assemble_neutral_boltzmann_rhs(
            vth, summed_source, zeros, alpha, previous, zeros, zeros
        )["rhs"]
        np.testing.assert_allclose(rhs, physical_balance, rtol=2e-13, atol=0.5)
        # CX redistributes velocity but a unit-integral h preserves particle number.
        assert np.any(np.abs(rhs) > 1.0)
        loss_integral = np.sum(volume[:, :, None] * physical_nu_cx * previous, axis=(0, 1))
        residual = np.sum(volume[:, :, None] * rhs, axis=(0, 1))
        np.testing.assert_allclose(residual / loss_integral, 0.0, atol=2e-12)
