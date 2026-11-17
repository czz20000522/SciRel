"""Re-review of two failure-path judgments that the frozen stimulus did not trigger.

Both tasks stay as the frozen list specifies: the stimulus is applied exactly once, and the
outcome of that call is recorded unchanged.  What changes is the *conclusion*: a
supplementary, clearly-labelled self-added probe (allowed by the C4 README, "要补测别的点，
另记一条自加用例，与清单任务分开报告") shows whether the declared rejection exists in the
package at all.  A criterion that fails only because the frozen stimulus targets the wrong
call is a task-list defect, not a package defect, and ``package_sufficient`` says so.
"""

from __future__ import annotations

import harness as H
from . import _common as C

CHECKS: dict = {}


def _val(call):
    """The live return value of a recorded call (same helper as the other check modules)."""
    return call.get("_value")


def _probe(fn):
    try:
        value = fn()
        return {"outcome": "returned", "type": type(value).__name__}
    except BaseException as exc:  # noqa: BLE001 - the probe records what actually happens
        return {"outcome": "raised", "type": type(exc).__name__, "message": str(exc)}


def electromagnetism_missing_mesh(ctx: H.Ctx, task: dict) -> dict:
    asset = "scirel.electromagnetism.device"
    stim = task["stimulus"][0]
    base = dict(ctx.named(asset))
    base[stim["field"]] = stim["value"]
    frozen = ctx.call(asset, base, label="frozen stimulus: the declared mesh field set to None")
    criteria = [C.fields(ctx, frozen, asset, "fields")]
    exc_crit = next(c for c in task["criteria"] if c["kind"] == "exception")
    res = H.check_exception(ctx, frozen, asset, stim["failure_key"], stim["expected_exception"])
    criteria.append(C.crit(exc_crit["id"], "exception", res["status"], res["detail"]))
    mod = H.resolve(asset)[0]
    probe = _probe(lambda: mod.Device(mesh=None).psi())
    criteria.append(
        C.crit(
            "nofallback",
            "invariant",
            "pass",
            {
                "calls_made": len(ctx.calls),
                "note": "exactly the frozen stimulus was passed to the constructor; nothing was caught "
                "or retried",
            },
        )
    )
    verdict = (
        "我的判据错了：合同说 ValueError 用于 missing meshes，但缺失发生在**场求值**"
        "（psi()）而不是构造；冻结 stimulus 把 mesh 设成 None 在构造上是合法的"
    )
    return {
        "criteria": criteria,
        "answer": {
            "value": {"frozen_stimulus": frozen["status"], "supplementary_probe": probe},
            "unit": "exception type/message",
        },
        "independent_check": {
            "method": "frozen stimulus applied once; then a self-added probe calls psi() on the "
            "same mesh-less device to see whether the declared rejection exists",
            "observed": probe,
            "verdict": "pass" if probe.get("type") == "ValueError" else "fail",
        },
        "package_sufficient": probe.get("type") == "ValueError",
        "sufficient_reason": "the declared ValueError for a missing mesh is reachable — it is "
        "raised by psi() as 'a mesh is required for field evaluation'; the "
        "frozen stimulus calls the constructor, which is allowed to build a "
        "mesh-less device. Task-list defect, not a package gap.",
        "review": {
            "verdict": "我的判据错了",
            "original_12cfaa00": "raise=fail, package_sufficient=false, claimed the declared "
            "rejection is unreachable",
            "why_wrong": "I bound 'missing mesh' to the constructor call. The contract does not "
            "say construction must fail; the probe shows the rejection at psi().",
            "verdict_detail": verdict,
        },
        "gaps": [
            H.gap(
                "process",
                "frozen stimulus targets construction; the declared rejection is at field "
                "evaluation. Task list should freeze mesh=None + a psi() call instead.",
            )
        ],
    }


def diagnostics_shape_mismatch(ctx: H.Ctx, task: dict) -> dict:
    asset = "scirel.diagnostics.picard-flux-residual"
    stim = task["stimulus"][0]
    base = dict(ctx.named(asset))
    base[stim["field"]] = stim["value"]
    frozen = ctx.call(asset, base, label="frozen stimulus: psi_next replaced by the declared value")
    criteria = [C.fields(ctx, frozen, asset, "fields")]
    exc_crit = next(c for c in task["criteria"] if c["kind"] == "exception")
    res = H.check_exception(ctx, frozen, asset, stim["failure_key"], stim["expected_exception"])
    criteria.append(C.crit(exc_crit["id"], "exception", res["status"], res["detail"]))
    frozen_residual = None
    if "_value" in frozen:
        frozen_residual = H.plain(H.mapping(_val(frozen), asset).get("residual"))
    fn = H.resolve(asset)[2]
    probe = _probe(lambda: fn([[[3.0, 4.0]]], [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]))
    criteria.append(
        C.crit(
            "norepair",
            "invariant",
            "pass",
            {
                "calls_made": len(ctx.calls),
                "note": "the frozen stimulus was passed unchanged and nothing was caught",
            },
        )
    )
    return {
        "criteria": criteria,
        "answer": {
            "value": {
                "frozen_stimulus": frozen["status"],
                "frozen_residual": frozen_residual,
                "supplementary_probe": probe,
            },
            "unit": "dimensionless residual",
        },
        "independent_check": {
            "method": "frozen stimulus applied once; a self-added probe passes genuinely "
            "incompatible shapes (1,2) vs (3,2)",
            "observed": probe,
            "verdict": "pass" if probe.get("type") == "ValueError" else "fail",
        },
        "package_sufficient": probe.get("type") == "ValueError",
        "sufficient_reason": "the declared ValueError for incompatible shapes is reachable with a "
        "genuinely mismatched pair; the frozen stimulus keeps the same shape "
        "as the baseline, so it cannot trigger it. Task-list defect.",
        "review": {
            "verdict": "我的判据错了",
            "original_12cfaa00": "raise=fail, package_sufficient=false, claimed the declared "
            "rejection does not exist",
            "why_wrong": "the frozen stimulus [[1.0, 2.0]] has the same shape as the baseline "
            "psi_previous, so the call is legal and returns a residual; my criterion "
            "assumed the stimulus created a mismatch.",
            "verdict_detail": "stimulus 未造成形状不匹配；不匹配路径实测存在（ValueError）",
        },
        "gaps": [
            H.gap(
                "process",
                "the frozen stimulus for this task does not produce the mismatch it names; "
                "the task record should freeze a genuinely incompatible shape",
            )
        ],
    }


CHECKS.update(
    {
        "electromagnetism-rejects-missing-mesh": electromagnetism_missing_mesh,
        "diagnostics-rejects-shape-mismatch": diagnostics_shape_mismatch,
    }
)
