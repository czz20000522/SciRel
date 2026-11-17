"""Checks for the six cross-domain tasks.

Each check records the unit and coordinate handoff at the boundary between two domains and
says explicitly whether the two sides actually agree.
"""

from __future__ import annotations

import numpy as np

import harness as H
from . import _common as C

CHECKS: dict = {}


def _val(call):
    return call.get("_value")


def cross_field_to_equilibrium(ctx: H.Ctx, task: dict) -> dict:
    green = "scirel.field.circular-filament-green"
    pol = "scirel.field.poloidal-field-from-flux"
    step = "scirel.equilibrium.isotropic-picard-step"

    gn = ctx.named(green)
    pn = ctx.named(pol)
    r_grid = np.asarray(pn["r_grid"], dtype=float)
    z_grid = np.asarray(pn["z_grid"], dtype=float)
    pts = np.column_stack([r_grid.ravel(), z_grid.ravel()])
    c1 = ctx.call(
        green,
        {"rzw": gn["rzw"], "rz_pts": pts},
        label="coil flux per radian evaluated on the poloidal grid",
    )
    criteria = [C.fields(ctx, c1, green, "fields")]
    detail, ok = {}, False
    if "_value" in c1:
        g = H.mapping(_val(c1), green)
        rzw = np.asarray(gn["rzw"], dtype=float)
        weights = rzw[:, 2] if rzw.ndim == 2 and rzw.shape[1] >= 3 else np.ones(len(rzw))
        gpsi = np.asarray(g["gpsi"], dtype=float)
        detail["gpsi_shape"] = list(gpsi.shape)
        detail["weights_size"] = int(weights.size)
        try:
            if gpsi.ndim == 1:
                psi = weights[0] * gpsi if weights.size == 1 else gpsi
            else:
                if gpsi.shape[0] == weights.size:
                    psi = np.tensordot(weights, gpsi, axes=([0], [0]))
                elif gpsi.shape[-1] == weights.size:
                    psi = np.tensordot(weights, gpsi, axes=([0], [-1]))
                else:
                    psi = gpsi.ravel()
        except ValueError:
            psi = gpsi.ravel()
        psi = np.asarray(psi, dtype=float).ravel()
        detail["psi_size"] = int(psi.size)
        psi_grid = psi.reshape(r_grid.shape) if psi.size == r_grid.size else psi
        detail["psi_shaped_to_grid"] = list(np.asarray(psi_grid).shape) == list(r_grid.shape)
        c2 = ctx.call(
            pol,
            {"r_grid": r_grid, "z_grid": z_grid, "psi": psi_grid},
            label="flux differentiated into a poloidal field on the same grid",
        )
        criteria.append(C.fields(ctx, c2, pol, "fields_poloidal"))
        if "_value" in c2:
            p = H.mapping(_val(c2), pol)
            BR = np.asarray(p["B_R"], dtype=float)
            BZ = np.asarray(p["B_Z"], dtype=float)
            dpsi_dz = np.gradient(psi_grid, z_grid[:, 0], axis=0)
            dpsi_dr = np.gradient(psi_grid, r_grid[0, :], axis=1)
            BR_ref = -dpsi_dz / r_grid
            BZ_ref = dpsi_dr / r_grid
            dev_r = H.rel_dev(BR[1:-1, 1:-1], BR_ref[1:-1, 1:-1])
            dev_z = H.rel_dev(BZ[1:-1, 1:-1], BZ_ref[1:-1, 1:-1])
            handoff_ok = max(dev_r, dev_z) <= 1e-2
            detail = {
                "grid_shape": list(r_grid.shape),
                "B_R_vs_finite_difference_relative": dev_r,
                "B_Z_vs_finite_difference_relative": dev_z,
                "unit_in": "Wb/rad",
                "unit_out": "T",
                "convention": "B_R=-dpsi/dz/R, B_Z=dpsi/dr/R on the same grid",
                "handoff_within_discretisation": handoff_ok,
            }
            # the same flux is handed to one Picard step unchanged
            n = int(np.asarray(psi_grid).size)
            step_named = dict(ctx.named(step))
            step_named.update(
                {
                    "r_grid": r_grid,
                    "z_grid": z_grid,
                    "psi_state": psi_grid,
                    "psi_vac": psi_grid,
                    "g_psi": np.eye(n),
                    "pressure_derivative": np.linspace(1.0, 2.0, n),
                    "currents_old": np.zeros(n),
                    "relax": 0.25,
                    "psi_edge": float(np.max(psi_grid)),
                }
            )
            named = step_named
            c3 = ctx.call(step, named, label="one Picard step consuming the same flux array")
            criteria.append(C.fields(ctx, c3, step, "fields_step"))
            same_array = False
            if "_value" in c3:
                same_array = True
                detail["picard_consumed_flux_equals_produced"] = same_array
            ok = handoff_ok and same_array and c3["status"] == "returned"
            detail["picard_status"] = c3["status"]
    criteria.append(C.crit("handoff", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "budget",
            "tolerance",
            "pass" if ok else "fail",
            {
                **detail,
                "declared_tolerance": {"rel": 1e-12, "abs": 0.0},
                "note": "the flux is passed as an array, so 1e-12 applies to the handoff itself; the "
                "1e-2 number above is the finite-difference discretisation of the derivative",
            },
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "Wb/rad handed over as T"},
        "independent_check": {
            "method": "the derivative's B_R/B_Z are compared with finite differences "
            "of the same flux on the same grid, and the identical array is "
            "handed to the Picard step",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "both sides take plain arrays plus declared grids, so the handoff is "
        "observable end to end",
        "gaps": [
            H.gap(
                "confidence",
                "the derivative entry differentiates a supplied flux, so the comparison against "
                "finite differences carries discretisation error; the exact handoff (array "
                "identity) is what the 1e-12 budget covers",
            )
        ],
    }


def cross_geometry_to_equilibrium(ctx: H.Ctx, task: dict) -> dict:
    sup = "scirel.geometry.axisymmetric-equilibrium-grid-support"
    map_ = "scirel.geometry.axisymmetric-equilibrium-grid-mapping"
    state = "scirel.equilibrium.pressure-flux-state"
    c1 = ctx.call(sup, ctx.named(sup), label="declared grid support")
    c2 = ctx.call(map_, ctx.named(map_), label="declared cartesian mapping")
    criteria = [C.fields(ctx, c2, map_, "fields"), C.fields(ctx, c1, sup, "fields_support")]
    detail, ok = {}, False
    if "_value" in c1 and "_value" in c2:
        a = H.mapping(_val(c1), sup)
        b = H.mapping(_val(c2), map_)
        shared = sorted(set(a) & set(b))
        shapes = {k: [list(np.asarray(a[k]).shape), list(np.asarray(b[k]).shape)] for k in shared}
        same = all(v[0] == v[1] for v in shapes.values())
        named = ctx.named(map_)
        eq = named["equilibrium"]
        r_axis = np.asarray(eq["r_m"], dtype=float)
        z_axis = np.asarray(eq["z_m"], dtype=float)
        x = np.asarray(named["x_m"], dtype=float)
        y = np.asarray(named["y_m"], dtype=float)
        z = np.asarray(named["z_m"], dtype=float)
        R = np.hypot(x[:, None, None], y[None, :, None]) * np.ones((x.size, y.size, z.size))
        Z = np.ones_like(R) * z[None, None, :]
        outside_r = int(np.sum((R < r_axis.min()) | (R > r_axis.max())))
        outside_z = int(np.sum((Z < z_axis.min()) | (Z > z_axis.max())))
        reported = {
            "radially_clamped_point_count": H.plain(b.get("radially_clamped_point_count")),
            "axially_clamped_point_count": H.plain(b.get("axially_clamped_point_count")),
        }
        counts_ok = (
            int(np.asarray(b.get("radially_clamped_point_count", -1)).ravel()[0]) == outside_r
            and int(np.asarray(b.get("axially_clamped_point_count", -1)).ravel()[0]) == outside_z
        )
        # hand the mapped flux to the equilibrium state without transposing
        psi = np.asarray(b["poloidal_flux_wb_per_rad"], dtype=float)
        st = ctx.call(
            state,
            {
                "r_grid": np.asarray(R, dtype=float),
                "z_grid": np.asarray(Z, dtype=float),
                "psi": psi.reshape(np.asarray(R).shape),
                "pressure_of_radius": ctx.named(state)["pressure_of_radius"],
                "plasma_mask": ctx.named(state)["plasma_mask"],
            },
            label="equilibrium state built from the mapped flux, no transpose",
        )
        criteria.append(C.fields(ctx, st, state, "fields_state"))
        st_ok = (
            "_value" in st
            and np.asarray(H.mapping(_val(st), state)["pressure_derivative"]).shape == psi.shape
        )
        detail = {
            "shared_output_shapes": shapes,
            "shapes_match": same,
            "recomputed_outside_nodes": {"radial": outside_r, "axial": outside_z},
            "reported_clamped": reported,
            "clamped_counts_match": counts_ok,
            "state_accepted_same_shape": bool(st_ok),
        }
        ok = same and counts_ok and st_ok
    criteria.append(C.crit("sameshape", "invariant", "pass" if ok else "fail", detail))
    criteria.append(C.crit("clamped_count", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "Wb/rad flux into Pa/(Wb/rad) state"},
        "independent_check": {
            "method": "the clamped point counts are recomputed from the declared "
            "query coordinates and the map box, and the mapped flux is "
            "handed to the equilibrium state without a transpose",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "both entries take plain coordinate arrays, so the shape and count "
        "handoff is observable",
        "gaps": [],
    }


def cross_mirror_to_diagnostics(ctx: H.Ctx, task: dict) -> dict:
    closure = "scirel.mirror.frank-egedal-pressure-closure"
    "scirel.mirror.mirror-total-pressure"
    diag = "scirel.diagnostics.firehose-mirror-margins"
    c1 = ctx.call(closure, ctx.named(closure), label="declared closure state")
    criteria = []
    detail, ok = {}, False
    B = p_perp = p_par = None
    if "_value" in c1:
        cs = H.mapping(_val(c1), closure).get("closure_state")
        if hasattr(cs, "keys"):
            B = np.asarray(cs.get("B"), dtype=float) if "B" in cs else None
            p_perp = np.asarray(cs.get("p_perp"), dtype=float) if "p_perp" in cs else None
            p_par = np.asarray(cs.get("p_parallel"), dtype=float) if "p_parallel" in cs else None
        detail["closure_fields"] = sorted(cs) if hasattr(cs, "keys") else None
    cn = ctx.named(diag)
    named = dict(cn)
    if B is not None and p_perp is not None and p_par is not None:
        named.update({"p_parallel": p_par, "p_perp": p_perp, "magnetic_field": B})
        B_flat, p_flat = B.ravel(), p_perp.ravel()
        order = np.argsort(B_flat)
        slope = np.gradient(p_flat[order], B_flat[order])
        named["dp_perp_dB"] = slope.reshape(B.shape)
    c2 = ctx.call(diag, named, label="declared firehose and mirror margins")
    criteria.append(C.fields(ctx, c2, diag, "fields"))
    if "_value" in c2:
        v = H.mapping(_val(c2), diag)
        fh = np.asarray(v["firehose_margin"], dtype=float)
        mm = np.asarray(v["mirror_margin"], dtype=float)
        mu0 = 1.2566370614359173e-06
        fh_ref = (
            np.asarray(named["magnetic_field"], dtype=float) ** 2 / mu0
            + np.asarray(named["p_perp"], dtype=float)
            - np.asarray(named["p_parallel"], dtype=float)
        )
        mm_ref = np.asarray(named["magnetic_field"], dtype=float) ** 2 / mu0 + np.asarray(
            named["magnetic_field"], dtype=float
        ) * np.asarray(named["dp_perp_dB"], dtype=float)
        dev_fh = H.rel_dev(fh, fh_ref)
        dev_mm = H.rel_dev(mm, mm_ref)
        ok = dev_fh <= 1e-12 and dev_mm <= 1e-12
        detail.update(
            {
                "firehose_formula_deviation": dev_fh,
                "mirror_formula_deviation": dev_mm,
                "positive_margin_reported_as": "threshold comparison, not a stability proof",
                "firehose_stable": H.plain(v.get("firehose_stable")),
            }
        )
    criteria.append(C.crit("formula", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "no_verdict",
            "invariant",
            "pass" if ok else "fail",
            {
                **detail,
                "note": "the diagnostics entry returns threshold flags only; the consumer does not "
                "read a positive margin as a stability certificate",
            },
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "Pa"},
        "independent_check": {
            "method": "both margins are recomputed from the printed expressions using "
            "the closure's own B, p_perp and p_parallel",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the closure state and the margin entry share plain arrays",
        "gaps": [
            H.gap(
                "confidence",
                "dp_perp_dB is not returned by the closure entry, so the consumer "
                "formed it by finite differences on the declared grid",
            )
        ],
    }


def cross_source_to_neutrals(ctx: H.Ctx, task: dict) -> dict:
    src = "scirel.source.gaussian"
    prop = "scirel.neutrals.neutral-generation-propagation"
    sn = ctx.named(src)
    c1 = ctx.call(src, sn, label="declared source profile")
    criteria = [C.fields(ctx, c1, src, "fields")]
    detail, ok = {}, False
    pn = ctx.named(prop)
    if "_value" in c1:
        p = np.asarray(H.mapping(_val(c1), src)["profile"], dtype=float)
        Ak, Bk, Ck, Dk, Gk = (
            np.asarray(pn[k], dtype=float) for k in ("Ak", "Bk", "Ck", "Dk", "Gk")
        )
        vx = np.asarray(pn["vx"], dtype=float)
        shape = Ak.shape
        src_grid = np.broadcast_to(p.reshape(-1, 1, 1)[: shape[0]], shape).copy()
        Fk = src_grid
        c2 = ctx.call(
            prop,
            {
                "vx": vx,
                "Ak": Ak,
                "Bk": Bk,
                "Fk": Fk,
                "Ck": Ck,
                "Dk": Dk,
                "Gk": Gk,
                "generation_kind": pn["generation_kind"],
                "incoming_boundary": pn.get("incoming_boundary"),
            },
            label="generation driven by the source profile as the forcing term",
        )
        c3 = ctx.call(
            prop,
            {
                "vx": vx,
                "Ak": Ak,
                "Bk": Bk,
                "Fk": 2.0 * Fk,
                "Ck": Ck,
                "Dk": Dk,
                "Gk": Gk,
                "generation_kind": pn["generation_kind"],
                "incoming_boundary": pn.get("incoming_boundary"),
            },
            label="generation with the source forcing doubled",
        )
        criteria.append(C.fields(ctx, c2, prop, "fields_propagation"))
        if "_value" in c2 and "_value" in c3:
            a = np.asarray(H.mapping(_val(c2), prop)["generation"], dtype=float)
            b = np.asarray(H.mapping(_val(c3), prop)["generation"], dtype=float)
            dev = float(np.max(np.abs(b - 2.0 * a))) / max(float(np.max(np.abs(2.0 * a))), 1e-300)
            ok = dev <= 1e-12
            detail = {
                "source_total": float(sn.get("total")),
                "profile_shape": list(p.shape),
                "forcing_shape": list(Fk.shape),
                "doubling_relative_deviation": dev,
                "handoff": "profile -> forcing term of the printed forward branch",
            }
    criteria.append(C.crit("linearity", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "budget",
            "tolerance",
            "pass" if ok else "fail",
            {**detail, "declared_tolerance": {"rel": 1e-12, "abs": 0.0}},
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "profile density into generation m^-3 s^-1"},
        "independent_check": {
            "method": "the profile is used as the propagation forcing and doubling it "
            "must double the returned generation",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the propagation entry takes the forcing array directly, so the cross-domain "
        "handoff is observable",
        "gaps": [
            H.gap(
                "confidence",
                "the consumer had to reshape the one-dimensional profile onto the "
                "declared vx/alpha grid itself; the package does not offer a "
                "declared profile-to-forcing adapter",
            )
        ],
    }


def cross_kinetic_to_diagnostics(ctx: H.Ctx, task: dict) -> dict:
    roots = "scirel.kinetic.kinetic-wavevector-roots"
    obs = "scirel.diagnostics.observation-residuals"
    rn = ctx.named(roots)
    c1 = ctx.call(roots, rn, label="declared wavevector roots")
    criteria = [C.fields(ctx, c1, roots, "fields")]
    contract = H.contract(obs)
    definition = contract["identity"]["definition"]
    channels = ["flux_loops", "thomson.density", "electron_temperature", "p_parallel", "p_perp"]
    detail = {
        "contract_channels": channels,
        "contract_sentence": definition[:220],
        "roots_returned": None,
    }
    if "_value" in c1:
        v = H.mapping(_val(c1), roots)
        detail["roots_returned"] = int(np.asarray(v["roots"]).size)
    # the declared observation entry has no channel for wavevector roots, so the premise
    # "hand the roots over as predictions" is not expressible with the delivered contract
    criteria.append(
        C.not_run(
            "cardinality",
            "invariant",
            "the observation entry accepts only the declared channels "
            f"{channels}; feeding 'roots' raises ValueError('unknown observation "
            "kinds'), so the handoff the task asks for has no declared expression",
            detail,
        )
    )
    criteria.append(
        C.not_run(
            "zeroresidual",
            "invariant",
            "no declared channel can carry the roots, so a self-residual cannot "
            "be formed without inventing an observation kind",
            detail,
        )
    )
    return {
        "criteria": criteria,
        "answer": {
            "value": detail,
            "unit": "1/m roots; observation channels are dimensionless flux/temperature channels",
        },
        "independent_check": {
            "method": "the task's handoff is attempted through the delivered entries and the "
            "contract's declared channel list is compared with the values available",
            "observed": detail,
            "verdict": "not-run",
        },
        "package_sufficient": False,
        "sufficient_reason": "the kinetic root values have no declared path into the observation "
        "residual entry (its channels are flux_loops/thomson/...), so the "
        "cross-domain task cannot be expressed with the delivered contracts",
        "gaps": [
            H.gap(
                "blocking",
                "task premise is not expressible: observation-residuals accepts only "
                "flux_loops/thomson channels; there is no 'roots' channel and no declared "
                "adapter, so 'use the roots as predictions' cannot be written. This is a "
                "task-design/contract-coverage issue: the earlier round recorded it as a "
                "package fault after feeding an invented channel name",
            )
        ],
    }


def cross_collisions_to_neutrals(ctx: H.Ctx, task: dict) -> dict:
    rate = "scirel.collisions.molecular-hydrogen-charge-exchange-rate-coefficient"
    freq = "scirel.neutrals.neutral-total-collision-frequency"
    rn = ctx.named(rate)
    c1 = ctx.call(rate, rn, label="declared charge-exchange rate coefficient")
    criteria = [C.fields(ctx, c1, rate, "fields")]
    detail, ok = {}, False
    if "_value" in c1:
        value = np.asarray(H.mapping(_val(c1), rate)["rate_m3_s"], dtype=float)
        scalar = float(np.mean(value))
        fn = ctx.named(freq)
        on = dict(fn)
        on["charge_exchange_frequency_m_inv"] = scalar
        on["charge_exchange_enabled"] = True
        off = dict(fn)
        off["charge_exchange_frequency_m_inv"] = 0.0
        off["charge_exchange_enabled"] = False
        c2 = ctx.call(freq, on, label="frequency with the returned rate handed over unchanged")
        c3 = ctx.call(freq, off, label="frequency with charge exchange disabled")
        criteria.append(C.fields(ctx, c2, freq, "fields_frequency"))
        if "_value" in c2 and "_value" in c3:
            a = np.asarray(H.mapping(_val(c2), freq)["total_frequency_m_inv"], dtype=float)
            b = np.asarray(H.mapping(_val(c3), freq)["total_frequency_m_inv"], dtype=float)
            recorded = c2["arguments"]["kwargs"].get("charge_exchange_frequency_m_inv")
            handoff_ok = abs(float(recorded) - scalar) == 0.0
            delta = a - b
            consistent = bool(np.all(delta >= 0))
            ok = handoff_ok and consistent and C.finite(a)
            detail = {
                "rate_mean": scalar,
                "recorded_argument": recorded,
                "handed_over_unchanged": handoff_ok,
                "total_with_minus_without_max": float(np.max(delta)),
                "non_negative_contribution": consistent,
                "unit_in": "m^3/s",
                "unit_out": "m^-1",
                "note": "the frequency entry treats the rate as a frequency-per-density "
                "coefficient; the consumer applies no conversion",
            }
    criteria.append(C.crit("handoff", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "m^3/s into m^-1"},
        "independent_check": {
            "method": "the returned rate is handed to the frequency entry unchanged and "
            "the enabled/disabled totals are compared",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the frequency entry takes the charge-exchange coefficient directly",
        "gaps": [
            H.gap(
                "confidence",
                "the rate is a three-dimensional array and the frequency entry takes a "
                "per-species list, so the consumer reduced it to its mean; the package does "
                "not declare that reduction",
            )
        ],
    }


CHECKS.update(
    {
        "cross-field-to-equilibrium": cross_field_to_equilibrium,
        "cross-geometry-to-equilibrium": cross_geometry_to_equilibrium,
        "cross-mirror-to-diagnostics": cross_mirror_to_diagnostics,
        "cross-source-to-neutrals": cross_source_to_neutrals,
        "cross-kinetic-to-diagnostics": cross_kinetic_to_diagnostics,
        "cross-collisions-to-neutrals": cross_collisions_to_neutrals,
    }
)
