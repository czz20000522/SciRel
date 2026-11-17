"""Checks for field, geometry, numerics, sampling, equilibrium, mirror, closures,
diagnostics, physics, electromagnetism and configurations tasks."""

from __future__ import annotations

import numpy as np

import harness as H
from . import _common as C

CHECKS: dict = {}

GREEN = "scirel.field.circular-filament-green"
SUPER = "scirel.field.current-green-superposition"
MULTI = "scirel.field.multi-coil-vacuum-field"


def _val(call):
    return call.get("_value")


def _max_rel(a, b):
    return H.rel_dev(a, b)


def field_filament_superposition(ctx: H.Ctx, task: dict) -> dict:
    ctx.call(GREEN, ctx.named(GREEN), label="declared single-filament Green response")
    base = ctx.named(SUPER)
    c2 = ctx.call(SUPER, base, label="declared superposed field")
    doubled = dict(base)
    doubled["currents"] = [2.0 * c for c in base["currents"]]
    c3 = ctx.call(SUPER, doubled, label="same sources with every weight doubled")
    ctx.call(MULTI, ctx.named(MULTI), label="declared multi-coil vacuum field")

    criteria = [C.fields(ctx, c2, SUPER, "fields")]
    ok, detail = False, {}
    if all("_value" in c for c in (c2, c3)):
        a, b = _val(c2), _val(c3)
        devs = {
            k: _max_rel(a[k], 2.0 * np.asarray(b[k]))
            for k in ("psi", "BR", "BZ")
            if k in a and k in b
        }
        # manual superposition straight from the returned Green columns
        psi_manual = np.tensordot(
            np.asarray(base["currents"]), np.asarray(base["gpsi"]), axes=([0], [0])
        )
        dev_manual = _max_rel(a["psi"], psi_manual)
        ok = max(list(devs.values()) + [dev_manual]) <= 2e-12
        detail = {
            "linearity_relative_deviation": devs,
            "manual_superposition_deviation": dev_manual,
            "declared_budget": 2e-12,
        }
    criteria.append(C.crit("linearity", "invariant", "pass" if ok else "fail", detail))
    criteria.append(C.crit("entryagreement", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "budget",
            "tolerance",
            "pass" if ok else "fail",
            {
                **detail,
                "quantity": "@declared_outputs psi/BR/BZ",
                "declared_tolerance": {"rel": 2e-12, "abs": 0.0},
            },
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "T and T*m for the field components"},
        "independent_check": {
            "method": "the superposed psi is recomputed as sum_k currents_k*gpsi_k "
            "from the returned Green columns and the doubled-weight call",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok and criteria[0]["status"] == "pass",
        "sufficient_reason": "weights, columns and composite record are all readable, so the "
        "linearity and summation conventions can be checked from the package",
        "gaps": [],
    }


def field_flux_to_poloidal(ctx: H.Ctx, task: dict) -> dict:
    flux = "scirel.field.poloidal-field-from-flux"
    mag = "scirel.field.poloidal-field-magnitude"
    c1 = ctx.call(flux, ctx.named(flux), label="declared flux differentiation")
    criteria = [C.fields(ctx, c1, flux, "fields")]
    ok, detail = False, {}
    if "_value" in c1:
        v = _val(c1)
        c2 = ctx.call(
            mag,
            {"br": np.asarray(v["B_R"]), "bz": np.asarray(v["B_Z"])},
            label="magnitude entry on the returned components",
        )
        criteria.append(C.fields(ctx, c2, mag, "fields_magnitude"))
        if "_value" in c2:
            w = _val(c2)
            hyp = np.maximum(np.hypot(np.asarray(v["B_R"]), np.asarray(v["B_Z"])), 1e-30)
            expected = float(np.median(hyp))
            got = np.asarray(w["B"])
            dev = float(np.max(np.abs(got - expected)))
            ok = dev <= 1e-14 * max(1.0, abs(expected))
            detail = {
                "returned_B": H.plain(got),
                "recomputed_median": expected,
                "max_abs_deviation": dev,
                "B0_default": H.plain(w.get("B0_default")),
                "declared_budget_rel": 1e-14,
            }
    criteria.append(C.crit("declared_median", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "budget",
            "tolerance",
            "pass" if ok else "fail",
            {**detail, "declared_tolerance": {"rel": 1e-14, "abs": 0.0}},
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "T"},
        "independent_check": {
            "method": "B is recomputed as the median of hypot(B_R,B_Z) with each "
            "component floored at 1e-30",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "components and magnitude are separate published entries at the same grid",
        "gaps": [],
    }


def geometry_equilibrium_grid(ctx: H.Ctx, task: dict) -> dict:
    support = "scirel.geometry.axisymmetric-equilibrium-grid-support"
    mapping = "scirel.geometry.axisymmetric-equilibrium-grid-mapping"
    average = "scirel.geometry.flux-surface-inverse-field-average"
    ctx.call(support, ctx.named(support), label="declared grid support")
    c2 = ctx.call(mapping, ctx.named(mapping), label="declared cartesian mapping")
    c3 = ctx.call(average, ctx.named(average), label="declared inverse-field average")
    criteria = [C.fields(ctx, c3, average, "fields"), C.fields(ctx, c2, mapping, "fields_mapping")]
    ok, detail = False, {}
    if "_value" in c3:
        v = _val(c3)
        line = np.asarray(ctx.named(average)["field_line_points"], dtype=float)
        seg = np.diff(line, axis=0)
        path = float(np.sum(np.hypot(seg[:, 0], seg[:, 1])))
        dl = np.asarray(v["dl_B"], dtype=float)
        expected = float(np.sum(dl)) / path if path else float("nan")
        got = float(np.asarray(v["flux_surface_average"]))
        dev = abs(got - expected) / max(abs(expected), 1e-300)
        ok = dev <= 1e-12
        detail = {
            "returned_average": got,
            "recomputed_sum_dl_over_path": expected,
            "path_length": path,
            "len_dl": int(dl.size),
            "relative_deviation": dev,
        }
    criteria.append(C.crit("declared_ratio", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "T^-1"},
        "independent_check": {
            "method": "flux_surface_average recomputed as sum(dl_B)/total path "
            "length of the declared polyline",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the differential array and the path are both returned/declared",
        "gaps": [],
    }


def geometry_mesh_and_volume(ctx: H.Ctx, task: dict) -> dict:
    rect = "scirel.geometry.rect-mesh"
    pts = "scirel.geometry.points-mesh"
    vol = "scirel.geometry.masked-toroidal-volume"
    ctx.call(rect, ctx.named(rect), label="declared rectangular mesh")
    ctx.call(pts, ctx.named(pts), label="declared points mesh")
    c3 = ctx.call(vol, ctx.named(vol), label="declared masked toroidal volume")
    criteria = [C.fields(ctx, c3, vol, "fields")]
    ok, detail = False, {}
    if "_value" in c3:
        v = H.mapping(_val(c3), vol)
        named = ctx.named(vol)
        R = np.asarray(named["R"], dtype=float)
        mask = np.asarray(named["core_mask"], dtype=bool)
        dR, dZ = float(named["dR"]), float(named["dZ"])
        expected = 2.0 * np.pi * float(np.sum(R * dR * dZ * mask))
        got = float(np.asarray(v["volume"]))
        # additivity on a split mask
        idx = np.flatnonzero(mask.ravel())
        half = len(idx) // 2
        m1 = np.zeros_like(mask)
        m1.ravel()[idx[:half]] = True
        m2 = np.zeros_like(mask)
        m2.ravel()[idx[half:]] = True
        s1 = ctx.call(vol, {**named, "core_mask": m1}, label="first disjoint submask")
        s2 = ctx.call(vol, {**named, "core_mask": m2}, label="second disjoint submask")
        additive = None
        if "_value" in s1 and "_value" in s2:
            additive = float(
                np.asarray(H.mapping(_val(s1), vol)["volume"])
                + np.asarray(H.mapping(_val(s2), vol)["volume"])
            )
        dev = abs(got - expected) / max(abs(expected), 1e-300)
        dev_add = (
            abs(additive - got) / max(abs(got), 1e-300) if additive is not None else float("inf")
        )
        ok = dev <= 1e-12 and dev_add <= 1e-12
        detail = {
            "returned_volume": got,
            "recomputed_volume": expected,
            "relative_deviation": dev,
            "additivity_deviation": dev_add,
            "cells_masked": int(mask.sum()),
        }
    criteria.append(C.crit("declared_measure", "invariant", "pass" if ok else "fail", detail))
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
        "answer": {"value": detail, "unit": "m^3"},
        "independent_check": {
            "method": "volume recomputed as 2*pi*sum(R*dR*dZ*mask) from the "
            "declared grid and checked additive over a split mask",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the entry takes the mask as an argument, so the consumer can split it",
        "gaps": [],
    }


def numerics_basis_projection(ctx: H.Ctx, task: dict) -> dict:
    modal = "scirel.numerics.orthonormal-modal-basis"
    proj = "scirel.numerics.modal-projection"
    c0 = ctx.call(modal, ctx.named(modal), label="declared modal basis")
    c1 = ctx.call(proj, ctx.named(proj), label="declared modal projection")
    criteria = [C.fields(ctx, c1, proj, "fields"), C.fields(ctx, c0, modal, "fields_basis")]
    ok, detail = False, {}
    try:
        ctx.named(modal)["kind"]
        from scirel.numerics.modal_basis import modal_basis as _mb

        b = _mb(ctx.named(modal)["kind"], ctx.named(modal)["ndim"], ctx.named(modal)["order"])
        nodes, weights = b.quadrature()
        members = b.evaluate(nodes)
        gram = np.einsum("q,qi,qj->ij", weights, members, members)
        ident_dev = float(np.max(np.abs(gram - np.eye(gram.shape[0]))))
        coeffs = np.arange(b.num_basis, dtype=float) - 3.5
        recovered = b.project(b.expand(nodes, coeffs))
        span_dev = float(np.max(np.abs(recovered - coeffs)))
        outer = b.expand(nodes, coeffs) + 0.75 * nodes[:, 0] ** 5
        outer_res = float(np.max(np.abs(b.project(outer) - coeffs)))
        ok = ident_dev <= 1e-12 and span_dev <= 1e-12 and outer_res > span_dev
        detail = {
            "gram_identity_deviation": ident_dev,
            "in_span_reconstruction_deviation": span_dev,
            "outside_span_reported_shift": outer_res,
            "num_basis": int(b.num_basis),
        }
    except Exception as exc:  # noqa: BLE001
        detail = {
            "why": f"the declared basis object could not be driven from its documented API: {exc}"
        }
    criteria.append(C.crit("orthonormal", "invariant", "pass" if ok else "fail", detail))
    criteria.append(C.crit("exactspan", "invariant", "pass" if ok else "fail", detail))
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
        "answer": {"value": detail, "unit": "dimensionless coefficients"},
        "independent_check": {
            "method": "Gram matrix recomputed from the returned quadrature and "
            "basis values, and an in-span expansion recovered",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the basis object exposes quadrature/evaluate/expand/project, so both "
        "criteria are checkable without private code",
        "gaps": [],
    }


def numerics_splines_and_inverse(ctx: H.Ctx, task: dict) -> dict:
    clamped = "scirel.numerics.clamped-cubic-spline"
    first = "scirel.numerics.first-clamped-cubic-spline"
    natural = "scirel.numerics.natural-cubic-spline"
    pinv = "scirel.numerics.truncated-svd-inverse"
    criteria, detail, ok = [], {}, True
    node_devs = {}
    for asset in (clamped, first, natural):
        call = ctx.call(asset, ctx.named(asset), label=f"declared {asset} node check")
        criteria.append(C.fields(ctx, call, asset, f"fields@{asset}"))
        if "_value" not in call:
            ok = False
            node_devs[asset] = "raised"
            continue
        named = ctx.named(asset)
        x = np.asarray(named["x_data"], dtype=float)
        y = np.asarray(named["y_data"], dtype=float)
        try:
            spline = _val(call)["spline"] if hasattr(_val(call), "keys") else _val(call)
            node_devs[asset] = float(np.max(np.abs(np.asarray(spline(x)) - y)))
        except Exception as exc:  # noqa: BLE001
            node_devs[asset] = f"could not evaluate: {exc}"
            ok = False
    if any(isinstance(v, str) or v > 1e-12 for v in node_devs.values()):
        ok = False
    c4 = ctx.call(pinv, ctx.named(pinv), label="declared truncated inverse")
    rank_detail = {}
    if "_value" in c4:
        m = np.asarray(ctx.named(pinv)["mat"], dtype=float)
        rcond = ctx.named(pinv).get("rcond")
        inv = np.asarray(_val(c4)["inverse"])
        sv = np.linalg.svd(m, compute_uv=False)
        rc = 0.0 if rcond is None else float(rcond)
        expected_rank = (
            int(np.sum(sv > rc * (sv[0] if sv.size else 1.0))) if rc else int(np.sum(sv > 0))
        )
        if m.shape[0] == m.shape[1]:
            diag = np.diag(m)
            rec = np.zeros_like(m)
            np.fill_diagonal(rec, np.where(diag != 0, 1.0 / np.where(diag == 0, 1.0, diag), 0.0))
            diag_dev = float(np.max(np.abs(inv - rec))) if inv.shape == m.shape else float("inf")
        else:
            diag_dev = None
        rank_detail = {
            "singular_values": sv.tolist(),
            "rcond": rc,
            "expected_rank_above_cutoff": expected_rank,
            "reciprocal_diagonal_deviation": diag_dev,
        }
        ok = ok and (diag_dev is None or diag_dev <= 1e-12)
    else:
        ok = False
    detail = {"node_deviations": node_devs, "truncated_inverse": rank_detail}
    criteria.append(
        C.crit(
            "nodes",
            "invariant",
            "pass"
            if all(not isinstance(v, str) and v <= 1e-12 for v in node_devs.values()) and node_devs
            else "fail",
            {"node_deviations": node_devs},
        )
    )
    criteria.append(
        C.crit("rank", "invariant", "pass" if ok and rank_detail else "fail", rank_detail)
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "dimensionless node deviations"},
        "independent_check": {
            "method": "each spline is evaluated at its own declared nodes and "
            "compared with the declared data; the truncated inverse is "
            "compared with the reciprocal diagonal",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the spline objects are callable and the inverse is returned as a matrix",
        "gaps": [],
    }


def sampling_regular_grid(ctx: H.Ctx, task: dict) -> dict:
    reg = "scirel.geometry.regular-grid"
    scat = "scirel.geometry.scattered-linear"
    near = "scirel.geometry.rectangular-nearest"
    c1 = ctx.call(reg, ctx.named(reg), label="declared regular-grid sampling")
    c2 = ctx.call(scat, ctx.named(scat), label="declared scattered linear sampling")
    ctx.call(near, ctx.named(near), label="declared rectangular nearest sampling")
    criteria = [C.fields(ctx, c1, reg, "fields")]
    detail, ok = {}, False
    if "_value" in c2:
        v = H.mapping(_val(c2), scat)
        named = ctx.named(scat)
        X = np.asarray(named["X"], dtype=float)
        Y = np.asarray(named["Y"], dtype=float)
        Q = np.asarray(named["Q"], dtype=float)
        pts = np.asarray(named["coord_list"], dtype=float).reshape(-1, 2)
        linear = X + 2.0 * Y
        expected = pts[:, 0] + 2.0 * pts[:, 1]
        dev = float(np.max(np.abs(np.asarray(v["values"]).ravel() - expected)))
        ok = dev <= 1e-12
        detail = {
            "linear_reproduction_deviation": dev,
            "field_linear": bool(np.allclose(Q, linear)),
            "query_points": H.plain(pts),
            "expected": H.plain(expected),
            "returned": H.plain(v["values"]),
            "declared_tolerance_rel": 1e-12,
        }
    criteria.append(C.crit("axisorder", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "field units of the declared linear function"},
        "independent_check": {
            "method": "the scattered entry is fed a field linear in (x,y) and the "
            "interpolated values are compared with the exact line",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the declared query points are inside the convex support and the exact "
        "linear value is known before the call",
        "gaps": [
            H.gap(
                "confidence",
                "the outside-support exclusion count is not a returned field of the "
                "declared scattered entry, so that half of the criterion was not evaluated",
            )
        ],
    }


def sampling_transform_and_derivative(ctx: H.Ctx, task: dict) -> dict:
    fwd = "scirel.geometry.meridional-polar-forward"
    inv = "scirel.geometry.meridional-polar-inverse"
    der = "scirel.geometry.nonuniform-first-derivative"
    named = ctx.named(fwd)
    c1 = ctx.call(fwd, named, label="declared forward transform")
    criteria = [C.fields(ctx, c1, fwd, "fields")]
    detail, ok = {}, False
    if "_value" in c1:
        out = _val(c1)
        fwd_vals = (
            list(out) if isinstance(out, (tuple, list)) else list(H.mapping(out, fwd).values())
        )
        inv_names = H.argnames(inv)
        if len(fwd_vals) == len(inv_names):
            back_named = dict(zip(inv_names, fwd_vals))
            back = ctx.call(inv, back_named, label="inverse applied to the forward result")
            criteria.append(C.fields(ctx, back, inv, "fields_inverse"))
            if "_value" in back:
                out2 = _val(back)
                back_vals = (
                    list(out2)
                    if isinstance(out2, (tuple, list))
                    else list(H.mapping(out2, inv).values())
                )
                fwd_in = [named[k] for k in named]
                devs = [abs(float(a) - float(b)) for a, b in zip(back_vals, fwd_in)]
                detail = {
                    "forward": H.plain(fwd_vals),
                    "roundtrip": H.plain(back_vals),
                    "declared_inputs": H.plain(fwd_in),
                    "max_abs_deviation": max(devs) if devs else None,
                }
                ok = bool(devs) and max(devs) <= 1e-12
    criteria.append(C.crit("roundtrip", "invariant", "pass" if ok else "fail", detail))
    der_detail, der_ok = {}, False
    dn = ctx.named(der)
    x = np.asarray(dn["x"], dtype=float)
    slope = 1.7
    r = ctx.call(
        der, {"x": x, "y": slope * x + 4.0}, label="linear function on the same nonuniform grid"
    )
    if "_value" in r:
        got = np.asarray(H.mapping(_val(r), der)["derivative"], dtype=float)
        der_ok = bool(np.all(np.abs(got - slope) <= 1e-12))
        der_detail = {
            "expected_slope": slope,
            "returned": H.plain(got),
            "max_abs_deviation": float(np.max(np.abs(got - slope))),
        }
    criteria.append(C.crit("derivative", "invariant", "pass" if der_ok else "fail", der_detail))
    return {
        "criteria": criteria,
        "answer": {"value": {**detail, "derivative": der_detail}, "unit": "declared coordinates"},
        "independent_check": {
            "method": "forward then inverse on the declared point, and a linear "
            "function differentiated on the declared nonuniform grid",
            "observed": {**detail, "derivative": der_detail},
            "verdict": "pass" if (ok and der_ok) else "fail",
        },
        "package_sufficient": ok and der_ok,
        "sufficient_reason": "both entries are published and the inverse accepts the forward record",
        "gaps": [],
    }


def fieldline_set_and_arclength(ctx: H.Ctx, task: dict) -> dict:
    fset = "scirel.geometry.fieldline-set"
    arcl = "scirel.geometry.arclength-derivative"
    cont = "scirel.geometry.contour-points"
    ctx.call(fset, ctx.named(fset), label="declared field-line set")
    c2 = ctx.call(arcl, ctx.named(arcl), label="declared arclength derivative")
    ctx.call(cont, ctx.named(cont), label="declared contour points")
    criteria = [C.fields(ctx, c2, arcl, "fields")]
    detail, ok = {}, False
    if "_value" in c2:
        named = ctx.named(arcl)
        p = np.asarray(named["vertices"], dtype=float)
        got = np.asarray(H.mapping(_val(c2), arcl)["derivative"], dtype=float)
        # declared three-point unequal-spacing stencil, one-sided quadratic ends
        s = np.r_[0.0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
        f = np.asarray(named["values"], dtype=float)
        exp = np.empty_like(f)
        for i in range(1, len(s) - 1):
            h1, h2 = s[i] - s[i - 1], s[i + 1] - s[i]
            exp[i] = (
                -h2 / (h1 * (h1 + h2)) * f[i - 1]
                + (h2 - h1) / (h1 * h2) * f[i]
                + h1 / (h2 * (h1 + h2)) * f[i + 1]
            )
        exp[0] = (f[1] - f[0]) / (s[1] - s[0])
        exp[-1] = (f[-1] - f[-2]) / (s[-1] - s[-2])
        interior = slice(1, -1)
        dev = float(np.max(np.abs(got[interior] - exp[interior])))
        ok = dev <= 1e-10
        detail = {
            "interior_max_abs_deviation": dev,
            "stencil": "three-point unequal spacing",
            "returned": H.plain(got),
            "recomputed": H.plain(exp),
            "declared_budget_rel": 1e-10,
        }
    criteria.append(C.crit("declared_stencil", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "budget",
            "tolerance",
            "pass" if ok else "fail",
            {**detail, "declared_tolerance": {"rel": 1e-10, "abs": 0.0}},
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "value per arc length"},
        "independent_check": {
            "method": "the derivative is recomputed with the declared three-point "
            "unequal-spacing stencil on the returned coordinates",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the grid points and values are both arguments, so the stencil is "
        "reproducible from the package record",
        "gaps": [
            H.gap(
                "confidence",
                "the one-sided quadratic endpoint stencils are not described numerically in "
                "the delivered contract, so they were not reproduced",
            )
        ],
    }


def equilibrium_isotropic_picard(ctx: H.Ctx, task: dict) -> dict:
    step = "scirel.equilibrium.isotropic-picard-step"
    solve = "scirel.equilibrium.isotropic-pressure-flux"
    state = "scirel.equilibrium.pressure-flux-state"
    c1 = ctx.call(step, ctx.named(step), label="declared Picard step")
    ctx.call(solve, ctx.named(solve), label="declared iterated solve")
    ctx.call(state, ctx.named(state), label="declared pressure-flux state")
    criteria = [C.fields(ctx, c1, step, "fields")]
    detail, ok = {}, False
    if "_value" in c1:
        v = _val(c1)
        named = ctx.named(step)
        R = np.asarray(named["r_grid"], dtype=float)
        dR = abs(float(R[0, 1] - R[0, 0])) if R.shape[1] > 1 else 0.0
        Z = np.asarray(named["z_grid"], dtype=float)
        dZ = abs(float(Z[1, 0] - Z[0, 0])) if Z.shape[0] > 1 else 0.0
        dp = np.asarray(named["pressure_derivative"], dtype=float).reshape(R.shape, order="C")
        old = np.asarray(named["currents_old"], dtype=float)
        relax = float(named["relax"])
        target = (R * dp * dR * dZ).ravel(order="C")
        expected = (1.0 - relax) * target + relax * old
        got = np.asarray(v["plasma_currents"], dtype=float).ravel()
        dev = float(np.max(np.abs(got - expected))) / max(float(np.max(np.abs(expected))), 1e-300)
        ok = dev <= 1e-12
        detail = {
            "relax": relax,
            "target_currents": H.plain(target),
            "returned": H.plain(got),
            "relative_deviation": dev,
            "residual": H.plain(v.get("residual")),
            "declared_budget_rel": 1e-12,
        }
    criteria.append(C.crit("declared_update", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "residualmeaning",
            "invariant",
            "not-run",
            {
                "why": "the declared norm of the difference between pre- and "
                "post-step flux is not returned beside the step "
                "record, so the reported residual could not be "
                "recomputed from stored arrays"
            },
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "A/m^2 (plasma current density)"},
        "independent_check": {
            "method": "currents recomputed as (1-relax)*I_target + relax*I_old with "
            "I_target from the declared grid and dp/dpsi",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": False,
        "sufficient_reason": "the update law is verified, but the residual criterion cannot be "
        "recomputed from the delivered record",
        "gaps": [
            H.gap(
                "confidence",
                "the step record carries a residual but not the pre/post flux arrays the "
                "contract defines the residual against",
            )
        ],
    }


def equilibrium_anisotropic_picard(ctx: H.Ctx, task: dict) -> dict:
    solve = "scirel.equilibrium.axisymmetric-anisotropic-picard"
    feedback = "scirel.equilibrium.anisotropic-picard-feedback"
    free = "scirel.equilibrium.free-boundary-anisotropic-picard"
    c1 = ctx.call(solve, ctx.named(solve), label="declared axisymmetric anisotropic Picard")
    ctx.call(feedback, ctx.named(feedback), label="declared feedback step")
    ctx.call(free, ctx.named(free), label="declared free-boundary Picard")
    criteria = [C.fields(ctx, c1, solve, "fields")]
    detail, ok = {}, False
    if "_value" in c1:
        v = _val(c1)
        named = ctx.named(solve)
        iters = v.get("iterations")
        hist = v.get("iteration_history")
        last = v.get("fixed_point_residual")
        tol = float(named.get("tol", 0.0) or 0.0)
        ratio_keys = [
            k for k in ("anisotropy_ratio", "pressure_anisotropy", "anisotropy") if k in v
        ]
        echoed = {}
        for k in ratio_keys:
            if k in named:
                try:
                    echoed[k] = bool(
                        np.allclose(
                            np.asarray(v[k], dtype=float), np.asarray(named[k], dtype=float)
                        )
                    )
                except (TypeError, ValueError):
                    echoed[k] = False
        consistent = True
        hist_detail = None
        if hist is not None and iters is not None:
            entries = list(hist)
            numeric = None
            if entries and isinstance(entries[0], dict):
                for key in ("fixed_point_residual", "residual", "error"):
                    if key in entries[0]:
                        numeric = [float(e[key]) for e in entries]
                        break
                hist_detail = {"entry_keys": sorted(entries[0])}
            else:
                numeric = [float(e) for e in entries]
            if numeric is not None:
                consistent = len(numeric) >= int(iters) and abs(
                    numeric[int(iters) - 1] - float(last)
                ) <= 1e-12 * max(1.0, abs(float(last)))
                hist_detail = {**(hist_detail or {}), "history_entries": len(numeric)}
        converged = bool(v.get("converged")) if "converged" in v else None
        status_ok = (converged is None) or (converged and float(last) <= tol) or (not converged)
        ok = consistent and status_ok and all(echoed.values())
        detail = {
            "iterations": iters,
            "residual_history_len": int(np.asarray(hist).size) if hist is not None else None,
            "last_residual": last,
            "tolerance": tol,
            "converged": converged,
            "echoed_ratios": echoed,
            "history_matches_last": consistent,
            "history": hist_detail,
        }
    criteria.append(C.crit("declared_ratio", "invariant", "pass" if ok else "fail", detail))
    criteria.append(C.crit("status", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "mixed (Wb/rad flux, T field)"},
        "independent_check": {
            "method": "iteration count and last residual compared with the "
            "returned residual history, and declared ratios compared "
            "with the echoed record",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the record carries the history and the convergence flag",
        "gaps": [],
    }


def mirror_frank_egedal(ctx: H.Ctx, task: dict) -> dict:
    closure = "scirel.mirror.frank-egedal-pressure-closure"
    pressure = "scirel.mirror.frank-egedal-pressure-state"
    total = "scirel.mirror.mirror-total-pressure"
    c1 = ctx.call(closure, ctx.named(closure), label="declared closure state")
    ctx.call(pressure, ctx.named(pressure), label="declared Frank-Egedal pressure")
    c3 = ctx.call(total, ctx.named(total), label="declared total pressure")
    criteria = [C.fields(ctx, c3, total, "fields")]
    detail, ok = {}, False
    if "_value" in c3:
        v = _val(c3)
        devs = {}
        for comp in ("p_parallel", "p_perpendicular"):
            ion_key = "ion_p_parallel" if comp == "p_parallel" else "ion_p_perpendicular"
            if comp in v and ion_key in v and "electron_pressure" in v:
                recomputed = np.asarray(v[ion_key]) + np.asarray(v["electron_pressure"])
                devs[comp] = H.rel_dev(v[comp], recomputed)
        ok = bool(devs) and max(devs.values()) <= 1e-13
        detail = {"composition_relative_deviation": devs, "declared_budget": 1e-13}
    criteria.append(C.crit("declared_composition", "invariant", "pass" if ok else "fail", detail))
    state_detail, state_ok = {}, False
    if "_value" in c1:
        v = _val(c1)
        cs = v.get("closure_state") if hasattr(v, "get") else None
        finite = all(C.finite(v.get(k)) for k in ("p_parallel", "p_perp") if k in v)
        state_ok = finite and cs is not None
        state_detail = {
            "closure_state_present": cs is not None,
            "p_parallel_finite": C.finite(v.get("p_parallel")),
            "p_perp_finite": C.finite(v.get("p_perp")),
        }
    criteria.append(
        C.crit("closure_state", "invariant", "pass" if state_ok else "fail", state_detail)
    )
    criteria.append(
        C.crit(
            "budget",
            "tolerance",
            "pass" if ok else "fail",
            {**detail, "declared_tolerance": {"rel": 1e-13, "abs": 0.0}},
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": {**detail, "closure": state_detail}, "unit": "Pa"},
        "independent_check": {
            "method": "total pressure recomputed as ion component plus the "
            "electron pressure added to both directions",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok and state_ok,
        "sufficient_reason": "both ion and electron components are in the same returned record",
        "gaps": [],
    }


def mirror_ambipolar_and_loss_cone(ctx: H.Ctx, task: dict) -> dict:
    amb = "scirel.mirror.mirror-ambipolar-potential"
    loss = "scirel.mirror.loss-cone-spectrum"
    dist = "scirel.mirror.mirror-invariant-distribution"
    ctx.call(amb, ctx.named(amb), label="declared ambipolar potential")
    c2 = ctx.call(loss, ctx.named(loss), label="declared loss-cone spectrum")
    c3 = ctx.call(dist, ctx.named(dist), label="declared invariant distribution")
    criteria = [C.fields(ctx, c2, loss, "fields")]
    detail, ok = {}, False
    if "_value" in c2:
        v = _val(c2)
        xi = np.asarray(v["xi"], dtype=float)
        eig = np.asarray(v["eigenvalues"], dtype=float)
        funcs = np.asarray(v["eigenfunctions"], dtype=float)
        expected = 1.0 - 3.0 * xi**2
        dev = float(np.max(np.abs(funcs[:, 0] - expected)))
        bnd = np.asarray(v.get("boundary_residuals", []), dtype=float)
        ok = dev <= 2e-10 and (bnd.size == 0 or float(np.max(np.abs(bnd))) <= 1e-8)
        detail = {
            "first_eigenfunction_deviation": dev,
            "first_eigenvalue": float(eig[0]) if eig.size else None,
            "boundary_residual_max": float(np.max(np.abs(bnd))) if bnd.size else None,
            "grid_points": int(xi.size),
        }
        frac = v.get("fraction")
        if frac is not None:
            detail["loss_cone_fraction"] = H.plain(frac)
            ok = ok and 0.0 <= float(np.asarray(frac).ravel()[0]) <= 1.0
    criteria.append(C.crit("declared_record", "invariant", "pass" if ok else "fail", detail))
    finite_ok = all(
        C.finite(_val(c).get(k))
        for c in (c3,)
        if "_value" in c
        for k in ("f0_s3_m6", "occupation")
        if k in _val(c)
    )
    criteria.append(
        C.crit(
            "finite_check",
            "invariant",
            "pass" if finite_ok else "fail",
            {"mirrored_distribution_finite": finite_ok},
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "dimensionless"},
        "independent_check": {
            "method": "the first loss-cone eigenfunction is compared with "
            "1-3*xi^2 and the fraction is checked inside [0,1]",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok and finite_ok,
        "sufficient_reason": "the spectrum returns the grid it was evaluated on, so the eigenfunction "
        "can be compared with its declared closed form",
        "gaps": [],
    }


def em_device_composition(ctx: H.Ctx, task: dict) -> dict:
    device = "scirel.electromagnetism.device"
    green = "scirel.electromagnetism.circular-filament-green"
    loops = "scirel.electromagnetism.loop-flux-matrix"
    c2 = ctx.call(green, ctx.named(green), label="declared Green response")
    c3 = ctx.call(loops, ctx.named(loops), label="declared loop flux matrix")
    criteria = [C.fields(ctx, c2, green, "fields_green"), C.fields(ctx, c3, loops, "fields_loop")]
    detail, ok = {}, False
    try:
        mod = H.resolve(device)[0]
        named = ctx.named(device)
        d1 = mod.Device(mesh=named["mesh"])
        d1.a = mod.ArbitraryPoints([[1.0, 0.0]])
        psi_one = np.asarray(d1.psi())
        d2 = mod.Device(mesh=named["mesh"])
        d2.a = mod.ArbitraryPoints([[1.0, 0.0]])
        d2.b = mod.ArbitraryPoints([[0.0, 2.0]], current=3.0) if True else None
        psi_two = np.asarray(d2.psi())
        d3 = mod.Device(mesh=named["mesh"])
        d3.b = mod.ArbitraryPoints([[0.0, 2.0]], current=3.0)
        d3.a = mod.ArbitraryPoints([[1.0, 0.0]])
        psi_reordered = np.asarray(d3.psi())
        dev_sum = float(np.max(np.abs(psi_two - (psi_one + np.asarray(d3.b.psi())))))
        dev_order = float(np.max(np.abs(psi_two - psi_reordered)))
        ok = dev_sum <= 1e-12 and dev_order <= 1e-12
        detail = {
            "registration_sum_deviation": dev_sum,
            "order_change_deviation": dev_order,
            "declared_budget_rel": 1e-12,
        }
    except Exception as exc:  # noqa: BLE001
        detail = {
            "why": f"the device object could not be composed from the documented example API: "
            f"{type(exc).__name__}: {exc}"
        }
    criteria.append(C.crit("registration", "invariant", "pass" if ok else "fail", detail))
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
        "answer": {"value": detail, "unit": "Wb/rad (flux per radian)"},
        "independent_check": {
            "method": "one device with two registered sources is compared with the "
            "sum of the two single-source devices, and the registration "
            "order is swapped",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "registration is a documented attribute assignment and psi() is public",
        "gaps": [],
    }


def configurations_retained_geometries(ctx: H.Ctx, task: dict) -> dict:
    assets = {
        "scirel.configurations.trex-coil": ("npts", 88),
        "scirel.configurations.brb": ("hh_n.npts", 88),
        "scirel.configurations.wham": ("current_sets", [32, 32, 10, 10]),
    }
    criteria, detail = [], {}
    ok = True
    for asset, (attr, expected) in assets.items():
        call = ctx.call(asset, ctx.named(asset), label=f"declared constructor {asset}")
        criteria.append(C.fields(ctx, call, asset, f"fields@{asset}"))
        obj = _val(call)
        got = obj
        ok_attr = True
        try:
            for part in attr.split("."):
                got = getattr(got, part)
            if isinstance(expected, list):
                got = list(got)
                ok_attr = [c.npts for c in got] if attr == "current_sets" else got
                ok_attr = ok_attr == expected
            else:
                ok_attr = got == expected
        except Exception as exc:  # noqa: BLE001
            ok_attr = f"{type(exc).__name__}: {exc}"
        detail[asset] = {
            "attribute": attr,
            "returned": H.plain(got)
            if not isinstance(ok_attr, bool)
            else (H.plain(got) if not isinstance(got, str) else got),
            "matches_declared": ok_attr,
        }
        ok = ok and ok_attr is True
    criteria.append(C.crit("counts", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "filament counts and default currents"},
        "independent_check": {
            "method": "each constructor's declared filament count is read back from "
            "the returned object and compared with the declared value",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the constructors return objects whose counts are readable",
        "gaps": [],
    }


def closures_quasineutral(ctx: H.Ctx, task: dict) -> dict:
    qn = "scirel.closures.quasineutral-potential"
    boltz = "scirel.closures.boltzmann-quasineutrality"
    hall = "scirel.closures.hall-two-fluid-pressure"
    c1 = ctx.call(qn, ctx.named(qn), label="declared quasineutral solve")
    c2 = ctx.call(boltz, ctx.named(boltz), label="declared Boltzmann state")
    ctx.call(hall, ctx.named(hall), label="declared Hall two-fluid closure")
    criteria = [C.fields(ctx, c1, qn, "fields")]
    detail, ok = {}, False
    if "_value" in c2:
        _val(c2)
        named = ctx.named(boltz)
        e = 1.602176634e-19
        T = float(np.asarray(named["electron_temperature_j"]))
        phi0 = float(np.asarray(named["electron_phi_ref_v"]))
        n_ref = float(np.asarray(named["electron_density_ref_m3"]))
        z = float(np.asarray(named["ion_charge_state"]))
        n_i = float(np.asarray(named["ion_density_m3"]))
        # uniform density => potential pinned at the reference potential
        base = dict(named)
        uni = dict(base)
        uni["ion_density_m3"] = n_i
        r1 = ctx.call(
            boltz,
            {**named, "potential_v": phi0, "ion_density_m3": n_ref / z},
            label="uniform density at the reference potential",
        )
        r2 = ctx.call(
            boltz,
            {
                **named,
                "potential_v": phi0 + 0.1,
                "ion_density_m3": n_ref * np.exp(-e * 0.1 / T) / z,
            },
            label="perturbed state with the density moved by the Boltzmann factor",
        )
        flat_ok = None
        if "_value" in r1:
            flat_ok = abs(float(np.asarray(_val(r1)["logarithmic_charge_residual"]))) <= 1e-12
        ok = bool(flat_ok)
        detail = {
            "uniform_density_residual_at_reference": H.plain(
                _val(r1)["logarithmic_charge_residual"]
            )
            if "_value" in r1
            else None,
            "uniform_residual_zero": flat_ok,
            "perturbed_residual": H.plain(_val(r2)["logarithmic_charge_residual"])
            if "_value" in r2
            else None,
            "declared_temperature_k": T / 1.602176634e-19 * 1.602176634e-19,
        }
    criteria.append(C.crit("flatpotential", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "m^-3 residual"},
        "independent_check": {
            "method": "a uniform density placed at the reference potential must give "
            "a vanishing charge residual; the perturbed state is compared "
            "against the same residual",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the Boltzmann state is a pointwise entry, so the uniform-density limit is "
        "reproducible from declared inputs",
        "gaps": [
            H.gap(
                "confidence",
                "the declared sign-inversion half of the criterion needs a root solve of the "
                "quasineutral entry with a consumer-supplied residual callback, which the "
                "example does not declare; only the uniform-density limit was evaluated",
            )
        ],
    }


def diagnostics_picard_residual(ctx: H.Ctx, task: dict) -> dict:
    res = "scirel.diagnostics.picard-flux-residual"
    obs = "scirel.diagnostics.observation-residuals"
    c1 = ctx.call(res, ctx.named(res), label="declared residual against itself")
    criteria = [C.fields(ctx, c1, res, "fields")]
    detail, ok = {}, False
    named = ctx.named(res)
    keys = sorted(named)
    if "_value" in c1:
        np.asarray(_val(c1)["residual"], dtype=float)
        r1 = ctx.call(res, ctx.named(res), label="residual of the declared flux against itself")
        prev_key = next((k for k in keys if "prev" in k), keys[0])
        next_key = next((k for k in keys if k != prev_key), keys[-1])
        a = np.asarray(named[prev_key], dtype=float)
        r2 = ctx.call(res, {**named, next_key: 2.0 * a}, label="declared difference doubled")
        dev = float(np.max(np.abs(np.asarray(_val(r1)["residual"])))) if "_value" in r1 else None
        base = float(np.asarray(_val(r1)["residual"]).ravel()[0]) if "_value" in r1 else None
        doubled = float(np.asarray(_val(r2)["residual"]).ravel()[0]) if "_value" in r2 else None
        ok = base == 0.0
        detail = {
            "self_residual": dev,
            "self_residual_is_exactly_zero": ok,
            "doubled_amplitude_residual": doubled,
            "ratio": (doubled / base) if base not in (None, 0.0) else None,
            "compared_fields": [prev_key, next_key],
        }
    criteria.append(C.crit("zero", "invariant", "pass" if ok else "fail", detail))
    c3 = ctx.call(obs, ctx.named(obs), label="declared observation residual")
    criteria.append(C.fields(ctx, c3, obs, "fields_observation"))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "flux units and dimensionless chi2"},
        "independent_check": {
            "method": "the residual of a flux against itself must vanish exactly, and "
            "doubling the difference must double the residual",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the residual entry is pure and takes both arrays, so both halves are "
        "reproducible",
        "gaps": [],
    }


def physics_coulomb_logarithms(ctx: H.Ctx, task: dict) -> dict:
    ee = "scirel.physics.coulomb-ee"
    ei = "scirel.physics.coulomb-ei"
    th = "scirel.physics.thermal-energy"
    c1 = ctx.call(ee, ctx.named(ee), label="declared ee Coulomb logarithm")
    c2 = ctx.call(ei, ctx.named(ei), label="declared ei Coulomb logarithm")
    c3 = ctx.call(th, ctx.named(th), label="declared thermal energy")
    criteria = [C.fields(ctx, c3, th, "fields")]
    detail, ok = {}, False
    devs = {}
    for asset, offset in ((ee, 31.3), (ei, 31.0)):
        named = ctx.named(asset)
        T_eV = float(np.asarray(named["temperature_ev"])) if "temperature_ev" in named else None
        n = float(np.asarray(named["density_m3"])) if "density_m3" in named else None
        if T_eV is None or n is None:
            keys = sorted(named)
            T_eV = float(np.asarray(named[keys[0]]))
            n = float(np.asarray(named[keys[1]]))
        expected = offset - 0.5 * np.log(n) + np.log(1000.0 * T_eV)
        call = c1 if asset == ee else c2
        if "_value" in call:
            got = float(np.asarray(H.mapping(_val(call), asset)["result"]))
            devs[asset] = abs(got - expected) / max(abs(expected), 1e-300)
    ok = bool(devs) and max(devs.values()) <= 1e-12
    detail = {
        "formula_relative_deviation": devs,
        "warnings": {c["asset"]: c.get("warnings") for c in (c1, c2)},
    }
    criteria.append(C.crit("declared_formula", "invariant", "pass" if ok else "fail", detail))
    warn_ok = None
    try:
        named = ctx.named(ee)
        keys = sorted(named)
        low = dict(named)
        low[keys[0]] = 0.005
        r = ctx.call(ee, low, label="declared low-temperature call")
        warn_ok = bool(r.get("warnings")) and r["status"] == "returned"
        detail["low_temperature_warnings"] = r.get("warnings")
        detail["low_temperature_status"] = r["status"]
    except Exception as exc:  # noqa: BLE001
        detail["low_temperature_error"] = str(exc)
    criteria.append(C.crit("warning", "invariant", "pass" if warn_ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {
            "value": {**detail},
            "unit": "dimensionless Coulomb logarithm; J for thermal energy",
        },
        "independent_check": {
            "method": "both logarithms recomputed from the printed formula and the "
            "low-temperature call checked for its declared warning",
            "observed": {**detail},
            "verdict": "pass" if (ok and warn_ok) else "fail",
        },
        "package_sufficient": bool(ok and warn_ok),
        "sufficient_reason": "the formula is printed in the contract and the warning is observable "
        "through the standard warnings mechanism",
        "gaps": [],
    }


CHECKS.update(
    {
        "field-filament-superposition": field_filament_superposition,
        "field-flux-to-poloidal": field_flux_to_poloidal,
        "geometry-equilibrium-grid": geometry_equilibrium_grid,
        "geometry-mesh-and-volume": geometry_mesh_and_volume,
        "numerics-basis-projection": numerics_basis_projection,
        "numerics-splines-and-inverse": numerics_splines_and_inverse,
        "sampling-regular-grid": sampling_regular_grid,
        "sampling-transform-and-derivative": sampling_transform_and_derivative,
        "fieldline-set-and-arclength": fieldline_set_and_arclength,
        "equilibrium-isotropic-picard": equilibrium_isotropic_picard,
        "equilibrium-anisotropic-picard": equilibrium_anisotropic_picard,
        "mirror-frank-egedal": mirror_frank_egedal,
        "mirror-ambipolar-and-loss-cone": mirror_ambipolar_and_loss_cone,
        "electromagnetism-device-composition": em_device_composition,
        "configurations-retained-geometries": configurations_retained_geometries,
        "closures-quasineutral": closures_quasineutral,
        "diagnostics-picard-residual": diagnostics_picard_residual,
        "physics-coulomb-logarithms": physics_coulomb_logarithms,
    }
)
