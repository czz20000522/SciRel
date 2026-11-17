"""Declarative checks for the ``failure`` and ``inapplicable`` tasks.

Both kinds are fully determined by the frozen task record plus the delivered contract:
a failure task replaces exactly one declared field with the frozen stimulus value and
asserts the exception channel the contract declares; an inapplicable task quotes the
contract's own excluded clause and performs no substitute computation.
"""

from __future__ import annotations

import harness as H
from . import _common as C

CHECKS: dict = {}


def _failure(ctx: H.Ctx, task: dict) -> dict:
    stimuli = task["stimulus"]
    exc_ids = [c["id"] for c in task["criteria"] if c["kind"] == "exception"]
    criteria, answers, gaps = [], [], []
    sufficient = True

    for cid, stim in zip(exc_ids, stimuli):
        asset = stim["asset"]
        base = dict(ctx.named(asset))
        if stim["field"] not in base:
            criteria.append(
                C.crit(
                    cid,
                    "exception",
                    "fail",
                    {
                        "why": f"stimulus field {stim['field']!r} is not a parameter of {asset}",
                        "binding_parameters": sorted(base),
                    },
                )
            )
            sufficient = False
            continue
        mutated = dict(base)
        mutated[stim["field"]] = stim["value"]
        call = ctx.call(
            asset,
            mutated,
            label=f"declare {stim['field']}={stim['value']!r} only (frozen stimulus)",
        )
        quote = H.contract(asset)["failure_semantics"].get(stim["failure_key"], "")
        res = H.check_exception(ctx, call, asset, stim["failure_key"], stim["expected_exception"])
        phrase_ok = stim["declared_rejection"] in quote
        actual = call.get("exception")
        status = res["status"] if phrase_ok else "fail"
        if status != "pass":
            sufficient = False
        criteria.append(
            C.crit(
                cid,
                "exception",
                status,
                {
                    **res["detail"],
                    "declared_rejection_phrase": stim["declared_rejection"],
                    "declared_rejection_appears_in_contract_quote": phrase_ok,
                    "stimulus_field": stim["field"],
                    "stimulus_value": stim["value"],
                    "baseline_value": H.plain(base[stim["field"]]),
                },
            )
        )
        answers.append(
            {
                "asset": asset,
                "field": stim["field"],
                "baseline_value": H.plain(base[stim["field"]]),
                "requested_value": stim["value"],
                "outcome": call["status"],
                "exception_type": (actual or {}).get("type"),
                "exception_message": (actual or {}).get("message"),
                "declared_exception": stim["expected_exception"],
            }
        )

    # one call per stimulus, nothing substituted, nothing retried
    expected_calls = len(stimuli)
    one_each = len(ctx.calls) == expected_calls
    details = [H.plain(c["arguments"]) for c in ctx.calls]
    no_substitute = C.crit(
        "nosubstitute",
        "invariant",
        "pass" if one_each else "fail",
        {
            "calls_made": len(ctx.calls),
            "calls_expected": expected_calls,
            "note": "exactly the frozen stimulus was passed; no fallback method, clamp or retry",
            "arguments": details,
        },
    )
    for c in task["criteria"]:
        if c["kind"] == "invariant":
            no_substitute["id"] = c["id"]
            no_substitute["detail"]["statement"] = c.get("statement")
            criteria.append(no_substitute)
    if not one_each:
        sufficient = False
        gaps.append(H.gap("process", "the failure task made more calls than its frozen stimuli"))

    return {
        "criteria": criteria,
        "answer": {"value": answers, "unit": "exception type and message, as raised"},
        "independent_check": {
            "method": "the contract's failure_semantics quote is compared with the exception "
            "the library actually raised, field by field",
            "verdict": "pass" if sufficient else "fail",
        },
        "package_sufficient": sufficient,
        "sufficient_reason": (
            "the declared rejection channel is reproducible from the delivered contract: the "
            "same field, the same value and the same exception type the contract names"
            if sufficient
            else "the library did not raise the exception the delivered contract declares for this "
            "stimulus, or the contract quote does not contain the frozen phrase"
        ),
        "gaps": gaps,
    }


def _inapplicable(ctx: H.Ctx, task: dict) -> dict:
    asset = task["assets"][0]
    excluded = H.contract(asset)["applicability"]["excluded"]
    quote = task["excluded_quote"]
    present = any(quote in clause for clause in excluded)
    alternatives = (
        [a for a in H.capability_index().get("assets", []) if a.get("asset_id") != asset]
        if "assets" in H.capability_index()
        else []
    )

    criteria = [
        C.crit(
            "nocall",
            "invariant",
            "pass" if not ctx.calls else "fail",
            {
                "calls_made": len(ctx.calls),
                "note": "no value is computed at the excluded limit and no nearby nonzero "
                "wavenumber is presented as the requested limit",
            },
        )
    ]
    sufficient = present
    gaps = []
    if not present:
        gaps.append(
            H.gap(
                "blocking",
                f"excluded_quote {quote!r} is not literally present in "
                f"applicability.excluded of {asset}",
            )
        )
    gaps.append(
        H.gap(
            "process",
            "this task declares min_calls=1 (from its asset count) while its own invariant forbids "
            "computing a value at the excluded limit, so no public call is made; the honest "
            "deliverable is the quoted exclusion. Recorded as a task-list defect, not a package defect.",
        )
    )
    return {
        "criteria": criteria,
        "answer": {
            "value": {
                "excluded_quote": quote,
                "applicability_excluded": excluded,
                "capability_index_candidates": len(alternatives),
            },
            "unit": "quoted clause (no numerical value)",
            "statement": "the declared model excludes this limit; no substitute value is produced",
        },
        "independent_check": {
            "method": "the frozen excluded_quote is matched literally against the delivered "
            "contract's applicability.excluded list",
            "verdict": "pass" if present else "fail",
        },
        "package_sufficient": sufficient,
        "sufficient_reason": "the exclusion and its wording are delivered inside the package",
        "gaps": gaps,
    }


def _register(tasklist: dict) -> None:
    for task in tasklist["tasks"]:
        if task["kind"] == "failure":
            CHECKS[task["id"]] = _failure
        elif task["kind"] == "inapplicable":
            CHECKS[task["id"]] = _inapplicable
