"""Kinetic-domain checks (8 nominal tasks; failure/inapplicable are handled generically)."""

from __future__ import annotations

import numpy as np

import harness as H
from . import _common as C

CHECKS: dict = {}

RESP = "scirel.kinetic.dielectric-response"
DIAG = "scirel.kinetic.dielectric-diagnostics"


def _get(value, key, default=None):
    if hasattr(value, "get"):
        return value.get(key, default)
    return default


def dielectric_finite_harmonic(ctx: H.Ctx, task: dict) -> dict:
    base = ctx.pick(RESP, method="harmonic")
    c1 = ctx.call(RESP, base, label="finite-harmonic tensor at the contract example point")
    scaled = H.scaled(base, {"B0": 2.0 ** -52, "omega": 2.0 ** -52, "kx": 2.0 ** -52,
                             "kz": 2.0 ** -52, "ns0": 2.0 ** -104})
    c2 = ctx.call(RESP, scaled, label="same point, B0/omega/kx/kz x2^-52 and ns0 x2^-104")
    c3 = ctx.call(DIAG, ctx.named(DIAG), label="raw diagnostic entry at the same declared point")

    criteria = [C.fields(ctx, c1, RESP, "fields"),
                C.params(ctx, RESP, ["method", "harmonics"], "params")]
    if "_value" in c1 and "_value" in c2:
        v1, v2 = c1["_value"], c2["_value"]
        devs = {k: H.rel_dev(_get(v1, k), _get(v2, k)) for k in ("K", "D", "determinant")}
        worst = max(devs.values())
        tol = 2e-12
        criteria.append(C.crit("silike", "invariant", "pass" if worst <= tol else "fail", {
            "per_output_relative_deviation": devs,
            "declared_budget": tol,
        }))
        criteria.append(C.crit("budget", "tolerance", "pass" if worst <= tol else "fail", {
            "quantity": "@declared_outputs (K, D, determinant)",
            "unit": "dimensionless",
            "observed_relative_deviation": worst,
            "declared_tolerance": {"rel": tol, "abs": 0.0},
            "basis": "two binary64 evaluations at inputs related by an exact power of two",
        }))
        dev = worst
    else:
        criteria.append(C.not_run("silike", "invariant", "one of the two calls raised"))
        criteria.append(C.not_run("budget", "tolerance", "one of the two calls raised"))
        dev = None

    harmonics_requested = base.get("harmonics")
    answer = {
        "value": {
            "determinant": H.plain(_get(c1.get("_value"), "determinant")) if "_value" in c1 else None,
            "harmonics_argument": harmonics_requested,
            "response_diagnostics": H.plain(_get(c1.get("_value"), "diagnostics")) if "_value" in c1 else None,
            "raw_diagnostic_diagnostics": H.plain(_get(c3.get("_value"), "diagnostics")) if "_value" in c3 else None,
        },
        "unit": "dimensionless tensor entries; determinant dimensionless",
        "statement": "finite-harmonic tensor at the contract example point and the separate raw "
                     "diagnostic at the same point",
    }
    sufficient = all(c["status"] == "pass" for c in criteria)
    return {
        "criteria": criteria,
        "answer": answer,
        "independent_check": {
            "method": "same-method power-of-two scale invariance recomputed by the consumer: "
                      "K, D and determinant must be invariant componentwise",
            "observed": {"relative_deviation": dev},
            "verdict": "pass" if dev is not None and dev <= 2e-12 else "fail",
        },
        "package_sufficient": sufficient,
        "sufficient_reason": "both entries are discoverable, callable and their declared outputs "
                             "are returned with the harmonics actually requested",
        "gaps": [H.gap("experience",
                       "the entry does not return the harmonic cutoff it used; the record only "
                       "reports the requested value, so the default cutoff is not observable")
                 if harmonics_requested is None else H.gap(
                       "experience", "the harmonic cutoff is only echoed as the argument")],
    }


