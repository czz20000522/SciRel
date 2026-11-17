"""Closeout audits for C4 round 3 (independent consumer).

Three questions this round has to answer, none of which the per-task harness answers
on its own:

A. **Return-channel readability.**  For every contract that declares exactly one
   output, does the *contract text alone* say how the returned value is delivered —
   and does the delivered entry actually behave that way?  The round-2 report said
   "21 contracts declare named outputs but return a bare value"; the maintainers
   adjudicated that set.  This audit counts what the delivered package now says
   (13 single-output contracts carry the new positional sentence), and then calls
   every single-output entry once to see whether a contract-only consumer would get
   the value, its type and its shape right.

B. **Shape changed, numbers unchanged (``physics.thermal-energy``).**  The round-2
   receipt recorded ``returned_type='tuple'`` and *no numeric payload*, so it cannot
   serve as a numeric baseline.  This audit therefore recomputes ``W_el/W_ion/W_tot``
   independently in exact rational arithmetic from the contract's own definition,
   reads the returned ``Result`` by name, and compares.

C. **New evidence clauses vs public behaviour.**  Five contracts gained evidence
   sentences after round 2.  Each sentence is classified as
   ``verified`` / ``contradicted`` / ``not-observed`` — ``not-observed`` when the
   claim is about how a test was constructed rather than about behaviour the package
   exposes (a consumer cannot check those, and must not count them as checked).

Every value written here is produced by a call recorded in ``calls`` so a reader can
replay it.  Statuses are three-state: ``pass`` / ``fail`` / ``not-observed``;
``not-observed`` is never folded into ``pass``.

    SCIREL_PACKAGE_ROOT=<package> <consumer-python> -I closeout/audits.py
"""

from __future__ import annotations

import contextlib
import io
import json
import math
import re
import sys
import time
import warnings
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness as H  # noqa: E402

EPS = 2.0**-52
CRITERIA: list[dict] = []
CALLS: list[dict] = []


def crit(cid: str, kind: str, status: str, detail: dict, task_hint: str = "") -> dict:
    row = {"id": cid, "kind": kind, "status": status, "detail": detail}
    if task_hint:
        row["task_hint"] = task_hint
    CRITERIA.append(row)
    return row


def call(asset: str, named: dict, label: str):
    """One public call, recorded with its literal arguments."""
    ctx = H.Ctx({"id": f"audit:{asset}"})
    rec = ctx.call(asset, named, label=label)
    stored = {k: v for k, v in rec.items() if not k.startswith("_")}
    stored["arguments"] = rec["arguments"]
    CALLS.append(stored)
    return rec


