"""Body-level adapter used by a host-controlled CodeFusion runner."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scirel_workflow import AutomatedCheckResult, CandidatePackage
from scirel_workflow.models import canonical_json


def _candidate_from_body(body: bytes) -> CandidatePackage:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("candidate artifact must contain a JSON object") from exc
    return CandidatePackage.from_mapping(payload)


def _next_action(checks: tuple[dict[str, Any], ...], gaps: tuple[str, ...]) -> str:
    if not gaps and checks and all(check.get("status") == "passed" for check in checks):
        return "ready"
    automations = {
        str(issue.get("automation"))
        for check in checks
        for issue in check.get("issues", ())
        if isinstance(issue, Mapping) and issue.get("automation")
    }
    if "request_rework" in automations:
        return "rework_requested"
    if automations.intersection(
        {"discover_or_generate_test", "resolve_or_request_evidence"}
    ):
        return "retry"
    return "needs_evidence"


def execute_automated_check(
    candidate_body: bytes,
    *,
    candidate_id: str | None = None,
    source_digest: str | None = None,
    result_id: str | None = None,
) -> bytes:
    """Return a JSON ``AutomatedCheckResult`` body for one candidate.

    The host validates the input artifact digest before calling this function.
    SciRel still checks domain identifiers and re-derives inventory gaps before
    serializing the result. This function does not edit source files.
    """

    candidate = _candidate_from_body(candidate_body)
    if candidate_id is not None and candidate.candidate_id != candidate_id:
        raise ValueError("candidate_id does not match candidate artifact")
    if source_digest is not None and candidate.source_digest != source_digest:
        raise ValueError("source_digest does not match candidate artifact")
    if result_id is None:
        result_id = "result-" + hashlib.sha256(candidate_body).hexdigest()
    checks = tuple(dict(check) for check in candidate.automated_checks)
    if not checks:
        checks = ({"name": "candidate_checks", "status": "failed"},)
    gaps = tuple(
        dict.fromkeys(
            (*candidate.gaps, *CandidatePackage._inventory_gaps(list(candidate.assets)))
        )
    )
    return canonical_json(
        AutomatedCheckResult(
            result_id=result_id,
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            checks=checks,
            gaps=gaps,
            next_action=_next_action(checks, gaps),
        ).to_dict()
    )