def faddeeva_family(ctx: H.Ctx, task: dict) -> dict:
    pdp = "scirel.kinetic.plasma-dispersion-function"
    fsf = "scirel.kinetic.fluid-special-functions"
    variants = ctx.discover(pdp)["variants"]
    calls = []
    for v in variants:
        calls.append(ctx.call(pdp, dict(v["named"]),
                              label=f"backend {v['named'].get('method')!r} as declared in the example"))
    c_fsf = ctx.call(fsf, ctx.named(fsf), label="fluid special function at the example point")

    criteria = [C.fields(ctx, calls[0], pdp, "fields")]
    worst = 0.0
    identity_ok = True
    per_call = []
    for call, v in zip(calls, variants):
        if "_value" not in call:
            identity_ok = False
            continue
        val = call["_value"]
        w = np.asarray(val["w"], dtype=complex)
        Z = np.asarray(val["Z"], dtype=complex)
        dev = float(np.max(np.abs(Z - 1j * np.sqrt(np.pi) * w) /
                           np.maximum(np.abs(Z), 1e-300))) if Z.size else 0.0
        worst = max(worst, dev)
        per_call.append({"method": v["named"].get("method"),
                         "order": v["named"].get("order"),
                         "Z_over_i_sqrt_pi_w_deviation": dev})
    criteria.append(C.crit("methodrecord", "invariant",
                           "pass" if identity_ok and worst <= 1e-12 else "fail", {
        "requested_backends": [v["named"].get("method") for v in variants],
        "requested_orders": [v["named"].get("order") for v in variants],
        "note": "the returned record has no method field; the requested method and order are "
                "carried by the arguments trace and the definition Z=i*sqrt(pi)*w is checked",
        "per_call": per_call,
    }))
    sufficient = worst <= 1e-12 and identity_ok
    return {
        "criteria": criteria,
        "answer": {
            "value": {str(v["named"].get("method")): H.plain(c.get("_value"))
                      for c, v in zip(calls, variants)},
            "unit": "dimensionless w and Z",
            "statement": "all four declared backends evaluated at the declared points",
        },
        "independent_check": {
            "method": "the contract definition Z(z)=i*sqrt(pi)*w(z) is recomputed from each "
                      "returned pair",
            "observed": {"max_relative_deviation": worst},
            "verdict": "pass" if worst <= 1e-12 else "fail",
        },
        "package_sufficient": sufficient,
        "sufficient_reason": "every declared backend is callable and satisfies the declared identity",
        "gaps": [H.gap("experience",
                       "a call that requests an order does not return that order, so a consumer "
                       "cannot read back which order produced the value from the record alone")],
    }


def generalized_dispersion(ctx: H.Ctx, task: dict) -> dict:
    gd = "scirel.kinetic.generalized-dispersion"
    scan = "scirel.kinetic.generalized-root-scans"
    c1 = ctx.call(gd, ctx.named(gd), label="generalized Z and Zp at the example point")
    c2 = ctx.call(scan, ctx.named(scan), label="declared beam root scan")

    criteria = [C.fields(ctx, c1, gd, "fields")]
    if "_value" in c2:
        v = c2["_value"]
        lens = {k: int(np.size(v[k])) for k in
                ("k", "omega", "dielectric_residual", "evaluations") if k in v}
        roots = lens.get("omega")
        counts_ok = (len({lens.get("k"), lens.get("omega"),
                          lens.get("dielectric_residual"), lens.get("evaluations")}) == 1)
        residuals = np.asarray(v["dielectric_residual"]) if "dielectric_residual" in v else np.array([])
        finite = bool(np.all(np.isfinite(residuals))) if residuals.size else False
        requested = np.size(ctx.named(scan).get("k_values"))
        criteria.append(C.crit("counts", "invariant",
                               "pass" if counts_ok and finite and roots == requested else "fail", {
            "lengths": lens,
            "roots_returned": roots,
            "grid_points_requested": int(requested),
            "residuals_finite": finite,
            "max_residual": float(np.max(np.abs(residuals))) if residuals.size else None,
        }))
        answer = {"value": {"roots": H.plain(v["omega"]),
                            "dielectric_residual": H.plain(v["dielectric_residual"]),
                            "counts": lens},
                  "unit": "dimensionless frequency and residual"}
        sufficient = counts_ok and finite and roots == requested
        dev = float(np.max(np.abs(residuals))) if residuals.size else None
    else:
        criteria.append(C.not_run("counts", "invariant", "the scan raised"))
        answer = {"value": None, "unit": "dimensionless"}
        sufficient = False
        dev = None
    return {
        "criteria": criteria,
        "answer": answer,
        "independent_check": {
            "method": "lengths of the returned k, omega, residual and evaluation arrays are "
                      "compared with the requested grid, and every residual is checked finite",
            "observed": {"max_abs_residual": dev},
            "verdict": "pass" if sufficient else "fail",
        },
        "package_sufficient": sufficient,
        "sufficient_reason": "the scan returns one entry per declared grid point and the "
                             "consumer can check that cardinality from the returned arrays",
        "gaps": [],
    }


