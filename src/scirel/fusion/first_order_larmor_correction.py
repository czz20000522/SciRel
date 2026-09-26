"""FIDASIM source-shaped guiding-center to particle gyro correction.

Source: FIDASIM ``gyro_step`` -- maps a guiding-center state to a particle
state under the source's finite-Larmor-radius (FLR) orders 0, 1 or 2:

- order 0: identity (particle position equals the guiding-center position,
  zero gyro-radius vector, scale 1);
- order 1: ``radius = (v x b_unit) * m/(q B)`` and the particle position is
  displaced by ``-radius``;
- order 2: the radius is additionally scaled by the source's first-order
  correction ``scale = 1 - (v.b)(m/qB)(b_hat.curl b_hat) - (r.grad|B|)/(2B)``
  evaluated from the caller-supplied cylindrical magnetic state
  (12 declared field/derivative components) and the coordinate-to-machine
  rotation matrix; the source rejects scale outside ``(0, 2)``.

``flr_order=None`` reproduces the historical contract (order 1 when
``flr_enabled`` else order 0).  ``flr_order=2`` is undefined on the
cylindrical axis and the source's ``(0, 2)`` scale acceptance window is
preserved verbatim as fail-closed.
"""
from __future__ import annotations

import numpy as np

__all__ = ["first_order_larmor_guiding_center_correction"]

ATOMIC_MASS_KG = 1.660539040e-27
ELEMENTARY_CHARGE_C = 1.60217733e-19


def _vector(value, name):
    result = np.asarray(value, dtype=float)
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite vector of shape (3,)")
    return result


def _cylindrical_state(value):
    if not isinstance(value, dict):
        raise ValueError("flr_order=2 requires cylindrical_magnetic_state")
    names = ("br_t", "bt_t", "bz_t", "dbr_dr_t_cm", "dbr_dphi_t_rad", "dbr_dz_t_cm", "dbt_dr_t_cm", "dbt_dphi_t_rad", "dbt_dz_t_cm", "dbz_dr_t_cm", "dbz_dphi_t_rad", "dbz_dz_t_cm")
    missing = [name for name in names if name not in value]
    if missing:
        raise ValueError("cylindrical_magnetic_state is missing " + ", ".join(missing))
    result = {name: float(value[name]) for name in names}
    if not all(np.isfinite(item) for item in result.values()):
        raise ValueError("cylindrical_magnetic_state values must be finite")
    return result


