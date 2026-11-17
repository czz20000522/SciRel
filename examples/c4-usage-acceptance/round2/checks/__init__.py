"""Consumer-side checks, one callable per task id.

``CHECKS[task_id](ctx, task) -> dict`` returns the task's criteria, answer, independent
check and sufficiency verdict.  Kinds that are fully determined by the frozen task record
(``failure``, ``inapplicable``) are generated from the task list itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import harness as H
from . import batch1, batch2, batch3, generic, kinetic

CHECKS: dict = {}

_TASKLIST = json.loads((Path(__file__).resolve().parents[2] / "tasklist.json").read_text())
generic._register(_TASKLIST)
CHECKS.update(generic.CHECKS)
CHECKS.update(kinetic.CHECKS)
CHECKS.update(batch1.CHECKS)
CHECKS.update(batch2.CHECKS)
CHECKS.update(batch3.CHECKS)