def fluid_two_path(ctx: H.Ctx, task: dict) -> dict:
    from scirel.kinetic.fluid_spectrum import derive_fluid_case

    resp = "scirel.kinetic.fluid-dispersion-response"
    mat = "scirel.kinetic.fluid-dispersion-matrix"
    bonk = "scirel.kinetic.fluid-bonk-search"

    s = derive_fluid_case("bonk", 2)
    c1 = ctx.call(resp, {"kx": 0, "state": s, "method": "fD"},
                  label="fluid response fD through the scalar entry")

    named = ctx.named(mat)
    c2 = ctx.call(mat, named, label="matrix form at the declared example scales")

    criteria = [C.fields(ctx, c2, mat, "fields")]
    ok = False
    detail = {}
    if "_value" in c2:
        v = c2["_value"]
        M = np.asarray(v["M"])
        size = int(np.size(v["matrix_size"]))
        layout = list(v["state_layout"])
        raw = named["order_lengths"]
        order_lengths = np.asarray(list(raw.values()) if hasattr(raw, "values") else raw,
                                   dtype=float).ravel()
        expected = int(3 * 1 * order_lengths.sum() + 4)
        declared_layout = [f"vx_snl", "vy_snl", "vz_snl", "Ey", "Ez", "By", "Bz"]
        ok = (M.shape == (size, size) and size == expected and layout == declared_layout)
        detail = {"matrix_size_returned": size, "matrix_shape": list(M.shape),
                  "recomputed_size": expected, "order_lengths": order_lengths.tolist(),
                  "state_layout": layout, "declared_layout": declared_layout}
    criteria.append(C.crit("declared_layout", "invariant", "pass" if ok else "fail", detail))
    criteria.append(C.not_run(
        "budget", "tolerance",
        "the task's budget compares a determinant through two published entries, but the "
        "response entry returns a mixed payload whose determinant field the contract does not "
        "name; no field of the delivered record can be substituted without guessing",
        {"declared_tolerance": {"rel": 1e-12, "abs": 0.0}}))
    c3 = ctx.call(bonk, ctx.named(bonk), label="Bonk search from the contract example")
    criteria.append(C.fields(ctx, c3, bonk, "fields_bonk"))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "dimensionless size and layout names"},
        "independent_check": {
            "method": "matrix dimension recomputed as 3*S*sum(order_lengths)+4 from the declared "
                      "oscillation counts and compared with the returned square matrix",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": False,
        "sufficient_reason": "the layout criterion is verified, but the tolerance criterion's "
                             "two-path determinant cannot be evaluated from the delivered fields",
        "gaps": [H.gap("confidence",
                       "fluid-dispersion-response returns one 'result' field with mixed units; the "
                       "contract does not name the determinant, so the second path could not be "
                       "compared and the declared 1e-12 budget stays unevaluated")],
    }


