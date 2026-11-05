"""Cell-local the neutral-transport formulation elastic moment reduction, independent of iteration caches.

SIG includes the target velocity quadrature, but not Vth. Therefore Alpha and
Omega have units m^-1. This is a moment-matched BGK approximation, not the full
Boltzmann collision operator. Undefined quotients are explicitly represented;
the underlying collision moments remain available.
"""

from __future__ import annotations
import numpy as np


def _real(value, name):
    a = np.asarray(value)
    if a.dtype.kind not in "iuf" or not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be finite real numeric data")
    return np.asarray(a, dtype=float)


def reduce_elastic_moments(
    f,
    density,
    alpha1,
    alpha2,
    sig_self,
    wr,
    dx,
    vr,
    vx,
    vth,
    flow1,
    flow2,
    *,
    moment_state,
    target_distribution,
    enabled,
    names,
    flow_name,
    stress_name,
    mass_fractions,
):
    f, density, alpha1, alpha2, sig_self, wr, dx, vr, vx, flow1, flow2 = (
        _real(v, n)
        for v, n in zip(
            (f, density, alpha1, alpha2, sig_self, wr, dx, vr, vx, flow1, flow2),
            (
                "f",
                "density",
                "alpha1",
                "alpha2",
                "sig_self",
                "wr",
                "dx",
                "vr",
                "vx",
                "flow1",
                "flow2",
            ),
        )
    )
    vth = _real(vth, "Vth")
    if vth.ndim != 0 or vth <= 0:
        raise ValueError("Vth must be a positive scalar in m/s")
    vth = float(vth)
    if f.ndim != 3 or any(n == 0 for n in f.shape) or np.any(f < 0):
        raise ValueError("f must be nonnegative nonempty (nvr,nvx,nx)")
    nr, nv, nx = f.shape
    if any(
        a.shape != shape
        for a, shape in (
            (density, (nx,)),
            (alpha1, f.shape),
            (alpha2, f.shape),
            (sig_self, (nr * nv, nr * nv)),
            (wr, (nr,)),
            (dx, (nv,)),
            (vr, (nr,)),
            (vx, (nv,)),
            (flow1, (nx,)),
            (flow2, (nx,)),
        )
    ):
        raise ValueError("inconsistent cylindrical velocity carrier shapes")
    if (
        np.any(wr <= 0)
        or np.any(dx <= 0)
        or np.any(vr <= 0)
        or np.any(np.diff(vr) <= 0)
        or np.any(np.diff(vx) <= 0)
        or np.any(density <= 0)
    ):
        raise ValueError("positive density/weights/radii and increasing axes required")
    if any(not isinstance(e, (bool, np.bool_)) for e in enabled):
        raise ValueError("channel flags must be booleans")
    weights = wr[:, None] * dx[None, :]

    def integral(values):
        """Integrate one velocity-grid field independently per spatial cell."""
        return np.sum(weights[:, :, None] * values, axis=(0, 1))

    # This tolerance only accommodates binary64 quadrature summation roundoff;
    # it never floors a collision moment or replaces a zero denominator.
    roundoff = 64 * np.finfo(float).eps
    n_actual = integral(f)
    if not np.allclose(n_actual, density, rtol=roundoff, atol=0):
        raise ValueError("density must equal the weighted integral of f")
    # Referencing an axis node reduces cancellation under a common boost.
    origin = vx[0]
    u_relative = integral(f * (vx - origin)[None, :, None]) / density
    u = origin + u_relative
    centered_vx = (vx - origin)[None, :, None] - u_relative[None, None, :]
    kernel = vr[:, None, None] ** 2 - 2 * centered_vx**2
    central = integral(f * kernel) / density
    state = np.asarray(moment_state)
    if state.ndim == 0:
        state = np.full(nx, str(state))
    if state.shape != (nx,) or not np.all(np.isin(state, ["central", "target"])):
        raise ValueError("moment_state must be central/target per spatial cell")
    stress = central.copy()
    target_cells = state == "target"
    if np.any(target_cells):
        if target_distribution is None:
            raise ValueError("target state requires an explicit target distribution")
        target = _real(target_distribution, "target_distribution")
        if target.shape != f.shape or np.any(target < 0):
            raise ValueError("target_distribution must be nonnegative and aligned")
        tn = integral(target)
        if not np.allclose(tn[target_cells], density[target_cells], rtol=roundoff, atol=0):
            raise ValueError("self-collision target must conserve each cell density")
        tu = integral(target * (vx - origin)[None, :, None]) / density
        scale = max(float(np.max(np.abs(vx - origin))), 1.0)
        if np.any(np.abs(tu[target_cells] - u_relative[target_cells]) > roundoff * scale):
            raise ValueError("self-collision target must conserve each cell bulk flow")
        energy_kernel = vr[:, None, None] ** 2 + centered_vx**2
        energy = integral(f * energy_kernel) / density
        target_energy = integral(target * energy_kernel) / density
        if not np.allclose(
            target_energy[target_cells], energy[target_cells], rtol=roundoff, atol=0
        ):
            raise ValueError("self-collision target must conserve each cell kinetic energy")
        stress[target_cells] = (integral((f - target) * kernel) / density)[target_cells]
    elif target_distribution is not None:
        raise ValueError("target_distribution supplied without a target-state cell")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        # SIG is column-weighted in Fortran velocity order.  Keep each
        # spatial cell as an m-by-1 matrix-vector product while broadcasting
        # the batch axis; multiplying SIG by an m-by-nx matrix would change
        # the BLAS reduction path and can change the saved floating-point
        # result by a few ULPs.
        flat = f.reshape((nr * nv, nx), order="F")
        self_alpha = (
            np.matmul(sig_self[None, :, :], flat.T[:, :, None])
            .squeeze(2)
            .T.reshape((nr, nv, nx), order="F")
        )
        numerators = [integral(f * a) / density for a in (alpha1, alpha2, self_alpha)]
        denominators = [(vth * u - flow1) / vth, (vth * u - flow2) / vth, stress]
    result = {flow_name: vth * u, stress_name: stress, "central_stress": central}
    all_defined = np.ones(nx, dtype=bool)
    omegas = []
    for i, (name, on, numerator, denominator) in enumerate(
        zip(names, enabled, numerators, denominators)
    ):
        moment = numerator if on else np.zeros(nx)
        defined = denominator != 0 if on else np.ones(nx, dtype=bool)
        omega = np.zeros(nx) if not on else np.full(nx, np.nan)
        if on:
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                np.divide(moment, denominator, out=omega, where=defined)
        status = np.full(nx, "disabled", dtype="<U32")
        if on:
            status[:] = "undefined_zero_denominator"
            status[defined & (omega >= 0)] = "finite_nonnegative"
            status[defined & (omega < 0)] = "negative_no_bgk_closure"
        with np.errstate(over="ignore", invalid="ignore"):
            nu = vth * omega
            # Physical acceleration (mixed) or central stress derivative (self).
            physical_moment = (
                -mass_fractions[i] * vth * vth * moment if i < 2 else -vth * vth * vth * moment
            )
        if (
            not np.all(np.isfinite(moment))
            or not np.all(np.isfinite(physical_moment))
            or not np.all(np.isfinite(omega[defined]))
            or not np.all(np.isfinite(nu[defined]))
        ):
            raise ValueError("elastic moment/rate is not representable")
        result.update(
            {
                f"Omega_{name}": omega,
                f"nu_{name}": nu,
                f"moment_{name}": moment,
                f"moment_rate_{name}": physical_moment,
                f"defined_{name}": defined,
                f"status_{name}": status,
            }
        )
        all_defined &= defined
        omegas.append(omega)
    result["Omega_EL"] = sum(omegas)
    result["nu_EL"] = vth * result["Omega_EL"]
    result["defined_EL"] = all_defined
    finite_core = (
        result[flow_name],
        stress,
        central,
        result["Omega_EL"][all_defined],
        result["nu_EL"][all_defined],
    )
    if any(not np.all(np.isfinite(v)) for v in finite_core):
        raise ValueError("elastic reduction produced an unrepresentable result")
    return result