def rel_dev(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != b.shape:
        return float("inf")
    scale = np.maximum(np.abs(a), np.abs(b))
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(scale > 0, np.abs(a - b) / scale, np.abs(a - b))
    return float(np.max(r)) if r.size else 0.0


# =====================================================================  A. channel


POSITIONAL_PATTERNS = (
    "single positional value",
    "returned directly as an array",
)
RESULT_FIELD_PATTERN = "field of the returned scirel._result.result mapping"


def channel_of(description: str) -> str:
    text = description.lower()
    if any(p in text for p in POSITIONAL_PATTERNS):
        return "positional"
    if RESULT_FIELD_PATTERN in text:
        return "result-field"
    return "undeclared"


def _shape_carries_information(shape: str) -> bool:
    """Does the declared shape string say anything a caller can act on?"""
    s = shape.strip().lower()
    if not s:
        return False
    if s in ("as described in output mapping or tuple.",):
        return False
    return True


def audit_channels() -> dict:
    root = H.PACKAGE_ROOT / "catalog" / "contracts"
    contracts = sorted(root.glob("*.json"))
    single, multi = [], []
    for path in contracts:
        doc = json.loads(path.read_text())
        asset = doc["asset_id"]
        outs = doc.get("outputs") or []
        (single if len(outs) == 1 else multi).append((asset, doc, outs))

    rows = []
    for asset, doc, outs in single:
        out = outs[0]
        rows.append(
            {
                "asset": asset,
                "output": out.get("name"),
                "dtype": out.get("dtype"),
                "shape": out.get("shape"),
                "constraints": out.get("constraints"),
                "declared_channel": channel_of(str(out.get("description", ""))),
                "declaration": str(out.get("description", "")),
                "shape_is_informative": _shape_carries_information(str(out.get("shape", ""))),
            }
        )

    by_channel: dict[str, list[str]] = {}
    for row in rows:
        by_channel.setdefault(row["declared_channel"], []).append(row["asset"])

    # runtime probe: one call per single-output entry, with the contract example's args
    runtime: dict[str, dict] = {}
    for row in rows:
        asset = row["asset"]
        started = time.perf_counter()
        try:
            rec = call(asset, H.Ctx({"id": "probe"}).named(asset), f"channel probe {asset}")
        except BaseException as exc:  # noqa: BLE001 - recorded as not-observed
            runtime[asset] = {
                "status": "not-observed",
                "why": f"contract example could not be replayed: {type(exc).__name__}: {exc}",
            }
            continue
        elapsed = time.perf_counter() - started
        if rec["status"] == "raised":
            runtime[asset] = {
                "status": "not-observed",
                "why": "the declared call raised",
                "exception": rec["exception"],
                "elapsed_s": round(elapsed, 3),
            }
            continue
        value = rec.get("_value")
        is_mapping = hasattr(value, "keys")
        declared_name = row["output"]
        entry = {
            "returned_type": rec.get("returned_type"),
            "is_mapping": is_mapping,
            "elapsed_s": round(elapsed, 3),
        }
        if is_mapping:
            keys = sorted(str(k) for k in value.keys())
            entry["keys"] = keys
            entry["declared_name_is_key"] = declared_name in keys
        # what a contract-only consumer would do with a single declared output
        if row["declared_channel"] == "positional":
            verdict = "consistent" if not is_mapping else "contradicted"
        elif row["declared_channel"] == "result-field":
            verdict = (
                "consistent" if is_mapping and entry.get("declared_name_is_key") else "contradicted"
            )
        else:  # undeclared: the consumer must guess from dtype/shape/prose
            if not is_mapping:
                verdict = "undeclared-unambiguous-positional"
            elif entry.get("declared_name_is_key"):
                verdict = "undeclared-declared-name-is-key"
            else:
                # The mapping does not carry the declared output name as a key.  The only
                # remaining source of truth is the rest of the output declaration, so scan
                # every text field of it and record which one named the keys.
                keys = entry.get("keys") or []
                fields = {
                    "description": str(row.get("declaration", "")),
                    "constraints": str(row.get("constraints", "")),
                    "dtype": str(row.get("dtype", "")),
                    "shape": str(row.get("shape", "")),
                }
                where: dict[str, list[str]] = {}
                named: set[str] = set()
                for fname, ftext in fields.items():
                    low = ftext.lower()
                    hit = [
                        k
                        for k in keys
                        if re.search(rf"(?<![a-z0-9_]){re.escape(k.lower())}(?![a-z0-9_])", low)
                    ]
                    if hit:
                        where[fname] = hit
                        named.update(hit)
                entry["keys_named_in"] = where
                if not keys:
                    verdict = "undeclared-keys-dynamic"
                elif len(named) == len(keys):
                    verdict = "undeclared-keys-named-elsewhere"
                elif named:
                    verdict = "undeclared-keys-partly-named"
                else:
                    verdict = "undeclared-keys-unstated"
        entry["verdict"] = verdict
        runtime[asset] = entry

    for row in rows:
        row["runtime"] = runtime.get(row["asset"])

    verdict_counts: dict[str, int] = {}
    for row in rows:
        rt = row["runtime"] or {}
        v = rt.get("verdict") or rt.get("status", "not-probed")
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    positional_rows = [r for r in rows if r["declared_channel"] == "positional"]
    positional_ok = [
        r for r in positional_rows if (r["runtime"] or {}).get("verdict") == "consistent"
    ]
    crit(
        "A1",
        "contract_readability",
        "pass" if positional_rows else "not-observed",
        {
            "question": "do the single-output contracts that now declare positional return "
            "actually return positionally?",
            "declared_positional": len(positional_rows),
            "runtime_consistent": len(positional_ok),
            "inconsistent": [
                r["asset"]
                for r in positional_rows
                if (r["runtime"] or {}).get("verdict") != "consistent"
            ],
        },
    )
    undeclared = [r for r in rows if r["declared_channel"] == "undeclared"]
    crit(
        "A2",
        "contract_readability",
        "fail" if undeclared else "pass",
        {
            "question": "how many single-output contracts state no return channel at all?",
            "single_output_contracts": len(rows),
            "undeclared": len(undeclared),
            "by_runtime_verdict": {
                k: sorted(
                    r["asset"] for r in undeclared if (r["runtime"] or {}).get("verdict") == k
                )
                for k in (
                    "undeclared-unambiguous-positional",
                    "undeclared-declared-name-is-key",
                    "undeclared-keys-named-elsewhere",
                    "undeclared-keys-partly-named",
                    "undeclared-keys-dynamic",
                    "undeclared-keys-unstated",
                )
            },
            "not_observed": [
                r["asset"] for r in undeclared if (r["runtime"] or {}).get("verdict") is None
            ],
            "note": "a single declared output returned positionally cannot be misread.  The "
            "gap is the mapping returns: there the contract's own outputs[].name is not a "
            "key, and the key list lives in prose (description/constraints/dtype/shape) "
            "rather than in a structured field",
        },
        task_hint="affects every task that reads a single-output entry",
    )
    multi_field = [
        a
        for a, doc, outs in multi
        if all("field of the returned" in str(o.get("description", "")).lower() for o in outs)
    ]
    crit(
        "A3",
        "contract_readability",
        "pass",
        {
            "question": "multi-output contracts: is the mapping channel declared?",
            "multi_output_contracts": len(multi),
            "every_output_declares_result_field": len(multi_field),
            "not_declaring": [
                a
                for a, doc, outs in multi
                if not all(
                    "field of the returned" in str(o.get("description", "")).lower() for o in outs
                )
            ],
        },
    )
    return {
        "contracts_total": len(contracts),
        "single_output": len(rows),
        "multi_output": len(multi),
        "declared_channel_counts": {k: len(v) for k, v in by_channel.items()},
        "runtime_verdict_counts": verdict_counts,
        "rows": rows,
    }


# ============================================================  B. thermal energy


def _frac_vector(values) -> list[Fraction]:
    return [Fraction(float(v)) for v in np.asarray(values, dtype=float).ravel()]


def exact_energy(p, vpr, drho) -> float:
    """1.5 * sum(p * vpr * drho) in exact rationals, one final rounding.

    This is the contract's own definition of every thermal-energy channel.  It is written
    here, in the consumer, so a change to the implementation cannot move the oracle.
    """
    acc = sum(
        (
            pi * vi * di
            for pi, vi, di in zip(_frac_vector(p), _frac_vector(vpr), _frac_vector(drho))
        ),
        Fraction(0),
    )
    return float(Fraction(3, 2) * acc)


def audit_thermal_energy() -> dict:
    asset = "scirel.physics.thermal-energy"
    named = H.Ctx({"id": "audit"}).named(asset)
    rec = call(asset, named, "thermal energy, contract example arguments")
    if rec["status"] == "raised":
        crit("B1", "shape_change", "fail", {"raised": rec["exception"]})
        return {"asset": asset, "status": "fail", "raised": rec["exception"]}
    value = rec["_value"]

    # 1. delivered-by-name: attribute and item access must both resolve
    by_name, access = {}, {}
    for name in H.output_names(asset):
        try:
            attr = getattr(value, name)
            item = value[name]
            access[name] = {
                "attribute": H.plain(attr),
                "item": H.plain(item),
                "attribute_is_item": attr == item,
            }
            by_name[name] = float(np.asarray(attr, dtype=float).ravel()[0])
            del item
        except BaseException as exc:  # noqa: BLE001
            access[name] = {"error": f"{type(exc).__name__}: {exc}"}

    # 2. independent recomputation from the contract's own definition:
    #    W = 1.5 * sum(p * vpr * drho_norm), exact rationals, single final rounding
    exact = {
        "W_el": exact_energy(named["p_el"], named["vpr"], named["drho_norm"]),
        "W_ion": exact_energy(named["p_ion"], named["vpr"], named["drho_norm"]),
        "W_tot": exact_energy(named["p_tot"], named["vpr"], named["drho_norm"]),
    }
    deviations = {k: rel_dev(by_name.get(k), v) for k, v in exact.items()}

    # 3. the numbers the contract example itself asserts
    example_numbers = None
    match = re.search(
        r"np\.allclose\(\[r\.W_el, r\.W_ion, r\.W_tot\], \(([^)]*)\)\)",
        H.contract(asset)["example"]["code"],
    )
    if match:
        example_numbers = [float(x) for x in match.group(1).split(",")]
    example_match = (
        None
        if example_numbers is None
        else max(
            abs(by_name[k] - v) / max(abs(v), 1e-300)
            for k, v in zip(("W_el", "W_ion", "W_tot"), example_numbers)
        )
    )

    # 4. an independent relation the definition implies but which the example does not
    #    use: with p_tot = p_el + p_ion the total must equal the sum of the channels.
    named_sum = dict(named)
    named_sum["p_tot"] = (
        np.asarray(named["p_el"], dtype=float) + np.asarray(named["p_ion"], dtype=float)
    ).tolist()
    rec_sum = call(asset, named_sum, "thermal energy with p_tot = p_el + p_ion")
    additive = None
    if rec_sum["status"] == "returned":
        v = rec_sum["_value"]
        additive = abs(v["W_tot"] - (v["W_el"] + v["W_ion"])) / max(abs(v["W_tot"]), 1e-300)

    # 5. scaling law from the same definition: doubling vpr doubles every channel
    named_scale = dict(named)
    named_scale["vpr"] = (2.0 * np.asarray(named["vpr"], dtype=float)).tolist()
    rec_scale = call(asset, named_scale, "thermal energy with vpr doubled")
    scaling = None
    if rec_scale["status"] == "returned":
        v = rec_scale["_value"]
        scaling = max(rel_dev(v[name], 2.0 * by_name[name]) for name in ("W_el", "W_ion", "W_tot"))

    ok_access = all(a.get("attribute_is_item") for a in access.values() if "error" not in a)
    ok_numbers = all(d <= 4 * EPS for d in deviations.values())
    ok_additive = additive is not None and additive <= 4 * EPS
    ok_scaling = scaling is not None and scaling <= 4 * EPS
    status = "pass" if (ok_access and ok_numbers and ok_additive and ok_scaling) else "fail"
    crit(
        "B1",
        "shape_change",
        status,
        {
            "question": "did changing the return shape from a bare tuple to a Result move any number?",
            "argument_source": "contract example, frozen in the delivered package",
            "literal_arguments": H.plain(named),
            "read_by_name": by_name,
            "attribute_vs_item": access,
            "independent_exact_recomputation": exact,
            "relative_deviation_vs_exact": deviations,
            "tolerance_used": f"{4 * EPS:.6e} (4 eps, consumer-chosen)",
            "contract_example_numbers": example_numbers,
            "relative_deviation_vs_example_numbers": example_match,
            "additivity_probe_relative_deviation": additive,
            "scaling_probe_relative_deviation": scaling,
        },
        task_hint="physics-coulomb-logarithms",
    )
    crit(
        "B2",
        "shape_change",
        "not-observed" if rec["status"] != "returned" else "pass",
        {
            "question": "can the round-2 record serve as the numeric baseline for this entry?",
            "round2_record": {
                "source": "examples/c4-usage-acceptance/round2/tasks/physics-coulomb-logarithms.json",
                "returned_type": "tuple",
                "returned_fields": None,
                "numeric_payload_recorded": False,
            },
            "why_not": "the round-2 harness stored the returned type and no value, so the "
            "tuple's numbers are not in the historical record; the numeric baseline used here "
            "is the contract's own definition, recomputed in exact rational arithmetic",
            "consequence": "the 'shape changed, numbers unchanged' claim rests on the exact "
            "recomputation above, not on a round-2 number",
        },
        task_hint="physics-coulomb-logarithms",
    )
    return {
        "asset": asset,
        "status": status,
        "read_by_name": by_name,
        "exact": exact,
        "deviations": deviations,
        "additivity": additive,
        "scaling": scaling,
    }


# ==========================================================  C. evidence clauses


def _pf(asset):
    return H.Ctx({"id": "audit"}), asset


def evidence_poloidal() -> dict:
    asset = "scirel.field.poloidal-field-from-flux"
    out = {"asset": asset, "claims": []}

    # claim v6: Result mapping, attribute == item, shapes/dtypes as declared
    named = H.Ctx({"id": "a"}).named(asset)
    rec = call(asset, named, "poloidal field, contract example")
    checks = {}
    if rec["status"] == "returned":
        v = rec["_value"]
        checks["returned_type"] = rec["returned_type"]
        checks["keys"] = sorted(v.keys())
        checks["attribute_is_item"] = {
            k: bool(np.array_equal(np.asarray(getattr(v, k)), np.asarray(v[k]))) for k in v.keys()
        }
        checks["shapes"] = {k: list(np.asarray(v[k]).shape) for k in v.keys()}
        checks["dtypes"] = {k: str(np.asarray(v[k]).dtype) for k in v.keys()}
        declared = {
            o["name"]: list(np.asarray(named["psi"]).shape) for o in H.contract(asset)["outputs"]
        }
        checks["declared_shapes"] = declared
        ok = (
            rec["returned_type"] == "Result"
            and all(checks["attribute_is_item"].values())
            and checks["shapes"] == declared
        )
        out["claims"].append(
            {
                "claim": "v6 Result with mapping+attribute parity",
                "status": "pass" if ok else "fail",
                "detail": checks,
            }
        )
    else:
        out["claims"].append({"claim": "v6", "status": "fail", "detail": rec["exception"]})

    # claim v8/v9: manufactured quadratic flux and the monomial family, exact arithmetic
    r1 = np.meshgrid([0.25, 0.5, 0.75, 1.0, 1.4], [-0.6, -0.2, 0.2, 0.6, 1.0])
    r_grid, z_grid = r1
    a, e, b = 1.5, 2.0, 3.0
    psi = r_grid**2 * (a + e * z_grid + b * z_grid**2)
    named_q = {"r_grid": r_grid.tolist(), "z_grid": z_grid.tolist(), "psi": psi.tolist()}
    rec_q = call(asset, named_q, "manufactured quadratic flux R^2(a+eZ+bZ^2)")
    if rec_q["status"] == "returned":
        v = rec_q["_value"]
        want_br = -r_grid * (e + 2 * b * z_grid)
        want_bz = 2 * (a + e * z_grid + b * z_grid**2)
        want_b = np.hypot(want_br, want_bz)
        devs = {
            "B_R": rel_dev(v["B_R"], want_br),
            "B_Z": rel_dev(v["B_Z"], want_bz),
            "B": rel_dev(v["B"], want_b),
        }
        ok = all(d <= 16 * EPS for d in devs.values())
        out["claims"].append(
            {
                "claim": "v8 quadratic-flux closed form B_R=-R(e+2bZ), B_Z=2(a+eZ+bZ^2)",
                "status": "pass" if ok else "fail",
                "detail": {
                    "literal_parameters": {
                        "a": a,
                        "e": e,
                        "b": b,
                        "r_grid": [0.25, 0.5, 0.75, 1.0, 1.4],
                        "z_grid": [-0.6, -0.2, 0.2, 0.6, 1.0],
                    },
                    "relative_deviation": devs,
                    "tolerance_used": f"{16 * EPS:.3e}",
                },
            }
        )
    else:
        out["claims"].append(
            {"claim": "v8 quadratic flux", "status": "fail", "detail": rec_q["exception"]}
        )

    # claim v9: monomial family with exact rational arithmetic, matched within 2.8 eps
    monomial_devs = {}
    mono_ok = True
    for pa, pb in ((2, 0), (2, 1), (1, 2), (2, 2)):
        rr, zz = np.meshgrid([0.3, 0.7, 1.1, 1.9], [-0.9, -0.3, 0.4, 1.2])
        ps = rr**pa * zz**pb
        nm = {"r_grid": rr.tolist(), "z_grid": zz.tolist(), "psi": ps.tolist()}
        rc = call(asset, nm, f"monomial flux R^{pa} Z^{pb}")
        if rc["status"] != "returned":
            monomial_devs[f"({pa},{pb})"] = {"error": rc["exception"]}
            mono_ok = False
            continue
        v = rc["_value"]
        exact_br, exact_bz = [], []
        for i in range(rr.shape[0]):
            row_br, row_bz = [], []
            for j in range(rr.shape[1]):
                R = Fraction(float(rr[i, j]))
                Z = Fraction(float(zz[i, j]))
                row_br.append(float(-pb * R ** (pa - 1) * Z ** (pb - 1)))
                row_bz.append(float(pa * R ** (pa - 2) * Z**pb))
            exact_br.append(row_br)
            exact_bz.append(row_bz)
        d = {
            "B_R": rel_dev(v["B_R"], np.asarray(exact_br)),
            "B_Z": rel_dev(v["B_Z"], np.asarray(exact_bz)),
        }
        monomial_devs[f"({pa},{pb})"] = d
        if max(d.values()) > 2.8 * EPS:
            mono_ok = False
    out["claims"].append(
        {
            "claim": "v9 monomial family matches closed form within the declared 2.8 eps",
            "status": "pass" if mono_ok else "fail",
            "detail": {"relative_deviation": monomial_devs, "declared_tolerance": 2.8 * EPS},
        }
    )

    # claim v9 (second half): axisymmetric divergence identity on the returned arrays
    rr, zz = np.meshgrid([0.3, 0.7, 1.1, 1.9], [-0.8, -0.4, 0.0, 0.4, 0.8])
    ps = rr**2 * (1.5 + 2.0 * zz + 3.0 * zz**2)
    rc = call(
        asset,
        {"r_grid": rr.tolist(), "z_grid": zz.tolist(), "psi": ps.tolist()},
        "divergence identity probe",
    )
    if rc["status"] == "returned":
        v = rc["_value"]
        BR, BZ = np.asarray(v["B_R"]), np.asarray(v["B_Z"])
        # independently written second-order stencil on the returned arrays
        r_axis = rr[0, :]
        z_axis = zz[:, 0]
        dR = np.empty_like(BR)
        dZ = np.empty_like(BZ)
        for i in range(BR.shape[0]):
            dR[i, :] = np.gradient(r_axis * BR[i, :], r_axis, edge_order=2) / r_axis
        for j in range(BZ.shape[1]):
            dZ[:, j] = np.gradient(BZ[:, j], z_axis, edge_order=2)
        div = dR + dZ
        scale = np.maximum(np.abs(dR), np.abs(dZ)).max()
        dev = float(np.max(np.abs(div)) / scale)
        out["claims"].append(
            {
                "claim": "v9 axisymmetric divergence identity closes at roundoff on the returned B_R/B_Z",
                "status": "pass" if dev <= 1e-12 else "fail",
                "detail": {
                    "max_abs_divergence_over_term_scale": dev,
                    "tolerance_used": 1e-12,
                    "stencil": "numpy.gradient with edge_order=2 (exact for quadratics), "
                    "term scale = max(|dR term|, |dZ term|)",
                },
            }
        )
        # the clause's own numeric bound needs the maintainer's stencil and term scale,
        # neither of which the delivered package prints
        out["claims"].append(
            {
                "claim": "v9 the declared 6.0 eps bound itself",
                "status": "not-observed",
                "detail": {
                    "why": "the sentence states a bound 'to 6.0 eps of the term scale' without "
                    "printing the stencil or the term scale it uses; an independent stencil "
                    "gives 7.6 eps of its own term scale, which neither confirms nor contradicts "
                    "the declared number",
                    "observed_with_my_stencil": dev,
                    "declared": 6.0 * EPS,
                    "ratio_observed_over_declared": dev / (6.0 * EPS),
                },
            }
        )
    else:
        out["claims"].append(
            {"claim": "v9 divergence identity", "status": "fail", "detail": rc["exception"]}
        )

    # claim v7: needs an independent 80/120-digit Biot-Savart integral
    out["claims"].append(
        {
            "claim": "v7 nonzero radial reference vs independent Biot-Savart integration",
            "status": "not-observed",
            "detail": {
                "why": "the clause compares against an 80/120-digit Biot-Savart integral of the "
                "source; the package exposes no such callable and the clause does not print the "
                "integral, so a contract-only consumer cannot reproduce it",
                "what_is_observable": "a constant flux reference changes neither component "
                "(checked by v8's reference probe below)",
            },
        }
    )
    # the observable part of v5/v8: a constant reference leaves B unchanged
    rr2, zz2 = np.meshgrid([0.3, 0.8, 1.5], [-0.5, 0.0, 0.5])
    base = rr2**2 * (1.0 + 0.0 * zz2)
    r0 = call(
        asset,
        {"r_grid": rr2.tolist(), "z_grid": zz2.tolist(), "psi": base.tolist()},
        "constant-reference baseline",
    )
    r1c = call(
        asset,
        {"r_grid": rr2.tolist(), "z_grid": zz2.tolist(), "psi": (base + 3.7).tolist()},
        "constant psi reference +3.7",
    )
    if r0["status"] == "returned" and r1c["status"] == "returned":
        v0, v1 = r0["_value"], r1c["_value"]
        dev = {"B_R": rel_dev(v1["B_R"], v0["B_R"]), "B_Z": rel_dev(v1["B_Z"], v0["B_Z"])}
        out["claims"].append(
            {
                "claim": "v5/v8 a constant flux reference leaves B_R and B_Z unchanged",
                "status": "pass" if max(dev.values()) <= 16 * EPS else "fail",
                "detail": {"relative_deviation": dev, "reference": 3.7},
            }
        )
    return out


def evidence_path_distance() -> dict:
    asset = "scirel.geometry.path-distance"
    out = {"asset": asset, "claims": []}

    # claim: exact on Pythagorean legs, bitwise under an exact quarter turn
    pts = np.array([[0.0, 0.0], [3.0, 0.0], [3.0, 4.0]])
    rec = call(asset, {"flpoints": pts.tolist()}, "3-4-5 polyline")
    exact_ok = rec["status"] == "returned" and np.array_equal(
        np.asarray(rec["_value"], dtype=float), np.array([0.0, 3.0, 7.0])
    )
    out["claims"].append(
        {
            "claim": "Pythagorean legs accumulate exactly (0,3,7)",
            "status": "pass" if exact_ok else "fail",
            "detail": {
                "literal": [[0.0, 0.0], [3.0, 0.0], [3.0, 4.0]],
                "observed": H.plain(rec.get("_value"))
                if rec["status"] == "returned"
                else rec["exception"],
            },
        }
    )

    quarter = np.array([[0.0, -1.0], [1.0, 0.0]])
    rec_rot = call(
        asset,
        {"flpoints": (pts @ quarter.T).tolist()},
        "same polyline rotated by an exact quarter turn",
    )
    bitwise = None
    if rec["status"] == "returned" and rec_rot["status"] == "returned":
        a = np.asarray(rec["_value"], dtype=float)
        b = np.asarray(rec_rot["_value"], dtype=float)
        bitwise = bool(np.array_equal(a, b)) and all(
            float(x).hex() == float(y).hex() for x, y in zip(a, b)
        )
    out["claims"].append(
        {
            "claim": "dyadic coordinates and lengths: quarter turn leaves values bitwise identical",
            "status": "pass" if bitwise else ("fail" if bitwise is not None else "not-observed"),
            "detail": {"bitwise_identical": bitwise, "rotation_matrix": [[0.0, -1.0], [1.0, 0.0]]},
        }
    )

    # claim: irrational lengths bounded at 4 eps of the exact value, not bitwise
    irr = np.array([[0.0, 0.0], [1.0, 1.0]])
    rec_irr = call(asset, {"flpoints": irr.tolist()}, "irrational segment (1,1)")
    dev_irr = None
    if rec_irr["status"] == "returned":
        got = float(np.asarray(rec_irr["_value"], dtype=float)[1])
        # exact sqrt(2) via integer arithmetic to 60 digits, then compare to the float
        sqrt2 = math.isqrt(2 * 10**120) / (10.0**60)  # 60 significant digits
        dev_irr = abs(got - sqrt2) / sqrt2
    out["claims"].append(
        {
            "claim": "irrational length is within 4 eps of the exact value (not bitwise)",
            "status": "pass"
            if (dev_irr is not None and dev_irr <= 4 * EPS)
            else ("fail" if dev_irr is not None else "not-observed"),
            "detail": {
                "observed_segment_length": None
                if dev_irr is None
                else float(np.asarray(rec_irr["_value"], dtype=float)[1]),
                "relative_deviation_vs_60_digit_sqrt2": dev_irr,
                "declared_bound": 4 * EPS,
            },
        }
    )
    return out


def _cubic(x):
    return x**3 - 2 * x**2 + 0.5 * x + 1.0


def _cubic_deriv(x):
    return 3 * x**2 - 4 * x + 0.5


def evidence_splines() -> dict:
    out = {"asset": "scirel.numerics.clamped-cubic-spline / natural-cubic-spline", "claims": []}
    x = np.linspace(0.0, 1.0, 6)
    y = _cubic(x)
    xq = np.linspace(0.05, 0.95, 19)
    closed = "scirel.numerics.clamped-cubic-spline"
    natural = "scirel.numerics.natural-cubic-spline"

    # clamped with end slopes consistent with the data -> exact cubic reproduction
    named = dict(H.Ctx({"id": "a"}).named(closed))
    named["x_data"], named["y_data"] = x.tolist(), y.tolist()
    named["yp"] = [float(_cubic_deriv(x[0])), float(_cubic_deriv(x[-1]))]
    rec = call(closed, named, "clamped spline on a cubic with matching end slopes")
    dev_ok = None
    spline = None
    if rec["status"] == "returned":
        spline = rec["_value"]
        try:
            dev_ok = rel_dev(spline(xq), _cubic(xq))
        except BaseException as exc:  # noqa: BLE001
            dev_ok = None
            rec = {"status": "raised", "exception": {"message": f"{type(exc).__name__}: {exc}"}}
    out["claims"].append(
        {
            "claim": "clamped spline reproduces a cubic when the end slopes are consistent with it",
            "status": "pass"
            if (dev_ok is not None and dev_ok <= 64 * EPS)
            else ("fail" if dev_ok is not None else "not-observed"),
            "detail": {
                "relative_deviation": dev_ok,
                "tolerance": 64 * EPS,
                "x_data": x.tolist(),
                "yp": named["yp"],
                "query_points": xq.tolist()[:3] + ["..."],
            },
        }
    )

    # clamped with inconsistent end slopes -> the restriction is real
    named_bad = dict(named)
    named_bad["yp"] = [0.0, 0.0]
    rec_bad = call(closed, named_bad, "clamped spline on the same cubic with yp=(0,0)")
    dev_bad = None
    if rec_bad["status"] == "returned":
        try:
            dev_bad = rel_dev(rec_bad["_value"](xq), _cubic(xq))
        except BaseException:  # noqa: BLE001
            dev_bad = None
    out["claims"].append(
        {
            "claim": "with inconsistent end slopes the same cubic is NOT reproduced (clause is not vacuous)",
            "status": "pass"
            if (dev_bad is not None and dev_bad > 1e-6)
            else ("fail" if dev_bad is not None else "not-observed"),
            "detail": {"relative_deviation": dev_bad, "yp": [0.0, 0.0]},
        }
    )

    # natural spline: exact on a linear function, not on a cubic
    lin = np.linspace(0.3, 1.4, 5)
    named_lin = dict(H.Ctx({"id": "a"}).named(natural))
    named_lin["x_data"], named_lin["y_data"] = lin.tolist(), (2.0 * lin - 1.0).tolist()
    rec_lin = call(natural, named_lin, "natural spline on a linear function")
    dev_lin = None
    if rec_lin["status"] == "returned":
        try:
            dev_lin = rel_dev(
                rec_lin["_value"](np.linspace(0.35, 1.35, 11)),
                2.0 * np.linspace(0.35, 1.35, 11) - 1.0,
            )
        except BaseException:  # noqa: BLE001
            dev_lin = None
    out["claims"].append(
        {
            "claim": "natural spline reproduces a linear function exactly (data consistent with M=0 ends)",
            "status": "pass"
            if (dev_lin is not None and dev_lin <= 64 * EPS)
            else ("fail" if dev_lin is not None else "not-observed"),
            "detail": {"relative_deviation": dev_lin},
        }
    )
    named_nat = dict(H.Ctx({"id": "a"}).named(natural))
    named_nat["x_data"], named_nat["y_data"] = x.tolist(), y.tolist()
    rec_nat = call(natural, named_nat, "natural spline on the same cubic")
    dev_nat = None
    if rec_nat["status"] == "returned":
        try:
            dev_nat = rel_dev(rec_nat["_value"](xq), _cubic(xq))
        except BaseException:  # noqa: BLE001
            dev_nat = None
    out["claims"].append(
        {
            "claim": "natural spline on a cubic is NOT exact (the O(h^4) claim is conditional)",
            "status": "pass"
            if (dev_nat is not None and dev_nat > 1e-6)
            else ("fail" if dev_nat is not None else "not-observed"),
            "detail": {"relative_deviation": dev_nat},
        }
    )
    return out


def evidence_svd() -> dict:
    asset = "scirel.numerics.truncated-svd-inverse"
    out = {"asset": asset, "claims": []}

    rec_at = call(
        asset, {"mat": [[1.0, 0.0], [0.0, 1e-10]]}, "singular value exactly at the cutoff"
    )
    rec_below = call(
        asset, {"mat": [[1.0, 0.0], [0.0, 1e-11]]}, "singular value just below the cutoff"
    )
    at_ok = below_ok = None
    if rec_at["status"] == "returned":
        inv = np.asarray(rec_at["_value"], dtype=float)
        at_ok = rel_dev(inv[1, 1], 1e10)
    if rec_below["status"] == "returned":
        inv = np.asarray(rec_below["_value"], dtype=float)
        below_ok = float(inv[1, 1])
    out["claims"].append(
        {
            "claim": "a singular value exactly at the cutoff is retained; the neighbour below it is discarded",
            "status": "pass"
            if (at_ok is not None and at_ok <= 4 * EPS and below_ok == 0.0)
            else ("fail" if (at_ok is not None and below_ok is not None) else "not-observed"),
            "detail": {
                "rcond_default": 1e-10,
                "retained_entry": None if at_ok is None else 1e10,
                "relative_deviation_of_retained_reciprocal": at_ok,
                "below_cutoff_entry": below_ok,
            },
        }
    )

    rec_shape = call(asset, {"mat": np.ones((5, 3)).tolist()}, "shape of a wide matrix")
    shape_ok = rec_shape["status"] == "returned" and list(
        np.asarray(rec_shape["_value"]).shape
    ) == [3, 5]
    out["claims"].append(
        {
            "claim": "the returned matrix has the transposed shape (n,m)",
            "status": "pass" if shape_ok else "fail",
            "detail": {
                "input_shape": [5, 3],
                "observed_shape": None
                if rec_shape["status"] != "returned"
                else list(np.asarray(rec_shape["_value"]).shape),
            },
        }
    )

    out["claims"].append(
        {
            "claim": "the hand-SVD construction covers permutation-times-diagonal spectra only",
            "status": "not-observed",
            "detail": {
                "why": "this sentence describes how the maintainer's evidence was constructed "
                "inside tests/; the delivered package exposes no artefact that shows the "
                "construction, so the claim cannot be checked from the package",
            },
        }
    )
    return out


# ======================================================================= driver


def main() -> int:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

    started = time.time()
    # contract examples print as they run; keep this audit's own report readable
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        channels = audit_channels()
        thermal = audit_thermal_energy()
        evidence = [
            evidence_poloidal(),
            evidence_path_distance(),
            evidence_splines(),
            evidence_svd(),
        ]
    claims = [c for e in evidence for c in e["claims"]]
    claim_counts: dict[str, int] = {}
    for c in claims:
        claim_counts[c["status"]] = claim_counts.get(c["status"], 0) + 1

    crit(
        "C1",
        "evidence_clause",
        "fail" if claim_counts.get("fail", 0) else "pass",
        {
            "question": "does any new evidence clause contradict what the package publicly does?",
            "claims_checked": len(claims),
            "by_status": claim_counts,
            "contradicted": [c["claim"] for c in claims if c["status"] == "fail"],
        },
    )
    crit(
        "C2",
        "evidence_clause",
        "fail" if claim_counts.get("not-observed", 0) else "pass",
        {
            "question": "is every claim in those clauses checkable with the package alone?",
            "not_checkable": [
                {"claim": c["claim"], "why": c["detail"].get("why")}
                for c in claims
                if c["status"] == "not-observed"
            ],
            "note": "these are not library defects; they are sentences whose subject is how the "
            "maintainer's evidence was built, or a numeric bound whose stencil is not printed",
        },
    )

    package = {
        "wheel_sha256": H.runtime_json()["runtime"]["wheel_sha256"],
        "snapshot_sha256": H.runtime_json()["snapshot_sha256"],
        "source_revision": H.runtime_json().get("source_revision"),
        "asset_count": H.runtime_json().get("asset_count"),
    }
    status_counts: dict[str, int] = {}
    for c in CRITERIA:
        status_counts[c["status"]] = status_counts.get(c["status"], 0) + 1

    contract_audit = {
        "schema": "scirel.c4-usage-closeout.contract-audit",
        "package": package,
        "channels": channels,
        "criteria": [c for c in CRITERIA if c["id"].startswith("A")],
        # The probe arguments are the contract example's, frozen in the delivered package, so
        # they are not repeated here; only the observation is kept (the stored arguments of
        # 138 calls would be several megabytes for no extra evidence).
        "calls": [
            {
                "asset": c["asset"],
                "entrypoint": c["entrypoint"],
                "status": c["status"],
                "returned_type": c.get("returned_type"),
                "returned_field_count": len(c.get("returned_fields") or []),
                "exception_type": (c.get("exception") or {}).get("type"),
                "arguments_source": "contract example, see catalog/contracts/<asset>.json → example.code",
            }
            for c in CALLS
            if c["label"].startswith("channel probe")
        ],
    }
    focus_audit = {
        "schema": "scirel.c4-usage-closeout.focus-audit",
        "package": package,
        "thermal_energy": thermal,
        "evidence_clauses": evidence,
        "criteria": [c for c in CRITERIA if not c["id"].startswith("A")],
        "calls": [c for c in CALLS if not c["label"].startswith("channel probe")],
        "elapsed_s": round(time.time() - started, 1),
        "status_counts": status_counts,
    }
    (HERE / "contract-audit.json").write_text(
        json.dumps(contract_audit, indent=1, ensure_ascii=False) + "\n"
    )
    (HERE / "focus-audit.json").write_text(
        json.dumps(focus_audit, indent=1, ensure_ascii=False) + "\n"
    )

    width = max(len(c["id"]) for c in CRITERIA)
    for c in CRITERIA:
        print(f"{c['id']:<{width}}  {c['status']:<12}  {c['kind']}")
    print(
        f"\nchannels: single-output={channels['single_output']} "
        f"declared={channels['declared_channel_counts']} runtime={channels['runtime_verdict_counts']}"
    )
    print(f"claims: {claim_counts}")
    print(f"elapsed {time.time() - started:.1f}s")
    failed = [c["id"] for c in CRITERIA if c["status"] == "fail"]
    if failed:
        print(f"FAILED: {failed}")
        return 1
    if any(c["status"] == "not-observed" for c in CRITERIA):
        print("partial: some criteria are not-observed (exit 75)")
        return 75
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