def spectral_scan(ctx: H.Ctx, task: dict) -> dict:
    state = "scirel.kinetic.spectral-plasma-state"
    scan = "scirel.kinetic.spectral-dispersion-scan"
    temp = "scirel.kinetic.spectral-temporal-spectrum"
    c1 = ctx.call(state, ctx.named(state), label="declared plasma state")
    c2 = ctx.call(scan, ctx.named(scan), label="declared two-point k grid")
    criteria = [C.fields(ctx, c2, scan, "fields"), C.fields(ctx, c1, state, "fields_state")]
    same = None
    detail = {}
    if "_value" in c1 and "_value" in c2:
        s = c1["_value"]
        sv = c2["_value"].get("state")
        if hasattr(sv, "keys"):
            common = sorted(set(s.keys()) & set(sv.keys()))
            diffs = {}
            for k in common:
                try:
                    if not np.allclose(np.asarray(s[k]), np.asarray(sv[k]), rtol=0, atol=0):
                        diffs[k] = H.plain(sv[k])
                except (TypeError, ValueError):
                    if repr(s[k]) != repr(sv[k]):
                        diffs[k] = H.plain(sv[k])
            same = not diffs
            detail = {"compared_fields": len(common), "mismatched": diffs}
    criteria.append(C.crit("state_values", "invariant", "pass" if same else
                           ("fail" if same is False else "not-run"),
                           detail or {"why": "the scan record carries no state mapping"}))
    # temporal spectrum on the values the scan returned
    if "_value" in c2 and "M" in c2["_value"] and "A" in c2["_value"]:
        c3 = ctx.call(temp, {"M": c2["_value"]["M"], "A": c2["_value"]["A"], "vectors": True},
                      label="temporal spectrum on the scan's own M and A")
        criteria.append(C.fields(ctx, c3, temp, "fields_temporal"))
        sufficient = bool(same) and c3["status"] == "returned"
    else:
        sufficient = False
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "field-by-field comparison of the declared state",
                   "statement": "state at the declared point and the scan over the declared two-point k grid"},
        "independent_check": {
            "method": "the scan's state mapping is compared field by field with the separately "
                      "returned plasma state, and the temporal spectrum is evaluated on the "
                      "scan's own M and A",
            "observed": detail,
            "verdict": "pass" if same else "fail",
        },
        "package_sufficient": sufficient,
        "sufficient_reason": "the scan echoes the state and the matrices needed for the temporal entry",
        "gaps": [],
    }