def first_order_larmor_guiding_center_correction(*, guiding_center_position_cm, ion_velocity_cm_s, magnetic_unit_vector, magnetic_magnitude_t, ion_mass_amu, flr_enabled=True, flr_order=None, guiding_center_machine_position_cm=None, coordinate_to_machine_matrix=None, cylindrical_magnetic_state=None):
    """Map a guiding-center state to a particle state under source FLR order 0, 1, or 2."""
    position = _vector(guiding_center_position_cm, "guiding_center_position_cm")
    velocity = _vector(ion_velocity_cm_s, "ion_velocity_cm_s")
    b_unit = _vector(magnetic_unit_vector, "magnetic_unit_vector")
    if not np.isfinite(magnetic_magnitude_t) or magnetic_magnitude_t <= 0.0 or not np.isfinite(ion_mass_amu) or ion_mass_amu <= 0.0:
        raise ValueError("magnetic_magnitude_t and ion_mass_amu must be finite and positive")
    if not np.isclose(np.linalg.norm(b_unit), 1.0, rtol=0.0, atol=1.0e-12):
        raise ValueError("magnetic_unit_vector must have unit norm")
    if flr_order is None:
        flr_order = 1 if flr_enabled else 0
    if type(flr_order) is not int or flr_order not in (0, 1, 2):
        raise ValueError("flr_order must be 0, 1, or 2")
    if flr_order == 0:
        radius = np.zeros(3)
        return {"particle_position_cm": position, "gyro_radius_vector_cm": radius, "gyro_scale_factor": 1.0}

    one_over_omega = ion_mass_amu * ATOMIC_MASS_KG / (magnetic_magnitude_t * ELEMENTARY_CHARGE_C)
    radius = np.cross(velocity, b_unit) * one_over_omega
    if not np.all(np.isfinite(radius)):
        raise ValueError(
            "gyro radius overflowed for finite but extreme velocity/mass/B "
            "magnitudes (registered hardening)")
    scale = 1.0
    if flr_order == 2:
        machine_position = _vector(guiding_center_machine_position_cm, "guiding_center_machine_position_cm")
        matrix = np.asarray(coordinate_to_machine_matrix, dtype=float)
        if matrix.shape != (3, 3) or not np.all(np.isfinite(matrix)):
            raise ValueError("coordinate_to_machine_matrix must be a finite (3,3) matrix")
        state = _cylindrical_state(cylindrical_magnetic_state)
        radius_machine = matrix @ radius
        radial = float(np.hypot(machine_position[0], machine_position[1]))
        if radial <= 0.0:
            raise ValueError("flr_order=2 is undefined on the cylindrical axis")
        phi = float(np.arctan2(machine_position[1], machine_position[0]))
        sine, cosine = np.sin(phi), np.cos(phi)
        radius_cylindrical = np.array((radius_machine[0] * cosine + radius_machine[1] * sine, -radius_machine[0] * sine + radius_machine[1] * cosine, radius_machine[2]))
        b_cylindrical = np.array((state["br_t"], state["bt_t"], state["bz_t"])) / magnetic_magnitude_t
        curl_unit_field = np.array(((state["dbz_dphi_t_rad"] / radial - state["dbt_dz_t_cm"]) / magnetic_magnitude_t, (state["dbr_dz_t_cm"] - state["dbz_dr_t_cm"]) / magnetic_magnitude_t, (state["bt_t"] / radial + state["dbt_dr_t_cm"] - state["dbr_dphi_t_rad"] / radial) / magnetic_magnitude_t))
        gradient_magnitude = np.array(((state["br_t"] * state["dbr_dr_t_cm"] + state["bt_t"] * state["dbt_dr_t_cm"] + state["bz_t"] * state["dbz_dr_t_cm"]) / magnetic_magnitude_t, (state["br_t"] * state["dbr_dphi_t_rad"] + state["bt_t"] * state["dbt_dphi_t_rad"] + state["bz_t"] * state["dbz_dz_t_cm"]) / (radial * magnetic_magnitude_t), (state["br_t"] * state["dbr_dz_t_cm"] + state["bt_t"] * state["dbt_dz_t_cm"] + state["bz_t"] * state["dbz_dz_t_cm"]) / magnetic_magnitude_t))
        term1 = float(np.dot(velocity, b_unit)) * one_over_omega * float(np.dot(b_cylindrical, curl_unit_field))
        term2 = -float(np.dot(radius_cylindrical, gradient_magnitude)) / (2.0 * magnetic_magnitude_t)
        scale = 1.0 - term1 - term2
        if not 0.0 < scale < 2.0:
            raise ValueError("source gyro_step rejects FLR scale outside (0,2)")
        radius *= scale
    particle_position = position - radius
    # Registered hardening: finite radius and finite position can still
    # overflow in the subtraction (e.g. position.x = 1e308 with radius.x
    # about -1.04e308); the saved implementation would return Inf silently,
    # this port checks every returned field.
    for name, value in (("particle_position_cm", particle_position),
                        ("gyro_radius_vector_cm", radius),
                        ("gyro_scale_factor", scale)):
        if not np.all(np.isfinite(value)):
            raise ValueError(
                f"{name} is non-finite for finite but extreme input "
                "magnitudes (registered hardening)")
    return {"particle_position_cm": particle_position, "gyro_radius_vector_cm": radius, "gyro_scale_factor": scale}
