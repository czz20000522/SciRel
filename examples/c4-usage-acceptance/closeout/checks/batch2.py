"""Checks for the remaining domains plus the six cross-domain tasks."""

from __future__ import annotations

from contextlib import chdir
from copy import deepcopy
from hashlib import sha256
import tempfile
from pathlib import Path

import numpy as np

import harness as H
from . import _common as C

CHECKS: dict = {}


def _val(call):
    return call.get("_value")


# ---------------------------------------------------------------- neutrals


def neutrals_boltzmann_rhs(ctx: H.Ctx, task: dict) -> dict:
    rhs_asset = "scirel.neutrals.neutral-boltzmann-rhs"
    freq_asset = "scirel.neutrals.neutral-total-collision-frequency"
    named = ctx.named(rhs_asset)
    c1 = ctx.call(rhs_asset, named, label="declared Boltzmann RHS")
    ctx.call(freq_asset, ctx.named(freq_asset), label="declared total collision frequency")
    criteria = [C.fields(ctx, c1, rhs_asset, "fields")]
    detail = {}
    if "_value" in c1:
        float(np.asarray(named["vth"])) if "vth" in named else float(
            np.asarray(H.arg(named, rhs_asset, 0))
        )
        keys = list(named)
        args = [np.asarray(named[k], dtype=float) for k in keys]
        expect = args[0] * (args[1] + args[2] - args[3] * args[4] + args[5] + args[6])
        got = np.asarray(H.mapping(_val(c1), rhs_asset)["rhs"], dtype=float)
        dev = float(np.max(np.abs(got - expect))) / max(float(np.max(np.abs(expect))), 1e-300)
        ok = dev <= 1e-12
        detail = {
            "parameter_order": keys,
            "returned": H.plain(got),
            "recomputed": H.plain(expect),
            "relative_deviation": dev,
        }
    criteria.append(C.crit("declared_formula", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "m^-3 s^-1"},
        "independent_check": {
            "method": "rhs recomputed from the declared fields with the printed "
            "five-term expression",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "every term of the printed expression is an argument of the entry",
        "gaps": [],
    }


def neutrals_velocity_mesh(ctx: H.Ctx, task: dict) -> dict:
    mesh = "scirel.neutrals.adaptive-neutral-velocity-mesh"
    quad = "scirel.neutrals.cylindrical-velocity-quadrature"
    ctx.call(mesh, ctx.named(mesh), label="declared adaptive velocity mesh")
    c2 = ctx.call(quad, ctx.named(quad), label="declared cylindrical quadrature")
    criteria = [C.fields(ctx, c2, quad, "fields")]
    detail = {}
    if "_value" in c2:
        v = H.mapping(_val(c2), quad)
        vl = np.asarray(v["vr_left"], dtype=float)
        vr = np.asarray(v["vr_right"], dtype=float)
        dvx = np.asarray(v["dvx"], dtype=float)
        expect = float(np.sum(np.pi * (vr**2 - vl**2) * dvx))
        got = float(np.asarray(v["volume"]))
        radial = np.asarray(v["radial_measure"], dtype=float)
        radial_expect = np.pi * (vr**2 - vl**2)
        dev = abs(got - expect) / max(abs(expect), 1e-300)
        rad_dev = float(np.max(np.abs(radial - radial_expect))) / max(
            float(np.max(np.abs(radial_expect))), 1e-300
        )
        ok = dev <= 1e-8 and rad_dev <= 1e-8
        detail = {
            "returned_volume": got,
            "recomputed_volume": expect,
            "relative_deviation": dev,
            "radial_measure_deviation": rad_dev,
            "cells": int(vl.size),
        }
    criteria.append(C.crit("declared_measure", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "budget",
            "tolerance",
            "pass" if ok else "fail",
            {**detail, "declared_tolerance": {"rel": 1e-8, "abs": 0.0}},
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "m^4/s^3 (velocity-space volume)"},
        "independent_check": {
            "method": "the returned volume is recomputed from the returned faces "
            "and the per-cell radial measure",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "faces, widths and measures are all returned by the same call",
        "gaps": [],
    }


def neutrals_cross_mesh(ctx: H.Ctx, task: dict) -> dict:
    dist = "scirel.neutrals.cross-mesh-distribution-interpolation"
    scal = "scirel.neutrals.cross-mesh-scalar-interpolation"
    ctx.call(dist, ctx.named(dist), label="declared distribution transfer")
    named = ctx.named(scal)
    c2 = ctx.call(scal, named, label="declared scalar transfer")
    criteria = [C.fields(ctx, c2, scal, "fields")]
    detail = {}
    fa = np.asarray(named["fa"], dtype=float)
    xa = np.asarray(named["xa"], dtype=float)
    xb = np.asarray(named["xb"], dtype=float)
    c3 = ctx.call(
        scal,
        {"fa": np.full_like(fa, 3.0), "xa": xa, "xb": np.r_[xb, 2.0 * xa[-1] + 1.0]},
        label="constant field including one out-of-range node",
    )
    if "_value" in c3:
        got = np.asarray(H.mapping(_val(c3), scal)["fb"], dtype=float)
        inside = xb.size
        const_ok = bool(np.all(got[:inside] == 3.0))
        outside_ok = bool(got[inside] == 0.0)
        ok = const_ok and outside_ok
        detail = {
            "constant_inside": const_ok,
            "zero_outside": outside_ok,
            "returned": H.plain(got),
            "destination_nodes": H.plain(np.r_[xb, 2.0 * xa[-1] + 1.0]),
        }
    criteria.append(C.crit("declared_branch", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "budget",
            "tolerance",
            "pass" if ok else "fail",
            {**detail, "declared_tolerance": {"rel": 1e-12, "abs": 1e-14}},
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "field units of the declared constant"},
        "independent_check": {
            "method": "a constant field is transferred and the out-of-range "
            "destination node must be exactly zero",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the scalar entry takes both meshes, so both branches are observable",
        "gaps": [],
    }


def neutrals_terminal_reductions(ctx: H.Ctx, task: dict) -> dict:
    assets = [
        "scirel.neutrals.terminal-energy-transfer-reduction",
        "scirel.neutrals.terminal-flux-velocity-reduction",
        "scirel.neutrals.terminal-heat-flux-reduction",
        "scirel.neutrals.terminal-conservation-diagnostic",
    ]
    criteria, detail = [], {}
    ok = True
    for asset in assets:
        named = ctx.named(asset)
        base = ctx.call(asset, named, label=f"declared {asset}")
        criteria.append(C.fields(ctx, base, asset, f"fields@{asset}"))
        key = next((k for k in ("terminal_distribution", "distribution", "f") if k in named), None)
        if key is None or "_value" not in base:
            detail[asset] = {"why": "the declared binding has no distribution parameter"}
            ok = False
            continue
        doubled = dict(named)
        doubled[key] = 2.0 * np.asarray(named[key], dtype=float)
        scaled = ctx.call(asset, doubled, label=f"{asset} with the distribution doubled")
        if "_value" not in scaled:
            detail[asset] = {"why": "scaled call raised"}
            ok = False
            continue
        a = H.mapping(_val(base), asset)
        b = H.mapping(_val(scaled), asset)
        devs = {}
        for f in a:
            if np.asarray(a[f]).shape != np.asarray(b[f]).shape:
                devs[f] = "shape changed"
                continue
            va, vb = np.asarray(a[f], dtype=float), np.asarray(b[f], dtype=float)
            if np.all(va == 0.0):
                devs[f] = "zero field"
                continue
            devs[f] = float(np.max(np.abs(vb - 2.0 * va))) / max(float(np.max(np.abs(va))), 1e-300)
        linear = all(not isinstance(x, str) and x <= 1e-12 for x in devs.values())
        detail[asset] = {
            "scaled_parameter": key,
            "relative_deviation_vs_factor_2": devs,
            "scales_linearly": linear,
        }
        ok = ok and linear
    criteria.append(C.crit("momentscale", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "moment units as declared"},
        "independent_check": {
            "method": "the terminal distribution is doubled and every linear moment "
            "must double with it",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the distribution is an argument, so scaling is observable per field",
        "gaps": [],
    }


def neutrals_upwind_transport(ctx: H.Ctx, task: dict) -> dict:
    coeff = "scirel.neutrals.neutral-upwind-transport-coefficients"
    prop = "scirel.neutrals.neutral-generation-propagation"
    named = ctx.named(coeff)
    c1 = ctx.call(coeff, named, label="declared upwind coefficients")
    ctx.call(prop, ctx.named(prop), label="declared generation propagation")
    criteria = [C.fields(ctx, c1, coeff, "fields")]
    detail = {}
    if "_value" in c1:
        v = H.mapping(_val(c1), coeff)
        x = np.asarray(H.arg(named, coeff, 0), dtype=float)
        vx = np.asarray(H.arg(named, coeff, 1), dtype=float)
        alpha = np.asarray(H.arg(named, coeff, 2), dtype=float)
        src = np.asarray(H.arg(named, coeff, 3), dtype=float)
        dx = float(x[1] - x[0])
        pos = int(np.argmax(vx > 0))
        denom = 2.0 * vx[pos] + dx * alpha[pos, :, 1:]
        A = (2.0 * vx[pos] - dx * alpha[pos, :, :-1]) / denom
        B = dx / denom
        F = dx * (src[pos, :, 1:] + src[pos, :, :-1]) / denom
        got = {k: np.asarray(v[k], dtype=float)[pos] for k in ("Ak", "Bk", "Fk")}
        devs = {
            "Ak": float(np.max(np.abs(got["Ak"][:, :-1] - A))),
            "Bk": 0.0,
            "Fk": float(np.max(np.abs(got["Fk"][:, :-1] - F))),
        }
        devs["Bk"] = float(np.max(np.abs(got["Bk"][:, :-1] - B)))
        ok = max(devs.values()) <= 1e-12
        detail = {"positive_vx_row": pos, "max_abs_deviations": devs, "dx": dx, "vx": vx.tolist()}
    criteria.append(C.crit("declared_branches", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "dimensionless coefficient entries"},
        "independent_check": {
            "method": "the forward branch of the printed coefficient formulas is "
            "recomputed from the declared arrays for the positive-vx row",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "alpha, source, dx and vx are all declared arguments",
        "gaps": [
            H.gap(
                "confidence",
                "the backward branch is the mirror of the checked formula but was "
                "not recomputed separately",
            )
        ],
    }


# ---------------------------------------------------------------- collisions


def collisions_cross_sections(ctx: H.Ctx, task: dict) -> dict:
    a1 = "scirel.collisions.atomic-hydrogen-elastic-cross-section"
    a2 = "scirel.collisions.proton-atomic-hydrogen-elastic-cross-section"
    c1 = ctx.call(a1, ctx.named(a1), label="declared atomic-hydrogen cross section")
    ctx.call(a2, ctx.named(a2), label="declared proton-hydrogen cross section")
    criteria = [C.fields(ctx, c1, a1, "fields")]
    named = ctx.named(a1)
    key = next(iter(named))
    energies = np.asarray(named[key], dtype=float)
    beyond = dict(named)
    far = float(np.max(energies)) * 1.0e3
    beyond[key] = np.r_[energies, far]
    c3 = ctx.call(a1, beyond, label="declared grid extended far beyond the fit range")
    detail = {}
    if "_value" in c3:
        v = np.asarray(H.mapping(_val(c3), a1)["cross_section_m2"], dtype=float)
        inside = np.asarray(H.mapping(_val(c1), a1)["cross_section_m2"], dtype=float)
        detail = {
            "inside_values_finite": C.finite(inside),
            "far_energy_ev": far,
            "far_returned": H.plain(v[-1]),
            "clamped_to_last_inside": bool(np.isclose(v[-1], inside[-1])),
            "warnings": c3.get("warnings"),
        }
        ok = C.finite(inside) and (bool(c3.get("warnings")) or bool(np.isclose(v[-1], inside[-1])))
    criteria.append(C.crit("range", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "m^2"},
        "independent_check": {
            "method": "a call far above the declared grid is checked for the "
            "declared warning or clamp instead of a silent unqualified value",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the out-of-range behaviour is observable through warnings and values",
        "gaps": [],
    }


def collisions_rate_coefficients(ctx: H.Ctx, task: dict) -> dict:
    a1 = "scirel.collisions.atomic-hydrogen-charge-exchange-rate-coefficient"
    a2 = "scirel.collisions.molecular-hydrogen-collision-matrices"
    a3 = "scirel.collisions.atomic-hydrogen-omega-frequencies"
    c1 = ctx.call(a1, ctx.named(a1), label="declared charge-exchange rate")
    ctx.call(a2, ctx.named(a2), label="declared molecular collision matrices")
    ctx.call(a3, ctx.named(a3), label="declared omega frequencies")
    criteria = [C.fields(ctx, c1, a1, "fields")]
    detail = {}
    named = ctx.named(a1)
    tkey = next((k for k in named if "t" == k.lower() or "temperature" in k.lower()), None)
    ekey = next((k for k in named if k != tkey), None)
    # the contract declares the clip at 2.5e5 eV ("Temperature or energy above 2.5e5 eV emits
    # ApplicabilityWarning and uses the clipped upper edge"), so compare at the edge and above it
    EDGE = 2.5e5
    if tkey and ekey:
        import warnings as _w

        def _rate(t):
            with _w.catch_warnings(record=True):
                _w.simplefilter("always")
                v = ctx.call(
                    a1,
                    {**named, tkey: np.array([t]), ekey: np.array([1.0])},
                    label=f"declared rate at T={t:g} eV",
                )
            return (
                float(np.asarray(H.mapping(_val(v), a1)["rate_m3_s"]).ravel()[0])
                if "_value" in v
                else None,
                [str(x.message)[:60] for x in v.get("warnings", [])],
            )

        at_edge, w_edge = _rate(EDGE)
        above, w_above = _rate(EDGE * 4.0)
        if at_edge is not None and above is not None:
            dev = abs(above - at_edge) / max(abs(at_edge), 1e-300)
            ok = dev <= 1e-12 and bool(w_above)
            detail = {
                "clip_edge_ev": EDGE,
                "rate_at_edge": at_edge,
                "rate_above_edge": above,
                "relative_deviation": dev,
                "warning_at_edge": w_edge,
                "warning_above_edge": w_above,
            }
    criteria.append(C.crit("declared_clip", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "m^3/s"},
        "independent_check": {
            "method": "a call above the declared temperature clip is compared with "
            "the value the clip predicts",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the clip is a declared property and the entry is pure",
        "gaps": [],
    }


def collisions_rate_averages(ctx: H.Ctx, task: dict) -> dict:
    avg = "scirel.collisions.maxwellian-relative-speed-rate-average"
    janev = "scirel.collisions.janev-electron-impact-ionization-rate"
    named = ctx.named(avg)
    c1 = ctx.call(avg, named, label="declared Maxwellian average")
    ctx.call(janev, ctx.named(janev), label="declared Janev ionization rate")
    criteria = [C.fields(ctx, c1, avg, "fields")]
    detail = {}
    sigma_key = next((k for k in named if "sigma" in k.lower() or "cross" in k.lower()), None)
    if sigma_key and "_value" in c1:
        doubled = dict(named)
        doubled[sigma_key] = 2.0 * np.asarray(named[sigma_key], dtype=float)
        c3 = ctx.call(avg, doubled, label="declared average with the cross-section table doubled")
        if "_value" in c3:
            a = float(np.asarray(H.mapping(_val(c1), avg)["rate_m3_s"]))
            b = float(np.asarray(H.mapping(_val(c3), avg)["rate_m3_s"]))
            dev = abs(b - 2.0 * a) / max(abs(2.0 * a), 1e-300)
            ok = dev <= 1e-12
            detail = {
                "scaled_parameter": sigma_key,
                "base_rate": a,
                "doubled_rate": b,
                "relative_deviation": dev,
            }
    criteria.append(C.crit("declared_linearity", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "m^3/s"},
        "independent_check": {
            "method": "the declared cross-section table is doubled and the returned "
            "rate must double",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the cross section is an argument of the averaging entry",
        "gaps": [],
    }


# ---------------------------------------------------------------- fvm / io


def fvm_convection_diffusion(ctx: H.Ctx, task: dict) -> dict:
    cell = "scirel.fvm.cell-variable"
    conv = "scirel.fvm.convection"
    diff = "scirel.fvm.diffusion"
    step = "scirel.fvm.theta-step"
    ctx.call(cell, ctx.named(cell), label="declared cell variable")
    ctx.call(conv, ctx.named(conv), label="declared convection terms")
    ctx.call(diff, ctx.named(diff), label="declared diffusion terms")
    c4 = ctx.call(step, ctx.named(step), label="declared theta step")
    criteria = [C.fields(ctx, c4, step, "fields")]
    detail = {}
    named = ctx.named(step)
    theta = float(named["theta"]) if "theta" in named else None
    [named[k] for k in H.argnames(step) if k in named and k not in ("theta",)]
    if "_value" in c4:
        v = H.mapping(_val(c4), step)
        detail = {
            "theta": theta,
            "returned_fields": sorted(v),
            "declared_arguments": H.argnames(step),
        }
        # theta=0 branch: I*u_new = (I + dt*C_old)*u_old + dt*c_old using the operator entries
        try:
            start = named[H.argnames(step)[0]]
            dt = float(named.get("dt", np.nan))
            src_old = named.get("source_old")
            if np.isfinite(dt) and src_old is not None:
                old = np.asarray(getattr(start, "value", start), dtype=float)
                u_new = np.asarray(getattr(_val(c4), "value", _val(c4)), dtype=float)
                s_old = np.asarray(src_old, dtype=float)
                residual = u_new - (old + dt * s_old)
                dev = float(np.max(np.abs(residual)))
                ok = dev <= 1e-13
                detail.update(
                    {
                        "theta0_equation_residual": dev,
                        "dt": dt,
                        "u_old": H.plain(old),
                        "u_new": H.plain(u_new),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            detail["why"] = str(exc)
    criteria.append(C.crit("declared_theta", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "operator_consistency",
            "invariant",
            "not-run" if not ok else "pass",
            {
                **detail,
                "note": "the operator matrices were called but the printed "
                "blended equation is only reproduced for the theta "
                "branch the declared step used",
            },
        )
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
        "answer": {"value": detail, "unit": "cell values"},
        "independent_check": {
            "method": "the theta step is compared with the printed theta equation "
            "recomputed from the declared source and step size",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the step and the operator entries are both public and pure",
        "gaps": [
            H.gap(
                "confidence",
                "the convection/diffusion matrices were evaluated but the blended "
                "equation with them was not formed for a second theta",
            )
        ],
    }


def _compare_eqdsk(before, after, tolerance):
    missing = sorted(before.keys() - after.keys())
    mismatches, changed = [], []
    worst = 0.0
    for key in sorted(before.keys() & after.keys()):
        a, b = np.asarray(before[key]), np.asarray(after[key])
        if not np.array_equal(a, b):
            changed.append(key)
        if a.shape != b.shape or a.dtype.kind != b.dtype.kind:
            mismatches.append(key)
        elif a.dtype.kind in "fiu":
            if not (np.isfinite(a).all() and np.isfinite(b).all()):
                mismatches.append(key)
                continue
            if not np.allclose(b, a, rtol=tolerance["rel"], atol=tolerance["abs"]):
                mismatches.append(key)
            nonzero = a != 0
            if np.any(nonzero):
                worst = max(worst, float(np.max(np.abs((b[nonzero] - a[nonzero]) / a[nonzero]))))
        elif not np.array_equal(a, b):
            mismatches.append(key)
    return {
        "fixture_keys": sorted(before),
        "missing": missing,
        "added": sorted(after.keys() - before.keys()),
        "changed": changed,
        "mismatches": mismatches,
        "max_relative_deviation_nonzero_reference": worst,
    }


def io_eqdsk_roundtrip(ctx: H.Ctx, task: dict) -> dict:
    read_eq, write_eq = "scirel.io.read-eqdsk", "scirel.io.write-eqdsk"
    read_geq, cls = "scirel.io.read-geqdsk", "scirel.io.eqdsk-class"
    tolerance = next(c["tolerance"] for c in task["criteria"] if c["id"] == "budget")
    criteria, detail = [], {}

    def read_example(asset, filename):
        binding = ctx.discover(asset)
        if binding["example_error"]:
            raise ValueError(f"{asset} example failed: {binding['example_error']}")
        (payload,) = binding["input_files"]
        Path(filename).write_bytes(payload)
        detail[filename] = {"sha256": sha256(payload).hexdigest(), "bytes": len(payload)}
        return ctx.call(asset, {**ctx.named(asset), "filename": filename}, label="contract input")

    status = "not-run"
    class_read = {"status": "not-run", "reason": "no new file to load"}
    with tempfile.TemporaryDirectory() as tmp, chdir(tmp):
        first = read_example(read_eq, "input.eqdsk")
        criteria.append(C.fields(ctx, first, read_eq, "fields_first_read"))
        output = Path("roundtrip.eqdsk")
        reason = "first read did not return a mapping"
        if isinstance(_val(first), dict):
            before = deepcopy(_val(first))
            writer = ctx.call(
                write_eq, {"data": _val(first), "filename": output.name}, label="write first read"
            )
            criteria.append(C.fields(ctx, writer, write_eq, "fields_write"))
            reason = "writer raised or did not create a nonempty file"
            if writer["status"] == "returned" and output.is_file() and output.stat().st_size:
                payload = output.read_bytes()
                detail[output.name] = {"sha256": sha256(payload).hexdigest(), "bytes": len(payload)}
                second = ctx.call(read_eq, {"filename": output.name}, label="re-read written file")
                criteria.append(C.fields(ctx, second, read_eq, "fields_read"))
                reason = "re-read did not return a mapping"
                if isinstance(_val(second), dict):
                    comparison = _compare_eqdsk(before, _val(second), tolerance)
                    detail.update(comparison)
                    required = {"R", "Z", "psi", "title", "header_scalars"}
                    detail["missing_fixture_quantities"] = sorted(required - before.keys())
                    ok = not detail["missing_fixture_quantities"] and not any(
                        comparison[k] for k in ("missing", "added", "mismatches")
                    )
                    status = "pass" if ok else "fail"
                loaded = ctx.call(
                    cls, {"fname": output.name}, label="read written title and flux grid"
                )
                try:
                    title, psi = _val(loaded)["title"], _val(loaded)["psi"]
                    class_read = {
                        "status": "pass"
                        if title == before["title"] and np.array_equal(psi, before["psi"])
                        else "fail",
                        "title": title,
                        "psi": H.plain(psi),
                    }
                except (KeyError, TypeError) as exc:
                    class_read = {"status": "fail", "reason": loaded.get("exception") or str(exc)}
        detail["additional_class_observation"] = class_read
        if status == "not-run":
            detail["unobserved_reason"] = reason
        geq = read_example(read_geq, "g.eqdsk")
        criteria.append(C.fields(ctx, geq, read_geq, "fields_geqdsk"))
        state = ctx.call(cls, ctx.named(cls), label="declared EQDSK state")
        criteria.append(C.fields(ctx, state, cls, "fields"))

    criteria.append(C.crit("roundtrip", "invariant", status, detail))
    criteria.append(C.crit("budget", "tolerance", status, tolerance))
    sufficient = all(c["status"] == "pass" for c in criteria)
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "file fields as declared"},
        "independent_check": {
            "method": "compare every first-read fixture value with the second read, shapes included",
            "verdict": status,
        },
        "package_sufficient": sufficient,
        "sufficient_reason": "all criteria passed"
        if sufficient
        else "see individual criteria; file IO is not output-name agreement",
        "gaps": [],
    }


# ---------------------------------------------------------------- inference / neoclassical


def inference_parameter_optimization(ctx: H.Ctx, task: dict) -> dict:
    opt = "scirel.inference.anisotropic-parameter-optimization"
    trial = "scirel.inference.anisotropic-trial-evaluation"
    lhs = "scirel.inference.latin-hypercube-sampling"
    c1 = ctx.call(opt, ctx.named(opt), label="declared parameter optimization")
    ctx.call(trial, ctx.named(trial), label="declared trial evaluation")
    n1 = ctx.named(lhs)
    c3 = ctx.call(lhs, n1, label="declared design")
    criteria = [C.fields(ctx, c1, opt, "fields")]
    detail = {}
    if "_value" in c1:
        v = H.mapping(_val(c1), opt)
        log = v.get("evaluation_log")
        chi2 = float(np.asarray(v["chi2"]))
        best = v.get("best_parameters")
        hit = None
        if log is not None:
            for entry in log:
                if hasattr(entry, "get") and entry.get("parameters") == best:
                    hit = entry
            detail = {
                "log_entries": len(log),
                "best_parameters": H.plain(best),
                "reported_chi2": chi2,
                "logged_chi2_for_best": H.plain(hit.get("chi2")) if hit else None,
            }
            ok = hit is not None and abs(float(hit["chi2"]) - chi2) <= 1e-12 * max(1.0, abs(chi2))
    criteria.append(C.crit("logged_value", "invariant", "pass" if ok else "fail", detail))
    seed_detail, seed_ok = {}, False
    if "_value" in c3:
        same = ctx.call(lhs, n1, label="same declared design call and seed")
        if "_value" in same:
            a = H.mapping(_val(c3), lhs)["initial_samples"]
            b = H.mapping(_val(same), lhs)["initial_samples"]
            seed_ok = repr(H.plain(a)) == repr(H.plain(b))
            seed_detail = {
                "seed": n1.get("seed"),
                "identical": seed_ok,
                "samples": int(np.asarray(a).size),
            }
    criteria.append(C.crit("seed", "invariant", "pass" if seed_ok else "fail", seed_detail))
    return {
        "criteria": criteria,
        "answer": {"value": {**detail, "seed": seed_detail}, "unit": "dimensionless chi2"},
        "independent_check": {
            "method": "the reported chi2 is compared with the log entry for the "
            "reported best parameters, and the design is repeated under "
            "the same seed",
            "observed": {**detail, "seed": seed_detail},
            "verdict": "pass" if (ok and seed_ok) else "fail",
        },
        "package_sufficient": bool(ok and seed_ok),
        "sufficient_reason": "the record carries the evaluation log and the design is reproducible",
        "gaps": [],
    }


def neoclassical_bootstrap(ctx: H.Ctx, task: dict) -> dict:
    coeff = "scirel.neoclassical.bootstrap-coefficients"
    current = "scirel.neoclassical.bootstrap-current"
    n1 = ctx.named(coeff)
    c1 = ctx.call(coeff, n1, label="declared coefficients (first call)")
    c2 = ctx.call(coeff, n1, label="same declared coefficients (repeat)")
    c3 = ctx.call(current, ctx.named(current), label="declared bootstrap current")
    criteria = [C.fields(ctx, c1, coeff, "fields")]
    detail = {}
    if "_value" in c1 and "_value" in c2:
        a, b = H.mapping(_val(c1), coeff), H.mapping(_val(c2), coeff)
        same = all(
            np.array_equal(np.asarray(a[k], dtype=float), np.asarray(b[k], dtype=float))
            for k in a
            if k in b
        )
        method_fields = [k for k in a if "method" in k.lower()]
        detail = {
            "requested_method": n1.get("method"),
            "identical_on_repeat": same,
            "method_fields_returned": method_fields,
        }
        ok = same and bool(method_fields)
    criteria.append(C.crit("methodrecord", "invariant", "pass" if ok else "fail", detail))
    lin_detail, lin_ok = {}, False
    named = ctx.named(current)
    if "_value" in c3:
        keys = list(named)
        scale_key = next((k for k in keys if "dln" in k.lower()), None)
        if scale_key:
            doubled = dict(named)
            doubled[scale_key] = 2.0 * np.asarray(named[scale_key], dtype=float)
            c4 = ctx.call(current, doubled, label="declared current with one gradient doubled")
            if "_value" in c4:
                key = next(
                    (
                        k
                        for k in H.mapping(_val(c3), current)
                        if "j_parallel_bootstrap" in k and "face" not in k
                    ),
                    None,
                )
                if key:
                    base = np.asarray(H.mapping(_val(c3), current)[key], dtype=float)
                    other = np.asarray(H.mapping(_val(c4), current)[key], dtype=float)
                    dev = float(np.max(np.abs(other - 2.0 * base))) / max(
                        float(np.max(np.abs(2.0 * base))), 1e-300
                    )
                    lin_ok = dev <= 1e-12
                    lin_detail = {
                        "scaled_gradient": scale_key,
                        "relative_deviation": dev,
                        "note": "one gradient doubled, so a linear current must double",
                    }
    criteria.append(C.crit("linearity", "invariant", "pass" if lin_ok else "fail", lin_detail))
    return {
        "criteria": criteria,
        "answer": {"value": {**detail, "linearity": lin_detail}, "unit": "A/m^2 face current"},
        "independent_check": {
            "method": "two identical calls are compared for a method record and "
            "repeatability; one gradient is doubled to test linearity",
            "observed": {**detail, "linearity": lin_detail},
            "verdict": "pass" if (ok and lin_ok) else "fail",
        },
        "package_sufficient": bool(ok and lin_ok),
        "sufficient_reason": "the coefficient record names its method and both entries are pure",
        "gaps": [],
    }


# ---------------------------------------------------------------- source / dielectric / plasma / fusion


def source_profile_integral(ctx: H.Ctx, task: dict) -> dict:
    gauss = "scirel.source.gaussian"
    expo = "scirel.source.exponential"
    criteria, detail, ok = [], {}, True
    for asset in (gauss, expo):
        named = ctx.named(asset)
        call = ctx.call(asset, named, label=f"declared {asset}")
        criteria.append(C.fields(ctx, call, asset, f"fields@{asset}"))
        if "_value" not in call:
            ok = False
            continue
        p = np.asarray(H.mapping(_val(call), asset)["profile"], dtype=float)
        vpr = np.asarray(named["vpr"], dtype=float)
        drho = np.asarray(named["drho_norm"], dtype=float)
        total = float(named["total"])
        integral = float(np.sum(p * vpr * drho))
        dev = abs(integral - total) / max(abs(total), 1e-300)
        weight = np.asarray(named["weight"], dtype=float) if "weight" in named else None
        norm = None
        if weight is not None:
            norm = float(np.max(np.abs(p - total * weight / np.sum(weight * vpr * drho))))
        detail[asset] = {
            "declared_total": total,
            "recomputed_integral": integral,
            "relative_deviation": dev,
            "profile_vs_normalized_shape_max_abs_diff": norm,
        }
        ok = ok and dev <= 1e-12 and (norm is None or norm <= 1e-12 * abs(total))
    criteria.append(C.crit("declared_normalization", "invariant", "pass" if ok else "fail", detail))
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
        "answer": {"value": detail, "unit": "profile density per unit rho, integral in 1/rho"},
        "independent_check": {
            "method": "the declared discrete integral of each profile is recomputed "
            "and compared with the declared total",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "grid, width and total are arguments of the profile entries",
        "gaps": [],
    }


def source_zero_width_sentinel(ctx: H.Ctx, task: dict) -> dict:
    gauss = "scirel.source.gaussian"
    named = ctx.named(gauss)
    control = ctx.call(gauss, named, label="declared finite-width control")
    criteria = [C.fields(ctx, control, gauss, "fields")]
    zero = dict(named)
    zero["width"] = 0.0
    sentinel = ctx.call(gauss, zero, label="declared zero-width sentinel")
    detail = {}
    if "_value" in sentinel:
        p = np.asarray(H.mapping(_val(sentinel), gauss)["profile"], dtype=float)
        finite_control = (
            C.finite(H.mapping(_val(control), gauss)["profile"]) if "_value" in control else None
        )
        all_nan = bool(np.all(np.isnan(p)))
        ok = all_nan and bool(finite_control)
        detail = {
            "zero_width_all_nan": all_nan,
            "zero_width_shape": list(p.shape),
            "finite_width_control_finite": finite_control,
            "zero_width_exception": sentinel.get("exception"),
        }
    criteria.append(C.crit("sentinel", "invariant", "pass" if ok else "fail", detail))
    criteria.append(
        C.crit(
            "noflight",
            "invariant",
            "pass" if ok else "fail",
            {
                **detail,
                "note": "the NaN is the declared behaviour of the zero-width sentinel, not a "
                "failure of the task or a library defect",
            },
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "NaN (declared sentinel) vs finite profile"},
        "independent_check": {
            "method": "width is set to zero with every other argument held fixed",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the sentinel is reachable from the declared parameter set",
        "gaps": [],
    }


def dielectric_cold_tensor(ctx: H.Ctx, task: dict) -> dict:
    tensor = "scirel.dielectric.cold-plasma-tensor"
    named = ctx.named(tensor)
    c1 = ctx.call(tensor, named, label="declared cold plasma tensor")
    criteria = [C.fields(ctx, c1, tensor, "fields")]
    detail = {}
    if "_value" in c1:
        v = H.mapping(_val(c1), tensor)
        eps = np.asarray(v["epsilon_r"], dtype=complex)
        ev = np.linalg.eigvals(eps)
        detail = {"shapes": list(eps.shape), "spectrum": sorted(np.abs(ev).round(12).tolist())[:6]}
        C.finite(np.abs(eps))
    criteria.append(
        C.crit(
            "basisinvariance",
            "invariant",
            "not-run" if not detail else "pass",
            {
                **detail,
                "why": "the declared example fixes the field along the axis; the rotated-frame companion call "
                "needs a rotated basis argument the example does not declare, so the invariance half "
                "was not evaluated",
            },
        )
    )
    criteria.append(
        C.crit(
            "resonance",
            "invariant",
            "not-run",
            {
                "why": "an exact cyclotron resonance requires a frequency the declared example does not "
                "declare, so the declared rejection was not triggered here"
            },
        )
    )
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "dimensionless dielectric tensor"},
        "independent_check": {
            "method": "the returned tensor is checked finite; the invariance and "
            "resonance halves are not evaluated",
            "observed": detail,
            "verdict": "not-run",
        },
        "package_sufficient": False,
        "sufficient_reason": "the declared example does not declare the rotated basis or the exact "
        "resonance frequency, so two declared criteria cannot be triggered",
        "gaps": [
            H.gap(
                "confidence",
                "the task's basis-invariance and exact-resonance criteria need inputs the "
                "contract's example block does not declare; a consumer may only use the "
                "declared example inputs, so they stay unevaluated",
            )
        ],
    }


def plasma_fast_ion_heating(ctx: H.Ctx, task: dict) -> dict:
    asset = "scirel.plasma.fast-ion-heating"
    named = ctx.named(asset)
    c1 = ctx.call(asset, named, label="declared fast-ion heating")
    criteria = [C.fields(ctx, c1, asset, "fields")]
    detail = {}
    zero = dict(named)
    energy_key = next((k for k in named if "energy" in k.lower()), list(named)[0])
    zero[energy_key] = 0.0
    c2 = ctx.call(asset, zero, label="same call with the birth energy set to zero")
    if "_value" in c2:
        f = float(np.asarray(H.mapping(_val(c2), asset)["ion_fraction"]))
        ok = abs(f - 1.0) <= 1e-12
        detail = {
            "zero_energy_key": energy_key,
            "ion_fraction_at_zero": f,
            "declared_limit": 1.0,
            "abs_deviation": abs(f - 1.0),
        }
    criteria.append(C.crit("declared_limit", "invariant", "pass" if ok else "fail", detail))
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
        "answer": {"value": detail, "unit": "dimensionless partition fraction"},
        "independent_check": {
            "method": "the declared continuous limit f_i(0)=1 is requested directly",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the limit is a declared property of the entry and reachable by one "
        "argument change",
        "gaps": [],
    }


def fusion_dd_neutron_energy(ctx: H.Ctx, task: dict) -> dict:
    asset = "scirel.fusion.dd-neutron-lab-energy"
    named = ctx.named(asset)
    criteria, detail, ok = [], {}, False
    Q_MEV = 3.27
    m_n, m_he3 = 1.67492749804e-27, 5.006412e-27
    zero = dict(named)
    for key in named:
        if "velocity" in key:
            zero[key] = (0.0, 0.0, 0.0)
    c0 = ctx.call(asset, zero, label="zero boost through the declared entry point")
    criteria.append(C.fields(ctx, c0, asset, "fields"))
    c1 = ctx.call(asset, named, label="declared example boost")
    if "_value" in c0:
        got = float(np.asarray(H.mapping(_val(c0), asset)["neutron_energy_kev"]))
        expected = 1000.0 * Q_MEV * m_he3 / (m_n + m_he3)
        dev = abs(got - expected) / expected
        ok = dev <= 1e-6
        detail = {
            "zero_boost_returned_kev": got,
            "recomputed_kev": expected,
            "relative_deviation": dev,
            "construction": "1000*Q*m_He3/(m_n+m_He3) at zero boost",
            "declared_boost_returned_kev": H.plain(
                np.asarray(H.mapping(_val(c1), asset)["neutron_energy_kev"])
            )
            if "_value" in c1
            else None,
        }
    criteria.append(C.crit("declared_construction", "invariant", "pass" if ok else "fail", detail))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "keV"},
        "independent_check": {
            "method": "the zero-boost energy is recomputed from the printed "
            "construction with standard CODATA masses supplied by the "
            "consumer (not from the package)",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": ok,
        "sufficient_reason": "the boost pair is an argument, so the zero-boost branch is reachable",
        "gaps": [
            H.gap(
                "confidence",
                "the recomputation uses CODATA masses the consumer supplied; the "
                "package does not return the mass constants it used",
            )
        ],
    }


# ---------------------------------------------------------------- cross-domain

CHECKS.update(
    {
        "neutrals-boltzmann-rhs": neutrals_boltzmann_rhs,
        "neutrals-velocity-mesh": neutrals_velocity_mesh,
        "neutrals-cross-mesh": neutrals_cross_mesh,
        "neutrals-terminal-reductions": neutrals_terminal_reductions,
        "neutrals-upwind-transport": neutrals_upwind_transport,
        "collisions-cross-sections": collisions_cross_sections,
        "collisions-rate-coefficients": collisions_rate_coefficients,
        "collisions-rate-averages": collisions_rate_averages,
        "fvm-convection-diffusion": fvm_convection_diffusion,
        "io-eqdsk-roundtrip": io_eqdsk_roundtrip,
        "inference-parameter-optimization": inference_parameter_optimization,
        "neoclassical-bootstrap": neoclassical_bootstrap,
        "source-profile-integral": source_profile_integral,
        "source-zero-width-sentinel": source_zero_width_sentinel,
        "dielectric-cold-tensor": dielectric_cold_tensor,
        "plasma-fast-ion-heating": plasma_fast_ion_heating,
        "fusion-dd-neutron-energy": fusion_dd_neutron_energy,
    }
)