def vp_initial_value(ctx: H.Ctx, task: dict) -> dict:
    init = "scirel.kinetic.vp-init"
    evolve = "scirel.kinetic.vp-evolve"
    step = "scirel.kinetic.vp-rk4-step"
    landau = "scirel.kinetic.vp-landau"
    c1 = ctx.call(init, ctx.named(init), label="declared initial state (nv=32, nt=5)")
    c2 = ctx.call(evolve, {"state": c1["_value"]}, label="evolve the reported state")
    c3 = ctx.call(landau, ctx.named(landau), label="declared Landau solve")
    criteria = [C.fields(ctx, c2, evolve, "fields"),
                C.fields(ctx, c3, landau, "fields_landau")]

    # one-step path: nt=1
    s1 = ctx.call(init, {**ctx.named(init), "nt": 1}, label="nt=1 initial state")
    e1 = ctx.call(evolve, {"state": s1["_value"]}, label="exactly one RK4 step through evolve")
    one_step = None
    detail = {}
    if "_value" in s1 and "_value" in e1:
        st = s1["_value"]
        try:
            f, E = H.resolve(step)[2](*(st[n] for n in ("df", "dE", "vv", "df0dv", "k", "dv", "dt")))
            got = e1["_value"]
            d_f = float(np.max(np.abs(np.asarray(f) - np.asarray(got["df"]))))
            d_E = float(np.max(np.abs(np.asarray(E) - np.asarray(got["dE"]))))
            one_step = d_f <= 1e-12 and d_E <= 1e-12
            detail = {"df_max_abs_diff": d_f, "dE_max_abs_diff": d_E,
                      "evolve_step_count": int(np.size(got.get("dEt", [])))}
        except Exception as exc:  # noqa: BLE001
            detail = {"why": f"the step entry could not be called on the declared state: {exc}"}
    criteria.append(C.crit("one_step", "invariant",
                           "pass" if one_step else ("fail" if one_step is False else "not-run"),
                           detail))

    diag = None
    diag_detail = {}
    if "_value" in c2:
        v = c2["_value"]
        declared_nt = int(np.size(ctx.named(init).get("nt")))
        diag_detail = {"declared_nt": declared_nt,
                       "returned_nt": H.plain(v.get("nt")),
                       "declared_dt": H.plain(ctx.named(init).get("dt")),
                       "returned_dt": H.plain(v.get("dt"))}
        diag = (diag_detail["returned_nt"] in (None, declared_nt))
    criteria.append(C.crit("declared_diagnostics", "invariant",
                           "pass" if diag else ("fail" if diag is False else "not-run"),
                           diag_detail))
    sufficient = bool(one_step) and bool(diag)
    return {
        "criteria": criteria,
        "answer": {"value": {"one_step": detail, "diagnostics": diag_detail},
                   "unit": "dimensionless state fields; dt in the declared time unit"},
        "independent_check": {
            "method": "one evolve step at nt=1 is compared with one direct call of the published "
                      "RK4 step entry on the same declared state",
            "observed": detail,
            "verdict": "pass" if one_step else "fail",
        },
        "package_sufficient": sufficient,
        "sufficient_reason": "the published step entry is callable on the returned state, so the "
                             "one-step path can be checked rather than taken on trust",
        "gaps": [],
    }


def multifluid_frequency(ctx: H.Ctx, task: dict) -> dict:
    deck = "scirel.kinetic.multifluid-deck"
    solve = "scirel.kinetic.multifluid-frequency-solve"
    scan = "scirel.kinetic.multifluid-scan"
    c1 = ctx.call(deck, ctx.named(deck), label="declared deck")
    c2 = ctx.call(solve, ctx.named(solve), label="single-point solve from the contract example")
    c3 = ctx.call(scan, ctx.named(scan), label="declared two-point scan")
    criteria = [C.fields(ctx, c3, scan, "fields")]
    ok, detail = False, {}
    if "_value" in c3:
        v = c3["_value"]
        k = np.asarray(v["k"]).ravel() if "k" in v else None
        theta = v.get("theta")
        if k is not None and theta is not None:
            th = np.asarray(theta).ravel()
            kx = np.asarray(v["kx"]).ravel()
            kz = np.asarray(v["kz"]).ravel()
            rebuilt_kx = k * np.sin(th)
            rebuilt_kz = k * np.cos(th)
            dev = max(float(np.max(np.abs(kx - rebuilt_kx))), float(np.max(np.abs(kz - rebuilt_kz))))
            ok = dev <= 1e-12 and np.size(v["w1"]) == k.size * 14
            detail = {"points": int(k.size), "theta": th.tolist(), "rebuilt_kx": rebuilt_kx.tolist(),
                      "rebuilt_kz": rebuilt_kz.tolist(), "max_abs_deviation": dev}
    criteria.append(C.crit("declared_grid", "invariant", "pass" if ok else "fail", detail))
    criteria.append(C.not_run(
        "budget", "tolerance",
        "the declared budget relates a non-iterative evaluation to the scanned one, but the "
        "delivered records of the two entries do not share a named field for the same quantity",
        {"declared_tolerance": {"rel": 1e-10, "abs": 0.0}}))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "k, kx, kz in m^-1; theta in rad; omega in rad/s"},
        "independent_check": {
            "method": "kx and kz are recomputed from the returned k and the declared theta and "
                      "compared with the returned components",
            "observed": detail,
            "verdict": "pass" if ok else "fail",
        },
        "package_sufficient": False,
        "sufficient_reason": "the grid relation is verified; the tolerance criterion's two paths "
                             "do not expose a common named field",
        "gaps": [H.gap("confidence",
                       "the scan and the single-point solve report different payload shapes, so the "
                       "declared 1e-10 agreement between them was not evaluated")],
    }


