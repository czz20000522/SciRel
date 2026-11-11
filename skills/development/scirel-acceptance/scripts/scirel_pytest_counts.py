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
from pathlib import Path

import pytest

COUNTS_OPTION = "--scirel-counts"

OUTCOMES = ("passed", "failed", "error", "skipped", "xfailed", "xpassed")
REASON_LIMIT = 160


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
        self.deselected = 0
        self.outcomes: dict[str, str] = {}
        self.skip_reasons: dict[str, list[str]] = {}
        self.conflicts: list[str] = []

    def pytest_deselected(self, items) -> None:
        self.deselected += len(items)

    def pytest_collection_finish(self, session) -> None:
        # All collection filters have finished; modifyitems hook order is not fixed.
        self.selected = len(session.items)

    def pytest_runtest_logreport(self, report) -> None:
        outcome = self._outcome(report)
        if outcome is None:
            return
        previous = self.outcomes.get(report.nodeid)
        if previous is not None:
            if previous != outcome:
                self.conflicts.append(f"{report.nodeid}: {previous} then {outcome}")
            return
        self.outcomes[report.nodeid] = outcome
        if outcome == "skipped":
            self.skip_reasons.setdefault(_skip_reason(report), []).append(report.nodeid)

    def _outcome(self, report) -> str | None:
        # pytest reports a test in up to three phases: a setup or teardown failure is an error, a
        # call failure is a failure. An xfail marker shows up as a skip (the test failed as
        # expected) or as a pass on the call phase (it passed unexpectedly); a strict xfail reports
        # its unexpected pass as a failure, and pytest counts that as failed, so it stays failed.
        xfail = getattr(report, "wasxfail", None)
        if report.skipped:
            return "xfailed" if xfail is not None else "skipped"
        if report.failed:
            return "error" if report.when in ("setup", "teardown") else "failed"
        if report.when == "call" and report.passed:
            return "xpassed" if xfail is not None else "passed"
        return None

    def report(self, exitstatus: int) -> dict:
        totals = {name: 0 for name in OUTCOMES}
        for outcome in self.outcomes.values():
            totals[outcome] += 1
        problems = list(self.conflicts)
        if len(self.outcomes) != self.selected:
            problems.append(
                f"{self.selected} selected but {len(self.outcomes)} reached a terminal outcome"
            )
        return {
            "schema": 1,
            "pytest_exitstatus": int(exitstatus),
            "collected": self.selected + self.deselected,
            "selected": self.selected,
            "deselected": self.deselected,
            **totals,
            "skip_reasons": self.skip_reasons,
            "consistent": not problems,
            "inconsistency": "; ".join(problems),
        }


def pytest_configure(config):
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
