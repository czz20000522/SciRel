"""Shared criterion helpers for the C4 round-2 consumer."""

from __future__ import annotations

import harness as H


def crit(cid: str, kind: str, status: str, detail) -> dict:
    assert status in ("pass", "fail", "not-run"), status
    return {"id": cid, "kind": kind, "status": status, "detail": detail}


def fields(ctx: H.Ctx, call: dict, asset: str, cid: str = "fields") -> dict:
    res = H.check_fields(ctx, call, asset)
    return crit(cid, "contract_fields", res["status"], res["detail"])


def params(ctx: H.Ctx, asset: str, expected: list[str], cid: str = "params") -> dict:
    """Only contract-declared parameter names may be passed.

    ``expected`` names the parameters the task's criterion cares about.  A name that the
    callback left at its declared default is reported as defaulted rather than failed:
    the criterion forbids inventing parameters, it does not force a default to be passed.
    """
    used = sorted(ctx.named(asset))
    declared = H.input_names(asset)
    undeclared = [n for n in used if n not in declared]
    not_a_contract_input = [n for n in expected if n not in declared]
    defaulted = [n for n in expected if n in declared and n not in used]
    status = "pass" if not undeclared and not not_a_contract_input else "fail"
    return crit(
        cid,
        "parameters",
        status,
        {
            "contract_inputs": declared,
            "args_used": used,
            "expected_names": expected,
            "expected_names_absent_from_contract": not_a_contract_input,
            "expected_names_left_at_default": defaulted,
            "undeclared_args": undeclared,
        },
    )


def not_run(cid: str, kind: str, why: str, detail=None) -> dict:
    return crit(cid, kind, "not-run", {"why": why, **(detail or {})})


def finite(value) -> bool:
    import numpy as np

    arr = np.asarray(value)
    try:
        return bool(np.all(np.isfinite(arr)))
    except (TypeError, ValueError):
        return False
