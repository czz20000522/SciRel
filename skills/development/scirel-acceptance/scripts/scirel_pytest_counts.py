"""Write one JSON file of pytest counts for ``check_all.py``'s ``tests`` step.

Loaded explicitly with ``-p scirel_pytest_counts``: nothing is discovered by name, so a third-party
environment cannot inject a plugin that happens to share the name.

The plugin is an observer only. It never changes a test outcome, never rewrites output and never
decides red or green: it records what pytest did and leaves the verdict to ``check_all.py``. The
invariants that make the numbers trustworthy live here, in one place, so a counter cannot be added
to one branch and forgotten in another:

* every selected test has exactly one terminal outcome;
* ``selected == passed + failed + error + skipped + xfailed + xpassed``;
* ``collected == selected + deselected``.

A report that breaks any of them is written with ``consistent`` false and the reason spelled out,
and ``check_all.py`` refuses it rather than reporting a number nobody can check.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

COUNTS_OPTION = "--scirel-counts"

OUTCOMES = ("passed", "failed", "error", "skipped", "xfailed", "xpassed")
REASON_LIMIT = 160
REASON_TRUNCATION = "…"
# A recorded reason is the audit trail for a test that never ran; a bare label is not one.
PLACEHOLDER_REASONS = frozenset(
    {
        "skip",
        "skipped",
        "skip.",
        "xfail",
        "xfailed",
        "n/a",
        "na",
        "none",
        "unknown",
        "todo",
        "tbd",
        "-",
        "?",
        "...",
    }
)
REASON_WORD = re.compile(r"[^\W_]{2,}")


def final_outcome(phases: list[dict]) -> str | None:
    """Reduce observed phases to one result; retain call results even after a teardown error."""
    expected = (
        ["setup", "call", "teardown"]
        if phases and phases[0]["outcome"] == "passed"
        else ["setup", "teardown"]
    )
    if [phase["when"] for phase in phases] != expected:
        return None
    outcomes = []
    for phase in phases:
        outcome, when = phase["outcome"], phase["when"]
        if outcome == "failed":
            outcomes.append("failed" if when == "call" else "error")
        elif outcome == "skipped":
            outcomes.append("xfailed" if "wasxfail" in phase else "skipped")
        elif when == "call":
            outcomes.append("xpassed" if "wasxfail" in phase else "passed")
    for outcome in ("error", "failed", "xfailed", "skipped", "xpassed", "passed"):
        if outcome in outcomes:
            return outcome
    return None


def _require_reason(nodeid: str, kind: str, reason: str) -> None:
    """A reason has to name something; a blank or bare label is not an audit trail.

    ``pytest.skip()`` and ``@pytest.mark.xfail`` without a reason produce an empty or
    placeholder string. Such a record says a test did not run but not why, so nobody can
    check the claim; it is refused here instead of being summarised as a green skip line.
    """
    text = reason.strip()
    if not text:
        raise ValueError(f"{nodeid}: {kind} reason is blank")
    if text.casefold() in PLACEHOLDER_REASONS:
        raise ValueError(f"{nodeid}: {kind} reason is a bare placeholder, not a reason")
    if REASON_WORD.search(text) is None:
        raise ValueError(f"{nodeid}: {kind} reason carries no word to audit")
    if text in nodeid:
        raise ValueError(f"{nodeid}: {kind} reason only repeats the test identity")


def _recorded_from_marker(recorded: str, marker: str) -> bool:
    """The skip reason an xfail record keeps is the marker reason, cut at REASON_LIMIT."""
    if recorded.endswith(REASON_TRUNCATION):
        recorded = recorded[: -len(REASON_TRUNCATION)]
    return bool(recorded) and marker.startswith(recorded)


def validate_execution_records(report: dict) -> None:
    """Validate the single counts protocol, including identities and phase-derived totals."""
    if type(report.get("schema")) is not int or report["schema"] != 2:
        raise ValueError("execution records require counts schema 2")
    if type(report.get("pytest_exitstatus")) is not int or report["pytest_exitstatus"] not in (
        0,
        1,
    ):
        raise ValueError("pytest collection or run did not finish normally")
    if report.get("collection_finished") is not True:
        raise ValueError("collection did not finish")
    collection = report.get("collection_reports")
    if not isinstance(collection, list):
        raise ValueError("missing collection reports")
    for item in collection:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("nodeid"), str)
            or item.get("outcome") not in ("failed", "skipped")
            or not isinstance(item.get("reason"), str)
        ):
            raise ValueError("invalid collection report")
        if item["outcome"] == "failed":
            raise ValueError("collection failed")
    selected = report.get("selected_nodeids")
    if (
        not isinstance(selected, list)
        or any(not isinstance(node, str) or not node for node in selected)
        or len(set(selected)) != len(selected)
        or len(selected) != report["selected"]
    ):
        raise ValueError("missing, duplicate or mismatched selected nodeids")
    results = report.get("results")
    if not isinstance(results, list) or len(results) != len(selected):
        raise ValueError("missing or duplicate per-test results")
    totals = dict.fromkeys(OUTCOMES, 0)
    skips: dict[str, list[str]] = {}
    for nodeid, item in zip(selected, results, strict=True):
        if not isinstance(item, dict) or item.get("nodeid") != nodeid:
            raise ValueError("result identities do not match selected nodeids in order")
        phases = item.get("phases")
        if not isinstance(phases, list) or not phases:
            raise ValueError(f"{nodeid}: missing phases")
        for phase in phases:
            if (
                not isinstance(phase, dict)
                or phase.get("when") not in ("setup", "call", "teardown")
                or phase.get("outcome") not in ("passed", "failed", "skipped")
                or ("wasxfail" in phase and not isinstance(phase["wasxfail"], str))
                or (phase["outcome"] == "skipped" and not isinstance(phase.get("reason"), str))
            ):
                raise ValueError(f"{nodeid}: invalid phase")
        expected = (
            ["setup", "call", "teardown"]
            if phases[0]["outcome"] == "passed"
            else ["setup", "teardown"]
        )
        if [phase["when"] for phase in phases] != expected:
            raise ValueError(f"{nodeid}: missing, duplicate or out-of-order phases")
        for phase in phases:
            if phase["outcome"] == "skipped":
                _require_reason(nodeid, "skip", phase["reason"])
            if "wasxfail" in phase:
                _require_reason(nodeid, "xfail", phase["wasxfail"])
                if phase["outcome"] == "skipped" and not _recorded_from_marker(
                    phase["reason"], phase["wasxfail"]
                ):
                    raise ValueError(f"{nodeid}: xfail reason disagrees with the marker reason")
        outcome = final_outcome(phases)
        if outcome is None or item.get("outcome") != outcome:
            raise ValueError(f"{nodeid}: final outcome disagrees with phases")
        totals[outcome] += 1
        if outcome == "skipped":
            reason = next(phase["reason"] for phase in phases if phase["outcome"] == "skipped")
            skips.setdefault(reason, []).append(nodeid)
    if any(report.get(name) != total for name, total in totals.items()):
        raise ValueError("per-test outcomes disagree with counts")
    if report.get("skip_reasons") != skips:
        raise ValueError("skip reasons disagree with per-test results")
    if report["pytest_exitstatus"] == 0 and (totals["failed"] or totals["error"]):
        raise ValueError("pytest exit status disagrees with failed/error outcomes")
    if report["pytest_exitstatus"] == 1 and not (totals["failed"] or totals["error"]):
        raise ValueError(
            "pytest exit status 1 without failed/error outcomes: the exit code and the"
            " recorded outcomes disagree"
        )


def pytest_addoption(parser):
    group = parser.getgroup("scirel")
    group.addoption(
        COUNTS_OPTION,
        action="store",
        default=None,
        metavar="PATH",
        help="write pytest counts as JSON to PATH; required by check_all.py",
    )


def _skip_reason(report) -> str:
    """Return the reason pytest recorded for a skip, without reading a human summary line."""
    xfail = getattr(report, "wasxfail", None)
    if xfail:
        reason = str(xfail)
    else:
        longrepr = getattr(report, "longrepr", None)
        if isinstance(longrepr, tuple) and len(longrepr) == 3:
            reason = str(longrepr[2])
        else:
            crash = getattr(longrepr, "reprcrash", None)
            if crash is not None and getattr(crash, "message", ""):
                reason = str(crash.message)
            else:
                reason = str(longrepr).strip() if longrepr else "unknown"
    prefix = "Skipped: "
    if reason.startswith(prefix):
        reason = reason[len(prefix) :]
    # A skip reason can be a whole traceback; the summary line has to stay readable.
    return reason if len(reason) <= REASON_LIMIT else reason[:REASON_LIMIT] + "…"


class CountsPlugin:
    """Record pytest's per-test outcomes and the collection counts they must add up to."""

    def __init__(self) -> None:
        self.selected = 0
        self.selected_nodeids: list[str] = []
        self.collection_finished = False
        self.collection_reports: list[dict] = []
        self.deselected = 0
        self.phases: dict[str, list[dict]] = {}

    def pytest_deselected(self, items) -> None:
        self.deselected += len(items)

    def pytest_collection_finish(self, session) -> None:
        # All collection filters have finished; modifyitems hook order is not fixed.
        self.selected = len(session.items)
        self.selected_nodeids = [item.nodeid for item in session.items]
        self.collection_finished = True

    def pytest_collectreport(self, report) -> None:
        if report.failed or report.skipped:
            self.collection_reports.append(
                {"nodeid": report.nodeid, "outcome": report.outcome, "reason": str(report.longrepr)}
            )

    def pytest_runtest_logreport(self, report) -> None:
        phase = {"when": report.when, "outcome": report.outcome}
        if hasattr(report, "wasxfail"):
            phase["wasxfail"] = str(report.wasxfail)
        if report.skipped:
            phase["reason"] = _skip_reason(report)
        self.phases.setdefault(report.nodeid, []).append(phase)

    def report(self, exitstatus: int) -> dict:
        totals = {name: 0 for name in OUTCOMES}
        results = []
        skips: dict[str, list[str]] = {}
        # Keep unstarted selections and unexpected report identities too, even on interruption.
        for nodeid in dict.fromkeys([*self.selected_nodeids, *self.phases]):
            phases = self.phases.get(nodeid, [])
            outcome = final_outcome(phases)
            results.append({"nodeid": nodeid, "outcome": outcome, "phases": phases})
            if outcome is not None:
                totals[outcome] += 1
            if outcome == "skipped":
                reason = next(phase["reason"] for phase in phases if phase["outcome"] == "skipped")
                skips.setdefault(reason, []).append(nodeid)
        report = {
            "schema": 2,
            "pytest_exitstatus": int(exitstatus),
            "collection_finished": self.collection_finished,
            "collection_reports": self.collection_reports,
            "selected_nodeids": self.selected_nodeids,
            "results": results,
            "collected": self.selected + self.deselected,
            "selected": self.selected,
            "deselected": self.deselected,
            **totals,
            "skip_reasons": skips,
        }
        try:
            validate_execution_records(report)
        except ValueError as error:
            report.update(consistent=False, inconsistency=str(error))
        else:
            report.update(consistent=True, inconsistency="")
        return report


def pytest_configure(config):
    import pytest

    # Fail early and plainly when the caller forgot the report path: the plugin exists to be
    # consumed, and a run that silently produced nothing would look green.
    if not config.getoption(COUNTS_OPTION):
        raise pytest.UsageError(f"check_all.py must pass {COUNTS_OPTION}=<path>")
    config.pluginmanager.register(CountsPlugin(), "scirel_counts")


def pytest_sessionfinish(session, exitstatus) -> None:
    destination = session.config.getoption(COUNTS_OPTION)
    plugin = session.config.pluginmanager.get_plugin("scirel_counts")
    Path(destination).write_text(
        json.dumps(plugin.report(exitstatus), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