def rational_pole(ctx: H.Ctx, task: dict) -> dict:
    deck = "scirel.kinetic.rational-default-deck"
    poles = "scirel.kinetic.rational-z-poles"
    solve = "scirel.kinetic.rational-solve-matrix"
    grid = "scirel.kinetic.rational-jpole-grid-coordinates"

    c1 = ctx.call(deck, ctx.named(deck), label="declared default deck")
    c2 = ctx.call(poles, ctx.named(poles), label="declared 8-pole table")
    c3 = ctx.call(solve, ctx.named(solve), label="solve at the declared order 4")
    c4 = ctx.call(grid, ctx.named(grid), label="declared 101x101 pole grid")

    criteria = [C.fields(ctx, c3, solve, "fields")]
    declared = set(H.output_names(solve))
    detail, ok = {}, False
    if "_value" in c3:
        v = c3["_value"]
        got = set(v.keys())
        missing = sorted(declared - got)
        needed = ["N", "source_pole_order", "poles", "residues"]
        absent = [k for k in needed if k not in got]
        if absent:
            detail = {"declared_output_count": len(declared), "returned_field_count": len(got),
                      "missing_declared_fields": missing,
                      "absent_fields_the_criterion_needs": absent}
            status = "not-run"
        else:
            n = int(np.size(v["N"]))
            sp = int(np.size(v["source_pole_order"]))
            npoles, nres = len(v["poles"]), len(v["residues"])
            finite = C.finite(v["poles"])
            ok = (n == 4 and sp == 4 and npoles == nres and finite)
            status = "pass" if ok else "fail"
            detail = {"N": n, "source_pole_order": sp, "len(poles)": npoles,
                      "len(residues)": nres, "poles_finite": finite, "declared_order": 4}
    else:
        status = "not-run"
        detail = {"why": "the solve raised"}
    criteria.append(C.crit("declared_counts", "invariant", status, detail))

    gaps = []
    sufficient = status == "pass" and criteria[0]["status"] == "pass"
    if criteria[0]["status"] == "fail":
        gaps.append(H.gap(
            "blocking",
            f"{solve} returns {len(set(c3.get('_value', {}).keys())) if '_value' in c3 else 0} of "
            f"{len(declared)} declared outputs for the declared es1d model; the record is missing "
            f"{len(detail.get('missing_declared_fields', []))} declared fields, including the pole "
            "count fields the task's criterion asks the consumer to read back"))
    return {
        "criteria": criteria,
        "answer": {"value": detail, "unit": "counts and dimensionless frequencies"},
        "independent_check": {
            "method": "the declared order 4 is compared with the returned N, source_pole_order and "
                      "the pole/residue lengths",
            "observed": detail,
            "verdict": "pass" if ok else ("not-run" if status == "not-run" else "fail"),
        },
        "package_sufficient": sufficient,
        "sufficient_reason": ("order, pole count and residues are readable from the record"
                              if sufficient else
                              "the entry does not return the fields the criterion names, so the "
                              "declared counts cannot be checked by a consumer"),
        "gaps": gaps,
    }


CHECKS.update({
    "kinetic-dielectric-finite-harmonic": dielectric_finite_harmonic,
    "kinetic-faddeeva-family": faddeeva_family,
    "kinetic-generalized-dispersion": generalized_dispersion,
    "kinetic-fluid-two-path": fluid_two_path,
    "kinetic-spectral-scan": spectral_scan,
    "kinetic-vp-initial-value": vp_initial_value,
    "kinetic-multifluid-frequency": multifluid_frequency,
    "kinetic-rational-pole": rational_pole,
})
